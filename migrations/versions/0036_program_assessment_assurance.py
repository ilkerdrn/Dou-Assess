"""Program assessment assurance plan

Revision ID: 0036_program_assessment_assurance
Revises: 0035_survey_indirect_assessment
"""
from alembic import op
import sqlalchemy as sa

revision = "0036_program_assessment_assurance"
down_revision = "0035_survey_indirect_assessment"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assessment_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("direct_weight", sa.Float(), nullable=False, server_default="70"),
        sa.Column("indirect_weight", sa.Float(), nullable=False, server_default="30"),
        sa.Column("owner", sa.String(255), nullable=False, server_default=""),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("program_id", "academic_year", "version_no", name="uq_assessment_plan_program_year_version"),
        sa.CheckConstraint("status IN ('draft','active','reviewed','archived')", name="ck_assessment_plan_status"),
    )
    for col in ("program_id", "academic_year", "status"):
        op.create_index(f"ix_assessment_plans_{col}", "assessment_plans", [col])

    op.create_table(
        "assessment_plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_plan_id", sa.Integer(), sa.ForeignKey("assessment_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("program_outcome_id", sa.Integer(), sa.ForeignKey("program_outcomes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_entity_id", sa.Integer(), nullable=True),
        sa.Column("method_label", sa.String(255), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False, server_default=""),
        sa.Column("term", sa.String(32), nullable=False, server_default=""),
        sa.Column("frequency", sa.String(64), nullable=False, server_default="annual"),
        sa.Column("target_percent", sa.Float(), nullable=False, server_default="60"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("evidence_required", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(24), nullable=False, server_default="planned"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("channel IN ('direct','indirect')", name="ck_assessment_plan_item_channel"),
        sa.CheckConstraint("source_type IN ('exam','assessment_measure','survey','manual')", name="ck_assessment_plan_item_source_type"),
        sa.CheckConstraint("status IN ('planned','in_progress','collected','reviewed','cancelled')", name="ck_assessment_plan_item_status"),
    )
    for col in ("assessment_plan_id", "program_outcome_id", "channel", "source_type", "source_entity_id", "status"):
        op.create_index(f"ix_assessment_plan_items_{col}", "assessment_plan_items", [col])

    op.create_table(
        "assessment_plan_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_plan_id", sa.Integer(), sa.ForeignKey("assessment_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("review_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="final"),
        sa.Column("decision", sa.Text(), nullable=False, server_default=""),
        sa.Column("snapshot", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("reviewed_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("assessment_plan_id", "review_no", name="uq_assessment_plan_review_no"),
        sa.CheckConstraint("status IN ('draft','final')", name="ck_assessment_plan_review_status"),
    )
    op.create_index("ix_assessment_plan_reviews_assessment_plan_id", "assessment_plan_reviews", ["assessment_plan_id"])
    op.create_index("ix_assessment_plan_reviews_status", "assessment_plan_reviews", ["status"])


def downgrade():
    op.drop_table("assessment_plan_reviews")
    op.drop_table("assessment_plan_items")
    op.drop_table("assessment_plans")
