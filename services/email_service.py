from sqlalchemy import insert
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from db import EmailMessage
from services import customer_service
from logger import logger
from util.email_util import map_emails

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
        messages = db.query(EmailMessage).filter_by(thread_id=thread_id).all()
        logger.info(f"Retrieved {len(messages)} messages for thread_id '{thread_id}'.")
        return messages
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch messages for thread_id '{thread_id}': {e}", exc_info=True)
        raise


def ingest_email_batch(db: Session, email_requests: list[EmailIngestItem]) -> list[EmailMessage]:
    if not email_requests:
        return []

    try:
        customer_data = [(item.customer_email, item.customer_name) for item in email_requests]
        customer_service.add_new_customers(db, customer_data)

        ids = {item.provider_message_id for item in email_requests}
        existing_ids = {id for (id,) in db.query(EmailMessage.provider_message_id).filter(EmailMessage.provider_message_id.in_(ids)).all()}

        thread_map = map_emails(email_requests, get_emails(db))

        new_messages: list[EmailMessage] = []
        seen_ids = set()
        for item in email_requests:
            if item.provider_message_id in existing_ids or item.provider_message_id in seen_ids:
                logger.info(f"Skipping duplicate message with provider_message_id '{item.provider_message_id}'.")
                continue

            message = EmailMessage(
                provider_message_id=item.provider_message_id,
                customer_email=item.customer_email,
                subject=item.subject,
                body=item.body,
                sent_at=item.sent_at,
                needs_response=item.needs_response,
                category=item.category,
                thread_id=thread_map[item.provider_message_id]
            )
            new_messages.append(message)
            seen_ids.add(item.provider_message_id)

        if new_messages:
            db.add_all(new_messages)
            db.commit()
            logger.info(f"Successfully added {len(new_messages)} new emails to the database.")

        return new_messages

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

        message.thread_id = new_thread_id
        db.commit()

        logger.info(f"Moved message '{provider_message_id}' to thread_id '{new_thread_id}'.")
        return message
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to move message '{provider_message_id}' to thread '{new_thread_id}': {e}", exc_info=True)
        raise


def merge_threads(db: Session, old_thread_id: int, new_thread_id: int) -> list[EmailMessage] | None:
    try:
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