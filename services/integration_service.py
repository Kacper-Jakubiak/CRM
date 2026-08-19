from integrations.reading_emails import process_new_emails
from integrations.sending_emails import send_email
from services import course_service
from db import AppConfig
from logger import logger
from datetime import date
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
        last_pull_config = db.get(AppConfig, "last_email_pull")
        if last_pull_config and last_pull_config.value:
            criteria = f"(SINCE {last_pull_config.value})"
        else:
            logger.warning("No previous email pull timestamp found. Fetching ALL emails.")
            criteria = "ALL"

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

        
        db.commit()
        logger.info(f"Successfully pulled and ingested {total_ingested_emails} emails and {total_ingested_courses} course entries.")
        _update_last_pull_date(db)

        return total_ingested_emails, total_ingested_courses

    except (SQLAlchemyError, RuntimeError) as e:
        db.rollback()
        logger.error(f"Error during email pull and ingestion workflow: {e}", exc_info=True)
        raise



def _update_last_pull_date(db):
    today_str = date.today().strftime("%d-%b-%Y")
      
    config = db.get(AppConfig, "last_email_pull")
    if not config:
      config = AppConfig(key="last_email_pull", value=today_str)
      db.add(config)
    else:
      config.value = today_str
      
    db.commit()
    logger.info(f"Saved last_pull_date as {today_str}")
    return
