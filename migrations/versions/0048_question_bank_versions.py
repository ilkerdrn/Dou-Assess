"""question bank content version history

Revision ID: 0048_question_bank_versions
Revises: 0047_institution_settings_outcome_approval
"""
from alembic import op
import sqlalchemy as sa

revision = "0048_question_bank_versions"
down_revision = "0047_institution_settings_outcome_approval"
branch_labels = None
depends_on = None


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "question_bank_versions" not in tables:
        op.create_table("question_bank_versions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("question_bank_id", sa.Integer(), sa.ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version_no", sa.Integer(), nullable=False),
            sa.Column("snapshot", sa.JSON(), nullable=False),
            sa.Column("changed_by", sa.String(255), nullable=False, server_default=""),
            sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source", sa.String(32), nullable=False, server_default="edit"),
            sa.UniqueConstraint("question_bank_id", "version_no", name="uq_question_bank_version"))
        op.create_index("ix_question_bank_versions_qid", "question_bank_versions", ["question_bank_id"])


def downgrade():
    op.drop_index("ix_question_bank_versions_qid", table_name="question_bank_versions")
    op.drop_table("question_bank_versions")
