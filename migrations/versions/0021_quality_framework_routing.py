"""University-wide quality framework routing.

Revision ID: 0021_quality_framework_routing
Revises: 0020_assessment_intelligence
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_quality_framework_routing"
down_revision = "0020_assessment_intelligence"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "quality_framework_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("framework_profile_id", sa.Integer(), sa.ForeignKey("quality_framework_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="auto"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("program_id", "framework_profile_id", name="uq_quality_framework_assignment_program_profile"),
    )
    op.create_index("ix_quality_framework_assignments_program_id", "quality_framework_assignments", ["program_id"])
    op.create_index("ix_quality_framework_assignments_framework_profile_id", "quality_framework_assignments", ["framework_profile_id"])
    op.create_index("ix_quality_framework_assignments_source", "quality_framework_assignments", ["source"])
    op.create_index("ix_quality_framework_assignments_is_primary", "quality_framework_assignments", ["is_primary"])
    op.create_index("ix_quality_framework_assignments_active", "quality_framework_assignments", ["active"])

def downgrade():
    op.drop_table("quality_framework_assignments")
