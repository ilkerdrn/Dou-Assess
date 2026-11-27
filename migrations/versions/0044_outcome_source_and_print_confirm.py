"""learning outcome provenance/active flag and exam print confirmation

Revision ID: 0044_outcome_source_and_print_confirm
Revises: 0043_response_grade_revisions
"""
from alembic import op
import sqlalchemy as sa

revision = "0044_outcome_source_and_print_confirm"
down_revision = "0043_response_grade_revisions"
branch_labels = None
depends_on = None


def _cols(table):
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade():
    lo = _cols("learning_outcomes")
    if "source" not in lo:
        op.add_column("learning_outcomes", sa.Column("source", sa.String(24), nullable=False, server_default="assess"))
    if "is_active" not in lo:
        op.add_column("learning_outcomes", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    ex = _cols("exams")
    if "printed_at" not in ex:
        op.add_column("exams", sa.Column("printed_at", sa.DateTime(timezone=True), nullable=True))
    if "printed_by" not in ex:
        op.add_column("exams", sa.Column("printed_by", sa.String(255), nullable=False, server_default=""))


def downgrade():
    for table, col in (("exams", "printed_by"), ("exams", "printed_at"), ("learning_outcomes", "is_active"), ("learning_outcomes", "source")):
        if col in _cols(table):
            op.drop_column(table, col)
