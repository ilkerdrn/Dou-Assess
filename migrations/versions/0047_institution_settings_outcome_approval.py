"""institution settings and outcome change approval requests

Revision ID: 0047_institution_settings_outcome_approval
Revises: 0046_exam_student_extra_time
"""
from alembic import op
import sqlalchemy as sa

revision = "0047_institution_settings_outcome_approval"
down_revision = "0046_exam_student_extra_time"
branch_labels = None
depends_on = None


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "institution_settings" not in tables:
        op.create_table("institution_settings",
            sa.Column("key", sa.String(64), primary_key=True),
            sa.Column("value", sa.Text(), nullable=False, server_default=""),
            sa.Column("updated_by", sa.String(255), nullable=False, server_default=""),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    if "outcome_change_requests" not in tables:
        op.create_table("outcome_change_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("learning_outcome_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(16), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("before", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
            sa.Column("requested_by", sa.String(255), nullable=False, server_default=""),
            sa.Column("decided_by", sa.String(255), nullable=False, server_default=""),
            sa.Column("decision_note", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))
        for col in ["course_id", "learning_outcome_id", "status"]:
            op.create_index(f"ix_outcome_change_requests_{col}", "outcome_change_requests", [col])


def downgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    for t in ("outcome_change_requests", "institution_settings"):
        if t in tables:
            op.drop_table(t)
