"""6.3 OMR scan station

Revision ID: 0004_omr_scan_station
Revises: 0003_exam_paper_workflow
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_omr_scan_station"
down_revision = "0003_exam_paper_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("scan_sessions",
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
    op.create_table("scan_items",
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
    op.create_table("scan_reviews",
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
    op.create_table("answer_key_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("corrections", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("affected_responses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_answer_key_revisions_exam_id", "answer_key_revisions", ["exam_id"])


def downgrade() -> None:
    op.drop_table("answer_key_revisions")
    op.drop_table("scan_reviews")
    op.drop_table("scan_items")
    op.drop_table("scan_sessions")
