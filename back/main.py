from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

from db import SessionLocal, Customer, EmailMessage, CourseEntry, Course, Thread
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
    parent_message_provider_id: Optional[str]

class EmailBatchIngestRequest(BaseModel):
    messages: List[EmailIngestRequest]

class CourseEntryRequest(BaseModel):
    customer_email: EmailStr
    course_name: str
    course_date: str
    sent_at: str

class CourseEntryBatchRequest(BaseModel):
    entries: List[CourseEntryRequest]

class EmailSendRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    body: str
    reply_message_id: Optional[str] = None

@app.post("/api/courses", status_code=status.HTTP_201_CREATED)
def add_course(course_name: str, db: Session = Depends(get_db)):
    existing_course = db.query(Course).filter_by(name=course_name).first()
    if existing_course:
        print(f"Course '{course_name}' already exists.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course '{existing_course.name}' already exists."
        )

    course = Course(name=course_name)
    db.add(course)
    db.commit()
    db.refresh(course)
    
    print(f"Successfully added course: {course_name}")
    return {"course_id": course.id, "course_name": course.name}


@app.post("/api/emails", status_code=status.HTTP_201_CREATED)
def ingest_email(payload: EmailIngestRequest, db: Session = Depends(get_db)):
    message = db.query(EmailMessage).filter_by(provider_message_id=payload.provider_message_id).first()
    if message:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=f"Message {payload.provider_message_id} already exists"
        )
    
    thread_id = None
    if payload.parent_message_provider_id:
        parent = db.query(EmailMessage).filter_by(provider_message_id=payload.parent_message_provider_id).first()
        if parent:
            thread_id = parent.thread_id
        else:
            print(f"Warning: Parent message {payload.parent_message_provider_id} not found. Creating a new thread.")

    if thread_id is None:
        new_thread = Thread()
        db.add(new_thread)
        db.flush()
        print(f"Added new thread {new_thread.id}")
        thread_id = new_thread.id
        
    
    customer = db.query(Customer).filter_by(email=payload.customer_email).first()
    if not customer:
        customer = Customer(email=payload.customer_email)
        db.add(customer)
        db.flush()
        print(f"Added customer {customer.email} | {customer.id}")

    
    message = EmailMessage(
        customer_id=customer.id,
        provider_message_id=payload.provider_message_id,
        sender=payload.customer_email,
        subject=payload.subject,
        body=payload.body,
        sent_at=datetime.fromisoformat(payload.sent_at),
        needs_response=payload.needs_response,
        category=payload.category,
        thread_id=thread_id
    )
    db.add(message)
    db.flush()
        
    db.commit()
    return {
        "customer_id": customer.id,
        "message_id": message.id,
        "thread_id": message.thread_id,
        "needs_response": message.needs_response
    }


@app.post("/api/emails/batch", status_code=status.HTTP_201_CREATED)
def batch_ingest_emails(payload: EmailBatchIngestRequest, db: Session = Depends(get_db)):
    results = []
    
    for item in payload.messages:
        existing_message = db.query(EmailMessage).filter_by(provider_message_id=item.provider_message_id).first()
        if existing_message:
            continue
        
        thread_id = None
        if item.parent_message_provider_id:
            parent = db.query(EmailMessage).filter_by(provider_message_id=item.parent_message_provider_id).first()
            if parent:
                thread_id = parent.thread_id

        if thread_id is None:
            new_thread = Thread()
            db.add(new_thread)
            db.flush()
            thread_id = new_thread.id

        customer = db.query(Customer).filter_by(email=item.customer_email).first()
        if not customer:
            customer = Customer(email=item.customer_email)
            db.add(customer)
            db.flush()

        message = EmailMessage(
            customer_id=customer.id,
            provider_message_id=item.provider_message_id,
            sender=item.customer_email,
            subject=item.subject,
            body=item.body,
            sent_at=datetime.fromisoformat(item.sent_at),
            needs_response=item.needs_response,
            category=item.category,
            thread_id=thread_id
        )
        db.add(message)
        db.flush()
        
        results.append({
            "provider_message_id": message.provider_message_id,
            "message_id": message.id,
            "thread_id": message.thread_id
        })

    db.commit()
    return {"processed_count": len(results), "messages": results}


@app.post("/api/course-entries", status_code=status.HTTP_201_CREATED)
def add_course_entry(payload: CourseEntryRequest, db: Session = Depends(get_db)):
    course = db.query(Course).filter_by(name=payload.course_name).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="course not found"
        )

    customer = db.query(Customer).filter_by(email=payload.customer_email).first()
    if not customer:
        customer = Customer(email=payload.customer_email)
        db.add(customer)
        db.flush()
        print(f"Added customer {customer.email} | {customer.id}")


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
        "customer_id": customer.id,
        "course_entry_id": course_entry.id,
        "course_id": course.id
    }


@app.post("/api/course-entries/batch", status_code=status.HTTP_201_CREATED)
def add_course_entries_batch(payload: CourseEntryBatchRequest, db: Session = Depends(get_db)):
    results = []
    courses = []
    
    for item in payload.entries:
        course = db.query(Course).filter_by(name=item.course_name).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course '{item.course_name}' not found"
            )
        courses.append(course)

    for item, course in zip(payload.entries, courses):
        customer = db.query(Customer).filter_by(email=item.customer_email).first()
        if not customer:
            customer = Customer(email=item.customer_email)
            db.add(customer)
            db.flush()

        course_entry = CourseEntry(
            customer_id=customer.id,
            course_id=course.id,
            course_date=datetime.fromisoformat(item.course_date),
            sent_at=datetime.fromisoformat(item.sent_at)
        )
        db.add(course_entry)
        db.flush()

        results.append({
            "customer_id": customer.id,
            "course_entry_id": course_entry.id,
            "course_id": course.id
        })

    db.commit()
    return {
        "processed_count": len(results),
        "course_entries": results
    }

@app.patch("/api/messages/{provider_message_id}/status")
def update_message_status(provider_message_id: str, needs_response: bool, db: Session = Depends(get_db)):
    message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    message.needs_response = needs_response
    db.commit()
    return {"needs_response": message.needs_response}


@app.get("/api/courses",)
def get_courses(db: Session = Depends(get_db)):
    courses = db.query(Course).all()

    return {
        "courses": [
            {"course_id": course.id, "course_name": course.name} 
            for course in courses
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
        .order_by(desc(CourseEntry.course_date))
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
                "needs_response": m.needs_response,
                "thread_id": m.thread_id
            }
            for m in messages
        ]
    }


@app.get("/api/customers/{email}/entries")
def get_customer_entries(email: str, db: Session = Depends(get_db)):
    """Displays all course entries connected to a user with the given email."""
    customer = db.query(Customer).filter_by(email=email).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    course_entries = (
        db.query(CourseEntry)
        .options(joinedload(CourseEntry.course))
        .filter(CourseEntry.customer_id == customer.id)
        .order_by(desc(CourseEntry.course_date))
        .all()
    )

    return {
        "customer": {
            "id": customer.id,
            "email": customer.email
        },
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


@app.get("/api/customers/{email}/messages")
def get_customer_messages(email: str, db: Session = Depends(get_db)):
    """Displays all messages connected to a user with the given email."""
    customer = db.query(Customer).filter_by(email=email).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    messages = (
        db.query(EmailMessage)
        .filter(EmailMessage.customer_id == customer.id)
        .order_by(EmailMessage.sent_at.desc())
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
                "needs_response": m.needs_response,
                "thread_id": m.thread_id
            }
            for m in messages
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


@app.get("/api/messages/{provider_message_id}")
def get_message(provider_message_id: str, db: Session = Depends(get_db)):
    message = (
        db.query(EmailMessage)
        .filter_by(provider_message_id=provider_message_id)
        .first()
    )
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    return {
        "message": {
                "id": message.id,
                "customer_id": message.customer_id,
                "sender": message.sender,
                "subject": message.subject,
                "body": message.body,
                "sent_at": message.sent_at.isoformat(),
                "needs_response": message.needs_response,
                "category": message.category
        }
    }

@app.patch("/api/messages/{provider_message_id}/move")
def move_message_to_thread(provider_message_id: str, new_thread_id: int, db: Session = Depends(get_db)):
    """
    Moves an email message and its entire downstream reply-chain subtree 
    to a new thread based on the provider_message_id lookup.
    """
    message = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    thread = db.query(Thread).filter_by(id=new_thread_id).first()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )

    old_thread_id = message.thread_id
    if old_thread_id == new_thread_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message is already in the specified thread"
        )

    moved_count = db.query(EmailMessage).filter_by(thread_id=old_thread_id).update(
        {EmailMessage.thread_id: new_thread_id}, 
        synchronize_session=False
    )

    db.query(Thread).filter(Thread.id == old_thread_id).delete(synchronize_session=False)
    db.commit()

    return {"detail": f"Successfully merged thread {old_thread_id} ({moved_count} messages) into thread {new_thread_id}."}