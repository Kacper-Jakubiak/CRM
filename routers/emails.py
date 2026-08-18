from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies import get_db
from schemas import EmailIngestRequest, EmailBatchIngestRequest, EmailMessageReply
from services import email_service

router = APIRouter(
    prefix="/api/emails",
    tags=["emails"]
)


@router.get("", response_model=list[EmailMessageReply])
def list_emails(db: Session = Depends(get_db)):
    email_messages = email_service.get_emails(db)
    return email_messages


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

    if email_message is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Message {payload.provider_message_id} already exists"
        )

    return email_message


@router.post("/batch", status_code=status.HTTP_201_CREATED, response_model=list[EmailMessageReply])
def batch_ingest_emails(payload: EmailBatchIngestRequest, db: Session = Depends(get_db)):
    email_messages = email_service.ingest_email_batch(db, [message.model_dump() for message in payload.messages])

    if email_messages is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email messages not found")

    return email_messages


@router.post("/all/status")
def update_all_emails(needs_response: bool, db: Session = Depends(get_db)):
    email_service.update_all_email_status(db, needs_response)
    return


@router.patch("/threads/merge", response_model=list[EmailMessageReply])
def merge_threads(old_thread_id: int, new_thread_id: int, db: Session = Depends(get_db)):
    email_messages = email_service.merge_threads(
        db=db,
        old_thread_id=old_thread_id,
        new_thread_id=new_thread_id
    )

    if email_messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both threads not found"
        )

    return email_messages


@router.get("/thread-messages", response_model=list[EmailMessageReply])
def get_thread_messages(thread_id: int, db: Session = Depends(get_db)):
    email_messages = email_service.get_thread_messages(db, thread_id)

    if email_messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )

    return email_messages


@router.get("/message", response_model=EmailMessageReply)
def get_message(provider_message_id: str, db: Session = Depends(get_db)):
    email_message = email_service.get_email(db, provider_message_id)

    if email_message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    return email_message


@router.patch("/status", response_model=EmailMessageReply)
def update_message_status(provider_message_id: str, needs_response: bool, db: Session = Depends(get_db)):
    email_message = email_service.update_email_status(
        db=db,
        provider_message_id=provider_message_id,
        needs_response=needs_response
    )

    if email_message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    return email_message


@router.patch("/move", response_model=EmailMessageReply)
def move_message_to_thread(provider_message_id: str, new_thread_id: int, db: Session = Depends(get_db)):
    email_message = email_service.move_email_to_thread(
        db=db,
        provider_message_id=provider_message_id,
        new_thread_id=new_thread_id
    )

    if email_message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message or thread not found"
        )

    return email_message