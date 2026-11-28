from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ObsLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=255)
    donem_id: str | None = None


class ProgramCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    faculty: str = ""
    department: str = ""
    academic_unit_id: Optional[int] = None


class ProgramOut(ORMModel):
    id: int
    code: str
    name: str
    faculty: str
    department: str
    academic_unit_id: Optional[int] = None


class CourseCreate(BaseModel):
    program_id: int
    catalog_item_id: Optional[int] = None
    code: str
    name: str
    academic_year: str
    term: str
    instructor_email: str = ""
    instructor_name: str = ""
    pass_threshold_percent: float = Field(default=50, ge=0, le=100)


class CourseOut(ORMModel):
    id: int
    program_id: int
    catalog_item_id: Optional[int] = None
    code: str
    name: str
    academic_year: str
    term: str
    instructor_email: str
    instructor_name: str
    pass_threshold_percent: float


class StudentCreate(BaseModel):
    program_id: int
    student_no: str
    full_name: str
    class_name: str = ""


class StudentOut(ORMModel):
    id: int
    program_id: int
    student_no: str
    full_name: str
    class_name: str
    anonymized_at: Optional[datetime] = None


class StudentAnonymizeRequest(BaseModel):
    confirm: bool = False
    reason: str = Field(default="KVKK saklama süresi / veri sahibi talebi", max_length=500)


class LearningOutcomeCreate(BaseModel):
    code: str
    description: str
    target_percent: float = Field(default=60, ge=0, le=100)


class ProgramOutcomeCreate(BaseModel):
    academic_year: str
    code: str
    description: str


class LearningOutcomeUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, min_length=1)
    target_percent: Optional[float] = Field(default=None, ge=0, le=100)


class ProgramOutcomeUpdate(BaseModel):
    academic_year: Optional[str] = Field(default=None, min_length=1, max_length=32)
    code: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, min_length=1)


class OutcomeMappingCreate(BaseModel):
    learning_outcome_id: int
    program_outcome_id: int
    contribution: int = Field(ge=1, le=5)


class OutcomeMappingBulkItem(BaseModel):
    learning_outcome_id: int
    program_outcome_id: int
    contribution: Optional[int] = Field(default=None, ge=1, le=5)  # None = eşleşmeyi kaldır


class OutcomeMappingBulk(BaseModel):
    items: list[OutcomeMappingBulkItem] = Field(min_length=1, max_length=500)


class ExamCreate(BaseModel):
    course_id: int
    title: str = Field(min_length=1, max_length=255)
    exam_type: str = Field(default="Sınav", min_length=1, max_length=64)
    exam_date: Optional[date] = None
    start_time: Optional[str] = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    location: str = Field(default="", max_length=255)
    duration_minutes: int = Field(default=50, ge=1, le=600)
    assessment_weight_percent: Optional[float] = Field(default=None, ge=0, le=100)
    booklet_count: Literal[1, 2, 4] = 4
    instructions: str = Field(default="", max_length=8000)
    staff_notes: str = Field(default="", max_length=8000)
    paper_size: Literal["A3", "A4", "A5"] = "A4"
    paper_orientation: Literal["portrait", "landscape"] = "portrait"
    omr_mode: Literal["embedded", "separate"] = "embedded"
    duplex_print: bool = False
    sync_students: bool = True


class ExamDuplicateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    exam_date: Optional[date] = None
    start_time: Optional[str] = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    location: Optional[str] = Field(default=None, max_length=255)


class QuestionCreate(BaseModel):
    order_no: int = Field(ge=1)
    question_type: Literal["mcq", "classic"]
    text: str
    points: float = Field(gt=0, le=100)
    correct_answer: Optional[str] = None
    choices: Optional[dict] = None
    answer_lines: int = Field(default=8, ge=1, le=40)
    learning_outcome_code: Optional[str] = None
    learning_outcome_codes: list[str] = Field(default_factory=list, max_length=20)
    topic: str = Field(default="", max_length=255)
    unit: str = Field(default="", max_length=255)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"] = "understand"
    image_data: Optional[str] = None
    rubric: Optional[dict[str, Any]] = None
    expected_answer: str = Field(default="", max_length=8000)


class ResponseItem(BaseModel):
    question_id: int
    answer_text: Optional[str] = None
    awarded_points: Optional[float] = None
    rubric_scores: Optional[dict[str, float]] = None


class ResponsesSubmit(BaseModel):
    responses: list[ResponseItem]


class ImprovementCreate(BaseModel):
    outcome_code: str
    action_text: str
    owner: str = ""
    due_date: Optional[date] = None
    status: Literal["open", "in_progress", "done", "cancelled"] = "open"
    baseline_percent: Optional[float] = Field(default=None, ge=0, le=100)
    target_percent: Optional[float] = Field(default=None, ge=0, le=100)
    actual_percent: Optional[float] = Field(default=None, ge=0, le=100)
    verification_method: str = Field(default="", max_length=4000)
    effectiveness_status: Literal["pending", "effective", "partially_effective", "ineffective"] = "pending"
    closure_note: str = Field(default="", max_length=4000)


class BulkEnrollRequest(BaseModel):
    student_ids: list[int]


class ProgramUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=64)
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    faculty: Optional[str] = None
    department: Optional[str] = None
    academic_unit_id: Optional[int] = None


class CourseUpdate(BaseModel):
    catalog_item_id: Optional[int] = None
    code: Optional[str] = None
    name: Optional[str] = None
    academic_year: Optional[str] = None
    term: Optional[str] = None
    instructor_email: Optional[str] = None
    instructor_name: Optional[str] = None
    pass_threshold_percent: Optional[float] = Field(default=None, ge=0, le=100)


class StudentUpdate(BaseModel):
    student_no: Optional[str] = None
    full_name: Optional[str] = None
    class_name: Optional[str] = None


class ExamUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    exam_type: Optional[str] = Field(default=None, min_length=1, max_length=64)
    exam_date: Optional[date] = None
    start_time: Optional[str] = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    location: Optional[str] = Field(default=None, max_length=255)
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    assessment_weight_percent: Optional[float] = Field(default=None, ge=0, le=100)
    booklet_count: Optional[Literal[1, 2, 4]] = None
    instructions: Optional[str] = Field(default=None, max_length=8000)
    staff_notes: Optional[str] = Field(default=None, max_length=8000)
    paper_size: Optional[Literal["A3", "A4", "A5"]] = None
    paper_orientation: Optional[Literal["portrait", "landscape"]] = None
    omr_mode: Optional[Literal["embedded", "separate"]] = None
    duplex_print: Optional[bool] = None


class ExamStatusUpdate(BaseModel):
    status: Literal["draft", "ready", "grading", "approved", "archived"]
    note: str = Field(default="", max_length=2000)


class ExamApprovalRequest(BaseModel):
    note: str = Field(default="", max_length=2000)


class QuestionUpdate(BaseModel):
    order_no: Optional[int] = Field(default=None, ge=1)
    question_type: Optional[Literal["mcq", "classic"]] = None
    text: Optional[str] = None
    points: Optional[float] = Field(default=None, gt=0, le=100)
    correct_answer: Optional[str] = None
    choices: Optional[dict] = None
    answer_lines: Optional[int] = Field(default=None, ge=1, le=40)
    learning_outcome_code: Optional[str] = None
    learning_outcome_codes: Optional[list[str]] = Field(default=None, max_length=20)
    topic: Optional[str] = Field(default=None, max_length=255)
    unit: Optional[str] = Field(default=None, max_length=255)
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    bloom_level: Optional[Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]] = None
    image_data: Optional[str] = None
    rubric: Optional[dict[str, Any]] = None
    expected_answer: Optional[str] = Field(default=None, max_length=8000)


class QuestionBankCreate(BaseModel):
    course_id: int
    question_type: Literal["mcq", "classic"]
    text: str = Field(min_length=1)
    default_points: float = Field(default=10, gt=0, le=100)
    correct_answer: Optional[str] = None
    choices: Optional[dict] = None
    answer_lines: int = Field(default=8, ge=1, le=40)
    learning_outcome_code: Optional[str] = None
    learning_outcome_codes: list[str] = Field(default_factory=list, max_length=20)
    tags: list[str] = Field(default_factory=list)
    topic: str = Field(default="", max_length=255)
    unit: str = Field(default="", max_length=255)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"] = "understand"
    author: str = Field(default="", max_length=255)
    reviewer: str = Field(default="", max_length=255)
    image_data: Optional[str] = None
    rubric: Optional[dict[str, Any]] = None
    expected_answer: str = Field(default="", max_length=8000)


class QuestionBankUpdate(BaseModel):
    question_type: Optional[Literal["mcq", "classic"]] = None
    text: Optional[str] = None
    default_points: Optional[float] = Field(default=None, gt=0, le=100)
    correct_answer: Optional[str] = None
    choices: Optional[dict] = None
    answer_lines: Optional[int] = Field(default=None, ge=1, le=40)
    learning_outcome_code: Optional[str] = None
    learning_outcome_codes: Optional[list[str]] = Field(default=None, max_length=20)
    tags: Optional[list[str]] = None
    is_active: Optional[bool] = None
    topic: Optional[str] = Field(default=None, max_length=255)
    unit: Optional[str] = Field(default=None, max_length=255)
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    bloom_level: Optional[Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]] = None
    author: Optional[str] = Field(default=None, max_length=255)
    reviewer: Optional[str] = Field(default=None, max_length=255)
    image_data: Optional[str] = None
    rubric: Optional[dict[str, Any]] = None
    expected_answer: Optional[str] = Field(default=None, max_length=8000)


class QuestionReviewRequest(BaseModel):
    status: Literal["draft", "review", "revision", "approved", "institutional", "retired"]
    note: str = Field(default="", max_length=4000)
    reviewer: str = Field(default="", max_length=255)


class BlueprintItemCreate(BaseModel):
    topic: str = Field(default="", max_length=255)
    learning_outcome_code: str = Field(default="", max_length=64)
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"] = "understand"
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    question_count: int = Field(default=1, ge=1, le=200)
    points: float = Field(default=5, gt=0, le=100)
    weight_percent: float = Field(default=0, ge=0, le=100)


class BlueprintCreate(BaseModel):
    course_id: int
    exam_type: str = Field(default="Sınav", max_length=64)
    title: str = Field(min_length=1, max_length=255)
    total_questions: int = Field(default=20, ge=1, le=500)
    total_points: float = Field(default=100, gt=0, le=1000)
    items: list[BlueprintItemCreate] = Field(default_factory=list, max_length=100)


class BlueprintStatusRequest(BaseModel):
    status: Literal["draft", "approved", "retired"]
    approved_by: str = Field(default="", max_length=255)


class AddBankQuestionRequest(BaseModel):
    bank_question_id: int
    order_no: int = Field(ge=1)
    points: Optional[float] = Field(default=None, gt=0, le=100)


class AddBankQuestionsBatchRequest(BaseModel):
    bank_question_ids: list[int] = Field(min_length=1, max_length=100)
    skip_existing: bool = True


class QuestionReorderRequest(BaseModel):
    question_ids: list[int] = Field(min_length=1, max_length=200)


class NormalizeQuestionPointsRequest(BaseModel):
    precision: int = Field(default=2, ge=0, le=2)

class ScanReviewOut(BaseModel):
    id: Optional[int] = None
    scan_item_id: int
    session_id: int
    reason: str = ""
    page_no: int
    status: str
    booklet: Optional[str] = None
    student_no: Optional[str] = None
    student_id: Optional[int] = None
    answers: dict[str, Any] = Field(default_factory=dict)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    issue_codes: list[str] = Field(default_factory=list)
    diagnostic_summary: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0
    confidence_percent: int = 100
    attention_questions: list[Any] = Field(default_factory=list)
    preview_url: Optional[str] = None
    raw_preview_url: Optional[str] = None


class ScanReviewResolve(BaseModel):
    action: Literal["accept", "reject"] = "accept"
    student_id: Optional[int] = None
    booklet: Optional[Literal["A", "B", "C", "D"]] = None
    answers: dict[str, Optional[str]] = Field(default_factory=dict)
    note: str = Field(default="", max_length=1000)


class QuestionKeyException(BaseModel):
    action: Literal["annul", "accept_alternative"]
    alternative: str | None = Field(default=None, max_length=8)
    reason: str = Field(default="", max_length=1000)


class ClassicGridRow(BaseModel):
    student_id: int
    rubric_scores: dict[str, float]


class ClassicGridSave(BaseModel):
    rows: list[ClassicGridRow] = Field(min_length=1, max_length=2000)


class AnswerKeyRegradeRequest(BaseModel):
    corrections: dict[int, str]
    reason: str = Field(default="", max_length=1000)




class AcademicPeriodCreate(BaseModel):
    academic_year: str = Field(min_length=1, max_length=32)
    term: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=255)
    starts_on: Optional[date] = None
    ends_on: Optional[date] = None


class AcademicPeriodStatusUpdate(BaseModel):
    status: Literal["planned", "active", "locked", "archived"]

class AccreditationProfileCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)
    required_general_evidence_kinds: list[str] = Field(default_factory=list)
    required_representative_evidence_kinds: list[str] = Field(default_factory=lambda: ["answer_sheet"])
    requires_representatives: bool = True
    requires_improvement_for_gaps: bool = True


class AccreditationPeriodCreate(BaseModel):
    program_id: int
    profile_id: int
    academic_year: str = Field(min_length=1, max_length=32)
    term: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=255)


class AccreditationPeriodStatusUpdate(BaseModel):
    status: Literal["collecting", "ready", "archived"]


class EvidenceUpdate(BaseModel):
    kind: Optional[str] = Field(default=None, min_length=1, max_length=64)
    category: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = Field(default=None, max_length=4000)
    retention_until: Optional[date] = None


class ImprovementUpdate(BaseModel):
    action_text: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[Literal["open", "in_progress", "done", "cancelled"]] = None
    baseline_percent: Optional[float] = Field(default=None, ge=0, le=100)
    target_percent: Optional[float] = Field(default=None, ge=0, le=100)
    actual_percent: Optional[float] = Field(default=None, ge=0, le=100)
    verification_method: Optional[str] = Field(default=None, max_length=4000)
    effectiveness_status: Optional[Literal["pending", "effective", "partially_effective", "ineffective"]] = None
    closure_note: Optional[str] = Field(default=None, max_length=4000)


class AppUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    external_object_id: Optional[str] = Field(default=None, max_length=64)
    tenant_id: Optional[str] = Field(default=None, max_length=64)
    auth_source: Literal["pilot", "entra", "legacy"] = "pilot"
    is_active: bool = True


class AppUserUpdate(BaseModel):
    email: Optional[str] = Field(default=None, min_length=3, max_length=255)
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    external_object_id: Optional[str] = Field(default=None, max_length=64)
    tenant_id: Optional[str] = Field(default=None, max_length=64)
    auth_source: Optional[Literal["pilot", "entra", "legacy"]] = None
    is_active: Optional[bool] = None


class UserRoleCreate(BaseModel):
    role: Literal["admin", "quality", "instructor", "program_head"]
    program_id: Optional[int] = None
    course_id: Optional[int] = None
    scope_faculty: str = Field(default="", max_length=255)
    scope_department: str = Field(default="", max_length=255)
    scope_program: str = Field(default="", max_length=255)


class PilotFeedbackCreate(BaseModel):
    category: Literal["general", "usability", "exam", "scan", "analysis", "accreditation", "bug"] = "general"
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    page: str = Field(default="", max_length=64)
    message: str = Field(min_length=3, max_length=4000)


class PilotFeedbackUpdate(BaseModel):
    status: Optional[Literal["open", "reviewed", "resolved"]] = None
    resolution_note: Optional[str] = Field(default=None, max_length=4000)


class AttendanceUpdate(BaseModel):
    status: Literal["attended", "absent", "excused", "invalidated"]
    note: str = Field(default="", max_length=2000)

class GradeLockRequest(BaseModel):
    note: str = Field(default="", max_length=2000)

class ExamIncidentCreate(BaseModel):
    incident_type: Literal["missing_paper", "duplicate_paper", "scan_issue", "technical", "academic_integrity", "accessibility", "late_arrival", "other"]
    severity: Literal["info", "warning", "critical"] = "warning"
    student_id: Optional[int] = None
    description: str = Field(min_length=3, max_length=4000)

class ExamIncidentResolve(BaseModel):
    status: Literal["resolved", "dismissed"] = "resolved"
    resolution_note: str = Field(min_length=2, max_length=4000)

class GradeAppealCreate(BaseModel):
    student_id: int
    question_id: Optional[int] = None
    reason: str = Field(min_length=3, max_length=4000)

class GradeAppealResolve(BaseModel):
    decision: Literal["accepted", "rejected"]
    decision_note: str = Field(min_length=2, max_length=4000)
    rubric_scores: Optional[dict[str, float]] = None
    awarded_points: Optional[float] = None


# ---------------------------------------------------------------------------
# 6.20 Quality & Accreditation 360
# ---------------------------------------------------------------------------

class CurriculumItemCreate(BaseModel):
    program_id: int
    academic_year: str = Field(min_length=1, max_length=32)
    term: str = Field(min_length=1, max_length=32)
    class_level: str = Field(default="1. Sınıf", min_length=1, max_length=32)
    course_code: str = Field(min_length=1, max_length=64)
    course_name: str = Field(min_length=1, max_length=255)
    ects: float = Field(default=0, ge=0, le=60)
    course_category: str = Field(default="Genel / Zorunlu", max_length=96)
    is_professional: bool = False
    is_program_specific: bool = False
    is_external_stakeholder_supported: bool = False
    is_applied_or_current_tech: bool = False
    quality_status: str = Field(default="implemented", max_length=32)
    notes: str = Field(default="", max_length=4000)


class StakeholderRecordCreate(BaseModel):
    program_id: int
    stakeholder_type: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    organization: str = Field(default="", max_length=255)
    engagement_type: str = Field(default="Görüş / Geri Bildirim", max_length=96)
    engagement_date: Optional[date] = None
    feedback: str = Field(default="", max_length=8000)
    resulting_action: str = Field(default="", max_length=8000)
    quality_status: str = Field(default="implemented", max_length=32)
    evidence_ref: str = Field(default="", max_length=512)


class GraduateRecordCreate(BaseModel):
    program_id: int
    graduate_key: str = Field(min_length=1, max_length=128)
    full_name: str = Field(default="", max_length=255)
    graduation_year: Optional[int] = Field(default=None, ge=1950, le=2200)
    employment_status: str = Field(default="Bilinmiyor", max_length=64)
    employer: str = Field(default="", max_length=255)
    sector: str = Field(default="", max_length=255)
    job_title: str = Field(default="", max_length=255)
    related_field: Optional[bool] = None
    survey_date: Optional[date] = None
    notes: str = Field(default="", max_length=4000)


class FacultyRecordCreate(BaseModel):
    program_id: int
    title: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    employment_type: str = Field(default="Tam Zamanlı", max_length=64)
    expertise: str = Field(default="", max_length=4000)
    highest_degree: str = Field(default="", max_length=128)
    industry_experience_years: float = Field(default=0, ge=0, le=80)
    weekly_course_hours: float = Field(default=0, ge=0, le=80)
    quality_status: str = Field(default="implemented", max_length=32)


class InfrastructureRecordCreate(BaseModel):
    program_id: int
    infrastructure_type: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=255)
    location: str = Field(default="", max_length=255)
    capacity: Optional[int] = Field(default=None, ge=0, le=100000)
    quality_status: str = Field(default="implemented", max_length=32)
    accessibility_status: str = Field(default="implemented", max_length=32)
    isg_status: str = Field(default="implemented", max_length=32)
    last_review_date: Optional[date] = None
    notes: str = Field(default="", max_length=4000)


class QualityCycleCreate(BaseModel):
    program_id: int
    academic_year: str = Field(min_length=1, max_length=32)
    criterion_code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    plan_text: str = Field(default="", max_length=8000)
    do_text: str = Field(default="", max_length=8000)
    check_text: str = Field(default="", max_length=8000)
    act_text: str = Field(default="", max_length=8000)
    owner: str = Field(default="", max_length=255)
    due_date: Optional[date] = None
    status: str = Field(default="planned", max_length=32)
    evidence_refs: list[str] = Field(default_factory=list)


class QualityActionAccept(BaseModel):
    program_id: int
    academic_year: str = Field(min_length=1, max_length=32)
    framework_id: Optional[int] = None
    criterion_code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    owner: str = Field(default="Program Kalite Sorumlusu", max_length=255)
    due_date: Optional[date] = None
    plan_text: str = Field(default="", max_length=8000)
    do_text: str = Field(default="", max_length=8000)
    check_text: str = Field(default="", max_length=8000)
    act_text: str = Field(default="", max_length=8000)
    expected_evidence: list[str] = Field(default_factory=list)


class QualityCalendarEventCreate(BaseModel):
    program_id: int
    academic_year: str = Field(min_length=1, max_length=32)
    event_type: Literal["meeting", "evidence_deadline", "pdca_deadline", "review", "audit", "other"] = "other"
    title: str = Field(min_length=1, max_length=255)
    start_date: date
    due_date: Optional[date] = None
    owner: str = Field(default="", max_length=255)
    owner_role: str = Field(default="", max_length=96)
    criterion_code: str = Field(default="", max_length=64)
    status: Literal["planned", "in_progress", "done", "cancelled"] = "planned"
    evidence_required: str = Field(default="", max_length=4000)
    related_entity_type: str = Field(default="", max_length=64)
    related_entity_id: Optional[int] = None
    notes: str = Field(default="", max_length=8000)

class QualityCalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    owner: Optional[str] = Field(default=None, max_length=255)
    owner_role: Optional[str] = Field(default=None, max_length=96)
    criterion_code: Optional[str] = Field(default=None, max_length=64)
    status: Optional[Literal["planned", "in_progress", "done", "cancelled"]] = None
    evidence_required: Optional[str] = Field(default=None, max_length=4000)
    notes: Optional[str] = Field(default=None, max_length=8000)


class GovernanceDecisionCreate(BaseModel):
    program_id: int
    body_type: str = Field(min_length=1, max_length=96)
    meeting_date: Optional[date] = None
    meeting_no: str = Field(min_length=1, max_length=64)
    decision_no: str = Field(min_length=1, max_length=64)
    subject: str = Field(min_length=1, max_length=255)
    decision_text: str = Field(min_length=1, max_length=12000)
    related_criterion: str = Field(default="", max_length=64)
    source_stakeholder_id: Optional[int] = None
    status: str = Field(default="implemented", max_length=32)
    evidence_ref: str = Field(default="", max_length=512)




class GovernanceDecisionActionCreate(BaseModel):
    academic_year: str = Field(min_length=1, max_length=32)
    owner: str = Field(default="Program Başkanı", max_length=255)
    due_date: Optional[date] = None
    criterion_code: str = Field(default="", max_length=64)
    expected_evidence: list[str] = Field(default_factory=list)


class QualityCycleCloseRequest(BaseModel):
    closure_note: str = Field(min_length=3, max_length=4000)

class QualityCriterionAssessmentUpsert(BaseModel):
    program_id: int
    framework_profile_id: int
    academic_year: str = Field(min_length=1, max_length=32)
    criterion_code: str = Field(min_length=1, max_length=64)
    maturity_level: int = Field(default=1, ge=1, le=5)
    quality_status: str = Field(default="planned", max_length=32)
    note: str = Field(default="", max_length=8000)
    evidence_refs: list[str] = Field(default_factory=list)


class StrategicObjectiveCreate(BaseModel):
    academic_year: str = Field(min_length=1, max_length=32)
    scope_type: Literal["university", "faculty", "department", "program"] = "university"
    scope_name: str = Field(default="Doğuş Üniversitesi", max_length=255)
    program_id: Optional[int] = None
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(default="", max_length=8000)
    owner: str = Field(default="", max_length=255)
    status: Literal["draft", "active", "completed", "cancelled"] = "active"
    start_date: Optional[date] = None
    due_date: Optional[date] = None

class StrategicKPICreate(BaseModel):
    objective_id: int
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=2, max_length=255)
    unit: str = Field(default="%", max_length=32)
    baseline_value: float = 0.0
    target_value: float = 100.0
    actual_value: float = 0.0
    weight: float = Field(default=1.0, gt=0, le=100)
    direction: Literal["higher", "lower"] = "higher"
    source_type: str = Field(default="manual", max_length=64)
    source_ref: str = Field(default="", max_length=255)
    status: Literal["active", "paused", "completed"] = "active"

class StrategicKPIUpdate(BaseModel):
    actual_value: Optional[float] = None
    target_value: Optional[float] = None
    status: Optional[Literal["active", "paused", "completed"]] = None

class AccreditationCrosswalkCreate(BaseModel):
    source_framework_family: str = Field(min_length=1, max_length=64)
    source_framework_version: str = Field(default="", max_length=64)
    source_criterion_code: str = Field(min_length=1, max_length=96)
    target_framework_family: str = Field(min_length=1, max_length=64)
    target_framework_version: str = Field(default="", max_length=64)
    target_criterion_code: str = Field(min_length=1, max_length=96)
    relationship: Literal["supports", "related", "equivalent"] = "supports"
    rationale: str = Field(default="", max_length=8000)

class AccreditationCrosswalkReview(BaseModel):
    review_status: Literal["approved", "rejected"]

class ReadinessSnapshotCreate(BaseModel):
    academic_year: str = Field(min_length=1, max_length=32)
    scope_type: Literal["institution", "faculty", "program"] = "institution"
    scope_key: str = Field(default="DOGUS", min_length=1, max_length=255)
