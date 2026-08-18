from integrations.reading_emails import process_new_emails
from integrations.sending_emails import send_email


def send_customer_email(recipient_email: str, subject: str, body: str, reply_message_id: str | None, add_html: bool) -> str:
    status = send_email(recipient_email=recipient_email, subject=subject, body=body, reply_message_id=reply_message_id, add_html=add_html)

    return status


def pull_new_emails(db):
    return process_new_emails(db)