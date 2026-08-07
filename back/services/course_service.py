from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from db import Course, CourseEntry, Customer, EmailMessage
from integrations.course_parser import find_courses


def add_course(db: Session, course_name: str) -> Course | None:
    existing_course = db.query(Course).filter_by(name=course_name).first()

    if existing_course:
        return None

    course = Course(name=course_name)

    db.add(course)
    db.commit()
    db.refresh(course)

    return course


def import_courses(db: Session) -> list[Course]:
    """
    Imports courses from an external source and adds missing courses.
    """

    courses = find_courses()
    added = []

    for course_name in courses:
        exists = (
            db.query(Course)
            .filter_by(name=course_name)
            .first()
        )

        if exists:
            continue
        
        course = Course(name=course_name)
        db.add(course)
        added.append(course)

    db.commit()

    for course in added:
        db.refresh(course)

    return added


def get_courses(db: Session) -> list[Course]:
    courses = db.query(Course).all()

    return courses


def add_course_entry(db: Session, customer_email: str, course_name: str, course_date: str, sent_at: str) -> CourseEntry | None:
    course = (
        db.query(Course)
        .filter_by(name=course_name)
        .first()
    )

    if not course:
        return None

    customer = (
        db.query(Customer)
        .filter_by(email=customer_email)
        .first()
    )

    if not customer:
        customer = Customer(email=customer_email)
        db.add(customer)
        db.flush()

    course_entry = CourseEntry(
        customer_id=customer.id,
        course_id=course.id,
        course_date=datetime.fromisoformat(course_date),
        sent_at=datetime.fromisoformat(sent_at)
    )

    db.add(course_entry)
    db.commit()
    db.refresh(course_entry)

    return course_entry


def add_course_entries_batch(db: Session, entries: list[dict[str, str]]) -> list[CourseEntry]:
    """
    entries should be a list of dictionaries:
    {
        "customer_email": "...",
        "course_name": "...",
        "course_date": "...",
        "sent_at": "..."
    }
    """

    added = []

    for item in entries:
        course = (
            db.query(Course)
            .filter_by(name=item["course_name"])
            .first()
        )

        if not course:
            continue

        customer = (
            db.query(Customer)
            .filter_by(email=item["customer_email"])
            .first()
        )

        if not customer:
            customer = Customer(email=item["customer_email"])
            db.add(customer)
            db.flush()

        course_entry = CourseEntry(
            customer_id=customer.id,
            course_id=course.id,
            course_date=datetime.fromisoformat(item["course_date"]),
            sent_at=datetime.fromisoformat(item["sent_at"])
        )

        db.add(course_entry)
        db.flush()

        added.append(course_entry)

    db.commit()
    for course_entry in added:
        db.refresh(course_entry)

    return added


def get_course_entries(db: Session, course_name: str) -> list[CourseEntry] | None:
    course = (
        db.query(Course)
        .filter_by(name=course_name)
        .first()
    )

    if not course:
        return None

    entries = (
        db.query(CourseEntry)
        .options(joinedload(CourseEntry.customer))
        .filter_by(course_id=course.id)
        .order_by(desc(CourseEntry.course_date))
        .all()
    )

    return entries


def get_course_emails(db: Session, course_name: str) -> list[EmailMessage] | None:
    course = (
        db.query(Course)
        .filter_by(name=course_name)
        .first()
    )

    if not course:
        return None

    search_pattern = f"%{course.name}%"
    emails = (
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

    return emails