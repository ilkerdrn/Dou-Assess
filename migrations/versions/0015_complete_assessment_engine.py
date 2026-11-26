"""Complete assessment engine, paper studio, rubrics and evidence lifecycle.

Revision ID: 0015_complete_assessment_engine
Revises: 0014_exam_workspace
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_complete_assessment_engine"
down_revision = "0014_exam_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("pass_threshold_percent", sa.Float(), nullable=False, server_default="50"))
    op.add_column("students", sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_students_anonymized_at", "students", ["anonymized_at"])

    for name, col in [
        ("paper_size", sa.Column("paper_size", sa.String(length=8), nullable=False, server_default="A4")),
        ("paper_orientation", sa.Column("paper_orientation", sa.String(length=16), nullable=False, server_default="portrait")),
        ("omr_mode", sa.Column("omr_mode", sa.String(length=16), nullable=False, server_default="embedded")),
        ("duplex_print", sa.Column("duplex_print", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("revision_no", sa.Column("revision_no", sa.Integer(), nullable=False, server_default="1")),
        ("created_by_user_id", sa.Column("created_by_user_id", sa.Integer(), nullable=True)),
        ("created_by_email", sa.Column("created_by_email", sa.String(length=255), nullable=False, server_default="")),
        ("approval_requested_by", sa.Column("approval_requested_by", sa.String(length=255), nullable=False, server_default="")),
        ("approval_requested_at", sa.Column("approval_requested_at", sa.DateTime(timezone=True), nullable=True)),
        ("approved_by", sa.Column("approved_by", sa.String(length=255), nullable=False, server_default="")),
        ("approved_at", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True)),
        ("approval_note", sa.Column("approval_note", sa.Text(), nullable=False, server_default="")),
    ]:
        op.add_column("exams", col)
    op.create_index("ix_exams_created_by_user_id", "exams", ["created_by_user_id"])

    bank_columns = [
        sa.Column("topic", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("unit", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("difficulty", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("bloom_level", sa.String(length=64), nullable=False, server_default="understand"),
        sa.Column("author", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("reviewer", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("image_data", sa.Text(), nullable=True),
        sa.Column("rubric", sa.JSON(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    ]
    for col in bank_columns:
        op.add_column("question_bank", col)

    question_columns = [
        sa.Column("topic", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("unit", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("difficulty", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("bloom_level", sa.String(length=64), nullable=False, server_default="understand"),
        sa.Column("image_data", sa.Text(), nullable=True),
        sa.Column("rubric", sa.JSON(), nullable=True),
    ]
    for col in question_columns:
        op.add_column("questions", col)

    op.add_column("responses", sa.Column("rubric_scores", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

    for col in [
        sa.Column("category", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("retention_until", sa.Date(), nullable=True),
    ]:
        op.add_column("evidence_assets", col)


def downgrade() -> None:
    for name in ["retention_until", "version_no", "description", "category"]:
        op.drop_column("evidence_assets", name)
    op.drop_column("responses", "rubric_scores")
    for name in ["rubric", "image_data", "bloom_level", "difficulty", "unit", "topic"]:
        op.drop_column("questions", name)
    for name in ["last_used_at", "usage_count", "rubric", "image_data", "version_no", "reviewer", "author", "bloom_level", "difficulty", "unit", "topic"]:
        op.drop_column("question_bank", name)
    op.drop_index("ix_exams_created_by_user_id", table_name="exams")
    for name in ["approval_note", "approved_at", "approved_by", "approval_requested_at", "approval_requested_by", "created_by_email", "created_by_user_id", "revision_no", "duplex_print", "omr_mode", "paper_orientation", "paper_size"]:
        op.drop_column("exams", name)
    op.drop_index("ix_students_anonymized_at", table_name="students")
    op.drop_column("students", "anonymized_at")
    op.drop_column("courses", "pass_threshold_percent")
