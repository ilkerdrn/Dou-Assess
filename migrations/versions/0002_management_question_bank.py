"""6.1 management and question bank

Revision ID: 0002_management_question_bank
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_management_question_bank"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_bank",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_type", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("default_points", sa.Float(), nullable=False, server_default="10"),
        sa.Column("correct_answer", sa.String(length=255), nullable=True),
        sa.Column("choices", sa.JSON(), nullable=True),
        sa.Column("learning_outcome_code", sa.String(length=64), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_question_bank_course_id", "question_bank", ["course_id"])
    with op.batch_alter_table("questions") as batch:
        batch.add_column(sa.Column("bank_question_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_questions_bank_question", "question_bank", ["bank_question_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_questions_bank_question_id", ["bank_question_id"])


def downgrade() -> None:
    with op.batch_alter_table("questions") as batch:
        batch.drop_index("ix_questions_bank_question_id")
        batch.drop_constraint("fk_questions_bank_question", type_="foreignkey")
        batch.drop_column("bank_question_id")
    op.drop_index("ix_question_bank_course_id", table_name="question_bank")
    op.drop_table("question_bank")
