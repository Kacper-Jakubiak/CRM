from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from dependencies import get_db
from services import course_service

from schemas import CourseResponse, CourseEntryResponse, CourseEntryBatchRequest, EmailMessageResponse

router = APIRouter(
    prefix="/api/courses",
    tags=["courses"]
)


@router.get("", response_model=list[CourseResponse])
def get_courses(db: Session = Depends(get_db)):
    try:
        courses = course_service.get_all_courses(db)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    return courses

@router.get("/entries", response_model=list[CourseEntryResponse])
def get_course_entries(db: Session = Depends(get_db)):
    try:
        entries = course_service.get_all_entries(db)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    return entries


@router.post("/entries/batch", status_code=status.HTTP_201_CREATED, response_model=list[CourseEntryResponse])
def add_course_entries_batch(payload: CourseEntryBatchRequest, db: Session = Depends(get_db)):
    try:
        entries = course_service.add_course_entries_batch(db, [item for item in payload.entries])
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    return entries


@router.get("/course-entries", response_model=list[CourseEntryResponse])
def get_course_entries_by_name(course_name: str, db: Session = Depends(get_db)):
    try:
        entries = course_service.get_course_entries(db, course_name)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    
    if entries is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    return entries


@router.get("/emails", response_model=list[EmailMessageResponse])
def get_course_emails(course_name: str, db: Session = Depends(get_db)):
    try:
        emails = course_service.get_course_emails(db, course_name)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    
    if emails is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    return emails