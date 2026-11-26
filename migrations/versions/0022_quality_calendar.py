"""Quality calendar and governance deadlines.

Revision ID: 0022_quality_calendar
Revises: 0021_quality_framework_routing
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_quality_calendar"
down_revision = "0021_quality_framework_routing"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "quality_calendar_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("owner", sa.String(255), nullable=False, server_default=""),
        sa.Column("owner_role", sa.String(96), nullable=False, server_default=""),
        sa.Column("criterion_code", sa.String(64), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="planned"),
        sa.Column("evidence_required", sa.Text(), nullable=False, server_default=""),
        sa.Column("related_entity_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("related_entity_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for c in ["program_id","academic_year","event_type","start_date","due_date","owner","criterion_code","status"]:
        op.create_index(f"ix_quality_calendar_events_{c}", "quality_calendar_events", [c])

def downgrade():
    op.drop_table("quality_calendar_events")
