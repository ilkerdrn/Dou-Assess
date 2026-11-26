"""Normalize outcome contribution scale to 1-5.

Revision ID: 0024_mapping_contribution_1_5
Revises: 0023_strategic_quality
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_mapping_contribution_1_5"
down_revision = "0023_strategic_quality"
branch_labels = None
depends_on = None


def _drop_check_if_exists(table: str, name: str):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    names = {c.get("name") for c in insp.get_check_constraints(table)}
    if name in names:
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(name, type_="check")


def _ensure_check(table: str, name: str):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    names = {c.get("name") for c in insp.get_check_constraints(table)}
    if name not in names:
        with op.batch_alter_table(table) as batch:
            batch.create_check_constraint(name, "contribution >= 1 AND contribution <= 5")


def upgrade():
    # Legacy releases could persist 0. Product scale is now strictly 1..5.
    op.execute(sa.text("UPDATE outcome_mappings SET contribution = 1 WHERE contribution < 1"))
    op.execute(sa.text("UPDATE outcome_mappings SET contribution = 5 WHERE contribution > 5"))
    op.execute(sa.text("UPDATE exam_outcome_mappings SET contribution = 1 WHERE contribution < 1"))
    op.execute(sa.text("UPDATE exam_outcome_mappings SET contribution = 5 WHERE contribution > 5"))

    _drop_check_if_exists("outcome_mappings", "ck_contribution_1_5")
    _ensure_check("outcome_mappings", "ck_contribution_1_5")
    _ensure_check("exam_outcome_mappings", "ck_exam_contribution_1_5")


def downgrade():
    # Data remains valid after downgrade; only the new DB guards are removed.
    _drop_check_if_exists("exam_outcome_mappings", "ck_exam_contribution_1_5")
    _drop_check_if_exists("outcome_mappings", "ck_contribution_1_5")
