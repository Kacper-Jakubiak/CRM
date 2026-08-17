from datetime import date
from util.email_util import process_email, extract_message_id
from integrations.classifier import EmailClassifier, extract_course_details
from dotenv import load_dotenv
import imaplib
import os
from db import EmailMessage, CourseEntry, AppConfig

load_dotenv()

from services import email_service
from services import course_service

IMAP_SERVER = "poczta.agh.edu.pl"
CONFIRMATION_EMAIL = "szkolenia-noreply@informatyka.agh.edu.pl"
IMAP_PORT = 993
IMAP_USER: str = os.getenv("CDSI_EMAIL_USER", "")
IMAP_PASSWORD: str = os.getenv("CDSI_EMAIL_PASSWORD", "")
LAST_PULL_FILE = "last_email_pull.txt"
BATCH_SIZE_LIMIT = 50


def build_classifier(db) -> EmailClassifier | None:
    courses = course_service.get_courses(db)
    course_names = [course.name for course in courses]
    return EmailClassifier(course_names)


def get_search_criteria(db) -> str:
  """Reads the last pull date from db
  """
  config = db.get(AppConfig, "last_email_pull")
  if config and config.value:
    return f"(SINCE {config.value})"
  return "ALL"


def update_last_pull_date(db):
  """Writes today's date to the last_email_pull.txt file."""
  today_str = date.today().strftime("%d-%b-%Y")
    
  config = db.get(AppConfig, "last_email_pull")
  if not config:
    config = AppConfig(key="last_email_pull", value=today_str)
    db.add(config)
  else:
    config.value = today_str
    
  db.commit()


def find_parent(mail: imaplib.IMAP4_SSL, references: list[str]) -> str | None:
    """
    Searches the IMAP Inbox for any ancestor message in the thread 
    by checking the full References header chain.
    """
    if not references:
        return None


    for msg_id in reversed(references):
        status, search_data = mail.search(None, f'(HEADER Message-ID <{msg_id}>)')
        
        if not status == "OK" or not search_data[0]:
            continue
        found_ids = search_data[0].split()
        if not found_ids:
            continue
        parent_e_id = found_ids[0]
        _, msg_data = mail.fetch(parent_e_id, '(BODY.PEEK[HEADER.FIELDS (Message-ID)])')
        
        return extract_message_id(msg_data)

    return None


def fetch_email_ids(mail, db):
    search_criteria = get_search_criteria(db)
    print(f"Using IMAP search criteria: {search_criteria}")

    status, messages = mail.search(None, search_criteria)
    if status != "OK":
        print(f"Error searching emails: {status}")
        return None

    return messages[0].split()


def process_single_email(mail, e_id, email_classifier):
    status, msg_data = mail.fetch(e_id, 'BODY.PEEK[]')
    if status != "OK":
        print(f"Failed to fetch email with ID {e_id.decode()}: {status}")
        return None, None

    status, processed_email, references = process_email(msg_data)
    if status != "OK":
        print(f"Failed to process email with ID {e_id.decode()}: {status}")
        return None, None

    if processed_email["sent_to"].lower() != IMAP_USER.lower():
        print(f"Email with ID {e_id.decode()} was not sent to the expected address. Skipping.")
        print(f"Sent to: {processed_email['sent_to']}, Expected: {IMAP_USER}")
        return None, None

    if processed_email["customer_email"].lower() == CONFIRMATION_EMAIL.lower():
        course_details = extract_course_details(processed_email["body"])
        email_payload = None
        print(f"Extracted course details: {course_details}")
        course_payload = course_details | {"sent_at": processed_email["sent_at"], "customer_name": processed_email["customer_name"]} if course_details else None
    else:
        classifier_email_data = email_classifier.classify_category(processed_email)
        email_payload = processed_email | classifier_email_data | {
            "parent_message_provider_id": find_parent(mail, references)
        }
        print(f"Classified category: {classifier_email_data['category']}, Needs response: {classifier_email_data['needs_response']}")
        course_payload = None

    return email_payload, course_payload


def save_email_batches(db, batch_email_payloads) -> list[EmailMessage]:
    all_ingested = []
    for email_chunk in chunk_list(batch_email_payloads, BATCH_SIZE_LIMIT):
        ingested = email_service.ingest_email_batch(db, email_chunk)
        if ingested:
            all_ingested.extend(ingested)
    return all_ingested


def save_entry_batches(db, batch_course_payloads) -> list[CourseEntry]:
    all_entries = []
    for course_chunk in chunk_list(batch_course_payloads, BATCH_SIZE_LIMIT):
        entries = course_service.add_course_entries_batch(db, course_chunk)
        if entries:
            all_entries.extend(entries)
    return all_entries


def chunk_list(data, size):
    for i in range(0, len(data), size):
        yield data[i:i + size]


def process_new_emails(db):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(IMAP_USER, IMAP_PASSWORD)
    mail.select("INBOX")

    email_ids = fetch_email_ids(mail, db)
    if email_ids is None:
        mail.logout()
        return None

    print(f"Processing {len(email_ids)} matching emails...")

    email_classifier = build_classifier(db)
    if not email_classifier:
        mail.logout()
        return None

    email_payloads = []
    course_payloads = []

    for idx, e_id in enumerate(email_ids):
        print(f"Email {e_id.decode()} ({idx+1}/{len(email_ids)}):")
        email_payload, course_payload = process_single_email(mail, e_id, email_classifier)

        if email_payload:
            email_payloads.append(email_payload)
        if course_payload:
            course_payloads.append(course_payload)

    email_batch_results = save_email_batches(db, email_payloads)
    entry_batch_results = save_entry_batches(db, course_payloads)

    mail.logout()

    update_last_pull_date(db)

    return email_batch_results, entry_batch_results