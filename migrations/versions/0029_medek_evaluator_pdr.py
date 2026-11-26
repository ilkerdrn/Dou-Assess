"""MEDEK evaluator PDR workflow
Revision ID: 0029_medek_evaluator_pdr
Revises: 0028_accreditation_final_report
"""
from alembic import op
import sqlalchemy as sa
revision="0029_medek_evaluator_pdr"
down_revision="0028_accreditation_final_report"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("quality_medek_evaluator_report_items",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("application_id",sa.Integer(),sa.ForeignKey("quality_accreditation_applications.id",ondelete="CASCADE"),nullable=False),
        sa.Column("workspace_id",sa.Integer(),sa.ForeignKey("quality_evaluator_workspaces.id",ondelete="SET NULL"),nullable=True),
        sa.Column("source_item_id",sa.Integer(),nullable=True),
        sa.Column("report_phase",sa.String(32),nullable=False,server_default="individual"),
        sa.Column("criterion_code",sa.String(64),nullable=False,server_default=""),
        sa.Column("evaluator_name",sa.String(255),nullable=False,server_default=""),
        sa.Column("item_type",sa.String(32),nullable=False),
        sa.Column("narrative",sa.Text(),nullable=False,server_default=""),
        sa.Column("assessment_value",sa.String(64),nullable=False,server_default=""),
        sa.Column("evidence_refs",sa.JSON(),nullable=False),
        sa.Column("status",sa.String(32),nullable=False,server_default="draft"),
        sa.Column("carried_forward",sa.Boolean(),nullable=False,server_default=sa.false()),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
    )
    for c in ["application_id","workspace_id","source_item_id","report_phase","criterion_code","item_type","status","carried_forward"]:
        op.create_index(f"ix_quality_medek_evaluator_report_items_{c}","quality_medek_evaluator_report_items",[c])
def downgrade():
    op.drop_table("quality_medek_evaluator_report_items")
