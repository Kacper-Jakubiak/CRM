from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from util.email_util import extract_domain

from db import Customer, CourseEntry, EmailMessage, Company
from schemas import CourseEntryReply, EmailMessageReply, CustomerReply
from util.schema_translations import to_email_message_reply, to_entry_reply, to_customer_reply

def _get_customer_by_email(db: Session, email_address: str) -> Customer | None:
    return db.query(Customer).filter_by(email=email_address).options(joinedload(Customer.company)).first()

def add_customer(db: Session, name: str, email_address: str) -> Customer:
    customer = _get_customer_by_email(db, email_address)

    if customer:
        return customer
    
    domain = extract_domain(email_address)
    company = db.query(Company).filter_by(domain=domain).first()
    if not company:
        company = Company(domain=domain)
        db.add(company)
        db.flush()

    customer = Customer(name=name, email=email_address, company_id=company.id)
    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


def add_customer_note(db:Session, email_address: str, note_text: str) -> CustomerReply | None:
    customer = _get_customer_by_email(db, email_address)
    if customer is None:
        return None
    
    customer.note = note_text
    db.commit()
    db.refresh(customer)
    return to_customer_reply(customer, customer.company.domain)


def get_customers(db: Session) -> list[CustomerReply]:
    customers = db.query(Customer).options(joinedload(Customer.company)).all()
    return [to_customer_reply(customer, customer.company.domain) for customer in customers]


def get_customer_entries(db: Session, email_address: str) -> list[CourseEntryReply] | None:
    customer = _get_customer_by_email(db, email_address)

    if not customer:
        return None

    course_entries = (
        db.query(CourseEntry)
        .options(joinedload(CourseEntry.course), joinedload(CourseEntry.customer))
        .filter(
            CourseEntry.customer_id == customer.id
        )
        .order_by(desc(CourseEntry.course_date))
        .all()
    )

    return [to_entry_reply(entry, entry.course.name, entry.customer.email) for entry in course_entries]


def get_customer_messages(db: Session, email_address: str) -> list[EmailMessageReply] | None:
    customer = _get_customer_by_email(db, email_address)

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

    return [to_email_message_reply(message) for message in messages]