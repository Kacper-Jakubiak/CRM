from typing import Optional
from pydantic import BaseModel, EmailStr, Field, AliasPath
from datetime import datetime

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
    messages: list[EmailIngestRequest]

class CourseEntryRequest(BaseModel):
    customer_email: EmailStr
    course_name: str
    course_date: datetime
    sent_at: datetime

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
    id: int
    name: str
    email: EmailStr
    company_id: int
    note: str

    company_name: str = Field(validation_alias=AliasPath("company", "domain"))

    class Config:
        from_attributes = True


class CourseEntryResponse(BaseModel):
    id: int
    customer_id: int
    course_id: int
    course_date: datetime
    sent_at: datetime

    customer_email: EmailStr = Field(validation_alias=AliasPath("customer", "email"))
    course_name: str = Field(validation_alias=AliasPath("course", "name"))

    class Config:
        from_attributes = True

class EmailMessageResponse(BaseModel):
    id: int
    customer_id: int
    provider_message_id: str
    sender: str
    subject: str
    body: str
    sent_at: datetime
    needs_response: bool
    category: str
    thread_id: int

    class Config:
        from_attributes = True