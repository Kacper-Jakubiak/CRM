from fastapi import APIRouter, Depends, HTTPException, status
from services import integration_service
from dependencies import get_db
from sqlalchemy.orm import Session

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