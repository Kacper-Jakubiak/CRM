from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from db import Course, CourseEntry, Customer, EmailMessage
from integrations.course_parser import find_courses
from schemas import CourseEntryReply, EmailMessageReply
from util.schema_translations import to_entry_reply, to_email_message_reply
from customer_service import add_customer


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
        exists = (db.query(Course).filter_by(name=course_name).first())

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


def get_entries(db: Session) -> list[CourseEntryReply]:
    entries = (
        db.query(CourseEntry)
        .options(joinedload(CourseEntry.course), joinedload(CourseEntry.customer))
        .order_by(desc(CourseEntry.course_date))
        .all()
    )

    return [to_entry_reply(entry, entry.course.name, entry.customer.email) for entry in entries]


def add_course_entry(db: Session, customer_email: str, course_name: str, course_date: str, sent_at: str) -> CourseEntryReply | None:
    course = (db.query(Course).filter_by(name=course_name).first())

    if not course:
        return None

    customer = add_customer(db, "", customer_email)

    course_entry = CourseEntry(
        customer_id=customer.id,
        course_id=course.id,
        course_date=datetime.fromisoformat(course_date),
        sent_at=datetime.fromisoformat(sent_at)
    )

    db.add(course_entry)
    db.commit()
    db.refresh(course_entry)

    return to_entry_reply(course_entry, course.name, customer.email)


def add_course_entries_batch(db: Session, entries: list[dict[str, str]]) -> list[CourseEntryReply]:
    """
    entries should be a list of dictionaries:
    {
        "customer_email": "...",
        "course_name": "...",
        "course_date": "...",
        "sent_at": "...",
        "customer_name: "..."
    }
    """

    added = []

    for item in entries:
        course = (db.query(Course).filter_by(name=item["course_name"]).first())

        if not course:
            continue

        customer = add_customer(db, item["customer_name"], item["customer_email"])

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

    return [to_entry_reply(entry, entry.course.name, entry.customer.email) for entry in added]


def get_course_entries(db: Session, course_name: str) -> list[CourseEntryReply] | None:
    course = (
        db.query(Course)
        .filter_by(name=course_name)
        .first()
    )

    if not course:
        return None

    entries = (
        db.query(CourseEntry)
        .options(joinedload(CourseEntry.course), joinedload(CourseEntry.customer))
        .filter_by(course_id=course.id)
        .order_by(desc(CourseEntry.course_date))
        .all()
    )

    return [to_entry_reply(entry, entry.course.name, entry.customer.email) for entry in entries]


def get_course_emails(db: Session, course_name: str) -> list[EmailMessageReply] | None:
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

    return [to_email_message_reply(email) for email in emails]