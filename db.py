from datetime import datetime
from typing import List
import os

from sqlalchemy import create_engine, ForeignKey, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from dotenv import load_dotenv
from uuid import UUID


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "")


engine = create_engine(DATABASE_URL, connect_args={"prepare_threshold": None})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    email: Mapped[str] = mapped_column(primary_key=True, index=True)

    name: Mapped[str] = mapped_column(nullable=False, default="")
    company_domain: Mapped[str] = mapped_column(index=True, nullable=False)
    note: Mapped[str] = mapped_column(nullable=False, default="")

    email_messages: Mapped[List["EmailMessage"]] = relationship("EmailMessage", back_populates="customer")
    course_entries: Mapped[List["CourseEntry"]] = relationship("CourseEntry", back_populates="customer")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)

    entries: Mapped[List["CourseEntry"]] = relationship("CourseEntry", back_populates="course")


class EmailMessage(Base):
    __tablename__ = "email_messages"

    provider_message_id: Mapped[str] = mapped_column(primary_key=True, index=True)
    customer_email: Mapped[int] = mapped_column(ForeignKey("customers.email"), index=True, nullable=False)
    subject: Mapped[str] = mapped_column(nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(nullable=False)
    needs_response: Mapped[bool] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(nullable=False)
    thread_id: Mapped[UUID] = mapped_column(Uuid, index=True, nullable=False)
    seen: Mapped[bool] = mapped_column(nullable=False, default=False)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="email_messages")


class CourseEntry(Base):
    __tablename__ = "course_entries"

    provider_message_id: Mapped[str] = mapped_column(primary_key=True)
    customer_email: Mapped[str] = mapped_column(ForeignKey("customers.email"), index=True, nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True, nullable=False)
    course_date: Mapped[datetime] = mapped_column(nullable=False)
    sent_at: Mapped[datetime] = mapped_column(nullable=False)
    seen: Mapped[bool] = mapped_column(nullable=False, default=False)

    course: Mapped["Course"] = relationship("Course", back_populates="entries")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="course_entries")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("created")