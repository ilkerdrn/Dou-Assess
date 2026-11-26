from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from . import models as m
from .authz import current_user, require_roles
from .config import settings
from .db import get_db
from .services.operations import enqueue_job, scheduler_tick

router = APIRouter()


def _job_out(x: m.OperationalJob) -> dict:
    return {
        "id": x.id, "job_type": x.job_type, "status": x.status, "priority": x.priority,
        "dedupe_key": x.dedupe_key, "payload": x.payload or {}, "result": x.result or {},
        "progress": x.progress, "attempts": x.attempts, "max_attempts": x.max_attempts,
        "run_after": x.run_after, "locked_by": x.locked_by, "locked_at": x.locked_at,
        "started_at": x.started_at, "finished_at": x.finished_at, "error_text": x.error_text,
        "created_by": x.created_by, "created_at": x.created_at, "updated_at": x.updated_at,
    }


def _notification_out(x: m.OperationalNotification) -> dict:
    return {
        "id": x.id, "user_email": x.user_email, "role_scope": x.role_scope, "program_id": x.program_id,
        "notification_type": x.notification_type, "severity": x.severity, "title": x.title, "body": x.body,
        "action_url": x.action_url, "source_entity_type": x.source_entity_type, "source_entity_id": x.source_entity_id,
        "status": x.status, "created_at": x.created_at, "read_at": x.read_at, "expires_at": x.expires_at,
    }


def _actor_email() -> str:
    try: return str(current_user().get("email") or "system")
    except Exception: return "system"


def _read_json(path: Path) -> dict:
    try: return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception: return {}


@router.get("/api/operations/summary")
def operations_summary(db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    queued = db.scalar(select(func.count()).select_from(m.OperationalJob).where(m.OperationalJob.status == "queued")) or 0
    running = db.scalar(select(func.count()).select_from(m.OperationalJob).where(m.OperationalJob.status == "running")) or 0
    failed = db.scalar(select(func.count()).select_from(m.OperationalJob).where(m.OperationalJob.status == "failed")) or 0
    unread = db.scalar(select(func.count()).select_from(m.OperationalNotification).where(m.OperationalNotification.status == "unread")) or 0
    root = Path(settings.ops_storage_path)
    return {
        "jobs": {"queued": queued, "running": running, "failed": failed},
        "notifications": {"unread": unread},
        "backup": _read_json(root / "backup-status.json") or None,
        "backup_verification": _read_json(root / "backup-verification-status.json") or None,
        "automation": {
            "backup_enabled": settings.backup_automation_enabled,
            "backup_interval_hours": settings.backup_interval_hours,
            "backup_retention_days": settings.backup_retention_days,
            "scheduler_interval_seconds": settings.scheduler_interval_seconds,
            "notification_lookahead_days": settings.notification_lookahead_days,
            "integrity_interval_hours": settings.evidence_integrity_interval_hours,
        },
    }


@router.get("/api/operations/jobs")
def list_jobs(
    status: str | None = None, job_type: str | None = None,
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    require_roles("admin", "quality")
    stmt = select(m.OperationalJob)
    count_stmt = select(func.count()).select_from(m.OperationalJob)
    conditions = []
    if status: conditions.append(m.OperationalJob.status == status)
    if job_type: conditions.append(m.OperationalJob.job_type == job_type)
    if conditions:
        stmt = stmt.where(*conditions); count_stmt = count_stmt.where(*conditions)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(m.OperationalJob.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [_job_out(x) for x in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/api/operations/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    obj = db.get(m.OperationalJob, job_id)
    if not obj: raise HTTPException(404, "İş bulunamadı")
    return _job_out(obj)


@router.post("/api/operations/jobs/integrity-scan")
def queue_integrity_scan(db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    job = enqueue_job(db, "evidence_integrity_scan", priority=30, created_by=_actor_email())
    db.commit(); db.refresh(job)
    return _job_out(job)


@router.post("/api/operations/jobs/backup")
def queue_backup(db: Session = Depends(get_db)):
    require_roles("admin")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M")
    job = enqueue_job(db, "backup_create", priority=80, dedupe_key=f"manual-backup:{stamp}", created_by=_actor_email())
    db.commit(); db.refresh(job)
    return _job_out(job)


@router.post("/api/operations/jobs/backup-verify")
def queue_backup_verify(db: Session = Depends(get_db)):
    require_roles("admin")
    job = enqueue_job(db, "backup_verify", priority=70, created_by=_actor_email())
    db.commit(); db.refresh(job)
    return _job_out(job)


@router.post("/api/operations/scheduler/run")
def run_scheduler_now(db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    result = scheduler_tick(db)
    return result


def _notification_scope(db: Session):
    ctx = current_user(); email = str(ctx.get("email") or "").lower(); roles = list(ctx.get("role_names") or [])
    if "admin" in roles:
        return None
    clauses = []
    if email: clauses.append(func.lower(m.OperationalNotification.user_email) == email)
    if roles: clauses.append(m.OperationalNotification.role_scope.in_(roles))
    # Quality managers see institution-wide quality notifications, but not private user notifications.
    if "quality" in roles: clauses.append(m.OperationalNotification.role_scope == "quality")
    return or_(*clauses) if clauses else m.OperationalNotification.id == -1


@router.get("/api/operations/notifications")
def list_notifications(
    status: str | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    scope = _notification_scope(db)
    conditions = []
    if scope is not None: conditions.append(scope)
    if status: conditions.append(m.OperationalNotification.status == status)
    now = datetime.now(timezone.utc)
    conditions.append(or_(m.OperationalNotification.expires_at.is_(None), m.OperationalNotification.expires_at > now))
    stmt = select(m.OperationalNotification).where(*conditions)
    count_stmt = select(func.count()).select_from(m.OperationalNotification).where(*conditions)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(m.OperationalNotification.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [_notification_out(x) for x in rows], "total": total, "limit": limit, "offset": offset}


@router.patch("/api/operations/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    scope = _notification_scope(db)
    stmt = select(m.OperationalNotification).where(m.OperationalNotification.id == notification_id)
    if scope is not None: stmt = stmt.where(scope)
    obj = db.scalar(stmt)
    if not obj: raise HTTPException(404, "Bildirim bulunamadı")
    obj.status = "read"; obj.read_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(obj)
    return _notification_out(obj)


@router.post("/api/operations/notifications/read-all")
def mark_all_notifications_read(db: Session = Depends(get_db)):
    scope = _notification_scope(db)
    stmt = select(m.OperationalNotification).where(m.OperationalNotification.status == "unread")
    if scope is not None: stmt = stmt.where(scope)
    rows = list(db.scalars(stmt).all()); now = datetime.now(timezone.utc)
    for obj in rows: obj.status = "read"; obj.read_at = now
    db.commit()
    return {"updated": len(rows)}
