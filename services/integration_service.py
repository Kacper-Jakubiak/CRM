from integrations.reading_emails import process_new_emails
from integrations.sending_emails import send_email
from services import course_service
from logger import logger
from datetime import datetime
from util.general import chunk_list
from services import email_service, course_service
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

BATCH_SIZE_LIMIT = 50


def send_customer_email(recipient_email: str, subject: str, body: str, reply_message_id: str | None, add_html: bool) -> bool:
    status = send_email(recipient_email=recipient_email, subject=subject, body=body, reply_message_id=reply_message_id, add_html=add_html)

    return status


def pull_new_emails(db: Session) -> tuple[int, int]:
    """
    Pulls new emails from the IMAP server using the last pull date as criteria,
    ingests email batches and course entry batches, and updates the last pull timestamp.
    
    Returns a tuple of (ingested_emails_count, ingested_courses_count).
    """
    try:
        target_date = _get_search_date(db)
        if target_date is None:
            logger.warning("No previous pull timestamps found. Fetching ALL emails.")
            criteria = "ALL"
        else:
            since_date = target_date.strftime("%d-%b-%Y")
            criteria = f'(SINCE "{since_date}")'

        courses = course_service.get_all_courses(db)
        names = [c.name for c in courses]
             
        result = process_new_emails(criteria, names)
        if result is None:
            logger.error("Failed to process new emails from IMAP.")
            raise RuntimeError("Email fetching and processing failed.")
            
        course_payloads, email_payloads = result

        total_ingested_emails = 0
        for email_chunk in chunk_list(email_payloads, BATCH_SIZE_LIMIT):
            ingested = email_service.ingest_email_batch(db, email_chunk)
            total_ingested_emails += len(ingested)
            
        total_ingested_courses = 0
        for course_chunk in chunk_list(course_payloads, BATCH_SIZE_LIMIT):
            entries = course_service.add_course_entries_batch(db, course_chunk)
            total_ingested_courses += len(entries)

        logger.info(f"Successfully pulled and ingested {total_ingested_emails} emails and {total_ingested_courses} course entries.")

        return total_ingested_emails, total_ingested_courses

    except (SQLAlchemyError, RuntimeError) as e:
        db.rollback()
        logger.error(f"Error during email pull and ingestion workflow: {e}", exc_info=True)
        raise


def _get_search_date(db: Session) -> datetime | None:
    newest_message = email_service.get_newest_email(db)
    newest_entry = course_service.get_newest_entry(db)

    valid_dates = []
    if newest_message:
        valid_dates.append(newest_message.sent_at)
        
    if newest_entry:
        valid_dates.append(newest_entry.sent_at)

    if len(valid_dates) == 0:
        return None

    return max(valid_dates)