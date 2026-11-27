"""Read-only evidence room for external evaluators (MEDEK / MÜDEK / TURAK ...).

Everything here is authenticated with the evaluator workspace token (same as the
snapshot endpoint) and is scoped to the program of the workspace's application.
No endpoint writes domain data; every access is written to the audit log.
Student names are masked (initials only); student numbers stay visible so that
evaluators can sample files.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from . import models as m
from .config import settings
from .db import get_db
from .services.analytics import exam_analytics, student_exam_analytics
from .services.compliance import build_student_outcome_card
from .services.paper import build_exam_pdf

router = APIRouter()
BASE = "/api/public/evaluator-workspaces/{workspace_id}/room"
# Draft exams are work-in-progress and never shown to evaluators.
VISIBLE_EXAM_STATUSES = ("approved", "grading", "archived")


class RoomScope:
    def __init__(self, ws: m.EvaluatorWorkspace, app: m.AccreditationApplication, program: m.Program):
        self.ws, self.app, self.program = ws, app, program


def _audit(db: Session, scope: RoomScope, action: str, entity_type: str, entity_id: int | None, payload: dict[str, Any] | None = None) -> None:
    data = {"workspace_id": scope.ws.id, "application_id": scope.app.id, **(payload or {})}
    db.add(m.AuditLog(
        actor_user_id=None, actor_email=f"evaluator:{scope.ws.evaluator_email}", actor_roles=["evaluator"],
        action=action, entity_type=entity_type, entity_id=entity_id,
        payload=json.loads(json.dumps(data, ensure_ascii=False, default=str)),
    ))
    db.commit()


def room_scope(workspace_id: int, x_dou_evaluator_token: str = Header(default="", alias="X-DOU-Evaluator-Token"), db: Session = Depends(get_db)) -> RoomScope:
    """Header-only token auth (no token in URLs; the UI downloads PDFs/scans via fetch + blob)."""
    from .compliance_api import _ensure_evaluator_workspace_active
    ws = db.get(m.EvaluatorWorkspace, workspace_id)
    if not ws:
        raise HTTPException(404, "Değerlendirici çalışma alanı bulunamadı")
    _ensure_evaluator_workspace_active(ws)
    supplied = hashlib.sha256((x_dou_evaluator_token or "").encode("utf-8")).hexdigest()
    if not ws.invitation_token_hash or not hmac.compare_digest(supplied, ws.invitation_token_hash):
        raise HTTPException(401, "Geçersiz değerlendirici erişim tokenı")
    app = db.get(m.AccreditationApplication, ws.application_id)
    program = db.get(m.Program, app.program_id) if app else None
    if not app or not program:
        raise HTTPException(404, "Başvuru veya program bulunamadı")
    return RoomScope(ws, app, program)


def mask_name(name: str | None) -> str:
    parts = [p for p in re.split(r"\s+", (name or "").strip()) if p]
    return " ".join(f"{p[0].upper()}***" for p in parts) or "—"


def _student_row(s: m.Student) -> dict[str, Any]:
    return {"student_id": s.id, "student_no": s.student_no, "name": mask_name(s.full_name), "class_name": s.class_name}


def _course(db: Session, scope: RoomScope, course_id: int) -> m.Course:
    c = db.get(m.Course, course_id)
    if not c or c.program_id != scope.program.id:
        raise HTTPException(404, "Ders bu programda bulunamadı")
    return c


def _exam(db: Session, scope: RoomScope, exam_id: int) -> m.Exam:
    e = db.scalar(select(m.Exam).options(
        selectinload(m.Exam.questions).selectinload(m.Question.learning_outcomes),
        selectinload(m.Exam.questions).selectinload(m.Question.learning_outcome),
        selectinload(m.Exam.learning_outcomes),
    ).where(m.Exam.id == exam_id))
    if not e or e.status not in VISIBLE_EXAM_STATUSES:
        raise HTTPException(404, "Sınav bulunamadı veya henüz değerlendiriciye açık değil")
    _course(db, scope, e.course_id)
    return e


def _student(db: Session, scope: RoomScope, student_id: int) -> m.Student:
    s = db.get(m.Student, student_id)
    if not s or s.program_id != scope.program.id:
        raise HTTPException(404, "Öğrenci bu programda bulunamadı")
    return s


def _year_filter(stmt, col, year: str | None):
    return stmt.where(col == year) if year else stmt


@router.get(BASE)
def room_overview(academic_year: str | None = None, scope: RoomScope = Depends(room_scope), db: Session = Depends(get_db)):
    p = scope.program
    pos = db.scalars(_year_filter(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == p.id), m.ProgramOutcome.academic_year, academic_year).order_by(m.ProgramOutcome.code)).all()
    courses = db.scalars(_year_filter(select(m.Course).where(m.Course.program_id == p.id), m.Course.academic_year, academic_year).order_by(m.Course.academic_year.desc(), m.Course.code)).all()
    ids = [c.id for c in courses]
    lo_n = dict(db.execute(select(m.LearningOutcome.course_id, func.count()).where(m.LearningOutcome.course_id.in_(ids)).group_by(m.LearningOutcome.course_id)).all()) if ids else {}
    ex_n = dict(db.execute(select(m.Exam.course_id, func.count()).where(m.Exam.course_id.in_(ids), m.Exam.status.in_(VISIBLE_EXAM_STATUSES)).group_by(m.Exam.course_id)).all()) if ids else {}
    en_n = dict(db.execute(select(m.Enrollment.course_id, func.count()).where(m.Enrollment.course_id.in_(ids)).group_by(m.Enrollment.course_id)).all()) if ids else {}
    years = sorted({c.academic_year for c in db.scalars(select(m.Course).where(m.Course.program_id == p.id)).all()}, reverse=True)
    student_count = db.scalar(select(func.count()).select_from(m.Student).where(m.Student.program_id == p.id)) or 0
    _audit(db, scope, "evaluator_room_overview", "program", p.id, {"academic_year": academic_year})
    return {
        "program": {"id": p.id, "code": p.code, "name": p.name, "faculty": p.faculty, "department": p.department},
        "application": {"academic_year": scope.app.academic_year, "stage": scope.app.stage},
        "academic_years": years, "student_count": student_count,
        "program_outcomes": [{"id": x.id, "code": x.code, "description": x.description, "academic_year": x.academic_year} for x in pos],
        "courses": [{"id": c.id, "code": c.code, "name": c.name, "academic_year": c.academic_year, "term": c.term,
                     "instructor": c.instructor_name or c.instructor_email, "outcome_count": lo_n.get(c.id, 0),
                     "exam_count": ex_n.get(c.id, 0), "student_count": en_n.get(c.id, 0)} for c in courses],
    }


@router.get(BASE + "/outcome-matrix")
def room_outcome_matrix(academic_year: str | None = None, scope: RoomScope = Depends(room_scope), db: Session = Depends(get_db)):
    """Course learning outcome → program outcome contribution matrix."""
    p = scope.program
    pos = db.scalars(_year_filter(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == p.id), m.ProgramOutcome.academic_year, academic_year).order_by(m.ProgramOutcome.code)).all()
    po_ids = {x.id for x in pos}
    courses = db.scalars(_year_filter(select(m.Course).options(selectinload(m.Course.learning_outcomes).selectinload(m.LearningOutcome.mappings)).where(m.Course.program_id == p.id), m.Course.academic_year, academic_year).order_by(m.Course.code)).all()
    rows = []
    for c in courses:
        for lo in sorted(c.learning_outcomes, key=lambda x: x.code):
            contrib = {mp.program_outcome_id: mp.contribution for mp in lo.mappings if mp.program_outcome_id in po_ids}
            rows.append({"course_id": c.id, "course_code": c.code, "course_name": c.name, "academic_year": c.academic_year,
                         "lo_code": lo.code, "lo_description": lo.description, "contributions": {str(k): v for k, v in contrib.items()}})
    _audit(db, scope, "evaluator_room_outcome_matrix", "program", p.id, {"academic_year": academic_year})
    return {"program_outcomes": [{"id": x.id, "code": x.code, "description": x.description} for x in pos], "rows": rows}


@router.get(BASE + "/courses/{course_id}")
def room_course(course_id: int, scope: RoomScope = Depends(room_scope), db: Session = Depends(get_db)):
    c = _course(db, scope, course_id)
    los = db.scalars(select(m.LearningOutcome).options(selectinload(m.LearningOutcome.mappings).selectinload(m.OutcomeMapping.program_outcome)).where(m.LearningOutcome.course_id == c.id).order_by(m.LearningOutcome.code)).all()
    exams = db.scalars(select(m.Exam).where(m.Exam.course_id == c.id, m.Exam.status.in_(VISIBLE_EXAM_STATUSES)).order_by(m.Exam.exam_date, m.Exam.id)).all()
    students = db.scalars(select(m.Student).join(m.Enrollment, m.Enrollment.student_id == m.Student.id).where(m.Enrollment.course_id == c.id).order_by(m.Student.student_no)).all()
    q_n = dict(db.execute(select(m.Question.exam_id, func.count()).where(m.Question.exam_id.in_([e.id for e in exams])).group_by(m.Question.exam_id)).all()) if exams else {}
    _audit(db, scope, "evaluator_room_course", "course", c.id)
    return {
        "course": {"id": c.id, "code": c.code, "name": c.name, "academic_year": c.academic_year, "term": c.term,
                   "instructor": c.instructor_name or c.instructor_email, "pass_threshold_percent": c.pass_threshold_percent},
        "learning_outcomes": [{"id": lo.id, "code": lo.code, "description": lo.description, "target_percent": lo.target_percent,
                               "program_outcomes": [{"code": mp.program_outcome.code, "description": mp.program_outcome.description, "contribution": mp.contribution} for mp in sorted(lo.mappings, key=lambda x: x.program_outcome.code)]} for lo in los],
        "exams": [{"id": e.id, "title": e.title, "exam_type": e.exam_type, "exam_date": e.exam_date.isoformat() if e.exam_date else None,
                   "status": e.status, "weight_percent": e.assessment_weight_percent, "question_count": q_n.get(e.id, 0)} for e in exams],
        "students": [_student_row(s) for s in students],
    }


@router.get(BASE + "/exams/{exam_id}")
def room_exam(exam_id: int, scope: RoomScope = Depends(room_scope), db: Session = Depends(get_db)):
    e = _exam(db, scope, exam_id)
    try:
        analytics = exam_analytics(db, e.id)
    except ValueError:
        analytics = {}
    q_stats = {q["question_id"]: q for q in analytics.get("question_analysis", [])}
    questions = []
    for q in sorted(e.questions, key=lambda x: x.order_no):
        codes = sorted({x.code for x in q.learning_outcomes}) or ([q.learning_outcome.code] if q.learning_outcome else [])
        st = q_stats.get(q.id, {})
        questions.append({"id": q.id, "order_no": q.order_no, "type": q.question_type, "text": q.text, "points": q.points,
                          "choices": q.choices, "correct_answer": q.correct_answer, "expected_answer": q.expected_answer,
                          "rubric": q.rubric, "has_image": bool(q.image_data), "bloom_level": q.bloom_level, "topic": q.topic,
                          "learning_outcomes": codes, "attainment_percent": st.get("attainment_percent"),
                          "average_points": st.get("average_points"), "difficulty": st.get("difficulty")})
    exam_students = db.scalars(select(m.ExamStudent).options(selectinload(m.ExamStudent.student)).where(m.ExamStudent.exam_id == e.id)).all()
    score = {r["student_id"]: r for r in analytics.get("students", [])}
    scans = db.scalars(select(m.ScanItem.student_id).where(m.ScanItem.exam_id == e.id, m.ScanItem.student_id.is_not(None))).all()
    scanned = set(scans)
    _audit(db, scope, "evaluator_room_exam", "exam", e.id)
    return {
        "exam": {"id": e.id, "course_id": e.course_id, "title": e.title, "exam_type": e.exam_type, "status": e.status,
                 "exam_date": e.exam_date.isoformat() if e.exam_date else None, "duration_minutes": e.duration_minutes,
                 "weight_percent": e.assessment_weight_percent, "approved_by": e.approved_by,
                 "approved_at": e.approved_at.isoformat() if e.approved_at else None, "revision_no": e.revision_no,
                 "instructions": e.instructions, "booklets": e.booklet_count, "grade_locked": bool(e.grade_locked_at)},
        "questions": questions,
        "learning_outcomes": analytics.get("learning_outcomes", []),
        "program_outcomes": analytics.get("program_outcomes", []),
        "summary": {k: analytics.get(k) for k in ("student_count", "class_average", "class_average_percent", "median_score", "standard_deviation", "min_score", "max_score", "pass_percent", "reliability", "score_distribution", "total_possible_points") if k in analytics},
        "students": [{**_student_row(es.student), "attendance": es.attendance_status,
                      "total_score": (score.get(es.student_id) or {}).get("total_score"),
                      "score_percent": (score.get(es.student_id) or {}).get("score_percent"),
                      "has_scan": es.student_id in scanned} for es in sorted(exam_students, key=lambda x: x.student.student_no)],
    }


@router.get(BASE + "/exams/{exam_id}/paper.pdf")
def room_exam_paper(exam_id: int, booklet: str = "A", scope: RoomScope = Depends(room_scope), db: Session = Depends(get_db)):
    e = _exam(db, scope, exam_id)
    if not e.questions:
        raise HTTPException(409, "Sınavda soru yok")
    try:
        data, meta = build_exam_pdf(e, (booklet or "A").upper())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    _audit(db, scope, "evaluator_room_exam_paper", "exam", e.id, {"booklet": meta.get("booklet"), "sha256": meta.get("pdf_sha256")})
    return StreamingResponse(BytesIO(data), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="exam_{e.id}.pdf"', "X-DOU-Paper-SHA256": str(meta.get("pdf_sha256", ""))})


@router.get(BASE + "/exams/{exam_id}/students/{student_id}")
def room_student_exam(exam_id: int, student_id: int, scope: RoomScope = Depends(room_scope), db: Session = Depends(get_db)):
    e = _exam(db, scope, exam_id)
    s = _student(db, scope, student_id)
    es = db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id == e.id, m.ExamStudent.student_id == s.id))
    if not es:
        raise HTTPException(404, "Öğrenci bu sınava kayıtlı değil")
    resp = {r.question_id: r for r in db.scalars(select(m.Response).where(m.Response.exam_student_id == es.id)).all()}
    try:
        an = student_exam_analytics(db, e.id, es.id)
    except ValueError:
        an = {}
    pages = db.scalars(select(m.ScanItem).where(m.ScanItem.exam_id == e.id, m.ScanItem.student_id == s.id).order_by(m.ScanItem.page_no)).all()
    _audit(db, scope, "evaluator_room_student_exam", "exam", e.id, {"student_id": s.id})
    return {
        "student": _student_row(s), "attendance": es.attendance_status,
        "total_score": an.get("total_score"), "total_possible_points": an.get("total_possible_points"), "score_percent": an.get("score_percent"),
        "learning_outcomes": an.get("learning_outcomes", []), "program_outcomes": an.get("program_outcomes", []),
        "answers": [{"order_no": q.order_no, "type": q.question_type, "points": q.points, "text": q.text,
                     "answer": (resp[q.id].answer_text if q.id in resp else None), "correct_answer": q.correct_answer,
                     "awarded_points": (resp[q.id].awarded_points if q.id in resp else 0.0),
                     "is_correct": (resp[q.id].is_correct if q.id in resp else None),
                     "rubric_scores": (resp[q.id].rubric_scores if q.id in resp else {})} for q in sorted(e.questions, key=lambda x: x.order_no)],
        "scan_pages": [{"id": p.id, "page_no": p.page_no, "booklet": p.booklet, "kind": p.page_kind, "has_preview": bool(p.preview_name)} for p in pages],
    }


@router.get(BASE + "/scan-items/{item_id}/preview")
def room_scan_preview(item_id: int, scope: RoomScope = Depends(room_scope), db: Session = Depends(get_db)):
    item = db.get(m.ScanItem, item_id)
    if not item or not item.preview_name or not item.student_id:
        raise HTTPException(404, "Tarama önizlemesi bulunamadı")
    _exam(db, scope, item.exam_id)
    _student(db, scope, item.student_id)
    root = Path(settings.scan_storage_path).resolve()
    path = (root / item.preview_name).resolve()
    if root not in path.parents or not path.exists():
        raise HTTPException(404, "Önizleme dosyası bulunamadı")
    _audit(db, scope, "evaluator_room_scan_preview", "scan_item", item.id, {"exam_id": item.exam_id})
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})


@router.get(BASE + "/students")
def room_students(q: str = "", limit: int = 50, offset: int = 0, scope: RoomScope = Depends(room_scope), db: Session = Depends(get_db)):
    limit = max(1, min(int(limit), 200)); offset = max(0, int(offset))
    stmt = select(m.Student).where(m.Student.program_id == scope.program.id)
    term = q.strip()
    if term:
        stmt = stmt.where(m.Student.student_no.ilike(f"%{term}%"))  # names are masked, so search by number only
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(m.Student.student_no).limit(limit).offset(offset)).all()
    return {"total": total, "items": [_student_row(s) for s in rows]}


@router.get(BASE + "/students/{student_id}/outcome-card")
def room_student_card(student_id: int, academic_year: str | None = None, scope: RoomScope = Depends(room_scope), db: Session = Depends(get_db)):
    s = _student(db, scope, student_id)
    try:
        card = build_student_outcome_card(db, s.id, academic_year)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    card = json.loads(json.dumps(card, ensure_ascii=False, default=str))
    for key in ("full_name", "student_name", "name"):
        if key in card:
            card[key] = mask_name(card[key])
    if isinstance(card.get("student"), dict) and "full_name" in card["student"]:
        card["student"]["full_name"] = mask_name(card["student"]["full_name"])
    _audit(db, scope, "evaluator_room_student_card", "student", s.id, {"academic_year": academic_year})
    return card
