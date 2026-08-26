from typing import Optional
from pydantic import BaseModel, EmailStr, Field, AliasPath
from datetime import datetime, date

class CourseEntryRequest(BaseModel):
    customer_email: EmailStr
    course_name: str
    course_date: date
    sent_at: datetime
    customer_name: str
    provider_message_id: str

class CourseEntryBatchRequest(BaseModel):
    entries: list[CourseEntryRequest]


class EmailSendRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    body: str
    reply_message_id: Optional[str] = None
    should_add_html: bool = False


class CourseResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class CustomerResponse(BaseModel):
    email: EmailStr

    name: str
    note: str
    company_domain: str

    class Config:
        from_attributes = True


class CourseEntryResponse(BaseModel):
    provider_message_id: str
    customer_email: EmailStr
    course_id: int
    course_date: datetime
    sent_at: datetime
    seen: bool

    course_name: str = Field(validation_alias=AliasPath("course", "name"))

    class Config:
        from_attributes = True

class EmailMessageResponse(BaseModel):
    provider_message_id: str
    customer_email: EmailStr
    subject: str
    body: str
    sent_at: datetime
    needs_response: bool
    category: str
    thread_id: int
    seen: bool

    class Config:
        from_attributes = True

class ProcessedEmail(BaseModel):
    provider_message_id: str
    customer_email: str
    sent_to: str
    subject: str
    body: str
    sent_at: datetime
    customer_name: str
    references: list[str]


class EmailIngestItem(ProcessedEmail):
    provider_message_id: str
    needs_response: bool
    category: str
