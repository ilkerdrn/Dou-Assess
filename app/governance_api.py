"""Institution settings, outcome-change approval (maker-checker) and the shared question pool."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models as m
from .authz import current_user, has_role, require_course_access, require_roles
from .config import settings
from .db import get_db
from .services.thresholds import active_threshold

router = APIRouter()

SETTING_KEYS = {
    "outcome_term": {"default": lambda: settings.outcome_term, "choices": {"Öğrenim", "Öğrenme", "Kazanım"}, "label": "ÖÇ terimi"},
    "outcome_change_approval": {"default": lambda: "off", "choices": {"on", "off"}, "label": "ÖÇ değişikliklerinde bölüm başkanı onayı"},
    "ai_scoring": {"default": lambda: "off", "choices": {"on", "off"}, "label": "Yapay zekâ puan önerisi (KVKK onayı sonrası)"},
    "question_self_approval": {"default": lambda: "on", "choices": {"on", "off"}, "label": "Soru yazarı kendi sorusunu onaylayabilir"},
}
REVIEWER_ROLES = ("admin", "program_head", "department_head", "faculty_admin")


def get_setting(db: Session, key: str) -> str:
    row = db.get(m.InstitutionSetting, key)
    return row.value if row and row.value != "" else SETTING_KEYS[key]["default"]()


def _audit(db: Session, action: str, entity_type: str, entity_id: int | None, payload: dict[str, Any]) -> None:
    u = current_user()
    db.add(m.AuditLog(actor_user_id=u.get("id"), actor_email=u.get("email") or "system", actor_roles=list(u.get("role_names") or []),
                      action=action, entity_type=entity_type, entity_id=entity_id, payload=json.loads(json.dumps(payload, default=str, ensure_ascii=False))))


# ------------------------------------------------------------------ settings
class SettingUpdate(BaseModel):
    value: str = Field(max_length=64)


@router.get("/api/institution-settings")
def list_settings(db: Session = Depends(get_db)):
    return [{"key": k, "label": v["label"], "value": get_setting(db, k), "choices": sorted(v["choices"]), "default": v["default"]()} for k, v in SETTING_KEYS.items()]


@router.put("/api/institution-settings/{key}")
def update_setting(key: str, body: SettingUpdate, db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    spec = SETTING_KEYS.get(key)
    if not spec: raise HTTPException(404, "Bilinmeyen ayar")
    if body.value not in spec["choices"]: raise HTTPException(400, f"Geçersiz değer. Seçenekler: {', '.join(sorted(spec['choices']))}")
    row = db.get(m.InstitutionSetting, key) or m.InstitutionSetting(key=key)
    old = row.value
    row.value = body.value; row.updated_by = current_user().get("email") or "system"; db.add(row)
    _audit(db, "institution_setting_update", "institution_setting", None, {"key": key, "from": old, "to": body.value}); db.commit()
    return {"key": key, "value": body.value}


# ------------------------------------------------------------------ learning-outcome cores (shared by direct edits and approvals)
def lo_out(x: m.LearningOutcome) -> dict:
    return {"id": x.id, "course_id": x.course_id, "code": x.code, "description": x.description, "target_percent": x.target_percent, "source": x.source, "is_active": x.is_active}


def lo_create_core(db: Session, course_id: int, payload: dict, explicit_target: bool) -> m.LearningOutcome:
    payload = dict(payload)
    if not explicit_target:
        course = db.get(m.Course, course_id)
        default = active_threshold(db, course.program_id, course.academic_year, "lo")
        if default is not None: payload["target_percent"] = default
    obj = m.LearningOutcome(course_id=course_id, source="assess", **payload); db.add(obj); db.flush()
    _audit(db, "create", "learning_outcome", obj.id, {"code": obj.code, "description": obj.description, "target_percent": obj.target_percent})
    return obj


def lo_update_core(db: Session, obj: m.LearningOutcome, changes: dict) -> m.LearningOutcome:
    before = {"code": obj.code, "description": obj.description, "target_percent": obj.target_percent}
    for k, v in changes.items(): setattr(obj, k, v)
    if obj.source == "obs" and any(before[k] != getattr(obj, k) for k in before):
        obj.source = "obs_modified"
    _audit(db, "update", "learning_outcome", obj.id, {"before": before, "after": {k: getattr(obj, k) for k in before}, "source": obj.source})
    return obj


def lo_delete_core(db: Session, obj: m.LearningOutcome) -> dict:
    bank = db.scalar(select(func.count()).select_from(m.QuestionBankOutcome).where(m.QuestionBankOutcome.learning_outcome_id == obj.id)) or 0
    snaps = db.scalar(select(func.count()).select_from(m.ExamLearningOutcome).where(m.ExamLearningOutcome.source_learning_outcome_id == obj.id)) or 0
    qlinks = db.scalar(select(func.count()).select_from(m.Question).join(m.ExamLearningOutcome, m.Question.exam_learning_outcome_id == m.ExamLearningOutcome.id).where(m.ExamLearningOutcome.source_learning_outcome_id == obj.id)) or 0
    if bank or snaps or qlinks:
        obj.is_active = False
        _audit(db, "deactivate", "learning_outcome", obj.id, {"code": obj.code, "bank_links": bank, "exam_snapshots": snaps})
        return {"deleted": False, "deactivated": True, "message": "ÖÇ bağlı soru/sınav içerdiği için silinmedi; pasife alındı."}
    _audit(db, "delete", "learning_outcome", obj.id, {"code": obj.code})
    db.delete(obj)
    return {"deleted": True}


def approval_gate(db: Session, course_id: int, action: str, payload: dict, lo: m.LearningOutcome | None = None) -> JSONResponse | None:
    """If the institution requires approval and the actor is not a reviewer, queue a request instead of changing the outcome."""
    if get_setting(db, "outcome_change_approval") != "on" or has_role(*REVIEWER_ROLES):
        return None
    before = {"code": lo.code, "description": lo.description, "target_percent": lo.target_percent} if lo else {}
    req = m.OutcomeChangeRequest(course_id=course_id, learning_outcome_id=lo.id if lo else None, action=action, payload=json.loads(json.dumps(payload, default=str)), before=before,
                                 requested_by=current_user().get("email") or "system")
    db.add(req); db.flush()
    _audit(db, "outcome_change_requested", "outcome_change_request", req.id, {"action": action, "course_id": course_id, "payload": payload}); db.commit()
    return JSONResponse(status_code=202, content={"pending_approval": True, "request_id": req.id, "message": "Değişiklik bölüm başkanı onayına gönderildi."})


# ------------------------------------------------------------------ approval queue
def _req_out(r: m.OutcomeChangeRequest) -> dict:
    return {"id": r.id, "course_id": r.course_id, "learning_outcome_id": r.learning_outcome_id, "action": r.action, "payload": r.payload, "before": r.before, "status": r.status,
            "requested_by": r.requested_by, "decided_by": r.decided_by, "decision_note": r.decision_note, "created_at": r.created_at.isoformat() if r.created_at else None}


@router.get("/api/outcome-change-requests")
def list_change_requests(status: str | None = None, course_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(m.OutcomeChangeRequest).order_by(m.OutcomeChangeRequest.id.desc()).limit(200)
    if status: stmt = stmt.where(m.OutcomeChangeRequest.status == status)
    if course_id:
        require_course_access(db, course_id, write=False); stmt = stmt.where(m.OutcomeChangeRequest.course_id == course_id)
    rows = db.scalars(stmt).all()
    out = []
    for r in rows:
        try: require_course_access(db, r.course_id, write=False)
        except HTTPException: continue
        out.append(_req_out(r))
    return out


class Decision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    note: str = Field(default="", max_length=2000)


@router.post("/api/outcome-change-requests/{request_id}/decision")
def decide_change_request(request_id: int, body: Decision, db: Session = Depends(get_db)):
    require_roles(*REVIEWER_ROLES)
    r = db.get(m.OutcomeChangeRequest, request_id)
    if not r: raise HTTPException(404, "Talep bulunamadı")
    require_course_access(db, r.course_id, write=True)
    if r.status != "pending": raise HTTPException(409, "Talep zaten sonuçlandırılmış")
    me = current_user().get("email") or "system"
    if r.requested_by == me and not has_role("admin"):
        raise HTTPException(403, "Kendi talebinizi onaylayamazsınız")
    if body.decision == "approved":
        if r.action == "create":
            lo_create_core(db, r.course_id, {k: r.payload[k] for k in ("code", "description", "target_percent") if k in r.payload}, "target_percent" in r.payload)
        else:
            lo = db.get(m.LearningOutcome, r.learning_outcome_id) if r.learning_outcome_id else None
            if not lo: raise HTTPException(409, "Talebe bağlı öğrenme çıktısı artık yok")
            if r.action == "update": lo_update_core(db, lo, r.payload)
            else: lo_delete_core(db, lo)
    r.status = body.decision; r.decided_by = me; r.decision_note = body.note.strip(); r.decided_at = datetime.now(timezone.utc)
    _audit(db, "outcome_change_decision", "outcome_change_request", r.id, {"decision": body.decision, "note": body.note}); db.commit()
    return _req_out(r)


# ------------------------------------------------------------------ question approval (maker-checker) and shared pool
def question_review_gate(db: Session, bank: m.QuestionBank, new_status: str) -> None:
    """When self-approval is switched off: the author cannot approve their own question, and only reviewers can make it institutional."""
    if new_status not in ("approved", "institutional"):
        return
    if new_status == "institutional" and get_setting(db, "question_self_approval") == "off" and not (has_role(*REVIEWER_ROLES) or has_role("quality")):
        raise HTTPException(403, "Kurumsal havuza yalnızca program başkanı, kalite veya yönetici alabilir")
    if get_setting(db, "question_self_approval") == "off":
        u = current_user()
        mine = {str(u.get("email") or "").lower(), str(u.get("display_name") or "").lower()} - {""}
        if (bank.author or "").lower() in mine:
            raise HTTPException(403, "Soru yazarı kendi sorusunu onaylayamaz; başka bir kontrolör gerekir")


@router.get("/api/question-bank/shared")
def shared_pool(course_id: int, q: str = "", limit: int = 50, db: Session = Depends(get_db)):
    """Institution-approved questions of other courses in the same program, ready to be copied into this course."""
    target = require_course_access(db, course_id, write=False)
    stmt = (select(m.QuestionBank, m.Course).join(m.Course, m.Course.id == m.QuestionBank.course_id)
            .where(m.Course.program_id == target.program_id, m.QuestionBank.course_id != course_id, m.QuestionBank.is_active.is_(True), m.QuestionBank.review_status == "institutional")
            .order_by(m.QuestionBank.id.desc()).limit(max(1, min(limit, 200))))
    if q.strip(): stmt = stmt.where(m.QuestionBank.text.ilike(f"%{q.strip()}%"))
    return [{"id": b.id, "course_code": c.code, "course_name": c.name, "question_type": b.question_type, "text": b.text, "topic": b.topic, "difficulty": b.difficulty,
             "bloom_level": b.bloom_level, "points": b.default_points, "usage_count": b.usage_count, "difficulty_index": b.difficulty_index} for b, c in db.execute(stmt).all()]


class CopyRequest(BaseModel):
    course_id: int


@router.post("/api/question-bank/{question_id}/copy-to-course", status_code=201)
def copy_shared_question(question_id: int, body: CopyRequest, db: Session = Depends(get_db)):
    src = db.get(m.QuestionBank, question_id)
    if not src or not src.is_active: raise HTTPException(404, "Soru bulunamadı")
    target = require_course_access(db, body.course_id, write=True)
    src_course = db.get(m.Course, src.course_id)
    if src.review_status != "institutional": raise HTTPException(409, "Yalnızca kurumsal havuzdaki sorular kopyalanabilir")
    if not src_course or src_course.program_id != target.program_id: raise HTTPException(403, "Soru yalnızca aynı programdaki derslere kopyalanabilir")
    if src.course_id == target.id: raise HTTPException(409, "Soru zaten bu dersin havuzunda")
    u = current_user()
    copy = m.QuestionBank(course_id=target.id, question_type=src.question_type, text=src.text, default_points=src.default_points, correct_answer=src.correct_answer, choices=src.choices,
                          tags=list(src.tags or []) + [f"kaynak:{src.id}"], topic=src.topic, unit=src.unit, difficulty=src.difficulty, bloom_level=src.bloom_level,
                          author=u.get("display_name") or u.get("email") or "", image_data=src.image_data, rubric=src.rubric, expected_answer=src.expected_answer,
                          answer_lines=src.answer_lines, review_status="draft")
    db.add(copy); db.flush()
    codes = [lo.code for lo in src.learning_outcomes]
    mapped = []
    for lo in db.scalars(select(m.LearningOutcome).where(m.LearningOutcome.course_id == target.id, m.LearningOutcome.code.in_(codes or [""]), m.LearningOutcome.is_active.is_(True))).all():
        db.add(m.QuestionBankOutcome(question_bank_id=copy.id, learning_outcome_id=lo.id)); mapped.append(lo.code)
    copy.learning_outcome_code = mapped[0] if mapped else None
    _audit(db, "question_shared_copy", "question_bank", copy.id, {"source_id": src.id, "to_course": target.id, "mapped_outcomes": mapped}); db.commit()
    return {"id": copy.id, "mapped_outcomes": mapped, "unmapped_outcomes": sorted(set(codes) - set(mapped)), "review_status": "draft"}
