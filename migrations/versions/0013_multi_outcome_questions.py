"""Multi-ÖÇ question mappings and navigation revision support.

Revision ID: 0013_multi_outcome_questions
Revises: 0012_security_performance_indexes
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_multi_outcome_questions"
down_revision = "0012_security_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_bank_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_bank_id", sa.Integer(), sa.ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False),
        sa.Column("learning_outcome_id", sa.Integer(), sa.ForeignKey("learning_outcomes.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("question_bank_id", "learning_outcome_id", name="uq_question_bank_outcome"),
    )
    op.create_index("ix_question_bank_outcomes_question", "question_bank_outcomes", ["question_bank_id"])
    op.create_index("ix_question_bank_outcomes_outcome", "question_bank_outcomes", ["learning_outcome_id"])

    op.create_table(
        "question_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_learning_outcome_id", sa.Integer(), sa.ForeignKey("exam_learning_outcomes.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("question_id", "exam_learning_outcome_id", name="uq_question_exam_outcome"),
    )
    op.create_index("ix_question_outcomes_question", "question_outcomes", ["question_id"])
    op.create_index("ix_question_outcomes_outcome", "question_outcomes", ["exam_learning_outcome_id"])

    # Backward-compatible migration: copy every existing single-ÖÇ mapping into
    # the new many-to-many tables. Legacy columns remain during the 6.x line so
    # older integrations can still read the primary/first outcome safely.
    op.execute(sa.text("""
        INSERT INTO question_bank_outcomes (question_bank_id, learning_outcome_id)
        SELECT qb.id, lo.id
        FROM question_bank qb
        JOIN learning_outcomes lo
          ON lo.course_id = qb.course_id
         AND lo.code = qb.learning_outcome_code
        WHERE qb.learning_outcome_code IS NOT NULL
          AND TRIM(qb.learning_outcome_code) <> ''
    """))
    op.execute(sa.text("""
        INSERT INTO question_outcomes (question_id, exam_learning_outcome_id)
        SELECT q.id, q.exam_learning_outcome_id
        FROM questions q
        WHERE q.exam_learning_outcome_id IS NOT NULL
    """))


def downgrade() -> None:
    op.drop_index("ix_question_outcomes_outcome", table_name="question_outcomes")
    op.drop_index("ix_question_outcomes_question", table_name="question_outcomes")
    op.drop_table("question_outcomes")
    op.drop_index("ix_question_bank_outcomes_outcome", table_name="question_bank_outcomes")
    op.drop_index("ix_question_bank_outcomes_question", table_name="question_bank_outcomes")
    op.drop_table("question_bank_outcomes")
