"""Institutional accreditation readiness and approved cross-framework evidence mappings.

Revision ID: 0037_institutional_accreditation_readiness
Revises: 0036_program_assessment_assurance
"""
from alembic import op
import sqlalchemy as sa

revision = "0037_institutional_accreditation_readiness"
down_revision = "0036_program_assessment_assurance"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quality_accreditation_crosswalks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_framework_family", sa.String(64), nullable=False),
        sa.Column("source_framework_version", sa.String(64), nullable=False, server_default=""),
        sa.Column("source_criterion_code", sa.String(96), nullable=False),
        sa.Column("target_framework_family", sa.String(64), nullable=False),
        sa.Column("target_framework_version", sa.String(64), nullable=False, server_default=""),
        sa.Column("target_criterion_code", sa.String(96), nullable=False),
        sa.Column("relationship", sa.String(24), nullable=False, server_default="supports"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("review_status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("approved_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "source_framework_family", "source_framework_version", "source_criterion_code",
            "target_framework_family", "target_framework_version", "target_criterion_code",
            name="uq_quality_accreditation_crosswalk_pair",
        ),
        sa.CheckConstraint("relationship IN ('supports','related','equivalent')", name="ck_quality_crosswalk_relationship"),
        sa.CheckConstraint("review_status IN ('draft','approved','rejected')", name="ck_quality_crosswalk_review_status"),
    )
    for col in ("source_framework_family", "source_criterion_code", "target_framework_family", "target_criterion_code", "review_status"):
        op.create_index(f"ix_quality_accreditation_crosswalks_{col}", "quality_accreditation_crosswalks", [col])

    op.create_table(
        "quality_institutional_readiness_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("academic_year", sa.String(32), nullable=False),
        sa.Column("scope_type", sa.String(24), nullable=False, server_default="institution"),
        sa.Column("scope_key", sa.String(255), nullable=False, server_default="DOGUS"),
        sa.Column("snapshot_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("frozen_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("academic_year", "scope_type", "scope_key", "snapshot_no", name="uq_quality_readiness_snapshot"),
        sa.CheckConstraint("scope_type IN ('institution','faculty','program')", name="ck_quality_readiness_snapshot_scope"),
    )
    for col in ("academic_year", "scope_type", "scope_key", "content_sha256"):
        op.create_index(f"ix_quality_institutional_readiness_snapshots_{col}", "quality_institutional_readiness_snapshots", [col])


def downgrade():
    op.drop_table("quality_institutional_readiness_snapshots")
    op.drop_table("quality_accreditation_crosswalks")
