"""6.15 final UX pilot feedback

Revision ID: 0011_final_ux_feedback
Revises: 0010_pilot_uat_operations
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0011_final_ux_feedback"
down_revision = "0010_pilot_uat_operations"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("pilot_feedback"):
        op.create_table(
            "pilot_feedback",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("category", sa.String(64), nullable=False, server_default="general"),
            sa.Column("rating", sa.Integer(), nullable=True),
            sa.Column("page", sa.String(64), nullable=False, server_default=""),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="open"),
            sa.Column("created_by", sa.String(255), nullable=False),
            sa.Column("role_names", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("resolution_note", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.CheckConstraint("status IN ('open','reviewed','resolved')", name="ck_pilot_feedback_status"),
            sa.CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_pilot_feedback_rating"),
        )
        op.create_index("ix_pilot_feedback_category", "pilot_feedback", ["category"])
        op.create_index("ix_pilot_feedback_status", "pilot_feedback", ["status"])
        op.create_index("ix_pilot_feedback_created_by", "pilot_feedback", ["created_by"])
        op.create_index("ix_pilot_feedback_created_at", "pilot_feedback", ["created_at"])

def downgrade() -> None:
    pass
