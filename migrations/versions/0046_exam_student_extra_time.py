"""per-student extra exam time (accommodation)

Revision ID: 0046_exam_student_extra_time
Revises: 0045_outcome_thresholds
"""
from alembic import op
import sqlalchemy as sa

revision = "0046_exam_student_extra_time"
down_revision = "0045_outcome_thresholds"
branch_labels = None
depends_on = None


def upgrade():
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("exam_students")}
    if "extra_time_percent" not in cols:
        op.add_column("exam_students", sa.Column("extra_time_percent", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("exam_students")}
    if "extra_time_percent" in cols:
        op.drop_column("exam_students", "extra_time_percent")
