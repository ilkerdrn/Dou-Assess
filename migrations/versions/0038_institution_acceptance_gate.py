"""institution acceptance gate

Revision ID: 0038_institution_acceptance_gate
Revises: 0037_institutional_accreditation_readiness
"""
from alembic import op
import sqlalchemy as sa

revision = "0038_institution_acceptance_gate"
down_revision = "0037_institutional_accreditation_readiness"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "institution_acceptance_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("environment", sa.String(length=32), nullable=False, server_default="production"),
        sa.Column("gate_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("evidence_ref", sa.String(length=1024), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("verified_by", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("environment", "gate_key", name="uq_institution_acceptance_gate"),
        sa.CheckConstraint("status IN ('pending','passed','failed','waived')", name="ck_institution_acceptance_status"),
    )
    op.create_index("ix_institution_acceptance_records_environment", "institution_acceptance_records", ["environment"])
    op.create_index("ix_institution_acceptance_records_gate_key", "institution_acceptance_records", ["gate_key"])
    op.create_index("ix_institution_acceptance_records_status", "institution_acceptance_records", ["status"])


def downgrade():
    op.drop_index("ix_institution_acceptance_records_status", table_name="institution_acceptance_records")
    op.drop_index("ix_institution_acceptance_records_gate_key", table_name="institution_acceptance_records")
    op.drop_index("ix_institution_acceptance_records_environment", table_name="institution_acceptance_records")
    op.drop_table("institution_acceptance_records")
