"""MEDEK final decision metadata and institution report seal

Revision ID: 0031_medek_final_decision
Revises: 0030_medek_pdr_form_automation
"""
from alembic import op
import sqlalchemy as sa

revision = "0031_medek_final_decision"
down_revision = "0030_medek_pdr_form_automation"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("quality_accreditation_final_reports", sa.Column("accreditation_term_years", sa.Integer(), nullable=True))
    op.add_column("quality_accreditation_final_reports", sa.Column("next_review_type", sa.String(64), nullable=False, server_default=""))
    op.add_column("quality_accreditation_final_reports", sa.Column("next_review_due", sa.Date(), nullable=True))
    op.add_column("quality_accreditation_final_reports", sa.Column("decision_basis", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("quality_accreditation_final_reports", sa.Column("institution_report_sha256", sa.String(64), nullable=False, server_default=""))

def downgrade():
    for col in ["institution_report_sha256","decision_basis","next_review_due","next_review_type","accreditation_term_years"]:
        op.drop_column("quality_accreditation_final_reports", col)
