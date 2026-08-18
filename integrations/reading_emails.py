from datetime import date
from util.email_util import process_email, extract_message_id
from integrations.classifier import EmailClassifier, extract_course_details
from dotenv import load_dotenv
import imaplib
import os
from logger import logger

load_dotenv()
IMAP_USER: str = os.getenv("CDSI_EMAIL_USER", "")
IMAP_PASSWORD: str = os.getenv("CDSI_EMAIL_PASSWORD", "")

IMAP_SERVER = "poczta.agh.edu.pl"
CONFIRMATION_EMAIL = "szkolenia-noreply@informatyka.agh.edu.pl"
IMAP_PORT = 993

def find_parent(mail: imaplib.IMAP4_SSL, references: list[str]) -> str | None:
    """
    Searches the IMAP Inbox for any ancestor message in the thread 
    by checking the full References header chain.
    """
    if not references:
        return None

    for msg_id in reversed(references):
        try:
            status, search_data = mail.search(None, f'(HEADER Message-ID <{msg_id}>)')
            
            if status != "OK" or not search_data or not search_data[0]:
                continue
                
            found_ids = search_data[0].split()
            if not found_ids:
                continue
                
            parent_e_id = found_ids[0]
            _, msg_data = mail.fetch(parent_e_id, '(BODY.PEEK[HEADER.FIELDS (Message-ID)])')
            
            parent_id = extract_message_id(msg_data)
            if parent_id:
                logger.debug(f"Found parent message ID '{parent_id}' for reference '{msg_id}'.")
                return parent_id
        except Exception as e:
            logger.error(f"Error while searching for parent message with reference '{msg_id}': {e}", exc_info=True)
            continue

    return None


def fetch_email_ids(mail, search_criteria):
    logger.info(f"Using IMAP search criteria: {search_criteria}")

    try:
        status, messages = mail.search(None, search_criteria)
        if status != "OK":
            logger.error(f"Error searching emails: status {status}")
            return None

        if not messages or not messages[0]:
            logger.info("No matching emails found.")
            return []

        email_ids = messages[0].split()
        logger.info(f"Found {len(email_ids)} email IDs matching search criteria.")
        return email_ids
    except Exception as e:
        logger.error(f"Failed to fetch email IDs: {e}", exc_info=True)
        return None


def process_single_email(mail, e_id, email_classifier) -> tuple[dict | None, dict | None]:
    e_id_str = e_id.decode()
    try:
        status, msg_data = mail.fetch(e_id, 'BODY.PEEK[]')
        if status != "OK":
            logger.error(f"Failed to fetch email with ID {e_id_str}: status {status}")
            return None, None

        status, processed_email, references = process_email(msg_data)
        if status != "OK":
            logger.error(f"Failed to process email with ID {e_id_str}: status {status}")
            return None, None

        if processed_email["sent_to"].lower() != IMAP_USER.lower():
            logger.debug(f"Email with ID {e_id_str} was not sent to expected address. ")
            return None, None

        if processed_email["customer_email"].lower() == CONFIRMATION_EMAIL.lower():
            logger.debug(f"Processing confirmation email ID {e_id_str} from '{CONFIRMATION_EMAIL}'.")
            course_details = extract_course_details(processed_email["body"])
            email_payload = None
            
            if course_details:
                logger.debug(f"Successfully extracted course details for email ID {e_id_str}.")
                course_payload = course_details | {
                    "sent_at": processed_email["sent_at"],
                    "customer_name": processed_email["customer_name"]
                }
            else:
                logger.warning(f"Failed to extract course details from confirmation email ID {e_id_str}.")
                course_payload = None
        else:
            logger.debug(f"Classifying standard email ID {e_id_str} from '{processed_email['customer_email']}'.")
            category, needs_response = email_classifier.classify_category(processed_email)
            parent_id = find_parent(mail, references)
            
            email_payload = processed_email | {"category": category, "needs_respnonse": needs_response} | {
                "parent_message_provider_id": parent_id
            }
            logger.debug(
                f"{category = }, {needs_response =}"
            )
            course_payload = None

        return email_payload, course_payload
    except Exception as e:
        logger.error(f"Unexpected error processing email ID {e_id_str}: {e}", exc_info=True)
        return None, None


def process_new_emails(seatch_criteria, course_names) -> tuple[list, list] | None:
    logger.info("Connecting to IMAP server for processing new emails...")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("INBOX")
    except Exception as e:
        logger.error(f"Failed to connect or log in to IMAP server: {e}", exc_info=True)
        return None

    try:
        email_ids = fetch_email_ids(mail, seatch_criteria)
        if email_ids is None:
            mail.logout()
            return None

        if not email_ids:
            mail.logout()
            return [], []

        logger.info(f"Processing {len(email_ids)} matching emails...")

        email_classifier = EmailClassifier(course_names)
        if not email_classifier:
            logger.error("Failed to initialize EmailClassifier.")
            mail.logout()
            return None

        email_payloads = []
        course_payloads = []

        for idx, e_id in enumerate(email_ids):
            logger.debug(f"Processing email {e_id.decode()} ({idx+1}/{len(email_ids)})...")
            email_payload, course_payload = process_single_email(mail, e_id, email_classifier)

            if email_payload:
                email_payloads.append(email_payload)
            if course_payload:
                course_payloads.append(course_payload)

        logger.info(f"Finished processing batch. Collected {len(email_payloads)} standard payloads and {len(course_payloads)} course payloads.")
        mail.logout()
        return email_payloads, course_payloads
    
    except Exception as e:
        logger.error(f"Critical error during email batch processing: {e}", exc_info=True)
        try:
            mail.logout()
        except Exception:
            pass
        return None