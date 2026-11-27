"""versioned outcome success thresholds

Revision ID: 0045_outcome_thresholds
Revises: 0044_outcome_source_and_print_confirm
"""
from alembic import op
import sqlalchemy as sa

revision = "0045_outcome_thresholds"
down_revision = "0044_outcome_source_and_print_confirm"
branch_labels = None
depends_on = None


def upgrade():
    if "outcome_thresholds" not in set(sa.inspect(op.get_bind()).get_table_names()):
        op.create_table("outcome_thresholds",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=True),
            sa.Column("academic_year", sa.String(32), nullable=False, server_default=""),
            sa.Column("kind", sa.String(8), nullable=False),
            sa.Column("target_percent", sa.Float(), nullable=False),
            sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("note", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(255), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
        op.create_index("ix_outcome_thresholds_program_id", "outcome_thresholds", ["program_id"])
        op.create_index("ix_outcome_thresholds_is_active", "outcome_thresholds", ["is_active"])


def downgrade():
    if "outcome_thresholds" in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_table("outcome_thresholds")
