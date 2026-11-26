from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models as m
from .authz import current_user, require_course_access, require_course_management, require_program_access, require_roles
from .db import get_db

router = APIRouter(prefix="/api", tags=["Academic Structure"])

UNIT_TYPES = {"institution", "campus", "faculty", "vocational_school", "institute", "department", "center"}


def _commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _audit(db: Session, action: str, entity_type: str, entity_id: int | None, payload: dict) -> None:
    try:
        actor = current_user()
    except Exception:
        actor = {"id": None, "email": "system", "role_names": []}
    db.add(m.AuditLog(
        actor_user_id=actor.get("id"), actor_email=actor.get("email") or "system",
        actor_roles=list(actor.get("role_names") or []), action=action,
        entity_type=entity_type, entity_id=entity_id, payload=payload,
    ))


class AcademicUnitCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    unit_type: Literal["institution", "campus", "faculty", "vocational_school", "institute", "department", "center"]
    parent_id: Optional[int] = None
    external_source: str = Field(default="", max_length=64)
    external_id: Optional[str] = Field(default=None, max_length=128)


class AcademicUnitUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    unit_type: Optional[Literal["institution", "campus", "faculty", "vocational_school", "institute", "department", "center"]] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None


class CurriculumVersionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    academic_year_start: str = Field(default="", max_length=32)
    academic_year_end: str = Field(default="", max_length=32)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    decision_ref: str = Field(default="", max_length=255)


class CatalogItemCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    ects: float = Field(default=0, ge=0, le=60)
    local_credits: float = Field(default=0, ge=0, le=60)
    default_semester_no: Optional[int] = Field(default=None, ge=1, le=20)
    course_type: Literal["required", "elective"] = "required"
    category: str = Field(default="", max_length=64)
    description: str = Field(default="", max_length=8000)


class CurriculumCourseCreate(BaseModel):
    catalog_item_id: int
    semester_no: Optional[int] = Field(default=None, ge=1, le=20)
    course_type: Literal["required", "elective"] = "required"
    elective_group: str = Field(default="", max_length=64)
    ects_override: Optional[float] = Field(default=None, ge=0, le=60)


class CourseOfferingCreate(BaseModel):
    section_code: str = Field(default="A", min_length=1, max_length=32)
    catalog_item_id: Optional[int] = None
    curriculum_version_id: Optional[int] = None
    campus: str = Field(default="", max_length=128)
    delivery_mode: Literal["face_to_face", "hybrid", "online"] = "face_to_face"
    language: str = Field(default="TR", max_length=32)
    capacity: Optional[int] = Field(default=None, ge=1, le=5000)
    status: Literal["planned", "active", "closed", "archived"] = "active"


class TeachingAssignmentCreate(BaseModel):
    app_user_id: Optional[int] = None
    instructor_email: str = Field(default="", max_length=255)
    instructor_name: str = Field(default="", max_length=255)
    role: Literal["lead", "co_instructor", "assistant"] = "lead"
    workload_hours: float = Field(default=0, ge=0, le=168)


def _unit_out(row: m.AcademicUnit) -> dict:
    return {
        "id": row.id, "code": row.code, "name": row.name, "unit_type": row.unit_type,
        "parent_id": row.parent_id, "is_active": row.is_active,
        "external_source": row.external_source or "", "external_id": row.external_id,
    }


def _unit_chain(db: Session, unit_id: int | None) -> list[dict]:
    chain = []
    seen: set[int] = set()
    current = db.get(m.AcademicUnit, unit_id) if unit_id else None
    while current and current.id not in seen:
        seen.add(current.id)
        chain.append(_unit_out(current))
        current = db.get(m.AcademicUnit, current.parent_id) if current.parent_id else None
    return list(reversed(chain))


@router.get("/academic-units")
def list_academic_units(parent_id: int | None = None, active_only: bool = True, db: Session = Depends(get_db)):
    stmt = select(m.AcademicUnit).order_by(m.AcademicUnit.name)
    if parent_id is not None:
        stmt = stmt.where(m.AcademicUnit.parent_id == parent_id)
    if active_only:
        stmt = stmt.where(m.AcademicUnit.is_active.is_(True))
    return [_unit_out(x) for x in db.scalars(stmt).all()]


@router.post("/academic-units", status_code=201)
def create_academic_unit(data: AcademicUnitCreate, db: Session = Depends(get_db)):
    require_roles("admin")
    if data.parent_id is not None and not db.get(m.AcademicUnit, data.parent_id):
        raise HTTPException(404, "Üst akademik birim bulunamadı")
    obj = m.AcademicUnit(**data.model_dump())
    db.add(obj); db.flush(); _audit(db, "create", "academic_unit", obj.id, data.model_dump()); _commit(db)
    return _unit_out(obj)


@router.patch("/academic-units/{unit_id}")
def update_academic_unit(unit_id: int, data: AcademicUnitUpdate, db: Session = Depends(get_db)):
    require_roles("admin")
    obj = db.get(m.AcademicUnit, unit_id)
    if not obj: raise HTTPException(404, "Akademik birim bulunamadı")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("parent_id") == unit_id:
        raise HTTPException(400, "Akademik birim kendisinin üst birimi olamaz")
    if changes.get("parent_id") is not None and not db.get(m.AcademicUnit, changes["parent_id"]):
        raise HTTPException(404, "Üst akademik birim bulunamadı")
    for key, value in changes.items(): setattr(obj, key, value)
    _audit(db, "update", "academic_unit", obj.id, changes); _commit(db)
    return _unit_out(obj)


@router.get("/programs/{program_id}/academic-structure")
def program_academic_structure(program_id: int, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=False)
    program = db.get(m.Program, program_id)
    if not program: raise HTTPException(404, "Program bulunamadı")
    versions = list(db.scalars(select(m.CurriculumVersion).where(m.CurriculumVersion.program_id == program_id).order_by(m.CurriculumVersion.id.desc())).all())
    catalog_count = db.scalar(select(func.count()).select_from(m.CourseCatalogItem).where(m.CourseCatalogItem.program_id == program_id)) or 0
    course_ids = list(db.scalars(select(m.Course.id).where(m.Course.program_id == program_id)).all())
    offering_count = db.scalar(select(func.count()).select_from(m.CourseOffering).where(m.CourseOffering.course_id.in_(course_ids))) or 0 if course_ids else 0
    return {
        "program": {"id": program.id, "code": program.code, "name": program.name, "academic_unit_id": program.academic_unit_id},
        "unit_chain": _unit_chain(db, program.academic_unit_id),
        "curriculum_versions": [{"id": x.id, "code": x.code, "name": x.name, "status": x.status, "academic_year_start": x.academic_year_start, "academic_year_end": x.academic_year_end, "revision_no": x.revision_no, "decision_ref": x.decision_ref} for x in versions],
        "catalog_item_count": int(catalog_count),
        "course_count": len(course_ids),
        "offering_count": int(offering_count),
    }


@router.get("/programs/{program_id}/curriculum-versions")
def list_curriculum_versions(program_id: int, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=False)
    rows = db.scalars(select(m.CurriculumVersion).where(m.CurriculumVersion.program_id == program_id).order_by(m.CurriculumVersion.id.desc())).all()
    return [{"id": x.id, "program_id": x.program_id, "code": x.code, "name": x.name, "academic_year_start": x.academic_year_start, "academic_year_end": x.academic_year_end, "status": x.status, "effective_from": x.effective_from.isoformat() if x.effective_from else None, "effective_to": x.effective_to.isoformat() if x.effective_to else None, "decision_ref": x.decision_ref, "revision_no": x.revision_no} for x in rows]


@router.post("/programs/{program_id}/curriculum-versions", status_code=201)
def create_curriculum_version(program_id: int, data: CurriculumVersionCreate, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=True)
    if not db.get(m.Program, program_id): raise HTTPException(404, "Program bulunamadı")
    obj = m.CurriculumVersion(program_id=program_id, status="draft", **data.model_dump())
    db.add(obj); db.flush(); _audit(db, "create", "curriculum_version", obj.id, data.model_dump()); _commit(db)
    return {"id": obj.id, "program_id": obj.program_id, "code": obj.code, "name": obj.name, "status": obj.status}


@router.post("/curriculum-versions/{version_id}/activate")
def activate_curriculum_version(version_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.CurriculumVersion, version_id)
    if not obj: raise HTTPException(404, "Müfredat versiyonu bulunamadı")
    require_program_access(db, obj.program_id, write=True)
    active_rows = db.scalars(select(m.CurriculumVersion).where(m.CurriculumVersion.program_id == obj.program_id, m.CurriculumVersion.status == "active", m.CurriculumVersion.id != obj.id)).all()
    for row in active_rows: row.status = "retired"
    obj.status = "active"; obj.revision_no = int(obj.revision_no or 1) + 1
    _audit(db, "activate", "curriculum_version", obj.id, {"retired_ids": [x.id for x in active_rows]}); _commit(db)
    return {"id": obj.id, "status": obj.status, "revision_no": obj.revision_no}


@router.get("/programs/{program_id}/course-catalog")
def list_course_catalog(program_id: int, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=False)
    rows = db.scalars(select(m.CourseCatalogItem).where(m.CourseCatalogItem.program_id == program_id).order_by(m.CourseCatalogItem.code)).all()
    return [{"id": x.id, "program_id": x.program_id, "code": x.code, "name": x.name, "ects": x.ects, "local_credits": x.local_credits, "default_semester_no": x.default_semester_no, "course_type": x.course_type, "category": x.category, "description": x.description, "is_active": x.is_active} for x in rows]


@router.post("/programs/{program_id}/course-catalog", status_code=201)
def create_course_catalog_item(program_id: int, data: CatalogItemCreate, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=True)
    if not db.get(m.Program, program_id): raise HTTPException(404, "Program bulunamadı")
    obj = m.CourseCatalogItem(program_id=program_id, **data.model_dump())
    db.add(obj); db.flush(); _audit(db, "create", "course_catalog_item", obj.id, data.model_dump()); _commit(db)
    return {"id": obj.id, "program_id": obj.program_id, "code": obj.code, "name": obj.name, "ects": obj.ects, "course_type": obj.course_type}


@router.get("/curriculum-versions/{version_id}/courses")
def curriculum_courses(version_id: int, db: Session = Depends(get_db)):
    version = db.get(m.CurriculumVersion, version_id)
    if not version: raise HTTPException(404, "Müfredat versiyonu bulunamadı")
    require_program_access(db, version.program_id, write=False)
    rows = db.scalars(select(m.CurriculumCourse).where(m.CurriculumCourse.curriculum_version_id == version_id).order_by(m.CurriculumCourse.semester_no, m.CurriculumCourse.id)).all()
    out = []
    for x in rows:
        item = db.get(m.CourseCatalogItem, x.catalog_item_id)
        out.append({"id": x.id, "catalog_item_id": x.catalog_item_id, "code": item.code if item else "", "name": item.name if item else "", "semester_no": x.semester_no, "course_type": x.course_type, "elective_group": x.elective_group, "ects": x.ects_override if x.ects_override is not None else (item.ects if item else 0)})
    return out


@router.post("/curriculum-versions/{version_id}/courses", status_code=201)
def add_curriculum_course(version_id: int, data: CurriculumCourseCreate, db: Session = Depends(get_db)):
    version = db.get(m.CurriculumVersion, version_id)
    item = db.get(m.CourseCatalogItem, data.catalog_item_id)
    if not version or not item: raise HTTPException(404, "Müfredat veya ders kataloğu kaydı bulunamadı")
    require_program_access(db, version.program_id, write=True)
    if item.program_id != version.program_id: raise HTTPException(400, "Ders ve müfredat aynı programa ait olmalıdır")
    obj = m.CurriculumCourse(curriculum_version_id=version_id, **data.model_dump())
    db.add(obj); db.flush(); _audit(db, "create", "curriculum_course", obj.id, data.model_dump()); _commit(db)
    return {"id": obj.id, "curriculum_version_id": version_id, **data.model_dump()}


@router.get("/courses/{course_id}/offerings")
def list_course_offerings(course_id: int, db: Session = Depends(get_db)):
    require_course_access(db, course_id, write=False)
    rows = db.scalars(select(m.CourseOffering).where(m.CourseOffering.course_id == course_id).order_by(m.CourseOffering.section_code)).all()
    return [{"id": x.id, "course_id": x.course_id, "catalog_item_id": x.catalog_item_id, "curriculum_version_id": x.curriculum_version_id, "section_code": x.section_code, "campus": x.campus, "delivery_mode": x.delivery_mode, "language": x.language, "capacity": x.capacity, "status": x.status} for x in rows]


@router.post("/courses/{course_id}/offerings", status_code=201)
def create_course_offering(course_id: int, data: CourseOfferingCreate, db: Session = Depends(get_db)):
    require_course_management(db, course_id)
    course = db.get(m.Course, course_id)
    if not course: raise HTTPException(404, "Ders bulunamadı")
    catalog_item_id = data.catalog_item_id or course.catalog_item_id
    if catalog_item_id:
        item = db.get(m.CourseCatalogItem, catalog_item_id)
        if not item or item.program_id != course.program_id: raise HTTPException(400, "Katalog dersi programla uyumlu değil")
    if data.curriculum_version_id:
        cv = db.get(m.CurriculumVersion, data.curriculum_version_id)
        if not cv or cv.program_id != course.program_id: raise HTTPException(400, "Müfredat versiyonu programla uyumlu değil")
    obj = m.CourseOffering(course_id=course_id, catalog_item_id=catalog_item_id, **data.model_dump(exclude={"catalog_item_id"}))
    db.add(obj); db.flush(); _audit(db, "create", "course_offering", obj.id, data.model_dump()); _commit(db)
    return {"id": obj.id, "course_id": obj.course_id, "section_code": obj.section_code, "status": obj.status}


@router.get("/course-offerings/{offering_id}/teaching-assignments")
def list_teaching_assignments(offering_id: int, db: Session = Depends(get_db)):
    offering = db.get(m.CourseOffering, offering_id)
    if not offering: raise HTTPException(404, "Ders şubesi bulunamadı")
    require_course_access(db, offering.course_id, write=False)
    rows = db.scalars(select(m.TeachingAssignment).where(m.TeachingAssignment.course_offering_id == offering_id).order_by(m.TeachingAssignment.role, m.TeachingAssignment.id)).all()
    return [{"id": x.id, "course_offering_id": x.course_offering_id, "app_user_id": x.app_user_id, "instructor_email": x.instructor_email, "instructor_name": x.instructor_name, "role": x.role, "workload_hours": x.workload_hours} for x in rows]


@router.post("/course-offerings/{offering_id}/teaching-assignments", status_code=201)
def create_teaching_assignment(offering_id: int, data: TeachingAssignmentCreate, db: Session = Depends(get_db)):
    offering = db.get(m.CourseOffering, offering_id)
    if not offering: raise HTTPException(404, "Ders şubesi bulunamadı")
    require_course_management(db, offering.course_id)
    if data.app_user_id and not db.get(m.AppUser, data.app_user_id): raise HTTPException(404, "Kullanıcı bulunamadı")
    obj = m.TeachingAssignment(course_offering_id=offering_id, **data.model_dump())
    db.add(obj); db.flush(); _audit(db, "create", "teaching_assignment", obj.id, data.model_dump()); _commit(db)
    return {"id": obj.id, "course_offering_id": obj.course_offering_id, "role": obj.role, "instructor_email": obj.instructor_email}

class CurriculumOutcomeMapUpsert(BaseModel):
    catalog_item_id: int
    program_outcome_id: int
    coverage_level: Literal["I", "R", "M"]
    note: str = Field(default="", max_length=2000)


def _program_outcomes_for_curriculum(db: Session, version: m.CurriculumVersion) -> list[m.ProgramOutcome]:
    stmt = select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == version.program_id)
    if version.academic_year_start:
        preferred = list(db.scalars(stmt.where(m.ProgramOutcome.academic_year == version.academic_year_start).order_by(m.ProgramOutcome.code)).all())
        if preferred:
            return preferred
    rows = list(db.scalars(stmt.order_by(m.ProgramOutcome.academic_year.desc(), m.ProgramOutcome.code)).all())
    if not rows:
        return []
    latest_year = rows[0].academic_year
    return [x for x in rows if x.academic_year == latest_year]


@router.get("/curriculum-versions/{version_id}/outcome-map")
def get_curriculum_outcome_map(version_id: int, db: Session = Depends(get_db)):
    version = db.get(m.CurriculumVersion, version_id)
    if not version:
        raise HTTPException(404, "Müfredat versiyonu bulunamadı")
    require_program_access(db, version.program_id, write=False)
    courses = list(db.scalars(select(m.CurriculumCourse).where(m.CurriculumCourse.curriculum_version_id == version_id).order_by(m.CurriculumCourse.semester_no, m.CurriculumCourse.id)).all())
    outcomes = _program_outcomes_for_curriculum(db, version)
    maps = list(db.scalars(select(m.CurriculumOutcomeMap).where(m.CurriculumOutcomeMap.curriculum_version_id == version_id)).all())
    map_by_pair = {(x.catalog_item_id, x.program_outcome_id): x for x in maps}
    course_rows = []
    for link in courses:
        item = db.get(m.CourseCatalogItem, link.catalog_item_id)
        cells = {}
        for po in outcomes:
            row = map_by_pair.get((link.catalog_item_id, po.id))
            cells[str(po.id)] = {"level": row.coverage_level, "note": row.note} if row else None
        course_rows.append({
            "catalog_item_id": link.catalog_item_id,
            "code": item.code if item else "",
            "name": item.name if item else "",
            "semester_no": link.semester_no,
            "course_type": link.course_type,
            "cells": cells,
        })
    return {
        "curriculum_version": {"id": version.id, "code": version.code, "name": version.name, "program_id": version.program_id},
        "program_outcomes": [{"id": po.id, "code": po.code, "description": po.description, "academic_year": po.academic_year} for po in outcomes],
        "courses": course_rows,
    }


@router.put("/curriculum-versions/{version_id}/outcome-map")
def upsert_curriculum_outcome_map(version_id: int, data: CurriculumOutcomeMapUpsert, db: Session = Depends(get_db)):
    version = db.get(m.CurriculumVersion, version_id)
    item = db.get(m.CourseCatalogItem, data.catalog_item_id)
    po = db.get(m.ProgramOutcome, data.program_outcome_id)
    if not version or not item or not po:
        raise HTTPException(404, "Müfredat, katalog dersi veya program çıktısı bulunamadı")
    require_program_access(db, version.program_id, write=True)
    if item.program_id != version.program_id or po.program_id != version.program_id:
        raise HTTPException(400, "Ders, müfredat ve PÇ aynı programa ait olmalıdır")
    in_curriculum = db.scalar(select(func.count()).select_from(m.CurriculumCourse).where(
        m.CurriculumCourse.curriculum_version_id == version_id,
        m.CurriculumCourse.catalog_item_id == data.catalog_item_id,
    )) or 0
    if not in_curriculum:
        raise HTTPException(400, "Ders bu müfredat versiyonunda yer almıyor")
    row = db.scalar(select(m.CurriculumOutcomeMap).where(
        m.CurriculumOutcomeMap.curriculum_version_id == version_id,
        m.CurriculumOutcomeMap.catalog_item_id == data.catalog_item_id,
        m.CurriculumOutcomeMap.program_outcome_id == data.program_outcome_id,
    ))
    if row:
        old = row.coverage_level
        row.coverage_level = data.coverage_level
        row.note = data.note
        _audit(db, "update", "curriculum_outcome_map", row.id, {"from": old, "to": data.coverage_level})
    else:
        row = m.CurriculumOutcomeMap(curriculum_version_id=version_id, **data.model_dump())
        db.add(row); db.flush()
        _audit(db, "create", "curriculum_outcome_map", row.id, data.model_dump())
    _commit(db)
    return {"id": row.id, "curriculum_version_id": version_id, "catalog_item_id": row.catalog_item_id, "program_outcome_id": row.program_outcome_id, "coverage_level": row.coverage_level, "note": row.note}


@router.delete("/curriculum-versions/{version_id}/outcome-map/{catalog_item_id}/{program_outcome_id}")
def delete_curriculum_outcome_map(version_id: int, catalog_item_id: int, program_outcome_id: int, db: Session = Depends(get_db)):
    version = db.get(m.CurriculumVersion, version_id)
    if not version:
        raise HTTPException(404, "Müfredat versiyonu bulunamadı")
    require_program_access(db, version.program_id, write=True)
    row = db.scalar(select(m.CurriculumOutcomeMap).where(
        m.CurriculumOutcomeMap.curriculum_version_id == version_id,
        m.CurriculumOutcomeMap.catalog_item_id == catalog_item_id,
        m.CurriculumOutcomeMap.program_outcome_id == program_outcome_id,
    ))
    if not row:
        raise HTTPException(404, "Müfredat-PÇ eşleşmesi bulunamadı")
    _audit(db, "delete", "curriculum_outcome_map", row.id, {"catalog_item_id": catalog_item_id, "program_outcome_id": program_outcome_id})
    db.delete(row); _commit(db)
    return {"deleted": True}


@router.get("/curriculum-versions/{version_id}/outcome-map/gaps")
def curriculum_outcome_map_gaps(version_id: int, db: Session = Depends(get_db)):
    version = db.get(m.CurriculumVersion, version_id)
    if not version:
        raise HTTPException(404, "Müfredat versiyonu bulunamadı")
    require_program_access(db, version.program_id, write=False)
    links = list(db.scalars(select(m.CurriculumCourse).where(m.CurriculumCourse.curriculum_version_id == version_id)).all())
    outcomes = _program_outcomes_for_curriculum(db, version)
    maps = list(db.scalars(select(m.CurriculumOutcomeMap).where(m.CurriculumOutcomeMap.curriculum_version_id == version_id)).all())
    semester_by_course = {x.catalog_item_id: x.semester_no for x in links}
    mapped_course_ids = {x.catalog_item_id for x in maps}
    no_mapping_courses = []
    for link in links:
        if link.catalog_item_id not in mapped_course_ids:
            item = db.get(m.CourseCatalogItem, link.catalog_item_id)
            no_mapping_courses.append({"catalog_item_id": link.catalog_item_id, "code": item.code if item else "", "name": item.name if item else "", "semester_no": link.semester_no})

    outcome_rows = []
    uncovered = []
    no_mastery = []
    single_point = []
    progression_warnings = []
    for po in outcomes:
        rows = [x for x in maps if x.program_outcome_id == po.id]
        levels = {x.coverage_level for x in rows}
        courses = []
        for x in rows:
            item = db.get(m.CourseCatalogItem, x.catalog_item_id)
            courses.append({"catalog_item_id": x.catalog_item_id, "code": item.code if item else "", "semester_no": semester_by_course.get(x.catalog_item_id), "level": x.coverage_level})
        courses.sort(key=lambda x: (x["semester_no"] is None, x["semester_no"] or 999, x["code"]))
        flags = []
        if not rows:
            uncovered.append(po.code); flags.append("no_coverage")
        if rows and "M" not in levels:
            no_mastery.append(po.code); flags.append("no_mastery")
        if len({x.catalog_item_id for x in rows}) == 1:
            single_point.append(po.code); flags.append("single_course_dependency")
        ranked = {"I": 1, "R": 2, "M": 3}
        last = 0
        for course in courses:
            current = ranked.get(course["level"], 0)
            if current < last:
                flags.append("progression_regression")
                progression_warnings.append({"program_outcome": po.code, "course": course["code"], "level": course["level"]})
                break
            last = max(last, current)
        outcome_rows.append({"program_outcome_id": po.id, "code": po.code, "levels": sorted(levels), "mapped_course_count": len({x.catalog_item_id for x in rows}), "courses": courses, "flags": flags})

    total_outcomes = len(outcomes)
    covered = total_outcomes - len(uncovered)
    mastered = sum(1 for row in outcome_rows if "M" in row["levels"])
    coverage_percent = round(100 * covered / total_outcomes, 1) if total_outcomes else 0.0
    mastery_percent = round(100 * mastered / total_outcomes, 1) if total_outcomes else 0.0
    readiness_score = round(coverage_percent * 0.6 + mastery_percent * 0.4, 1) if total_outcomes else 0.0
    return {
        "curriculum_version_id": version_id,
        "summary": {
            "course_count": len(links),
            "program_outcome_count": total_outcomes,
            "coverage_percent": coverage_percent,
            "mastery_percent": mastery_percent,
            "readiness_score": readiness_score,
        },
        "gaps": {
            "outcomes_without_coverage": uncovered,
            "outcomes_without_mastery": no_mastery,
            "single_course_dependencies": single_point,
            "courses_without_outcome_mapping": no_mapping_courses,
            "progression_warnings": progression_warnings,
        },
        "outcomes": outcome_rows,
    }
