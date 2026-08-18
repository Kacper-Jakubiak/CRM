from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies import get_db
from services import course_service

from schemas import CourseEntryRequest, CourseEntryBatchRequest, CourseReply, CourseEntryReply, EmailMessageReply

router = APIRouter(
    prefix="/api/courses",
    tags=["courses"]
)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CourseReply)
def add_course(course_name: str, db: Session = Depends(get_db)):
    course = course_service.add_course(db, course_name)

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course '{course_name}' already exists"
        )

    return CourseReply(course_id=course.id, course_name=course.name)


@router.get("", response_model=list[CourseReply])
def get_courses(db: Session = Depends(get_db)):
    courses = course_service.get_courses(db)
    return [CourseReply(course_id=c.id, course_name=c.name) for c in courses]


@router.get("/entries", response_model=list[CourseEntryReply])
def get_all_course_entries(db: Session = Depends(get_db)):
    entries = course_service.get_entries(db)
    return entries


@router.post("/entries", status_code=status.HTTP_201_CREATED, response_model=CourseEntryReply)
def add_course_entry(payload: CourseEntryRequest, db: Session = Depends(get_db)):
    entry = course_service.add_course_entry(
        db=db,
        customer_email=payload.customer_email,
        course_name=payload.course_name,
        course_date=payload.course_date,
        sent_at=payload.sent_at
    )

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    return entry


@router.post("/entries/batch", status_code=status.HTTP_201_CREATED, response_model=list[CourseEntryReply])
def add_course_entries_batch(payload: CourseEntryBatchRequest, db: Session = Depends(get_db)):
    entries = course_service.add_course_entries_batch(db, [entry.model_dump() for entry in payload.entries])
    return entries



@router.get("/course-entries", response_model=list[CourseEntryReply])
def get_course_entries_by_name(course_name: str, db: Session = Depends(get_db)):
    entries = course_service.get_course_entries(db, course_name)

    if entries is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    return entries


@router.get("/emails", response_model=list[EmailMessageReply])
def get_course_emails(course_name: str, db: Session = Depends(get_db)):
    email_messages = course_service.get_course_emails(db, course_name)

    if email_messages is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    return email_messages