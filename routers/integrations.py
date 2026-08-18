from fastapi import APIRouter, Depends, HTTPException, status
from services import integration_service, course_service
from dependencies import get_db
from sqlalchemy.orm import Session
from schemas import CourseReply, EmailSendRequest

router = APIRouter(prefix="/api/integrations")


@router.post("/emails/pull", status_code=status.HTTP_201_CREATED)
def pull_emails(db: Session = Depends(get_db)):
    result = integration_service.pull_new_emails(db)
    if result is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    email_batch, entry_batch = result
    return {
      "email_messages": len(email_batch),
      "course_entries": len(entry_batch)
    }


@router.post("/courses/import", status_code=status.HTTP_201_CREATED, response_model=list[CourseReply])
def import_courses(db: Session = Depends(get_db)):
    courses = course_service.import_courses(db)
    return [CourseReply(course_id=c.id, course_name=c.name) for c in courses]


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