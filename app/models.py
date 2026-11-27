from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer,
    JSON, String, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)



class AcademicUnit(Base):
    __tablename__ = "academic_units"
    __table_args__ = (
        UniqueConstraint("code", name="uq_academic_unit_code"),
        CheckConstraint("unit_type IN ('institution','campus','faculty','vocational_school','institute','department','center')", name="ck_academic_unit_type"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("academic_units.id", ondelete="SET NULL"), nullable=True, index=True)
    external_source: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    parent: Mapped[Optional["AcademicUnit"]] = relationship(remote_side="AcademicUnit.id", back_populates="children")
    children: Mapped[list["AcademicUnit"]] = relationship(back_populates="parent")


class Program(Base):
    __tablename__ = "programs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    faculty: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    department: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    academic_unit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("academic_units.id", ondelete="SET NULL"), nullable=True, index=True)
    external_source: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    courses: Mapped[list["Course"]] = relationship(back_populates="program", cascade="all, delete-orphan")
    students: Mapped[list["Student"]] = relationship(back_populates="program", cascade="all, delete-orphan")
    program_outcomes: Mapped[list["ProgramOutcome"]] = relationship(back_populates="program", cascade="all, delete-orphan")
    academic_unit: Mapped[Optional[AcademicUnit]] = relationship()
    curriculum_versions: Mapped[list["CurriculumVersion"]] = relationship(back_populates="program", cascade="all, delete-orphan")
    catalog_items: Mapped[list["CourseCatalogItem"]] = relationship(back_populates="program", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("program_id", "code", "academic_year", "term", name="uq_course_offering"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    catalog_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("course_catalog_items.id", ondelete="SET NULL"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False)
    term: Mapped[str] = mapped_column(String(32), nullable=False)
    instructor_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    instructor_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    pass_threshold_percent: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    external_source: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    program: Mapped[Program] = relationship(back_populates="courses")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    learning_outcomes: Mapped[list["LearningOutcome"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    exams: Mapped[list["Exam"]] = relationship(back_populates="course", cascade="all, delete-orphan")



class CurriculumVersion(Base):
    __tablename__ = "curriculum_versions"
    __table_args__ = (
        UniqueConstraint("program_id", "code", name="uq_curriculum_version_program_code"),
        CheckConstraint("status IN ('draft','active','retired')", name="ck_curriculum_version_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    academic_year_start: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    academic_year_end: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False, index=True)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    decision_ref: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    program: Mapped[Program] = relationship(back_populates="curriculum_versions")
    curriculum_courses: Mapped[list["CurriculumCourse"]] = relationship(back_populates="curriculum_version", cascade="all, delete-orphan")


class CourseCatalogItem(Base):
    __tablename__ = "course_catalog_items"
    __table_args__ = (UniqueConstraint("program_id", "code", name="uq_course_catalog_program_code"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ects: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    local_credits: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    default_semester_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    course_type: Mapped[str] = mapped_column(String(32), default="required", nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    program: Mapped[Program] = relationship(back_populates="catalog_items")
    curriculum_links: Mapped[list["CurriculumCourse"]] = relationship(back_populates="catalog_item", cascade="all, delete-orphan")


class CurriculumCourse(Base):
    __tablename__ = "curriculum_courses"
    __table_args__ = (UniqueConstraint("curriculum_version_id", "catalog_item_id", name="uq_curriculum_catalog_item"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    curriculum_version_id: Mapped[int] = mapped_column(ForeignKey("curriculum_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    catalog_item_id: Mapped[int] = mapped_column(ForeignKey("course_catalog_items.id", ondelete="CASCADE"), nullable=False, index=True)
    semester_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    course_type: Mapped[str] = mapped_column(String(32), default="required", nullable=False)
    elective_group: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    ects_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    curriculum_version: Mapped[CurriculumVersion] = relationship(back_populates="curriculum_courses")
    catalog_item: Mapped[CourseCatalogItem] = relationship(back_populates="curriculum_links")



class CurriculumOutcomeMap(Base):
    __tablename__ = "curriculum_outcome_maps"
    __table_args__ = (
        UniqueConstraint("curriculum_version_id", "catalog_item_id", "program_outcome_id", name="uq_curriculum_course_po_map"),
        CheckConstraint("coverage_level IN ('I','R','M')", name="ck_curriculum_coverage_level"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    curriculum_version_id: Mapped[int] = mapped_column(ForeignKey("curriculum_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    catalog_item_id: Mapped[int] = mapped_column(ForeignKey("course_catalog_items.id", ondelete="CASCADE"), nullable=False, index=True)
    program_outcome_id: Mapped[int] = mapped_column(ForeignKey("program_outcomes.id", ondelete="CASCADE"), nullable=False, index=True)
    coverage_level: Mapped[str] = mapped_column(String(1), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CourseOffering(Base):
    __tablename__ = "course_offerings"
    __table_args__ = (
        UniqueConstraint("course_id", "section_code", name="uq_course_offering_section"),
        CheckConstraint("status IN ('planned','active','closed','archived')", name="ck_course_offering_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    catalog_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("course_catalog_items.id", ondelete="SET NULL"), nullable=True, index=True)
    curriculum_version_id: Mapped[Optional[int]] = mapped_column(ForeignKey("curriculum_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    section_code: Mapped[str] = mapped_column(String(32), default="A", nullable=False)
    campus: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    delivery_mode: Mapped[str] = mapped_column(String(32), default="face_to_face", nullable=False)
    language: Mapped[str] = mapped_column(String(32), default="TR", nullable=False)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    external_source: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TeachingAssignment(Base):
    __tablename__ = "teaching_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_offering_id: Mapped[int] = mapped_column(ForeignKey("course_offerings.id", ondelete="CASCADE"), nullable=False, index=True)
    app_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("app_users.id", ondelete="SET NULL"), nullable=True, index=True)
    instructor_email: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    instructor_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="lead", nullable=False)
    workload_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    student_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    class_name: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    external_source: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    anonymized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    program: Mapped[Program] = relationship(back_populates="students")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("course_id", "student_id", name="uq_course_student"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    course_offering_id: Mapped[Optional[int]] = mapped_column(ForeignKey("course_offerings.id", ondelete="SET NULL"), nullable=True, index=True)

    course: Mapped[Course] = relationship(back_populates="enrollments")
    student: Mapped[Student] = relationship(back_populates="enrollments")


class RubricTemplate(Base):
    __tablename__ = "rubric_templates"
    __table_args__ = (
        UniqueConstraint("course_id", "title", "version_no", name="uq_rubric_course_title_version"),
        CheckConstraint("status IN ('draft','active','retired')", name="ck_rubric_template_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False, index=True)
    max_points: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"
    __table_args__ = (UniqueConstraint("rubric_template_id", "code", name="uq_rubric_criterion_code"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rubric_template_id: Mapped[int] = mapped_column(ForeignKey("rubric_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    learning_outcome_id: Mapped[Optional[int]] = mapped_column(ForeignKey("learning_outcomes.id", ondelete="SET NULL"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_points: Mapped[float] = mapped_column(Float, nullable=False)
    weight_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class RubricLevel(Base):
    __tablename__ = "rubric_levels"
    __table_args__ = (UniqueConstraint("rubric_criterion_id", "code", name="uq_rubric_level_code"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rubric_criterion_id: Mapped[int] = mapped_column(ForeignKey("rubric_criteria.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    score_percent: Mapped[float] = mapped_column(Float, nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class AssessmentMeasure(Base):
    __tablename__ = "assessment_measures"
    __table_args__ = (
        UniqueConstraint("course_id", "code", name="uq_assessment_measure_course_code"),
        CheckConstraint("measure_type IN ('exam','assignment','project','presentation','laboratory','internship','portfolio','capstone','practical','peer_assessment')", name="ck_assessment_measure_type"),
        CheckConstraint("status IN ('draft','active','closed','archived')", name="ck_assessment_measure_status"),
        CheckConstraint("directness IN ('direct','indirect')", name="ck_assessment_measure_directness"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    course_offering_id: Mapped[Optional[int]] = mapped_column(ForeignKey("course_offerings.id", ondelete="SET NULL"), nullable=True, index=True)
    rubric_template_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rubric_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    measure_type: Mapped[str] = mapped_column(String(32), nullable=False)
    directness: Mapped[str] = mapped_column(String(16), default="direct", nullable=False)
    weight_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_points: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    target_percent: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class AssessmentMeasureOutcome(Base):
    __tablename__ = "assessment_measure_outcomes"
    __table_args__ = (UniqueConstraint("assessment_measure_id", "learning_outcome_id", name="uq_measure_learning_outcome"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_measure_id: Mapped[int] = mapped_column(ForeignKey("assessment_measures.id", ondelete="CASCADE"), nullable=False, index=True)
    learning_outcome_id: Mapped[int] = mapped_column(ForeignKey("learning_outcomes.id", ondelete="CASCADE"), nullable=False, index=True)
    weight_percent: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)


class AssessmentMeasureResult(Base):
    __tablename__ = "assessment_measure_results"
    __table_args__ = (UniqueConstraint("assessment_measure_id", "student_id", name="uq_measure_student_result"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_measure_id: Mapped[int] = mapped_column(ForeignKey("assessment_measures.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rubric_scores: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    graded_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class SurveyTemplate(Base):
    __tablename__ = "survey_templates"
    __table_args__ = (
        UniqueConstraint("program_id", "code", "version_no", name="uq_survey_program_code_version"),
        CheckConstraint("survey_type IN ('student','graduate','employer','external_stakeholder','faculty','course_evaluation','program_evaluation')", name="ck_survey_type"),
        CheckConstraint("status IN ('draft','active','retired')", name="ck_survey_template_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    survey_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    target_percent: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    anonymous: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class SurveyQuestion(Base):
    __tablename__ = "survey_questions"
    __table_args__ = (
        UniqueConstraint("survey_template_id", "code", name="uq_survey_question_code"),
        CheckConstraint("question_type IN ('likert','single_choice','multi_choice','open_text','nps')", name="ck_survey_question_type"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    survey_template_id: Mapped[int] = mapped_column(ForeignKey("survey_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(24), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    scale_min: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    scale_max: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    options: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    weight_percent: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    target_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class SurveyQuestionTarget(Base):
    __tablename__ = "survey_question_targets"
    __table_args__ = (
        UniqueConstraint("survey_question_id", "target_type", "program_outcome_id", "objective_id", "framework_family", "criterion_code", name="uq_survey_question_target"),
        CheckConstraint("target_type IN ('program_outcome','pea','quality_criterion')", name="ck_survey_question_target_type"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    survey_question_id: Mapped[int] = mapped_column(ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    program_outcome_id: Mapped[Optional[int]] = mapped_column(ForeignKey("program_outcomes.id", ondelete="CASCADE"), nullable=True, index=True)
    objective_id: Mapped[Optional[int]] = mapped_column(ForeignKey("program_educational_objectives.id", ondelete="CASCADE"), nullable=True, index=True)
    framework_family: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    criterion_code: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    weight_percent: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)


class SurveyCampaign(Base):
    __tablename__ = "survey_campaigns"
    __table_args__ = (
        UniqueConstraint("survey_template_id", "academic_year", "term", "code", name="uq_survey_campaign_template_period_code"),
        UniqueConstraint("public_token", name="uq_survey_campaign_public_token"),
        CheckConstraint("status IN ('draft','open','closed','archived')", name="ck_survey_campaign_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    survey_template_id: Mapped[int] = mapped_column(ForeignKey("survey_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    term: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    audience_type: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    public_token: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    __table_args__ = (
        UniqueConstraint("campaign_id", "response_key", name="uq_survey_campaign_response_key"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("survey_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    response_key: Mapped[str] = mapped_column(String(64), nullable=False)
    respondent_key_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    respondent_type: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    respondent_meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class SurveyAnswer(Base):
    __tablename__ = "survey_answers"
    __table_args__ = (
        UniqueConstraint("response_id", "question_id", name="uq_survey_response_question"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[int] = mapped_column(ForeignKey("survey_responses.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    numeric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    text_value: Mapped[str] = mapped_column(Text, default="", nullable=False)
    selected_options: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class AssessmentPlan(Base):
    __tablename__ = "assessment_plans"
    __table_args__ = (
        UniqueConstraint("program_id", "academic_year", "version_no", name="uq_assessment_plan_program_year_version"),
        CheckConstraint("status IN ('draft','active','reviewed','archived')", name="ck_assessment_plan_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    direct_weight: Mapped[float] = mapped_column(Float, default=70.0, nullable=False)
    indirect_weight: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    review_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class AssessmentPlanItem(Base):
    __tablename__ = "assessment_plan_items"
    __table_args__ = (
        CheckConstraint("channel IN ('direct','indirect')", name="ck_assessment_plan_item_channel"),
        CheckConstraint("source_type IN ('exam','assessment_measure','survey','manual')", name="ck_assessment_plan_item_source_type"),
        CheckConstraint("status IN ('planned','in_progress','collected','reviewed','cancelled')", name="ck_assessment_plan_item_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_plan_id: Mapped[int] = mapped_column(ForeignKey("assessment_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    program_outcome_id: Mapped[int] = mapped_column(ForeignKey("program_outcomes.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    method_label: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    term: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    frequency: Mapped[str] = mapped_column(String(64), default="annual", nullable=False)
    target_percent: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    evidence_required: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="planned", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class AssessmentPlanReview(Base):
    __tablename__ = "assessment_plan_reviews"
    __table_args__ = (
        UniqueConstraint("assessment_plan_id", "review_no", name="uq_assessment_plan_review_no"),
        CheckConstraint("status IN ('draft','final')", name="ck_assessment_plan_review_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_plan_id: Mapped[int] = mapped_column(ForeignKey("assessment_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    review_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="final", nullable=False, index=True)
    decision: Mapped[str] = mapped_column(Text, default="", nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


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
        CheckConstraint("contribution >= 1 AND contribution <= 5", name="ck_contribution_1_5"),
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
    course_offering_id: Mapped[Optional[int]] = mapped_column(ForeignKey("course_offerings.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(64), default="Sınav", nullable=False)
    exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    start_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    assessment_weight_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    booklet_count: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    staff_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    # Immutable-at-creation exam paper snapshots. These keep historical papers stable
    # even if the live course/program record is edited later.
    course_code_snapshot: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    course_name_snapshot: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    academic_year_snapshot: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    term_snapshot: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    instructor_snapshot: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    program_name_snapshot: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    department_snapshot: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    faculty_snapshot: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    paper_template_version: Mapped[str] = mapped_column(String(64), default="dou-official-v2", nullable=False)
    paper_size: Mapped[str] = mapped_column(String(8), default="A4", nullable=False)
    paper_orientation: Mapped[str] = mapped_column(String(16), default="portrait", nullable=False)
    omr_mode: Mapped[str] = mapped_column(String(16), default="embedded", nullable=False)
    duplex_print: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    created_by_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approval_requested_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approval_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    grade_locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    grade_locked_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    grade_lock_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
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
    mapped_questions: Mapped[list["Question"]] = relationship(secondary="question_outcomes", viewonly=True)


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
    __table_args__ = (UniqueConstraint("exam_learning_outcome_id", "exam_program_outcome_id", name="uq_exam_lo_po"), CheckConstraint("contribution >= 1 AND contribution <= 5", name="ck_exam_contribution_1_5"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_learning_outcome_id: Mapped[int] = mapped_column(ForeignKey("exam_learning_outcomes.id", ondelete="CASCADE"), nullable=False)
    exam_program_outcome_id: Mapped[int] = mapped_column(ForeignKey("exam_program_outcomes.id", ondelete="CASCADE"), nullable=False)
    contribution: Mapped[int] = mapped_column(Integer, nullable=False)

    learning_outcome: Mapped[ExamLearningOutcome] = relationship(back_populates="mappings")
    program_outcome: Mapped[ExamProgramOutcome] = relationship(back_populates="mappings")


class QuestionBankOutcome(Base):
    __tablename__ = "question_bank_outcomes"
    __table_args__ = (UniqueConstraint("question_bank_id", "learning_outcome_id", name="uq_question_bank_outcome"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_bank_id: Mapped[int] = mapped_column(ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False, index=True)
    learning_outcome_id: Mapped[int] = mapped_column(ForeignKey("learning_outcomes.id", ondelete="CASCADE"), nullable=False, index=True)

    question_bank: Mapped["QuestionBank"] = relationship(back_populates="outcome_links")
    learning_outcome: Mapped[LearningOutcome] = relationship()


class QuestionBank(Base):
    __tablename__ = "question_bank"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    default_points: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    correct_answer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    choices: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    learning_outcome_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    topic: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    unit: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    bloom_level: Mapped[str] = mapped_column(String(64), default="understand", nullable=False)
    author: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    image_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rubric: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    expected_answer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    answer_lines: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    review_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    difficulty_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    discrimination_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    distractor_efficiency: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    psychometric_sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), default="unmeasured", nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    outcome_links: Mapped[list["QuestionBankOutcome"]] = relationship(back_populates="question_bank", cascade="all, delete-orphan")
    learning_outcomes: Mapped[list[LearningOutcome]] = relationship(secondary="question_bank_outcomes", viewonly=True)


class AssessmentBlueprint(Base):
    __tablename__ = "assessment_blueprints"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_type: Mapped[str] = mapped_column(String(64), nullable=False, default="Sınav")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", index=True)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    total_points: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    approved_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    items: Mapped[list["AssessmentBlueprintItem"]] = relationship(back_populates="blueprint", cascade="all, delete-orphan")


class AssessmentBlueprintItem(Base):
    __tablename__ = "assessment_blueprint_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    blueprint_id: Mapped[int] = mapped_column(ForeignKey("assessment_blueprints.id", ondelete="CASCADE"), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    learning_outcome_code: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    bloom_level: Mapped[str] = mapped_column(String(64), nullable=False, default="understand")
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    points: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    weight_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    blueprint: Mapped[AssessmentBlueprint] = relationship(back_populates="items")


class QuestionOutcome(Base):
    __tablename__ = "question_outcomes"
    __table_args__ = (UniqueConstraint("question_id", "exam_learning_outcome_id", name="uq_question_exam_outcome"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_learning_outcome_id: Mapped[int] = mapped_column(ForeignKey("exam_learning_outcomes.id", ondelete="CASCADE"), nullable=False, index=True)

    question: Mapped["Question"] = relationship(back_populates="outcome_links")
    learning_outcome: Mapped[ExamLearningOutcome] = relationship()


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
    answer_lines: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    exam_learning_outcome_id: Mapped[Optional[int]] = mapped_column(ForeignKey("exam_learning_outcomes.id", ondelete="SET NULL"), nullable=True)
    bank_question_id: Mapped[Optional[int]] = mapped_column(ForeignKey("question_bank.id", ondelete="SET NULL"), nullable=True, index=True)
    topic: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    unit: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    bloom_level: Mapped[str] = mapped_column(String(64), default="understand", nullable=False)
    image_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rubric: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    expected_answer: Mapped[str] = mapped_column(Text, default="", nullable=False)

    exam: Mapped[Exam] = relationship(back_populates="questions")
    learning_outcome: Mapped[Optional[ExamLearningOutcome]] = relationship(back_populates="questions")
    outcome_links: Mapped[list["QuestionOutcome"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    learning_outcomes: Mapped[list[ExamLearningOutcome]] = relationship(secondary="question_outcomes", viewonly=True)


class ExamStudent(Base):
    __tablename__ = "exam_students"
    __table_args__ = (UniqueConstraint("exam_id", "student_id", name="uq_exam_student"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_status: Mapped[str] = mapped_column(String(24), default="attended", nullable=False, index=True)
    attendance_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attendance_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    rubric_scores: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    graded_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revision_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

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
    integrity_status: Mapped[str] = mapped_column(String(16), default="unchecked", nullable=False, index=True)
    integrity_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retention_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
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
    baseline_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    verification_method: Mapped[str] = mapped_column(Text, default="", nullable=False)
    effectiveness_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    verified_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closure_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ExamIncident(Base):
    __tablename__ = "exam_incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    incident_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), default="warning", nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="open", nullable=False, index=True)
    resolution_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resolved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class GradeAppeal(Base):
    __tablename__ = "grade_appeals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[Optional[int]] = mapped_column(ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="open", nullable=False, index=True)
    old_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    new_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    old_rubric_scores: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    new_rubric_scores: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    decision_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    decided_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ResponseGradeRevision(Base):
    """Immutable before/after trail for every change to an already-graded
    Response.awarded_points/rubric_scores, across every pathway that can
    change a grade (manual entry, OMR, answer-key regrade, Excel import,
    appeal resolution). Written once per change; never updated or deleted."""
    __tablename__ = "response_grade_revisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[int] = mapped_column(ForeignKey("responses.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_student_id: Mapped[int] = mapped_column(ForeignKey("exam_students.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_awarded_points: Mapped[float] = mapped_column(Float, nullable=False)
    new_awarded_points: Mapped[float] = mapped_column(Float, nullable=False)
    previous_rubric_scores: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    new_rubric_scores: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    changed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class AcademicPeriod(Base):
    __tablename__ = "academic_periods"
    __table_args__ = (
        UniqueConstraint("academic_year", "term", name="uq_academic_period_year_term"),
        CheckConstraint("status IN ('planned','active','locked','archived')", name="ck_academic_period_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    term: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False, index=True)
    starts_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ends_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class IntegrationSyncRun(Base):
    __tablename__ = "integration_sync_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), default="obs-workbook", nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), default="full", nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AppUser(Base):
    __tablename__ = "app_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_object_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    auth_source: Mapped[str] = mapped_column(String(32), default="pilot", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignments"
    __table_args__ = (
        CheckConstraint("role IN ('admin','quality','instructor','program_head','department_head','faculty_admin')", name="ck_user_role_valid"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    program_id: Mapped[Optional[int]] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=True, index=True)
    course_id: Mapped[Optional[int]] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True)
    scope_faculty: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    scope_department: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    scope_program: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    actor_email: Mapped[str] = mapped_column(String(255), default="system", nullable=False)
    actor_roles: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class SecurityEvent(Base):
    __tablename__ = "security_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), default="info", nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String(96), default="", nullable=False, index=True)
    actor_email: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    remote_addr: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    method: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    path: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class ScanSession(Base):
    __tablename__ = "scan_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="processing", nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    support_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ScanItem(Base):
    __tablename__ = "scan_items"
    __table_args__ = (UniqueConstraint("exam_id", "page_fingerprint", name="uq_exam_scan_fingerprint"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("scan_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    booklet: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    student_no_detected: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    page_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    answers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    diagnostics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    issue_summary: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    preview_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page_kind: Mapped[str] = mapped_column(String(32), default="omr", nullable=False)
    logical_page_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    question_numbers: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ScanReview(Base):
    __tablename__ = "scan_reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_item_id: Mapped[int] = mapped_column(ForeignKey("scan_items.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    resolved_answers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AnswerKeyRevision(Base):
    __tablename__ = "answer_key_revisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    corrections: Mapped[dict] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    affected_responses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AccreditationProfile(Base):
    __tablename__ = "accreditation_profiles"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_accreditation_profile_version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    required_general_evidence_kinds: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    required_representative_evidence_kinds: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    requires_representatives: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_improvement_for_gaps: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AccreditationPeriod(Base):
    __tablename__ = "accreditation_periods"
    __table_args__ = (
        UniqueConstraint("program_id", "profile_id", "academic_year", "term", name="uq_accreditation_period"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("accreditation_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False)
    term: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="collecting", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AccreditationPeriodExam(Base):
    __tablename__ = "accreditation_period_exams"
    __table_args__ = (UniqueConstraint("period_id", "exam_id", name="uq_accreditation_period_exam"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("accreditation_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RepresentativeSnapshot(Base):
    __tablename__ = "representative_snapshots"
    __table_args__ = (UniqueConstraint("exam_id", "slot", name="uq_exam_representative_slot"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    slot: Mapped[str] = mapped_column(String(8), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_no: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    class_average: Mapped[float] = mapped_column(Float, nullable=False)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PilotUATRun(Base):
    __tablename__ = "pilot_uat_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    checks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), default="system", nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class PilotFeedback(Base):
    __tablename__ = "pilot_feedback"
    __table_args__ = (
        CheckConstraint("status IN ('open','reviewed','resolved')", name="ck_pilot_feedback_status"),
        CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_pilot_feedback_rating"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(64), default="general", nullable=False, index=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role_names: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    resolution_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


# ---------------------------------------------------------------------------
# 6.20 Quality & Accreditation 360
# ---------------------------------------------------------------------------

class QualityFrameworkProfile(Base):
    __tablename__ = "quality_framework_profiles"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_quality_framework_profile_version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    framework_family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    effective_from_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transition_from_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    criteria: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class QualityFrameworkAssignment(Base):
    __tablename__ = "quality_framework_assignments"
    __table_args__ = (
        UniqueConstraint("program_id", "framework_profile_id", name="uq_quality_framework_assignment_program_profile"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    framework_profile_id: Mapped[int] = mapped_column(ForeignKey("quality_framework_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), default="auto", nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CurriculumItem(Base):
    __tablename__ = "quality_curriculum_items"
    __table_args__ = (
        UniqueConstraint("program_id", "academic_year", "course_code", name="uq_quality_curriculum_program_year_course"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    term: Mapped[str] = mapped_column(String(32), nullable=False)
    class_level: Mapped[str] = mapped_column(String(32), default="1. Sınıf", nullable=False)
    course_code: Mapped[str] = mapped_column(String(64), nullable=False)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ects: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    course_category: Mapped[str] = mapped_column(String(96), default="Genel / Zorunlu", nullable=False)
    is_professional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_program_specific: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_external_stakeholder_supported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_applied_or_current_tech: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), default="implemented", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class StakeholderRecord(Base):
    __tablename__ = "quality_stakeholders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    stakeholder_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    engagement_type: Mapped[str] = mapped_column(String(96), default="Görüş / Geri Bildirim", nullable=False)
    engagement_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resulting_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), default="implemented", nullable=False)
    evidence_ref: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class GraduateRecord(Base):
    __tablename__ = "quality_graduates"
    __table_args__ = (
        UniqueConstraint("program_id", "graduate_key", name="uq_quality_graduate_program_key"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    graduate_key: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    employment_status: Mapped[str] = mapped_column(String(64), default="Bilinmiyor", nullable=False, index=True)
    employer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    sector: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    related_field: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    survey_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FacultyRecord(Base):
    __tablename__ = "quality_faculty"
    __table_args__ = (
        UniqueConstraint("program_id", "email", name="uq_quality_faculty_program_email"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(64), default="Tam Zamanlı", nullable=False)
    expertise: Mapped[str] = mapped_column(Text, default="", nullable=False)
    highest_degree: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    industry_experience_years: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    weekly_course_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), default="implemented", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class InfrastructureRecord(Base):
    __tablename__ = "quality_infrastructure"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    infrastructure_type: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quality_status: Mapped[str] = mapped_column(String(32), default="implemented", nullable=False)
    accessibility_status: Mapped[str] = mapped_column(String(32), default="implemented", nullable=False)
    isg_status: Mapped[str] = mapped_column(String(32), default="implemented", nullable=False)
    last_review_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class QualityCycle(Base):
    __tablename__ = "quality_cycles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    criterion_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    do_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    check_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    act_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False, index=True)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class GovernanceDecision(Base):
    __tablename__ = "quality_governance_decisions"
    __table_args__ = (
        UniqueConstraint("program_id", "meeting_no", "decision_no", name="uq_quality_governance_decision"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    body_type: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    meeting_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    meeting_no: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_no: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    decision_text: Mapped[str] = mapped_column(Text, nullable=False)
    related_criterion: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    source_stakeholder_id: Mapped[Optional[int]] = mapped_column(ForeignKey("quality_stakeholders.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="implemented", nullable=False)
    evidence_ref: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class QualityCalendarEvent(Base):
    __tablename__ = "quality_calendar_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    owner_role: Mapped[str] = mapped_column(String(96), default="", nullable=False)
    criterion_code: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False, index=True)
    evidence_required: Mapped[str] = mapped_column(Text, default="", nullable=False)
    related_entity_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    related_entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class QualityCriterionAssessment(Base):
    __tablename__ = "quality_criterion_assessments"
    __table_args__ = (
        UniqueConstraint("program_id", "framework_profile_id", "academic_year", "criterion_code", name="uq_quality_criterion_assessment"),
        CheckConstraint("maturity_level >= 1 AND maturity_level <= 5", name="ck_quality_maturity_1_5"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    framework_profile_id: Mapped[int] = mapped_column(ForeignKey("quality_framework_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    criterion_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    maturity_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class QualityEvidenceAsset(Base):
    __tablename__ = "quality_evidence_assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_code: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), default="program", nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kind: Mapped[str] = mapped_column(String(64), default="document", nullable=False)
    category: Mapped[str] = mapped_column(String(96), default="quality", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream", nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    integrity_status: Mapped[str] = mapped_column(String(16), default="unchecked", nullable=False, index=True)
    integrity_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retention_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# ---------------------------------------------------------------------------
# 6.36 Strategic Quality Management
# ---------------------------------------------------------------------------
class StrategicObjective(Base):
    __tablename__ = "quality_strategic_objectives"
    __table_args__ = (UniqueConstraint("academic_year", "scope_type", "scope_name", "code", name="uq_quality_strategy_objective_scope_code"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(32), default="university", nullable=False, index=True)
    scope_name: Mapped[str] = mapped_column(String(255), default="Doğuş Üniversitesi", nullable=False, index=True)
    program_id: Mapped[Optional[int]] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class StrategicKPI(Base):
    __tablename__ = "quality_strategic_kpis"
    __table_args__ = (UniqueConstraint("objective_id", "code", name="uq_quality_strategy_kpi_objective_code"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    objective_id: Mapped[int] = mapped_column(ForeignKey("quality_strategic_objectives.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), default="%", nullable=False)
    baseline_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    target_value: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    actual_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), default="higher", nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), default="manual", nullable=False, index=True)
    source_ref: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

# ---------------------------------------------------------------------------
# 6.41 Accreditation Compliance Core
# ---------------------------------------------------------------------------

class QualityFrameworkSnapshot(Base):
    __tablename__ = "quality_framework_snapshots"
    __table_args__ = (
        UniqueConstraint("program_id", "academic_year", "framework_profile_id", name="uq_quality_framework_snapshot"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    framework_profile_id: Mapped[int] = mapped_column(ForeignKey("quality_framework_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    framework_code: Mapped[str] = mapped_column(String(96), nullable=False)
    framework_version: Mapped[str] = mapped_column(String(64), nullable=False)
    framework_family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    criteria: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    frozen_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProgramEducationalObjective(Base):
    __tablename__ = "program_educational_objectives"
    __table_args__ = (
        UniqueConstraint("program_id", "academic_year", "code", name="uq_program_educational_objective"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    stakeholder_basis: Mapped[str] = mapped_column(Text, default="", nullable=False)
    mission_alignment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    review_cycle_years: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    target_indicator: Mapped[str] = mapped_column(Text, default="", nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), default="implemented", nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProgramEducationalObjectiveOutcomeMap(Base):
    __tablename__ = "program_educational_objective_outcome_maps"
    __table_args__ = (
        UniqueConstraint("objective_id", "program_outcome_id", name="uq_pea_po_map"),
        CheckConstraint("contribution >= 1 AND contribution <= 5", name="ck_pea_po_contribution_1_5"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    objective_id: Mapped[int] = mapped_column(ForeignKey("program_educational_objectives.id", ondelete="CASCADE"), nullable=False, index=True)
    program_outcome_id: Mapped[int] = mapped_column(ForeignKey("program_outcomes.id", ondelete="CASCADE"), nullable=False, index=True)
    contribution: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ProgramOutcomeComponent(Base):
    __tablename__ = "program_outcome_components"
    __table_args__ = (
        UniqueConstraint("program_outcome_id", "code", name="uq_program_outcome_component"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_outcome_id: Mapped[int] = mapped_column(ForeignKey("program_outcomes.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(96), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    component_type: Mapped[str] = mapped_column(String(64), default="knowledge-skill-competency", nullable=False)
    framework_family: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    framework_version: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    framework_component_code: Mapped[str] = mapped_column(String(96), default="", nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class StudentOutcomeSnapshot(Base):
    __tablename__ = "student_outcome_snapshots"
    __table_args__ = (
        UniqueConstraint("student_id", "academic_year", "snapshot_type", "version_no", name="uq_student_outcome_snapshot_version"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(32), default="progress", nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    frozen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    frozen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AccreditationApplication(Base):
    __tablename__ = "quality_accreditation_applications"
    __table_args__ = (
        UniqueConstraint("program_id", "framework_profile_id", "academic_year", "application_type", name="uq_quality_accreditation_application"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    framework_profile_id: Mapped[int] = mapped_column(ForeignKey("quality_framework_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    framework_snapshot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("quality_framework_snapshots.id", ondelete="SET NULL"), nullable=True, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    application_type: Mapped[str] = mapped_column(String(48), default="general", nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(48), default="preparation", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    application_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    self_evaluation_due: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    correction_due: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    visit_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    decision_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    previous_application_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    evaluation_mode: Mapped[str] = mapped_column(String(32), default="site_visit", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EvaluatorWorkspace(Base):
    __tablename__ = "quality_evaluator_workspaces"
    __table_args__ = (
        UniqueConstraint("application_id", "evaluator_email", name="uq_evaluator_workspace_application_email"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("quality_accreditation_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluator_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    evaluator_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    access_mode: Mapped[str] = mapped_column(String(32), default="read_only", nullable=False)
    snapshot_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    invitation_token_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    token_issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_access_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AccreditationDocumentRequest(Base):
    __tablename__ = "quality_accreditation_document_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("quality_accreditation_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_code: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requested_by: Mapped[str] = mapped_column(String(255), default="Evaluator", nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    response_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AccreditationFinding(Base):
    __tablename__ = "quality_accreditation_findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("quality_accreditation_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    source_finding_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    criterion_code: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    finding_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    response_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    carried_forward: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AccreditationFindingRevision(Base):
    __tablename__ = "quality_accreditation_finding_revisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("quality_accreditation_findings.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("quality_accreditation_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(48), default="updated", nullable=False, index=True)
    before_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    after_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actor: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AccreditationFinalReport(Base):
    __tablename__ = "quality_accreditation_final_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("quality_accreditation_applications.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    team_opinion: Mapped[str] = mapped_column(Text, default="", nullable=False)
    institution_response_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    final_decision_code: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    accreditation_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    accreditation_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    accreditation_term_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    next_review_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    next_review_due: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    decision_basis: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    institution_report_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    criterion_results: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    snapshot_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    snapshot_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    frozen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AccreditationDecisionHistory(Base):
    __tablename__ = "quality_accreditation_decision_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("quality_accreditation_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    from_stage: Mapped[str] = mapped_column(String(48), default="", nullable=False)
    to_stage: Mapped[str] = mapped_column(String(48), default="", nullable=False)
    decision_code: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    actor: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AccreditationVisitNote(Base):
    __tablename__ = "quality_accreditation_visit_notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("quality_accreditation_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_code: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    note_type: Mapped[str] = mapped_column(String(32), default="observation", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="internal", nullable=False, index=True)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MedekEvaluatorReportItem(Base):
    __tablename__ = "quality_medek_evaluator_report_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("quality_accreditation_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[Optional[int]] = mapped_column(ForeignKey("quality_evaluator_workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    source_item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    report_phase: Mapped[str] = mapped_column(String(32), default="individual", nullable=False, index=True)
    criterion_code: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    evaluator_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    narrative: Mapped[str] = mapped_column(Text, default="", nullable=False)
    assessment_value: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    carried_forward: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MedekPdrFormAnalysis(Base):
    __tablename__ = "quality_medek_pdr_form_analyses"
    __table_args__ = (
        UniqueConstraint("application_id", "form_code", "subject_ref", name="uq_medek_pdr_form_application_subject"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("quality_accreditation_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    form_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(128), default="program", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    analysis_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[str] = mapped_column(String(32), default="review", nullable=False, index=True)
    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ControlledDocument(Base):
    __tablename__ = "quality_controlled_documents"
    __table_args__ = (
        UniqueConstraint("document_code", name="uq_quality_controlled_document_code"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[Optional[int]] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=True, index=True)
    document_code: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    retention_years: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ControlledDocumentRevision(Base):
    __tablename__ = "quality_controlled_document_revisions"
    __table_args__ = (
        UniqueConstraint("document_id", "revision_no", name="uq_quality_controlled_document_revision"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("quality_controlled_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    review_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    change_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), default="text/plain", nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    integrity_status: Mapped[str] = mapped_column(String(16), default="unchecked", nullable=False, index=True)
    integrity_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    prepared_by: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class QualityBudgetPlan(Base):
    __tablename__ = "quality_budget_plans"
    __table_args__ = (
        UniqueConstraint("program_id", "academic_year", name="uq_quality_budget_plan_program_year"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), default="TRY", nullable=False)
    allocated_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    spent_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), default="implemented", nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class QualityBudgetLine(Base):
    __tablename__ = "quality_budget_lines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    budget_plan_id: Mapped[int] = mapped_column(ForeignKey("quality_budget_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    planned_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    actual_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    funding_source: Mapped[str] = mapped_column(String(128), default="Kurum", nullable=False)
    criterion_code: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class FacultyCVRevision(Base):
    __tablename__ = "quality_faculty_cv_revisions"
    __table_args__ = (
        UniqueConstraint("faculty_record_id", "format_type", "version_no", name="uq_quality_faculty_cv_revision"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    faculty_record_id: Mapped[int] = mapped_column(ForeignKey("quality_faculty.id", ondelete="CASCADE"), nullable=False, index=True)
    format_type: Mapped[str] = mapped_column(String(32), default="YOKSIS-UAK", nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    cv_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FacultyWorkloadRecord(Base):
    __tablename__ = "quality_faculty_workload_records"
    __table_args__ = (
        UniqueConstraint("faculty_record_id", "academic_year", "term", "course_code", "workload_type", name="uq_quality_faculty_workload"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    faculty_record_id: Mapped[int] = mapped_column(ForeignKey("quality_faculty.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    term: Mapped[str] = mapped_column(String(32), nullable=False)
    course_code: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    workload_type: Mapped[str] = mapped_column(String(64), default="course", nullable=False)
    weekly_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="manual", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class GraduateFollowup(Base):
    __tablename__ = "quality_graduate_followups"
    __table_args__ = (
        UniqueConstraint("graduate_record_id", "followup_year", name="uq_quality_graduate_followup_year"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    graduate_record_id: Mapped[int] = mapped_column(ForeignKey("quality_graduates.id", ondelete="CASCADE"), nullable=False, index=True)
    followup_year: Mapped[int] = mapped_column(Integer, nullable=False)
    survey_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    employment_status: Mapped[str] = mapped_column(String(64), default="Bilinmiyor", nullable=False)
    employer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    related_field: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    satisfaction_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    employer_feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resulting_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class InfrastructureMaintenance(Base):
    __tablename__ = "quality_infrastructure_maintenance"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    infrastructure_id: Mapped[int] = mapped_column(ForeignKey("quality_infrastructure.id", ondelete="CASCADE"), nullable=False, index=True)
    maintenance_type: Mapped[str] = mapped_column(String(64), default="periodic", nullable=False)
    planned_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    completed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class MissionActivity(Base):
    __tablename__ = "quality_mission_activities"
    __table_args__ = (
        UniqueConstraint("academic_year", "domain", "scope_type", "scope_name", "code", name="uq_quality_mission_activity"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[Optional[int]] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=True, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(32), default="university", nullable=False)
    scope_name: Mapped[str] = mapped_column(String(255), default="Doğuş Üniversitesi", nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(96), default="activity", nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    partner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    country: Mapped[str] = mapped_column(String(96), default="", nullable=False)
    participants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    budget_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    target_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False, index=True)
    outcome_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AccreditationReportTemplate(Base):
    __tablename__ = "quality_accreditation_report_templates"
    __table_args__ = (
        UniqueConstraint("framework_family", "report_type", "version", name="uq_accreditation_report_template"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    framework_family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    sections: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    folder_layout: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream", nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

# ---------------------------------------------------------------------------
# 6.63 Institutional Accreditation Readiness
# ---------------------------------------------------------------------------

class AccreditationCrosswalk(Base):
    __tablename__ = "quality_accreditation_crosswalks"
    __table_args__ = (
        UniqueConstraint(
            "source_framework_family", "source_framework_version", "source_criterion_code",
            "target_framework_family", "target_framework_version", "target_criterion_code",
            name="uq_quality_accreditation_crosswalk_pair",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_framework_family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_framework_version: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    source_criterion_code: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    target_framework_family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_framework_version: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    target_criterion_code: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    relationship: Mapped[str] = mapped_column(String(24), default="supports", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    review_status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class InstitutionalReadinessSnapshot(Base):
    __tablename__ = "quality_institutional_readiness_snapshots"
    __table_args__ = (
        UniqueConstraint("academic_year", "scope_type", "scope_key", "snapshot_no", name="uq_quality_readiness_snapshot"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(24), default="institution", nullable=False, index=True)
    scope_key: Mapped[str] = mapped_column(String(255), default="DOGUS", nullable=False, index=True)
    snapshot_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    frozen_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

# ---------------------------------------------------------------------------
# 6.66 Production / Institution Acceptance Gate
# ---------------------------------------------------------------------------

class InstitutionAcceptanceRecord(Base):
    __tablename__ = "institution_acceptance_records"
    __table_args__ = (
        UniqueConstraint("environment", "gate_key", name="uq_institution_acceptance_gate"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    environment: Mapped[str] = mapped_column(String(32), default="production", nullable=False, index=True)
    gate_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False, index=True)
    evidence_ref: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    verified_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

# ---------------------------------------------------------------------------
# 6.68 Operations & Automation
# ---------------------------------------------------------------------------

class OperationalJob(Base):
    __tablename__ = "operational_jobs"
    __table_args__ = (
        CheckConstraint("status IN ('queued','running','succeeded','failed','cancelled')", name="ck_operational_job_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    run_after: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    locked_by: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), default="system", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class OperationalNotification(Base):
    __tablename__ = "operational_notifications"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_operational_notification_dedupe"),
        CheckConstraint("status IN ('unread','read','archived')", name="ck_operational_notification_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_email: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    role_scope: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    program_id: Mapped[Optional[int]] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=True, index=True)
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), default="info", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    action_url: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    source_entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="unread", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

# ---------------------------------------------------------------------------
# 6.69 Program Review & Evidence Hub 2.0
# ---------------------------------------------------------------------------

class ProgramReviewTemplate(Base):
    __tablename__ = "program_review_templates"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_program_review_template_code_version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sections: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProgramReview(Base):
    __tablename__ = "program_reviews"
    __table_args__ = (
        UniqueConstraint("program_id", "academic_year", "review_no", name="uq_program_review_cycle"),
        CheckConstraint("status IN ('draft','in_progress','review','final','archived')", name="ck_program_review_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("program_review_templates.id", ondelete="RESTRICT"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    review_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False, index=True)
    final_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    final_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    finalized_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProgramReviewSection(Base):
    __tablename__ = "program_review_sections"
    __table_args__ = (
        UniqueConstraint("review_id", "section_key", name="uq_program_review_section"),
        CheckConstraint("status IN ('not_started','in_progress','submitted','approved','changes_requested')", name="ck_program_review_section_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("program_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    section_key: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    guidance: Mapped[str] = mapped_column(Text, default="", nullable=False)
    narrative: Mapped[str] = mapped_column(Text, default="", nullable=False)
    contributor_email: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    reviewer_email: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="not_started", nullable=False, index=True)
    reviewer_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProgramReviewEvidenceLink(Base):
    __tablename__ = "program_review_evidence_links"
    __table_args__ = (
        UniqueConstraint("section_id", "source_type", "source_id", name="uq_program_review_evidence_link"),
        CheckConstraint("source_type IN ('exam','quality','controlled')", name="ck_program_review_evidence_source"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("program_review_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    added_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EvidenceTag(Base):
    __tablename__ = "evidence_tags"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", "tag_key", name="uq_evidence_tag_source_key"),
        CheckConstraint("source_type IN ('exam','quality','controlled')", name="ck_evidence_tag_source"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tag_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tag_label: Mapped[str] = mapped_column(String(96), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
