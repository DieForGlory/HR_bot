
from sqlalchemy import BigInteger, String, ForeignKey, Date, Boolean, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import date
from typing import List

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    fullname: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    department: Mapped[str] = mapped_column(String(255), nullable=True)
    position: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    birth_date: Mapped[str] = mapped_column(String(50), nullable=True)
    car_info: Mapped[str] = mapped_column(String(255), nullable=True)
    face_id_photo: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="employee")
    language_code: Mapped[str] = mapped_column(String(2), default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(50))  # vacation, day_off, sick_leave, certificate
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    comment: Mapped[str] = mapped_column(String(500), nullable=True)
    file_id: Mapped[str] = mapped_column(String(255), nullable=True)

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