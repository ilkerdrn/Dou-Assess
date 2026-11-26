"""operations and automation

Revision ID: 0040_operations_automation
Revises: 0039_evidence_integrity_security
"""
from alembic import op
import sqlalchemy as sa

revision = "0040_operations_automation"
down_revision = "0039_evidence_integrity_security"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table: str) -> set[str]:
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}


def _ix(name: str, table: str, cols: list[str]):
    if name not in _indexes(table):
        op.create_index(name, table, cols)


def upgrade():
    tables = _tables()
    if "operational_jobs" not in tables:
        op.create_table(
            "operational_jobs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("job_type", sa.String(64), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("dedupe_key", sa.String(255), nullable=False, server_default=""),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("result", sa.JSON(), nullable=False),
            sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("run_after", sa.DateTime(timezone=True), nullable=True),
            sa.Column("locked_by", sa.String(128), nullable=False, server_default=""),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(255), nullable=False, server_default="system"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("status IN ('queued','running','succeeded','failed','cancelled')", name="ck_operational_job_status"),
        )
    for name, cols in [
        ("ix_operational_jobs_job_type", ["job_type"]), ("ix_operational_jobs_status", ["status"]),
        ("ix_operational_jobs_priority", ["priority"]), ("ix_operational_jobs_dedupe_key", ["dedupe_key"]),
        ("ix_operational_jobs_run_after", ["run_after"]), ("ix_operational_jobs_locked_at", ["locked_at"]),
        ("ix_operational_jobs_created_by", ["created_by"]), ("ix_operational_jobs_created_at", ["created_at"]),
        ("ix_operational_jobs_claim", ["status", "run_after", "priority", "id"]),
    ]:
        _ix(name, "operational_jobs", cols)

    if "operational_notifications" not in tables:
        op.create_table(
            "operational_notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_email", sa.String(255), nullable=False, server_default=""),
            sa.Column("role_scope", sa.String(64), nullable=False, server_default=""),
            sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=True),
            sa.Column("notification_type", sa.String(64), nullable=False),
            sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False, server_default=""),
            sa.Column("action_url", sa.String(1024), nullable=False, server_default=""),
            sa.Column("dedupe_key", sa.String(255), nullable=False),
            sa.Column("source_entity_type", sa.String(64), nullable=False, server_default=""),
            sa.Column("source_entity_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default="unread"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("dedupe_key", name="uq_operational_notification_dedupe"),
            sa.CheckConstraint("status IN ('unread','read','archived')", name="ck_operational_notification_status"),
        )
    for name, cols in [
        ("ix_operational_notifications_user_email", ["user_email"]),
        ("ix_operational_notifications_role_scope", ["role_scope"]),
        ("ix_operational_notifications_program_id", ["program_id"]),
        ("ix_operational_notifications_notification_type", ["notification_type"]),
        ("ix_operational_notifications_severity", ["severity"]),
        ("ix_operational_notifications_source_entity_type", ["source_entity_type"]),
        ("ix_operational_notifications_source_entity_id", ["source_entity_id"]),
        ("ix_operational_notifications_status", ["status"]),
        ("ix_operational_notifications_created_at", ["created_at"]),
        ("ix_operational_notifications_expires_at", ["expires_at"]),
        ("ix_operational_notifications_inbox", ["status", "user_email", "role_scope", "created_at"]),
    ]:
        _ix(name, "operational_notifications", cols)

    # High-volume deadline/filter paths used by the scheduler and operations center.
    for name, table, cols in [
        ("ix_quality_cycles_due_status", "quality_cycles", ["due_date", "status"]),
        ("ix_quality_calendar_due_status", "quality_calendar_events", ["due_date", "status"]),
        ("ix_accreditation_requests_due_status", "quality_accreditation_document_requests", ["due_date", "status"]),
        ("ix_accreditation_findings_due_status", "quality_accreditation_findings", ["due_date", "status"]),
        ("ix_assessment_plan_items_due_status", "assessment_plan_items", ["due_date", "status"]),
    ]:
        if table in _tables():
            _ix(name, table, cols)


def downgrade():
    for name, table in [
        ("ix_assessment_plan_items_due_status", "assessment_plan_items"),
        ("ix_accreditation_findings_due_status", "quality_accreditation_findings"),
        ("ix_accreditation_requests_due_status", "quality_accreditation_document_requests"),
        ("ix_quality_calendar_due_status", "quality_calendar_events"),
        ("ix_quality_cycles_due_status", "quality_cycles"),
    ]:
        if table in _tables() and name in _indexes(table): op.drop_index(name, table_name=table)
    if "operational_notifications" in _tables(): op.drop_table("operational_notifications")
    if "operational_jobs" in _tables(): op.drop_table("operational_jobs")
