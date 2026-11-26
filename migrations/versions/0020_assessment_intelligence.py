"""Assessment intelligence: blueprint, review workflow, psychometric cache.

Revision ID: 0020_assessment_intelligence
Revises: 0019_quality360
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_assessment_intelligence"
down_revision = "0019_quality360"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("question_bank", sa.Column("review_status", sa.String(32), nullable=False, server_default="draft"))
    op.add_column("question_bank", sa.Column("review_note", sa.Text(), nullable=False, server_default=""))
    op.add_column("question_bank", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("question_bank", sa.Column("difficulty_index", sa.Float(), nullable=True))
    op.add_column("question_bank", sa.Column("discrimination_index", sa.Float(), nullable=True))
    op.add_column("question_bank", sa.Column("distractor_efficiency", sa.Float(), nullable=True))
    op.add_column("question_bank", sa.Column("psychometric_sample_size", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("question_bank", sa.Column("quality_status", sa.String(32), nullable=False, server_default="unmeasured"))
    op.create_index("ix_question_bank_review_status", "question_bank", ["review_status"])
    op.create_index("ix_question_bank_quality_status", "question_bank", ["quality_status"])
    # Existing institutional pool is trusted legacy content; only newly created rows start as draft.
    op.execute("UPDATE question_bank SET review_status = 'institutional' WHERE review_status = 'draft'")
    op.create_table("assessment_blueprints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_type", sa.String(64), nullable=False, server_default="Sınav"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("total_points", sa.Float(), nullable=False, server_default="100"),
        sa.Column("created_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("approved_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_assessment_blueprints_course_id", "assessment_blueprints", ["course_id"])
    op.create_index("ix_assessment_blueprints_status", "assessment_blueprints", ["status"])
    op.create_table("assessment_blueprint_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("blueprint_id", sa.Integer(), sa.ForeignKey("assessment_blueprints.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False, server_default=""),
        sa.Column("learning_outcome_code", sa.String(64), nullable=False, server_default=""),
        sa.Column("bloom_level", sa.String(64), nullable=False, server_default="understand"),
        sa.Column("difficulty", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("points", sa.Float(), nullable=False, server_default="5"),
        sa.Column("weight_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_assessment_blueprint_items_blueprint_id", "assessment_blueprint_items", ["blueprint_id"])

def downgrade():
    op.drop_index("ix_assessment_blueprint_items_blueprint_id", table_name="assessment_blueprint_items")
    op.drop_table("assessment_blueprint_items")
    op.drop_index("ix_assessment_blueprints_status", table_name="assessment_blueprints")
    op.drop_index("ix_assessment_blueprints_course_id", table_name="assessment_blueprints")
    op.drop_table("assessment_blueprints")
    op.drop_index("ix_question_bank_quality_status", table_name="question_bank")
    op.drop_index("ix_question_bank_review_status", table_name="question_bank")
    for c in ["quality_status","psychometric_sample_size","distractor_efficiency","discrimination_index","difficulty_index","reviewed_at","review_note","review_status"]:
        op.drop_column("question_bank", c)
