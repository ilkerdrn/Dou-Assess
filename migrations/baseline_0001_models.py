from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer,
    JSON, String, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Program(Base):
    __tablename__ = "programs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    faculty: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    department: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    courses: Mapped[list["Course"]] = relationship(back_populates="program", cascade="all, delete-orphan")
    students: Mapped[list["Student"]] = relationship(back_populates="program", cascade="all, delete-orphan")
    program_outcomes: Mapped[list["ProgramOutcome"]] = relationship(back_populates="program", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("program_id", "code", "academic_year", "term", name="uq_course_offering"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False)
    term: Mapped[str] = mapped_column(String(32), nullable=False)
    instructor_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    program: Mapped[Program] = relationship(back_populates="courses")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    learning_outcomes: Mapped[list["LearningOutcome"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    exams: Mapped[list["Exam"]] = relationship(back_populates="course", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    student_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    class_name: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    program: Mapped[Program] = relationship(back_populates="students")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("course_id", "student_id", name="uq_course_student"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    course: Mapped[Course] = relationship(back_populates="enrollments")
    student: Mapped[Student] = relationship(back_populates="enrollments")


class LearningOutcome(Base):
    __tablename__ = "learning_outcomes"
    __table_args__ = (UniqueConstraint("course_id", "code", name="uq_course_lo"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_percent: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)

    course: Mapped[Course] = relationship(back_populates="learning_outcomes")
    mappings: Mapped[list["OutcomeMapping"]] = relationship(back_populates="learning_outcome", cascade="all, delete-orphan")


class ProgramOutcome(Base):
    __tablename__ = "program_outcomes"
    __table_args__ = (UniqueConstraint("program_id", "academic_year", "code", name="uq_program_po"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    program: Mapped[Program] = relationship(back_populates="program_outcomes")
    mappings: Mapped[list["OutcomeMapping"]] = relationship(back_populates="program_outcome", cascade="all, delete-orphan")


class OutcomeMapping(Base):
    __tablename__ = "outcome_mappings"
    __table_args__ = (
        UniqueConstraint("learning_outcome_id", "program_outcome_id", name="uq_lo_po"),
        CheckConstraint("contribution >= 0 AND contribution <= 5", name="ck_contribution_0_5"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    learning_outcome_id: Mapped[int] = mapped_column(ForeignKey("learning_outcomes.id", ondelete="CASCADE"), nullable=False)
    program_outcome_id: Mapped[int] = mapped_column(ForeignKey("program_outcomes.id", ondelete="CASCADE"), nullable=False)
    contribution: Mapped[int] = mapped_column(Integer, nullable=False)

    learning_outcome: Mapped[LearningOutcome] = relationship(back_populates="mappings")
    program_outcome: Mapped[ProgramOutcome] = relationship(back_populates="mappings")


class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(64), default="Sınav", nullable=False)
    exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    course: Mapped[Course] = relationship(back_populates="exams")
    learning_outcomes: Mapped[list["ExamLearningOutcome"]] = relationship(back_populates="exam", cascade="all, delete-orphan")
    program_outcomes: Mapped[list["ExamProgramOutcome"]] = relationship(back_populates="exam", cascade="all, delete-orphan")
    questions: Mapped[list["Question"]] = relationship(back_populates="exam", cascade="all, delete-orphan")
    exam_students: Mapped[list["ExamStudent"]] = relationship(back_populates="exam", cascade="all, delete-orphan")


class ExamLearningOutcome(Base):
    __tablename__ = "exam_learning_outcomes"
    __table_args__ = (UniqueConstraint("exam_id", "code", name="uq_exam_lo"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    source_learning_outcome_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_percent: Mapped[float] = mapped_column(Float, nullable=False)

    exam: Mapped[Exam] = relationship(back_populates="learning_outcomes")
    mappings: Mapped[list["ExamOutcomeMapping"]] = relationship(back_populates="learning_outcome", cascade="all, delete-orphan")
    questions: Mapped[list["Question"]] = relationship(back_populates="learning_outcome")


class ExamProgramOutcome(Base):
    __tablename__ = "exam_program_outcomes"
    __table_args__ = (UniqueConstraint("exam_id", "code", name="uq_exam_po"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    source_program_outcome_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    exam: Mapped[Exam] = relationship(back_populates="program_outcomes")
    mappings: Mapped[list["ExamOutcomeMapping"]] = relationship(back_populates="program_outcome", cascade="all, delete-orphan")


class ExamOutcomeMapping(Base):
    __tablename__ = "exam_outcome_mappings"
    __table_args__ = (UniqueConstraint("exam_learning_outcome_id", "exam_program_outcome_id", name="uq_exam_lo_po"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_learning_outcome_id: Mapped[int] = mapped_column(ForeignKey("exam_learning_outcomes.id", ondelete="CASCADE"), nullable=False)
    exam_program_outcome_id: Mapped[int] = mapped_column(ForeignKey("exam_program_outcomes.id", ondelete="CASCADE"), nullable=False)
    contribution: Mapped[int] = mapped_column(Integer, nullable=False)

    learning_outcome: Mapped[ExamLearningOutcome] = relationship(back_populates="mappings")
    program_outcome: Mapped[ExamProgramOutcome] = relationship(back_populates="mappings")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("exam_id", "order_no", name="uq_exam_question_order"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    points: Mapped[float] = mapped_column(Float, nullable=False)
    correct_answer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    choices: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    exam_learning_outcome_id: Mapped[Optional[int]] = mapped_column(ForeignKey("exam_learning_outcomes.id", ondelete="SET NULL"), nullable=True)

    exam: Mapped[Exam] = relationship(back_populates="questions")
    learning_outcome: Mapped[Optional[ExamLearningOutcome]] = relationship(back_populates="questions")


class ExamStudent(Base):
    __tablename__ = "exam_students"
    __table_args__ = (UniqueConstraint("exam_id", "student_id", name="uq_exam_student"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    exam: Mapped[Exam] = relationship(back_populates="exam_students")
    student: Mapped[Student] = relationship()
    responses: Mapped[list["Response"]] = relationship(back_populates="exam_student", cascade="all, delete-orphan")


class Response(Base):
    __tablename__ = "responses"
    __table_args__ = (UniqueConstraint("exam_student_id", "question_id", name="uq_student_question_response"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_student_id: Mapped[int] = mapped_column(ForeignKey("exam_students.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    awarded_points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    exam_student: Mapped[ExamStudent] = relationship(back_populates="responses")
    question: Mapped[Question] = relationship()


class EvidenceAsset(Base):
    __tablename__ = "evidence_assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ImprovementAction(Base):
    __tablename__ = "improvement_actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    outcome_code: Mapped[str] = mapped_column(String(64), nullable=False)
    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
