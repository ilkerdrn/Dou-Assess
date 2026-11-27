"""Scan quality sampling, semester-closure package and scan retention/purge."""
from __future__ import annotations

import json
import random
import zipfile
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from . import models as m
from .authz import current_user, require_exam_access, require_roles
from .config import settings
from .db import get_db
from .services.analytics import exam_analytics
from .services.paper import build_exam_pdf

router = APIRouter()


def _audit(db: Session, action: str, entity_type: str, entity_id: int | None, payload: dict[str, Any]) -> None:
    u = current_user()
    db.add(m.AuditLog(actor_user_id=u.get("id"), actor_email=u.get("email") or "system", actor_roles=list(u.get("role_names") or []),
                      action=action, entity_type=entity_type, entity_id=entity_id, payload=json.loads(json.dumps(payload, default=str))))


# ---------------------------------------------------------------- random sampling of auto-accepted reads
class SampleRequest(BaseModel):
    percent: int = Field(default=10, ge=1, le=100)
    minimum: int = Field(default=5, ge=1, le=500)


class SampleResult(BaseModel):
    ok: bool
    note: str = Field(default="", max_length=1000)


def _audit_state(db: Session, exam_id: int) -> dict[str, Any]:
    ids = list(db.scalars(select(m.ScanItem.id).where(m.ScanItem.exam_id == exam_id)).all())
    sampled, results = {}, {}
    if ids:
        for log in db.scalars(select(m.AuditLog).where(m.AuditLog.entity_type == "scan_item", m.AuditLog.entity_id.in_(ids), m.AuditLog.action.in_(["scan_audit_sampled", "scan_audit_result"])).order_by(m.AuditLog.id)).all():
            if log.action == "scan_audit_sampled": sampled[log.entity_id] = log.created_at
            else: results[log.entity_id] = bool((log.payload or {}).get("ok"))
    return {"sampled": sampled, "results": results}


@router.post("/api/exams/{exam_id}/scan-audit/sample", status_code=201)
def scan_audit_sample(exam_id: int, body: SampleRequest, db: Session = Depends(get_db)):
    """Draw a random sample of automatically accepted OMR pages for human re-check (the 'safe' reads are the risky ones)."""
    require_exam_access(db, exam_id, write=True)
    state = _audit_state(db, exam_id)
    pool = [i for i in db.scalars(select(m.ScanItem.id).where(m.ScanItem.exam_id == exam_id, m.ScanItem.status == "accepted", m.ScanItem.page_kind == "omr")).all() if i not in state["sampled"]]
    total_accepted = db.scalar(select(func.count()).select_from(m.ScanItem).where(m.ScanItem.exam_id == exam_id, m.ScanItem.status == "accepted", m.ScanItem.page_kind == "omr")) or 0
    want = min(len(pool), max(body.minimum, -(-total_accepted * body.percent // 100)))
    picked = random.sample(pool, want) if want else []
    for iid in picked:
        _audit(db, "scan_audit_sampled", "scan_item", iid, {"exam_id": exam_id, "percent": body.percent})
    db.commit()
    return {"drawn": len(picked), "pool_left": len(pool) - len(picked), "item_ids": picked}


@router.get("/api/exams/{exam_id}/scan-audit")
def scan_audit_status(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    st = _audit_state(db, exam_id)
    checked = len(st["results"]); bad = sum(1 for v in st["results"].values() if not v)
    rate = round(bad / checked * 100, 2) if checked else None
    items = {x.id: x for x in db.scalars(select(m.ScanItem).where(m.ScanItem.id.in_(list(st["sampled"])))).all()} if st["sampled"] else {}
    pending = [{"scan_item_id": i, "page_no": items[i].page_no, "student_no": items[i].student_no_detected, "answers": items[i].answers,
                "preview_url": f"/api/scan-items/{i}/review-preview"} for i in st["sampled"] if i not in st["results"] and i in items]
    target = float(settings.scan_target_error_percent)
    return {"sampled": len(st["sampled"]), "checked": checked, "mismatches": bad, "error_rate_percent": rate, "target_error_percent": target,
            "meets_target": (rate <= target) if rate is not None else None, "pending": pending}


@router.post("/api/scan-items/{item_id}/audit-result")
def scan_audit_result(item_id: int, body: SampleResult, db: Session = Depends(get_db)):
    item = db.get(m.ScanItem, item_id)
    if not item: raise HTTPException(404, "Tarama kaydı bulunamadı")
    require_exam_access(db, item.exam_id, write=True)
    st = _audit_state(db, item.exam_id)
    if item_id not in st["sampled"]: raise HTTPException(409, "Bu sayfa örneklemede değil")
    if item_id in st["results"]: raise HTTPException(409, "Bu örnek zaten değerlendirildi")
    _audit(db, "scan_audit_result", "scan_item", item_id, {"exam_id": item.exam_id, "ok": body.ok, "note": body.note})
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- semester closure package
def _w(z: zipfile.ZipFile, sums: dict[str, str], name: str, data: bytes) -> None:
    z.writestr(name, data); sums[name] = sha256(data).hexdigest()


def _j(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str).encode("utf-8")


@router.get("/api/exams/{exam_id}/closure-package.zip")
def closure_package(exam_id: int, db: Session = Depends(get_db)):
    """Final, hash-sealed archive of one exam: paper, key + revisions, scores, grade history, appeals, scans, audit trail."""
    require_exam_access(db, exam_id, write=False)
    exam = db.scalar(select(m.Exam).options(selectinload(m.Exam.questions).selectinload(m.Question.learning_outcomes), selectinload(m.Exam.questions).selectinload(m.Question.learning_outcome),
                                            selectinload(m.Exam.learning_outcomes), selectinload(m.Exam.exam_students)).where(m.Exam.id == exam_id))
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    if not exam.grade_locked_at:
        raise HTTPException(409, "Dönem kapanış paketi için önce puanlar kilitlenmelidir")
    sums: dict[str, str] = {}
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        qs = [{"id": q.id, "order_no": q.order_no, "type": q.question_type, "text": q.text, "points": q.points, "choices": q.choices, "correct_answer": q.correct_answer,
               "expected_answer": q.expected_answer, "rubric": q.rubric, "outcomes": sorted({x.code for x in q.learning_outcomes})} for q in sorted(exam.questions, key=lambda x: x.order_no)]
        _w(z, sums, "exam.json", _j({"id": exam.id, "title": exam.title, "type": exam.exam_type, "date": exam.exam_date, "status": exam.status, "revision_no": exam.revision_no,
                                     "printed_at": exam.printed_at, "grade_locked_at": exam.grade_locked_at, "grade_locked_by": exam.grade_locked_by,
                                     "snapshot": {"course": exam.course_code_snapshot, "year": exam.academic_year_snapshot, "term": exam.term_snapshot},
                                     "learning_outcomes": [{"code": x.code, "description": x.description, "target_percent": x.target_percent} for x in exam.learning_outcomes], "questions": qs}))
        _w(z, sums, "analytics.json", _j(exam_analytics(db, exam_id)))
        for bk in ["A", "B", "C", "D"][: (exam.booklet_count or 4)]:
            if exam.questions:
                data, meta = build_exam_pdf(exam, bk)
                _w(z, sums, f"paper/booklet-{bk}.pdf", data); _w(z, sums, f"paper/booklet-{bk}.metadata.json", _j(meta))
        revs = db.scalars(select(m.AnswerKeyRevision).where(m.AnswerKeyRevision.exam_id == exam_id).order_by(m.AnswerKeyRevision.id)).all()
        _w(z, sums, "answer-key-revisions.json", _j([{"id": r.id, "corrections": r.corrections, "reason": r.reason, "affected": r.affected_responses, "at": r.created_at} for r in revs]))
        es_ids = [es.id for es in exam.exam_students]
        grev = db.scalars(select(m.ResponseGradeRevision).where(m.ResponseGradeRevision.exam_student_id.in_(es_ids)).order_by(m.ResponseGradeRevision.id)).all() if es_ids else []
        _w(z, sums, "grade-revisions.json", _j([{"response_id": r.response_id, "exam_student_id": r.exam_student_id, "question_id": r.question_id, "from": r.previous_awarded_points, "to": r.new_awarded_points, "source": r.source, "by": r.changed_by, "at": r.changed_at} for r in grev]))
        responses = db.scalars(select(m.Response).where(m.Response.exam_student_id.in_(es_ids))).all() if es_ids else []
        _w(z, sums, "responses.json", _j([{"exam_student_id": r.exam_student_id, "question_id": r.question_id, "answer": r.answer_text, "awarded": r.awarded_points, "rubric": r.rubric_scores, "graded_by": r.graded_by} for r in responses]))
        appeals = db.scalars(select(m.GradeAppeal).where(m.GradeAppeal.exam_id == exam_id)).all()
        _w(z, sums, "appeals.json", _j([{"id": a.id, "student_id": a.student_id, "question_id": a.question_id, "reason": a.reason, "status": a.status, "old": a.old_points, "new": a.new_points, "note": a.decision_note} for a in appeals]))
        scans = db.scalars(select(m.ScanItem).where(m.ScanItem.exam_id == exam_id).order_by(m.ScanItem.id)).all()
        root = Path(settings.scan_storage_path).resolve()
        for s in scans:
            if s.preview_name:
                p = (root / s.preview_name).resolve()
                if root in p.parents and p.exists():
                    _w(z, sums, f"scans/{s.id}_{Path(s.preview_name).name}", p.read_bytes())
        _w(z, sums, "scan-items.json", _j([{"id": s.id, "page_no": s.page_no, "status": s.status, "booklet": s.booklet, "student_id": s.student_id, "answers": s.answers, "issues": s.issue_summary} for s in scans]))
        qids = [q.id for q in exam.questions]
        logs = db.scalars(select(m.AuditLog).where(((m.AuditLog.entity_type == "exam") & (m.AuditLog.entity_id == exam_id)) | ((m.AuditLog.entity_type == "question") & (m.AuditLog.entity_id.in_(qids or [0]))) | ((m.AuditLog.entity_type == "scan_item") & (m.AuditLog.entity_id.in_([s.id for s in scans] or [0])))).order_by(m.AuditLog.id)).all()
        _w(z, sums, "audit-trail.json", _j([{"id": a.id, "at": a.created_at, "actor": a.actor_email, "action": a.action, "entity": f"{a.entity_type}:{a.entity_id}", "payload": a.payload} for a in logs]))
        manifest = {"exam_id": exam_id, "generated_at": datetime.now(timezone.utc).isoformat(), "generated_by": current_user().get("email") or "system", "files": dict(sorted(sums.items()))}
        manifest["package_sha256"] = sha256(json.dumps(manifest["files"], sort_keys=True).encode()).hexdigest()
        z.writestr("SHA256SUMS.json", _j(manifest))
    _audit(db, "closure_package_generate", "exam", exam_id, {"files": len(sums), "package_sha256": manifest["package_sha256"]}); db.commit()
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="DOU_closure_exam_{exam_id}.zip"', "X-DOU-Package-SHA256": manifest["package_sha256"]})


# ---------------------------------------------------------------- scan retention
def _retention_rows(db: Session) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(settings.scan_retention_days))
    out = []
    for e in db.scalars(select(m.Exam).where(m.Exam.grade_locked_at.is_not(None))).all():
        locked = e.grade_locked_at if e.grade_locked_at.tzinfo else e.grade_locked_at.replace(tzinfo=timezone.utc)
        n = db.scalar(select(func.count()).select_from(m.ScanItem).where(m.ScanItem.exam_id == e.id, m.ScanItem.preview_name.is_not(None))) or 0
        out.append({"exam_id": e.id, "title": e.title, "grade_locked_at": locked.isoformat(), "scan_files": n,
                    "retention_until": (locked + timedelta(days=int(settings.scan_retention_days))).isoformat(), "expired": locked <= cutoff and n > 0})
    return out


@router.get("/api/archive/retention")
def retention_overview(db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    rows = _retention_rows(db)
    return {"scan_retention_days": settings.scan_retention_days, "note": "Süreyi kurum arşiv yönergesiyle teyit edin (SCAN_RETENTION_DAYS).",
            "expired_count": sum(1 for r in rows if r["expired"]), "items": [r for r in rows if r["scan_files"]]}


class PurgeRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


@router.post("/api/exams/{exam_id}/purge-scans")
def purge_scans(exam_id: int, body: PurgeRequest, db: Session = Depends(get_db)):
    """Recorded deletion of scanned page images after the retention period. Scores and the audit trail stay."""
    require_roles("admin")
    row = next((r for r in _retention_rows(db) if r["exam_id"] == exam_id), None)
    if not row: raise HTTPException(404, "Sınav bulunamadı veya puanları kilitli değil")
    if not row["expired"]: raise HTTPException(409, f"Saklama süresi dolmadı (bitiş: {row['retention_until'][:10]})")
    root = Path(settings.scan_storage_path).resolve(); removed = 0
    for s in db.scalars(select(m.ScanItem).where(m.ScanItem.exam_id == exam_id, m.ScanItem.preview_name.is_not(None))).all():
        p = (root / s.preview_name).resolve()
        if root in p.parents and p.exists():
            p.unlink(); removed += 1
        s.preview_name = None
    _audit(db, "scan_purge", "exam", exam_id, {"files_removed": removed, "reason": body.reason, "retention_days": settings.scan_retention_days}); db.commit()
    return {"files_removed": removed}
