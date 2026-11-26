"""6.6 production security events and hardening support

Revision ID: 0008_production_security
Revises: 0007_identity_roles_entra_ready
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0008_production_security"
down_revision = "0007_identity_roles_entra_ready"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table("security_events"):
        return
    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
        sa.Column("request_id", sa.String(96), nullable=False, server_default=""),
        sa.Column("actor_email", sa.String(255), nullable=False, server_default=""),
        sa.Column("remote_addr", sa.String(64), nullable=False, server_default=""),
        sa.Column("method", sa.String(16), nullable=False, server_default=""),
        sa.Column("path", sa.String(512), nullable=False, server_default=""),
        sa.Column("detail", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_severity", "security_events", ["severity"])
    op.create_index("ix_security_events_request_id", "security_events", ["request_id"])
    op.create_index("ix_security_events_actor_email", "security_events", ["actor_email"])
    op.create_index("ix_security_events_created_at", "security_events", ["created_at"])


def downgrade() -> None:
    # Security/audit history is intentionally retained.
    pass
