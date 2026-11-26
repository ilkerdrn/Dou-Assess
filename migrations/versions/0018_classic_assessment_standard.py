"""Classic assessment expected-answer standard.

Revision ID: 0018_classic_assessment_standard
Revises: 0017_quality_ops
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_classic_assessment_standard"
down_revision = "0017_quality_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("question_bank", sa.Column("expected_answer", sa.Text(), nullable=False, server_default=""))
    op.add_column("questions", sa.Column("expected_answer", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("questions", "expected_answer")
    op.drop_column("question_bank", "expected_answer")
