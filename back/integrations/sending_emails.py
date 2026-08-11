import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = "poczta.agh.edu.pl"
SMTP_PORT = 465
SENDER_EMAIL = os.getenv("CDSI_EMAIL_USER")
SENDER_PASSWORD = os.getenv("CDSI_EMAIL_PASSWORD")


def send_email(
    recipient_email: str,
    subject: str,
    body: str,
    reply_message_id: Optional[str] = None
) -> str:
    """Sends a plain text email using SMTP with SSL, supporting optional reply threading."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email

    if reply_message_id:
        msg["In-Reply-To"] = reply_message_id
        msg["References"] = reply_message_id

    msg.attach(MIMEText(body, "plain"))

    # print(msg.as_string())
    # return "OK"

    try:
        # print(f"Connecting to SMTP server {SMTP_SERVER}:{SMTP_PORT}...")
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
            print(f"Successfully sent email to {recipient_email}")
            return "OK"
            
    except Exception as e:
        error_string = f"Failed to send email. Error: {e}"
        print(error_string)
        return error_string


if __name__ == "__main__":
    RECIPIENT = "recipient@example.com"
    
    EMAIL_SUBJECT = "Exampe subject"
    EMAIL_BODY = """
Hello,

This is an example mail body.
"""
    ORIGINAL_MESSAGE_ID = None

    send_email(
        recipient_email=RECIPIENT,
        subject=EMAIL_SUBJECT,
        body=EMAIL_BODY,
        message_id=ORIGINAL_MESSAGE_ID
    )