from email.policy import default
import email

def process_email(msg_data) -> tuple[str, dict]:
    email_bytes = None
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            email_bytes = response_part[1]
            break
    if email_bytes is None:
        return "None email_bytes", {}

    raw_msg = email.message_from_bytes(email_bytes, policy=default)

    provider_message_id = str(raw_msg.get("Message-ID", "")).strip("<> ")
    subject = str(raw_msg.get("Subject", ""))

    from_header = raw_msg.get("From")
    if not from_header or not hasattr(from_header, "addresses") or not from_header.addresses:
        return "None from_header", {}
    customer_email = from_header.addresses[0].addr_spec

    date_header = raw_msg.get("Date")
    if not date_header:
        return "None date_header", {}
    else:
        sent_at = date_header.datetime.isoformat()

    body_part = raw_msg.get_body(preferencelist=('plain', 'html'))
    body = body_part.get_content() if body_part else ""

    return "OK", {
        "provider_message_id": provider_message_id,
        "customer_email": customer_email,
        "subject": subject,
        "body": body,
        "sent_at": sent_at
    }

def extract_message_id(msg_data) -> str:
    """
    Extracts the cleaned provider message ID from raw msg_data 
    using the same email-parsing style as process_email.
    """
    email_bytes = None
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            email_bytes = response_part[1]
            break
    if email_bytes is None:
        return ""

    raw_msg = email.message_from_bytes(email_bytes, policy=default)
    provider_message_id = str(raw_msg.get("Message-ID", "")).strip("<> ")
    
    return provider_message_id