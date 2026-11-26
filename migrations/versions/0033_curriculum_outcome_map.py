"""Curriculum outcome map I/R/M progression

Revision ID: 0033_curriculum_outcome_map
Revises: 0032_academic_structure_foundation
"""
from alembic import op
import sqlalchemy as sa

revision = "0033_curriculum_outcome_map"
down_revision = "0032_academic_structure_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "curriculum_outcome_maps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("curriculum_version_id", sa.Integer(), sa.ForeignKey("curriculum_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("catalog_item_id", sa.Integer(), sa.ForeignKey("course_catalog_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("program_outcome_id", sa.Integer(), sa.ForeignKey("program_outcomes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("coverage_level", sa.String(1), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("curriculum_version_id", "catalog_item_id", "program_outcome_id", name="uq_curriculum_course_po_map"),
        sa.CheckConstraint("coverage_level IN ('I','R','M')", name="ck_curriculum_coverage_level"),
    )
    op.create_index("ix_curriculum_outcome_maps_curriculum_version_id", "curriculum_outcome_maps", ["curriculum_version_id"])
    op.create_index("ix_curriculum_outcome_maps_catalog_item_id", "curriculum_outcome_maps", ["catalog_item_id"])
    op.create_index("ix_curriculum_outcome_maps_program_outcome_id", "curriculum_outcome_maps", ["program_outcome_id"])


def downgrade():
    op.drop_table("curriculum_outcome_maps")
