"""Strategic quality objectives and KPIs.

Revision ID: 0023_strategic_quality
Revises: 0022_quality_calendar
"""
from alembic import op
import sqlalchemy as sa

revision="0023_strategic_quality"
down_revision="0022_quality_calendar"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("quality_strategic_objectives",
      sa.Column("id",sa.Integer(),primary_key=True),sa.Column("academic_year",sa.String(32),nullable=False),
      sa.Column("scope_type",sa.String(32),nullable=False,server_default="university"),sa.Column("scope_name",sa.String(255),nullable=False,server_default="Doğuş Üniversitesi"),
      sa.Column("program_id",sa.Integer(),sa.ForeignKey("programs.id",ondelete="CASCADE"),nullable=True),sa.Column("code",sa.String(64),nullable=False),
      sa.Column("title",sa.String(255),nullable=False),sa.Column("description",sa.Text(),nullable=False,server_default=""),sa.Column("owner",sa.String(255),nullable=False,server_default=""),
      sa.Column("status",sa.String(32),nullable=False,server_default="active"),sa.Column("start_date",sa.Date(),nullable=True),sa.Column("due_date",sa.Date(),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
      sa.UniqueConstraint("academic_year","scope_type","scope_name","code",name="uq_quality_strategy_objective_scope_code"))
    for c in ["academic_year","scope_type","scope_name","program_id","code","status","due_date"]: op.create_index(f"ix_quality_strategic_objectives_{c}","quality_strategic_objectives",[c])
    op.create_table("quality_strategic_kpis",
      sa.Column("id",sa.Integer(),primary_key=True),sa.Column("objective_id",sa.Integer(),sa.ForeignKey("quality_strategic_objectives.id",ondelete="CASCADE"),nullable=False),
      sa.Column("code",sa.String(64),nullable=False),sa.Column("name",sa.String(255),nullable=False),sa.Column("unit",sa.String(32),nullable=False,server_default="%"),
      sa.Column("baseline_value",sa.Float(),nullable=False,server_default="0"),sa.Column("target_value",sa.Float(),nullable=False,server_default="100"),sa.Column("actual_value",sa.Float(),nullable=False,server_default="0"),
      sa.Column("weight",sa.Float(),nullable=False,server_default="1"),sa.Column("direction",sa.String(16),nullable=False,server_default="higher"),sa.Column("source_type",sa.String(64),nullable=False,server_default="manual"),
      sa.Column("source_ref",sa.String(255),nullable=False,server_default=""),sa.Column("status",sa.String(32),nullable=False,server_default="active"),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
      sa.UniqueConstraint("objective_id","code",name="uq_quality_strategy_kpi_objective_code"))
    for c in ["objective_id","code","source_type","status"]: op.create_index(f"ix_quality_strategic_kpis_{c}","quality_strategic_kpis",[c])

def downgrade():
    op.drop_table("quality_strategic_kpis"); op.drop_table("quality_strategic_objectives")
