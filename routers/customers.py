from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from dependencies import get_db
from services import customer_service
from schemas import CustomerResponse, CourseEntryResponse, EmailMessageResponse

router = APIRouter(
    prefix="/api/customers",
    tags=["customers"]
)

@router.get("", response_model=list[CustomerResponse])
def get_customers(db: Session = Depends(get_db)):
    try:
        customers = customer_service.get_customers(db=db)
        return customers
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customers"
        )


@router.get("/entries", response_model=list[CourseEntryResponse])
def get_customer_entries(email_address: str, db: Session = Depends(get_db)):
    try:
        entries = customer_service.get_customer_entries(
            db=db,
            email_address=email_address
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer entries"
        )

    if entries is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return entries


@router.get("/emails", response_model=list[EmailMessageResponse])
def get_customer_messages(email_address: str, db: Session = Depends(get_db)):
    try:
        email_messages = customer_service.get_customer_messages(
            db=db,
            email_address=email_address
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer messages"
        )

    if email_messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return email_messages


@router.patch("/note", response_model=CustomerResponse)
def patch_customer_note(email_address: str, note_text: str, db: Session = Depends(get_db)):
    try:
        customer = customer_service.add_customer_note(
            db=db,
            email_address=email_address,
            note_text=note_text
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update customer note"
        )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return customer