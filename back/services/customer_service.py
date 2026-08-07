from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from db import Customer, CourseEntry, EmailMessage


def get_customers(db: Session) -> list[Customer]:
    return db.query(Customer).all()


def get_customer_by_email(db: Session, email: str) -> Customer | None:
    return db.query(Customer).filter_by(email=email).first()


def get_customer_entries(db: Session, email: str) -> list[CourseEntry] | None:
    customer = get_customer_by_email(db, email)

    if not customer:
        return None

    course_entries = (
        db.query(CourseEntry)
        .options(joinedload(CourseEntry.course))
        .filter(
            CourseEntry.customer_id == customer.id
        )
        .order_by(desc(CourseEntry.course_date))
        .all()
    )

    return course_entries


def get_customer_messages(db: Session, email: str) -> list[EmailMessage]:
    customer = get_customer_by_email(db, email)

    if not customer:
        return None

    messages = (
        db.query(EmailMessage)
        .filter(
            EmailMessage.customer_id == customer.id
        )
        .order_by(EmailMessage.sent_at.desc())
        .all()
    )

    return messages