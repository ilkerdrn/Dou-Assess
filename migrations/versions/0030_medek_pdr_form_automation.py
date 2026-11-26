"""MEDEK PDR form automation

Revision ID: 0030_medek_pdr_form_automation
Revises: 0029_medek_evaluator_pdr
"""
from alembic import op
import sqlalchemy as sa

revision = "0030_medek_pdr_form_automation"
down_revision = "0029_medek_evaluator_pdr"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "quality_medek_pdr_form_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("quality_accreditation_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("form_code", sa.String(16), nullable=False),
        sa.Column("subject_ref", sa.String(128), nullable=False, server_default="program"),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("analysis_payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.String(32), nullable=False, server_default="review"),
        sa.Column("reviewer", sa.String(255), nullable=False, server_default=""),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("application_id","form_code","subject_ref",name="uq_medek_pdr_form_application_subject"),
    )
    for col in ["application_id","form_code","subject_ref","result","status"]:
        op.create_index(f"ix_quality_medek_pdr_form_analyses_{col}","quality_medek_pdr_form_analyses",[col])

def downgrade():
    op.drop_table("quality_medek_pdr_form_analyses")
