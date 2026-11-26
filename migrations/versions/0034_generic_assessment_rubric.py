"""Generic assessment measures and reusable rubric engine

Revision ID: 0034_generic_assessment_rubric
Revises: 0033_curriculum_outcome_map
"""
from alembic import op
import sqlalchemy as sa

revision = "0034_generic_assessment_rubric"
down_revision = "0033_curriculum_outcome_map"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rubric_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("max_points", sa.Float(), nullable=False, server_default="100"),
        sa.Column("created_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("course_id", "title", "version_no", name="uq_rubric_course_title_version"),
        sa.CheckConstraint("status IN ('draft','active','retired')", name="ck_rubric_template_status"),
    )
    op.create_index("ix_rubric_templates_course_id", "rubric_templates", ["course_id"])
    op.create_index("ix_rubric_templates_status", "rubric_templates", ["status"])

    op.create_table(
        "rubric_criteria",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rubric_template_id", sa.Integer(), sa.ForeignKey("rubric_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("learning_outcome_id", sa.Integer(), sa.ForeignKey("learning_outcomes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("order_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_points", sa.Float(), nullable=False),
        sa.Column("weight_percent", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("rubric_template_id", "code", name="uq_rubric_criterion_code"),
    )
    op.create_index("ix_rubric_criteria_rubric_template_id", "rubric_criteria", ["rubric_template_id"])
    op.create_index("ix_rubric_criteria_learning_outcome_id", "rubric_criteria", ["learning_outcome_id"])

    op.create_table(
        "rubric_levels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rubric_criterion_id", sa.Integer(), sa.ForeignKey("rubric_criteria.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("score_percent", sa.Float(), nullable=False),
        sa.Column("order_no", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("rubric_criterion_id", "code", name="uq_rubric_level_code"),
    )
    op.create_index("ix_rubric_levels_rubric_criterion_id", "rubric_levels", ["rubric_criterion_id"])

    op.create_table(
        "assessment_measures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_offering_id", sa.Integer(), sa.ForeignKey("course_offerings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rubric_template_id", sa.Integer(), sa.ForeignKey("rubric_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("measure_type", sa.String(32), nullable=False),
        sa.Column("directness", sa.String(16), nullable=False, server_default="direct"),
        sa.Column("weight_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_points", sa.Float(), nullable=False, server_default="100"),
        sa.Column("target_percent", sa.Float(), nullable=False, server_default="60"),
        sa.Column("instructions", sa.Text(), nullable=False, server_default=""),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("course_id", "code", name="uq_assessment_measure_course_code"),
        sa.CheckConstraint("measure_type IN ('exam','assignment','project','presentation','laboratory','internship','portfolio','capstone','practical','peer_assessment')", name="ck_assessment_measure_type"),
        sa.CheckConstraint("status IN ('draft','active','closed','archived')", name="ck_assessment_measure_status"),
        sa.CheckConstraint("directness IN ('direct','indirect')", name="ck_assessment_measure_directness"),
    )
    for col in ("course_id","course_offering_id","rubric_template_id","status"):
        op.create_index(f"ix_assessment_measures_{col}", "assessment_measures", [col])

    op.create_table(
        "assessment_measure_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_measure_id", sa.Integer(), sa.ForeignKey("assessment_measures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("learning_outcome_id", sa.Integer(), sa.ForeignKey("learning_outcomes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weight_percent", sa.Float(), nullable=False, server_default="100"),
        sa.UniqueConstraint("assessment_measure_id", "learning_outcome_id", name="uq_measure_learning_outcome"),
    )
    op.create_index("ix_assessment_measure_outcomes_assessment_measure_id", "assessment_measure_outcomes", ["assessment_measure_id"])
    op.create_index("ix_assessment_measure_outcomes_learning_outcome_id", "assessment_measure_outcomes", ["learning_outcome_id"])

    op.create_table(
        "assessment_measure_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_measure_id", sa.Integer(), sa.ForeignKey("assessment_measures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rubric_scores", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("feedback", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("graded_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("assessment_measure_id", "student_id", name="uq_measure_student_result"),
    )
    op.create_index("ix_assessment_measure_results_assessment_measure_id", "assessment_measure_results", ["assessment_measure_id"])
    op.create_index("ix_assessment_measure_results_student_id", "assessment_measure_results", ["student_id"])


def downgrade():
    op.drop_table("assessment_measure_results")
    op.drop_table("assessment_measure_outcomes")
    op.drop_table("assessment_measures")
    op.drop_table("rubric_levels")
    op.drop_table("rubric_criteria")
    op.drop_table("rubric_templates")
