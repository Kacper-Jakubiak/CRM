from fastapi import APIRouter, Depends, HTTPException, status
from services import integration_service
from dependencies import get_db
from sqlalchemy.orm import Session
from schemas import PullEmailsReply

router = APIRouter(prefix="/api/integrations")

@router.post("/emails/pull", response_model=PullEmailsReply)
def pull_emails(db: Session = Depends(get_db)):
    result = integration_service.pull_new_emails(db)
    if result is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    email_batch, entry_batch = result
    return PullEmailsReply(
        email_batch=email_batch,
        entry_batch=entry_batch
    )