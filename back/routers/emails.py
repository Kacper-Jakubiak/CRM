from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies import get_db
from schemas import EmailIngestRequest, EmailBatchIngestRequest
from services import email_service

router = APIRouter(
    prefix="/api/emails",
    tags=["emails"]
)


@router.post("", status_code=status.HTTP_201_CREATED)
def ingest_email(payload: EmailIngestRequest, db: Session = Depends(get_db)):
    email_message = email_service.ingest_email(
        db=db,
        provider_message_id=payload.provider_message_id,
        customer_email=payload.customer_email,
        category=payload.category,
        needs_response=payload.needs_response,
        subject=payload.subject,
        body=payload.body,
        sent_at=payload.sent_at,
        parent_message_provider_id=payload.parent_message_provider_id
    )

    if not email_message:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Message {payload.provider_message_id} already exists")

    return {
            "id": email_message.id,
            "customer_id": email_message.customer_id,
            "provider_message_id": email_message.provider_message_id,
            "sender": email_message.sender,
            "subject": email_message.subject,
            "body": email_message.body,
            "sent_at": email_message.sent_at.isoformat(),
            "needs_response": email_message.needs_response,
            "category": email_message.category,
            "thread_id": email_message.thread_id
        }



@router.post("/batch", status_code=status.HTTP_201_CREATED)
def batch_ingest_emails(payload: EmailBatchIngestRequest, db: Session = Depends(get_db)):
    email_messages =  email_service.ingest_email_batch(db, payload.messages)

    if not email_messages:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    return {
        "email_messages": [{
            "id": em.id,
            "customer_id": em.customer_id,
            "provider_message_id": em.provider_message_id,
            "sender": em.sender,
            "subject": em.subject,
            "body": em.body,
            "sent_at": em.sent_at.isoformat(),
            "needs_response": em.needs_response,
            "category": em.category,
            "thread_id": em.thread_id
        } for em in email_messages]
    }


@router.patch("/{provider_message_id}/status")
def update_message_status(provider_message_id: str, needs_response: bool, db: Session = Depends(get_db)):
    email_message = email_service.update_email_status(
        db=db,
        provider_message_id=provider_message_id,
        needs_response=needs_response
    )

    if not email_message:
        raise HTTPException(
            status_code=404,
            detail="Message not found"
        )

    return {
            "id": email_message.id,
            "customer_id": email_message.customer_id,
            "provider_message_id": email_message.provider_message_id,
            "sender": email_message.sender,
            "subject": email_message.subject,
            "body": email_message.body,
            "sent_at": email_message.sent_at.isoformat(),
            "needs_response": email_message.needs_response,
            "category": email_message.category,
            "thread_id": email_message.thread_id
        }


@router.get("/{provider_message_id}")
def get_message(provider_message_id: str, db: Session = Depends(get_db)):
    email_message = email_service.get_email(db, provider_message_id )

    if not email_message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    return {
            "id": email_message.id,
            "customer_id": email_message.customer_id,
            "provider_message_id": email_message.provider_message_id,
            "sender": email_message.sender,
            "subject": email_message.subject,
            "body": email_message.body,
            "sent_at": email_message.sent_at.isoformat(),
            "needs_response": email_message.needs_response,
            "category": email_message.category,
            "thread_id": email_message.thread_id
        }


@router.patch("/{provider_message_id}/move")
def move_message_to_thread(
    provider_message_id: str,
    new_thread_id: int,
    db: Session = Depends(get_db)
):
    result = email_service.move_email_to_thread(
        db=db,
        provider_message_id=provider_message_id,
        new_thread_id=new_thread_id
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Message or thread not found"
        )

    return {
        "detail": (
            f"Successfully merged thread "
            f"{result['old_thread_id']} "
            f"({result['moved_count']} messages) "
            f"into thread {result['new_thread_id']}."
        )
    }