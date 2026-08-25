from email.policy import default
from email.utils import parseaddr
import email
from schemas import ProcessedEmail, EmailIngestItem
from db import EmailMessage
from pydantic import EmailStr
import hashlib
from uuid import uuid4, UUID

def process_email(msg_data) -> ProcessedEmail:
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
        customer_name=customer_name,
        references=references
    )

    return email_instance


def extract_domain(email_address: EmailStr) -> str:
    name, clean_email = parseaddr(email_address)
    domain = clean_email.split("@")[-1]

    return domain


def map_emails(email_requests: list[EmailIngestItem], email_messages: list[EmailMessage]) -> dict[str, UUID]:
    thread_map: dict[str, UUID] = {email.provider_message_id: email.thread_id for email in email_messages}

    for item in email_requests:
        for ref in reversed(item.references):
            if ref not in thread_map:
                continue
            thread_map[item.provider_message_id] = thread_map[ref]
            break
        if item.provider_message_id not in thread_map:
            thread_map[item.provider_message_id] = uuid4()

    return thread_map