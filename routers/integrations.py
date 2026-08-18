from fastapi import APIRouter, Depends, HTTPException, status
from services import integration_service, course_service
from dependencies import get_db
from sqlalchemy.orm import Session
from schemas import CourseResponse, EmailSendRequest
from integrations.course_fetcher import fetch_course_names
from sqlalchemy.exc import SQLAlchemyError
from logger import logger

router = APIRouter(prefix="/api/integrations")


@router.post("/emails/pull", status_code=status.HTTP_201_CREATED)
def pull_emails(db: Session = Depends(get_db)):
    try:
      email_count, entry_count = integration_service.pull_new_emails(db)
    except SQLAlchemyError as e:
        logger.error(f"Database error during email pull: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pull new emails due to a database error"
        )
    except Exception as e:
        logger.error(f"Unexpected error during email pull: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pull new emails"
        )
    return {
        "email_messages": email_count,
        "course_entries": entry_count
    }


@router.post("/courses/import", status_code=status.HTTP_201_CREATED, response_model=list[CourseResponse])
def import_courses(db: Session = Depends(get_db)):
    course_names = fetch_course_names()
    if course_names is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error while fetching course names"
        )
    
    try:
        new_courses = course_service.add_courses(db, course_names)
    except:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while saving courses."
        )

    return new_courses


@router.post("/send", response_model=str)
def send(payload: EmailSendRequest):
    send_status = integration_service.send_customer_email(
        recipient_email=payload.recipient_email,
        subject=payload.subject,
        body=payload.body,
        reply_message_id=payload.reply_message_id,
        add_html=payload.should_add_html
        )
    
    if send_status != "OK":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=status)
    return send_status