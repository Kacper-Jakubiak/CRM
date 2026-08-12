from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies import get_db
from services import customer_service
from schemas import CustomerReply, CourseEntryReply, EmailMessageReply

router = APIRouter(
    prefix="/api/customers",
    tags=["customers"]
)


@router.get("", response_model=list[CustomerReply])
def get_customers(db: Session = Depends(get_db)):
    customers = customer_service.get_customers(db)
    return [
        CustomerReply(
            customer_id=customer.id,
            customer_email=customer.email,
            customer_note=customer.note,
            company_id=customer.company_id
        )
        for customer in customers]


@router.get("/{email_address}/entries", response_model=list[CourseEntryReply])
def get_customer_entries(email_address: str, db: Session = Depends(get_db)):
    entries = customer_service.get_customer_entries(db, email_address)

    if entries is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    return entries



@router.get("/{email_address}/emails", response_model=list[EmailMessageReply])
def get_customer_messages(email_address: str, db: Session = Depends(get_db)):
    email_messages = customer_service.get_customer_messages(db, email_address)

    if email_messages is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    return email_messages


@router.patch("/{email_address}/note", response_model=CustomerReply)
def patch_customer_note(email_address: str, note_text: str, db: Session = Depends(get_db)):
    customer = customer_service.add_customer_note(db, email_address, note_text)

    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    return CustomerReply(
            customer_id=customer.id,
            customer_email=customer.email,
            customer_note=customer.note,
            company_id=customer.company_id
        )