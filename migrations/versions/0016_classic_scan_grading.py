"""Classic scan page association and grading workspace.

Revision ID: 0016_classic_scan_grading
Revises: 0015_complete_assessment_engine
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_classic_scan_grading"
down_revision = "0015_complete_assessment_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scan_sessions", sa.Column("support_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("scan_items", sa.Column("page_kind", sa.String(length=32), nullable=False, server_default="omr"))
    op.add_column("scan_items", sa.Column("logical_page_no", sa.Integer(), nullable=True))
    op.add_column("scan_items", sa.Column("question_numbers", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.create_index("ix_scan_items_student_page_kind", "scan_items", ["exam_id", "student_id", "page_kind"])


def downgrade() -> None:
    op.drop_index("ix_scan_items_student_page_kind", table_name="scan_items")
    op.drop_column("scan_items", "question_numbers")
    op.drop_column("scan_items", "logical_page_no")
    op.drop_column("scan_items", "page_kind")
    op.drop_column("scan_sessions", "support_count")
