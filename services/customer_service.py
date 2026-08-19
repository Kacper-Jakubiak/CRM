from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from util.email_util import extract_domain
from db import Customer, CourseEntry, EmailMessage
from logger import logger

def _get_customer_by_email(db: Session, email_address: str) -> Customer | None:
    return db.query(Customer).filter_by(email=email_address).first()

def add_customer(db: Session, name: str, email_address: str) -> Customer:
    try:
        customer = _get_customer_by_email(db, email_address)
        if customer:
            logger.info(f"Customer '{email_address}' already exists.")
            return customer

        domain = extract_domain(email_address)

        customer = Customer(email=email_address, name=name, company_domain=domain)
        db.add(customer)
        db.commit()
        db.refresh(customer)

        logger.info(f"Successfully added customer '{email_address}'.")
        return customer
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to add customer '{email_address}': {e}", exc_info=True)
        raise

def add_customer_note(db: Session, email_address: str, note_text: str) -> Customer | None:
    try:
        customer = _get_customer_by_email(db, email_address)
        if customer is None:
            logger.warning(f"Customer '{email_address}' not found when adding note.")
            return None

        customer.note = note_text
        db.commit()
        db.refresh(customer)

        logger.info(f"Successfully updated note for customer '{email_address}'.")
        return customer
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to add note for customer '{email_address}': {e}", exc_info=True)
        raise

def get_customers(db: Session) -> list[Customer]:
    try:
        customers = db.query(Customer).all()
        logger.info(f"Retrieved {len(customers)} customers.")
        return customers
    except SQLAlchemyError as e:
        logger.error(f"Failed to retrieve customers: {e}", exc_info=True)
        raise

def get_customer_entries(db: Session, email_address: str) -> list[CourseEntry] | None:
    try:
        customer = _get_customer_by_email(db, email_address)
        if not customer:
            logger.warning(f"Customer '{email_address}' not found when fetching course entries.")
            return None

        course_entries = (
            db.query(CourseEntry)
            .options(joinedload(CourseEntry.course))
            .filter(CourseEntry.customer_email == customer.email)
            .order_by(desc(CourseEntry.course_date))
            .all()
        )

        logger.info(f"Retrieved {len(course_entries)} entries for customer '{email_address}'.")
        return course_entries
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch course entries for '{email_address}': {e}", exc_info=True)
        raise

def get_customer_messages(db: Session, email_address: str) -> list[EmailMessage] | None:
    try:
        customer = _get_customer_by_email(db, email_address)
        if not customer:
            logger.warning(f"Customer '{email_address}' not found when fetching messages.")
            return None

        messages = (
            db.query(EmailMessage)
            .filter(EmailMessage.customer_email == customer.email)
            .order_by(EmailMessage.sent_at.desc())
            .all()
        )

        logger.info(f"Retrieved {len(messages)} messages for customer '{email_address}'.")
        return messages
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch messages for customer '{email_address}': {e}", exc_info=True)
        raise