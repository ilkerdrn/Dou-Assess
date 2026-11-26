"""evidence integrity and security

Revision ID: 0039_evidence_integrity_security
Revises: 0038_institution_acceptance_gate
"""
from alembic import op
import sqlalchemy as sa

revision = "0039_evidence_integrity_security"
down_revision = "0038_institution_acceptance_gate"
branch_labels = None
depends_on = None


def _column_names(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _index_names(table: str) -> set[str]:
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if column.name not in _column_names(table):
        op.add_column(table, column)


def _create_index_if_missing(name: str, table: str, columns: list[str]) -> None:
    if name not in _index_names(table):
        op.create_index(name, table, columns)


def _drop_column_if_exists(table: str, column: str) -> None:
    if column in _column_names(table):
        op.drop_column(table, column)


def _drop_index_if_exists(name: str, table: str) -> None:
    if name in _index_names(table):
        op.drop_index(name, table_name=table)


def _add_integrity_columns(table: str, prefix: str):
    _add_column_if_missing(table, sa.Column("integrity_status", sa.String(length=16), nullable=False, server_default="unchecked"))
    _add_column_if_missing(table, sa.Column("integrity_checked_at", sa.DateTime(timezone=True), nullable=True))
    _create_index_if_missing(f"ix_{prefix}_integrity_status", table, ["integrity_status"])


def upgrade():
    # Historical migration 0025 creates some tables from live SQLAlchemy metadata.
    # Fresh installs can therefore already contain these latest columns, while a
    # real 0038 production database does not. Conditional DDL keeps both paths safe.
    _add_integrity_columns("evidence_assets", "evidence_assets")
    _add_integrity_columns("quality_evidence_assets", "quality_evidence_assets")
    _add_integrity_columns("quality_controlled_document_revisions", "quality_controlled_document_revisions")

    _add_column_if_missing("quality_controlled_document_revisions", sa.Column("prepared_by", sa.String(length=255), nullable=False, server_default=""))
    _add_column_if_missing("quality_controlled_document_revisions", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("quality_controlled_document_revisions", sa.Column("reviewed_by", sa.String(length=255), nullable=False, server_default=""))
    _add_column_if_missing("quality_controlled_document_revisions", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    _create_index_if_missing("ix_quality_controlled_document_revisions_prepared_by", "quality_controlled_document_revisions", ["prepared_by"])

    _add_column_if_missing("quality_evaluator_workspaces", sa.Column("invitation_token_hash", sa.String(length=64), nullable=False, server_default=""))
    _add_column_if_missing("quality_evaluator_workspaces", sa.Column("token_issued_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("quality_evaluator_workspaces", sa.Column("last_access_at", sa.DateTime(timezone=True), nullable=True))
    _create_index_if_missing("ix_quality_evaluator_workspaces_invitation_token_hash", "quality_evaluator_workspaces", ["invitation_token_hash"])


def downgrade():
    _drop_index_if_exists("ix_quality_evaluator_workspaces_invitation_token_hash", "quality_evaluator_workspaces")
    _drop_column_if_exists("quality_evaluator_workspaces", "last_access_at")
    _drop_column_if_exists("quality_evaluator_workspaces", "token_issued_at")
    _drop_column_if_exists("quality_evaluator_workspaces", "invitation_token_hash")

    _drop_index_if_exists("ix_quality_controlled_document_revisions_prepared_by", "quality_controlled_document_revisions")
    _drop_column_if_exists("quality_controlled_document_revisions", "reviewed_at")
    _drop_column_if_exists("quality_controlled_document_revisions", "reviewed_by")
    _drop_column_if_exists("quality_controlled_document_revisions", "submitted_at")
    _drop_column_if_exists("quality_controlled_document_revisions", "prepared_by")

    for table, prefix in [
        ("quality_controlled_document_revisions", "quality_controlled_document_revisions"),
        ("quality_evidence_assets", "quality_evidence_assets"),
        ("evidence_assets", "evidence_assets"),
    ]:
        _drop_index_if_exists(f"ix_{prefix}_integrity_status", table)
        _drop_column_if_exists(table, "integrity_checked_at")
        _drop_column_if_exists(table, "integrity_status")
