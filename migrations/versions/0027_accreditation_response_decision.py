"""accreditation response decision history

Revision ID: 0027_accreditation_response_decision
Revises: 0026_accreditation_visit_control
"""
from alembic import op
import sqlalchemy as sa

revision = "0027_accreditation_response_decision"
down_revision = "0026_accreditation_visit_control"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("quality_accreditation_decision_history",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("application_id",sa.Integer(),sa.ForeignKey("quality_accreditation_applications.id",ondelete="CASCADE"),nullable=False),
        sa.Column("action",sa.String(48),nullable=False),sa.Column("from_stage",sa.String(48),nullable=False,server_default=""),sa.Column("to_stage",sa.String(48),nullable=False,server_default=""),
        sa.Column("decision_code",sa.String(64),nullable=False,server_default=""),sa.Column("note",sa.Text(),nullable=False,server_default=""),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("actor",sa.String(255),nullable=False,server_default=""),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_quality_accreditation_decision_history_application_id","quality_accreditation_decision_history",["application_id"])
    op.create_index("ix_quality_accreditation_decision_history_action","quality_accreditation_decision_history",["action"])
    op.create_index("ix_quality_accreditation_decision_history_decision_code","quality_accreditation_decision_history",["decision_code"])

def downgrade():
    op.drop_table("quality_accreditation_decision_history")
