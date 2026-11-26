"""6.4 accreditation center

Revision ID: 0005_accreditation_center
Revises: 0004_omr_scan_station
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_accreditation_center"
down_revision = "0004_omr_scan_station"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accreditation_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("required_general_evidence_kinds", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("required_representative_evidence_kinds", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("requires_representatives", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("requires_improvement_for_gaps", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", "version", name="uq_accreditation_profile_version"),
    )
    op.create_table(
        "accreditation_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("accreditation_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("academic_year", sa.String(32), nullable=False),
        sa.Column("term", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="collecting"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("program_id", "profile_id", "academic_year", "term", name="uq_accreditation_period"),
    )
    op.create_index("ix_accreditation_periods_program_id", "accreditation_periods", ["program_id"])
    op.create_index("ix_accreditation_periods_profile_id", "accreditation_periods", ["profile_id"])
    op.create_table(
        "accreditation_period_exams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("accreditation_periods.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("period_id", "exam_id", name="uq_accreditation_period_exam"),
    )
    op.create_index("ix_accreditation_period_exams_period_id", "accreditation_period_exams", ["period_id"])
    op.create_index("ix_accreditation_period_exams_exam_id", "accreditation_period_exams", ["exam_id"])
    op.create_table(
        "representative_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slot", sa.String(8), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("student_no", sa.String(64), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("class_average", sa.Float(), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("exam_id", "slot", name="uq_exam_representative_slot"),
    )
    op.create_index("ix_representative_snapshots_exam_id", "representative_snapshots", ["exam_id"])
    op.create_index("ix_representative_snapshots_student_id", "representative_snapshots", ["student_id"])


def downgrade() -> None:
    op.drop_table("representative_snapshots")
    op.drop_table("accreditation_period_exams")
    op.drop_table("accreditation_periods")
    op.drop_table("accreditation_profiles")
