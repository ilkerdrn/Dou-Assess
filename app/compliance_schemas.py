from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class FrameworkFreezeRequest(BaseModel):
    framework_profile_id: int
    academic_year: str


class PEAObjectiveCreate(BaseModel):
    program_id: int
    academic_year: str
    code: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=3)
    stakeholder_basis: str = ""
    mission_alignment: str = ""
    review_cycle_years: int = Field(default=3, ge=1, le=10)
    target_indicator: str = ""
    quality_status: str = "implemented"
    evidence_refs: list[Any] = Field(default_factory=list)


class PEAOutcomeMapCreate(BaseModel):
    objective_id: int
    program_outcome_id: int
    contribution: int = Field(ge=1, le=5)
    rationale: str = ""


class ProgramOutcomeComponentCreate(BaseModel):
    program_outcome_id: int
    code: str = Field(min_length=1, max_length=96)
    description: str = Field(min_length=2)
    component_type: str = "knowledge-skill-competency"
    framework_family: str = ""
    framework_version: str = ""
    framework_component_code: str = ""
    required: bool = True
    evidence_refs: list[Any] = Field(default_factory=list)


class StudentOutcomeSnapshotCreate(BaseModel):
    academic_year: str
    snapshot_type: Literal["progress", "graduation"] = "progress"
    freeze: bool = False


class AccreditationApplicationCreate(BaseModel):
    program_id: int
    framework_profile_id: int
    academic_year: str
    application_type: Literal["general", "interim", "renewal", "monitoring"] = "general"
    stage: str = "preparation"
    status: str = "active"
    application_date: date | None = None
    self_evaluation_due: date | None = None
    correction_due: date | None = None
    visit_date: date | None = None
    decision_date: date | None = None
    owner: str = ""
    notes: str = ""
    previous_application_id: int | None = None
    evaluation_mode: Literal["site_visit", "report_only"] = "site_visit"


class AccreditationApplicationUpdate(BaseModel):
    stage: str | None = None
    status: str | None = None
    application_date: date | None = None
    self_evaluation_due: date | None = None
    correction_due: date | None = None
    visit_date: date | None = None
    decision_date: date | None = None
    owner: str | None = None
    notes: str | None = None
    previous_application_id: int | None = None
    evaluation_mode: Literal["site_visit", "report_only"] | None = None


class EvaluatorWorkspaceCreate(BaseModel):
    application_id: int
    evaluator_email: str
    evaluator_name: str = ""
    access_mode: Literal["read_only"] = "read_only"
    expires_at: datetime | None = None


class EvaluatorWorkspaceAccessUpdate(BaseModel):
    active: bool


class DocumentRequestCreate(BaseModel):
    application_id: int
    criterion_code: str = ""
    title: str = Field(min_length=2)
    description: str = ""
    requested_by: str = "Evaluator"
    due_date: date | None = None
    evidence_refs: list[Any] = Field(default_factory=list)


class DocumentRequestUpdate(BaseModel):
    status: Literal["open", "in_progress", "answered", "closed"] | None = None
    response_note: str | None = None
    evidence_refs: list[Any] | None = None


class AccreditationFindingCreate(BaseModel):
    application_id: int
    criterion_code: str = ""
    finding_type: Literal["deficiency", "weakness", "concern", "observation", "strength"]
    title: str = Field(min_length=2)
    description: str = ""
    status: Literal["open", "monitoring", "resolved", "closed"] = "open"
    owner: str = ""
    due_date: date | None = None
    evidence_refs: list[Any] = Field(default_factory=list)
    response_note: str = ""


class AccreditationFindingUpdate(BaseModel):
    criterion_code: str | None = None
    finding_type: Literal["deficiency", "weakness", "concern", "observation", "strength"] | None = None
    title: str | None = None
    description: str | None = None
    status: Literal["open", "monitoring", "resolved", "closed"] | None = None
    owner: str | None = None
    due_date: date | None = None
    evidence_refs: list[Any] | None = None
    response_note: str | None = None


class AccreditationVisitNoteCreate(BaseModel):
    application_id: int
    criterion_code: str = ""
    note_type: Literal["interview", "observation", "evidence_request", "strength", "risk", "exit_meeting"] = "observation"
    title: str = Field(min_length=2)
    note: str = ""
    recorded_by: str = ""
    visibility: Literal["internal", "evaluator", "institution"] = "internal"
    evidence_refs: list[Any] = Field(default_factory=list)
    occurred_at: datetime | None = None


class AccreditationFinalReportUpdate(BaseModel):
    team_opinion: str | None = None
    institution_response_summary: str | None = None
    final_decision_code: str | None = None
    accreditation_start: date | None = None
    accreditation_end: date | None = None
    accreditation_term_years: int | None = Field(default=None, ge=0, le=10)
    next_review_type: str | None = None
    next_review_due: date | None = None
    decision_basis: dict[str, Any] | None = None


class AccreditationDecisionCreate(BaseModel):
    action: Literal["response_submitted", "finding_closed", "decision_recorded", "application_closed"]
    decision_code: str = ""
    note: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class MedekEvaluatorReportItemCreate(BaseModel):
    application_id: int
    workspace_id: int | None = None
    report_phase: Literal["individual", "pre_consensus", "site_draft", "final"] = "individual"
    criterion_code: str = ""
    evaluator_name: str = ""
    item_type: Literal["strength", "improvement_area", "site_question", "assessment"]
    narrative: str = Field(min_length=2)
    assessment_value: str = ""
    evidence_refs: list[Any] = Field(default_factory=list)
    status: Literal["draft", "confirmed"] = "draft"


class MedekEvaluatorReportItemUpdate(BaseModel):
    report_phase: Literal["individual", "pre_consensus", "site_draft", "final"] | None = None
    criterion_code: str | None = None
    evaluator_name: str | None = None
    item_type: Literal["strength", "improvement_area", "site_question", "assessment"] | None = None
    narrative: str | None = None
    assessment_value: str | None = None
    evidence_refs: list[Any] | None = None
    status: Literal["draft", "confirmed"] | None = None


class MedekPdrFormAnalysisCreate(BaseModel):
    application_id: int
    form_code: Literal["FORM1", "FORM2", "FORM3"]
    subject_ref: str = "program"
    title: str = ""
    analysis_payload: dict[str, Any] = Field(default_factory=dict)
    result: Literal["satisfied", "improvement_area", "review"] = "review"
    reviewer: str = ""
    evidence_refs: list[Any] = Field(default_factory=list)
    status: Literal["draft", "confirmed"] = "draft"


class MedekPdrFormAnalysisUpdate(BaseModel):
    title: str | None = None
    analysis_payload: dict[str, Any] | None = None
    result: Literal["satisfied", "improvement_area", "review"] | None = None
    reviewer: str | None = None
    evidence_refs: list[Any] | None = None
    status: Literal["draft", "confirmed"] | None = None


class ControlledDocumentCreate(BaseModel):
    program_id: int | None = None
    document_code: str = Field(min_length=1, max_length=96)
    document_type: Literal["policy", "directive", "procedure", "instruction", "form", "plan", "report", "other"]
    title: str = Field(min_length=2)
    owner: str = ""
    status: str = "active"
    retention_years: int = Field(default=5, ge=1, le=50)


class ControlledDocumentRevisionCreate(BaseModel):
    revision_no: int = Field(ge=1)
    effective_date: date | None = None
    review_date: date | None = None
    status: Literal["draft", "submitted", "reviewed", "approved", "superseded", "archived"] = "draft"
    change_summary: str = ""
    content_text: str = ""
    original_name: str = ""
    mime_type: str = "text/plain"
    approved_by: str = ""  # accepted for backwards compatibility; server derives approver identity


class BudgetPlanCreate(BaseModel):
    program_id: int
    academic_year: str
    currency: str = "TRY"
    allocated_amount: float = Field(default=0, ge=0)
    spent_amount: float = Field(default=0, ge=0)
    owner: str = ""
    quality_status: str = "implemented"
    evidence_refs: list[Any] = Field(default_factory=list)


class BudgetLineCreate(BaseModel):
    budget_plan_id: int
    category: str
    description: str = ""
    planned_amount: float = Field(default=0, ge=0)
    actual_amount: float = Field(default=0, ge=0)
    funding_source: str = "Kurum"
    criterion_code: str = ""
    evidence_refs: list[Any] = Field(default_factory=list)


class FacultyCVRevisionCreate(BaseModel):
    faculty_record_id: int
    format_type: str = "YOKSIS-UAK"
    version_no: int = Field(default=1, ge=1)
    cv_data: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False


class FacultyWorkloadCreate(BaseModel):
    faculty_record_id: int
    academic_year: str
    term: str
    course_code: str = ""
    workload_type: str = "course"
    weekly_hours: float = Field(default=0, ge=0, le=100)
    source: str = "manual"
    notes: str = ""


class GraduateFollowupCreate(BaseModel):
    graduate_record_id: int
    followup_year: int = Field(ge=1, le=10)
    survey_date: date | None = None
    employment_status: str = "Bilinmiyor"
    employer: str = ""
    job_title: str = ""
    related_field: bool | None = None
    satisfaction_percent: float | None = Field(default=None, ge=0, le=100)
    employer_feedback: str = ""
    resulting_action: str = ""
    evidence_refs: list[Any] = Field(default_factory=list)


class InfrastructureMaintenanceCreate(BaseModel):
    infrastructure_id: int
    maintenance_type: str = "periodic"
    planned_date: date | None = None
    completed_date: date | None = None
    status: str = "planned"
    owner: str = ""
    notes: str = ""
    evidence_refs: list[Any] = Field(default_factory=list)


class MissionActivityCreate(BaseModel):
    program_id: int | None = None
    academic_year: str
    domain: Literal["research", "social_contribution", "internationalization"]
    scope_type: str = "university"
    scope_name: str = "Doğuş Üniversitesi"
    code: str
    title: str
    activity_type: str = "activity"
    start_date: date | None = None
    end_date: date | None = None
    owner: str = ""
    partner: str = ""
    country: str = ""
    participants: int = Field(default=0, ge=0)
    budget_amount: float = Field(default=0, ge=0)
    target_value: float | None = None
    actual_value: float | None = None
    unit: str = ""
    status: str = "planned"
    outcome_text: str = ""
    evidence_refs: list[Any] = Field(default_factory=list)


class ReportTemplateCreate(BaseModel):
    framework_family: str
    report_type: Literal["ODR", "KIDR", "BBO", "FBO", "EVIDENCE_INDEX", "COURSE_FILE"]
    version: str
    title: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    folder_layout: list[dict[str, Any] | str] = Field(default_factory=list)
    source_url: str = ""
    source_sha256: str = ""
    locked: bool = True
    effective_from: date | None = None

