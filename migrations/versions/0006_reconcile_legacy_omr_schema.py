"""reconcile legacy OMR tables with 6.3+ scan station schema

Revision ID: 0006_reconcile_legacy_omr_schema
Revises: 0005_accreditation_center

This migration is intentionally defensive. Some pilot databases were created
before Alembic ownership of the OMR tables and can contain the v4 scan schema
under the same table names. 6.3+ expects a different schema.

If a legacy/incomplete OMR schema is detected, every existing row is first
copied into archive tables and only then are the active OMR tables rebuilt.
Fresh/new-format databases are left untouched.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0006_reconcile_legacy_omr_schema"
down_revision = "0005_accreditation_center"
branch_labels = None
depends_on = None

_REQUIRED = {
    "scan_sessions": {
        "id", "exam_id", "source_name", "source_sha256", "status",
        "page_count", "accepted_count", "review_count", "duplicate_count",
        "skipped_count", "created_at",
    },
    "scan_items": {
        "id", "session_id", "exam_id", "page_no", "status", "booklet",
        "token", "student_no_detected", "student_id", "page_fingerprint",
        "answers", "diagnostics", "issue_summary", "preview_name", "created_at",
    },
    "scan_reviews": {
        "id", "scan_item_id", "exam_id", "status", "reason",
        "resolved_student_id", "resolved_answers", "resolved_at", "created_at",
    },
}


def _columns(bind, table: str) -> set[str]:
    insp = inspect(bind)
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _unique_archive_name(bind, base: str) -> str:
    insp = inspect(bind)
    if not insp.has_table(base):
        return base
    i = 2
    while insp.has_table(f"{base}_{i}"):
        i += 1
    return f"{base}_{i}"


def _archive_table(bind, table: str) -> str | None:
    if not inspect(bind).has_table(table):
        return None
    archive = _unique_archive_name(bind, f"legacy_{table}_pre_6_3")
    # CTAS deliberately copies the data only. This avoids carrying legacy
    # constraints/sequences into the clean active schema while preserving all
    # original columns and rows for forensic/history access.
    bind.exec_driver_sql(f'CREATE TABLE "{archive}" AS SELECT * FROM "{table}"')
    return archive


def _drop_if_exists(table: str) -> None:
    bind = op.get_bind()
    if inspect(bind).has_table(table):
        op.drop_table(table)


def _create_scan_sessions() -> None:
    op.create_table(
        "scan_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="processing"),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scan_sessions_exam_id", "scan_sessions", ["exam_id"])
    op.create_index("ix_scan_sessions_source_sha256", "scan_sessions", ["source_sha256"])


def _create_scan_items() -> None:
    op.create_table(
        "scan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("scan_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("booklet", sa.String(8), nullable=True),
        sa.Column("token", sa.String(64), nullable=True),
        sa.Column("student_no_detected", sa.String(64), nullable=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="SET NULL"), nullable=True),
        sa.Column("page_fingerprint", sa.String(64), nullable=True),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.Column("issue_summary", sa.JSON(), nullable=False),
        sa.Column("preview_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("exam_id", "page_fingerprint", name="uq_exam_scan_fingerprint"),
    )
    op.create_index("ix_scan_items_session_id", "scan_items", ["session_id"])
    op.create_index("ix_scan_items_exam_id", "scan_items", ["exam_id"])
    op.create_index("ix_scan_items_student_no_detected", "scan_items", ["student_no_detected"])


def _create_scan_reviews() -> None:
    op.create_table(
        "scan_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scan_item_id", sa.Integer(), sa.ForeignKey("scan_items.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("resolved_student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_answers", sa.JSON(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scan_reviews_scan_item_id", "scan_reviews", ["scan_item_id"])
    op.create_index("ix_scan_reviews_exam_id", "scan_reviews", ["exam_id"])


def _create_answer_key_revisions() -> None:
    op.create_table(
        "answer_key_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("corrections", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("affected_responses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_answer_key_revisions_exam_id", "answer_key_revisions", ["exam_id"])


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    existing_scan_tables = [t for t in _REQUIRED if insp.has_table(t)]
    incompatible = False
    for table, required in _REQUIRED.items():
        cols = _columns(bind, table)
        if cols and not required.issubset(cols):
            incompatible = True

    # Partial presence is also unsafe because 6.3 treats the three tables as
    # one unit with inter-table foreign keys.
    if existing_scan_tables and len(existing_scan_tables) != len(_REQUIRED):
        incompatible = True

    if incompatible:
        # Archive in parent-to-child agnostic order first, then drop children
        # before parents. All legacy rows remain queryable in legacy_* tables.
        for table in ("scan_sessions", "scan_items", "scan_reviews"):
            _archive_table(bind, table)
        _drop_if_exists("scan_reviews")
        _drop_if_exists("scan_items")
        _drop_if_exists("scan_sessions")

    insp = inspect(bind)
    if not insp.has_table("scan_sessions"):
        _create_scan_sessions()
    if not inspect(bind).has_table("scan_items"):
        _create_scan_items()
    if not inspect(bind).has_table("scan_reviews"):
        _create_scan_reviews()
    if not inspect(bind).has_table("answer_key_revisions"):
        _create_answer_key_revisions()


def downgrade() -> None:
    # Intentionally non-destructive. This revision may have archived a legacy
    # schema. Automatically replacing the repaired schema with an incompatible
    # legacy schema would risk losing newer scan data.
    pass
