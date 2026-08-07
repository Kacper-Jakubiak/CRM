from fastapi import APIRouter, Depends, HTTPException, status
from services import integration_service
from dependencies import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/integrations")

@router.post("/emails/pull")
def pull_emails(db: Session = Depends(get_db)):
    result = integration_service.pull_new_emails(db)
    if not result:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    email_batch, entry_batch = result
    return {
        "email_batch": [{
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
        } for em in email_batch],
        
        "entry_batch": [{
                "entry_id": e.id,
                "course_id": e.course_id,
                "customer_id": e.customer_id
        } for e in entry_batch]
    }