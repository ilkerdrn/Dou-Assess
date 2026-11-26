"""accreditation final report and finding revision history
Revision ID: 0028_accreditation_final_report
Revises: 0027_accreditation_response_decision
"""
from alembic import op
import sqlalchemy as sa
revision="0028_accreditation_final_report"
down_revision="0027_accreditation_response_decision"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("quality_accreditation_finding_revisions",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("finding_id",sa.Integer(),sa.ForeignKey("quality_accreditation_findings.id",ondelete="CASCADE"),nullable=False),sa.Column("application_id",sa.Integer(),sa.ForeignKey("quality_accreditation_applications.id",ondelete="CASCADE"),nullable=False),sa.Column("event_type",sa.String(48),nullable=False,server_default="updated"),sa.Column("before_payload",sa.JSON(),nullable=False),sa.Column("after_payload",sa.JSON(),nullable=False),sa.Column("rationale",sa.Text(),nullable=False,server_default=""),sa.Column("actor",sa.String(255),nullable=False,server_default=""),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_quality_accreditation_finding_revisions_finding_id","quality_accreditation_finding_revisions",["finding_id"]); op.create_index("ix_quality_accreditation_finding_revisions_application_id","quality_accreditation_finding_revisions",["application_id"])
    op.create_table("quality_accreditation_final_reports",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("application_id",sa.Integer(),sa.ForeignKey("quality_accreditation_applications.id",ondelete="CASCADE"),nullable=False,unique=True),sa.Column("status",sa.String(32),nullable=False,server_default="draft"),sa.Column("team_opinion",sa.Text(),nullable=False,server_default=""),sa.Column("institution_response_summary",sa.Text(),nullable=False,server_default=""),sa.Column("final_decision_code",sa.String(64),nullable=False,server_default=""),sa.Column("accreditation_start",sa.Date()),sa.Column("accreditation_end",sa.Date()),sa.Column("criterion_results",sa.JSON(),nullable=False),sa.Column("snapshot_payload",sa.JSON(),nullable=False),sa.Column("snapshot_sha256",sa.String(64),nullable=False,server_default=""),sa.Column("frozen_at",sa.DateTime(timezone=True)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_quality_accreditation_final_reports_application_id","quality_accreditation_final_reports",["application_id"],unique=True)
def downgrade():
    op.drop_table("quality_accreditation_final_reports"); op.drop_table("quality_accreditation_finding_revisions")
