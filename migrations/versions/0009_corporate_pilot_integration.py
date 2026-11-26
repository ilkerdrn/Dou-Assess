"""6.12 corporate pilot integration, academic periods and OBS bridge metadata

Revision ID: 0009_corporate_pilot_integration
Revises: 0008_production_security
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0009_corporate_pilot_integration"
down_revision = "0008_production_security"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = inspect(bind)
    return insp.has_table(table) and column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    for table in ("programs", "courses", "students"):
        if insp.has_table(table) and not _has_column(bind, table, "external_source"):
            op.add_column(table, sa.Column("external_source", sa.String(64), nullable=False, server_default=""))
        if insp.has_table(table) and not _has_column(bind, table, "external_id"):
            op.add_column(table, sa.Column("external_id", sa.String(128), nullable=True))
            op.create_index(f"ix_{table}_external_id", table, ["external_id"])

    if not inspect(bind).has_table("academic_periods"):
        op.create_table(
            "academic_periods",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("academic_year", sa.String(32), nullable=False),
            sa.Column("term", sa.String(32), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="planned"),
            sa.Column("starts_on", sa.Date(), nullable=True),
            sa.Column("ends_on", sa.Date(), nullable=True),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.UniqueConstraint("academic_year", "term", name="uq_academic_period_year_term"),
            sa.CheckConstraint("status IN ('planned','active','locked','archived')", name="ck_academic_period_status"),
        )
        op.create_index("ix_academic_periods_academic_year", "academic_periods", ["academic_year"])
        op.create_index("ix_academic_periods_term", "academic_periods", ["term"])
        op.create_index("ix_academic_periods_status", "academic_periods", ["status"])

    if not inspect(bind).has_table("integration_sync_runs"):
        op.create_table(
            "integration_sync_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider", sa.String(64), nullable=False, server_default="obs-workbook"),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("mode", sa.String(32), nullable=False, server_default="full"),
            sa.Column("source_sha256", sa.String(64), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        )
        op.create_index("ix_integration_sync_runs_provider", "integration_sync_runs", ["provider"])
        op.create_index("ix_integration_sync_runs_source_sha256", "integration_sync_runs", ["source_sha256"])
        op.create_index("ix_integration_sync_runs_status", "integration_sync_runs", ["status"])
        op.create_index("ix_integration_sync_runs_created_at", "integration_sync_runs", ["created_at"])

    # Seed academic periods from existing course offerings without changing course rows.
    if inspect(bind).has_table("courses") and inspect(bind).has_table("academic_periods"):
        rows = bind.execute(sa.text("SELECT DISTINCT academic_year, term FROM courses WHERE academic_year <> '' AND term <> ''")).all()
        for academic_year, term in rows:
            exists = bind.execute(sa.text(
                "SELECT id FROM academic_periods WHERE academic_year=:y AND term=:t LIMIT 1"
            ), {"y": academic_year, "t": term}).scalar()
            if not exists:
                bind.execute(sa.text(
                    "INSERT INTO academic_periods (academic_year, term, title, status, created_at) "
                    "VALUES (:y, :t, :title, 'planned', CURRENT_TIMESTAMP)"
                ), {"y": academic_year, "t": term, "title": f"{academic_year} {term}"})


def downgrade() -> None:
    # Pilot history and external identifiers are intentionally retained.
    pass
