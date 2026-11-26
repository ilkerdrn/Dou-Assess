"""6.17 final exam workspace metadata

Revision ID: 0014_exam_workspace
Revises: 0013_multi_outcome_questions
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_exam_workspace"
down_revision = "0013_multi_outcome_questions"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("exams", sa.Column("start_time", sa.String(length=5), nullable=True))
    op.add_column("exams", sa.Column("location", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("exams", sa.Column("assessment_weight_percent", sa.Float(), nullable=True))
    op.add_column("exams", sa.Column("booklet_count", sa.Integer(), nullable=False, server_default="4"))
    op.add_column("exams", sa.Column("staff_notes", sa.Text(), nullable=False, server_default=""))
    op.create_index("ix_exams_date_status", "exams", ["exam_date", "status"], unique=False)

def downgrade() -> None:
    op.drop_index("ix_exams_date_status", table_name="exams")
    op.drop_column("exams", "staff_notes")
    op.drop_column("exams", "booklet_count")
    op.drop_column("exams", "assessment_weight_percent")
    op.drop_column("exams", "location")
    op.drop_column("exams", "start_time")
