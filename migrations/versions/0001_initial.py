"""initial pilot schema - frozen 6.0 baseline

Revision ID: 0001_initial
Revises:

IMPORTANT: This migration intentionally imports a frozen metadata snapshot from
migrations.baseline_0001_models. Never import the live app.models here; doing so
would make fresh installations depend on future model changes.
"""
from alembic import op
from migrations.baseline_0001_models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
