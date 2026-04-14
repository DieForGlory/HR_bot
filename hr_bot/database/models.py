from sqlalchemy import BigInteger, String, ForeignKey, Date, Boolean, Integer, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import date, datetime
from typing import List

class Base(DeclarativeBase):
    pass

class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    parent_id: Mapped[int] = mapped_column(Integer, nullable=True)
    head_id: Mapped[int] = mapped_column(Integer, nullable=True)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    fullname: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    department_id: Mapped[int] = mapped_column(Integer, nullable=True)
    position: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    birth_date: Mapped[str] = mapped_column(String(50), nullable=True)
    car_info: Mapped[str] = mapped_column(String(255), nullable=True)
    face_id_photo: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="employee")
    language_code: Mapped[str] = mapped_column(String(2), default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    vacation_total: Mapped[int] = mapped_column(Integer, default=28)
    vacation_used: Mapped[int] = mapped_column(Integer, default=0)

class Request(Base):
    __tablename__ = "requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    comment: Mapped[str] = mapped_column(String(500), nullable=True)
    file_id: Mapped[str] = mapped_column(String(255), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(255))
    details: Mapped[str] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class Survey(Base):
    __tablename__ = "surveys"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    questions: Mapped[List["SurveyQuestion"]] = relationship(back_populates="survey")

class SurveyQuestion(Base):
    __tablename__ = "survey_questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id"))
    text: Mapped[str] = mapped_column(Text)
    survey: Mapped["Survey"] = relationship(back_populates="questions")

class SurveyAnswer(Base):
    __tablename__ = "survey_answers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("survey_questions.id"))
    answer: Mapped[str] = mapped_column(Text)

class Holiday(Base):
    __tablename__ = "holidays"
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True)

class SystemConfig(Base):
    __tablename__ = "system_config"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text)