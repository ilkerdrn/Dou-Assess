from __future__ import annotations

import hashlib
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models as m, schemas as s
from .authz import current_user, require_program_access, require_roles
from .config import settings
from .db import get_db
from .security import read_upload_limited, validate_document_upload, verify_stored_file
from .services.quality360 import (
    CLASS_LEVELS, COURSE_CATEGORIES, EMPLOYMENT_TYPES, GOVERNANCE_BODIES,
    GRADUATE_EMPLOYMENT_STATUSES, INFRASTRUCTURE_TYPES, INSTRUCTOR_TITLES,
    QUALITY_CYCLE_STATUSES, QUALITY_STATUS_VALUES, STAKEHOLDER_ENGAGEMENT_TYPES,
    STAKEHOLDER_TYPES, TERMS, build_odr_docx, build_self_evaluation_report, build_self_evaluation_docx, build_institutional_self_evaluation_report, build_institutional_self_evaluation_docx, catalogs, model_dict,
    program_dashboard, curriculum_check, seed_builtin_frameworks, recommend_program_frameworks, mudek_version_route, medek_version_route, medek_program_specific_profile, previous_general_framework_version, university_quality_dashboard, quality_action_recommendations, quality_escalation_queue, accreditation_evidence_readiness, framework_preparation_readiness,
    medek_odr_readiness, build_medek_odr_docx, medek_odr_valid_codes, mudek_ek1_profile, mudek_ek1_valid_codes, mudek_evidence_room_readiness, mudek_discipline_specific_readiness, institutional_accreditation_readiness,
)

from .services.framework_preparation_catalog import framework_preparation_valid_codes
router = APIRouter(tags=["Quality & Accreditation 360"])


def _commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _audit(db: Session, action: str, entity_type: str, entity_id: int | None = None, payload: dict[str, Any] | None = None) -> None:
    try:
        actor = current_user()
    except Exception:
        actor = {"id": None, "email": "system", "role_names": []}
    db.add(m.AuditLog(
        actor_user_id=actor.get("id"), actor_email=actor.get("email") or "system",
        actor_roles=list(actor.get("role_names") or []), action=action, entity_type=entity_type,
        entity_id=entity_id, payload=payload or {},
    ))


def _validate_status(value: str) -> None:
    if value not in QUALITY_STATUS_VALUES:
        raise HTTPException(422, "Kalite durumu katalogda bulunamadı")


def _validate_program_payload(db: Session, program_id: int, *, write: bool = True) -> None:
    require_program_access(db, program_id, write=write, accreditation=True)


def _rows(db: Session, model: type, program_id: int, *extra) -> list[dict[str, Any]]:
    _validate_program_payload(db, program_id, write=False)
    stmt = select(model).where(model.program_id == program_id)
    for condition in extra:
        stmt = stmt.where(condition)
    stmt = stmt.order_by(model.id.desc())
    return [model_dict(x) for x in db.scalars(stmt).all()]


@router.get("/api/catalogs")
def quality_catalogs() -> dict[str, Any]:
    return catalogs()


@router.get("/api/quality360/frameworks")
def quality_frameworks(db: Session = Depends(get_db)):
    return [model_dict(x) for x in seed_builtin_frameworks(db)]



@router.get("/api/quality360/frameworks/mudek-route")
def quality360_mudek_version_route(
    academic_year: str, application_type: str = "general", preferred_version: str | None = None,
    previous_general_version: str | None = None, program_id: int | None = None, db: Session = Depends(get_db),
):
    try:
        if previous_general_version is None and program_id is not None:
            previous_general_version = previous_general_framework_version(db, program_id, "MÜDEK", academic_year)
        return mudek_version_route(db, academic_year, application_type, preferred_version, previous_general_version)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/api/quality360/frameworks/medek-route")
def quality360_medek_version_route(
    academic_year: str, application_type: str = "general", preferred_version: str | None = None,
    previous_general_version: str | None = None, program_id: int | None = None, db: Session = Depends(get_db),
):
    try:
        if previous_general_version is None and program_id is not None:
            previous_general_version = previous_general_framework_version(db, program_id, "MEDEK", academic_year)
        return medek_version_route(db, academic_year, application_type, preferred_version, previous_general_version)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/api/quality360/programs/{program_id}/medek-program-specific")
def quality360_medek_program_specific(
    program_id: int, framework_id: int, academic_year: str | None = None, db: Session = Depends(get_db),
):
    try:
        return medek_program_specific_profile(db, program_id, framework_id, academic_year)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/api/quality360/programs/{program_id}/mudek-discipline-specific")
def quality360_mudek_discipline_specific(program_id:int, framework_id:int, db:Session=Depends(get_db)):
    try: return mudek_discipline_specific_readiness(db,program_id,framework_id)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc

@router.get("/api/quality360/programs/{program_id}/mudek-ek1")
def quality360_mudek_ek1(program_id: int, academic_year: str, framework_id: int | None = None, db: Session = Depends(get_db)):
    try:
        return mudek_ek1_profile(db, program_id, academic_year, framework_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/api/quality360/programs/{program_id}/mudek-evidence-room-readiness")
def quality360_mudek_evidence_room_readiness(program_id: int, academic_year: str, room_type: str = "BBO", framework_id: int | None = None, application_id: int | None = None, db: Session = Depends(get_db)):
    try:
        return mudek_evidence_room_readiness(db, program_id, academic_year, room_type, framework_id, application_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/api/quality360/university/dashboard")
def quality360_university_dashboard(academic_year: str, db: Session = Depends(get_db)):
    require_roles("admin", "quality", "faculty_admin", "department_head", "program_head")
    return university_quality_dashboard(db, academic_year)


@router.get("/api/quality360/programs/{program_id}/framework-routing")
def quality360_framework_routing(program_id: int, db: Session = Depends(get_db)):
    return recommend_program_frameworks(db, program_id)

@router.get("/api/quality360/escalations")
def quality360_escalations(academic_year: str, db: Session = Depends(get_db)):
    require_roles("admin", "quality", "faculty_admin", "department_head", "program_head")
    return quality_escalation_queue(db, academic_year)



@router.post("/api/quality360/programs/{program_id}/framework-override", status_code=201)
def quality360_framework_override(program_id: int, framework_id: int, is_primary: bool = True, db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    _validate_program_payload(db, program_id)
    fw = db.get(m.QualityFrameworkProfile, framework_id)
    if not fw:
        raise HTTPException(404, "Kalite çerçevesi bulunamadı")
    if is_primary:
        for row in db.scalars(select(m.QualityFrameworkAssignment).where(m.QualityFrameworkAssignment.program_id == program_id, m.QualityFrameworkAssignment.active.is_(True))).all():
            row.is_primary = False
    row = db.scalar(select(m.QualityFrameworkAssignment).where(m.QualityFrameworkAssignment.program_id == program_id, m.QualityFrameworkAssignment.framework_profile_id == framework_id))
    if row:
        row.source = "manual"; row.active = True; row.is_primary = is_primary; row.confidence = 1.0; row.rationale = "Kalite yöneticisi tarafından manuel doğrulandı."
    else:
        row = m.QualityFrameworkAssignment(program_id=program_id, framework_profile_id=framework_id, source="manual", active=True, is_primary=is_primary, confidence=1.0, rationale="Kalite yöneticisi tarafından manuel doğrulandı.")
        db.add(row)
    db.flush(); _audit(db, "quality_framework_override", "quality_framework_assignment", row.id, {"program_id": program_id, "framework_id": framework_id}); _commit(db)
    return model_dict(row)

@router.get("/api/quality360/programs/{program_id}/dashboard")
def quality360_dashboard(program_id: int, academic_year: str, framework_id: int | None = None, db: Session = Depends(get_db)):
    try:
        return program_dashboard(db, program_id, academic_year, framework_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/api/quality360/programs/{program_id}/accreditation-readiness")
def quality360_accreditation_readiness(program_id: int, academic_year: str, framework_id: int | None = None, db: Session = Depends(get_db)):
    try:
        return accreditation_evidence_readiness(db, program_id, academic_year, framework_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/api/quality360/programs/{program_id}/framework-preparation-readiness")
def quality360_framework_preparation_readiness(program_id: int, academic_year: str, framework_id: int | None = None, db: Session = Depends(get_db)):
    try:
        return framework_preparation_readiness(db, program_id, academic_year, framework_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/api/quality360/institutional/self-evaluation")
def quality360_institutional_self_evaluation(academic_year: str, faculty: str | None = None, db: Session = Depends(get_db)):
    require_roles("admin", "quality", "faculty_admin", "department_head", "program_head")
    return build_institutional_self_evaluation_report(db, academic_year, faculty)


@router.get("/api/quality360/institutional/self-evaluation.docx")
def quality360_institutional_self_evaluation_docx(academic_year: str, faculty: str | None = None, db: Session = Depends(get_db)):
    require_roles("admin", "quality", "faculty_admin", "department_head", "program_head")
    payload, filename = build_institutional_self_evaluation_docx(db, academic_year, faculty)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(payload, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers=headers)




def _kpi_progress(kpi: m.StrategicKPI) -> float:
    target=float(kpi.target_value or 0); actual=float(kpi.actual_value or 0); base=float(kpi.baseline_value or 0)
    if kpi.direction == "lower":
        if actual <= target: return 100.0
        denom=max(abs(base-target),1e-9)
        return max(0.0,min(100.0,100.0-((actual-target)/denom)*100.0))
    if target == base:
        return 100.0 if actual >= target else 0.0
    return max(0.0,min(100.0,((actual-base)/(target-base))*100.0))

@router.get("/api/quality360/strategy/dashboard")
def strategic_quality_dashboard(academic_year: str, faculty: str | None = None, db: Session = Depends(get_db)):
    require_roles("admin","quality","faculty_admin","department_head","program_head")
    stmt=select(m.StrategicObjective).where(m.StrategicObjective.academic_year==academic_year).order_by(m.StrategicObjective.code)
    objectives=list(db.scalars(stmt).all())
    if faculty:
        objectives=[o for o in objectives if o.scope_type=="university" or o.scope_name==faculty]
    rows=[]; weighted=0.0; totalw=0.0; risk=0
    for o in objectives:
        kpis=list(db.scalars(select(m.StrategicKPI).where(m.StrategicKPI.objective_id==o.id).order_by(m.StrategicKPI.code)).all())
        kp=[]; ow=0.0; os=0.0
        for k in kpis:
            prog=round(_kpi_progress(k),2); w=float(k.weight or 1.0); ow+=w; os+=prog*w
            if prog < 70: risk += 1
            kp.append({**model_dict(k),"progress_percent":prog,"health":"critical" if prog<50 else "watch" if prog<70 else "healthy"})
        score=round(os/ow,2) if ow else 0.0
        if ow: weighted += score*ow; totalw += ow
        rows.append({**model_dict(o),"score_percent":score,"kpis":kp,"kpi_count":len(kp)})
    institution_score=round(weighted/totalw,2) if totalw else 0.0
    return {"academic_year":academic_year,"faculty":faculty,"summary":{"objective_count":len(rows),"kpi_count":sum(x["kpi_count"] for x in rows),"risk_kpi_count":risk,"strategy_score_percent":institution_score},"objectives":rows,"human_approval_required":True,"disclaimer":"Stratejik kalite skoru kurum içi yönetim göstergesidir; resmî akreditasyon veya YÖKAK puanı değildir."}

@router.post("/api/quality360/strategy/objectives", status_code=201)
def strategic_objective_create(body: s.StrategicObjectiveCreate, db: Session = Depends(get_db)):
    require_roles("admin","quality")
    if body.program_id: _validate_program_payload(db,body.program_id)
    obj=m.StrategicObjective(**body.model_dump()); db.add(obj); db.flush(); _audit(db,"strategy_objective_create","strategic_objective",obj.id,{"code":obj.code}); _commit(db); return model_dict(obj)

@router.post("/api/quality360/strategy/kpis", status_code=201)
def strategic_kpi_create(body: s.StrategicKPICreate, db: Session = Depends(get_db)):
    require_roles("admin","quality")
    if not db.get(m.StrategicObjective,body.objective_id): raise HTTPException(404,"Stratejik hedef bulunamadı")
    obj=m.StrategicKPI(**body.model_dump()); db.add(obj); db.flush(); _audit(db,"strategy_kpi_create","strategic_kpi",obj.id,{"objective_id":obj.objective_id,"code":obj.code}); _commit(db); return {**model_dict(obj),"progress_percent":round(_kpi_progress(obj),2)}

@router.patch("/api/quality360/strategy/kpis/{kpi_id}")
def strategic_kpi_update(kpi_id:int, body:s.StrategicKPIUpdate, db:Session=Depends(get_db)):
    require_roles("admin","quality","faculty_admin","department_head","program_head")
    obj=db.get(m.StrategicKPI,kpi_id)
    if not obj: raise HTTPException(404,"KPI bulunamadı")
    for k,v in body.model_dump(exclude_none=True).items(): setattr(obj,k,v)
    obj.updated_at=datetime.now(timezone.utc); db.flush(); _audit(db,"strategy_kpi_update","strategic_kpi",obj.id,body.model_dump(exclude_none=True)); _commit(db); return {**model_dict(obj),"progress_percent":round(_kpi_progress(obj),2)}

@router.get("/api/quality360/programs/{program_id}/curriculum-check")
def quality360_curriculum_check(program_id: int, academic_year: str, db: Session = Depends(get_db)):
    return curriculum_check(db, program_id, academic_year)


@router.get("/api/quality360/programs/{program_id}/medek-odr-readiness")
def quality360_medek_odr_readiness(
    program_id: int, academic_year: str, framework_id: int | None = None, application_type: str = "general", db: Session = Depends(get_db)
):
    try:
        return medek_odr_readiness(db, program_id, academic_year, framework_id, application_type)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/api/quality360/programs/{program_id}/medek-odr.docx")
def quality360_medek_odr_docx(
    program_id: int, academic_year: str, framework_id: int | None = None, application_type: str = "general", db: Session = Depends(get_db)
):
    try:
        payload, filename = build_medek_odr_docx(db, program_id, academic_year, framework_id, application_type)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(payload, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers=headers)


@router.get("/api/quality360/programs/{program_id}/odr.docx")
def quality360_odr(program_id: int, academic_year: str, framework_id: int | None = None, db: Session = Depends(get_db)):
    payload, filename = build_odr_docx(db, program_id, academic_year, framework_id)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(payload, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers=headers)

@router.get("/api/quality360/programs/{program_id}/self-evaluation")
def quality360_self_evaluation(program_id: int, academic_year: str, framework_id: int | None = None, db: Session = Depends(get_db)):
    try:
        return build_self_evaluation_report(db, program_id, academic_year, framework_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/api/quality360/programs/{program_id}/self-evaluation.docx")
def quality360_self_evaluation_docx(program_id: int, academic_year: str, framework_id: int | None = None, db: Session = Depends(get_db)):
    payload, filename = build_self_evaluation_docx(db, program_id, academic_year, framework_id)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(payload, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers=headers)


@router.get("/api/quality360/programs/{program_id}/curriculum")
def curriculum_list(program_id: int, academic_year: str | None = None, db: Session = Depends(get_db)):
    extra = (m.CurriculumItem.academic_year == academic_year,) if academic_year else ()
    return _rows(db, m.CurriculumItem, program_id, *extra)


@router.post("/api/quality360/curriculum", status_code=201)
def curriculum_create(body: s.CurriculumItemCreate, db: Session = Depends(get_db)):
    _validate_program_payload(db, body.program_id)
    if body.term not in TERMS or body.class_level not in CLASS_LEVELS or body.course_category not in COURSE_CATEGORIES:
        raise HTTPException(422, "Dönem, sınıf veya ders kategorisi katalogda bulunamadı")
    _validate_status(body.quality_status)
    existing = db.scalar(select(m.CurriculumItem).where(
        m.CurriculumItem.program_id == body.program_id,
        m.CurriculumItem.academic_year == body.academic_year,
        m.CurriculumItem.course_code == body.course_code,
    ))
    data = body.model_dump()
    if existing:
        for key, value in data.items(): setattr(existing, key, value)
        obj = existing
    else:
        obj = m.CurriculumItem(**data); db.add(obj)
    db.flush(); _audit(db, "quality360_curriculum_upsert", "curriculum_item", obj.id, {"program_id": body.program_id}); _commit(db)
    return model_dict(obj)


@router.get("/api/quality360/programs/{program_id}/stakeholders")
def stakeholder_list(program_id: int, db: Session = Depends(get_db)):
    return _rows(db, m.StakeholderRecord, program_id)


@router.post("/api/quality360/stakeholders", status_code=201)
def stakeholder_create(body: s.StakeholderRecordCreate, db: Session = Depends(get_db)):
    _validate_program_payload(db, body.program_id)
    if body.stakeholder_type not in STAKEHOLDER_TYPES or body.engagement_type not in STAKEHOLDER_ENGAGEMENT_TYPES:
        raise HTTPException(422, "Paydaş veya katılım türü katalogda bulunamadı")
    _validate_status(body.quality_status)
    obj = m.StakeholderRecord(**body.model_dump()); db.add(obj); db.flush()
    _audit(db, "quality360_stakeholder_create", "stakeholder", obj.id, {"program_id": body.program_id}); _commit(db)
    return model_dict(obj)


@router.get("/api/quality360/programs/{program_id}/graduates")
def graduate_list(program_id: int, db: Session = Depends(get_db)):
    return _rows(db, m.GraduateRecord, program_id)


@router.post("/api/quality360/graduates", status_code=201)
def graduate_create(body: s.GraduateRecordCreate, db: Session = Depends(get_db)):
    _validate_program_payload(db, body.program_id)
    if body.employment_status not in GRADUATE_EMPLOYMENT_STATUSES:
        raise HTTPException(422, "Mezun istihdam durumu katalogda bulunamadı")
    obj = db.scalar(select(m.GraduateRecord).where(m.GraduateRecord.program_id == body.program_id, m.GraduateRecord.graduate_key == body.graduate_key))
    data = body.model_dump()
    if obj:
        for key, value in data.items(): setattr(obj, key, value)
    else:
        obj = m.GraduateRecord(**data); db.add(obj)
    db.flush(); _audit(db, "quality360_graduate_upsert", "graduate", obj.id, {"program_id": body.program_id}); _commit(db)
    return model_dict(obj)


@router.get("/api/quality360/programs/{program_id}/faculty")
def faculty_list(program_id: int, db: Session = Depends(get_db)):
    return _rows(db, m.FacultyRecord, program_id)


@router.post("/api/quality360/faculty", status_code=201)
def faculty_create(body: s.FacultyRecordCreate, db: Session = Depends(get_db)):
    _validate_program_payload(db, body.program_id)
    if body.title not in INSTRUCTOR_TITLES or body.employment_type not in EMPLOYMENT_TYPES:
        raise HTTPException(422, "Unvan veya çalışma türü katalogda bulunamadı")
    _validate_status(body.quality_status)
    email = body.email.strip().lower()
    obj = db.scalar(select(m.FacultyRecord).where(m.FacultyRecord.program_id == body.program_id, m.FacultyRecord.email == email))
    data = body.model_dump(); data["email"] = email
    if obj:
        for key, value in data.items(): setattr(obj, key, value)
    else:
        obj = m.FacultyRecord(**data); db.add(obj)
    db.flush(); _audit(db, "quality360_faculty_upsert", "faculty", obj.id, {"program_id": body.program_id}); _commit(db)
    return model_dict(obj)


@router.get("/api/quality360/programs/{program_id}/infrastructure")
def infrastructure_list(program_id: int, db: Session = Depends(get_db)):
    return _rows(db, m.InfrastructureRecord, program_id)


@router.post("/api/quality360/infrastructure", status_code=201)
def infrastructure_create(body: s.InfrastructureRecordCreate, db: Session = Depends(get_db)):
    _validate_program_payload(db, body.program_id)
    if body.infrastructure_type not in INFRASTRUCTURE_TYPES:
        raise HTTPException(422, "Altyapı türü katalogda bulunamadı")
    for status in (body.quality_status, body.accessibility_status, body.isg_status): _validate_status(status)
    obj = m.InfrastructureRecord(**body.model_dump()); db.add(obj); db.flush()
    _audit(db, "quality360_infrastructure_create", "infrastructure", obj.id, {"program_id": body.program_id}); _commit(db)
    return model_dict(obj)


@router.get("/api/quality360/programs/{program_id}/action-recommendations")
def quality_action_recommendation_list(program_id: int, academic_year: str, framework_id: int | None = None, db: Session = Depends(get_db)):
    _validate_program_payload(db, program_id, write=False)
    return quality_action_recommendations(db, program_id, academic_year, framework_id)


@router.post("/api/quality360/action-recommendations/accept", status_code=201)
def quality_action_accept(body: s.QualityActionAccept, db: Session = Depends(get_db)):
    require_roles("admin", "quality", "program_head")
    _validate_program_payload(db, body.program_id)
    existing = db.scalar(select(m.QualityCycle).where(
        m.QualityCycle.program_id == body.program_id,
        m.QualityCycle.academic_year == body.academic_year,
        m.QualityCycle.criterion_code == body.criterion_code,
        m.QualityCycle.status != "closed",
    ))
    if existing:
        raise HTTPException(409, "Bu ölçüt için açık bir PUKÖ döngüsü zaten var")
    evidence_refs = [f"beklenen:{x}" for x in body.expected_evidence[:20]]
    obj = m.QualityCycle(
        program_id=body.program_id, academic_year=body.academic_year, criterion_code=body.criterion_code,
        title=body.title, plan_text=body.plan_text, do_text=body.do_text, check_text=body.check_text,
        act_text=body.act_text, owner=body.owner, due_date=body.due_date, status="planned", evidence_refs=evidence_refs,
    )
    db.add(obj); db.flush()
    _audit(db, "quality_action_accept", "quality_cycle", obj.id, {"program_id":body.program_id,"criterion_code":body.criterion_code,"framework_id":body.framework_id})
    _commit(db)
    return model_dict(obj)


@router.get("/api/quality360/programs/{program_id}/quality-cycles")
def quality_cycle_list(program_id: int, academic_year: str | None = None, db: Session = Depends(get_db)):
    extra = (m.QualityCycle.academic_year == academic_year,) if academic_year else ()
    return _rows(db, m.QualityCycle, program_id, *extra)


@router.post("/api/quality360/quality-cycles", status_code=201)
def quality_cycle_create(body: s.QualityCycleCreate, db: Session = Depends(get_db)):
    _validate_program_payload(db, body.program_id)
    if body.status not in QUALITY_CYCLE_STATUSES:
        raise HTTPException(422, "PUKÖ durumu katalogda bulunamadı")
    data = body.model_dump()
    if body.status == "closed": data["closed_at"] = datetime.now(timezone.utc)
    obj = m.QualityCycle(**data); db.add(obj); db.flush()
    _audit(db, "quality360_cycle_create", "quality_cycle", obj.id, {"program_id": body.program_id}); _commit(db)
    return model_dict(obj)


@router.get("/api/quality360/programs/{program_id}/calendar")
def quality_calendar_list(program_id: int, academic_year: str, db: Session = Depends(get_db)):
    _validate_program_payload(db, program_id, write=False)
    explicit = [model_dict(x) for x in db.scalars(select(m.QualityCalendarEvent).where(m.QualityCalendarEvent.program_id == program_id, m.QualityCalendarEvent.academic_year == academic_year).order_by(m.QualityCalendarEvent.start_date.asc(), m.QualityCalendarEvent.id.asc())).all()]
    derived = []
    for cycle in db.scalars(select(m.QualityCycle).where(m.QualityCycle.program_id == program_id, m.QualityCycle.academic_year == academic_year, m.QualityCycle.due_date.is_not(None))).all():
        derived.append({"id": f"cycle-{cycle.id}", "source": "quality_cycle", "event_type": "pdca_deadline", "title": cycle.title, "start_date": cycle.due_date.isoformat(), "due_date": cycle.due_date.isoformat(), "owner": cycle.owner, "owner_role": "Program / Kalite", "criterion_code": cycle.criterion_code, "status": "done" if cycle.status == "closed" else "planned", "evidence_required": "; ".join(str(x) for x in (cycle.evidence_refs or [])), "related_entity_type": "quality_cycle", "related_entity_id": cycle.id, "notes": "PUKÖ termininden otomatik takvim kaydı"})
    for decision in db.scalars(select(m.GovernanceDecision).where(m.GovernanceDecision.program_id == program_id, m.GovernanceDecision.meeting_date.is_not(None))).all():
        derived.append({"id": f"governance-{decision.id}", "source": "governance", "event_type": "meeting", "title": f"{decision.body_type} · {decision.subject}", "start_date": decision.meeting_date.isoformat(), "due_date": decision.meeting_date.isoformat(), "owner": decision.body_type, "owner_role": "Kurul", "criterion_code": decision.related_criterion, "status": "done" if decision.status in {"implemented", "measured", "closed"} else "planned", "evidence_required": decision.evidence_ref, "related_entity_type": "governance_decision", "related_entity_id": decision.id, "notes": f"Toplantı {decision.meeting_no} · Karar {decision.decision_no}"})
    today = date.today()
    rows = [{**x, "source": "calendar"} for x in explicit] + derived
    for row in rows:
        target = row.get("due_date") or row.get("start_date")
        try: d = date.fromisoformat(str(target)[:10]) if target else None
        except Exception: d = None
        row["days_remaining"] = (d - today).days if d else None
        row["attention"] = bool(d and row.get("status") not in {"done", "cancelled"} and (d - today).days <= 7)
        row["overdue"] = bool(d and row.get("status") not in {"done", "cancelled"} and d < today)
    rows.sort(key=lambda x: (str(x.get("start_date") or "9999-12-31"), str(x.get("title") or "")))
    return {"program_id": program_id, "academic_year": academic_year, "items": rows, "summary": {"total": len(rows), "overdue": sum(1 for x in rows if x.get("overdue")), "attention": sum(1 for x in rows if x.get("attention") and not x.get("overdue")), "evidence_deadlines": sum(1 for x in rows if x.get("event_type") == "evidence_deadline"), "meetings": sum(1 for x in rows if x.get("event_type") == "meeting")}}

@router.post("/api/quality360/calendar", status_code=201)
def quality_calendar_create(body: s.QualityCalendarEventCreate, db: Session = Depends(get_db)):
    _validate_program_payload(db, body.program_id)
    if body.due_date and body.due_date < body.start_date:
        raise HTTPException(422, "Bitiş/teslim tarihi başlangıç tarihinden önce olamaz")
    obj = m.QualityCalendarEvent(**body.model_dump()); db.add(obj); db.flush()
    _audit(db, "quality360_calendar_create", "quality_calendar_event", obj.id, {"program_id": body.program_id, "event_type": body.event_type}); _commit(db)
    return model_dict(obj)

@router.patch("/api/quality360/calendar/{event_id}")
def quality_calendar_update(event_id: int, body: s.QualityCalendarEventUpdate, db: Session = Depends(get_db)):
    obj = db.get(m.QualityCalendarEvent, event_id)
    if not obj: raise HTTPException(404, "Kalite takvim kaydı bulunamadı")
    _validate_program_payload(db, obj.program_id)
    for key, value in body.model_dump(exclude_unset=True).items(): setattr(obj, key, value)
    if obj.due_date and obj.due_date < obj.start_date: raise HTTPException(422, "Bitiş/teslim tarihi başlangıç tarihinden önce olamaz")
    _audit(db, "quality360_calendar_update", "quality_calendar_event", obj.id, {"status": obj.status}); _commit(db)
    return model_dict(obj)


@router.get("/api/quality360/programs/{program_id}/governance")
def governance_list(program_id: int, db: Session = Depends(get_db)):
    return _rows(db, m.GovernanceDecision, program_id)


@router.post("/api/quality360/governance", status_code=201)
def governance_create(body: s.GovernanceDecisionCreate, db: Session = Depends(get_db)):
    _validate_program_payload(db, body.program_id)
    if body.body_type not in GOVERNANCE_BODIES:
        raise HTTPException(422, "Kurul türü katalogda bulunamadı")
    _validate_status(body.status)
    if body.source_stakeholder_id:
        stakeholder = db.get(m.StakeholderRecord, body.source_stakeholder_id)
        if not stakeholder or stakeholder.program_id != body.program_id:
            raise HTTPException(422, "Kaynak paydaş bu programa ait değil")
    obj = db.scalar(select(m.GovernanceDecision).where(
        m.GovernanceDecision.program_id == body.program_id,
        m.GovernanceDecision.meeting_no == body.meeting_no,
        m.GovernanceDecision.decision_no == body.decision_no,
    ))
    data = body.model_dump()
    if obj:
        for key, value in data.items(): setattr(obj, key, value)
    else:
        obj = m.GovernanceDecision(**data); db.add(obj)
    db.flush(); _audit(db, "quality360_governance_upsert", "governance_decision", obj.id, {"program_id": body.program_id}); _commit(db)
    return model_dict(obj)


@router.post("/api/quality360/governance/{decision_id}/start-action", status_code=201)
def governance_start_action(decision_id: int, body: s.GovernanceDecisionActionCreate, db: Session = Depends(get_db)):
    require_roles("admin", "quality", "program_head")
    decision = db.get(m.GovernanceDecision, decision_id)
    if not decision:
        raise HTTPException(404, "Kurul kararı bulunamadı")
    _validate_program_payload(db, decision.program_id)
    source_ref = f"decision:{decision.id}"
    for cycle in db.scalars(select(m.QualityCycle).where(
        m.QualityCycle.program_id == decision.program_id,
        m.QualityCycle.academic_year == body.academic_year,
        m.QualityCycle.status != "closed",
    )).all():
        if source_ref in (cycle.evidence_refs or []):
            raise HTTPException(409, "Bu kurul kararı için açık bir PUKÖ zaten var")
    criterion = (body.criterion_code or decision.related_criterion or "GENEL").strip()
    expected = [f"beklenen:{x.strip()}" for x in body.expected_evidence if x and x.strip()][:20]
    refs = [source_ref, *expected]
    obj = m.QualityCycle(
        program_id=decision.program_id,
        academic_year=body.academic_year,
        criterion_code=criterion,
        title=f"Kurul kararı · {decision.subject}"[:255],
        plan_text=f"{decision.body_type} {decision.meeting_no} / {decision.decision_no} numaralı kararın uygulanması planlandı. Karar: {decision.decision_text}",
        do_text="Kararda tanımlanan faaliyetleri sorumlu birimler uygular ve yürütme kanıtlarını sisteme yükler.",
        check_text="Termin sonunda gerçekleşme, ilgili kalite ölçütü ve yüklenen kanıtlar üzerinden doğrulanır.",
        act_text="Sonuç kurul/kalite birimince değerlendirilir; etkiliyse standardize edilir, değilse yeni iyileştirme döngüsü açılır.",
        owner=body.owner or "Program Başkanı",
        due_date=body.due_date,
        status="planned",
        evidence_refs=refs,
    )
    db.add(obj); db.flush()
    _audit(db, "quality_governance_start_action", "quality_cycle", obj.id, {"decision_id": decision.id, "program_id": decision.program_id, "criterion_code": criterion})
    _commit(db)
    return model_dict(obj)


@router.get("/api/quality360/programs/{program_id}/closure-readiness")
def quality_cycle_closure_readiness(program_id: int, academic_year: str, db: Session = Depends(get_db)):
    _validate_program_payload(db, program_id, write=False)
    cycles = db.scalars(select(m.QualityCycle).where(
        m.QualityCycle.program_id == program_id,
        m.QualityCycle.academic_year == academic_year,
        m.QualityCycle.status != "closed",
    ).order_by(m.QualityCycle.id.desc())).all()
    evidence = db.scalars(select(m.QualityEvidenceAsset).where(m.QualityEvidenceAsset.program_id == program_id)).all()
    rows = []
    for cycle in cycles:
        criterion_assets = [x for x in evidence if (x.criterion_code or "") == (cycle.criterion_code or "")]
        general_assets = [x for x in evidence if not (x.criterion_code or "")]
        actual_assets = criterion_assets or general_assets
        expected = [str(x).split(":",1)[1] for x in (cycle.evidence_refs or []) if str(x).startswith("beklenen:")]
        has_evidence = bool(actual_assets)
        has_owner = bool((cycle.owner or "").strip())
        has_due = cycle.due_date is not None
        checks = [
            {"key":"owner","label":"Sorumlu atanmış","ok":has_owner},
            {"key":"due_date","label":"Termin belirlenmiş","ok":has_due},
            {"key":"evidence","label":"Gerçek kalite kanıtı yüklenmiş","ok":has_evidence},
        ]
        ready = has_owner and has_evidence
        rows.append({
            "cycle_id":cycle.id,"title":cycle.title,"criterion_code":cycle.criterion_code,"owner":cycle.owner,
            "due_date":cycle.due_date.isoformat() if cycle.due_date else None,"status":cycle.status,
            "expected_evidence":expected,"evidence_count":len(actual_assets),"checks":checks,
            "ready_for_closure_review":ready,
            "recommendation":"Kapanış incelemesine gönder" if ready else "Eksik sorumluluk/kanıtları tamamla",
        })
    return {"program_id":program_id,"academic_year":academic_year,"items":rows,"summary":{"open_cycles":len(rows),"ready_for_closure":sum(1 for x in rows if x["ready_for_closure_review"])}}


@router.post("/api/quality360/quality-cycles/{cycle_id}/close")
def quality_cycle_close(cycle_id: int, body: s.QualityCycleCloseRequest, db: Session = Depends(get_db)):
    require_roles("admin", "quality", "program_head")
    cycle = db.get(m.QualityCycle, cycle_id)
    if not cycle:
        raise HTTPException(404, "PUKÖ döngüsü bulunamadı")
    _validate_program_payload(db, cycle.program_id)
    if cycle.status == "closed":
        raise HTTPException(409, "PUKÖ döngüsü zaten kapalı")
    evidence = db.scalars(select(m.QualityEvidenceAsset).where(m.QualityEvidenceAsset.program_id == cycle.program_id)).all()
    matching = [x for x in evidence if (x.criterion_code or "") == (cycle.criterion_code or "")]
    general = [x for x in evidence if not (x.criterion_code or "")]
    if not (matching or general):
        raise HTTPException(409, "PUKÖ kapanışı için en az bir gerçek kalite kanıtı yüklenmelidir")
    cycle.status = "closed"
    cycle.closed_at = datetime.now(timezone.utc)
    note = body.closure_note.strip()
    cycle.act_text = ((cycle.act_text or "").rstrip() + f"\n\nKapanış notu: {note}").strip()
    _audit(db, "quality_cycle_close", "quality_cycle", cycle.id, {"program_id":cycle.program_id,"criterion_code":cycle.criterion_code,"closure_note":note})
    _commit(db)
    return model_dict(cycle)


@router.put("/api/quality360/criterion-assessments")
def criterion_assessment_upsert(body: s.QualityCriterionAssessmentUpsert, db: Session = Depends(get_db)):
    _validate_program_payload(db, body.program_id)
    _validate_status(body.quality_status)
    framework = db.get(m.QualityFrameworkProfile, body.framework_profile_id)
    if not framework:
        seed_builtin_frameworks(db); framework = db.get(m.QualityFrameworkProfile, body.framework_profile_id)
    if not framework:
        raise HTTPException(404, "Kalite çerçevesi bulunamadı")
    valid_codes = {str(x.get("code")) for x in (framework.criteria or [])}
    for criterion in framework.criteria or []:
        valid_codes.update(str(x.get("code")) for x in (criterion.get("subcriteria") or []) if x.get("code"))
    if framework.framework_family == "MEDEK" and framework.version == "v1.1":
        valid_codes.update(medek_odr_valid_codes())
    if framework.framework_family == "MÜDEK" and framework.version in {"3.0", "3.1"}:
        valid_codes.update(mudek_ek1_valid_codes())
    if framework.framework_family in {"TURAK", "SABAK", "EPDAD"}:
        valid_codes.update(framework_preparation_valid_codes(framework.framework_family))
    if body.criterion_code not in valid_codes:
        raise HTTPException(422, "Ölçüt kodu seçili kalite çerçevesinde bulunamadı")
    obj = db.scalar(select(m.QualityCriterionAssessment).where(
        m.QualityCriterionAssessment.program_id == body.program_id,
        m.QualityCriterionAssessment.framework_profile_id == body.framework_profile_id,
        m.QualityCriterionAssessment.academic_year == body.academic_year,
        m.QualityCriterionAssessment.criterion_code == body.criterion_code,
    ))
    data = body.model_dump(); data["updated_at"] = datetime.now(timezone.utc)
    if obj:
        for key, value in data.items(): setattr(obj, key, value)
    else:
        obj = m.QualityCriterionAssessment(**data); db.add(obj)
    db.flush(); _audit(db, "quality360_assessment_upsert", "criterion_assessment", obj.id, {"program_id": body.program_id}); _commit(db)
    return model_dict(obj)


def _safe_filename(name: str) -> str:
    base = Path(name or "evidence.bin").name
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return (base or "evidence.bin")[:180]


def _evidence_root() -> Path:
    root = Path(settings.evidence_storage_path) / "quality360"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _verify_quality_evidence_integrity(db: Session, obj: m.QualityEvidenceAsset, path: Path) -> None:
    status, actual = verify_stored_file(path, obj.sha256)
    previous = obj.integrity_status or "unchecked"
    obj.integrity_status = status
    obj.integrity_checked_at = datetime.now(timezone.utc)
    if status != previous or status != "verified":
        _audit(db, "quality360_evidence_integrity_check", "quality_evidence", obj.id, {"program_id": obj.program_id, "status": status, "expected_sha256": obj.sha256, "actual_sha256": actual})
    _commit(db)
    if status == "missing":
        raise HTTPException(404, "Kanıt dosyasının fiziksel kopyası bulunamadı")
    if status != "verified":
        raise HTTPException(409, "Kanıt dosyası SHA-256 bütünlük kontrolünden geçemedi")


@router.get("/api/quality360/programs/{program_id}/evidence")
def evidence_list(program_id: int, criterion_code: str | None = None, db: Session = Depends(get_db)):
    extra = (m.QualityEvidenceAsset.criterion_code == criterion_code,) if criterion_code else ()
    return _rows(db, m.QualityEvidenceAsset, program_id, *extra)


@router.post("/api/quality360/programs/{program_id}/evidence", status_code=201)
async def evidence_upload(
    program_id: int,
    file: UploadFile = File(...),
    criterion_code: str = Form(""),
    entity_type: str = Form("program"),
    entity_id: int | None = Form(None),
    kind: str = Form("document"),
    category: str = Form("quality"),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    _validate_program_payload(db, program_id)
    payload = await read_upload_limited(file)
    if not payload:
        raise HTTPException(400, "Boş kanıt dosyası yüklenemez")
    original = _safe_filename(file.filename or "evidence.bin")
    canonical_mime = validate_document_upload(original, payload, purpose="Kalite kanıtı")
    suffix = Path(original).suffix[:16]
    stored = f"p{program_id}_{uuid.uuid4().hex}{suffix}"
    path = _evidence_root() / stored
    path.write_bytes(payload)
    sha = hashlib.sha256(payload).hexdigest()
    retention = date.today() + timedelta(days=settings.evidence_retention_days)
    obj = m.QualityEvidenceAsset(
        program_id=program_id, criterion_code=criterion_code.strip()[:64], entity_type=entity_type.strip()[:64] or "program",
        entity_id=entity_id, kind=kind.strip()[:64] or "document", category=category.strip()[:96] or "quality",
        description=description.strip()[:8000], original_name=original, stored_name=stored,
        mime_type=canonical_mime, size_bytes=len(payload), sha256=sha, integrity_status="verified",
        integrity_checked_at=datetime.now(timezone.utc), retention_until=retention,
    )
    try:
        db.add(obj); db.flush(); _audit(db, "quality360_evidence_upload", "quality_evidence", obj.id, {"program_id": program_id, "sha256": sha, "size_bytes": len(payload)}); _commit(db)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return model_dict(obj)


@router.get("/api/quality360/evidence/{evidence_id}/download")
def evidence_download(evidence_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.QualityEvidenceAsset, evidence_id)
    if not obj:
        raise HTTPException(404, "Kanıt dosyası bulunamadı")
    _validate_program_payload(db, obj.program_id, write=False)
    path = _evidence_root() / obj.stored_name
    _verify_quality_evidence_integrity(db, obj, path)
    return FileResponse(path, media_type=obj.mime_type, filename=obj.original_name)


@router.delete("/api/quality360/evidence/{evidence_id}")
def evidence_delete(evidence_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.QualityEvidenceAsset, evidence_id)
    if not obj:
        raise HTTPException(404, "Kanıt dosyası bulunamadı")
    _validate_program_payload(db, obj.program_id)
    path = _evidence_root() / obj.stored_name
    program_id = obj.program_id
    _audit(db, "quality360_evidence_delete", "quality_evidence", obj.id, {"program_id": program_id, "sha256": obj.sha256})
    db.delete(obj); _commit(db); path.unlink(missing_ok=True)
    return {"status": "deleted", "id": evidence_id}

# ---------------------------------------------------------------------------
# 6.63 Institutional Accreditation Readiness
# ---------------------------------------------------------------------------

@router.get("/api/quality360/institutional/readiness")
def quality360_institutional_readiness(academic_year: str, db: Session = Depends(get_db)):
    require_roles("admin", "quality", "faculty_admin", "department_head", "program_head")
    return institutional_accreditation_readiness(db, academic_year)


@router.get("/api/quality360/institutional/crosswalks")
def quality360_institutional_crosswalks(review_status: str | None = None, db: Session = Depends(get_db)):
    require_roles("admin", "quality", "faculty_admin", "department_head", "program_head")
    stmt = select(m.AccreditationCrosswalk)
    if review_status:
        if review_status not in {"draft", "approved", "rejected"}:
            raise HTTPException(422, "Geçersiz crosswalk review durumu")
        stmt = stmt.where(m.AccreditationCrosswalk.review_status == review_status)
    stmt = stmt.order_by(m.AccreditationCrosswalk.review_status, m.AccreditationCrosswalk.source_framework_family, m.AccreditationCrosswalk.id)
    return [model_dict(x) for x in db.scalars(stmt).all()]


@router.post("/api/quality360/institutional/crosswalks", status_code=201)
def quality360_create_crosswalk(body: s.AccreditationCrosswalkCreate, db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    src = body.source_framework_family.strip().upper()
    dst = body.target_framework_family.strip().upper()
    if src == dst and body.source_criterion_code.strip() == body.target_criterion_code.strip():
        raise HTTPException(422, "Aynı framework/ölçüt kendi kendine crosswalk olamaz")
    actor = current_user()
    row = m.AccreditationCrosswalk(
        source_framework_family=src,
        source_framework_version=body.source_framework_version.strip(),
        source_criterion_code=body.source_criterion_code.strip(),
        target_framework_family=dst,
        target_framework_version=body.target_framework_version.strip(),
        target_criterion_code=body.target_criterion_code.strip(),
        relationship=body.relationship,
        rationale=body.rationale.strip(),
        review_status="draft",
        created_by=actor.get("email") or "",
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Bu cross-framework eşleme zaten kayıtlı")
    _audit(db, "accreditation_crosswalk_create", "accreditation_crosswalk", row.id, {"source":src,"target":dst})
    _commit(db)
    db.refresh(row)
    return model_dict(row)


@router.patch("/api/quality360/institutional/crosswalks/{crosswalk_id}")
def quality360_review_crosswalk(crosswalk_id: int, body: s.AccreditationCrosswalkReview, db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    row = db.get(m.AccreditationCrosswalk, crosswalk_id)
    if not row:
        raise HTTPException(404, "Crosswalk kaydı bulunamadı")
    actor = current_user()
    row.review_status = body.review_status
    row.approved_by = actor.get("email") or "" if body.review_status == "approved" else ""
    row.approved_at = datetime.now(timezone.utc) if body.review_status == "approved" else None
    row.updated_at = datetime.now(timezone.utc)
    _audit(db, "accreditation_crosswalk_review", "accreditation_crosswalk", row.id, {"status":body.review_status})
    _commit(db)
    db.refresh(row)
    return model_dict(row)


@router.get("/api/quality360/institutional/readiness-snapshots")
def quality360_readiness_snapshots(academic_year: str, scope_type: str = "institution", scope_key: str = "DOGUS", db: Session = Depends(get_db)):
    require_roles("admin", "quality", "faculty_admin", "department_head", "program_head")
    stmt = select(m.InstitutionalReadinessSnapshot).where(
        m.InstitutionalReadinessSnapshot.academic_year == academic_year,
        m.InstitutionalReadinessSnapshot.scope_type == scope_type,
        m.InstitutionalReadinessSnapshot.scope_key == scope_key,
    ).order_by(m.InstitutionalReadinessSnapshot.snapshot_no.desc())
    return [model_dict(x) for x in db.scalars(stmt).all()]


@router.post("/api/quality360/institutional/readiness-snapshots", status_code=201)
def quality360_freeze_readiness_snapshot(body: s.ReadinessSnapshotCreate, db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    payload = institutional_accreditation_readiness(db, body.academic_year)
    if body.scope_type == "faculty":
        payload = {**payload, "programs":[x for x in payload["programs"] if (x.get("faculty") or "") == body.scope_key]}
    elif body.scope_type == "program":
        try:
            pid = int(body.scope_key)
        except ValueError:
            raise HTTPException(422, "Program scope_key program id olmalıdır")
        payload = {**payload, "programs":[x for x in payload["programs"] if x.get("program_id") == pid]}
    canonical = __import__('json').dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    latest = db.scalar(select(m.InstitutionalReadinessSnapshot).where(
        m.InstitutionalReadinessSnapshot.academic_year == body.academic_year,
        m.InstitutionalReadinessSnapshot.scope_type == body.scope_type,
        m.InstitutionalReadinessSnapshot.scope_key == body.scope_key,
    ).order_by(m.InstitutionalReadinessSnapshot.snapshot_no.desc()))
    actor = current_user()
    row = m.InstitutionalReadinessSnapshot(
        academic_year=body.academic_year, scope_type=body.scope_type, scope_key=body.scope_key,
        snapshot_no=(latest.snapshot_no + 1 if latest else 1), payload=payload, content_sha256=digest,
        frozen_by=actor.get("email") or "",
    )
    db.add(row); db.flush()
    _audit(db, "institutional_readiness_snapshot_freeze", "institutional_readiness_snapshot", row.id, {"sha256":digest})
    _commit(db); db.refresh(row)
    return model_dict(row)
