"""6.14 pilot UAT operations history

Revision ID: 0010_pilot_uat_operations
Revises: 0009_corporate_pilot_integration
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0010_pilot_uat_operations"
down_revision = "0009_corporate_pilot_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("pilot_uat_runs"):
        op.create_table(
            "pilot_uat_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("checks", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_by", sa.String(255), nullable=False, server_default="system"),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        )
        op.create_index("ix_pilot_uat_runs_status", "pilot_uat_runs", ["status"])
        op.create_index("ix_pilot_uat_runs_created_at", "pilot_uat_runs", ["created_at"])


def downgrade() -> None:
    pass
