import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
from jinja2 import Template  # <-- Added Jinja2 import

load_dotenv()

SMTP_SERVER = "poczta.agh.edu.pl"
SMTP_PORT = 465
SENDER_EMAIL: str = os.getenv("CDSI_EMAIL_USER", "")
SENDER_PASSWORD: str = os.getenv("CDSI_EMAIL_PASSWORD", "")

# Define a clean, basic HTML template using Jinja2 syntax
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f6f6f6; margin: 0; padding: 20px; }
        .container { background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); max-width: 600px; margin: auto; }
        .content { font-size: 16px; color: #333333; line-height: 1.6; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #eeeeee; font-size: 12px; color: #999999; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <!-- The replace filter converts plain text newlines to HTML line breaks -->
            {{ message_body | replace('\n', '<br>') }}
        </div>
        <div class="footer">
            <p>Sent via Automated System</p>
        </div>
    </div>
</body>
</html>
"""

def send_email(
    recipient_email: str,
    subject: str,
    body: str,
    reply_message_id: str | None,
    add_html: bool
) -> str:
    """Sends an email using SMTP with SSL, supporting optional reply threading and HTML."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email

    if reply_message_id:
        msg["In-Reply-To"] = reply_message_id
        msg["References"] = reply_message_id

    # IMPORTANT: Attach the plain text part FIRST for 'alternative' payloads.
    # Email clients will render the LAST part they understand (HTML).
    msg.attach(MIMEText(body, "plain"))

    if add_html:
        # Render the template with the provided body text
        template = Template(HTML_TEMPLATE)
        html_content = template.render(message_body=body)
        
        # Attach the rendered HTML part SECOND
        msg.attach(MIMEText(html_content, "html"))

    # print(msg.as_string())

    # return "NOT"
    try:
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