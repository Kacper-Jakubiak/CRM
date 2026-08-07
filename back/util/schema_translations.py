from db import CourseEntry, EmailMessage
from schemas import CourseEntryReply, EmailMessageReply


def to_email_message_reply(message: EmailMessage) -> EmailMessageReply:
    return EmailMessageReply(
        id=message.id,
        customer_id=message.customer_id,
        provider_message_id=message.provider_message_id,
        sender=message.sender,
        subject=message.subject,
        body=message.body,
        sent_at=message.sent_at.isoformat(),
        needs_response=message.needs_response,
        category=message.category,
        thread_id=message.thread_id,
    )


def to_entry_reply(entry: CourseEntry, course_name: str) -> CourseEntryReply:
    return CourseEntryReply(
        entry_id=entry.id,
        course_id=entry.course_id,
        customer_id=entry.customer_id,
        course_name=course_name,
        course_date=entry.course_date.isoformat(),
        sent_at=entry.sent_at.isoformat(),
    )
