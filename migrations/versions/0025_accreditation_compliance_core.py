"""Accreditation compliance core: official framework snapshots, PEA/PO components,
student outcome cards, lifecycle/evaluator workspace, controlled documents, budget,
faculty CV/workload, graduate longitudinal tracking, infrastructure maintenance and
YOKAK mission-domain activities.

Revision ID: 0025_accreditation_compliance_core
Revises: 0024_mapping_contribution_1_5
"""
from alembic import op
from app.db import Base
from app import models  # noqa: F401 - registers metadata

revision = "0025_accreditation_compliance_core"
down_revision = "0024_mapping_contribution_1_5"
branch_labels = None
depends_on = None

NEW_TABLES = [
    "quality_framework_snapshots",
    "program_educational_objectives",
    "program_educational_objective_outcome_maps",
    "program_outcome_components",
    "student_outcome_snapshots",
    "quality_accreditation_applications",
    "quality_evaluator_workspaces",
    "quality_accreditation_document_requests",
    "quality_controlled_documents",
    "quality_controlled_document_revisions",
    "quality_budget_plans",
    "quality_budget_lines",
    "quality_faculty_cv_revisions",
    "quality_faculty_workload_records",
    "quality_graduate_followups",
    "quality_infrastructure_maintenance",
    "quality_mission_activities",
    "quality_accreditation_report_templates",
]


def upgrade():
    bind = op.get_bind()
    for name in NEW_TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)


def downgrade():
    bind = op.get_bind()
    for name in reversed(NEW_TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
