from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

from db import SessionLocal, Customer, EmailMessage, CourseEntry, Course
from sending_emails import send_email

app = FastAPI(title="Email CRM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class EmailIngestRequest(BaseModel):
    provider_message_id: str
    customer_email: EmailStr
    category: str
    needs_response: bool
    subject: str
    body: str
    sent_at: str

class CourseEntryRequest(BaseModel):
    customer_email: EmailStr
    course_name: str
    course_date: str
    sent_at: str

class EmailSendRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    body: str
    reply_message_id: Optional[str] = None

@app.post("/api/emails/ingest")
def ingest_email(payload: EmailIngestRequest, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter_by(email=payload.customer_email).first()
    if not customer:
        customer = Customer(email=payload.customer_email)
        print(f"Added customer {customer.email}")
        db.add(customer)
        db.flush()

    sent_time = datetime.fromisoformat(payload.sent_at)

    message = db.query(EmailMessage).filter_by(provider_message_id=payload.provider_message_id).first()
    if message:
        raise HTTPException(status_code=409, detail=f"Message {payload.provider_message_id} already exists")
    
    message = EmailMessage(
        customer_id=customer.id,
        provider_message_id=payload.provider_message_id,
        sender=payload.customer_email,
        subject=payload.subject,
        body=payload.body,
        sent_at=sent_time,
        needs_response=payload.needs_response,
        category=payload.category
    )
    db.add(message)
    db.flush()
        
    db.commit()
    return {
        "customer_id": customer.id,
        "message_id": message.id,
        "needs_response": message.needs_response
    }


@app.post("/api/add_course_entry", status_code=status.HTTP_201_CREATED)
def add_course_entry(payload: CourseEntryRequest, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter_by(email=payload.customer_email).first()
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")

    course = db.query(Course).filter_by(name=payload.course_name).first()
    if not course:
        raise HTTPException(status_code=404, detail="course not found")

    
    course_entry = CourseEntry(
        customer_id = customer.id,
        course_id = course.id,
        course_date = datetime.fromisoformat(payload.course_date),
        sent_at = datetime.fromisoformat(payload.sent_at)
    )
    db.add(course_entry)
    db.flush()
    db.commit()

    return {
        "course_entry_id": course_entry.id,
        "course_id": course.id
    }


@app.get("/api/unanswered")
def get_unanswered_messages(db: Session = Depends(get_db)):
    messages = (
        db.query(EmailMessage)
        .options(joinedload(EmailMessage.customer))
        .filter(EmailMessage.needs_response == True)
        .order_by(EmailMessage.sent_at.desc())
        .all()
    )
    
    return [
        {
            "provider_message_id": m.provider_message_id,
            "customer_email": m.customer.email,
            "sent_at": m.sent_at.isoformat()
        }
        for m in messages
    ]


@app.get("/api/messages/{provider_message_id}")
def get_message(provider_message_id: str, db: Session = Depends(get_db)):
    message = (
        db.query(EmailMessage)
        .options(joinedload(EmailMessage.customer))
        .filter_by(provider_message_id=provider_message_id)
        .first()
    )
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    return {
        "provider_message_id": message.provider_message_id,
        "customer": {
            "email": message.customer.email
        },
        "message": {
                "sender": message.sender,
                "subject": message.subject,
                "body": message.body,
                "sent_at": message.sent_at.isoformat()
        }
    }


@app.patch("/api/messages/{provider_message_id}/status")
def update_message_status(provider_message_id: str, needs_response: bool, db: Session = Depends(get_db)):
    message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    message.needs_response = needs_response
    db.commit()
    return {"needs_response": message.needs_response}


@app.post("/api/add_course", status_code=status.HTTP_201_CREATED)
def add_course(course_name: str, db: Session = Depends(get_db)):
    existing_course = db.query(Course).filter_by(name=course_name).first()
    if existing_course:
        print(f"Course '{course_name}' already exists.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course '{existing_course.name}' already exists."
        )

    course = Course(name=course_name)
    db.add(course)
    db.commit()
    db.refresh(course)
    
    print(f"Successfully added course: {course_name}")
    return {"course_id": course.id, "course_name": course.name}


@app.get("/api/courses",)
def get_courses(db: Session = Depends(get_db)):
    courses = db.query(Course).all()

    return {
        "courses": [
            {"course_id": course.id, "course_name": course.name} 
            for course in courses
        ]
    }

@app.get("/api/courses/{course_name}/entries")
def get_course_entries_by_course(course_name: str, db: Session = Depends(get_db)):
    """Displays all course entries connected to the given course name."""
    course = db.query(Course).filter_by(name=course_name).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    course_entries = (
        db.query(CourseEntry)
        .options(joinedload(CourseEntry.customer))
        .filter_by(course_id=course.id)
        .all()
    )

    return {
        "course_name": course.name,
        "course_entries": [
            {
                "course_entry_id": ce.id,
                "customer_email": ce.customer.email,
                "course_date": ce.course_date.isoformat(),
                "sent_at": ce.sent_at.isoformat()
            }
            for ce in course_entries
        ]
    }

@app.get("/api/courses/{course_name}/messages")
def get_messages_containing_course(course_name: str, db: Session = Depends(get_db)):
    """Displays all messages where the subject or body contains the course name."""
    course = db.query(Course).filter_by(name=course_name).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    search_pattern = f"%{course.name}%"
    messages = (
        db.query(EmailMessage)
        .options(joinedload(EmailMessage.customer))
        .filter(
            (EmailMessage.subject.ilike(search_pattern)) | 
            (EmailMessage.body.ilike(search_pattern)) |
            (EmailMessage.category.ilike(search_pattern))
        )
        .order_by(EmailMessage.sent_at.desc())
        .all()
    )

    return {
        "course_name": course.name,
        "messages": [
            {
                "provider_message_id": m.provider_message_id,
                "customer_email": m.customer.email if m.customer else None,
                "subject": m.subject,
                "body": m.body,
                "sent_at": m.sent_at.isoformat(),
                "needs_response": m.needs_response
            }
            for m in messages
        ]
    }


@app.get("/api/customers/{email}/history")
def get_customer_history(email: str, db: Session = Depends(get_db)):
    """Displays all messages and course entries connected to a user with the given email."""
    customer = db.query(Customer).filter_by(email=email).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    messages = (
        db.query(EmailMessage)
        .filter(EmailMessage.customer_id == customer.id)
        .order_by(EmailMessage.sent_at.desc())
        .all()
    )

    course_entries = (
        db.query(CourseEntry)
        .options(joinedload(CourseEntry.course))
        .filter(CourseEntry.customer_id == customer.id)
        .all()
    )

    return {
        "customer": {
            "id": customer.id,
            "email": customer.email
        },
        "messages": [
            {
                "provider_message_id": m.provider_message_id,
                "subject": m.subject,
                "body": m.body,
                "sent_at": m.sent_at.isoformat(),
                "needs_response": m.needs_response
            }
            for m in messages
        ],
        "course_entries": [
            {
                "course_entry_id": ce.id,
                "course_name": ce.course.name,
                "course_date": ce.course_date.isoformat(),
                "sent_at": ce.sent_at.isoformat()
            }
            for ce in course_entries
        ]
    }


@app.get("/api/customers")
def get_customers(db: Session = Depends(get_db)):
    customers = db.query(Customer).all()
    return {
        "customers": [
            {"customer_id": c.id, "customer_email": c.email} 
            for c in customers
        ]
    }

@app.post("/api/send")
def send(payload: EmailSendRequest):
    status = send_email(
        recipient_email=payload.recipient_email,
        subject=payload.subject,
        body=payload.body,
        reply_message_id=payload.reply_message_id
        )
    if status != "OK":
        raise HTTPException(status_code=500, detail=status)
    return {}
