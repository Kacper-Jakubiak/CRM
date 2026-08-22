from sqlalchemy import insert
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from db import EmailMessage, Thread, Customer
from util.email_util import extract_domain
from logger import logger

from schemas import EmailIngestItem


def get_emails(db: Session) -> list[EmailMessage]:
    try:
        messages = db.query(EmailMessage).all()
        logger.info(f"Retrieved {len(messages)} total email messages.")
        return messages
    except SQLAlchemyError as e:
        logger.error(f"Failed to retrieve emails: {e}", exc_info=True)
        raise


def get_newest_email(db: Session) -> EmailMessage | None:
    try:
        message = db.query(EmailMessage).order_by(EmailMessage.sent_at.desc()).first()
        logger.info(f"Retrieved email message.")
        return message
    except SQLAlchemyError as e:
        logger.error(f"Failed to retrieve email: {e}", exc_info=True)
        raise


def get_thread_messages(db: Session, thread_id: int) -> list[EmailMessage] | None:
    try:
        thread = db.query(Thread).filter_by(id=thread_id).first()
        if not thread:
            logger.warning(f"Thread '{thread_id}' not found when fetching messages.")
            return None

        messages = db.query(EmailMessage).filter_by(thread_id=thread_id).all()
        logger.info(f"Retrieved {len(messages)} messages for thread_id '{thread_id}'.")
        return messages
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch messages for thread_id '{thread_id}': {e}", exc_info=True)
        raise


def ingest_email_batch(db: Session, emails: list[EmailIngestItem]) -> list[EmailMessage]:
    if not emails:
        return []

    try:
        customer_emails = {item.customer_email for item in emails}

        existing_customers = db.query(Customer).filter(Customer.email.in_(customer_emails)).all()
        existing_emails = {c.email for c in existing_customers}
        missing_emails = customer_emails - existing_emails

        new_customers_data = []
        seen_in_batch = set()

        for email_data in emails:
            email = email_data.customer_email
            if email in missing_emails and email not in seen_in_batch:
                seen_in_batch.add(email)
                new_customers_data.append({
                    "email": email,
                    "name": email_data.customer_name,
                    "company_domain": extract_domain(email),
                })

        if new_customers_data:
            db.execute(insert(Customer), new_customers_data)

        batch_email_ids = {item.provider_message_id for item in emails}
        parent_ids = {item.parent_message_provider_id for item in emails if item.parent_message_provider_id}
        all_needed_provider_ids = batch_email_ids.union(parent_ids)

        existing_messages = db.query(EmailMessage).filter(
            EmailMessage.provider_message_id.in_(all_needed_provider_ids)
        ).all()
        
        message_map = {m.provider_message_id: m for m in existing_messages}
        batch_thread_map = {pid: m.thread_id for pid, m in message_map.items()}

        ingested_messages: list[EmailMessage] = []

        for email_data in emails:
            provider_message_id = email_data.provider_message_id

            if provider_message_id in message_map:
                logger.info(f"Skipping duplicate message with provider_message_id '{provider_message_id}'.")
                continue

            parent_id = email_data.parent_message_provider_id
            thread_id = None

            if parent_id:
                thread_id = batch_thread_map.get(parent_id)

            if thread_id is None:
                thread = Thread()
                db.add(thread)
                db.flush()
                thread_id = thread.id

            batch_thread_map[provider_message_id] = thread_id

            message = EmailMessage(
                provider_message_id=provider_message_id,
                customer_email=email_data.customer_email,
                subject=email_data.subject,
                body=email_data.body,
                sent_at=email_data.sent_at,
                needs_response=email_data.needs_response,
                category=email_data.category,
                thread_id=thread_id
            )

            db.add(message)
            ingested_messages.append(message)
            message_map[provider_message_id] = message

        db.commit()

        for message in ingested_messages:
            db.refresh(message)

        logger.info(f"Successfully ingested batch of {len(ingested_messages)} email messages.")
        return ingested_messages

    except (SQLAlchemyError, ValueError) as e:
        db.rollback()
        logger.error(f"Failed to ingest email batch: {e}", exc_info=True)
        raise


def set_seen(db: Session, provider_message_id: str, seen_status: bool) -> EmailMessage | None:
    try:
        message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()
        if message is None:
            logger.warning(f"Entry '{provider_message_id}' not found when fetching entries.")
            return None
        message.seen = seen_status
        db.commit()
        db.refresh(message)
        logger.info(f"Updated 'seen' to {seen_status} for message '{provider_message_id}'.")
        return message
    except SQLAlchemyError as e:
        logger.error(f"Failed to retrieve message: {e}", exc_info=True)
        raise

      
def update_email_status(db: Session, provider_message_id: str, needs_response: bool) -> EmailMessage | None:
    try:
        message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()
        if not message:
            logger.warning(f"Email message '{provider_message_id}' not found when updating status.")
            return None

        message.needs_response = needs_response
        db.commit()
        db.refresh(message)

        logger.info(f"Updated 'needs_response' to {needs_response} for provider_message_id '{provider_message_id}'.")
        return message
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to update status for message '{provider_message_id}': {e}", exc_info=True)
        raise


def update_all_email_status(db: Session, needs_response: bool) -> None:
    try:
        updated_count = db.query(EmailMessage).update(
            {EmailMessage.needs_response: needs_response},
            synchronize_session=False
        )
        db.commit()
        logger.info(f"Updated 'needs_response' status to {needs_response} for {updated_count} messages.")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to update all email statuses: {e}", exc_info=True)
        raise


def get_email(db: Session, provider_message_id: str) -> EmailMessage | None:
    try:
        message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()
        if not message:
            logger.warning(f"Email message with provider_message_id '{provider_message_id}' not found.")
            return None
        return message
    except SQLAlchemyError as e:
        logger.error(f"Failed to retrieve email '{provider_message_id}': {e}", exc_info=True)
        raise


def move_email_to_thread(db: Session, provider_message_id: str, new_thread_id: int) -> EmailMessage | None:
    try:
        message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()
        if not message:
            logger.warning(f"Email message '{provider_message_id}' not found when moving to new thread.")
            return None

        thread = db.query(Thread).filter_by(id=new_thread_id).first()
        if not thread:
            logger.warning(f"Destination thread_id '{new_thread_id}' not found.")
            return None

        message.thread_id = new_thread_id
        db.commit()
        db.refresh(message)

        logger.info(f"Moved message '{provider_message_id}' to thread_id '{new_thread_id}'.")
        return message
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to move message '{provider_message_id}' to thread '{new_thread_id}': {e}", exc_info=True)
        raise


def merge_threads(db: Session, old_thread_id: int, new_thread_id: int) -> list[EmailMessage] | None:
    try:
        old_thread = db.query(Thread).filter_by(id=old_thread_id).first()
        if not old_thread:
            logger.warning(f"Source thread_id '{old_thread_id}' not found for merging.")
            return None

        new_thread = db.query(Thread).filter_by(id=new_thread_id).first()
        if not new_thread:
            logger.warning(f"Target thread_id '{new_thread_id}' not found for merging.")
            return None

        moved_count = db.query(EmailMessage).filter_by(thread_id=old_thread_id).update(
            {EmailMessage.thread_id: new_thread_id},
            synchronize_session=False
        )

        messages = db.query(EmailMessage).filter_by(thread_id=new_thread_id).all()
        db.commit()

        logger.info(f"Merged thread_id '{old_thread_id}' into '{new_thread_id}' ({moved_count} messages moved).")
        return messages
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to merge thread '{old_thread_id}' into '{new_thread_id}': {e}", exc_info=True)
        raise