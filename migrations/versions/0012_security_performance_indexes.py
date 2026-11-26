"""6.16 security and performance hardening indexes

Revision ID: 0012_security_performance_indexes
Revises: 0011_final_ux_feedback
"""
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa

revision = "0012_security_performance_indexes"
down_revision = "0011_final_ux_feedback"
branch_labels = None
depends_on = None

_INDEXES = {
    "courses": [
        ("ix_courses_program_period", ["program_id", "academic_year", "term"]),
    ],
    "exams": [
        ("ix_exams_course_status_date", ["course_id", "status", "exam_date"]),
    ],
    "question_bank": [
        ("ix_question_bank_course_active_type", ["course_id", "is_active", "question_type"]),
    ],
    "scan_sessions": [
        ("ix_scan_sessions_exam_created", ["exam_id", "created_at"]),
    ],
    "scan_items": [
        ("ix_scan_items_exam_status", ["exam_id", "status"]),
    ],
    "scan_reviews": [
        ("ix_scan_reviews_exam_status", ["exam_id", "status"]),
    ],
    "improvement_actions": [
        ("ix_improvement_actions_exam_status", ["exam_id", "status"]),
    ],
    "audit_logs": [
        ("ix_audit_logs_created_at", ["created_at"]),
        ("ix_audit_logs_entity", ["entity_type", "entity_id", "created_at"]),
    ],
    "security_events": [
        ("ix_security_events_type_created", ["event_type", "created_at"]),
    ],
    "integration_sync_runs": [
        ("ix_integration_sync_provider_created", ["provider", "created_at"]),
    ],
    "pilot_feedback": [
        ("ix_pilot_feedback_status_created", ["status", "created_at"]),
    ],
}


def upgrade() -> None:
    bind = op.get_bind()

    # Alembic creates alembic_version.version_num as VARCHAR(32) by default.
    # This revision id is 33 characters, so PostgreSQL would otherwise fail
    # after the migration body when Alembic records the new revision.
    # Widen it before Alembic performs that UPDATE. SQLite does not enforce
    # VARCHAR lengths and does not need this PostgreSQL-specific ALTER.
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "alembic_version",
            "version_num",
            existing_type=sa.String(length=32),
            type_=sa.String(length=64),
            existing_nullable=False,
        )

    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    for table, specs in _INDEXES.items():
        if table not in tables:
            continue
        existing = {x["name"] for x in inspect(bind).get_indexes(table)}
        for name, columns in specs:
            if name not in existing:
                op.create_index(name, table, columns, unique=False)


def downgrade() -> None:
    # Pilot release migrations are intentionally forward-only to protect evidence history.
    pass
