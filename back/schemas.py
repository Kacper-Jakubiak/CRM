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

class EmailSendRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    body: str
    reply_message_id: Optional[str] = None