from util.email_util import process_email
from integrations.classifier import EmailClassifier, extract_course_details
from dotenv import load_dotenv
import imaplib
import os
import email
from schemas import CourseEntryRequest, EmailIngestItem
from logger import logger

load_dotenv()
IMAP_USER: str = os.getenv("CDSI_EMAIL_USER", "")
IMAP_PASSWORD: str = os.getenv("CDSI_EMAIL_PASSWORD", "")

IMAP_SERVER = "poczta.agh.edu.pl"
CONFIRMATION_EMAIL = "szkolenia-noreply@informatyka.agh.edu.pl"
IMAP_PORT = 993
FETCH_BATCH_SIZE = 50


def build_message_id_index(mail: imaplib.IMAP4_SSL, email_ids: list[str]) -> dict[str, str]:
    if not email_ids:
        return {}

    message_id_index: dict[str, str] = {}

    for i in range(0, len(email_ids), FETCH_BATCH_SIZE):
        chunk = email_ids[i:i + FETCH_BATCH_SIZE]
        sequence_set = ",".join(chunk)

        try:
            status, msg_data = mail.fetch(
                sequence_set,
                "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])"
            )

            if status != "OK":
                continue

            for item in msg_data:
                if not isinstance(item, tuple) or len(item) != 2:
                    continue

                metadata, header_data = item

                try:
                    e_id = metadata.split()[0].decode()
                    message = email.message_from_bytes(header_data)
                    message_id = message.get("Message-ID")

                    if message_id:
                        message_id_index[message_id.strip()] = e_id
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Error building Message-ID index: {e}", exc_info=True)

    logger.info(f"Built Message-ID index with {len(message_id_index)} messages.")
    return message_id_index


def find_parent(references: list[str], message_id_index: dict[str, str]) -> str | None:
    if not references:
        return None

    for msg_id in reversed(references):
        msg_id = msg_id.strip()

        if msg_id in message_id_index:
            logger.debug(f"Found parent message ID '{msg_id}'.")
            return msg_id

    return None


def fetch_email_ids(mail: imaplib.IMAP4_SSL, search_criteria: str) -> list[str] | None:
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
        email_ids = [e_id.decode() for e_id in email_ids]

        logger.info(f"Found {len(email_ids)} email IDs matching search criteria.")
        return email_ids

    except Exception as e:
        logger.error(f"Failed to fetch email IDs: {e}", exc_info=True)
        return None


def fetch_email_messages(
    mail: imaplib.IMAP4_SSL,
    email_ids: list[str]
) -> dict[str, tuple[bytes, bytes]]:
    messages: dict[str, tuple[bytes, bytes]] = {}

    for i in range(0, len(email_ids), FETCH_BATCH_SIZE):
        chunk = email_ids[i:i + FETCH_BATCH_SIZE]
        sequence_set = ",".join(chunk)

        try:
            status, msg_data = mail.fetch(
                sequence_set,
                "(BODY.PEEK[])"
            )

            if status != "OK":
                logger.error(
                    f"Failed to fetch email batch starting at {chunk[0]}."
                )
                continue

            for item in msg_data:
                if not isinstance(item, tuple) or len(item) != 2:
                    continue

                metadata, message_data = item

                if not isinstance(metadata, bytes):
                    continue

                if not isinstance(message_data, bytes):
                    continue

                try:
                    e_id = metadata.split()[0].decode()
                    messages[e_id] = (metadata, message_data)
                except (IndexError, UnicodeDecodeError):
                    continue

        except Exception as e:
            logger.error(f"Failed to fetch email batch: {e}", exc_info=True)

    logger.info(f"Fetched {len(messages)} email messages in bulk.")
    return messages


def process_single_email(
    e_id: str,
    msg_data: tuple[bytes, bytes],
    email_classifier: EmailClassifier
) -> tuple[CourseEntryRequest | None, EmailIngestItem | None]:
    try:
        try:
            processed_email = process_email([msg_data])
        except Exception as err:
            logger.error(f"Failed to process email with ID {e_id}: {err}")
            return None, None

        if processed_email.sent_to.lower() != IMAP_USER.lower():
            logger.info(f"Email with ID {e_id} was not sent to expected address. ")
            return None, None

        email_payload = None
        course_payload = None

        if processed_email.customer_email.lower() == CONFIRMATION_EMAIL.lower():
            logger.debug(f"Processing confirmation email ID {e_id} from '{CONFIRMATION_EMAIL}'.")
            course_details = extract_course_details(processed_email.body)

            if course_details:
                logger.debug(f"Successfully extracted course details for email ID {e_id}.")
                c_name, c_email, c_date = course_details

                course_payload = CourseEntryRequest(
                    customer_email=c_email,
                    course_name=c_name,
                    course_date=c_date,
                    sent_at=processed_email.sent_at,
                    customer_name=processed_email.customer_name,
                    provider_message_id=processed_email.provider_message_id
                )
            else:
                logger.warning(f"Failed to extract course details from confirmation email ID {e_id}.")

        else:
            logger.debug(f"Classifying standard email ID {e_id} from '{processed_email.customer_email}'.")
            category, needs_response = email_classifier.classify_category(processed_email)

            email_payload = EmailIngestItem(
                **processed_email.model_dump(),
                needs_response=needs_response,
                category=category,
            )

            logger.debug(f"{category = }, {needs_response =}")

        return course_payload, email_payload

    except Exception as e:
        logger.error(f"Unexpected error processing email ID {e_id}: {e}", exc_info=True)
        return None, None


def process_new_emails(
    seatch_criteria: str,
    course_names: list[str]
) -> tuple[list[CourseEntryRequest], list[EmailIngestItem]] | None:
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

        if len(email_ids) == 0:
            mail.logout()
            return [], []

        logger.info(f"Processing {len(email_ids)} matching emails...")

        email_messages = fetch_email_messages(mail, email_ids)

        use_ai = (seatch_criteria != "ALL")
        email_classifier = EmailClassifier(course_names, use_ai)

        if not email_classifier:
            logger.error("Failed to initialize EmailClassifier.")
            mail.logout()
            return None

        email_payloads: list[EmailIngestItem] = []
        course_payloads: list[CourseEntryRequest] = []

        for idx, e_id in enumerate(email_ids):
            logger.debug(f"Processing email {e_id} ({idx + 1}/{len(email_ids)})...")

            msg_data = email_messages.get(e_id)

            if not msg_data:
                continue

            course_payload, email_payload = process_single_email(
                e_id,
                msg_data,
                email_classifier
            )

            if email_payload:
                email_payloads.append(email_payload)

            if course_payload:
                course_payloads.append(course_payload)

        logger.info(
            f"Finished processing batch. Collected "
            f"{len(email_payloads)} standard payloads and "
            f"{len(course_payloads)} course payloads."
        )

        mail.logout()
        return course_payloads, email_payloads

    except Exception as e:
        logger.error(f"Critical error during email batch processing: {e}", exc_info=True)

        try:
            mail.logout()
        except Exception:
            pass

        return None


if __name__ == "__main__":
    import cProfile
    import pstats

    profiler = cProfile.Profile()
    profiler.enable()

    try:
        process_new_emails("ALL", [])
    finally:
        profiler.disable()

        stats = pstats.Stats(profiler)
        stats.sort_stats("cumulative")
        stats.print_stats(30)