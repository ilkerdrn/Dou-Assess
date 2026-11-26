"""Quality operations, attendance, grade locking and appeals.

Revision ID: 0017_quality_ops
Revises: 0016_classic_scan_grading
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_quality_ops"
down_revision = "0016_classic_scan_grading"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("exams", sa.Column("grade_locked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("exams", sa.Column("grade_locked_by", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("exams", sa.Column("grade_lock_note", sa.Text(), nullable=False, server_default=""))
    op.create_index("ix_exams_grade_locked_at", "exams", ["grade_locked_at"])

    op.add_column("exam_students", sa.Column("attendance_status", sa.String(length=24), nullable=False, server_default="attended"))
    op.add_column("exam_students", sa.Column("attendance_note", sa.Text(), nullable=False, server_default=""))
    op.add_column("exam_students", sa.Column("attendance_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_exam_students_attendance_status", "exam_students", ["attendance_status"])

    op.add_column("responses", sa.Column("graded_by", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("responses", sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("responses", sa.Column("revision_no", sa.Integer(), nullable=False, server_default="1"))

    for name, typ, default in [
        ("baseline_percent", sa.Float(), None), ("target_percent", sa.Float(), None), ("actual_percent", sa.Float(), None),
        ("verification_method", sa.Text(), ""), ("effectiveness_status", sa.String(length=32), "pending"),
        ("verified_by", sa.String(length=255), ""), ("verified_at", sa.DateTime(timezone=True), None),
        ("closure_note", sa.Text(), ""),
    ]:
        kwargs = {"nullable": True} if default is None else {"nullable": False, "server_default": default}
        op.add_column("improvement_actions", sa.Column(name, typ, **kwargs))

    op.create_table(
        "exam_incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="SET NULL"), nullable=True),
        sa.Column("incident_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="warning"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("resolution_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("resolved_by", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_exam_incidents_exam_id", "exam_incidents", ["exam_id"])
    op.create_index("ix_exam_incidents_student_id", "exam_incidents", ["student_id"])
    op.create_index("ix_exam_incidents_status", "exam_incidents", ["status"])
    op.create_index("ix_exam_incidents_severity", "exam_incidents", ["severity"])
    op.create_index("ix_exam_incidents_incident_type", "exam_incidents", ["incident_type"])

    op.create_table(
        "grade_appeals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("old_points", sa.Float(), nullable=True),
        sa.Column("new_points", sa.Float(), nullable=True),
        sa.Column("old_rubric_scores", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("new_rubric_scores", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("decision_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("decided_by", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_grade_appeals_exam_id", "grade_appeals", ["exam_id"])
    op.create_index("ix_grade_appeals_student_id", "grade_appeals", ["student_id"])
    op.create_index("ix_grade_appeals_question_id", "grade_appeals", ["question_id"])
    op.create_index("ix_grade_appeals_status", "grade_appeals", ["status"])


def downgrade() -> None:
    for idx, table in [
        ("ix_grade_appeals_status","grade_appeals"),("ix_grade_appeals_question_id","grade_appeals"),("ix_grade_appeals_student_id","grade_appeals"),("ix_grade_appeals_exam_id","grade_appeals")]:
        op.drop_index(idx, table_name=table)
    op.drop_table("grade_appeals")
    for idx, table in [
        ("ix_exam_incidents_incident_type","exam_incidents"),("ix_exam_incidents_severity","exam_incidents"),("ix_exam_incidents_status","exam_incidents"),("ix_exam_incidents_student_id","exam_incidents"),("ix_exam_incidents_exam_id","exam_incidents")]:
        op.drop_index(idx, table_name=table)
    op.drop_table("exam_incidents")
    for col in ["closure_note","verified_at","verified_by","effectiveness_status","verification_method","actual_percent","target_percent","baseline_percent"]:
        op.drop_column("improvement_actions", col)
    for col in ["revision_no","graded_at","graded_by"]:
        op.drop_column("responses", col)
    op.drop_index("ix_exam_students_attendance_status", table_name="exam_students")
    for col in ["attendance_updated_at","attendance_note","attendance_status"]:
        op.drop_column("exam_students", col)
    op.drop_index("ix_exams_grade_locked_at", table_name="exams")
    for col in ["grade_lock_note","grade_locked_by","grade_locked_at"]:
        op.drop_column("exams", col)
