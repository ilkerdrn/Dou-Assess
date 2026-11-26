"""program review and evidence hub 2.0

Revision ID: 0041_program_review_evidence_hub
Revises: 0040_operations_automation
"""
from alembic import op
import sqlalchemy as sa

revision = "0041_program_review_evidence_hub"
down_revision = "0040_operations_automation"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade():
    tables=_tables()
    if "program_review_templates" not in tables:
        op.create_table("program_review_templates",
            sa.Column("id",sa.Integer(),primary_key=True), sa.Column("code",sa.String(96),nullable=False),
            sa.Column("version",sa.String(32),nullable=False,server_default="1.0"), sa.Column("title",sa.String(255),nullable=False),
            sa.Column("description",sa.Text(),nullable=False,server_default=""), sa.Column("sections",sa.JSON(),nullable=False),
            sa.Column("active",sa.Boolean(),nullable=False,server_default=sa.true()), sa.Column("created_by",sa.String(255),nullable=False,server_default=""),
            sa.Column("created_at",sa.DateTime(timezone=True),nullable=False), sa.UniqueConstraint("code","version",name="uq_program_review_template_code_version"))
        op.create_index("ix_program_review_templates_code","program_review_templates",["code"]);op.create_index("ix_program_review_templates_active","program_review_templates",["active"])
    tables=_tables()
    if "program_reviews" not in tables:
        op.create_table("program_reviews",
            sa.Column("id",sa.Integer(),primary_key=True), sa.Column("program_id",sa.Integer(),sa.ForeignKey("programs.id",ondelete="CASCADE"),nullable=False),
            sa.Column("template_id",sa.Integer(),sa.ForeignKey("program_review_templates.id",ondelete="RESTRICT"),nullable=False), sa.Column("academic_year",sa.String(32),nullable=False),
            sa.Column("review_no",sa.Integer(),nullable=False,server_default="1"), sa.Column("title",sa.String(255),nullable=False), sa.Column("owner",sa.String(255),nullable=False,server_default=""),
            sa.Column("due_date",sa.Date(),nullable=True), sa.Column("status",sa.String(24),nullable=False,server_default="draft"), sa.Column("final_snapshot",sa.JSON(),nullable=False),
            sa.Column("final_sha256",sa.String(64),nullable=False,server_default=""), sa.Column("finalized_by",sa.String(255),nullable=False,server_default=""), sa.Column("finalized_at",sa.DateTime(timezone=True),nullable=True),
            sa.Column("created_at",sa.DateTime(timezone=True),nullable=False), sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
            sa.UniqueConstraint("program_id","academic_year","review_no",name="uq_program_review_cycle"), sa.CheckConstraint("status IN ('draft','in_progress','review','final','archived')",name="ck_program_review_status"))
        for col in ["program_id","template_id","academic_year","owner","due_date","status","final_sha256"]: op.create_index(f"ix_program_reviews_{col}","program_reviews",[col])
    tables=_tables()
    if "program_review_sections" not in tables:
        op.create_table("program_review_sections",
            sa.Column("id",sa.Integer(),primary_key=True), sa.Column("review_id",sa.Integer(),sa.ForeignKey("program_reviews.id",ondelete="CASCADE"),nullable=False),
            sa.Column("section_key",sa.String(96),nullable=False), sa.Column("title",sa.String(255),nullable=False), sa.Column("order_no",sa.Integer(),nullable=False,server_default="1"),
            sa.Column("guidance",sa.Text(),nullable=False,server_default=""), sa.Column("narrative",sa.Text(),nullable=False,server_default=""),
            sa.Column("contributor_email",sa.String(255),nullable=False,server_default=""), sa.Column("reviewer_email",sa.String(255),nullable=False,server_default=""),
            sa.Column("due_date",sa.Date(),nullable=True), sa.Column("status",sa.String(24),nullable=False,server_default="not_started"), sa.Column("reviewer_note",sa.Text(),nullable=False,server_default=""),
            sa.Column("submitted_at",sa.DateTime(timezone=True),nullable=True),sa.Column("approved_at",sa.DateTime(timezone=True),nullable=True),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
            sa.UniqueConstraint("review_id","section_key",name="uq_program_review_section"), sa.CheckConstraint("status IN ('not_started','in_progress','submitted','approved','changes_requested')",name="ck_program_review_section_status"))
        for col in ["review_id","section_key","contributor_email","reviewer_email","due_date","status"]: op.create_index(f"ix_program_review_sections_{col}","program_review_sections",[col])
    tables=_tables()
    if "program_review_evidence_links" not in tables:
        op.create_table("program_review_evidence_links",
            sa.Column("id",sa.Integer(),primary_key=True),sa.Column("section_id",sa.Integer(),sa.ForeignKey("program_review_sections.id",ondelete="CASCADE"),nullable=False),
            sa.Column("source_type",sa.String(24),nullable=False),sa.Column("source_id",sa.Integer(),nullable=False),sa.Column("note",sa.Text(),nullable=False,server_default=""),
            sa.Column("added_by",sa.String(255),nullable=False,server_default=""),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
            sa.UniqueConstraint("section_id","source_type","source_id",name="uq_program_review_evidence_link"),sa.CheckConstraint("source_type IN ('exam','quality','controlled')",name="ck_program_review_evidence_source"))
        for col in ["section_id","source_type","source_id"]: op.create_index(f"ix_program_review_evidence_links_{col}","program_review_evidence_links",[col])
    tables=_tables()
    if "evidence_tags" not in tables:
        op.create_table("evidence_tags",
            sa.Column("id",sa.Integer(),primary_key=True),sa.Column("source_type",sa.String(24),nullable=False),sa.Column("source_id",sa.Integer(),nullable=False),
            sa.Column("tag_key",sa.String(64),nullable=False),sa.Column("tag_label",sa.String(96),nullable=False),sa.Column("created_by",sa.String(255),nullable=False,server_default=""),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
            sa.UniqueConstraint("source_type","source_id","tag_key",name="uq_evidence_tag_source_key"),sa.CheckConstraint("source_type IN ('exam','quality','controlled')",name="ck_evidence_tag_source"))
        for col in ["source_type","source_id","tag_key"]: op.create_index(f"ix_evidence_tags_{col}","evidence_tags",[col])


def downgrade():
    for t in ["evidence_tags","program_review_evidence_links","program_review_sections","program_reviews","program_review_templates"]:
        if t in _tables(): op.drop_table(t)
