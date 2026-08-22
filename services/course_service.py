from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from schemas import CourseEntryRequest
from util.email_util import extract_domain
from sqlalchemy import insert

from db import Course, CourseEntry, Customer, EmailMessage
from logger import logger

def add_courses(db: Session, course_names: list[str]) -> list[Course]:
    unique_names = set(course_names)
    if not unique_names:
        return []

    try:
        existing_names = set(name for (name,) in db.query(Course.name).filter(Course.name.in_(unique_names)).all())
        new_courses = [Course(name=name) for name in unique_names if name not in existing_names]

        if not new_courses:
            logger.info("No new courses to add; all provided names already exist in the database.")
            return []

        db.add_all(new_courses)
        db.commit()

        for course in new_courses:
            db.refresh(course)

        logger.info(f"Successfully added {len(new_courses)} new courses to the database.")
        return new_courses
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to batch add courses to database: {e}", exc_info=True)
        raise

def get_all_courses(db: Session) -> list[Course]:
    try:
        courses = db.query(Course).order_by(Course.name.asc()).all()
        logger.info(f"Retrieved {len(courses)} courses.")
        return courses
    except SQLAlchemyError as e:
        logger.error(f"Failed to retrieve courses: {e}", exc_info=True)
        raise

def get_all_entries(db: Session) -> list[CourseEntry]:
    try:
        entries = (
            db.query(CourseEntry)
            .options(joinedload(CourseEntry.course))
            .order_by(desc(CourseEntry.course_date))
            .all()
        )
        logger.info(f"Retrieved {len(entries)} course entries.")
        return entries
    except SQLAlchemyError as e:
        logger.error(f"Failed to retrieve course entries: {e}", exc_info=True)
        raise

def get_newest_entry(db: Session) -> CourseEntry | None:
    try:
        message = db.query(CourseEntry).options(joinedload(CourseEntry.course)).order_by(CourseEntry.sent_at.desc()).first()
        logger.info(f"Retrieved course entry message.")
        return message
    except SQLAlchemyError as e:
        logger.error(f"Failed to retrieve entry: {e}", exc_info=True)
        raise

def add_course_entries_batch(db: Session, entries: list[CourseEntryRequest]) -> list[CourseEntry]:
    if not entries:
        return []

    try:
        customer_emails = {item.customer_email for item in entries}

        existing_customers = db.query(Customer).filter(Customer.email.in_(customer_emails)).all()
        existing_emails = {c.email for c in existing_customers}
        missing_emails = customer_emails - existing_emails

        new_customers_data = []
        seen_in_batch = set()

        for item in entries:
            email = item.customer_email
            if email in missing_emails and email not in seen_in_batch:
                seen_in_batch.add(email)
                new_customers_data.append({
                    "email": email,
                    "name": item.customer_name if item.customer_name else "",
                    "company_domain": extract_domain(email),
                })

        if new_customers_data:
            db.execute(insert(Customer), new_customers_data)
            
        batch_entry_ids = {item.provider_message_id for item in entries}
        existing_entries =  db.query(CourseEntry).filter(
            CourseEntry.provider_message_id.in_(batch_entry_ids)
        ).all()
        entry_map = {e.provider_message_id: e for e in existing_entries}
        course_names = {item.course_name for item in entries}
        courses_map = {c.name: c for c in db.query(Course).filter(Course.name.in_(course_names)).all()}

        inserted_entries: list[CourseEntry] = []

        for item in entries:
            provider_message_id = item.provider_message_id

            if provider_message_id in entry_map:
                logger.info(f"Skipping duplicate entry with provider_message_id '{provider_message_id}'.")
                continue

            course = courses_map.get(item.course_name)
            if not course:
                logger.warning(f"Skipping entry: Course '{item.course_name}' not found.")
                continue

            course_entry = CourseEntry(
                provider_message_id=item.provider_message_id,
                customer_email=item.customer_email,
                course_id=course.id,
                course_date=item.course_date,
                sent_at=item.sent_at,
            )
            db.add(course_entry)
            inserted_entries.append(course_entry)
            entry_map[provider_message_id] = course_entry

        db.commit()
        for entry in inserted_entries:
            db.refresh(entry)

        logger.info(f"Successfully added {len(inserted_entries)} course entries in batch.")
        return inserted_entries
    
    except (SQLAlchemyError, ValueError, KeyError) as e:
        db.rollback()
        logger.error(f"Failed to batch add course entries to database: {e}", exc_info=True)
        raise

def set_seen(db: Session, provider_message_id: str, seen_status: bool) -> CourseEntry | None:
    try:
        entry = db.query(CourseEntry).filter_by(provider_message_id=provider_message_id).options(joinedload(CourseEntry.course)).first()
        if entry is None:
            logger.warning(f"Entry '{provider_message_id}' not found when fetching entries.")
            return None
        entry.seen = seen_status
        db.commit()
        db.refresh(entry)
        logger.info(f"Updated 'seen' to {seen_status} for entry '{provider_message_id}'.")
        return entry
    except SQLAlchemyError as e:
        logger.error(f"Failed to retrieve entry: {e}", exc_info=True)
        raise


def get_course_entries(db: Session, course_name: str) -> list[CourseEntry] | None:
    try:
        course = db.query(Course).filter_by(name=course_name).first()
        if not course:
            logger.warning(f"Course '{course_name}' not found when fetching entries.")
            return None

        entries = (
            db.query(CourseEntry)
            .options(joinedload(CourseEntry.course))
            .filter_by(course_id=course.id)
            .order_by(desc(CourseEntry.course_date))
            .all()
        )
        logger.info(f"Retrieved {len(entries)} entries for course '{course_name}'.")
        return entries
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch course entries for '{course_name}': {e}", exc_info=True)
        raise

def get_course_emails(db: Session, course_name: str) -> list[EmailMessage] | None:
    try:
        course = db.query(Course).filter_by(name=course_name).first()
        if not course:
            logger.warning(f"Course '{course_name}' not found when fetching emails.")
            return None

        search_pattern = f"%{course.name}%"
        emails = (
            db.query(EmailMessage)
            .filter(
                (EmailMessage.subject.ilike(search_pattern)) | 
                (EmailMessage.body.ilike(search_pattern)) |
                (EmailMessage.category.ilike(search_pattern))
            )
            .order_by(EmailMessage.sent_at.desc())
            .all()
        )
        logger.info(f"Retrieved {len(emails)} emails matching course '{course_name}'.")
        return emails
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch emails for course '{course_name}': {e}", exc_info=True)
        raise