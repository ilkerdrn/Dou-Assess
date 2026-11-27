"""grade change audit trail (response_grade_revisions)

Revision ID: 0043_response_grade_revisions
Revises: 0042_performance_production_hardening
"""
from alembic import op
import sqlalchemy as sa

revision = "0043_response_grade_revisions"
down_revision = "0042_performance_production_hardening"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade():
    if "response_grade_revisions" not in _tables():
        op.create_table("response_grade_revisions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("response_id", sa.Integer(), sa.ForeignKey("responses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("exam_student_id", sa.Integer(), sa.ForeignKey("exam_students.id", ondelete="CASCADE"), nullable=False),
            sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("previous_awarded_points", sa.Float(), nullable=False),
            sa.Column("new_awarded_points", sa.Float(), nullable=False),
            sa.Column("previous_rubric_scores", sa.JSON(), nullable=False),
            sa.Column("new_rubric_scores", sa.JSON(), nullable=False),
            sa.Column("source", sa.String(32), nullable=False),
            sa.Column("changed_by", sa.String(255), nullable=False, server_default=""),
            sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False))
        for col in ["response_id", "exam_student_id", "question_id", "source", "changed_at"]:
            op.create_index(f"ix_response_grade_revisions_{col}", "response_grade_revisions", [col])


def downgrade():
    if "response_grade_revisions" in _tables():
        op.drop_table("response_grade_revisions")
