from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import models as m
from .authz import current_user, require_program_access, require_roles, require_student_access
from .compliance_schemas import (
    AccreditationApplicationCreate, AccreditationApplicationUpdate, BudgetLineCreate,
    BudgetPlanCreate, ControlledDocumentCreate, ControlledDocumentRevisionCreate,
    AccreditationFindingCreate, AccreditationFindingUpdate, AccreditationVisitNoteCreate, AccreditationDecisionCreate, AccreditationFinalReportUpdate, MedekEvaluatorReportItemCreate, MedekEvaluatorReportItemUpdate, MedekPdrFormAnalysisCreate, MedekPdrFormAnalysisUpdate,
    DocumentRequestCreate, DocumentRequestUpdate, EvaluatorWorkspaceCreate, EvaluatorWorkspaceAccessUpdate,
    FacultyCVRevisionCreate, FacultyWorkloadCreate, FrameworkFreezeRequest,
    GraduateFollowupCreate, InfrastructureMaintenanceCreate, MissionActivityCreate,
    PEAObjectiveCreate, PEAOutcomeMapCreate, ProgramOutcomeComponentCreate,
    ReportTemplateCreate, StudentOutcomeSnapshotCreate,
)
from .config import settings
from .db import get_db
from .security import read_upload_limited, validate_document_upload, validate_generic_zip, verify_stored_file
from .services.compliance import (
    build_compliance_report_docx, build_course_file_docx, build_evidence_room_zip,
    build_student_outcome_card, build_student_outcome_card_pdf, compliance_matrix, framework_criteria_tree,
    build_template_report_docx, build_medek_institution_report_docx, build_medek_institution_report_pdf,
    freeze_framework, quality_domain_dashboard, seed_report_templates,
    snapshot_student_outcomes, stable_sha256,
)
from .services.quality360 import model_dict, seed_builtin_frameworks, validate_mudek_framework_selection, validate_medek_framework_selection
from .services.framework_lifecycle_catalog import lifecycle_profiles

router = APIRouter(tags=["Accreditation Compliance Core"])

@router.get("/api/compliance/framework-lifecycle-profiles")
def framework_lifecycle_profiles(cycle_year: int = 2026):
    require_roles("admin", "quality", "faculty_admin", "department_head", "program_head")
    if cycle_year < 2020 or cycle_year > 2100:
        raise HTTPException(422, "Geçersiz akreditasyon döngü yılı")
    return lifecycle_profiles(cycle_year)


STAGES = [
    "preparation", "submitted", "pre_review", "correction", "visit_ready",
    "site_visit", "response_30_day", "response_7_day", "decision", "closed",
]

SITE_VISIT_FLOW = ["preparation", "submitted", "pre_review", "correction", "visit_ready", "site_visit", "response_30_day", "decision", "closed"]
REPORT_ONLY_FLOW = ["preparation", "submitted", "pre_review", "correction", "response_30_day", "decision", "closed"]
MEDEK_SITE_VISIT_FLOW = ["preparation", "submitted", "pre_review", "correction", "visit_ready", "site_visit", "response_7_day", "decision", "closed"]
MEDEK_REPORT_ONLY_FLOW = ["preparation", "submitted", "pre_review", "correction", "response_7_day", "decision", "closed"]

def _application_family(db: Session, app: m.AccreditationApplication) -> str:
    fw = db.get(m.QualityFrameworkProfile, app.framework_profile_id)
    return (fw.framework_family if fw else "") or ""

def _allowed_flow(app: m.AccreditationApplication, db: Session | None = None) -> list[str]:
    family = _application_family(db, app) if db is not None else ""
    if family == "MEDEK":
        return MEDEK_REPORT_ONLY_FLOW if app.evaluation_mode == "report_only" else MEDEK_SITE_VISIT_FLOW
    return REPORT_ONLY_FLOW if app.evaluation_mode == "report_only" else SITE_VISIT_FLOW

def _decision_row(db: Session, app: m.AccreditationApplication, action: str, from_stage: str = "", to_stage: str = "", decision_code: str = "", note: str = "", payload: dict[str, Any] | None = None) -> m.AccreditationDecisionHistory:
    try:
        actor = current_user().get("email") or "system"
    except Exception:
        actor = "system"
    row = m.AccreditationDecisionHistory(application_id=app.id, action=action, from_stage=from_stage, to_stage=to_stage, decision_code=decision_code, note=note, payload=payload or {}, actor=actor)
    db.add(row); db.flush(); return row


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
        actor_roles=list(actor.get("role_names") or []), action=action,
        entity_type=entity_type, entity_id=entity_id,
        payload=json.loads(json.dumps(payload or {}, ensure_ascii=False, default=str)),
    ))


def _program(db: Session, program_id: int, *, write: bool = True) -> m.Program:
    p = db.get(m.Program, program_id)
    if not p:
        raise HTTPException(404, "Program bulunamadı")
    require_program_access(db, program_id, write=write, accreditation=True)
    return p



def _latest_family_general_application(db: Session, program_id: int, family: str) -> m.AccreditationApplication | None:
    rows = list(db.scalars(select(m.AccreditationApplication).where(
        m.AccreditationApplication.program_id == program_id,
        m.AccreditationApplication.application_type.in_(["general", "renewal"]),
    ).order_by(m.AccreditationApplication.id.desc())).all())
    for row in rows:
        fw = db.get(m.QualityFrameworkProfile, row.framework_profile_id)
        if fw and (fw.framework_family or "").casefold() == family.casefold():
            return row
    return None


def _request_sla_payload(row: m.AccreditationDocumentRequest) -> dict[str, Any]:
    data = model_dict(row)
    today = date.today()
    if row.status in {"answered", "closed"}:
        data["sla_state"] = row.status
        data["days_remaining"] = 0
    elif row.due_date:
        remaining = (row.due_date - today).days
        data["days_remaining"] = remaining
        data["sla_state"] = "overdue" if remaining < 0 else ("due_soon" if remaining <= 3 else "open")
    else:
        data["sla_state"] = "open"
        data["days_remaining"] = None
    return data

def _obj(db: Session, cls: type, obj_id: int, message: str):
    obj = db.get(cls, obj_id)
    if not obj:
        raise HTTPException(404, message)
    return obj


def _template_root() -> Path:
    p = Path(settings.evidence_storage_path) / "quality360" / "official-templates"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _controlled_root() -> Path:
    p = Path(settings.evidence_storage_path) / "quality360" / "controlled-documents"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_filename(name: str) -> str:
    base = Path(name or "document.bin").name
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return (base or "document.bin")[:180]




def _add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years)


def _medek_decision_profile(code: str, start: date | None) -> dict[str, Any]:
    profiles = {
        "full": {"label":"Tam Akreditasyon","term_years":4,"next_review_type":"reaccreditation","review_offset_years":3},
        "conditional": {"label":"Koşullu Akreditasyon","term_years":2,"next_review_type":"interim_site_visit","review_offset_years":2},
        "short_term": {"label":"Kısa Süreli Akreditasyon","term_years":1,"next_review_type":"interim_site_visit","review_offset_years":1},
        "reapply": {"label":"Yeniden Başvuru","term_years":0,"next_review_type":"general_reapplication","review_offset_years":None},
    }
    if code not in profiles:
        raise HTTPException(409,"MEDEK nihai karar kodu full / conditional / short_term / reapply olmalıdır")
    out=dict(profiles[code])
    out["code"]=code
    if start and out["term_years"]:
        out["accreditation_end"]=_add_years(start,out["term_years"]) - timedelta(days=1)
    else:
        out["accreditation_end"]=None
    if start and out["review_offset_years"]:
        out["next_review_due"]=_add_years(start,out["review_offset_years"]) - timedelta(days=1)
    else:
        out["next_review_due"]=None
    return out


def _medek_final_readiness_payload(db: Session, app: m.AccreditationApplication) -> dict[str, Any]:
    _require_medek(db, app)
    forms=list(db.scalars(select(m.MedekPdrFormAnalysis).where(m.MedekPdrFormAnalysis.application_id==app.id)).all())
    confirmed_forms={x.form_code for x in forms if x.status=="confirmed"}
    required_forms={"FORM1","FORM2","FORM3"}
    pdr=list(db.scalars(select(m.MedekEvaluatorReportItem).where(
        m.MedekEvaluatorReportItem.application_id==app.id,
        m.MedekEvaluatorReportItem.report_phase=="final",
        m.MedekEvaluatorReportItem.status=="confirmed"
    )).all())
    assessments=[x for x in pdr if x.item_type=="assessment"]
    numeric=[]
    for x in assessments:
        try:
            n=int(str(x.assessment_value).strip().split()[0])
            if 1 <= n <= 5: numeric.append({"criterion_code":x.criterion_code,"score":n})
        except Exception:
            continue
    missing_forms=sorted(required_forms-confirmed_forms)
    gaps=[]
    if missing_forms: gaps.append("FORM1/FORM2/FORM3 onayları eksik: "+", ".join(missing_forms))
    if not pdr: gaps.append("Onaylanmış nihai PDR maddesi yok")
    if not assessments: gaps.append("Nihai PDR içinde ölçüt değerlendirme satırı yok")
    if app.stage not in {"response_7_day","decision"}: gaps.append("Başvuru +7 gün yanıt veya karar aşamasında değil")
    eligible=[]
    if numeric:
        scores=[x["score"] for x in numeric]
        if any(x==1 for x in scores): eligible=["reapply"]
        else:
            if all(x>=3 for x in scores): eligible.append("full")
            if any(x==2 for x in scores): eligible.append("conditional")
            # Kısa süreli karar yalnız skorla otomatik belirlenmez; MEK insan kararı gerekir.
            if any(x==2 for x in scores) and not any(x>=4 for x in scores): eligible.append("short_term")
    return {
        "application":model_dict(app),
        "ready":not gaps,
        "gaps":gaps,
        "confirmed_forms":sorted(confirmed_forms),
        "final_pdr_count":len(pdr),
        "assessment_rows":numeric,
        "eligible_decision_options":eligible,
        "official_rule_note":"MEK nihai karar merciidir. Sistem yalnız resmî karar koşullarına göre uygunluk/uyarı ve süre otomasyonu sağlar; otomatik karar vermez.",
    }

@router.get("/api/compliance/catalogs")
def compliance_catalogs():
    return {
        "application_stages": STAGES,
        "mission_domains": ["research", "social_contribution", "internationalization"],
        "document_types": ["policy", "directive", "procedure", "instruction", "form", "plan", "report", "other"],
        "snapshot_types": ["progress", "graduation"],
        "evidence_rooms": ["BBO", "FBO"],
        "official_template_placeholders": ["PROGRAM_CODE", "PROGRAM_NAME", "ACADEMIC_YEAR", "FACULTY", "DEPARTMENT"],
    }


# ---------------------------------------------------------------------------
# Official framework / report template registry and immutable snapshots
# ---------------------------------------------------------------------------
@router.get("/api/compliance/templates")
def templates(db: Session = Depends(get_db)):
    return [model_dict(x) for x in seed_report_templates(db)]


@router.post("/api/compliance/templates", status_code=201)
def template_create(body: ReportTemplateCreate, db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    obj = m.AccreditationReportTemplate(**body.model_dump(), is_builtin=False)
    db.add(obj); db.flush(); _audit(db, "compliance_template_create", "accreditation_report_template", obj.id, body.model_dump()); _commit(db)
    return model_dict(obj)


@router.post("/api/compliance/templates/{template_id}/upload", status_code=201)
async def template_upload(template_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    obj = _obj(db, m.AccreditationReportTemplate, template_id, "Rapor şablonu bulunamadı")
    payload = await read_upload_limited(file)
    if not payload:
        raise HTTPException(400, "Boş şablon yüklenemez")
    original = _safe_filename(file.filename or "official-template.docx")
    suffix = Path(original).suffix.lower()
    if suffix not in {".docx", ".xlsx", ".pdf", ".zip"}:
        raise HTTPException(422, "Resmî şablon DOCX/XLSX/PDF/ZIP olmalıdır")
    if suffix == ".zip":
        validate_generic_zip(payload, purpose="Resmî şablon ZIP")
        canonical_mime = "application/zip"
    else:
        canonical_mime = validate_document_upload(original, payload, purpose="Resmî akreditasyon şablonu", allowed_extensions={".docx", ".xlsx", ".pdf"})
    stored = f"t{obj.id}_{uuid.uuid4().hex}{suffix}"
    path = _template_root() / stored
    path.write_bytes(payload)
    obj.original_name = original
    obj.stored_name = stored
    obj.mime_type = canonical_mime
    obj.source_sha256 = hashlib.sha256(payload).hexdigest()
    obj.locked = True
    _audit(db, "compliance_template_upload_freeze", "accreditation_report_template", obj.id, {"sha256": obj.source_sha256, "original_name": original})
    _commit(db)
    return model_dict(obj)


@router.get("/api/compliance/templates/{template_id}/render.docx")
def template_render(template_id: int, program_id: int, academic_year: str, db: Session = Depends(get_db)):
    _program(db, program_id, write=False)
    try:
        payload, name = build_template_report_docx(db, template_id, program_id, academic_year)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return Response(payload, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/api/compliance/templates/{template_id}/source")
def template_source(template_id: int, db: Session = Depends(get_db)):
    obj = _obj(db, m.AccreditationReportTemplate, template_id, "Rapor şablonu bulunamadı")
    if not obj.stored_name:
        raise HTTPException(404, "Bu şablonun fiziksel resmî kaynak dosyası henüz yüklenmedi")
    path = _template_root() / obj.stored_name
    if not path.is_file():
        raise HTTPException(404, "Şablon kaynak dosyası bulunamadı")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != obj.source_sha256:
        raise HTTPException(409, "Resmî şablon SHA-256 bütünlük kontrolü başarısız")
    return Response(payload, media_type=obj.mime_type, headers={"Content-Disposition": f'attachment; filename="{obj.original_name}"'})


@router.post("/api/compliance/programs/{program_id}/framework-freeze", status_code=201)
def framework_freeze(program_id: int, body: FrameworkFreezeRequest, db: Session = Depends(get_db)):
    _program(db, program_id)
    actor = current_user()
    try:
        obj = freeze_framework(db, program_id, body.framework_profile_id, body.academic_year, actor.get("email") or "quality")
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    _audit(db, "framework_snapshot_freeze", "quality_framework_snapshot", obj.id, {"program_id": program_id, "academic_year": body.academic_year, "sha256": obj.content_sha256})
    _commit(db)
    return model_dict(obj)


@router.get("/api/compliance/programs/{program_id}/framework-snapshots")
def framework_snapshots(program_id: int, academic_year: str | None = None, db: Session = Depends(get_db)):
    _program(db, program_id, write=False)
    stmt = select(m.QualityFrameworkSnapshot).where(m.QualityFrameworkSnapshot.program_id == program_id)
    if academic_year:
        stmt = stmt.where(m.QualityFrameworkSnapshot.academic_year == academic_year)
    return [model_dict(x) for x in db.scalars(stmt.order_by(m.QualityFrameworkSnapshot.id.desc())).all()]


@router.get("/api/compliance/programs/{program_id}/criteria-tree")
def criteria_tree(program_id: int, framework_profile_id: int, academic_year: str, db: Session = Depends(get_db)):
    _program(db, program_id, write=False)
    snap = db.scalar(select(m.QualityFrameworkSnapshot).where(
        m.QualityFrameworkSnapshot.program_id == program_id,
        m.QualityFrameworkSnapshot.academic_year == academic_year,
        m.QualityFrameworkSnapshot.framework_profile_id == framework_profile_id,
    ))
    fw = snap or db.get(m.QualityFrameworkProfile, framework_profile_id)
    if not fw:
        raise HTTPException(404, "Kalite çerçevesi bulunamadı")
    tree = framework_criteria_tree(fw)
    return {"source": "frozen" if snap else "live", "framework": model_dict(fw), "criteria": tree, "criteria_count": len(tree), "subcriteria_count": sum(len(x.get("subcriteria") or []) for x in tree)}


# ---------------------------------------------------------------------------
# Program Educational Objectives and PO components
# ---------------------------------------------------------------------------
@router.get("/api/compliance/programs/{program_id}/program-outcomes")
def compliance_program_outcomes(program_id: int, academic_year: str | None = None, db: Session = Depends(get_db)):
    _program(db, program_id, write=False)
    stmt = select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == program_id)
    if academic_year:
        stmt = stmt.where(m.ProgramOutcome.academic_year == academic_year)
    rows = list(db.scalars(stmt.order_by(m.ProgramOutcome.code)).all())
    out=[]
    for po in rows:
        d=model_dict(po)
        d["components"]=[model_dict(x) for x in db.scalars(select(m.ProgramOutcomeComponent).where(m.ProgramOutcomeComponent.program_outcome_id==po.id).order_by(m.ProgramOutcomeComponent.code)).all()]
        out.append(d)
    return out


@router.get("/api/compliance/programs/{program_id}/pea")
def pea_list(program_id: int, academic_year: str | None = None, db: Session = Depends(get_db)):
    _program(db, program_id, write=False)
    stmt = select(m.ProgramEducationalObjective).where(m.ProgramEducationalObjective.program_id == program_id)
    if academic_year:
        stmt = stmt.where(m.ProgramEducationalObjective.academic_year == academic_year)
    rows = list(db.scalars(stmt.order_by(m.ProgramEducationalObjective.code)).all())
    out = []
    for x in rows:
        d = model_dict(x)
        d["outcome_maps"] = [model_dict(z) for z in db.scalars(select(m.ProgramEducationalObjectiveOutcomeMap).where(m.ProgramEducationalObjectiveOutcomeMap.objective_id == x.id)).all()]
        out.append(d)
    return out


@router.post("/api/compliance/pea", status_code=201)
def pea_create(body: PEAObjectiveCreate, db: Session = Depends(get_db)):
    _program(db, body.program_id)
    obj = m.ProgramEducationalObjective(**body.model_dump())
    db.add(obj); db.flush(); _audit(db, "pea_create", "program_educational_objective", obj.id, body.model_dump()); _commit(db)
    return model_dict(obj)


@router.post("/api/compliance/pea/outcome-map", status_code=201)
def pea_map_create(body: PEAOutcomeMapCreate, db: Session = Depends(get_db)):
    objective = _obj(db, m.ProgramEducationalObjective, body.objective_id, "Program Eğitim Amacı bulunamadı")
    po = _obj(db, m.ProgramOutcome, body.program_outcome_id, "Program Çıktısı bulunamadı")
    if po.program_id != objective.program_id:
        raise HTTPException(422, "PEA ve PÇ aynı programa ait olmalıdır")
    _program(db, objective.program_id)
    obj = m.ProgramEducationalObjectiveOutcomeMap(**body.model_dump())
    db.add(obj); db.flush(); _audit(db, "pea_po_map_create", "pea_po_map", obj.id, body.model_dump()); _commit(db)
    return model_dict(obj)


@router.get("/api/compliance/program-outcomes/{program_outcome_id}/components")
def po_components(program_outcome_id: int, db: Session = Depends(get_db)):
    po = _obj(db, m.ProgramOutcome, program_outcome_id, "Program Çıktısı bulunamadı")
    _program(db, po.program_id, write=False)
    return [model_dict(x) for x in db.scalars(select(m.ProgramOutcomeComponent).where(m.ProgramOutcomeComponent.program_outcome_id == program_outcome_id).order_by(m.ProgramOutcomeComponent.code)).all()]


@router.post("/api/compliance/program-outcome-components", status_code=201)
def po_component_create(body: ProgramOutcomeComponentCreate, db: Session = Depends(get_db)):
    po = _obj(db, m.ProgramOutcome, body.program_outcome_id, "Program Çıktısı bulunamadı")
    _program(db, po.program_id)
    obj = m.ProgramOutcomeComponent(**body.model_dump())
    db.add(obj); db.flush(); _audit(db, "po_component_create", "program_outcome_component", obj.id, body.model_dump()); _commit(db)
    return model_dict(obj)


# ---------------------------------------------------------------------------
# Per-student / per-graduate cumulative outcome report card
# ---------------------------------------------------------------------------
@router.get("/api/compliance/students/{student_id}/outcome-card")
def student_outcome_card(student_id: int, academic_year: str | None = None, db: Session = Depends(get_db)):
    student = _obj(db, m.Student, student_id, "Öğrenci bulunamadı")
    require_student_access(db, student_id, write=False)
    try:
        return build_student_outcome_card(db, student_id, academic_year)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/api/compliance/students/{student_id}/outcome-card.pdf")
def student_outcome_card_pdf(student_id: int, academic_year: str | None = None, db: Session = Depends(get_db)):
    student = _obj(db, m.Student, student_id, "Öğrenci bulunamadı")
    require_student_access(db, student_id, write=False)
    try:
        payload, filename = build_student_outcome_card_pdf(db, student_id, academic_year)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(payload, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/api/compliance/students/{student_id}/outcome-snapshots", status_code=201)
def student_outcome_snapshot(student_id: int, body: StudentOutcomeSnapshotCreate, db: Session = Depends(get_db)):
    student = _obj(db, m.Student, student_id, "Öğrenci bulunamadı")
    _program(db, student.program_id)
    obj = snapshot_student_outcomes(db, student_id, body.academic_year, body.snapshot_type, body.freeze)
    _audit(db, "student_outcome_snapshot", "student_outcome_snapshot", obj.id, {"student_id": student_id, "academic_year": body.academic_year, "freeze": body.freeze, "sha256": obj.content_sha256})
    _commit(db)
    return model_dict(obj)


@router.get("/api/compliance/students/{student_id}/outcome-snapshots")
def student_outcome_snapshots(student_id: int, db: Session = Depends(get_db)):
    student = _obj(db, m.Student, student_id, "Öğrenci bulunamadı")
    require_student_access(db, student_id, write=False)
    return [model_dict(x) for x in db.scalars(select(m.StudentOutcomeSnapshot).where(m.StudentOutcomeSnapshot.student_id == student_id).order_by(m.StudentOutcomeSnapshot.id.desc())).all()]


# ---------------------------------------------------------------------------
# Accreditation lifecycle + evaluator workspace + additional document requests
# ---------------------------------------------------------------------------
@router.get("/api/compliance/programs/{program_id}/applications")
def applications(program_id: int, academic_year: str | None = None, db: Session = Depends(get_db)):
    _program(db, program_id, write=False)
    stmt = select(m.AccreditationApplication).where(m.AccreditationApplication.program_id == program_id)
    if academic_year:
        stmt = stmt.where(m.AccreditationApplication.academic_year == academic_year)
    return [model_dict(x) for x in db.scalars(stmt.order_by(m.AccreditationApplication.id.desc())).all()]


@router.post("/api/compliance/applications", status_code=201)
def application_create(body: AccreditationApplicationCreate, db: Session = Depends(get_db)):
    _program(db, body.program_id)
    if body.stage not in STAGES:
        raise HTTPException(422, "Geçersiz akreditasyon aşaması")
    framework = db.get(m.QualityFrameworkProfile, body.framework_profile_id)
    if not framework:
        seed_builtin_frameworks(db); framework = db.get(m.QualityFrameworkProfile, body.framework_profile_id)
    if not framework:
        raise HTTPException(404, "Akreditasyon framework'ü bulunamadı")
    try:
        validate_mudek_framework_selection(db, framework, body.academic_year, body.application_type, program_id=body.program_id)
        validate_medek_framework_selection(db, framework, body.academic_year, body.application_type, program_id=body.program_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    freeze = freeze_framework(db, body.program_id, body.framework_profile_id, body.academic_year, current_user().get("email") or "quality")
    data = body.model_dump(); data["framework_snapshot_id"] = freeze.id
    previous = None
    if framework.framework_family in {"MÜDEK", "MEDEK"} and body.application_type in {"interim", "monitoring"}:
        previous = db.get(m.AccreditationApplication, body.previous_application_id) if body.previous_application_id else _latest_family_general_application(db, body.program_id, framework.framework_family)
        if not previous:
            raise HTTPException(422, f"{framework.framework_family} ara değerlendirmesi için önceki genel/yeniden genel değerlendirme gereklidir")
        data["previous_application_id"] = previous.id
    obj = m.AccreditationApplication(**data)
    db.add(obj); db.flush()
    if previous and framework.framework_family == "MÜDEK":
        prior_findings = list(db.scalars(select(m.AccreditationFinding).where(
            m.AccreditationFinding.application_id == previous.id,
            m.AccreditationFinding.finding_type == "weakness",
            m.AccreditationFinding.status.notin_(["resolved", "closed"]),
        )).all())
        for finding in prior_findings:
            db.add(m.AccreditationFinding(
                application_id=obj.id, source_finding_id=finding.id, criterion_code=finding.criterion_code,
                finding_type=finding.finding_type, title=finding.title, description=finding.description,
                status="monitoring", owner=finding.owner, due_date=finding.due_date,
                evidence_refs=list(finding.evidence_refs or []), response_note="", carried_forward=True,
            ))
    elif previous and framework.framework_family == "MEDEK":
        prior_items = list(db.scalars(select(m.MedekEvaluatorReportItem).where(
            m.MedekEvaluatorReportItem.application_id == previous.id,
            m.MedekEvaluatorReportItem.report_phase == "final",
            m.MedekEvaluatorReportItem.item_type == "improvement_area",
            m.MedekEvaluatorReportItem.status == "confirmed",
        )).all())
        for item in prior_items:
            db.add(m.MedekEvaluatorReportItem(
                application_id=obj.id, source_item_id=item.id, report_phase="pre_consensus", criterion_code=item.criterion_code,
                evaluator_name="Önceki değerlendirmeden devralındı", item_type="improvement_area", narrative=item.narrative,
                assessment_value=item.assessment_value, evidence_refs=list(item.evidence_refs or []), status="confirmed", carried_forward=True,
            ))
    _audit(db, "accreditation_application_create", "accreditation_application", obj.id, data); _commit(db)
    return model_dict(obj)


@router.patch("/api/compliance/applications/{application_id}")
def application_update(application_id: int, body: AccreditationApplicationUpdate, db: Session = Depends(get_db)):
    obj = _obj(db, m.AccreditationApplication, application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, obj.program_id)
    data = body.model_dump(exclude_unset=True)
    if "evaluation_mode" in data and data["evaluation_mode"] is not None and obj.stage != "preparation" and data["evaluation_mode"] != obj.evaluation_mode:
        raise HTTPException(409, "Değerlendirme modu yalnız hazırlık aşamasında değiştirilebilir")
    target_mode = data.get("evaluation_mode") or obj.evaluation_mode
    if "stage" in data and data["stage"] is not None:
        if data["stage"] not in STAGES:
            raise HTTPException(422, "Geçersiz akreditasyon aşaması")
        flow = _allowed_flow(obj, db) if target_mode == obj.evaluation_mode else (MEDEK_REPORT_ONLY_FLOW if _application_family(db,obj)=="MEDEK" and target_mode=="report_only" else MEDEK_SITE_VISIT_FLOW if _application_family(db,obj)=="MEDEK" else REPORT_ONLY_FLOW if target_mode=="report_only" else SITE_VISIT_FLOW)
        if obj.stage not in flow or data["stage"] not in flow:
            raise HTTPException(409, "Bu değerlendirme modu için geçersiz akreditasyon aşaması")
        old_idx, new_idx = flow.index(obj.stage), flow.index(data["stage"])
        if new_idx < old_idx or new_idx > old_idx + 1:
            raise HTTPException(409, "Akreditasyon yaşam döngüsü yalnız bir sonraki aşamaya ilerletilebilir")
        _decision_row(db, obj, "stage_transition", obj.stage, data["stage"], payload={"evaluation_mode": target_mode})
    for k, v in data.items():
        setattr(obj, k, v)
    obj.updated_at = datetime.now(timezone.utc)
    _audit(db, "accreditation_application_update", "accreditation_application", obj.id, data); _commit(db)
    return model_dict(obj)


def _evaluator_workspace_payload(db: Session, ws: m.EvaluatorWorkspace) -> dict[str, Any]:
    app = _obj(db, m.AccreditationApplication, ws.application_id, "Akreditasyon başvurusu bulunamadı")
    fw = db.get(m.QualityFrameworkSnapshot, app.framework_snapshot_id) if app.framework_snapshot_id else None
    requests = [_request_sla_payload(x) for x in db.scalars(select(m.AccreditationDocumentRequest).where(m.AccreditationDocumentRequest.application_id == app.id).order_by(m.AccreditationDocumentRequest.id)).all()]
    findings = [model_dict(x) for x in db.scalars(select(m.AccreditationFinding).where(m.AccreditationFinding.application_id == app.id).order_by(m.AccreditationFinding.id)).all()]
    notes = [model_dict(x) for x in db.scalars(select(m.AccreditationVisitNote).where(m.AccreditationVisitNote.application_id == app.id, m.AccreditationVisitNote.visibility.in_(["evaluator", "institution"])).order_by(m.AccreditationVisitNote.id)).all()]
    workspace = model_dict(ws)
    workspace.pop("invitation_token_hash", None)
    return {"workspace": workspace, "read_only": True, "application": model_dict(app), "framework_snapshot": model_dict(fw) if fw else None, "document_requests": requests, "findings": findings, "visit_notes": notes, "snapshot_sha256": ws.snapshot_sha256}


def _ensure_evaluator_workspace_active(ws: m.EvaluatorWorkspace) -> None:
    now = datetime.now(timezone.utc)
    if not ws.active:
        raise HTTPException(410, "Değerlendirici çalışma alanı devre dışı")
    if ws.expires_at:
        expiry = ws.expires_at if ws.expires_at.tzinfo else ws.expires_at.replace(tzinfo=timezone.utc)
        if expiry <= now:
            raise HTTPException(410, "Değerlendirici çalışma alanının süresi doldu")


@router.post("/api/compliance/evaluator-workspaces", status_code=201)
def evaluator_workspace_create(body: EvaluatorWorkspaceCreate, db: Session = Depends(get_db)):
    app = _obj(db, m.AccreditationApplication, body.application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, app.program_id)
    snapshot = db.get(m.QualityFrameworkSnapshot, app.framework_snapshot_id) if app.framework_snapshot_id else None
    digest = stable_sha256({"application": model_dict(app), "framework_snapshot_sha256": snapshot.content_sha256 if snapshot else ""})
    now = datetime.now(timezone.utc)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    data = body.model_dump()
    if not data.get("expires_at"):
        data["expires_at"] = now + timedelta(days=14)
    obj = m.EvaluatorWorkspace(**data, snapshot_sha256=digest, invitation_token_hash=token_hash, token_issued_at=now)
    db.add(obj); db.flush(); _audit(db, "evaluator_workspace_create", "evaluator_workspace", obj.id, {"application_id": app.id, "snapshot_sha256": digest, "read_only": True, "expires_at": obj.expires_at}); _commit(db)
    result = model_dict(obj)
    result.pop("invitation_token_hash", None)
    result["invitation_token"] = raw_token
    result["invitation_path"] = f"/evaluator.html?workspace={obj.id}#token={raw_token}"
    result["token_delivery_note"] = "Bu token ve davet bağlantısı yalnız bu yanıtta gösterilir; güvenli kanaldan değerlendiriciye iletin."
    return result


@router.get("/api/compliance/applications/{application_id}/evaluator-workspaces")
def evaluator_workspaces(application_id: int, db: Session = Depends(get_db)):
    app = _obj(db, m.AccreditationApplication, application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, app.program_id, write=False)
    out=[]
    for x in db.scalars(select(m.EvaluatorWorkspace).where(m.EvaluatorWorkspace.application_id == application_id)).all():
        row=model_dict(x); row.pop("invitation_token_hash",None); out.append(row)
    return out


@router.get("/api/compliance/evaluator-workspaces/{workspace_id}/snapshot")
def evaluator_snapshot(workspace_id: int, db: Session = Depends(get_db)):
    ws = _obj(db, m.EvaluatorWorkspace, workspace_id, "Değerlendirici çalışma alanı bulunamadı")
    app = _obj(db, m.AccreditationApplication, ws.application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, app.program_id, write=False)
    _ensure_evaluator_workspace_active(ws)
    return _evaluator_workspace_payload(db, ws)


@router.patch("/api/compliance/evaluator-workspaces/{workspace_id}/access")
def evaluator_workspace_access(workspace_id: int, body: EvaluatorWorkspaceAccessUpdate, db: Session = Depends(get_db)):
    ws = _obj(db, m.EvaluatorWorkspace, workspace_id, "Değerlendirici çalışma alanı bulunamadı")
    app = _obj(db, m.AccreditationApplication, ws.application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, app.program_id)
    ws.active = bool(body.active)
    _audit(db, "evaluator_workspace_access_update", "evaluator_workspace", ws.id, {"active": ws.active})
    _commit(db)
    row=model_dict(ws); row.pop("invitation_token_hash",None); return row


@router.get("/api/public/evaluator-workspaces/{workspace_id}/snapshot")
def evaluator_public_snapshot(workspace_id: int, x_dou_evaluator_token: str = Header(default="", alias="X-DOU-Evaluator-Token"), db: Session = Depends(get_db)):
    ws = _obj(db, m.EvaluatorWorkspace, workspace_id, "Değerlendirici çalışma alanı bulunamadı")
    _ensure_evaluator_workspace_active(ws)
    supplied = hashlib.sha256((x_dou_evaluator_token or "").encode("utf-8")).hexdigest()
    if not ws.invitation_token_hash or not hmac.compare_digest(supplied, ws.invitation_token_hash):
        raise HTTPException(401, "Geçersiz değerlendirici erişim tokenı")
    ws.last_access_at = datetime.now(timezone.utc)
    _audit(db, "evaluator_workspace_public_access", "evaluator_workspace", ws.id, {"application_id": ws.application_id})
    _commit(db)
    return _evaluator_workspace_payload(db, ws)


@router.post("/api/compliance/document-requests", status_code=201)
def document_request_create(body: DocumentRequestCreate, db: Session = Depends(get_db)):
    app = _obj(db, m.AccreditationApplication, body.application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, app.program_id)
    obj = m.AccreditationDocumentRequest(**body.model_dump())
    db.add(obj); db.flush(); _audit(db, "accreditation_document_request_create", "accreditation_document_request", obj.id, body.model_dump()); _commit(db)
    return model_dict(obj)


@router.patch("/api/compliance/document-requests/{request_id}")
def document_request_update(request_id: int, body: DocumentRequestUpdate, db: Session = Depends(get_db)):
    obj = _obj(db, m.AccreditationDocumentRequest, request_id, "Ek belge talebi bulunamadı")
    app = _obj(db, m.AccreditationApplication, obj.application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, app.program_id)
    data = body.model_dump(exclude_unset=True)
    before = model_dict(obj)
    for k, v in data.items(): setattr(obj, k, v)
    now = datetime.now(timezone.utc)
    if data.get("status") == "answered" and obj.answered_at is None: obj.answered_at = now
    if data.get("status") == "closed" and obj.closed_at is None: obj.closed_at = now
    _audit(db, "accreditation_document_request_update", "accreditation_document_request", obj.id, data); _commit(db)
    return _request_sla_payload(obj)


@router.get("/api/compliance/applications/{application_id}/visit-control-center")
def visit_control_center(application_id: int, db: Session = Depends(get_db)):
    app = _obj(db, m.AccreditationApplication, application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, app.program_id, write=False)
    previous = db.get(m.AccreditationApplication, app.previous_application_id) if app.previous_application_id else None
    current_findings = list(db.scalars(select(m.AccreditationFinding).where(m.AccreditationFinding.application_id == app.id).order_by(m.AccreditationFinding.id)).all())
    prior_findings = list(db.scalars(select(m.AccreditationFinding).where(m.AccreditationFinding.application_id == previous.id).order_by(m.AccreditationFinding.id)).all()) if previous else []
    requests = list(db.scalars(select(m.AccreditationDocumentRequest).where(m.AccreditationDocumentRequest.application_id == app.id).order_by(m.AccreditationDocumentRequest.id)).all())
    notes = list(db.scalars(select(m.AccreditationVisitNote).where(m.AccreditationVisitNote.application_id == app.id).order_by(m.AccreditationVisitNote.id)).all())
    weakness_scope = sorted({x.criterion_code for x in prior_findings if x.finding_type == "weakness" and x.status not in {"resolved", "closed"} and x.criterion_code})
    open_findings = [x for x in current_findings if x.status not in {"resolved", "closed"}]
    overdue = [x for x in requests if _request_sla_payload(x)["sla_state"] == "overdue"]
    return {
        "application": model_dict(app), "previous_application": model_dict(previous) if previous else None,
        "interim_primary_scope_codes": weakness_scope,
        "findings": [model_dict(x) for x in current_findings],
        "previous_findings": [model_dict(x) for x in prior_findings],
        "document_requests": [_request_sla_payload(x) for x in requests],
        "visit_notes": [model_dict(x) for x in notes],
        "summary": {"open_findings": len(open_findings), "document_requests": len(requests), "overdue_requests": len(overdue), "visit_notes": len(notes), "response_30_day_open": app.stage == "response_30_day"},
    }


def _finding_revision(db: Session, obj: m.AccreditationFinding, before: dict[str, Any], after: dict[str, Any], rationale: str = "") -> m.AccreditationFindingRevision:
    try:
        actor = current_user().get("email") or "system"
    except Exception:
        actor = "system"
    row = m.AccreditationFindingRevision(finding_id=obj.id, application_id=obj.application_id, event_type="updated", before_payload=before, after_payload=after, rationale=rationale, actor=actor)
    db.add(row); db.flush(); return row


def _criterion_result_rows(findings: list[m.AccreditationFinding]) -> list[dict[str, Any]]:
    groups: dict[str, list[m.AccreditationFinding]] = {}
    for x in findings:
        groups.setdefault(x.criterion_code or "GENEL", []).append(x)
    severity = {"deficiency": 4, "weakness": 3, "concern": 2, "observation": 1, "strength": 0}
    rows=[]
    for code, items in sorted(groups.items()):
        open_items=[x for x in items if x.status not in {"resolved","closed"}]
        worst=max(open_items or items, key=lambda x: severity.get(x.finding_type,0)) if items else None
        rows.append({"criterion_code":code,"finding_count":len(items),"open_count":len(open_items),"result":"satisfied" if not open_items else (worst.finding_type if worst else "review"),"finding_ids":[x.id for x in items]})
    return rows


@router.post("/api/compliance/findings", status_code=201)
def accreditation_finding_create(body: AccreditationFindingCreate, db: Session = Depends(get_db)):
    app = _obj(db, m.AccreditationApplication, body.application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, app.program_id)
    obj = m.AccreditationFinding(**body.model_dump())
    db.add(obj); db.flush(); _audit(db, "accreditation_finding_create", "accreditation_finding", obj.id, body.model_dump()); _commit(db)
    return model_dict(obj)


@router.patch("/api/compliance/findings/{finding_id}")
def accreditation_finding_update(finding_id: int, body: AccreditationFindingUpdate, db: Session = Depends(get_db)):
    obj = _obj(db, m.AccreditationFinding, finding_id, "Akreditasyon bulgusu bulunamadı")
    app = _obj(db, m.AccreditationApplication, obj.application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, app.program_id)
    data = body.model_dump(exclude_unset=True)
    before = model_dict(obj)
    for k, v in data.items(): setattr(obj, k, v)
    obj.updated_at = datetime.now(timezone.utc)
    if data.get("status") in {"resolved", "closed"}: obj.resolved_at = datetime.now(timezone.utc)
    _finding_revision(db, obj, before, model_dict(obj), data.get("response_note") or "")
    _audit(db, "accreditation_finding_update", "accreditation_finding", obj.id, data); _commit(db)
    return model_dict(obj)


@router.post("/api/compliance/visit-notes", status_code=201)
def accreditation_visit_note_create(body: AccreditationVisitNoteCreate, db: Session = Depends(get_db)):
    app = _obj(db, m.AccreditationApplication, body.application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, app.program_id)
    if app.evaluation_mode == "report_only":
        raise HTTPException(409, "Raporla ara değerlendirmede saha ziyareti notu oluşturulamaz")
    data = body.model_dump()
    if data.get("occurred_at") is None: data["occurred_at"] = datetime.now(timezone.utc)
    obj = m.AccreditationVisitNote(**data)
    db.add(obj); db.flush(); _audit(db, "accreditation_visit_note_create", "accreditation_visit_note", obj.id, data); _commit(db)
    return model_dict(obj)


@router.post("/api/compliance/applications/{application_id}/open-30-day-response")
def open_30_day_response(application_id: int, db: Session = Depends(get_db)):
    app = _obj(db, m.AccreditationApplication, application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, app.program_id)
    expected = "correction" if app.evaluation_mode == "report_only" else "site_visit"
    if app.stage != expected:
        raise HTTPException(409, f"30-gün yanıt penceresi {app.evaluation_mode} modu için {expected} aşamasından açılabilir")
    old_stage = app.stage
    app.stage = "response_30_day"
    app.correction_due = date.today() + timedelta(days=30)
    app.updated_at = datetime.now(timezone.utc)
    _decision_row(db, app, "response_window_opened", old_stage, app.stage, payload={"correction_due": str(app.correction_due), "evaluation_mode": app.evaluation_mode})
    _audit(db, "accreditation_response_30_day_open", "accreditation_application", app.id, {"correction_due": str(app.correction_due), "evaluation_mode": app.evaluation_mode})
    _commit(db)
    return model_dict(app)



def _require_medek(db: Session, app: m.AccreditationApplication) -> m.QualityFrameworkProfile:
    fw = db.get(m.QualityFrameworkProfile, app.framework_profile_id)
    if not fw or fw.framework_family != "MEDEK":
        raise HTTPException(409, "Bu işlem yalnız MEDEK başvurularında kullanılabilir")
    return fw

@router.get("/api/compliance/applications/{application_id}/medek-pdr-center")
def medek_pdr_center(application_id: int, db: Session = Depends(get_db)):
    app = _obj(db, m.AccreditationApplication, application_id, "Akreditasyon başvurusu bulunamadı"); _program(db, app.program_id, write=False)
    fw = _require_medek(db, app)
    items = list(db.scalars(select(m.MedekEvaluatorReportItem).where(m.MedekEvaluatorReportItem.application_id == app.id).order_by(m.MedekEvaluatorReportItem.id)).all())
    workspaces = list(db.scalars(select(m.EvaluatorWorkspace).where(m.EvaluatorWorkspace.application_id == app.id).order_by(m.EvaluatorWorkspace.id)).all())
    previous = db.get(m.AccreditationApplication, app.previous_application_id) if app.previous_application_id else None
    carried = [x for x in items if x.carried_forward]
    phases = {phase:[model_dict(x) for x in items if x.report_phase==phase] for phase in ["individual","pre_consensus","site_draft","final"]}
    confirmed_final = [x for x in items if x.report_phase=="final" and x.status=="confirmed"]
    improvements = [x for x in confirmed_final if x.item_type=="improvement_area"]
    strengths = [x for x in confirmed_final if x.item_type=="strength"]
    questions = [x for x in items if x.item_type=="site_question" and x.status=="confirmed"]
    return {
        "application": model_dict(app), "framework": model_dict(fw), "previous_application": model_dict(previous) if previous else None,
        "workspaces": [model_dict(x) for x in workspaces], "phases": phases,
        "interim_scope": [model_dict(x) for x in carried] if app.application_type in {"interim","monitoring"} else [],
        "summary": {"items":len(items),"final_confirmed":len(confirmed_final),"improvement_areas":len(improvements),"strengths":len(strengths),"site_questions":len(questions),"response_7_day_open":app.stage=="response_7_day"},
        "official_process_note":"2026 PDR: bireysel ön rapor → saha öncesi uzlaşım → saha taslağı → +7 gün kurum yanıtı sonrası nihai rapor",
    }

@router.post("/api/compliance/medek-pdr-items", status_code=201)
def medek_pdr_item_create(body: MedekEvaluatorReportItemCreate, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,body.application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id); _require_medek(db,app)
    if body.workspace_id is not None:
        ws=_obj(db,m.EvaluatorWorkspace,body.workspace_id,"Değerlendirici çalışma alanı bulunamadı")
        if ws.application_id != app.id: raise HTTPException(422,"Değerlendirici çalışma alanı bu başvuruya ait değil")
    obj=m.MedekEvaluatorReportItem(**body.model_dump()); db.add(obj); db.flush(); _audit(db,"medek_pdr_item_create","medek_pdr_item",obj.id,body.model_dump()); _commit(db); return model_dict(obj)

@router.patch("/api/compliance/medek-pdr-items/{item_id}")
def medek_pdr_item_update(item_id: int, body: MedekEvaluatorReportItemUpdate, db: Session = Depends(get_db)):
    obj=_obj(db,m.MedekEvaluatorReportItem,item_id,"MEDEK PDR maddesi bulunamadı"); app=_obj(db,m.AccreditationApplication,obj.application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id); _require_medek(db,app)
    data=body.model_dump(exclude_unset=True)
    for k,v in data.items(): setattr(obj,k,v)
    obj.updated_at=datetime.now(timezone.utc); _audit(db,"medek_pdr_item_update","medek_pdr_item",obj.id,data); _commit(db); return model_dict(obj)

@router.post("/api/compliance/applications/{application_id}/open-medek-7-day-response")
def open_medek_7_day_response(application_id: int, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id); _require_medek(db,app)
    expected="correction" if app.evaluation_mode=="report_only" else "site_visit"
    if app.stage != expected: raise HTTPException(409,f"MEDEK +7 gün yanıt penceresi {expected} aşamasından açılabilir")
    old=app.stage; app.stage="response_7_day"; app.correction_due=date.today()+timedelta(days=7); app.updated_at=datetime.now(timezone.utc)
    _decision_row(db,app,"medek_response_7_day_opened",old,app.stage,payload={"correction_due":str(app.correction_due)})
    _audit(db,"medek_response_7_day_open","accreditation_application",app.id,{"correction_due":str(app.correction_due)}); _commit(db); return model_dict(app)

@router.get("/api/compliance/applications/{application_id}/medek-response-package")
def medek_response_package(application_id: int, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id,write=False); _require_medek(db,app)
    items=list(db.scalars(select(m.MedekEvaluatorReportItem).where(m.MedekEvaluatorReportItem.application_id==app.id).order_by(m.MedekEvaluatorReportItem.id)).all())
    improvements=[model_dict(x) for x in items if x.report_phase in {"site_draft","final"} and x.item_type=="improvement_area"]
    requests=list(db.scalars(select(m.AccreditationDocumentRequest).where(m.AccreditationDocumentRequest.application_id==app.id).order_by(m.AccreditationDocumentRequest.id)).all())
    return {"application":model_dict(app),"due_date":app.correction_due,"improvement_areas":improvements,"document_requests":[_request_sla_payload(x) for x in requests],"submission_ready":app.stage=="response_7_day" and all((x.get("narrative") or "").strip() for x in improvements)}

@router.get("/api/compliance/applications/{application_id}/medek-pdr-forms")
def medek_pdr_forms(application_id: int, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id,write=False); _require_medek(db,app)
    rows=list(db.scalars(select(m.MedekPdrFormAnalysis).where(m.MedekPdrFormAnalysis.application_id==app.id).order_by(m.MedekPdrFormAnalysis.form_code,m.MedekPdrFormAnalysis.subject_ref)).all())
    by={code:[model_dict(x) for x in rows if x.form_code==code] for code in ["FORM1","FORM2","FORM3"]}
    confirmed=sum(1 for x in rows if x.status=="confirmed")
    return {"application":model_dict(app),"forms":by,"summary":{"total":len(rows),"confirmed":confirmed,"draft":len(rows)-confirmed},"official_note":"FORM1 Öğretim Planı Analizi · FORM2 Not Belgesi Analizi · FORM3 Program Değerlendirici Çizelgesi"}

@router.post("/api/compliance/medek-pdr-forms", status_code=201)
def medek_pdr_form_create(body: MedekPdrFormAnalysisCreate, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,body.application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id); _require_medek(db,app)
    existing=db.scalar(select(m.MedekPdrFormAnalysis).where(m.MedekPdrFormAnalysis.application_id==app.id,m.MedekPdrFormAnalysis.form_code==body.form_code,m.MedekPdrFormAnalysis.subject_ref==body.subject_ref))
    if existing: raise HTTPException(409,"Bu FORM/konu kaydı zaten mevcut")
    obj=m.MedekPdrFormAnalysis(**body.model_dump())
    if obj.status=="confirmed": obj.confirmed_at=datetime.now(timezone.utc)
    db.add(obj); db.flush(); _audit(db,"medek_pdr_form_create","medek_pdr_form_analysis",obj.id,body.model_dump()); _commit(db); return model_dict(obj)

@router.patch("/api/compliance/medek-pdr-forms/{form_id}")
def medek_pdr_form_update(form_id:int, body: MedekPdrFormAnalysisUpdate, db: Session = Depends(get_db)):
    obj=_obj(db,m.MedekPdrFormAnalysis,form_id,"MEDEK PDR form analizi bulunamadı"); app=_obj(db,m.AccreditationApplication,obj.application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id); _require_medek(db,app)
    data=body.model_dump(exclude_unset=True)
    for k,v in data.items(): setattr(obj,k,v)
    if data.get("status")=="confirmed": obj.confirmed_at=datetime.now(timezone.utc)
    obj.updated_at=datetime.now(timezone.utc); _audit(db,"medek_pdr_form_update","medek_pdr_form_analysis",obj.id,data); _commit(db); return model_dict(obj)

@router.get("/api/compliance/applications/{application_id}/medek-institution-report")
def medek_institution_report(application_id:int, db:Session=Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); program=_program(db,app.program_id,write=False); fw=_require_medek(db,app)
    pdr=list(db.scalars(select(m.MedekEvaluatorReportItem).where(m.MedekEvaluatorReportItem.application_id==app.id,m.MedekEvaluatorReportItem.report_phase=="final",m.MedekEvaluatorReportItem.status=="confirmed").order_by(m.MedekEvaluatorReportItem.criterion_code,m.MedekEvaluatorReportItem.id)).all())
    forms=list(db.scalars(select(m.MedekPdrFormAnalysis).where(m.MedekPdrFormAnalysis.application_id==app.id).order_by(m.MedekPdrFormAnalysis.form_code,m.MedekPdrFormAnalysis.subject_ref)).all())
    strengths=[model_dict(x) for x in pdr if x.item_type=="strength"]
    improvements=[model_dict(x) for x in pdr if x.item_type=="improvement_area"]
    assessments=[model_dict(x) for x in pdr if x.item_type=="assessment"]
    required_forms={"FORM1","FORM2","FORM3"}; confirmed={x.form_code for x in forms if x.status=="confirmed"}
    return {"application":model_dict(app),"program":model_dict(program),"framework":model_dict(fw),"strengths":strengths,"improvement_areas":improvements,"assessments":assessments,"forms":[model_dict(x) for x in forms],"team_consolidation_ready":bool(pdr) and required_forms.issubset(confirmed),"missing_required_forms":sorted(required_forms-confirmed),"official_note":"Takım başkanı, bireysel PDR'leri ve FORM1/FORM2/FORM3 analizlerini birleştirerek kurum raporu taslağını konsolide eder."}

@router.get("/api/compliance/applications/{application_id}/closure-matrix")
def accreditation_closure_matrix(application_id: int, db: Session = Depends(get_db)):
    app = _obj(db, m.AccreditationApplication, application_id, "Akreditasyon başvurusu bulunamadı")
    _program(db, app.program_id, write=False)
    findings = list(db.scalars(select(m.AccreditationFinding).where(m.AccreditationFinding.application_id == app.id).order_by(m.AccreditationFinding.id)).all())
    rows=[]
    for x in findings:
        evidence_count=len(x.evidence_refs or [])
        ready=x.status in {"resolved","closed"} and evidence_count>0 and bool((x.response_note or "").strip())
        rows.append({**model_dict(x), "evidence_count": evidence_count, "closure_ready": ready, "closure_gap": "" if ready else ("Kanıt eksik" if evidence_count==0 else "Yanıt/kapanış notu eksik" if not (x.response_note or "").strip() else "Bulgu henüz kapatılmadı")})
    return {"application": model_dict(app), "rows": rows, "summary": {"total": len(rows), "closure_ready": sum(1 for r in rows if r["closure_ready"]), "open": sum(1 for r in rows if r["status"] not in {"resolved","closed"})}}

@router.get("/api/compliance/applications/{application_id}/decision-history")
def accreditation_decision_history(application_id: int, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id,write=False)
    return [model_dict(x) for x in db.scalars(select(m.AccreditationDecisionHistory).where(m.AccreditationDecisionHistory.application_id==app.id).order_by(m.AccreditationDecisionHistory.id)).all()]

@router.post("/api/compliance/applications/{application_id}/decisions", status_code=201)
def accreditation_decision_create(application_id: int, body: AccreditationDecisionCreate, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id)
    row=_decision_row(db,app,body.action,app.stage,app.stage,body.decision_code,body.note,body.payload)
    _audit(db,"accreditation_decision_create","accreditation_decision_history",row.id,body.model_dump()); _commit(db); return model_dict(row)

@router.get("/api/compliance/applications/{application_id}/response-package")
def accreditation_response_package(application_id: int, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id,write=False)
    findings=list(db.scalars(select(m.AccreditationFinding).where(m.AccreditationFinding.application_id==app.id).order_by(m.AccreditationFinding.id)).all())
    requests=list(db.scalars(select(m.AccreditationDocumentRequest).where(m.AccreditationDocumentRequest.application_id==app.id).order_by(m.AccreditationDocumentRequest.id)).all())
    closure=accreditation_closure_matrix(application_id,db)
    return {"application":model_dict(app),"evaluation_mode":app.evaluation_mode,"due_date":app.correction_due,"findings":[model_dict(x) for x in findings],"document_requests":[_request_sla_payload(x) for x in requests],"closure_matrix":closure,"submission_ready": app.stage=="response_30_day" and closure["summary"]["open"]==0}

@router.get("/api/compliance/findings/{finding_id}/history")
def accreditation_finding_history(finding_id: int, db: Session = Depends(get_db)):
    obj=_obj(db,m.AccreditationFinding,finding_id,"Akreditasyon bulgusu bulunamadı")
    app=_obj(db,m.AccreditationApplication,obj.application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id,write=False)
    return [model_dict(x) for x in db.scalars(select(m.AccreditationFindingRevision).where(m.AccreditationFindingRevision.finding_id==finding_id).order_by(m.AccreditationFindingRevision.id)).all()]

@router.get("/api/compliance/applications/{application_id}/final-report")
def accreditation_final_report(application_id: int, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id,write=False)
    findings=list(db.scalars(select(m.AccreditationFinding).where(m.AccreditationFinding.application_id==app.id).order_by(m.AccreditationFinding.id)).all())
    report=db.scalar(select(m.AccreditationFinalReport).where(m.AccreditationFinalReport.application_id==app.id))
    if not report:
        report=m.AccreditationFinalReport(application_id=app.id,criterion_results=_criterion_result_rows(findings)); db.add(report); db.flush(); _commit(db)
    return {**model_dict(report),"application":model_dict(app),"criterion_results":_criterion_result_rows(findings),"closure":accreditation_closure_matrix(application_id,db)}

@router.patch("/api/compliance/applications/{application_id}/final-report")
def accreditation_final_report_update(application_id: int, body: AccreditationFinalReportUpdate, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id)
    if app.stage not in {"response_30_day","response_7_day","decision"}: raise HTTPException(409,"Nihai rapor yalnız kurum yanıtı veya karar aşamasında düzenlenebilir")
    findings=list(db.scalars(select(m.AccreditationFinding).where(m.AccreditationFinding.application_id==app.id).order_by(m.AccreditationFinding.id)).all())
    report=db.scalar(select(m.AccreditationFinalReport).where(m.AccreditationFinalReport.application_id==app.id)) or m.AccreditationFinalReport(application_id=app.id)
    if report.id is None: db.add(report); db.flush()
    for k,v in body.model_dump(exclude_unset=True).items(): setattr(report,k,v)
    report.criterion_results=_criterion_result_rows(findings); report.updated_at=datetime.now(timezone.utc)
    _audit(db,"accreditation_final_report_update","accreditation_final_report",report.id,body.model_dump(exclude_unset=True)); _commit(db); return model_dict(report)

@router.post("/api/compliance/applications/{application_id}/finalize-decision")
def accreditation_finalize_decision(application_id: int, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id)
    if app.stage != "decision": raise HTTPException(409,"Nihai karar yalnız karar aşamasında dondurulabilir")
    report=db.scalar(select(m.AccreditationFinalReport).where(m.AccreditationFinalReport.application_id==app.id))
    if not report or not (report.final_decision_code or "").strip(): raise HTTPException(409,"Nihai karar kodu girilmelidir")
    closure=accreditation_closure_matrix(application_id,db)
    if closure["summary"]["open"]>0: raise HTTPException(409,"Açık bulgular varken akreditasyon dönemi dondurulamaz")
    findings=list(db.scalars(select(m.AccreditationFinding).where(m.AccreditationFinding.application_id==app.id).order_by(m.AccreditationFinding.id)).all())
    revisions=list(db.scalars(select(m.AccreditationFindingRevision).where(m.AccreditationFindingRevision.application_id==app.id).order_by(m.AccreditationFindingRevision.id)).all())
    decisions=list(db.scalars(select(m.AccreditationDecisionHistory).where(m.AccreditationDecisionHistory.application_id==app.id).order_by(m.AccreditationDecisionHistory.id)).all())
    payload={"application":model_dict(app),"criterion_results":_criterion_result_rows(findings),"findings":[model_dict(x) for x in findings],"finding_revisions":[model_dict(x) for x in revisions],"decision_history":[model_dict(x) for x in decisions],"final_decision_code":report.final_decision_code,"accreditation_start":report.accreditation_start,"accreditation_end":report.accreditation_end}
    report.snapshot_payload=json.loads(json.dumps(payload,ensure_ascii=False,default=str)); report.snapshot_sha256=stable_sha256(report.snapshot_payload); report.status="frozen"; report.frozen_at=datetime.now(timezone.utc); report.updated_at=datetime.now(timezone.utc)
    old=app.stage; app.stage="closed"; app.status="closed"; app.decision_date=date.today(); app.updated_at=datetime.now(timezone.utc)
    _decision_row(db,app,"application_closed",old,"closed",report.final_decision_code,"Nihai değerlendirme raporu donduruldu",{"snapshot_sha256":report.snapshot_sha256})
    _audit(db,"accreditation_final_decision_freeze","accreditation_final_report",report.id,{"snapshot_sha256":report.snapshot_sha256}); _commit(db)
    return {"application":model_dict(app),"report":model_dict(report)}


@router.get("/api/compliance/applications/{application_id}/medek-final-readiness")
def medek_final_readiness(application_id: int, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id,write=False)
    return _medek_final_readiness_payload(db,app)


@router.post("/api/compliance/applications/{application_id}/medek-final-decision")
def medek_final_decision(application_id: int, decision_code: str, accreditation_start: date | None = None, team_opinion: str = "", institution_response_summary: str = "", db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id)
    readiness=_medek_final_readiness_payload(db,app)
    if not readiness["ready"]: raise HTTPException(409,"MEDEK nihai karar hazırlığı tamamlanmadı: "+"; ".join(readiness["gaps"]))
    if app.stage=="response_7_day":
        old=app.stage; app.stage="decision"; app.updated_at=datetime.now(timezone.utc)
        _decision_row(db,app,"response_submitted",old,"decision","MEDEK_7_DAY_RESPONSE_CLOSED","MEDEK +7 gün kurum yanıtı kapatıldı",{})
    if app.stage!="decision": raise HTTPException(409,"MEDEK nihai karar yalnız karar aşamasında kaydedilebilir")
    start=accreditation_start or date.today()
    profile=_medek_decision_profile(decision_code,start)
    report=db.scalar(select(m.AccreditationFinalReport).where(m.AccreditationFinalReport.application_id==app.id)) or m.AccreditationFinalReport(application_id=app.id)
    if report.id is None: db.add(report); db.flush()
    report.final_decision_code=decision_code
    report.team_opinion=team_opinion or report.team_opinion
    report.institution_response_summary=institution_response_summary or report.institution_response_summary
    report.accreditation_term_years=profile["term_years"]
    report.accreditation_start=start if profile["term_years"] else None
    report.accreditation_end=profile["accreditation_end"]
    report.next_review_type=profile["next_review_type"]
    report.next_review_due=profile["next_review_due"]
    report.decision_basis={
        "decision_label":profile["label"],
        "official_term_years":profile["term_years"],
        "assessment_rows":readiness["assessment_rows"],
        "eligible_decision_options":readiness["eligible_decision_options"],
        "forms_confirmed":readiness["confirmed_forms"],
        "human_authority":"MEK",
    }
    report.updated_at=datetime.now(timezone.utc)
    _decision_row(db,app,"decision_recorded","decision","decision",decision_code,f"MEDEK nihai karar taslağı kaydedildi: {profile['label']}",{"term_years":profile["term_years"],"next_review_type":profile["next_review_type"]})
    _audit(db,"medek_final_decision_recorded","accreditation_final_report",report.id,{"decision_code":decision_code}); _commit(db)
    return {"application":model_dict(app),"report":model_dict(report),"readiness":readiness,"decision_profile":profile}


@router.get("/api/compliance/applications/{application_id}/medek-institution-report.docx")
def medek_institution_report_docx(application_id: int, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id,write=False); _require_medek(db,app)
    try: payload,name,digest=build_medek_institution_report_docx(db,application_id)
    except ValueError as exc: raise HTTPException(409,str(exc))
    report=db.scalar(select(m.AccreditationFinalReport).where(m.AccreditationFinalReport.application_id==app.id))
    if report and report.status!="frozen": report.institution_report_sha256=digest; _commit(db)
    return Response(content=payload,media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",headers={"Content-Disposition":f'attachment; filename="{name}"',"X-Content-SHA256":digest})


@router.get("/api/compliance/applications/{application_id}/medek-institution-report.pdf")
def medek_institution_report_pdf(application_id: int, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id,write=False); _require_medek(db,app)
    try: payload,name,digest=build_medek_institution_report_pdf(db,application_id)
    except ValueError as exc: raise HTTPException(409,str(exc))
    return Response(content=payload,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{name}"',"X-Content-SHA256":digest})


@router.post("/api/compliance/applications/{application_id}/medek-finalize")
def medek_finalize(application_id: int, db: Session = Depends(get_db)):
    app=_obj(db,m.AccreditationApplication,application_id,"Akreditasyon başvurusu bulunamadı"); _program(db,app.program_id); _require_medek(db,app)
    readiness=_medek_final_readiness_payload(db,app)
    if not readiness["ready"]: raise HTTPException(409,"MEDEK karar freeze için hazırlık tamamlanmadı")
    if app.stage!="decision": raise HTTPException(409,"MEDEK nihai karar yalnız karar aşamasında dondurulabilir")
    report=db.scalar(select(m.AccreditationFinalReport).where(m.AccreditationFinalReport.application_id==app.id))
    if not report or report.final_decision_code not in {"full","conditional","short_term","reapply"}: raise HTTPException(409,"Geçerli MEDEK nihai karar kodu girilmelidir")
    closure=accreditation_closure_matrix(application_id,db)
    if closure["summary"]["open"]>0: raise HTTPException(409,"Açık bulgular varken MEDEK dönemi dondurulamaz")
    pdr=list(db.scalars(select(m.MedekEvaluatorReportItem).where(m.MedekEvaluatorReportItem.application_id==app.id).order_by(m.MedekEvaluatorReportItem.id)).all())
    forms=list(db.scalars(select(m.MedekPdrFormAnalysis).where(m.MedekPdrFormAnalysis.application_id==app.id).order_by(m.MedekPdrFormAnalysis.id)).all())
    findings=list(db.scalars(select(m.AccreditationFinding).where(m.AccreditationFinding.application_id==app.id).order_by(m.AccreditationFinding.id)).all())
    decisions=list(db.scalars(select(m.AccreditationDecisionHistory).where(m.AccreditationDecisionHistory.application_id==app.id).order_by(m.AccreditationDecisionHistory.id)).all())
    payload={
        "application":model_dict(app),"report":{k:v for k,v in model_dict(report).items() if k not in {"snapshot_payload"}},
        "pdr":[model_dict(x) for x in pdr],"forms":[model_dict(x) for x in forms],"findings":[model_dict(x) for x in findings],
        "decision_history":[model_dict(x) for x in decisions],"readiness":readiness,
    }
    report.snapshot_payload=json.loads(json.dumps(payload,ensure_ascii=False,default=str)); report.snapshot_sha256=stable_sha256(report.snapshot_payload); report.status="frozen"; report.frozen_at=datetime.now(timezone.utc); report.updated_at=datetime.now(timezone.utc)
    old=app.stage; app.stage="closed"; app.status="closed"; app.decision_date=date.today(); app.updated_at=datetime.now(timezone.utc)
    _decision_row(db,app,"application_closed",old,"closed",report.final_decision_code,"MEDEK nihai kurum raporu ve karar dönemi donduruldu",{"snapshot_sha256":report.snapshot_sha256,"term_years":report.accreditation_term_years,"next_review_type":report.next_review_type})
    _audit(db,"medek_final_decision_freeze","accreditation_final_report",report.id,{"snapshot_sha256":report.snapshot_sha256}); _commit(db)
    return {"application":model_dict(app),"report":model_dict(report),"readiness":readiness}


# ---------------------------------------------------------------------------
# Controlled documents: policy/directive/procedure/form + immutable revisions
# ---------------------------------------------------------------------------
@router.get("/api/compliance/documents")
def controlled_documents(program_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(m.ControlledDocument)
    if program_id is not None:
        _program(db, program_id, write=False)
        stmt = stmt.where(or_(m.ControlledDocument.program_id == program_id, m.ControlledDocument.program_id.is_(None)))
    else:
        require_roles("admin", "quality", "faculty_admin", "department_head", "program_head")
    rows = list(db.scalars(stmt.order_by(m.ControlledDocument.document_code)).all())
    out=[]
    for x in rows:
        d=model_dict(x)
        rev=db.scalar(select(m.ControlledDocumentRevision).where(m.ControlledDocumentRevision.document_id==x.id).order_by(m.ControlledDocumentRevision.revision_no.desc()))
        d["latest_revision"]=model_dict(rev) if rev else None
        out.append(d)
    return out


@router.post("/api/compliance/documents", status_code=201)
def controlled_document_create(body: ControlledDocumentCreate, db: Session = Depends(get_db)):
    if body.program_id is not None: _program(db, body.program_id)
    else: require_roles("admin", "quality")
    obj=m.ControlledDocument(**body.model_dump()); db.add(obj); db.flush(); _audit(db,"controlled_document_create","controlled_document",obj.id,body.model_dump()); _commit(db); return model_dict(obj)


def _finalize_revision(db: Session, doc: m.ControlledDocument, obj: m.ControlledDocumentRevision) -> m.ControlledDocumentRevision:
    if obj.status == "approved":
        prev=list(db.scalars(select(m.ControlledDocumentRevision).where(m.ControlledDocumentRevision.document_id==doc.id,m.ControlledDocumentRevision.id!=obj.id,m.ControlledDocumentRevision.status=="approved")).all())
        for x in prev: x.status="superseded"
        obj.approved_at=datetime.now(timezone.utc)
    return obj


def _controlled_revision_doc(db: Session, revision_id: int, *, write: bool = True) -> tuple[m.ControlledDocumentRevision, m.ControlledDocument]:
    rev=_obj(db,m.ControlledDocumentRevision,revision_id,"Kontrollü doküman revizyonu bulunamadı")
    doc=_obj(db,m.ControlledDocument,rev.document_id,"Kontrollü doküman bulunamadı")
    if doc.program_id is not None:_program(db,doc.program_id,write=write)
    elif write:require_roles("admin","quality")
    else:require_roles("admin","quality","faculty_admin","department_head","program_head")
    return rev,doc


def _verify_controlled_revision_integrity(db: Session, rev: m.ControlledDocumentRevision) -> None:
    if rev.stored_name:
        status,actual=verify_stored_file(_controlled_root()/rev.stored_name,rev.sha256)
    else:
        actual=hashlib.sha256((rev.content_text or "").encode("utf-8")).hexdigest()
        status="verified" if actual==rev.sha256 else "mismatch"
    previous=rev.integrity_status or "unchecked"
    rev.integrity_status=status;rev.integrity_checked_at=datetime.now(timezone.utc)
    if status!=previous or status!="verified":
        _audit(db,"controlled_document_integrity_check","controlled_document_revision",rev.id,{"status":status,"expected_sha256":rev.sha256,"actual_sha256":actual})
    _commit(db)
    if status=="missing":raise HTTPException(404,"Kontrollü doküman dosyasının fiziksel kopyası bulunamadı")
    if status!="verified":raise HTTPException(409,"Kontrollü doküman SHA-256 bütünlük kontrolünden geçemedi")


@router.post("/api/compliance/documents/{document_id}/revisions", status_code=201)
def controlled_revision_create(document_id: int, body: ControlledDocumentRevisionCreate, db: Session = Depends(get_db)):
    doc=_obj(db,m.ControlledDocument,document_id,"Kontrollü doküman bulunamadı")
    if doc.program_id is not None: _program(db,doc.program_id)
    else: require_roles("admin","quality")
    if body.status!="draft":
        raise HTTPException(409,"Yeni revizyon doğrudan onaylanamaz; önce taslak oluşturup maker-checker akışını tamamlayın")
    actor=current_user().get("email") or "system"
    data=body.model_dump();data["status"]="draft";data["approved_by"]="";data["prepared_by"]=actor
    content=(data.get("content_text") or "").encode("utf-8");data["sha256"]=hashlib.sha256(content).hexdigest();data["document_id"]=document_id
    data["integrity_status"]="verified";data["integrity_checked_at"]=datetime.now(timezone.utc)
    obj=m.ControlledDocumentRevision(**data);db.add(obj);db.flush();_audit(db,"controlled_document_revision_create","controlled_document_revision",obj.id,{"document_id":document_id,"revision_no":obj.revision_no,"sha256":obj.sha256,"status":obj.status,"prepared_by":actor});_commit(db);return model_dict(obj)


@router.post("/api/compliance/documents/{document_id}/revisions/upload", status_code=201)
async def controlled_revision_upload(document_id:int, revision_no:int=Form(...), status:str=Form("draft"), change_summary:str=Form(""), approved_by:str=Form(""), file:UploadFile=File(...), db:Session=Depends(get_db)):
    doc=_obj(db,m.ControlledDocument,document_id,"Kontrollü doküman bulunamadı")
    if doc.program_id is not None: _program(db,doc.program_id)
    else: require_roles("admin","quality")
    if revision_no < 1: raise HTTPException(422,"Geçersiz revizyon bilgisi")
    if status!="draft": raise HTTPException(409,"Dosyalı revizyon doğrudan onaylanamaz; maker-checker akışını kullanın")
    payload=await read_upload_limited(file)
    original=_safe_filename(file.filename or "controlled-document.bin")
    canonical_mime=validate_document_upload(original,payload,purpose="Kontrollü doküman")
    stored=f"d{document_id}_r{revision_no}_{uuid.uuid4().hex}{Path(original).suffix[:16]}";path=_controlled_root()/stored;path.write_bytes(payload)
    actor=current_user().get("email") or "system"
    obj=m.ControlledDocumentRevision(document_id=document_id,revision_no=revision_no,status="draft",change_summary=change_summary,content_text="",original_name=original,stored_name=stored,mime_type=canonical_mime,sha256=hashlib.sha256(payload).hexdigest(),integrity_status="verified",integrity_checked_at=datetime.now(timezone.utc),prepared_by=actor,approved_by="")
    try:
        db.add(obj);db.flush();_audit(db,"controlled_document_binary_revision_upload","controlled_document_revision",obj.id,{"sha256":obj.sha256,"original_name":original,"prepared_by":actor});_commit(db)
    except Exception:
        path.unlink(missing_ok=True); raise
    return model_dict(obj)


@router.get("/api/compliance/documents/{document_id}/revisions")
def controlled_revisions(document_id:int, db:Session=Depends(get_db)):
    doc=_obj(db,m.ControlledDocument,document_id,"Kontrollü doküman bulunamadı")
    if doc.program_id is not None:_program(db,doc.program_id,write=False)
    else:require_roles("admin","quality","faculty_admin","department_head","program_head")
    return [model_dict(x) for x in db.scalars(select(m.ControlledDocumentRevision).where(m.ControlledDocumentRevision.document_id==document_id).order_by(m.ControlledDocumentRevision.revision_no.desc())).all()]


@router.get("/api/compliance/document-revisions/{revision_id}/download")
def controlled_revision_download(revision_id:int,db:Session=Depends(get_db)):
    rev,_doc=_controlled_revision_doc(db,revision_id,write=False)
    if not rev.stored_name: raise HTTPException(409,"Bu revizyon yalnız metin içeriğidir; indirilebilir ikili dosya yok")
    _verify_controlled_revision_integrity(db,rev)
    return FileResponse(_controlled_root()/rev.stored_name,media_type=rev.mime_type,filename=rev.original_name)


@router.post("/api/compliance/document-revisions/{revision_id}/submit")
def controlled_revision_submit(revision_id:int,db:Session=Depends(get_db)):
    rev,_doc=_controlled_revision_doc(db,revision_id,write=True)
    if rev.status!="draft": raise HTTPException(409,"Yalnız taslak revizyon incelemeye gönderilebilir")
    _verify_controlled_revision_integrity(db,rev)
    rev.status="submitted";rev.submitted_at=datetime.now(timezone.utc)
    _audit(db,"controlled_document_revision_submit","controlled_document_revision",rev.id,{"prepared_by":rev.prepared_by});_commit(db);return model_dict(rev)


@router.post("/api/compliance/document-revisions/{revision_id}/review")
def controlled_revision_review(revision_id:int,db:Session=Depends(get_db)):
    require_roles("admin","quality")
    rev,_doc=_controlled_revision_doc(db,revision_id,write=True)
    if rev.status!="submitted": raise HTTPException(409,"Yalnız incelemeye gönderilmiş revizyon kontrol edilebilir")
    actor=current_user().get("email") or "system"
    if actor.lower()==(rev.prepared_by or "").lower(): raise HTTPException(409,"Hazırlayan kullanıcı aynı revizyonun kontrolünü yapamaz")
    _verify_controlled_revision_integrity(db,rev)
    rev.status="reviewed";rev.reviewed_by=actor;rev.reviewed_at=datetime.now(timezone.utc)
    _audit(db,"controlled_document_revision_review","controlled_document_revision",rev.id,{"reviewed_by":actor});_commit(db);return model_dict(rev)


@router.post("/api/compliance/document-revisions/{revision_id}/approve")
def controlled_revision_approve(revision_id:int,db:Session=Depends(get_db)):
    require_roles("admin","quality")
    rev,doc=_controlled_revision_doc(db,revision_id,write=True)
    if rev.status!="reviewed": raise HTTPException(409,"Revizyon onaydan önce kontrol edilmiş olmalıdır")
    actor=current_user().get("email") or "system"
    if actor.lower()==(rev.prepared_by or "").lower(): raise HTTPException(409,"Hazırlayan kullanıcı aynı revizyonu onaylayamaz")
    _verify_controlled_revision_integrity(db,rev)
    rev.status="approved";rev.approved_by=actor;rev.approved_at=datetime.now(timezone.utc);_finalize_revision(db,doc,rev)
    _audit(db,"controlled_document_revision_approve","controlled_document_revision",rev.id,{"approved_by":actor,"reviewed_by":rev.reviewed_by});_commit(db);return model_dict(rev)


# ---------------------------------------------------------------------------
# Budget/resources
# ---------------------------------------------------------------------------
@router.get("/api/compliance/programs/{program_id}/budget")
def budget(program_id:int, academic_year:str, db:Session=Depends(get_db)):
    _program(db,program_id,write=False); plan=db.scalar(select(m.QualityBudgetPlan).where(m.QualityBudgetPlan.program_id==program_id,m.QualityBudgetPlan.academic_year==academic_year))
    if not plan:return {"program_id":program_id,"academic_year":academic_year,"plan":None,"lines":[],"variance":0}
    lines=list(db.scalars(select(m.QualityBudgetLine).where(m.QualityBudgetLine.budget_plan_id==plan.id).order_by(m.QualityBudgetLine.id)).all())
    return {"plan":model_dict(plan),"lines":[model_dict(x) for x in lines],"variance":round(plan.allocated_amount-plan.spent_amount,2),"planned_lines":round(sum(x.planned_amount for x in lines),2),"actual_lines":round(sum(x.actual_amount for x in lines),2)}


@router.post("/api/compliance/budget-plans",status_code=201)
def budget_plan_create(body:BudgetPlanCreate,db:Session=Depends(get_db)):
    _program(db,body.program_id);obj=m.QualityBudgetPlan(**body.model_dump());db.add(obj);db.flush();_audit(db,"budget_plan_create","quality_budget_plan",obj.id,body.model_dump());_commit(db);return model_dict(obj)


@router.post("/api/compliance/budget-lines",status_code=201)
def budget_line_create(body:BudgetLineCreate,db:Session=Depends(get_db)):
    plan=_obj(db,m.QualityBudgetPlan,body.budget_plan_id,"Bütçe planı bulunamadı");_program(db,plan.program_id);obj=m.QualityBudgetLine(**body.model_dump());db.add(obj);db.flush();plan.spent_amount=float(db.scalar(select(func.coalesce(func.sum(m.QualityBudgetLine.actual_amount),0)).where(m.QualityBudgetLine.budget_plan_id==plan.id)) or 0);_audit(db,"budget_line_create","quality_budget_line",obj.id,body.model_dump());_commit(db);return model_dict(obj)


# ---------------------------------------------------------------------------
# Faculty CV / workload
# ---------------------------------------------------------------------------
@router.post("/api/compliance/faculty-cv",status_code=201)
def faculty_cv_create(body:FacultyCVRevisionCreate,db:Session=Depends(get_db)):
    faculty=_obj(db,m.FacultyRecord,body.faculty_record_id,"Öğretim elemanı kaydı bulunamadı");_program(db,faculty.program_id);data=body.model_dump();data["content_sha256"]=stable_sha256(data["cv_data"]);obj=m.FacultyCVRevision(**data);db.add(obj);db.flush();_audit(db,"faculty_cv_revision_create","faculty_cv_revision",obj.id,{"faculty_record_id":faculty.id,"version_no":obj.version_no,"sha256":obj.content_sha256});_commit(db);return model_dict(obj)


@router.get("/api/compliance/faculty/{faculty_record_id}/cv")
def faculty_cv_list(faculty_record_id:int,db:Session=Depends(get_db)):
    faculty=_obj(db,m.FacultyRecord,faculty_record_id,"Öğretim elemanı kaydı bulunamadı");_program(db,faculty.program_id,write=False);return [model_dict(x) for x in db.scalars(select(m.FacultyCVRevision).where(m.FacultyCVRevision.faculty_record_id==faculty_record_id).order_by(m.FacultyCVRevision.version_no.desc())).all()]


@router.post("/api/compliance/faculty-workload",status_code=201)
def faculty_workload_create(body:FacultyWorkloadCreate,db:Session=Depends(get_db)):
    faculty=_obj(db,m.FacultyRecord,body.faculty_record_id,"Öğretim elemanı kaydı bulunamadı");_program(db,faculty.program_id);obj=m.FacultyWorkloadRecord(**body.model_dump());db.add(obj);db.flush();_audit(db,"faculty_workload_create","faculty_workload",obj.id,body.model_dump());_commit(db);return model_dict(obj)


@router.get("/api/compliance/faculty/{faculty_record_id}/workload")
def faculty_workload(faculty_record_id:int,academic_year:str,term:str|None=None,db:Session=Depends(get_db)):
    faculty=_obj(db,m.FacultyRecord,faculty_record_id,"Öğretim elemanı kaydı bulunamadı");_program(db,faculty.program_id,write=False);stmt=select(m.FacultyWorkloadRecord).where(m.FacultyWorkloadRecord.faculty_record_id==faculty_record_id,m.FacultyWorkloadRecord.academic_year==academic_year);stmt=stmt.where(m.FacultyWorkloadRecord.term==term) if term else stmt; rows=list(db.scalars(stmt.order_by(m.FacultyWorkloadRecord.term,m.FacultyWorkloadRecord.course_code)).all());return {"faculty":model_dict(faculty),"academic_year":academic_year,"weekly_hours":round(sum(x.weekly_hours for x in rows),2),"rows":[model_dict(x) for x in rows]}


# ---------------------------------------------------------------------------
# Graduate longitudinal tracking / infrastructure maintenance
# ---------------------------------------------------------------------------
@router.post("/api/compliance/graduate-followups",status_code=201)
def graduate_followup_create(body:GraduateFollowupCreate,db:Session=Depends(get_db)):
    graduate=_obj(db,m.GraduateRecord,body.graduate_record_id,"Mezun kaydı bulunamadı");_program(db,graduate.program_id);obj=m.GraduateFollowup(**body.model_dump());db.add(obj);db.flush();_audit(db,"graduate_followup_create","graduate_followup",obj.id,body.model_dump());_commit(db);return model_dict(obj)


@router.get("/api/compliance/programs/{program_id}/graduate-followup-dashboard")
def graduate_followup_dashboard(program_id:int,db:Session=Depends(get_db)):
    _program(db,program_id,write=False);graduates=list(db.scalars(select(m.GraduateRecord).where(m.GraduateRecord.program_id==program_id)).all());gids=[x.id for x in graduates];followups=[] if not gids else list(db.scalars(select(m.GraduateFollowup).where(m.GraduateFollowup.graduate_record_id.in_(gids))).all());by_year={y:sum(1 for x in followups if x.followup_year==y) for y in (1,3,5)};den=len(graduates);return {"graduates":den,"followups":len(followups),"coverage":{"1_year":round(100*by_year[1]/den,1) if den else 0,"3_year":round(100*by_year[3]/den,1) if den else 0,"5_year":round(100*by_year[5]/den,1) if den else 0},"counts":by_year}


@router.post("/api/compliance/infrastructure-maintenance",status_code=201)
def infrastructure_maintenance_create(body:InfrastructureMaintenanceCreate,db:Session=Depends(get_db)):
    infra=_obj(db,m.InfrastructureRecord,body.infrastructure_id,"Altyapı kaydı bulunamadı");_program(db,infra.program_id);obj=m.InfrastructureMaintenance(**body.model_dump());db.add(obj);db.flush();_audit(db,"infrastructure_maintenance_create","infrastructure_maintenance",obj.id,body.model_dump());_commit(db);return model_dict(obj)


@router.get("/api/compliance/programs/{program_id}/infrastructure-maintenance")
def infrastructure_maintenance(program_id:int,db:Session=Depends(get_db)):
    _program(db,program_id,write=False);rows=list(db.scalars(select(m.InfrastructureMaintenance).join(m.InfrastructureRecord,m.InfrastructureRecord.id==m.InfrastructureMaintenance.infrastructure_id).where(m.InfrastructureRecord.program_id==program_id).order_by(m.InfrastructureMaintenance.planned_date,m.InfrastructureMaintenance.id)).all());return [model_dict(x) for x in rows]


# ---------------------------------------------------------------------------
# YÖKAK mission domains: R&D / societal contribution / internationalization
# ---------------------------------------------------------------------------
@router.post("/api/compliance/mission-activities",status_code=201)
def mission_activity_create(body:MissionActivityCreate,db:Session=Depends(get_db)):
    if body.program_id is not None:_program(db,body.program_id)
    else:require_roles("admin","quality","faculty_admin")
    obj=m.MissionActivity(**body.model_dump());db.add(obj);db.flush();_audit(db,"mission_activity_create","mission_activity",obj.id,body.model_dump());_commit(db);return model_dict(obj)


@router.get("/api/compliance/mission/{domain}")
def mission_dashboard(domain:str,academic_year:str,program_id:int|None=None,db:Session=Depends(get_db)):
    if domain not in {"research","social_contribution","internationalization"}:raise HTTPException(422,"Geçersiz misyon alanı")
    if program_id is not None:_program(db,program_id,write=False)
    else:require_roles("admin","quality","faculty_admin","department_head","program_head")
    return quality_domain_dashboard(db,academic_year,domain,program_id)


# ---------------------------------------------------------------------------
# Exports / readiness matrix
# ---------------------------------------------------------------------------
@router.get("/api/compliance/programs/{program_id}/matrix")
def matrix(program_id:int,academic_year:str,db:Session=Depends(get_db)):
    _program(db,program_id,write=False);return compliance_matrix(db,program_id,academic_year)


@router.get("/api/compliance/programs/{program_id}/matrix.docx")
def matrix_docx(program_id:int,academic_year:str,db:Session=Depends(get_db)):
    _program(db,program_id,write=False);payload,name=build_compliance_report_docx(db,program_id,academic_year);return Response(payload,media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",headers={"Content-Disposition":f'attachment; filename="{name}"'})


@router.get("/api/compliance/programs/{program_id}/evidence-room.zip")
def evidence_room(program_id:int,academic_year:str,room_type:str="BBO",application_id:int|None=None,framework_id:int|None=None,db:Session=Depends(get_db)):
    _program(db,program_id,write=False)
    if room_type.upper() not in {"BBO","FBO"}:raise HTTPException(422,"room_type BBO veya FBO olmalıdır")
    try:payload,name=build_evidence_room_zip(db,program_id,academic_year,room_type.upper(),application_id,framework_id)
    except ValueError as exc:raise HTTPException(409,str(exc)) from exc
    return Response(payload,media_type="application/zip",headers={"Content-Disposition":f'attachment; filename="{name}"'})


@router.get("/api/compliance/courses/{course_id}/course-file.docx")
def course_file(course_id:int,db:Session=Depends(get_db)):
    course=_obj(db,m.Course,course_id,"Ders bulunamadı");require_program_access(db,course.program_id,write=False,accreditation=True);payload,name=build_course_file_docx(db,course_id);return Response(payload,media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",headers={"Content-Disposition":f'attachment; filename="{name}"'})


@router.post("/api/compliance/seed-official-registry")
def seed_official_registry(db:Session=Depends(get_db)):
    require_roles("admin","quality");frameworks=seed_builtin_frameworks(db);templates=seed_report_templates(db);return {"frameworks":len(frameworks),"templates":len(templates),"status":"ready"}
