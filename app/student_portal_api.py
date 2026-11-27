"""Student exam-paper review and grade-appeal portal (Gradescope-style).

No student accounts and no new tables: staff generate per-student links whose token is an
HMAC of (exam, student) under STUDENT_LINK_SECRET. A student sees only their own paper, only after
the exam's grades are locked (released), and may file appeals only inside STUDENT_APPEAL_DAYS.
Appeals land in the existing GradeAppeal workflow (decided by program head/admin).
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .authz import require_exam_access
from .config import settings
from .db import get_db

router = APIRouter()
PUB = "/api/public/student-exam/{exam_id}/{student_id}"


def _secret() -> str:
    if settings.student_link_secret:
        return settings.student_link_secret
    if settings.app_env == "production":
        raise HTTPException(503, "Öğrenci bağlantıları için STUDENT_LINK_SECRET tanımlı değil")
    return "dev-only-student-link-secret"


def make_token(exam_id: int, student_id: int) -> str:
    return hmac.new(_secret().encode(), f"student-exam:{exam_id}:{student_id}".encode(), hashlib.sha256).hexdigest()[:40]


class Ctx:
    def __init__(self, exam, es, student):
        self.exam, self.es, self.student = exam, es, student


def student_ctx(exam_id: int, student_id: int, x_dou_student_token: str = Header(default="", alias="X-DOU-Student-Token"), db: Session = Depends(get_db)) -> Ctx:
    if not hmac.compare_digest(x_dou_student_token or "", make_token(exam_id, student_id)):
        raise HTTPException(401, "Geçersiz öğrenci bağlantısı")
    exam = db.get(m.Exam, exam_id)
    es = db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.student_id == student_id))
    student = db.get(m.Student, student_id)
    if not exam or not es or not student:
        raise HTTPException(404, "Kayıt bulunamadı")
    if not exam.grade_locked_at:
        raise HTTPException(403, "Sonuçlar henüz açıklanmadı")
    return Ctx(exam, es, student)


def _window(exam: m.Exam) -> tuple[bool, str]:
    locked = exam.grade_locked_at if exam.grade_locked_at.tzinfo else exam.grade_locked_at.replace(tzinfo=timezone.utc)
    deadline = locked + timedelta(days=max(0, int(settings.student_appeal_days)))
    return datetime.now(timezone.utc) <= deadline, deadline.isoformat()


def _audit(db: Session, ctx: Ctx, action: str, payload: dict | None = None) -> None:
    db.add(m.AuditLog(actor_user_id=None, actor_email=f"student:{ctx.student.student_no}", actor_roles=["student"], action=action,
                      entity_type="exam", entity_id=ctx.exam.id, payload=json.loads(json.dumps(payload or {}, default=str))))
    db.commit()


@router.get("/api/exams/{exam_id}/student-links")
def student_links(exam_id: int, db: Session = Depends(get_db)):
    """Staff: per-student review links (share via OBS/e-mail). Only after grades are locked."""
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    if not exam.grade_locked_at:
        raise HTTPException(409, "Öğrenci bağlantıları için önce puanlar kilitlenmelidir")
    rows = db.scalars(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.attendance_status == "attended")).all()
    out = []
    for es in rows:
        st = db.get(m.Student, es.student_id)
        out.append({"student_no": st.student_no, "full_name": st.full_name,
                    "path": f"/student.html?exam={exam_id}&student={st.id}#t={make_token(exam_id, st.id)}"})
    return {"exam_id": exam_id, "appeal_days": settings.student_appeal_days, "links": sorted(out, key=lambda x: x["student_no"])}


@router.get(PUB)
def student_view(ctx: Ctx = Depends(student_ctx), db: Session = Depends(get_db)):
    exam, es = ctx.exam, ctx.es
    qs = db.scalars(select(m.Question).where(m.Question.exam_id == exam.id).order_by(m.Question.order_no)).all()
    resp = {r.question_id: r for r in db.scalars(select(m.Response).where(m.Response.exam_student_id == es.id)).all()}
    appeals = db.scalars(select(m.GradeAppeal).where(m.GradeAppeal.exam_id == exam.id, m.GradeAppeal.student_id == ctx.student.id).order_by(m.GradeAppeal.id.desc())).all()
    scans = db.scalars(select(m.ScanItem).where(m.ScanItem.exam_id == exam.id, m.ScanItem.student_id == ctx.student.id).order_by(m.ScanItem.page_no)).all()
    open_ok, deadline = _window(exam)
    total = sum(float(r.awarded_points or 0) for r in resp.values())
    possible = sum(float(q.points) for q in qs)
    _audit(db, ctx, "student_portal_view")
    return {
        "student": {"student_no": ctx.student.student_no, "name": ctx.student.full_name},
        "exam": {"title": exam.title, "type": exam.exam_type, "date": exam.exam_date.isoformat() if exam.exam_date else None},
        "total": round(total, 2), "possible": round(possible, 2),
        "appeal_open": open_ok, "appeal_deadline": deadline,
        "questions": [{"id": q.id, "no": q.order_no, "text": q.text, "type": q.question_type, "points": q.points,
                       "answer": resp[q.id].answer_text if q.id in resp else None,
                       "awarded": float(resp[q.id].awarded_points) if q.id in resp else 0.0,
                       "correct_answer": q.correct_answer if q.question_type == "mcq" else None,
                       "rubric_scores": (resp[q.id].rubric_scores if q.id in resp else {}),
                       "rubric": q.rubric} for q in qs],
        "appeals": [{"id": a.id, "question_id": a.question_id, "reason": a.reason, "status": a.status,
                     "decision_note": a.decision_note if a.status != "open" else "", "created_at": a.created_at.isoformat()} for a in appeals],
        "scan_pages": [{"id": s.id, "page_no": s.page_no} for s in scans if s.preview_name],
    }


@router.get(PUB + "/scan/{item_id}")
def student_scan(item_id: int, ctx: Ctx = Depends(student_ctx), db: Session = Depends(get_db)):
    item = db.get(m.ScanItem, item_id)
    if not item or item.exam_id != ctx.exam.id or item.student_id != ctx.student.id or not item.preview_name:
        raise HTTPException(404, "Sayfa bulunamadı")
    root = Path(settings.scan_storage_path).resolve()
    path = (root / item.preview_name).resolve()
    if root not in path.parents or not path.exists():
        raise HTTPException(404, "Sayfa dosyası bulunamadı")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})


class StudentAppeal(BaseModel):
    question_id: int
    reason: str = Field(min_length=10, max_length=2000)


@router.post(PUB + "/appeals", status_code=201)
def student_appeal(body: StudentAppeal, ctx: Ctx = Depends(student_ctx), db: Session = Depends(get_db)):
    ok, deadline = _window(ctx.exam)
    if not ok:
        raise HTTPException(409, f"İtiraz süresi doldu ({deadline[:10]})")
    q = db.get(m.Question, body.question_id)
    if not q or q.exam_id != ctx.exam.id:
        raise HTTPException(400, "Soru bu sınava ait değil")
    dup = db.scalar(select(m.GradeAppeal).where(m.GradeAppeal.exam_id == ctx.exam.id, m.GradeAppeal.student_id == ctx.student.id,
                                                m.GradeAppeal.question_id == q.id, m.GradeAppeal.status == "open"))
    if dup:
        raise HTTPException(409, "Bu soru için açık bir itirazınız zaten var")
    r = db.scalar(select(m.Response).where(m.Response.exam_student_id == ctx.es.id, m.Response.question_id == q.id))
    obj = m.GradeAppeal(exam_id=ctx.exam.id, student_id=ctx.student.id, question_id=q.id, reason=body.reason.strip(),
                        old_points=float(r.awarded_points) if r else None, old_rubric_scores=dict(r.rubric_scores or {}) if r else {},
                        created_by=f"student:{ctx.student.student_no}")
    db.add(obj); db.flush()
    course = db.get(m.Course, ctx.exam.course_id)
    if course and course.instructor_email:
        db.add(m.OperationalNotification(
            user_email=course.instructor_email.lower(), program_id=course.program_id, notification_type="student_appeal", severity="warning",
            title=f"Yeni not itirazı: {ctx.exam.title}", body=f"{ctx.student.student_no} · soru {q.order_no}: {obj.reason[:200]}",
            action_url=f"/#exam={ctx.exam.id}", dedupe_key=f"student_appeal:{obj.id}", source_entity_type="grade_appeal", source_entity_id=obj.id))
    _audit(db, ctx, "student_appeal_create", {"appeal_id": obj.id, "question_id": q.id})
    return {"id": obj.id, "status": obj.status}
