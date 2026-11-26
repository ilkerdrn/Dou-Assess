"""Quality & Accreditation 360 center.

Revision ID: 0019_quality360
Revises: 0018_classic_assessment_standard
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_quality360"
down_revision = "0018_classic_assessment_standard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quality_framework_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=96), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("framework_family", sa.String(length=64), nullable=False),
        sa.Column("effective_from_year", sa.Integer(), nullable=True),
        sa.Column("transition_from_year", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("thresholds", sa.JSON(), nullable=False),
        sa.Column("source_meta", sa.JSON(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", "version", name="uq_quality_framework_profile_version"),
    )
    op.create_index("ix_quality_framework_profiles_code", "quality_framework_profiles", ["code"])
    op.create_index("ix_quality_framework_profiles_framework_family", "quality_framework_profiles", ["framework_family"])
    op.create_index("ix_quality_framework_profiles_status", "quality_framework_profiles", ["status"])

    op.create_table(
        "quality_curriculum_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year", sa.String(length=32), nullable=False),
        sa.Column("term", sa.String(length=32), nullable=False),
        sa.Column("class_level", sa.String(length=32), nullable=False, server_default="1. Sınıf"),
        sa.Column("course_code", sa.String(length=64), nullable=False),
        sa.Column("course_name", sa.String(length=255), nullable=False),
        sa.Column("ects", sa.Float(), nullable=False, server_default="0"),
        sa.Column("course_category", sa.String(length=96), nullable=False, server_default="Genel / Zorunlu"),
        sa.Column("is_professional", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_program_specific", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_external_stakeholder_supported", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_applied_or_current_tech", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="implemented"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("program_id", "academic_year", "course_code", name="uq_quality_curriculum_program_year_course"),
    )
    op.create_index("ix_quality_curriculum_items_program_id", "quality_curriculum_items", ["program_id"])
    op.create_index("ix_quality_curriculum_items_academic_year", "quality_curriculum_items", ["academic_year"])

    op.create_table(
        "quality_stakeholders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stakeholder_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("organization", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("engagement_type", sa.String(length=96), nullable=False, server_default="Görüş / Geri Bildirim"),
        sa.Column("engagement_date", sa.Date(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=False, server_default=""),
        sa.Column("resulting_action", sa.Text(), nullable=False, server_default=""),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="implemented"),
        sa.Column("evidence_ref", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quality_stakeholders_program_id", "quality_stakeholders", ["program_id"])
    op.create_index("ix_quality_stakeholders_stakeholder_type", "quality_stakeholders", ["stakeholder_type"])
    op.create_index("ix_quality_stakeholders_engagement_date", "quality_stakeholders", ["engagement_date"])

    op.create_table(
        "quality_graduates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("graduate_key", sa.String(length=128), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("graduation_year", sa.Integer(), nullable=True),
        sa.Column("employment_status", sa.String(length=64), nullable=False, server_default="Bilinmiyor"),
        sa.Column("employer", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("sector", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("job_title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("related_field", sa.Boolean(), nullable=True),
        sa.Column("survey_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("program_id", "graduate_key", name="uq_quality_graduate_program_key"),
    )
    op.create_index("ix_quality_graduates_program_id", "quality_graduates", ["program_id"])
    op.create_index("ix_quality_graduates_graduation_year", "quality_graduates", ["graduation_year"])
    op.create_index("ix_quality_graduates_employment_status", "quality_graduates", ["employment_status"])

    op.create_table(
        "quality_faculty",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("employment_type", sa.String(length=64), nullable=False, server_default="Tam Zamanlı"),
        sa.Column("expertise", sa.Text(), nullable=False, server_default=""),
        sa.Column("highest_degree", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("industry_experience_years", sa.Float(), nullable=False, server_default="0"),
        sa.Column("weekly_course_hours", sa.Float(), nullable=False, server_default="0"),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="implemented"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("program_id", "email", name="uq_quality_faculty_program_email"),
    )
    op.create_index("ix_quality_faculty_program_id", "quality_faculty", ["program_id"])

    op.create_table(
        "quality_infrastructure",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("infrastructure_type", sa.String(length=96), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="implemented"),
        sa.Column("accessibility_status", sa.String(length=32), nullable=False, server_default="implemented"),
        sa.Column("isg_status", sa.String(length=32), nullable=False, server_default="implemented"),
        sa.Column("last_review_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quality_infrastructure_program_id", "quality_infrastructure", ["program_id"])
    op.create_index("ix_quality_infrastructure_infrastructure_type", "quality_infrastructure", ["infrastructure_type"])

    op.create_table(
        "quality_cycles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year", sa.String(length=32), nullable=False),
        sa.Column("criterion_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("plan_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("do_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("check_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("act_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="planned"),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quality_cycles_program_id", "quality_cycles", ["program_id"])
    op.create_index("ix_quality_cycles_academic_year", "quality_cycles", ["academic_year"])
    op.create_index("ix_quality_cycles_criterion_code", "quality_cycles", ["criterion_code"])
    op.create_index("ix_quality_cycles_status", "quality_cycles", ["status"])

    op.create_table(
        "quality_governance_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body_type", sa.String(length=96), nullable=False),
        sa.Column("meeting_date", sa.Date(), nullable=True),
        sa.Column("meeting_no", sa.String(length=64), nullable=False),
        sa.Column("decision_no", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("decision_text", sa.Text(), nullable=False),
        sa.Column("related_criterion", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("source_stakeholder_id", sa.Integer(), sa.ForeignKey("quality_stakeholders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="implemented"),
        sa.Column("evidence_ref", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("program_id", "meeting_no", "decision_no", name="uq_quality_governance_decision"),
    )
    op.create_index("ix_quality_governance_decisions_program_id", "quality_governance_decisions", ["program_id"])
    op.create_index("ix_quality_governance_decisions_body_type", "quality_governance_decisions", ["body_type"])
    op.create_index("ix_quality_governance_decisions_meeting_date", "quality_governance_decisions", ["meeting_date"])
    op.create_index("ix_quality_governance_decisions_status", "quality_governance_decisions", ["status"])

    op.create_table(
        "quality_criterion_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("framework_profile_id", sa.Integer(), sa.ForeignKey("quality_framework_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year", sa.String(length=32), nullable=False),
        sa.Column("criterion_code", sa.String(length=64), nullable=False),
        sa.Column("maturity_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="planned"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("maturity_level >= 1 AND maturity_level <= 5", name="ck_quality_maturity_1_5"),
        sa.UniqueConstraint("program_id", "framework_profile_id", "academic_year", "criterion_code", name="uq_quality_criterion_assessment"),
    )
    op.create_index("ix_quality_criterion_assessments_program_id", "quality_criterion_assessments", ["program_id"])
    op.create_index("ix_quality_criterion_assessments_framework_profile_id", "quality_criterion_assessments", ["framework_profile_id"])
    op.create_index("ix_quality_criterion_assessments_academic_year", "quality_criterion_assessments", ["academic_year"])
    op.create_index("ix_quality_criterion_assessments_criterion_code", "quality_criterion_assessments", ["criterion_code"])

    op.create_table(
        "quality_evidence_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("criterion_code", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("entity_type", sa.String(length=64), nullable=False, server_default="program"),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False, server_default="document"),
        sa.Column("category", sa.String(length=96), nullable=False, server_default="quality"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(length=128), nullable=False, server_default="application/octet-stream"),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("retention_until", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quality_evidence_assets_program_id", "quality_evidence_assets", ["program_id"])
    op.create_index("ix_quality_evidence_assets_criterion_code", "quality_evidence_assets", ["criterion_code"])
    op.create_index("ix_quality_evidence_assets_sha256", "quality_evidence_assets", ["sha256"])


def downgrade() -> None:
    tables = [
        "quality_evidence_assets", "quality_criterion_assessments", "quality_governance_decisions",
        "quality_cycles", "quality_infrastructure", "quality_faculty", "quality_graduates",
        "quality_stakeholders", "quality_curriculum_items", "quality_framework_profiles",
    ]
    for table in tables:
        op.drop_table(table)
