from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies import get_db
from services import customer_service

router = APIRouter(
    prefix="/api/customers",
    tags=["customers"]
)


@router.get("")
def get_customers(db: Session = Depends(get_db)):
    customers = customer_service.get_customers(db)

    return {
        "customers": [{
                "customer_id": customer.id,
                "customer_email": customer.email
            }
            for customer in customers
        ]
    }


@router.get("/{email_address}/entries")
def get_customer_entries(email_address: str, db: Session = Depends(get_db)):
    entries = customer_service.get_customer_entries(db, email_address)

    if not entries:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    return {
        "course_entries": [{
            "entry_id": e.id,
            "course_id": e.course_id,
            "customer_id": e.customer_id
        } for e in entries]
    }



@router.get("/{email_address}/emails")
def get_customer_messages(email_address: str, db: Session = Depends(get_db)):
    # print(email_address)
    email_messages = customer_service.get_customer_messages(db, email_address)

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