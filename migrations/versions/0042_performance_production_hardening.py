"""performance and production hardening indexes

Revision ID: 0042_performance_production_hardening
Revises: 0041_program_review_evidence_hub
"""
from alembic import op
import sqlalchemy as sa

revision = "0042_performance_production_hardening"
down_revision = "0041_program_review_evidence_hub"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {str(x.get("name")) for x in inspector.get_indexes(table) if x.get("name")}


def _create(table: str, name: str, columns: list[str]) -> None:
    if table not in _tables() or name in _indexes(table):
        return
    op.create_index(name, table, columns, unique=False)


def upgrade() -> None:
    # Authorization/directory hot paths.
    _create("courses", "ix_courses_scope_period_instructor", ["program_id", "academic_year", "term", "instructor_email"])
    _create("courses", "ix_courses_instructor_email", ["instructor_email"])
    _create("students", "ix_students_program_student_no", ["program_id", "student_no"])
    _create("exams", "ix_exams_course_status_id", ["course_id", "status", "id"])
    _create("question_bank", "ix_question_bank_course_active_review_id", ["course_id", "is_active", "review_status", "id"])

    # Evidence/security and operational control centers.
    _create("evidence_assets", "ix_evidence_assets_exam_integrity_id", ["exam_id", "integrity_status", "id"])
    _create("audit_logs", "ix_audit_logs_entity_action_id", ["entity_type", "action", "id"])
    _create("security_events", "ix_security_events_type_severity_id", ["event_type", "severity", "id"])
    _create("scan_items", "ix_scan_items_exam_status_id", ["exam_id", "status", "id"])
    _create("scan_reviews", "ix_scan_reviews_exam_status_id", ["exam_id", "status", "id"])
    _create("operational_jobs", "ix_operational_jobs_status_run_after_locked", ["status", "run_after", "locked_at", "id"])
    _create("operational_notifications", "ix_operational_notifications_user_status_id", ["user_email", "status", "id"])

    # Program Review / Evidence Hub hot paths.
    _create("program_reviews", "ix_program_reviews_program_year_status_id", ["program_id", "academic_year", "status", "id"])
    _create("program_review_sections", "ix_program_review_sections_review_status_order", ["review_id", "status", "order_no"])
    _create("program_review_evidence_links", "ix_program_review_evidence_source_section", ["source_type", "source_id", "section_id"])
    _create("evidence_tags", "ix_evidence_tags_source_tag", ["source_type", "source_id", "tag_key"])


def downgrade() -> None:
    for table, name in reversed([
        ("courses", "ix_courses_scope_period_instructor"),
        ("courses", "ix_courses_instructor_email"),
        ("students", "ix_students_program_student_no"),
        ("exams", "ix_exams_course_status_id"),
        ("question_bank", "ix_question_bank_course_active_review_id"),
        ("evidence_assets", "ix_evidence_assets_exam_integrity_id"),
        ("audit_logs", "ix_audit_logs_entity_action_id"),
        ("security_events", "ix_security_events_type_severity_id"),
        ("scan_items", "ix_scan_items_exam_status_id"),
        ("scan_reviews", "ix_scan_reviews_exam_status_id"),
        ("operational_jobs", "ix_operational_jobs_status_run_after_locked"),
        ("operational_notifications", "ix_operational_notifications_user_status_id"),
        ("program_reviews", "ix_program_reviews_program_year_status_id"),
        ("program_review_sections", "ix_program_review_sections_review_status_order"),
        ("program_review_evidence_links", "ix_program_review_evidence_source_section"),
        ("evidence_tags", "ix_evidence_tags_source_tag"),
    ]):
        if table in _tables() and name in _indexes(table):
            op.drop_index(name, table_name=table)
