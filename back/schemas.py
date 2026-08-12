from typing import Optional, List
from pydantic import BaseModel, EmailStr

class EmailIngestRequest(BaseModel):
    provider_message_id: str
    customer_email: EmailStr
    category: str
    needs_response: bool
    subject: str
    body: str
    sent_at: str
    parent_message_provider_id: Optional[str]

class EmailBatchIngestRequest(BaseModel):
    messages: List[EmailIngestRequest]

class CourseEntryRequest(BaseModel):
    customer_email: EmailStr
    course_name: str
    course_date: str
    sent_at: str

class CourseEntryBatchRequest(BaseModel):
    entries: List[CourseEntryRequest]

class CourseReply(BaseModel):
    course_id: int
    course_name: str

class CustomerReply(BaseModel):
    customer_id: int
    customer_email: EmailStr
    customer_note: str
    company_id: int

class CourseEntryReply(BaseModel):
    entry_id: int
    course_id: int
    customer_id: int
    customer_email: EmailStr
    course_name: str
    course_date: str
    sent_at: str

class EmailMessageReply(BaseModel):
    id: int
    customer_id: int
    provider_message_id: str
    sender: str
    subject: str
    body: str
    sent_at: str
    needs_response: bool
    category: str
    thread_id: int

class EmailSendRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    body: str
    reply_message_id: Optional[str] = None
    should_add_html: bool = False

class PullEmailsReply(BaseModel):
    email_batch: List[EmailMessageReply]
    entry_batch: List[CourseEntryReply]
