from datetime import date
from email_parser import *
from classifier import EmailClassifier, extract_course_details
from dotenv import load_dotenv
import imaplib
import os
import requests

load_dotenv()

POST_EMAIL_API_URL = "http://127.0.0.1:8000/api/emails/ingest"
POST_COURSEENTRY_API_URL = "http://127.0.0.1:8000/api/course-entries"
GET_COURSES_API_URL = "http://127.0.0.1:8000/api/courses"
IMAP_SERVER = "poczta.agh.edu.pl"
CONFIRMATION_EMAIL = "szkolenia-noreply@informatyka.agh.edu.pl"
IMAP_PORT = 993
IMAP_USER: str = os.getenv("CDSI_EMAIL_USER", "")
IMAP_PASSWORD: str = os.getenv("CDSI_EMAIL_PASSWORD", "")
LAST_PULL_FILE = "last_email_pull.txt"


def build_classifier() -> EmailClassifier | None:
    response = requests.get(GET_COURSES_API_URL)
    if response.status_code != 200:
        print(f"Status: {response.status_code} | Response: {response.json()}")
        return None
    data = response.json()
    course_names = [course["course_name"] for course in data.get("courses", [])]
    return EmailClassifier(course_names)


def get_search_criteria() -> str:
  """Reads the last pull date from file or defaults to fetching all emails

  if the file is missing or empty.
  """
  if os.path.exists(LAST_PULL_FILE):
    with open(LAST_PULL_FILE, "r") as f:
      last_date = f.read().strip()
      if last_date:
        return f"(SINCE {last_date})"

  return "ALL"


def update_last_pull_date():
  """Writes today's date to the last_email_pull.txt file."""
  today_str = date.today().strftime("%d-%b-%Y")
  with open(LAST_PULL_FILE, "w") as f:
    f.write(today_str)


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

def process_emails():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(IMAP_USER, IMAP_PASSWORD)
    mail.select("INBOX")

    search_criteria = get_search_criteria()
    print(f"Using IMAP search criteria: {search_criteria}")

    status, messages = mail.search(None, search_criteria)

    if status != "OK":
        print(f"Error searching emails: {status}")
        mail.logout()
        return

    email_ids = messages[0].split()[-50:]
    print(f"Processing {len(email_ids)} new emails...")

    email_classifier = build_classifier()
    if not email_classifier:
        mail.logout()
        return

    for e_id in email_ids:
        status, msg_data = mail.fetch(e_id, 'BODY.PEEK[]')
        if status != "OK":
            print(f"Failed to fetch email with ID {e_id.decode()}: {status}")
            continue

        status, processed_email, references = process_email(msg_data)

        if status != "OK":
            print(f"Failed to process email with ID {e_id.decode()}: {status}")
            continue

        if processed_email["sent_to"].lower() != IMAP_USER.lower():
            print(f"Email with ID {e_id.decode()} was not sent to the expected address. Skipping.")
            print(f"Sent to: {processed_email['sent_to']}, Expected: {IMAP_USER}")
            print()
            continue

        if processed_email["customer_email"].lower() == CONFIRMATION_EMAIL.lower():
           course_details = extract_course_details(processed_email["body"])
           classifier_email_data = None
           course_data = course_details
        else:
            classifier_email_data = email_classifier.classify_category(processed_email)
            course_data = None

        # for key, value in processed_email.items():
        #     if key == "body":
        #         continue
        #     print(f"{key}: {value}")
        
        # for key, value in classifier_email_data.items():
        #     print(f"{key}: {value}")

        # if classifier_course_data is not None:
        #     for key, value in classifier_course_data.items():
        #         print(f"{key}: {value}")
        if classifier_email_data is not None:
            payload = processed_email | classifier_email_data | {"parent_message_provider_id": find_parent(mail, references)}
            response = requests.post(POST_EMAIL_API_URL, json=payload)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")

        if course_data is not None:
            payload = course_data | {"sent_at": processed_email["sent_at"]}
            print(f"Posting course entry data: {payload}")
            response = requests.post(POST_COURSEENTRY_API_URL, json=payload)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
        
        print()

    # update_last_pull_date()
    mail.logout()


if __name__ == "__main__":
    process_emails()