from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from typing import Literal, Optional
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models as m
from .authz import current_user, require_program_access
from .db import get_db
from .services.analytics import exam_analytics

router = APIRouter(prefix="/api", tags=["Survey & Indirect Assessment"])

SURVEY_TYPES = {"student","graduate","employer","external_stakeholder","faculty","course_evaluation","program_evaluation"}
NUMERIC_TYPES = {"likert","nps"}


def _commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _actor() -> dict:
    try:
        return current_user()
    except Exception:
        return {"id": None, "email": "system", "role_names": []}


def _audit(db: Session, action: str, entity_type: str, entity_id: int | None, payload: dict) -> None:
    actor = _actor()
    db.add(m.AuditLog(
        actor_user_id=actor.get("id"), actor_email=actor.get("email") or "system",
        actor_roles=list(actor.get("role_names") or []), action=action,
        entity_type=entity_type, entity_id=entity_id, payload=payload,
    ))


class SurveyQuestionIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=4000)
    question_type: Literal["likert","single_choice","multi_choice","open_text","nps"] = "likert"
    required: bool = True
    order_no: int = Field(default=1, ge=1)
    scale_min: float = 1
    scale_max: float = 5
    options: list[str] = Field(default_factory=list)
    weight_percent: float = Field(default=100, ge=0, le=100)
    target_percent: Optional[float] = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_question(self):
        if self.question_type in NUMERIC_TYPES and self.scale_max <= self.scale_min:
            raise ValueError("Sayısal ölçek üst sınırı alt sınırdan büyük olmalıdır")
        if self.question_type in {"single_choice","multi_choice"} and len(self.options) < 2:
            raise ValueError("Seçimli sorularda en az iki seçenek olmalıdır")
        if self.question_type == "nps":
            self.scale_min, self.scale_max = 0, 10
        return self


class SurveyCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    survey_type: Literal["student","graduate","employer","external_stakeholder","faculty","course_evaluation","program_evaluation"]
    version_no: int = Field(default=1, ge=1)
    target_percent: float = Field(default=60, ge=0, le=100)
    anonymous: bool = True
    questions: list[SurveyQuestionIn] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_codes(self):
        codes = [q.code.strip().lower() for q in self.questions]
        if len(codes) != len(set(codes)):
            raise ValueError("Anket soru kodları benzersiz olmalıdır")
        return self


class SurveyTargetIn(BaseModel):
    target_type: Literal["program_outcome","pea","quality_criterion"]
    program_outcome_id: Optional[int] = None
    objective_id: Optional[int] = None
    framework_family: str = Field(default="", max_length=64)
    criterion_code: str = Field(default="", max_length=64)
    weight_percent: float = Field(default=100, ge=0, le=100)

    @model_validator(mode="after")
    def validate_target(self):
        if self.target_type == "program_outcome" and not self.program_outcome_id:
            raise ValueError("Program çıktısı hedefinde program_outcome_id gereklidir")
        if self.target_type == "pea" and not self.objective_id:
            raise ValueError("PEA hedefinde objective_id gereklidir")
        if self.target_type == "quality_criterion" and (not self.framework_family.strip() or not self.criterion_code.strip()):
            raise ValueError("Kalite ölçütünde framework_family ve criterion_code gereklidir")
        return self


class SurveyTargetsReplace(BaseModel):
    items: list[SurveyTargetIn] = Field(default_factory=list)


class CampaignCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    academic_year: str = Field(min_length=1, max_length=32)
    term: str = Field(default="", max_length=32)
    audience_type: str = Field(default="", max_length=64)
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def date_order(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("Kampanya bitiş tarihi başlangıç tarihinden önce olamaz")
        return self


class SurveyAnswerIn(BaseModel):
    question_id: int
    numeric_value: Optional[float] = None
    text_value: str = Field(default="", max_length=12000)
    selected_options: list[str] = Field(default_factory=list)


class PublicResponseIn(BaseModel):
    respondent_key: str = Field(default="", max_length=255)
    respondent_type: str = Field(default="", max_length=64)
    respondent_meta: dict = Field(default_factory=dict)
    answers: list[SurveyAnswerIn] = Field(min_length=1)



def _targets(db: Session, question_id: int) -> list[dict]:
    rows = db.scalars(select(m.SurveyQuestionTarget).where(m.SurveyQuestionTarget.survey_question_id == question_id).order_by(m.SurveyQuestionTarget.id)).all()
    out = []
    for x in rows:
        po = db.get(m.ProgramOutcome, x.program_outcome_id) if x.program_outcome_id else None
        pea = db.get(m.ProgramEducationalObjective, x.objective_id) if x.objective_id else None
        out.append({
            "id": x.id, "target_type": x.target_type,
            "program_outcome_id": x.program_outcome_id, "program_outcome_code": po.code if po else None,
            "objective_id": x.objective_id, "objective_code": pea.code if pea else None,
            "framework_family": x.framework_family, "criterion_code": x.criterion_code,
            "weight_percent": x.weight_percent,
        })
    return out


def _questions(db: Session, survey_id: int, *, include_targets: bool = True) -> list[dict]:
    rows = db.scalars(select(m.SurveyQuestion).where(m.SurveyQuestion.survey_template_id == survey_id).order_by(m.SurveyQuestion.order_no, m.SurveyQuestion.id)).all()
    return [{
        "id": q.id, "code": q.code, "prompt": q.prompt, "question_type": q.question_type,
        "required": q.required, "order_no": q.order_no, "scale_min": q.scale_min, "scale_max": q.scale_max,
        "options": q.options or [], "weight_percent": q.weight_percent, "target_percent": q.target_percent,
        **({"targets": _targets(db, q.id)} if include_targets else {}),
    } for q in rows]


def _survey_out(db: Session, row: m.SurveyTemplate) -> dict:
    campaign_count = db.scalar(select(func.count()).select_from(m.SurveyCampaign).where(m.SurveyCampaign.survey_template_id == row.id)) or 0
    return {
        "id": row.id, "program_id": row.program_id, "code": row.code, "title": row.title,
        "description": row.description, "survey_type": row.survey_type, "version_no": row.version_no,
        "target_percent": row.target_percent, "anonymous": row.anonymous, "status": row.status,
        "campaign_count": int(campaign_count), "questions": _questions(db, row.id),
    }


def _campaign_out(db: Session, c: m.SurveyCampaign, *, include_token: bool = True) -> dict:
    survey = db.get(m.SurveyTemplate, c.survey_template_id)
    response_count = db.scalar(select(func.count()).select_from(m.SurveyResponse).where(m.SurveyResponse.campaign_id == c.id)) or 0
    return {
        "id": c.id, "survey_template_id": c.survey_template_id, "survey_title": survey.title if survey else "",
        "code": c.code, "academic_year": c.academic_year, "term": c.term, "audience_type": c.audience_type,
        "start_date": c.start_date.isoformat() if c.start_date else None, "end_date": c.end_date.isoformat() if c.end_date else None,
        "status": c.status, "response_count": int(response_count),
        **({"public_token": c.public_token, "public_path": f"/api/public/surveys/{c.public_token}"} if include_token else {}),
    }


@router.get("/programs/{program_id}/survey-context")
def survey_context(program_id: int, academic_year: str = "", db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=False)
    po_stmt = select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == program_id)
    pea_stmt = select(m.ProgramEducationalObjective).where(m.ProgramEducationalObjective.program_id == program_id)
    if academic_year:
        po_stmt = po_stmt.where(m.ProgramOutcome.academic_year == academic_year)
        pea_stmt = pea_stmt.where(m.ProgramEducationalObjective.academic_year == academic_year)
    pos = list(db.scalars(po_stmt.order_by(m.ProgramOutcome.academic_year, m.ProgramOutcome.code)).all())
    peas = list(db.scalars(pea_stmt.order_by(m.ProgramEducationalObjective.academic_year, m.ProgramEducationalObjective.code)).all())
    return {
        "program_outcomes": [{"id":x.id,"academic_year":x.academic_year,"code":x.code,"description":x.description} for x in pos],
        "objectives": [{"id":x.id,"academic_year":x.academic_year,"code":x.code,"description":x.description} for x in peas],
        "survey_types": sorted(SURVEY_TYPES),
    }


@router.get("/programs/{program_id}/surveys")
def list_surveys(program_id: int, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=False)
    rows = db.scalars(select(m.SurveyTemplate).where(m.SurveyTemplate.program_id == program_id).order_by(m.SurveyTemplate.id.desc())).all()
    return [_survey_out(db, x) for x in rows]


@router.post("/programs/{program_id}/surveys", status_code=201)
def create_survey(program_id: int, data: SurveyCreate, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=True)
    if not db.get(m.Program, program_id): raise HTTPException(404, "Program bulunamadı")
    actor = _actor().get("email") or "system"
    obj = m.SurveyTemplate(program_id=program_id, code=data.code.strip(), title=data.title.strip(), description=data.description,
        survey_type=data.survey_type, version_no=data.version_no, target_percent=data.target_percent, anonymous=data.anonymous,
        status="draft", created_by=actor)
    db.add(obj); db.flush()
    for q in data.questions:
        db.add(m.SurveyQuestion(survey_template_id=obj.id, **q.model_dump()))
    _audit(db, "create", "survey_template", obj.id, {"program_id": program_id, "code": data.code, "survey_type": data.survey_type, "question_count": len(data.questions)})
    _commit(db)
    return _survey_out(db, obj)


@router.post("/surveys/{survey_id}/activate")
def activate_survey(survey_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.SurveyTemplate, survey_id)
    if not obj: raise HTTPException(404, "Anket şablonu bulunamadı")
    require_program_access(db, obj.program_id, write=True)
    if not db.scalar(select(func.count()).select_from(m.SurveyQuestion).where(m.SurveyQuestion.survey_template_id == obj.id)):
        raise HTTPException(400, "Sorusuz anket aktifleştirilemez")
    obj.status = "active"
    _audit(db, "activate", "survey_template", obj.id, {})
    _commit(db)
    return _survey_out(db, obj)


@router.put("/survey-questions/{question_id}/targets")
def replace_question_targets(question_id: int, data: SurveyTargetsReplace, db: Session = Depends(get_db)):
    q = db.get(m.SurveyQuestion, question_id)
    if not q: raise HTTPException(404, "Anket sorusu bulunamadı")
    survey = db.get(m.SurveyTemplate, q.survey_template_id)
    require_program_access(db, survey.program_id, write=True)
    seen: set[tuple] = set()
    for item in data.items:
        if item.target_type == "program_outcome":
            po = db.get(m.ProgramOutcome, item.program_outcome_id)
            if not po or po.program_id != survey.program_id: raise HTTPException(400, "Program çıktısı bu programa ait değil")
        elif item.target_type == "pea":
            pea = db.get(m.ProgramEducationalObjective, item.objective_id)
            if not pea or pea.program_id != survey.program_id: raise HTTPException(400, "PEA bu programa ait değil")
        key = (item.target_type, item.program_outcome_id or 0, item.objective_id or 0, item.framework_family.strip().upper(), item.criterion_code.strip().upper())
        if key in seen: raise HTTPException(400, "Aynı anket hedefi birden fazla kez bağlanamaz")
        seen.add(key)
    for old in db.scalars(select(m.SurveyQuestionTarget).where(m.SurveyQuestionTarget.survey_question_id == question_id)).all(): db.delete(old)
    for item in data.items:
        payload = item.model_dump(); payload["framework_family"] = payload["framework_family"].strip().upper(); payload["criterion_code"] = payload["criterion_code"].strip().upper()
        db.add(m.SurveyQuestionTarget(survey_question_id=question_id, **payload))
    _audit(db, "replace_targets", "survey_question", q.id, {"items": [x.model_dump() for x in data.items]})
    _commit(db)
    return {"question_id": q.id, "targets": _targets(db, q.id)}


@router.get("/surveys/{survey_id}/campaigns")
def list_campaigns(survey_id: int, db: Session = Depends(get_db)):
    survey = db.get(m.SurveyTemplate, survey_id)
    if not survey: raise HTTPException(404, "Anket şablonu bulunamadı")
    require_program_access(db, survey.program_id, write=False)
    rows = db.scalars(select(m.SurveyCampaign).where(m.SurveyCampaign.survey_template_id == survey_id).order_by(m.SurveyCampaign.id.desc())).all()
    return [_campaign_out(db, x) for x in rows]


@router.post("/surveys/{survey_id}/campaigns", status_code=201)
def create_campaign(survey_id: int, data: CampaignCreate, db: Session = Depends(get_db)):
    survey = db.get(m.SurveyTemplate, survey_id)
    if not survey: raise HTTPException(404, "Anket şablonu bulunamadı")
    require_program_access(db, survey.program_id, write=True)
    if survey.status != "active": raise HTTPException(400, "Yalnız aktif anket şablonundan kampanya açılabilir")
    actor = _actor().get("email") or "system"
    obj = m.SurveyCampaign(survey_template_id=survey_id, public_token=secrets.token_urlsafe(32), status="draft", created_by=actor, **data.model_dump())
    db.add(obj); db.flush(); _audit(db, "create", "survey_campaign", obj.id, data.model_dump(mode="json")); _commit(db)
    return _campaign_out(db, obj)


@router.post("/survey-campaigns/{campaign_id}/open")
def open_campaign(campaign_id: int, db: Session = Depends(get_db)):
    c = db.get(m.SurveyCampaign, campaign_id)
    if not c: raise HTTPException(404, "Anket kampanyası bulunamadı")
    survey = db.get(m.SurveyTemplate, c.survey_template_id); require_program_access(db, survey.program_id, write=True)
    c.status = "open"; _audit(db, "open", "survey_campaign", c.id, {}); _commit(db)
    return _campaign_out(db, c)


@router.post("/survey-campaigns/{campaign_id}/close")
def close_campaign(campaign_id: int, db: Session = Depends(get_db)):
    c = db.get(m.SurveyCampaign, campaign_id)
    if not c: raise HTTPException(404, "Anket kampanyası bulunamadı")
    survey = db.get(m.SurveyTemplate, c.survey_template_id); require_program_access(db, survey.program_id, write=True)
    c.status = "closed"; _audit(db, "close", "survey_campaign", c.id, {}); _commit(db)
    return _campaign_out(db, c)


def _campaign_public_payload(db: Session, c: m.SurveyCampaign) -> dict:
    survey = db.get(m.SurveyTemplate, c.survey_template_id)
    return {
        "campaign": {"code": c.code, "academic_year": c.academic_year, "term": c.term, "audience_type": c.audience_type, "status": c.status, "start_date": c.start_date.isoformat() if c.start_date else None, "end_date": c.end_date.isoformat() if c.end_date else None},
        "survey": {"code": survey.code, "title": survey.title, "description": survey.description, "survey_type": survey.survey_type, "anonymous": survey.anonymous, "target_percent": survey.target_percent},
        "questions": _questions(db, survey.id, include_targets=False),
    }


def _campaign_is_open(c: m.SurveyCampaign) -> bool:
    today = date.today()
    if c.status != "open": return False
    if c.start_date and today < c.start_date: return False
    if c.end_date and today > c.end_date: return False
    return True


@router.get("/public/surveys/{token}")
def public_survey(token: str, db: Session = Depends(get_db)):
    c = db.scalar(select(m.SurveyCampaign).where(m.SurveyCampaign.public_token == token))
    if not c or not _campaign_is_open(c): raise HTTPException(404, "Anket açık değil veya bağlantı geçersiz")
    return _campaign_public_payload(db, c)


@router.post("/public/surveys/{token}/responses", status_code=201)
def submit_public_survey(token: str, data: PublicResponseIn, db: Session = Depends(get_db)):
    c = db.scalar(select(m.SurveyCampaign).where(m.SurveyCampaign.public_token == token))
    if not c or not _campaign_is_open(c): raise HTTPException(404, "Anket açık değil veya bağlantı geçersiz")
    survey = db.get(m.SurveyTemplate, c.survey_template_id)
    questions = {q.id: q for q in db.scalars(select(m.SurveyQuestion).where(m.SurveyQuestion.survey_template_id == survey.id)).all()}
    answer_ids = [x.question_id for x in data.answers]
    if len(answer_ids) != len(set(answer_ids)): raise HTTPException(400, "Aynı soruya birden fazla yanıt gönderilemez")
    if any(qid not in questions for qid in answer_ids): raise HTTPException(400, "Yanıt içinde bu ankete ait olmayan soru var")
    missing = [q.code for q in questions.values() if q.required and q.id not in set(answer_ids)]
    if missing: raise HTTPException(400, f"Zorunlu sorular eksik: {', '.join(missing)}")
    respondent_hash = ""
    meta = {}
    if not survey.anonymous:
        if not data.respondent_key.strip(): raise HTTPException(400, "Bu ankette katılımcı anahtarı gereklidir")
        respondent_hash = sha256(data.respondent_key.strip().encode("utf-8")).hexdigest()
        if db.scalar(select(m.SurveyResponse).where(m.SurveyResponse.campaign_id == c.id, m.SurveyResponse.respondent_key_hash == respondent_hash)):
            raise HTTPException(409, "Bu katılımcı anketi daha önce yanıtladı")
        meta = {str(k)[:64]: str(v)[:255] for k, v in data.respondent_meta.items() if str(k).strip()}
    response = m.SurveyResponse(campaign_id=c.id, response_key=secrets.token_hex(16), respondent_key_hash=respondent_hash,
        respondent_type=(data.respondent_type or c.audience_type)[:64], respondent_meta=meta)
    db.add(response); db.flush()
    for ans in data.answers:
        q = questions[ans.question_id]
        numeric = ans.numeric_value
        selected = [str(x)[:255] for x in ans.selected_options]
        text = ans.text_value.strip()
        if q.question_type in NUMERIC_TYPES:
            if numeric is None: raise HTTPException(400, f"{q.code} sayısal yanıt gerektirir")
            if numeric < q.scale_min or numeric > q.scale_max: raise HTTPException(400, f"{q.code} ölçek dışında")
        elif q.question_type == "single_choice":
            if len(selected) != 1 or selected[0] not in (q.options or []): raise HTTPException(400, f"{q.code} için geçerli tek seçenek gerekir")
        elif q.question_type == "multi_choice":
            if not selected or any(x not in (q.options or []) for x in selected): raise HTTPException(400, f"{q.code} seçenekleri geçersiz")
        elif q.question_type == "open_text" and q.required and not text:
            raise HTTPException(400, f"{q.code} metin yanıtı gerektirir")
        db.add(m.SurveyAnswer(response_id=response.id, question_id=q.id, numeric_value=numeric, text_value=text, selected_options=selected))
    _commit(db)
    return {"response_key": response.response_key, "submitted": True, "anonymous": survey.anonymous}


def _question_stats(db: Session, campaign_id: int, survey: m.SurveyTemplate) -> list[dict]:
    questions = db.scalars(select(m.SurveyQuestion).where(m.SurveyQuestion.survey_template_id == survey.id).order_by(m.SurveyQuestion.order_no, m.SurveyQuestion.id)).all()
    response_ids = list(db.scalars(select(m.SurveyResponse.id).where(m.SurveyResponse.campaign_id == campaign_id)).all())
    out = []
    for q in questions:
        answers = db.scalars(select(m.SurveyAnswer).where(m.SurveyAnswer.question_id == q.id, m.SurveyAnswer.response_id.in_(response_ids))).all() if response_ids else []
        numeric = [float(a.numeric_value) for a in answers if a.numeric_value is not None]
        avg = sum(numeric)/len(numeric) if numeric else None
        normalized = (avg / float(q.scale_max) * 100.0) if avg is not None and q.scale_max else None
        target = float(q.target_percent if q.target_percent is not None else survey.target_percent)
        out.append({
            "question_id": q.id, "code": q.code, "prompt": q.prompt, "question_type": q.question_type,
            "answer_count": len(answers), "numeric_count": len(numeric), "average_value": round(avg,2) if avg is not None else None,
            "normalized_percent": round(normalized,2) if normalized is not None else None, "target_percent": target,
            "status": ("achieved" if normalized is not None and normalized >= target else "needs_improvement" if normalized is not None else "qualitative"),
            "targets": _targets(db, q.id),
        })
    return out


@router.get("/survey-campaigns/{campaign_id}/analytics")
def campaign_analytics(campaign_id: int, db: Session = Depends(get_db)):
    c = db.get(m.SurveyCampaign, campaign_id)
    if not c: raise HTTPException(404, "Anket kampanyası bulunamadı")
    survey = db.get(m.SurveyTemplate, c.survey_template_id); require_program_access(db, survey.program_id, write=False)
    stats = _question_stats(db, c.id, survey)
    numeric = [x["normalized_percent"] for x in stats if x["normalized_percent"] is not None]
    return {
        "campaign": _campaign_out(db, c), "survey": {"id": survey.id, "title": survey.title, "survey_type": survey.survey_type, "target_percent": survey.target_percent},
        "response_count": db.scalar(select(func.count()).select_from(m.SurveyResponse).where(m.SurveyResponse.campaign_id == c.id)) or 0,
        "question_stats": stats, "overall_percent": round(sum(numeric)/len(numeric),2) if numeric else None,
        "mapped_question_count": sum(1 for x in stats if x["targets"]),
    }


def _indirect_program_outcomes(db: Session, program_id: int, academic_year: str) -> dict[int, list[tuple[float,float,int]]]:
    surveys = list(db.scalars(select(m.SurveyTemplate).where(m.SurveyTemplate.program_id == program_id)).all())
    survey_ids = [x.id for x in surveys]
    if not survey_ids: return {}
    campaigns = list(db.scalars(select(m.SurveyCampaign).where(m.SurveyCampaign.survey_template_id.in_(survey_ids), m.SurveyCampaign.academic_year == academic_year, m.SurveyCampaign.status.in_(["open","closed","archived"]))).all())
    acc: dict[int, list[tuple[float,float,int]]] = {}
    survey_by_id = {x.id:x for x in surveys}
    for c in campaigns:
        survey = survey_by_id[c.survey_template_id]
        for row in _question_stats(db, c.id, survey):
            pct = row["normalized_percent"]
            if pct is None: continue
            for target in row["targets"]:
                if target["target_type"] == "program_outcome" and target["program_outcome_id"]:
                    acc.setdefault(target["program_outcome_id"], []).append((float(pct), float(target["weight_percent"] or 100), c.id))
    return acc


def _direct_program_outcomes(db: Session, program_id: int, academic_year: str) -> dict[int, list[tuple[float,float,str,int]]]:
    acc: dict[int, list[tuple[float,float,str,int]]] = {}
    courses = list(db.scalars(select(m.Course).where(m.Course.program_id == program_id, m.Course.academic_year == academic_year)).all())
    course_ids = [x.id for x in courses]
    if not course_ids: return acc
    # Existing approved/archived exam engine.
    exams = list(db.scalars(select(m.Exam).where(m.Exam.course_id.in_(course_ids), m.Exam.status.in_(["approved","archived"]))).all())
    for exam in exams:
        analysis = exam_analytics(db, exam.id)
        snaps = {x.code:x for x in db.scalars(select(m.ExamProgramOutcome).where(m.ExamProgramOutcome.exam_id == exam.id)).all()}
        for row in analysis.get("program_outcomes", []):
            snap = snaps.get(row["code"])
            po_id = snap.source_program_outcome_id if snap else None
            if po_id:
                acc.setdefault(po_id, []).append((float(row["attainment_percent"]), 1.0, "exam", exam.id))
    # Generic direct assessment measures (project, assignment, lab, internship, etc.).
    measures = list(db.scalars(select(m.AssessmentMeasure).where(m.AssessmentMeasure.course_id.in_(course_ids), m.AssessmentMeasure.directness == "direct", m.AssessmentMeasure.status.in_(["active","closed","archived"]))).all())
    for measure in measures:
        results = list(db.scalars(select(m.AssessmentMeasureResult).where(m.AssessmentMeasureResult.assessment_measure_id == measure.id, m.AssessmentMeasureResult.status == "final")).all())
        if not results or not measure.max_points: continue
        avg_pct = sum(float(x.raw_score)/float(measure.max_points)*100 for x in results)/len(results)
        links = list(db.scalars(select(m.AssessmentMeasureOutcome).where(m.AssessmentMeasureOutcome.assessment_measure_id == measure.id)).all())
        for link in links:
            maps = list(db.scalars(select(m.OutcomeMapping).where(m.OutcomeMapping.learning_outcome_id == link.learning_outcome_id)).all())
            for mp in maps:
                po = db.get(m.ProgramOutcome, mp.program_outcome_id)
                if po and po.program_id == program_id and po.academic_year == academic_year:
                    weight = max(0.0001, float(link.weight_percent or 100) * float(mp.contribution or 1))
                    acc.setdefault(po.id, []).append((float(avg_pct), weight, "measure", measure.id))
    return acc


def _weighted(rows):
    denom = sum(float(x[1]) for x in rows)
    return (sum(float(x[0])*float(x[1]) for x in rows)/denom) if denom else None


@router.get("/programs/{program_id}/indirect-assessment")
def indirect_assessment(program_id: int, academic_year: str, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=False)
    pos = list(db.scalars(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == program_id, m.ProgramOutcome.academic_year == academic_year).order_by(m.ProgramOutcome.code)).all())
    acc = _indirect_program_outcomes(db, program_id, academic_year)
    rows = []
    for po in pos:
        values = acc.get(po.id, [])
        score = _weighted(values)
        rows.append({"program_outcome_id": po.id, "code": po.code, "description": po.description, "indirect_percent": round(score,2) if score is not None else None, "survey_evidence_count": len({x[2] for x in values}), "measurement_count": len(values)})
    return {"program_id": program_id, "academic_year": academic_year, "program_outcomes": rows, "measured_outcome_count": sum(1 for x in rows if x["indirect_percent"] is not None)}


@router.get("/programs/{program_id}/outcome-evidence-mix")
def outcome_evidence_mix(program_id: int, academic_year: str, direct_weight: float = 70, indirect_weight: float = 30, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=False)
    if direct_weight < 0 or indirect_weight < 0 or direct_weight + indirect_weight <= 0: raise HTTPException(400, "Geçerli direct/indirect ağırlıkları gereklidir")
    total = direct_weight + indirect_weight; dw, iw = direct_weight/total, indirect_weight/total
    pos = list(db.scalars(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == program_id, m.ProgramOutcome.academic_year == academic_year).order_by(m.ProgramOutcome.code)).all())
    direct = _direct_program_outcomes(db, program_id, academic_year); indirect = _indirect_program_outcomes(db, program_id, academic_year)
    rows = []
    for po in pos:
        drows, irows = direct.get(po.id, []), indirect.get(po.id, [])
        d, i = _weighted(drows), _weighted(irows)
        combined = (d*dw + i*iw) if d is not None and i is not None else None
        state = "complete" if d is not None and i is not None else "direct_only" if d is not None else "indirect_only" if i is not None else "no_data"
        rows.append({
            "program_outcome_id": po.id, "code": po.code, "description": po.description,
            "direct_percent": round(d,2) if d is not None else None, "indirect_percent": round(i,2) if i is not None else None,
            "combined_percent": round(combined,2) if combined is not None else None, "evidence_status": state,
            "direct_source_count": len(drows), "indirect_measurement_count": len(irows),
        })
    return {"program_id": program_id, "academic_year": academic_year, "weights": {"direct": round(dw*100,2), "indirect": round(iw*100,2)}, "program_outcomes": rows, "complete_outcome_count": sum(1 for x in rows if x["evidence_status"] == "complete")}
