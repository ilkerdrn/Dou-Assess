"""Academic hierarchy, curriculum versions, catalog and course sections

Revision ID: 0032_academic_structure_foundation
Revises: 0031_medek_final_decision
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha1

from alembic import op
import sqlalchemy as sa

revision = "0032_academic_structure_foundation"
down_revision = "0031_medek_final_decision"
branch_labels = None
depends_on = None


def _legacy_code(prefix: str, value: str) -> str:
    digest = sha1(value.encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{digest}"


def upgrade():
    op.create_table(
        "academic_units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("unit_type", sa.String(32), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("academic_units.id", ondelete="SET NULL"), nullable=True),
        sa.Column("external_source", sa.String(64), nullable=False, server_default=""),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_academic_unit_code"),
        sa.CheckConstraint("unit_type IN ('institution','campus','faculty','vocational_school','institute','department','center')", name="ck_academic_unit_type"),
    )
    op.create_index("ix_academic_units_parent_id", "academic_units", ["parent_id"])
    op.create_index("ix_academic_units_external_id", "academic_units", ["external_id"])

    with op.batch_alter_table("programs") as batch:
        batch.add_column(sa.Column("academic_unit_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_programs_academic_unit", "academic_units", ["academic_unit_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_programs_academic_unit_id", ["academic_unit_id"])

    op.create_table(
        "curriculum_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("academic_year_start", sa.String(32), nullable=False, server_default=""),
        sa.Column("academic_year_end", sa.String(32), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("decision_ref", sa.String(255), nullable=False, server_default=""),
        sa.Column("revision_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("program_id", "code", name="uq_curriculum_version_program_code"),
        sa.CheckConstraint("status IN ('draft','active','retired')", name="ck_curriculum_version_status"),
    )
    op.create_index("ix_curriculum_versions_program_id", "curriculum_versions", ["program_id"])
    op.create_index("ix_curriculum_versions_status", "curriculum_versions", ["status"])

    op.create_table(
        "course_catalog_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ects", sa.Float(), nullable=False, server_default="0"),
        sa.Column("local_credits", sa.Float(), nullable=False, server_default="0"),
        sa.Column("default_semester_no", sa.Integer(), nullable=True),
        sa.Column("course_type", sa.String(32), nullable=False, server_default="required"),
        sa.Column("category", sa.String(64), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("program_id", "code", name="uq_course_catalog_program_code"),
    )
    op.create_index("ix_course_catalog_items_program_id", "course_catalog_items", ["program_id"])

    op.create_table(
        "curriculum_courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("curriculum_version_id", sa.Integer(), sa.ForeignKey("curriculum_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("catalog_item_id", sa.Integer(), sa.ForeignKey("course_catalog_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("semester_no", sa.Integer(), nullable=True),
        sa.Column("course_type", sa.String(32), nullable=False, server_default="required"),
        sa.Column("elective_group", sa.String(64), nullable=False, server_default=""),
        sa.Column("ects_override", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("curriculum_version_id", "catalog_item_id", name="uq_curriculum_catalog_item"),
    )
    op.create_index("ix_curriculum_courses_curriculum_version_id", "curriculum_courses", ["curriculum_version_id"])
    op.create_index("ix_curriculum_courses_catalog_item_id", "curriculum_courses", ["catalog_item_id"])

    op.create_table(
        "course_offerings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("catalog_item_id", sa.Integer(), sa.ForeignKey("course_catalog_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("curriculum_version_id", sa.Integer(), sa.ForeignKey("curriculum_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("section_code", sa.String(32), nullable=False, server_default="A"),
        sa.Column("campus", sa.String(128), nullable=False, server_default=""),
        sa.Column("delivery_mode", sa.String(32), nullable=False, server_default="face_to_face"),
        sa.Column("language", sa.String(32), nullable=False, server_default="TR"),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("external_source", sa.String(64), nullable=False, server_default=""),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("course_id", "section_code", name="uq_course_offering_section"),
        sa.CheckConstraint("status IN ('planned','active','closed','archived')", name="ck_course_offering_status"),
    )
    op.create_index("ix_course_offerings_course_id", "course_offerings", ["course_id"])
    op.create_index("ix_course_offerings_catalog_item_id", "course_offerings", ["catalog_item_id"])
    op.create_index("ix_course_offerings_curriculum_version_id", "course_offerings", ["curriculum_version_id"])
    op.create_index("ix_course_offerings_status", "course_offerings", ["status"])
    op.create_index("ix_course_offerings_external_id", "course_offerings", ["external_id"])

    op.create_table(
        "teaching_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_offering_id", sa.Integer(), sa.ForeignKey("course_offerings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("app_user_id", sa.Integer(), sa.ForeignKey("app_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("instructor_email", sa.String(255), nullable=False, server_default=""),
        sa.Column("instructor_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("role", sa.String(32), nullable=False, server_default="lead"),
        sa.Column("workload_hours", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_teaching_assignments_course_offering_id", "teaching_assignments", ["course_offering_id"])
    op.create_index("ix_teaching_assignments_app_user_id", "teaching_assignments", ["app_user_id"])
    op.create_index("ix_teaching_assignments_instructor_email", "teaching_assignments", ["instructor_email"])

    with op.batch_alter_table("courses") as batch:
        batch.add_column(sa.Column("catalog_item_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_courses_catalog_item", "course_catalog_items", ["catalog_item_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_courses_catalog_item_id", ["catalog_item_id"])
    with op.batch_alter_table("enrollments") as batch:
        batch.add_column(sa.Column("course_offering_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_enrollments_course_offering", "course_offerings", ["course_offering_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_enrollments_course_offering_id", ["course_offering_id"])
    with op.batch_alter_table("exams") as batch:
        batch.add_column(sa.Column("course_offering_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_exams_course_offering", "course_offerings", ["course_offering_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_exams_course_offering_id", ["course_offering_id"])

    # Compatibility backfill: existing flat faculty/department/course data becomes the new hierarchy.
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    bind.execute(sa.text("INSERT INTO academic_units (code,name,unit_type,parent_id,external_source,is_active,created_at) VALUES (:c,:n,'institution',NULL,'migration',TRUE,:dt)"), {"c":"DOGUS", "n":"Doğuş Üniversitesi", "dt":now})
    root_id = bind.execute(sa.text("SELECT id FROM academic_units WHERE code='DOGUS'")).scalar_one()
    programs = bind.execute(sa.text("SELECT id, code, name, faculty, department FROM programs ORDER BY id")).mappings().all()
    for pr in programs:
        parent_id = root_id
        faculty = (pr["faculty"] or "").strip()
        department = (pr["department"] or "").strip()
        if faculty:
            fcode = _legacy_code("LEGACY-FAC", faculty)
            existing = bind.execute(sa.text("SELECT id FROM academic_units WHERE code=:c"), {"c":fcode}).scalar_one_or_none()
            if existing is None:
                utype = "vocational_school" if ("MYO" in faculty.upper() or "MESLEK YÜKSEKOKUL" in faculty.upper()) else "faculty"
                bind.execute(sa.text("INSERT INTO academic_units (code,name,unit_type,parent_id,external_source,is_active,created_at) VALUES (:c,:n,:t,:p,'migration',TRUE,:dt)"), {"c":fcode,"n":faculty,"t":utype,"p":root_id,"dt":now})
                existing = bind.execute(sa.text("SELECT id FROM academic_units WHERE code=:c"), {"c":fcode}).scalar_one()
            parent_id = existing
        if department:
            dcode = _legacy_code("LEGACY-DEP", f"{parent_id}|{department}")
            dep_id = bind.execute(sa.text("SELECT id FROM academic_units WHERE code=:c"), {"c":dcode}).scalar_one_or_none()
            if dep_id is None:
                bind.execute(sa.text("INSERT INTO academic_units (code,name,unit_type,parent_id,external_source,is_active,created_at) VALUES (:c,:n,'department',:p,'migration',TRUE,:dt)"), {"c":dcode,"n":department,"p":parent_id,"dt":now})
                dep_id = bind.execute(sa.text("SELECT id FROM academic_units WHERE code=:c"), {"c":dcode}).scalar_one()
            parent_id = dep_id
        bind.execute(sa.text("UPDATE programs SET academic_unit_id=:u WHERE id=:p"), {"u":parent_id,"p":pr["id"]})

        cv_code = "LEGACY-CURRENT"
        bind.execute(sa.text("INSERT INTO curriculum_versions (program_id,code,name,status,decision_ref,revision_no,created_at) VALUES (:p,:c,:n,'active','6.58 migration',1,:dt)"), {"p":pr["id"],"c":cv_code,"n":"Mevcut Müfredat (Geçiş)","dt":now})
        cv_id = bind.execute(sa.text("SELECT id FROM curriculum_versions WHERE program_id=:p AND code=:c"), {"p":pr["id"],"c":cv_code}).scalar_one()
        courses = bind.execute(sa.text("SELECT id, code, name, academic_year, term, instructor_email, instructor_name FROM courses WHERE program_id=:p ORDER BY id"), {"p":pr["id"]}).mappings().all()
        catalog_by_code = {}
        for course in courses:
            ccode = course["code"]
            cat_id = catalog_by_code.get(ccode)
            if cat_id is None:
                cat_id = bind.execute(sa.text("SELECT id FROM course_catalog_items WHERE program_id=:p AND code=:c"), {"p":pr["id"],"c":ccode}).scalar_one_or_none()
                if cat_id is None:
                    bind.execute(sa.text("INSERT INTO course_catalog_items (program_id,code,name,course_type,is_active,created_at) VALUES (:p,:c,:n,'required',TRUE,:dt)"), {"p":pr["id"],"c":ccode,"n":course["name"],"dt":now})
                    cat_id = bind.execute(sa.text("SELECT id FROM course_catalog_items WHERE program_id=:p AND code=:c"), {"p":pr["id"],"c":ccode}).scalar_one()
                    bind.execute(sa.text("INSERT INTO curriculum_courses (curriculum_version_id,catalog_item_id,course_type,created_at) VALUES (:v,:i,'required',:dt)"), {"v":cv_id,"i":cat_id,"dt":now})
                catalog_by_code[ccode] = cat_id
            bind.execute(sa.text("UPDATE courses SET catalog_item_id=:cat WHERE id=:cid"), {"cat":cat_id,"cid":course["id"]})
            bind.execute(sa.text("INSERT INTO course_offerings (course_id,catalog_item_id,curriculum_version_id,section_code,status,external_source,created_at) VALUES (:cid,:cat,:cv,'A','active','migration',:dt)"), {"cid":course["id"],"cat":cat_id,"cv":cv_id,"dt":now})
            offering_id = bind.execute(sa.text("SELECT id FROM course_offerings WHERE course_id=:cid AND section_code='A'"), {"cid":course["id"]}).scalar_one()
            bind.execute(sa.text("UPDATE enrollments SET course_offering_id=:o WHERE course_id=:cid"), {"o":offering_id,"cid":course["id"]})
            bind.execute(sa.text("UPDATE exams SET course_offering_id=:o WHERE course_id=:cid"), {"o":offering_id,"cid":course["id"]})
            email = (course["instructor_email"] or "").strip().lower()
            name = (course["instructor_name"] or "").strip()
            if email or name:
                user_id = bind.execute(sa.text("SELECT id FROM app_users WHERE lower(email)=:e"), {"e":email}).scalar_one_or_none() if email else None
                bind.execute(sa.text("INSERT INTO teaching_assignments (course_offering_id,app_user_id,instructor_email,instructor_name,role,workload_hours,created_at) VALUES (:o,:u,:e,:n,'lead',0,:dt)"), {"o":offering_id,"u":user_id,"e":email,"n":name,"dt":now})


def downgrade():
    with op.batch_alter_table("exams") as batch:
        batch.drop_index("ix_exams_course_offering_id")
        batch.drop_constraint("fk_exams_course_offering", type_="foreignkey")
        batch.drop_column("course_offering_id")
    with op.batch_alter_table("enrollments") as batch:
        batch.drop_index("ix_enrollments_course_offering_id")
        batch.drop_constraint("fk_enrollments_course_offering", type_="foreignkey")
        batch.drop_column("course_offering_id")
    with op.batch_alter_table("courses") as batch:
        batch.drop_index("ix_courses_catalog_item_id")
        batch.drop_constraint("fk_courses_catalog_item", type_="foreignkey")
        batch.drop_column("catalog_item_id")
    op.drop_table("teaching_assignments")
    op.drop_table("course_offerings")
    op.drop_table("curriculum_courses")
    op.drop_table("course_catalog_items")
    op.drop_table("curriculum_versions")
    with op.batch_alter_table("programs") as batch:
        batch.drop_index("ix_programs_academic_unit_id")
        batch.drop_constraint("fk_programs_academic_unit", type_="foreignkey")
        batch.drop_column("academic_unit_id")
    op.drop_table("academic_units")
