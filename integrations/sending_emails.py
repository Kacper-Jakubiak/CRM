import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
from jinja2 import Template, Environment, FileSystemLoader
from logger import logger

load_dotenv()
SENDER_EMAIL: str = os.getenv("CDSI_EMAIL_USER", "")
SENDER_PASSWORD: str = os.getenv("CDSI_EMAIL_PASSWORD", "")

SMTP_SERVER = "poczta.agh.edu.pl"
SMTP_PORT = 465
jinja_env = Environment(loader=FileSystemLoader('integrations/'))
template = jinja_env.get_template('email_template.html')

def send_email(
    recipient_email: str,
    subject: str,
    body: str,
    reply_message_id: str | None,
    add_html: bool
) -> bool:
    """Sends an email using SMTP with SSL, supporting optional reply threading and HTML."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email

    if reply_message_id:
        msg["In-Reply-To"] = reply_message_id
        msg["References"] = reply_message_id

    msg.attach(MIMEText(body, "plain"))

    if add_html:
        output_html = template.render(message_body=body)
        msg.attach(MIMEText(output_html, "html"))

    try:
        logger.info(f"Connecting to SMTP server {SMTP_SERVER}:{SMTP_PORT}...")
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
            logger.info(f"Successfully sent email to {recipient_email}")
            return True
            
    except Exception as e:
        error_string = f"Failed to send email to {recipient_email}. Error: {e}"
        logger.error(error_string)
        return False


if __name__ == "__main__":
    RECIPIENT = "recipient@example.com"
    
    EMAIL_SUBJECT = "Example subject"
    EMAIL_BODY = """Hello,

This is an example mail body.

Best regards,
Python Script"""
    
    ORIGINAL_MESSAGE_ID = None

    send_email(
        recipient_email=RECIPIENT,
        subject=EMAIL_SUBJECT,
        body=EMAIL_BODY,
        reply_message_id=ORIGINAL_MESSAGE_ID,
        add_html=True
    )