from datetime import datetime
from pathlib import Path
from typing import List

from sqlalchemy import create_engine, ForeignKey, func, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

DB_PATH = Path(__file__).parent / "app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    # name: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    domain: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)

    customers: Mapped[List["Customer"]] = relationship("Customer", back_populates="company")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True, nullable=False)
    note: Mapped[str] = mapped_column(nullable=False, default="")

    company: Mapped["Company"] = relationship("Company", back_populates="customers")
    email_messages: Mapped[List["EmailMessage"]] = relationship("EmailMessage", back_populates="customer")
    course_entries: Mapped[List["CourseEntry"]] = relationship("CourseEntry", back_populates="customer")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)

    entries: Mapped[List["CourseEntry"]] = relationship("CourseEntry", back_populates="course")


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    provider_message_id: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    sender: Mapped[str] = mapped_column(nullable=False)
    subject: Mapped[str] = mapped_column(nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(nullable=False)
    needs_response: Mapped[bool] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(nullable=False)

    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id"), index=True, nullable=False)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="email_messages")
    thread: Mapped["Thread"] = relationship("Thread", back_populates="messages")


class CourseEntry(Base):
    __tablename__ = "course_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True, nullable=False)
    course_date: Mapped[datetime] = mapped_column(nullable=False)
    sent_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)

    course: Mapped["Course"] = relationship("Course", back_populates="entries")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="course_entries")


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[int] = mapped_column(primary_key=True)

    messages: Mapped[List["EmailMessage"]] = relationship("EmailMessage", back_populates="thread", cascade="all, delete-orphan")


Base.metadata.create_all(bind=engine)