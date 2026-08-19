from email.policy import default
from email.utils import parseaddr
import email
from schemas import ProcessedEmail
import hashlib

def process_email(msg_data) -> tuple[ProcessedEmail, list[str]]:
    email_bytes = None
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            email_bytes = response_part[1]
            break
    if email_bytes is None:
        raise Exception("None email_bytes")

    raw_msg = email.message_from_bytes(email_bytes, policy=default)

    raw_id = (
        raw_msg.get("Message-ID")
        or raw_msg.get("Resent-Message-ID")
        or raw_msg.get("X-Message-ID")
        or raw_msg.get("X-Google-Message-Id")
    )

    subject = str(raw_msg.get("Subject", ""))

    from_header = raw_msg.get("From")
    if not from_header or not hasattr(from_header, "addresses") or not from_header.addresses:
        raise Exception("None from_header")
    first_address = from_header.addresses[0]
    customer_email = first_address.addr_spec
    customer_name = first_address.display_name

    to_header = raw_msg.get("To")
    if not to_header or not hasattr(to_header, "addresses") or not to_header.addresses:
        raise Exception("None to_header")
    sent_to = to_header.addresses[0].addr_spec

    date_header = raw_msg.get("Date")
    if not date_header:
        raise Exception("None date_header")
    else:
        sent_at = date_header.datetime.isoformat()

    body_part = raw_msg.get_body(preferencelist=('plain', 'html'))
    body = body_part.get_content() if body_part else ""

    references: list[str] = []
    raw_refs = str(raw_msg.get("References", "")).strip()
    if raw_refs:
        references = [ref.strip("<> ") for ref in raw_refs.split() if ref.strip("<> ")]

    provider_message_id = str(raw_id).strip("<> ") if raw_id else ""
    if not provider_message_id:
        fingerprint = f"{customer_email}|{subject}|{sent_at}".encode("utf-8")
        hash_id = hashlib.sha256(fingerprint).hexdigest()[:16]
        provider_message_id = f"gen-{hash_id}"

    email_instance = ProcessedEmail(
        provider_message_id=provider_message_id,
        customer_email=customer_email,
        sent_to=sent_to,
        subject=subject,
        body=body,
        sent_at=sent_at,
        customer_name=customer_name
    )

    return email_instance, references


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


def extract_domain(email_address: str) -> str:
    name, clean_email = parseaddr(email_address)
    domain = clean_email.split("@")[-1]

    return domain