"""6.2 official exam paper workflow and immutable paper snapshots

Revision ID: 0003_exam_paper_workflow
Revises: 0002_management_question_bank
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_exam_paper_workflow"
down_revision = "0002_management_question_bank"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("courses") as batch:
        batch.add_column(sa.Column("instructor_name", sa.String(length=255), nullable=False, server_default=""))

    with op.batch_alter_table("exams") as batch:
        batch.add_column(sa.Column("course_code_snapshot", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("course_name_snapshot", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("academic_year_snapshot", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("term_snapshot", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("instructor_snapshot", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("program_name_snapshot", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("department_snapshot", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("faculty_snapshot", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("paper_template_version", sa.String(length=64), nullable=False, server_default="dou-official-v1"))

    # Existing 6.1 exams receive a one-time immutable snapshot during upgrade.
    op.execute("""
        UPDATE exams SET
          course_code_snapshot = (SELECT c.code FROM courses c WHERE c.id = exams.course_id),
          course_name_snapshot = (SELECT c.name FROM courses c WHERE c.id = exams.course_id),
          academic_year_snapshot = (SELECT c.academic_year FROM courses c WHERE c.id = exams.course_id),
          term_snapshot = (SELECT c.term FROM courses c WHERE c.id = exams.course_id),
          instructor_snapshot = (SELECT CASE WHEN c.instructor_name <> '' THEN c.instructor_name ELSE c.instructor_email END FROM courses c WHERE c.id = exams.course_id),
          program_name_snapshot = (SELECT p.name FROM programs p JOIN courses c ON c.program_id = p.id WHERE c.id = exams.course_id),
          department_snapshot = (SELECT p.department FROM programs p JOIN courses c ON c.program_id = p.id WHERE c.id = exams.course_id),
          faculty_snapshot = (SELECT p.faculty FROM programs p JOIN courses c ON c.program_id = p.id WHERE c.id = exams.course_id)
        WHERE course_code_snapshot IS NULL
    """)

    with op.batch_alter_table("question_bank") as batch:
        batch.add_column(sa.Column("answer_lines", sa.Integer(), nullable=False, server_default="8"))
    with op.batch_alter_table("questions") as batch:
        batch.add_column(sa.Column("answer_lines", sa.Integer(), nullable=False, server_default="8"))


def downgrade() -> None:
    with op.batch_alter_table("questions") as batch:
        batch.drop_column("answer_lines")
    with op.batch_alter_table("question_bank") as batch:
        batch.drop_column("answer_lines")
    with op.batch_alter_table("exams") as batch:
        batch.drop_column("paper_template_version")
        batch.drop_column("faculty_snapshot")
        batch.drop_column("department_snapshot")
        batch.drop_column("program_name_snapshot")
        batch.drop_column("instructor_snapshot")
        batch.drop_column("term_snapshot")
        batch.drop_column("academic_year_snapshot")
        batch.drop_column("course_name_snapshot")
        batch.drop_column("course_code_snapshot")
    with op.batch_alter_table("courses") as batch:
        batch.drop_column("instructor_name")
