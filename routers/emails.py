from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from dependencies import get_db
from schemas import EmailMessageResponse
from services import email_service

router = APIRouter(
    prefix="/api/emails",
    tags=["emails"]
)


@router.get("", response_model=list[EmailMessageResponse])
def list_emails(db: Session = Depends(get_db)):
    try:
        email_messages = email_service.get_emails(db=db)
        return email_messages
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve emails"
        )


@router.post("/all/status", status_code=status.HTTP_204_NO_CONTENT)
def update_all_emails(needs_response: bool, db: Session = Depends(get_db)):
    try:
        email_service.update_all_email_status(db=db, needs_response=needs_response)
        return
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email statuses"
        )


@router.patch("/threads/merge", response_model=list[EmailMessageResponse])
def merge_threads(old_thread_id: int, new_thread_id: int, db: Session = Depends(get_db)):
    try:
        email_messages = email_service.merge_threads(
            db=db,
            old_thread_id=old_thread_id,
            new_thread_id=new_thread_id
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to merge threads"
        )

    if email_messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both threads not found"
        )

    return email_messages


@router.get("/thread-messages", response_model=list[EmailMessageResponse])
def get_thread_messages(thread_id: int, db: Session = Depends(get_db)):
    try:
        email_messages = email_service.get_thread_messages(db=db, thread_id=thread_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve thread messages"
        )

    if email_messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )

    return email_messages


@router.get("/message", response_model=EmailMessageResponse)
def get_message(provider_message_id: str, db: Session = Depends(get_db)):
    try:
        email_message = email_service.get_email(db=db, provider_message_id=provider_message_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve message"
        )

    if email_message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    return email_message


@router.patch("/status", response_model=EmailMessageResponse)
def update_message_status(provider_message_id: str, needs_response: bool, db: Session = Depends(get_db)):
    try:
        email_message = email_service.update_email_status(
            db=db,
            provider_message_id=provider_message_id,
            needs_response=needs_response
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update message status"
        )

    if email_message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    return email_message


@router.patch("/move", response_model=EmailMessageResponse)
def move_message_to_thread(provider_message_id: str, new_thread_id: int, db: Session = Depends(get_db)):
    try:
        email_message = email_service.move_email_to_thread(
            db=db,
            provider_message_id=provider_message_id,
            new_thread_id=new_thread_id
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to move message"
        )

    if email_message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message or thread not found"
        )

    return email_message