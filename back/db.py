from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DB_PATH = Path(__file__).parent / "app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)

class EmailMessage(Base):
    __tablename__ = "email_messages"
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True, nullable=False)
    provider_message_id = Column(String, unique=True, index=True, nullable=False)
    sender = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=func.now(), nullable=False)
    needs_response = Column(Boolean, default=False, nullable=False)
    category = Column(String, nullable=False)
    
    thread_id = Column(Integer, ForeignKey("threads.id"), index=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("email_messages.id"), index=True, nullable=True)
    
    customer = relationship("Customer")
    thread = relationship("Thread", back_populates="messages")
    
    parent = relationship("EmailMessage", remote_side=[id], back_populates="replies")
    replies = relationship("EmailMessage", back_populates="parent", cascade="all, delete")

class CourseEntry(Base):
    __tablename__ = "course_entries"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), index=True, nullable=True)
    course_date = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, default=func.now(), nullable=False)

    course = relationship("Course")
    customer = relationship("Customer")

class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True)
    
    messages = relationship("EmailMessage", back_populates="thread", cascade="all, delete-orphan")

Base.metadata.create_all(bind=engine)