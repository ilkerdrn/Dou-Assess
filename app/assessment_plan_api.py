from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import get_db
from . import models as m
from .authz import current_user, require_program_access, require_roles
from .survey_api import _direct_program_outcomes, _indirect_program_outcomes, _weighted

router = APIRouter(prefix="/api", tags=["Program Assessment Assurance"])


def _actor() -> dict:
    try:
        return current_user()
    except Exception:
        return {"id": None, "email": "system", "role_names": []}


def _audit(db: Session, action: str, entity_type: str, entity_id: int | None, payload: dict) -> None:
    actor = _actor()
    db.add(m.AuditLog(actor_user_id=actor.get("id"), actor_email=actor.get("email") or "system",
                      actor_roles=list(actor.get("role_names") or []), action=action,
                      entity_type=entity_type, entity_id=entity_id, payload=payload))


def _commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


class PlanCreate(BaseModel):
    academic_year: str = Field(min_length=1, max_length=32)
    title: str = Field(default="Program Ölçme Güvence Planı", min_length=1, max_length=255)
    version_no: int = Field(default=1, ge=1)
    direct_weight: float = Field(default=70, ge=0, le=100)
    indirect_weight: float = Field(default=30, ge=0, le=100)
    owner: str = Field(default="", max_length=255)
    review_date: Optional[date] = None
    notes: str = Field(default="", max_length=6000)

    @model_validator(mode="after")
    def valid_weights(self):
        if self.direct_weight + self.indirect_weight <= 0:
            raise ValueError("Doğrudan ve dolaylı ağırlıkların toplamı sıfırdan büyük olmalıdır")
        return self


class PlanPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    direct_weight: Optional[float] = Field(default=None, ge=0, le=100)
    indirect_weight: Optional[float] = Field(default=None, ge=0, le=100)
    owner: Optional[str] = Field(default=None, max_length=255)
    review_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=6000)
    status: Optional[Literal["draft","active","reviewed","archived"]] = None


class PlanItemCreate(BaseModel):
    program_outcome_id: int
    channel: Literal["direct","indirect"]
    source_type: Literal["exam","assessment_measure","survey","manual"]
    source_entity_id: Optional[int] = None
    method_label: str = Field(min_length=1, max_length=255)
    owner: str = Field(default="", max_length=255)
    term: str = Field(default="", max_length=32)
    frequency: str = Field(default="annual", max_length=64)
    target_percent: float = Field(default=60, ge=0, le=100)
    due_date: Optional[date] = None
    evidence_required: str = Field(default="", max_length=4000)
    status: Literal["planned","in_progress","collected","reviewed","cancelled"] = "planned"


class PlanItemPatch(BaseModel):
    method_label: Optional[str] = Field(default=None, min_length=1, max_length=255)
    owner: Optional[str] = Field(default=None, max_length=255)
    term: Optional[str] = Field(default=None, max_length=32)
    frequency: Optional[str] = Field(default=None, max_length=64)
    target_percent: Optional[float] = Field(default=None, ge=0, le=100)
    due_date: Optional[date] = None
    evidence_required: Optional[str] = Field(default=None, max_length=4000)
    status: Optional[Literal["planned","in_progress","collected","reviewed","cancelled"]] = None


class ReviewCreate(BaseModel):
    decision: str = Field(default="", max_length=12000)
    final: bool = True


class PdcaCreate(BaseModel):
    criterion_code: str = Field(min_length=1, max_length=64)
    title: str = Field(default="", max_length=255)
    owner: str = Field(default="", max_length=255)
    due_date: Optional[date] = None


def _plan_out(db: Session, plan: m.AssessmentPlan, include_items: bool = True) -> dict:
    out = {
        "id": plan.id, "program_id": plan.program_id, "academic_year": plan.academic_year,
        "title": plan.title, "version_no": plan.version_no, "direct_weight": plan.direct_weight,
        "indirect_weight": plan.indirect_weight, "owner": plan.owner,
        "review_date": plan.review_date.isoformat() if plan.review_date else None,
        "notes": plan.notes, "status": plan.status,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }
    if include_items:
        rows = list(db.scalars(select(m.AssessmentPlanItem).where(m.AssessmentPlanItem.assessment_plan_id == plan.id).order_by(m.AssessmentPlanItem.program_outcome_id, m.AssessmentPlanItem.channel, m.AssessmentPlanItem.id)).all())
        pos = {x.id: x for x in db.scalars(select(m.ProgramOutcome).where(m.ProgramOutcome.id.in_([r.program_outcome_id for r in rows]))).all()} if rows else {}
        out["items"] = [{
            "id": r.id, "program_outcome_id": r.program_outcome_id,
            "program_outcome_code": pos.get(r.program_outcome_id).code if pos.get(r.program_outcome_id) else "",
            "channel": r.channel, "source_type": r.source_type, "source_entity_id": r.source_entity_id,
            "method_label": r.method_label, "owner": r.owner, "term": r.term, "frequency": r.frequency,
            "target_percent": r.target_percent, "due_date": r.due_date.isoformat() if r.due_date else None,
            "evidence_required": r.evidence_required, "status": r.status,
        } for r in rows]
    return out


def _validate_plan(db: Session, plan_id: int, *, write: bool) -> m.AssessmentPlan:
    plan = db.get(m.AssessmentPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Ölçme güvence planı bulunamadı")
    require_program_access(db, plan.program_id, write=write)
    return plan


def _ensure_plan_editable(plan: m.AssessmentPlan) -> None:
    if plan.status in {"reviewed", "archived"}:
        raise HTTPException(409, "Yıl sonu review ile dondurulmuş/arsivlenmiş ölçme planı değiştirilemez; yeni sürüm açılmalıdır")


def _validate_item_source(db: Session, plan: m.AssessmentPlan, data: PlanItemCreate) -> None:
    if data.source_type == "manual":
        if data.source_entity_id is not None:
            raise HTTPException(422, "Manual ölçme kaleminde source_entity_id kullanılmaz")
        return
    if data.source_entity_id is None:
        raise HTTPException(422, "Seçilen kaynak türü için source_entity_id zorunludur")
    if data.source_type in {"exam", "assessment_measure"} and data.channel != "direct":
        raise HTTPException(422, "Sınav ve assessment measure yalnız doğrudan ölçme kanalında kullanılabilir")
    if data.source_type == "survey" and data.channel != "indirect":
        raise HTTPException(422, "Anket yalnız dolaylı ölçme kanalında kullanılabilir")
    if data.source_type == "exam":
        source = db.get(m.Exam, data.source_entity_id)
        course = db.get(m.Course, source.course_id) if source else None
        if not source or not course or course.program_id != plan.program_id or course.academic_year != plan.academic_year:
            raise HTTPException(422, "Sınav kaynağı planın programı ve akademik yılıyla eşleşmelidir")
    elif data.source_type == "assessment_measure":
        source = db.get(m.AssessmentMeasure, data.source_entity_id)
        course = db.get(m.Course, source.course_id) if source else None
        if not source or not course or course.program_id != plan.program_id or course.academic_year != plan.academic_year:
            raise HTTPException(422, "Assessment measure kaynağı planın programı ve akademik yılıyla eşleşmelidir")
    elif data.source_type == "survey":
        source = db.get(m.SurveyTemplate, data.source_entity_id)
        if not source or source.program_id != plan.program_id:
            raise HTTPException(422, "Anket kaynağı planın programıyla eşleşmelidir")


@router.get("/programs/{program_id}/assessment-plans")
def list_plans(program_id: int, academic_year: str = "", db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=False)
    stmt = select(m.AssessmentPlan).where(m.AssessmentPlan.program_id == program_id)
    if academic_year:
        stmt = stmt.where(m.AssessmentPlan.academic_year == academic_year)
    rows = db.scalars(stmt.order_by(m.AssessmentPlan.academic_year.desc(), m.AssessmentPlan.version_no.desc(), m.AssessmentPlan.id.desc())).all()
    return [_plan_out(db, x) for x in rows]


@router.post("/programs/{program_id}/assessment-plans", status_code=201)
def create_plan(program_id: int, data: PlanCreate, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=True)
    if not db.get(m.Program, program_id):
        raise HTTPException(404, "Program bulunamadı")
    if db.scalar(select(m.AssessmentPlan).where(m.AssessmentPlan.program_id == program_id, m.AssessmentPlan.academic_year == data.academic_year, m.AssessmentPlan.version_no == data.version_no)):
        raise HTTPException(409, "Bu program/yıl/sürüm için ölçme güvence planı zaten var")
    obj = m.AssessmentPlan(program_id=program_id, created_by=_actor().get("email") or "system", **data.model_dump())
    db.add(obj); db.flush(); _audit(db, "assessment_plan_create", "assessment_plan", obj.id, {"program_id": program_id, "academic_year": data.academic_year}); _commit(db)
    return _plan_out(db, obj)


@router.patch("/assessment-plans/{plan_id}")
def patch_plan(plan_id: int, data: PlanPatch, db: Session = Depends(get_db)):
    obj = _validate_plan(db, plan_id, write=True)
    changes = data.model_dump(exclude_unset=True)
    if obj.status == "archived":
        raise HTTPException(409, "Arşivlenmiş ölçme planı değiştirilemez")
    if obj.status == "reviewed":
        if changes != {"status": "archived"}:
            raise HTTPException(409, "Yıl sonu review ile dondurulmuş ölçme planında yalnız arşivleme yapılabilir; içerik için yeni sürüm açılmalıdır")
    if changes.get("status") == "reviewed":
        raise HTTPException(422, "reviewed durumu yalnız final yıl sonu review ile verilir")
    dw = changes.get("direct_weight", obj.direct_weight); iw = changes.get("indirect_weight", obj.indirect_weight)
    if dw + iw <= 0:
        raise HTTPException(422, "Doğrudan ve dolaylı ağırlıkların toplamı sıfırdan büyük olmalıdır")
    for k, v in changes.items(): setattr(obj, k, v)
    _audit(db, "assessment_plan_update", "assessment_plan", obj.id, {k:(v.isoformat() if hasattr(v, "isoformat") else v) for k,v in changes.items()}); _commit(db)
    return _plan_out(db, obj)


@router.post("/assessment-plans/{plan_id}/items", status_code=201)
def add_plan_item(plan_id: int, data: PlanItemCreate, db: Session = Depends(get_db)):
    plan = _validate_plan(db, plan_id, write=True)
    _ensure_plan_editable(plan)
    po = db.get(m.ProgramOutcome, data.program_outcome_id)
    if not po or po.program_id != plan.program_id or po.academic_year != plan.academic_year:
        raise HTTPException(422, "Program Çıktısı planın programı ve akademik yılıyla eşleşmelidir")
    _validate_item_source(db, plan, data)
    dup = db.scalar(select(m.AssessmentPlanItem).where(
        m.AssessmentPlanItem.assessment_plan_id == plan.id,
        m.AssessmentPlanItem.program_outcome_id == data.program_outcome_id,
        m.AssessmentPlanItem.channel == data.channel,
        m.AssessmentPlanItem.source_type == data.source_type,
        m.AssessmentPlanItem.source_entity_id == data.source_entity_id,
        m.AssessmentPlanItem.method_label == data.method_label,
    ))
    if dup: raise HTTPException(409, "Aynı ölçme planı kalemi zaten var")
    obj = m.AssessmentPlanItem(assessment_plan_id=plan.id, **data.model_dump())
    db.add(obj); db.flush(); _audit(db, "assessment_plan_item_create", "assessment_plan_item", obj.id, {"plan_id": plan.id, "program_outcome_id": data.program_outcome_id}); _commit(db)
    return _plan_out(db, plan)


@router.patch("/assessment-plan-items/{item_id}")
def patch_plan_item(item_id: int, data: PlanItemPatch, db: Session = Depends(get_db)):
    obj = db.get(m.AssessmentPlanItem, item_id)
    if not obj:
        raise HTTPException(404, "Ölçme planı kalemi bulunamadı")
    plan = _validate_plan(db, obj.assessment_plan_id, write=True)
    _ensure_plan_editable(plan)
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(obj, key, value)
    _audit(db, "assessment_plan_item_update", "assessment_plan_item", obj.id, {k:(v.isoformat() if hasattr(v, "isoformat") else v) for k,v in changes.items()})
    _commit(db)
    return _plan_out(db, plan)


def _autobuild_items(db: Session, plan: m.AssessmentPlan) -> int:
    created = 0
    pos = list(db.scalars(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == plan.program_id, m.ProgramOutcome.academic_year == plan.academic_year)).all())
    po_ids = {x.id for x in pos}
    course_ids = list(db.scalars(select(m.Course.id).where(m.Course.program_id == plan.program_id, m.Course.academic_year == plan.academic_year)).all())

    # Direct generic measures through ÖÇ -> PÇ mapping.
    if course_ids:
        measures = list(db.scalars(select(m.AssessmentMeasure).where(m.AssessmentMeasure.course_id.in_(course_ids), m.AssessmentMeasure.directness == "direct", m.AssessmentMeasure.status != "archived")).all())
        for measure in measures:
            links = list(db.scalars(select(m.AssessmentMeasureOutcome).where(m.AssessmentMeasureOutcome.assessment_measure_id == measure.id)).all())
            target_po_ids = set()
            for link in links:
                target_po_ids.update(db.scalars(select(m.OutcomeMapping.program_outcome_id).where(m.OutcomeMapping.learning_outcome_id == link.learning_outcome_id)).all())
            for po_id in sorted(target_po_ids & po_ids):
                exists = db.scalar(select(m.AssessmentPlanItem).where(m.AssessmentPlanItem.assessment_plan_id == plan.id, m.AssessmentPlanItem.program_outcome_id == po_id, m.AssessmentPlanItem.channel == "direct", m.AssessmentPlanItem.source_type == "assessment_measure", m.AssessmentPlanItem.source_entity_id == measure.id))
                if not exists:
                    db.add(m.AssessmentPlanItem(assessment_plan_id=plan.id, program_outcome_id=po_id, channel="direct", source_type="assessment_measure", source_entity_id=measure.id, method_label=f"{measure.code} · {measure.title}", owner=measure.created_by, term="", frequency="term", target_percent=measure.target_percent, due_date=measure.due_date, evidence_required="Final öğrenci sonuçları + rubrik/ölçme kanıtı", status="planned")); created += 1

        exams = list(db.scalars(select(m.Exam).where(m.Exam.course_id.in_(course_ids))).all())
        for exam in exams:
            snaps = list(db.scalars(select(m.ExamProgramOutcome).where(m.ExamProgramOutcome.exam_id == exam.id)).all())
            for snap in snaps:
                po_id = snap.source_program_outcome_id
                if po_id not in po_ids: continue
                exists = db.scalar(select(m.AssessmentPlanItem).where(m.AssessmentPlanItem.assessment_plan_id == plan.id, m.AssessmentPlanItem.program_outcome_id == po_id, m.AssessmentPlanItem.channel == "direct", m.AssessmentPlanItem.source_type == "exam", m.AssessmentPlanItem.source_entity_id == exam.id))
                if not exists:
                    db.add(m.AssessmentPlanItem(assessment_plan_id=plan.id, program_outcome_id=po_id, channel="direct", source_type="exam", source_entity_id=exam.id, method_label=f"Sınav · {exam.title}", owner="", term="", frequency="term", target_percent=float(getattr(snap, "target_percent", 60) or 60), evidence_required="Onaylı sınav sonucu + soru/ÖÇ/PÇ analitiği", status="planned")); created += 1

    # Indirect survey templates with PÇ targets.
    surveys = list(db.scalars(select(m.SurveyTemplate).where(m.SurveyTemplate.program_id == plan.program_id, m.SurveyTemplate.status != "retired")).all())
    for survey in surveys:
        question_ids = list(db.scalars(select(m.SurveyQuestion.id).where(m.SurveyQuestion.survey_template_id == survey.id)).all())
        if not question_ids: continue
        target_po_ids = set(db.scalars(select(m.SurveyQuestionTarget.program_outcome_id).where(m.SurveyQuestionTarget.survey_question_id.in_(question_ids), m.SurveyQuestionTarget.target_type == "program_outcome", m.SurveyQuestionTarget.program_outcome_id.is_not(None))).all())
        for po_id in sorted(target_po_ids & po_ids):
            exists = db.scalar(select(m.AssessmentPlanItem).where(m.AssessmentPlanItem.assessment_plan_id == plan.id, m.AssessmentPlanItem.program_outcome_id == po_id, m.AssessmentPlanItem.channel == "indirect", m.AssessmentPlanItem.source_type == "survey", m.AssessmentPlanItem.source_entity_id == survey.id))
            if not exists:
                db.add(m.AssessmentPlanItem(assessment_plan_id=plan.id, program_outcome_id=po_id, channel="indirect", source_type="survey", source_entity_id=survey.id, method_label=f"{survey.code} · {survey.title}", owner=survey.created_by, term="", frequency="annual", target_percent=survey.target_percent, evidence_required="Kapanmış/uygulanmış anket kampanyası + PÇ eşleşmiş soru analitiği", status="planned")); created += 1
    return created


@router.post("/programs/{program_id}/assessment-plans/autobuild", status_code=201)
def autobuild_plan(program_id: int, data: PlanCreate, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=True)
    existing = db.scalar(select(m.AssessmentPlan).where(m.AssessmentPlan.program_id == program_id, m.AssessmentPlan.academic_year == data.academic_year, m.AssessmentPlan.version_no == data.version_no))
    if existing:
        plan = existing
        _ensure_plan_editable(plan)
    else:
        plan = m.AssessmentPlan(program_id=program_id, created_by=_actor().get("email") or "system", **data.model_dump())
        db.add(plan); db.flush()
    created = _autobuild_items(db, plan)
    if plan.status == "draft": plan.status = "active"
    _audit(db, "assessment_plan_autobuild", "assessment_plan", plan.id, {"created_items": created}); _commit(db)
    out = _plan_out(db, plan); out["autobuilt_item_count"] = created
    return out


def _dashboard(db: Session, plan: m.AssessmentPlan) -> dict:
    pos = list(db.scalars(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == plan.program_id, m.ProgramOutcome.academic_year == plan.academic_year).order_by(m.ProgramOutcome.code)).all())
    items = list(db.scalars(select(m.AssessmentPlanItem).where(m.AssessmentPlanItem.assessment_plan_id == plan.id, m.AssessmentPlanItem.status != "cancelled")).all())
    by_po: dict[int, list[m.AssessmentPlanItem]] = {}
    for item in items: by_po.setdefault(item.program_outcome_id, []).append(item)
    direct = _direct_program_outcomes(db, plan.program_id, plan.academic_year)
    indirect = _indirect_program_outcomes(db, plan.program_id, plan.academic_year)
    total_weight = plan.direct_weight + plan.indirect_weight
    dw, iw = plan.direct_weight / total_weight, plan.indirect_weight / total_weight
    rows = []
    for po in pos:
        po_items = by_po.get(po.id, [])
        direct_plans = [x for x in po_items if x.channel == "direct"]
        indirect_plans = [x for x in po_items if x.channel == "indirect"]
        allowed_exams = {x.source_entity_id for x in direct_plans if x.source_type == "exam" and x.source_entity_id is not None}
        allowed_measures = {x.source_entity_id for x in direct_plans if x.source_type == "assessment_measure" and x.source_entity_id is not None}
        direct_rows = [x for x in direct.get(po.id, []) if (x[2] == "exam" and x[3] in allowed_exams) or (x[2] == "measure" and x[3] in allowed_measures)]
        survey_template_ids = {x.source_entity_id for x in indirect_plans if x.source_type == "survey" and x.source_entity_id is not None}
        campaign_ids = set(db.scalars(select(m.SurveyCampaign.id).where(m.SurveyCampaign.survey_template_id.in_(survey_template_ids), m.SurveyCampaign.academic_year == plan.academic_year)).all()) if survey_template_ids else set()
        indirect_rows = [x for x in indirect.get(po.id, []) if x[2] in campaign_ids]
        d, i = _weighted(direct_rows), _weighted(indirect_rows)
        combined = (d * dw + i * iw) if d is not None and i is not None else None
        targets = [float(x.target_percent) for x in po_items] or [60.0]
        target = max(targets)
        planned_complete = bool(direct_plans and indirect_plans)
        evidence_complete = d is not None and i is not None
        if not po_items: state = "not_planned"
        elif not planned_complete: state = "plan_gap"
        elif not evidence_complete: state = "awaiting_evidence"
        elif combined is not None and combined >= target: state = "achieved"
        else: state = "below_target"
        rows.append({
            "program_outcome_id": po.id, "code": po.code, "description": po.description,
            "target_percent": round(target, 2), "planned_direct_count": len(direct_plans), "planned_indirect_count": len(indirect_plans),
            "direct_percent": round(d,2) if d is not None else None, "indirect_percent": round(i,2) if i is not None else None,
            "combined_percent": round(combined,2) if combined is not None else None, "status": state,
            "needs_pdca": state == "below_target",
            "methods": [{"id":x.id,"channel":x.channel,"source_type":x.source_type,"source_entity_id":x.source_entity_id,"method_label":x.method_label,"owner":x.owner,"term":x.term,"target_percent":x.target_percent,"status":x.status} for x in po_items],
        })
    n = len(rows)
    planned = sum(1 for x in rows if x["planned_direct_count"] and x["planned_indirect_count"])
    evidence = sum(1 for x in rows if x["direct_percent"] is not None and x["indirect_percent"] is not None)
    observed = [x for x in rows if x["combined_percent"] is not None]
    achieved = sum(1 for x in observed if x["combined_percent"] >= x["target_percent"])
    return {
        "plan": _plan_out(db, plan, include_items=False),
        "weights": {"direct": round(dw*100,2), "indirect": round(iw*100,2)},
        "summary": {
            "outcome_count": n,
            "plan_coverage_percent": round(planned/n*100,1) if n else 0,
            "evidence_completeness_percent": round(evidence/n*100,1) if n else 0,
            "target_attainment_percent": round(achieved/len(observed)*100,1) if observed else 0,
            "below_target_count": sum(1 for x in rows if x["status"] == "below_target"),
            "plan_gap_count": sum(1 for x in rows if x["status"] in {"not_planned","plan_gap"}),
        },
        "program_outcomes": rows,
    }


@router.get("/assessment-plans/{plan_id}/dashboard")
def plan_dashboard(plan_id: int, db: Session = Depends(get_db)):
    plan = _validate_plan(db, plan_id, write=False)
    return _dashboard(db, plan)


@router.get("/assessment-plans/{plan_id}/reviews")
def plan_reviews(plan_id: int, db: Session = Depends(get_db)):
    plan = _validate_plan(db, plan_id, write=False)
    rows = db.scalars(select(m.AssessmentPlanReview).where(m.AssessmentPlanReview.assessment_plan_id == plan.id).order_by(m.AssessmentPlanReview.review_no.desc())).all()
    return [{"id":x.id,"review_no":x.review_no,"status":x.status,"decision":x.decision,"snapshot":x.snapshot,"reviewed_by":x.reviewed_by,"reviewed_at":x.reviewed_at.isoformat()} for x in rows]


@router.post("/assessment-plans/{plan_id}/reviews", status_code=201)
def create_review(plan_id: int, data: ReviewCreate, db: Session = Depends(get_db)):
    plan = _validate_plan(db, plan_id, write=True)
    _ensure_plan_editable(plan)
    snapshot = _dashboard(db, plan)
    review_no = int(db.scalar(select(func.coalesce(func.max(m.AssessmentPlanReview.review_no), 0)).where(m.AssessmentPlanReview.assessment_plan_id == plan.id)) or 0) + 1
    obj = m.AssessmentPlanReview(assessment_plan_id=plan.id, review_no=review_no, status="final" if data.final else "draft", decision=data.decision, snapshot=snapshot, reviewed_by=_actor().get("email") or "system")
    db.add(obj); db.flush()
    if data.final: plan.status = "reviewed"
    _audit(db, "assessment_plan_review", "assessment_plan_review", obj.id, {"plan_id": plan.id, "review_no": review_no, "final": data.final}); _commit(db)
    return {"id":obj.id,"review_no":obj.review_no,"status":obj.status,"decision":obj.decision,"snapshot":obj.snapshot,"reviewed_by":obj.reviewed_by,"reviewed_at":obj.reviewed_at.isoformat()}


@router.post("/assessment-plans/{plan_id}/outcomes/{program_outcome_id}/quality-cycle", status_code=201)
def create_outcome_pdca(plan_id: int, program_outcome_id: int, data: PdcaCreate, db: Session = Depends(get_db)):
    require_roles("admin", "quality", "program_head")
    plan = _validate_plan(db, plan_id, write=True)
    dash = _dashboard(db, plan)
    row = next((x for x in dash["program_outcomes"] if x["program_outcome_id"] == program_outcome_id), None)
    if not row: raise HTTPException(404, "Program Çıktısı bulunamadı")
    if row["status"] != "below_target": raise HTTPException(409, "PUKÖ yalnız hedef altında kalan ve doğrudan+dolaylı kanıtı tamamlanmış çıktı için açılır")
    title = data.title.strip() or f"{row['code']} ölçme sonucu iyileştirme döngüsü"
    existing = db.scalar(select(m.QualityCycle).where(m.QualityCycle.program_id == plan.program_id, m.QualityCycle.academic_year == plan.academic_year, m.QualityCycle.title == title, m.QualityCycle.status != "closed"))
    if existing: raise HTTPException(409, "Bu çıktı için açık PUKÖ döngüsü zaten var")
    obj = m.QualityCycle(program_id=plan.program_id, academic_year=plan.academic_year, criterion_code=data.criterion_code.strip(), title=title,
        plan_text=f"{row['code']} için hedef %{row['target_percent']}; birleşik ölçüm %{row['combined_percent']} seviyesinde. Kök neden analizi ve iyileştirme planı oluşturulacaktır.",
        do_text="Planlanan akademik iyileştirme uygulanır.", check_text="Bir sonraki doğrudan ve dolaylı ölçüm çevriminde etkililik doğrulanır.",
        act_text="Hedefe ulaşıldıysa uygulama standardize edilir; ulaşılamadıysa yeni aksiyon döngüsü açılır.", owner=data.owner, due_date=data.due_date,
        status="planned", evidence_refs=[f"assessment_plan:{plan.id}", f"program_outcome:{program_outcome_id}", f"combined_percent:{row['combined_percent']}"])
    db.add(obj); db.flush(); _audit(db, "assessment_plan_pdca_create", "quality_cycle", obj.id, {"plan_id": plan.id, "program_outcome_id": program_outcome_id}); _commit(db)
    return {"id":obj.id,"program_id":obj.program_id,"academic_year":obj.academic_year,"criterion_code":obj.criterion_code,"title":obj.title,"owner":obj.owner,"due_date":obj.due_date.isoformat() if obj.due_date else None,"status":obj.status,"evidence_refs":obj.evidence_refs}
