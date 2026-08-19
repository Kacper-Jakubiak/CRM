from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from db import EmailMessage, Thread
from services.customer_service import add_customer_no_commit
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
    ingested_messages = []
    customer_cache = {}
    batch_thread_map = {}

    try:
        for email_data in emails:
            provider_message_id = email_data.provider_message_id

            existing_message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()
            if existing_message:
                batch_thread_map[provider_message_id] = existing_message.thread_id
                logger.info(f"Skipping duplicate message with provider_message_id '{provider_message_id}'.")
                continue

            customer_email = email_data.customer_email
            parent_message_provider_id = email_data.parent_message_provider_id

            thread_id = None
            if parent_message_provider_id:
                if parent_message_provider_id in batch_thread_map:
                    thread_id = batch_thread_map[parent_message_provider_id]
                else:
                    parent = db.query(EmailMessage).filter_by(provider_message_id=parent_message_provider_id).first()
                    if parent:
                        thread_id = parent.thread_id

            if thread_id is None:
                thread = Thread()
                db.add(thread)
                db.flush()
                thread_id = thread.id

            batch_thread_map[provider_message_id] = thread_id

            if customer_email in customer_cache:
                customer_id = customer_cache[customer_email]
            else:
                customer = add_customer_no_commit(db, email_data.customer_name, customer_email)
                customer_id = customer.id
                customer_cache[customer_email] = customer_id

            message = EmailMessage(
                customer_id=customer_id,
                provider_message_id=provider_message_id,
                sender=customer_email,
                subject=email_data.subject,
                body=email_data.body,
                sent_at=email_data.sent_at,
                needs_response=email_data.needs_response,
                category=email_data.category,
                thread_id=thread_id
            )

            db.add(message)
            ingested_messages.append(message)

        db.commit()

        for message in ingested_messages:
            db.refresh(message)

        logger.info(f"Successfully ingested batch of {len(ingested_messages)} email messages.")
        return ingested_messages
        
    except (SQLAlchemyError, ValueError) as e:
        db.rollback()
        logger.error(f"Failed to ingest email batch: {e}", exc_info=True)
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