from datetime import datetime

from sqlalchemy.orm import Session

from db import EmailMessage, Thread
from schemas import EmailMessageReply
from util.schema_translations import to_email_message_reply
from services.customer_service import add_customer


def get_emails(db: Session) -> list[EmailMessageReply]:
    return [to_email_message_reply(message) for message in db.query(EmailMessage).all()]


def get_thread_messages(db: Session, thread_id: int) -> list[EmailMessageReply] | None:
    thread = db.query(Thread).filter_by(id=thread_id).first()
    if not thread:
        return None
    
    return [to_email_message_reply(message) for message in db.query(EmailMessage).filter_by(thread_id=thread_id).all()]


def ingest_email(
    db: Session,
    provider_message_id: str,
    customer_email: str,
    category: str,
    needs_response: bool,
    subject: str,
    body: str,
    sent_at: str,
    parent_message_provider_id: str | None = None
) -> EmailMessageReply | None:
    existing_message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()

    if existing_message:
        return None

    thread_id = None

    if parent_message_provider_id:
        parent = db.query(EmailMessage).filter_by(provider_message_id=parent_message_provider_id).first()
        if parent:
            thread_id = parent.thread_id

    if thread_id is None:
        thread = Thread()
        db.add(thread)
        db.flush()
        thread_id = thread.id

    customer = add_customer(db, "", customer_email)

    message = EmailMessage(
        customer_id=customer.id,
        provider_message_id=provider_message_id,
        sender=customer_email,
        subject=subject,
        body=body,
        sent_at=datetime.fromisoformat(sent_at),
        needs_response=needs_response,
        category=category,
        thread_id=thread_id
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return to_email_message_reply(message)


def ingest_email_batch(db: Session, emails: list[dict[str, str]]) -> list[EmailMessageReply]:
    """
    entries should be a list of dictionaries:
    {
        provider_message_id: str,
        customer_email: str,
        category: str,
        needs_response: bool,
        subject: str,
        body: str,
        sent_at: str,
        parent_message_provider_id: str | None
        customer_name: str
    }
    """
    ingested_messages = []
    
    customer_cache = {}

    for email_data in emails:
        provider_message_id = email_data["provider_message_id"]
        
        existing_message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()

        if existing_message:
            continue

        customer_email = email_data["customer_email"]
        parent_message_provider_id = email_data["parent_message_provider_id"]
        
        thread_id = None
        if parent_message_provider_id:
            parent = db.query(EmailMessage).filter_by(provider_message_id=parent_message_provider_id).first()
            if parent:
                thread_id = parent.thread_id

        if thread_id is None:
            thread = Thread()
            db.add(thread)
            db.flush()
            thread_id = thread.id

        if customer_email in customer_cache:
            customer_id = customer_cache[customer_email]
        else:
            customer = add_customer(db, email_data["customer_name"], customer_email)
            customer_id = customer.id
            customer_cache[customer_email] = customer_id

        message = EmailMessage(
            customer_id=customer_id,
            provider_message_id=provider_message_id,
            sender=customer_email,
            subject=email_data["subject"],
            body=email_data["body"],
            sent_at=datetime.fromisoformat(email_data["sent_at"]),
            needs_response=email_data["needs_response"],
            category=email_data["category"],
            thread_id=thread_id
        )

        db.add(message)
        ingested_messages.append(message)

    db.commit()

    for message in ingested_messages:
        db.refresh(message)

    return [to_email_message_reply(message) for message in ingested_messages]


def update_email_status(db: Session, provider_message_id: str, needs_response: bool) -> EmailMessageReply | None:
    message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()

    if not message:
        return None

    message.needs_response = needs_response
    db.commit()
    db.refresh(message)

    return to_email_message_reply(message)


def update_all_email_status(db: Session, needs_response: bool) -> None:
    db.query(EmailMessage).update({EmailMessage.needs_response: needs_response}, synchronize_session=False)
    db.commit()


def get_email(db: Session, provider_message_id: str) -> EmailMessageReply | None:
    message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()
    if message is None:
        return None
    return to_email_message_reply(message)


def move_email_to_thread(db: Session, provider_message_id: str, new_thread_id: int) -> EmailMessageReply | None:
    message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()

    if not message:
        return None

    thread = db.query(Thread).filter_by(id=new_thread_id).first()

    if not thread:
        return None


    message.thread_id = new_thread_id

    db.commit()

    return to_email_message_reply(message)


def merge_threads(db: Session, old_thread_id: int, new_thread_id: int) -> list[EmailMessageReply] | None:
    old_thread = db.query(Thread).filter_by(id=old_thread_id).first()

    if not old_thread:
        return None

    new_thread = db.query(Thread).filter_by(id=new_thread_id).first()

    if not new_thread:
        return None
    
    moved_count = db.query(EmailMessage).filter_by(thread_id=old_thread_id).update({
        EmailMessage.thread_id: new_thread_id
    },
    synchronize_session=False
    )
    
    messages = db.query(EmailMessage).filter_by(thread_id=new_thread_id).all()

    db.commit()

    return [to_email_message_reply(message) for message in messages]