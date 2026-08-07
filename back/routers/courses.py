from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies import get_db
from services import course_service

from schemas import CourseEntryRequest, CourseEntryBatchRequest

router = APIRouter(
    prefix="/api/courses",
    tags=["courses"]
)


@router.post("", status_code=status.HTTP_201_CREATED)
def add_course(course_name: str, db: Session = Depends(get_db)):
    course = course_service.add_course(db, course_name)

    if not course:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course '{course_name}' already exists"
        )

    return {
        "course_id": course.id,
        "course_name": course.name
    }


@router.post("/import", status_code=status.HTTP_201_CREATED)
def import_courses(db: Session = Depends(get_db)):
    courses = course_service.import_courses(db)
    return {
        "courses": [{
            "course_id": c.id,
            "course_name": c.name
        } for c in courses]
    }



@router.get("")
def get_courses(db: Session = Depends(get_db)):
    courses = course_service.get_courses(db)
    return {
        "courses": [{
            "course_id": c.id,
            "course_name": c.name
        } for c in courses]
    }


@router.post("/entries", status_code=status.HTTP_201_CREATED)
def add_course_entry(payload: CourseEntryRequest, db: Session = Depends(get_db)):
    entry = course_service.add_course_entry(
        db=db,
        customer_email=payload.customer_email,
        course_name=payload.course_name,
        course_date=payload.course_date,
        sent_at=payload.sent_at
    )

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    return {
        "course_entry_id": entry.id,
        "customer_id": entry.customer_id,
        "course_id": entry.course_id
    }


@router.post("/entries/batch", status_code=status.HTTP_201_CREATED)
def add_course_entries_batch(payload: CourseEntryBatchRequest, db: Session = Depends(get_db)):
    entries = course_service.add_course_entries_batch(db, [entry.model_dump() for entry in payload.entries])
    return {
        "course_entries": [{
            "entry_id": e.id,
            "course_id": e.course_id,
            "customer_id": e.customer_id
        } for e in entries]
    }



@router.get("/{course_name}/entries")
def get_course_entries(course_name: str, db: Session = Depends(get_db)):
    entries = course_service.get_course_entries(db, course_name)

    if not entries:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    return {
        "course_entries": [{
            "entry_id": e.id,
            "course_id": e.course_id,
            "customer_id": e.customer_id
        } for e in entries]
    }


@router.get("/{course_name}/emails")
def get_course_emails(course_name: str, db: Session = Depends(get_db)):
    email_messages = course_service.get_course_emails(db, course_name)

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