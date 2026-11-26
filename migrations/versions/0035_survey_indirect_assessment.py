"""Survey and indirect assessment engine

Revision ID: 0035_survey_indirect_assessment
Revises: 0034_generic_assessment_rubric
"""
from alembic import op
import sqlalchemy as sa

revision = "0035_survey_indirect_assessment"
down_revision = "0034_generic_assessment_rubric"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "survey_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("survey_type", sa.String(32), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("target_percent", sa.Float(), nullable=False, server_default="60"),
        sa.Column("anonymous", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("program_id", "code", "version_no", name="uq_survey_program_code_version"),
        sa.CheckConstraint("survey_type IN ('student','graduate','employer','external_stakeholder','faculty','course_evaluation','program_evaluation')", name="ck_survey_type"),
        sa.CheckConstraint("status IN ('draft','active','retired')", name="ck_survey_template_status"),
    )
    for col in ("program_id","survey_type","status"):
        op.create_index(f"ix_survey_templates_{col}", "survey_templates", [col])

    op.create_table(
        "survey_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("survey_template_id", sa.Integer(), sa.ForeignKey("survey_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(24), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("order_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scale_min", sa.Float(), nullable=False, server_default="1"),
        sa.Column("scale_max", sa.Float(), nullable=False, server_default="5"),
        sa.Column("options", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("weight_percent", sa.Float(), nullable=False, server_default="100"),
        sa.Column("target_percent", sa.Float(), nullable=True),
        sa.UniqueConstraint("survey_template_id", "code", name="uq_survey_question_code"),
        sa.CheckConstraint("question_type IN ('likert','single_choice','multi_choice','open_text','nps')", name="ck_survey_question_type"),
    )
    op.create_index("ix_survey_questions_survey_template_id", "survey_questions", ["survey_template_id"])

    op.create_table(
        "survey_question_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("survey_question_id", sa.Integer(), sa.ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("program_outcome_id", sa.Integer(), sa.ForeignKey("program_outcomes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("objective_id", sa.Integer(), sa.ForeignKey("program_educational_objectives.id", ondelete="CASCADE"), nullable=True),
        sa.Column("framework_family", sa.String(64), nullable=False, server_default=""),
        sa.Column("criterion_code", sa.String(64), nullable=False, server_default=""),
        sa.Column("weight_percent", sa.Float(), nullable=False, server_default="100"),
        sa.UniqueConstraint("survey_question_id", "target_type", "program_outcome_id", "objective_id", "framework_family", "criterion_code", name="uq_survey_question_target"),
        sa.CheckConstraint("target_type IN ('program_outcome','pea','quality_criterion')", name="ck_survey_question_target_type"),
    )
    for col in ("survey_question_id","target_type","program_outcome_id","objective_id"):
        op.create_index(f"ix_survey_question_targets_{col}", "survey_question_targets", [col])

    op.create_table(
        "survey_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("survey_template_id", sa.Integer(), sa.ForeignKey("survey_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("academic_year", sa.String(32), nullable=False),
        sa.Column("term", sa.String(32), nullable=False, server_default=""),
        sa.Column("audience_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("public_token", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("survey_template_id", "academic_year", "term", "code", name="uq_survey_campaign_template_period_code"),
        sa.UniqueConstraint("public_token", name="uq_survey_campaign_public_token"),
        sa.CheckConstraint("status IN ('draft','open','closed','archived')", name="ck_survey_campaign_status"),
    )
    for col in ("survey_template_id","academic_year","audience_type","public_token","status"):
        op.create_index(f"ix_survey_campaigns_{col}", "survey_campaigns", [col])

    op.create_table(
        "survey_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("survey_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("response_key", sa.String(64), nullable=False),
        sa.Column("respondent_key_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("respondent_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("respondent_meta", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("campaign_id", "response_key", name="uq_survey_campaign_response_key"),
    )
    for col in ("campaign_id","respondent_key_hash","respondent_type","submitted_at"):
        op.create_index(f"ix_survey_responses_{col}", "survey_responses", [col])

    op.create_table(
        "survey_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("response_id", sa.Integer(), sa.ForeignKey("survey_responses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("numeric_value", sa.Float(), nullable=True),
        sa.Column("text_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("selected_options", sa.JSON(), nullable=False, server_default="[]"),
        sa.UniqueConstraint("response_id", "question_id", name="uq_survey_response_question"),
    )
    op.create_index("ix_survey_answers_response_id", "survey_answers", ["response_id"])
    op.create_index("ix_survey_answers_question_id", "survey_answers", ["question_id"])


def downgrade():
    op.drop_table("survey_answers")
    op.drop_table("survey_responses")
    op.drop_table("survey_campaigns")
    op.drop_table("survey_question_targets")
    op.drop_table("survey_questions")
    op.drop_table("survey_templates")
