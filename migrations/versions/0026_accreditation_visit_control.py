"""MÜDEK evaluator, site-visit findings and 30-day response control center.

Revision ID: 0026_accreditation_visit_control
Revises: 0025_accreditation_compliance_core
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from app.db import Base
from app import models  # noqa: F401

revision = "0026_accreditation_visit_control"
down_revision = "0025_accreditation_compliance_core"
branch_labels = None
depends_on = None

NEW_TABLES = ["quality_accreditation_findings", "quality_accreditation_visit_notes"]

def _cols(bind, table):
    return {c["name"] for c in inspect(bind).get_columns(table)}

def upgrade():
    bind=op.get_bind()
    cols=_cols(bind,"quality_accreditation_applications")
    if "previous_application_id" not in cols:
        op.add_column("quality_accreditation_applications", sa.Column("previous_application_id", sa.Integer(), nullable=True))
        op.create_index("ix_quality_accreditation_applications_previous_application_id","quality_accreditation_applications",["previous_application_id"])
    if "evaluation_mode" not in cols:
        op.add_column("quality_accreditation_applications", sa.Column("evaluation_mode", sa.String(length=32), nullable=False, server_default="site_visit"))
        op.create_index("ix_quality_accreditation_applications_evaluation_mode","quality_accreditation_applications",["evaluation_mode"])
    dcols=_cols(bind,"quality_accreditation_document_requests")
    if "answered_at" not in dcols:
        op.add_column("quality_accreditation_document_requests", sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True))
    if "closed_at" not in dcols:
        op.add_column("quality_accreditation_document_requests", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    for name in NEW_TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)

def downgrade():
    bind=op.get_bind()
    for name in reversed(NEW_TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
    dcols=_cols(bind,"quality_accreditation_document_requests")
    if "closed_at" in dcols: op.drop_column("quality_accreditation_document_requests","closed_at")
    if "answered_at" in dcols: op.drop_column("quality_accreditation_document_requests","answered_at")
    cols=_cols(bind,"quality_accreditation_applications")
    if "evaluation_mode" in cols:
        op.drop_index("ix_quality_accreditation_applications_evaluation_mode",table_name="quality_accreditation_applications")
        op.drop_column("quality_accreditation_applications","evaluation_mode")
    if "previous_application_id" in cols:
        op.drop_index("ix_quality_accreditation_applications_previous_application_id",table_name="quality_accreditation_applications")
        op.drop_column("quality_accreditation_applications","previous_application_id")
