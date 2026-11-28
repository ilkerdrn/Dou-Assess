from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import tarfile
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from .. import models as m
from ..config import settings
from ..release import APP_VERSION
from .integrity import scan_evidence_integrity

UTC = timezone.utc


def utcnow() -> datetime:
    return datetime.now(UTC)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))


def _audit(db: Session, action: str, entity_type: str, entity_id: int | None, payload: dict | None = None, actor: str = "system:operations") -> None:
    db.add(m.AuditLog(
        actor_email=actor,
        actor_roles=["system"],
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=_json_safe(payload or {}),
    ))


def enqueue_job(
    db: Session,
    job_type: str,
    *,
    payload: dict | None = None,
    priority: int = 0,
    run_after: datetime | None = None,
    max_attempts: int = 3,
    dedupe_key: str = "",
    created_by: str = "system",
) -> m.OperationalJob:
    now = utcnow()
    if dedupe_key:
        existing = db.scalar(
            select(m.OperationalJob)
            .where(
                m.OperationalJob.dedupe_key == dedupe_key,
                m.OperationalJob.status.in_(["queued", "running", "succeeded"]),
            )
            .order_by(m.OperationalJob.id.desc())
            .limit(1)
        )
        if existing:
            return existing
    job = m.OperationalJob(
        job_type=job_type,
        status="queued",
        priority=int(priority),
        dedupe_key=dedupe_key,
        payload=_json_safe(payload or {}),
        result={},
        progress=0,
        attempts=0,
        max_attempts=max(1, int(max_attempts)),
        run_after=run_after or now,
        created_by=created_by or "system",
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.flush()
    _audit(db, "job_enqueue", "operational_job", job.id, {"job_type": job_type, "dedupe_key": dedupe_key}, created_by or "system")
    return job


def recover_stale_jobs(db: Session) -> int:
    cutoff = utcnow() - timedelta(minutes=max(1, settings.job_stale_minutes))
    rows = list(db.scalars(
        select(m.OperationalJob).where(
            m.OperationalJob.status == "running",
            m.OperationalJob.locked_at.is_not(None),
            m.OperationalJob.locked_at < cutoff,
        )
    ).all())
    now = utcnow()
    for job in rows:
        job.status = "queued" if job.attempts < job.max_attempts else "failed"
        job.locked_by = ""
        job.locked_at = None
        job.error_text = (job.error_text + "\nRecovered stale worker lock.").strip()
        job.run_after = now + timedelta(seconds=10) if job.status == "queued" else job.run_after
        job.finished_at = now if job.status == "failed" else None
        job.updated_at = now
        _audit(db, "job_stale_recovered", "operational_job", job.id, {"status": job.status})
    return len(rows)


def claim_next_job(db: Session, worker_id: str) -> m.OperationalJob | None:
    now = utcnow()
    stmt = (
        select(m.OperationalJob)
        .where(
            m.OperationalJob.status == "queued",
            or_(m.OperationalJob.run_after.is_(None), m.OperationalJob.run_after <= now),
        )
        .order_by(m.OperationalJob.priority.desc(), m.OperationalJob.id.asc())
        .limit(1)
    )
    # PostgreSQL workers can safely compete. SQLite is only used for tests/pilot.
    if not settings.database_url.startswith("sqlite"):
        stmt = stmt.with_for_update(skip_locked=True)
    job = db.scalar(stmt)
    if not job:
        return None
    job.status = "running"
    job.attempts = int(job.attempts or 0) + 1
    job.locked_by = worker_id
    job.locked_at = now
    job.started_at = job.started_at or now
    job.updated_at = now
    job.progress = max(int(job.progress or 0), 1)
    _audit(db, "job_claim", "operational_job", job.id, {"worker_id": worker_id, "attempt": job.attempts})
    db.commit()
    db.refresh(job)
    return job


def _job_success(db: Session, job: m.OperationalJob, result: dict) -> None:
    now = utcnow()
    job.status = "succeeded"
    job.result = _json_safe(result)
    job.progress = 100
    job.finished_at = now
    job.locked_at = None
    job.locked_by = ""
    job.error_text = ""
    job.updated_at = now
    _audit(db, "job_succeeded", "operational_job", job.id, {"job_type": job.job_type})
    db.commit()


def _job_failure(db: Session, job: m.OperationalJob, exc: Exception) -> None:
    now = utcnow()
    message = f"{type(exc).__name__}: {exc}"[:4000]
    retry = int(job.attempts or 0) < int(job.max_attempts or 1)
    job.status = "queued" if retry else "failed"
    job.error_text = message
    job.locked_at = None
    job.locked_by = ""
    job.updated_at = now
    if retry:
        delay = min(300, 10 * (2 ** max(0, int(job.attempts or 1) - 1)))
        job.run_after = now + timedelta(seconds=delay)
        job.progress = 0
    else:
        job.finished_at = now
    _audit(db, "job_failed" if not retry else "job_retry", "operational_job", job.id, {"job_type": job.job_type, "error": message, "retry": retry})
    db.commit()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_tar_add(tf: tarfile.TarFile, source: Path, arcname: str, *, exclude_backups: bool = False) -> None:
    if not source.exists():
        return
    if source.is_file():
        tf.add(source, arcname=arcname, recursive=False)
        return
    for p in sorted(source.rglob("*")):
        if exclude_backups and "automated-backups" in p.parts:
            continue
        rel = p.relative_to(source)
        tf.add(p, arcname=str(Path(arcname) / rel), recursive=False)


def _pg_dump(out: Path) -> None:
    url = make_url(settings.database_url)
    env = os.environ.copy()
    if url.host: env["PGHOST"] = url.host
    if url.port: env["PGPORT"] = str(url.port)
    if url.database: env["PGDATABASE"] = url.database
    if url.username: env["PGUSER"] = url.username
    if url.password: env["PGPASSWORD"] = url.password
    subprocess.run(["pg_dump", "-Fc", "-f", str(out)], check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def _sqlite_backup(out: Path) -> None:
    raw = settings.database_url.split("///", 1)[-1]
    source = Path(raw)
    if not source.is_absolute():
        source = Path.cwd() / source
    if not source.exists():
        raise RuntimeError(f"SQLite veritabanı bulunamadı: {source}")
    con_src = sqlite3.connect(source)
    con_dst = sqlite3.connect(out)
    try:
        con_src.backup(con_dst)
    finally:
        con_dst.close(); con_src.close()


def create_operational_backup() -> dict:
    root = Path(settings.ops_storage_path)
    backup_root = root / "automated-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = utcnow().strftime("%Y%m%dT%H%M%SZ")
    out = backup_root / stamp
    out.mkdir(parents=True, exist_ok=False)
    db_file = out / ("database.sqlite3" if settings.database_url.startswith("sqlite") else "postgresql.dump")
    if settings.database_url.startswith("sqlite"):
        _sqlite_backup(db_file)
    else:
        _pg_dump(db_file)
    tar_path = out / "persistent-data.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        _safe_tar_add(tf, Path(settings.evidence_storage_path), "evidence")
        _safe_tar_add(tf, Path(settings.scan_storage_path), "scans")
        _safe_tar_add(tf, root, "ops", exclude_backups=True)
    checksums = {db_file.name: _sha256_file(db_file), tar_path.name: _sha256_file(tar_path)}
    manifest = {
        "created_at": utcnow().isoformat(),
        "path": str(out),
        "database_file": db_file.name,
        "persistent_file": tar_path.name,
        "checksums": checksums,
        "host": socket.gethostname(),
        "app_version": APP_VERSION,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "backup-status.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def verify_operational_backup(path: str | Path | None = None) -> dict:
    root = Path(settings.ops_storage_path)
    if path:
        target = Path(path)
    else:
        status = root / "backup-status.json"
        if not status.exists(): raise RuntimeError("backup-status.json bulunamadı")
        target = Path(json.loads(status.read_text(encoding="utf-8"))["path"])
    manifest_path = target / "manifest.json"
    if not manifest_path.exists(): raise RuntimeError("Backup manifest bulunamadı")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    for name, expected in (manifest.get("checksums") or {}).items():
        p = target / name
        if not p.exists(): failures.append({"file": name, "reason": "missing"}); continue
        actual = _sha256_file(p)
        if actual != expected: failures.append({"file": name, "reason": "sha256_mismatch", "actual": actual, "expected": expected})
    tar_path = target / manifest.get("persistent_file", "persistent-data.tar.gz")
    try:
        with tarfile.open(tar_path, "r:gz") as tf:
            # Parsing all members validates gzip/tar structure without extracting.
            tf.getmembers()
    except Exception as exc:
        failures.append({"file": tar_path.name, "reason": f"tar_invalid:{type(exc).__name__}"})
    db_path = target / manifest.get("database_file", "postgresql.dump")
    if db_path.exists() and not settings.database_url.startswith("sqlite"):
        proc = subprocess.run(["pg_restore", "--list", str(db_path)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            failures.append({"file": db_path.name, "reason": "pg_restore_list_failed", "detail": proc.stderr[-500:]})
    result = {
        "verified_at": utcnow().isoformat(),
        "backup_path": str(target),
        "status": "pass" if not failures else "failed",
        "failures": failures,
    }
    (root / "backup-verification-status.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def prune_operational_backups() -> dict:
    root = Path(settings.ops_storage_path) / "automated-backups"
    if not root.exists(): return {"removed": 0}
    cutoff = utcnow() - timedelta(days=max(1, settings.backup_retention_days))
    removed = 0
    for p in sorted(root.iterdir()):
        if not p.is_dir(): continue
        try:
            created = datetime.strptime(p.name, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        except ValueError:
            continue
        if created < cutoff:
            shutil.rmtree(p)
            removed += 1
    return {"removed": removed, "retention_days": settings.backup_retention_days}


def _stage_for_due(due: date, today: date, lookahead: int) -> tuple[str, str, int] | None:
    days = (due - today).days
    if days < 0: return "overdue", "critical", days
    if days == 0: return "due_today", "critical", days
    if days <= 1: return "due_1d", "warning", days
    if days <= 3: return "due_3d", "warning", days
    if days <= lookahead: return "due_7d", "info", days
    return None


def _target(owner: str | None, default_role: str = "quality") -> tuple[str, str]:
    owner = (owner or "").strip()
    return (owner.lower(), "") if "@" in owner else ("", default_role)


def _notification_exists(db: Session, key: str) -> bool:
    return db.scalar(select(m.OperationalNotification.id).where(m.OperationalNotification.dedupe_key == key).limit(1)) is not None


def _emit_due_notification(
    db: Session, *, entity_type: str, entity_id: int, program_id: int | None, title: str,
    due: date, owner: str | None, action_url: str, default_role: str = "quality"
) -> bool:
    stage = _stage_for_due(due, date.today(), max(1, settings.notification_lookahead_days))
    if not stage: return False
    stage_key, severity, days = stage
    key = f"due:{entity_type}:{entity_id}:{due.isoformat()}:{stage_key}"
    if _notification_exists(db, key): return False
    email, role = _target(owner, default_role)
    if days < 0: body = f"Termin {abs(days)} gün geçti."
    elif days == 0: body = "Termin bugün."
    else: body = f"Termine {days} gün kaldı."
    db.add(m.OperationalNotification(
        user_email=email, role_scope=role, program_id=program_id, notification_type="deadline",
        severity=severity, title=title[:255], body=body, action_url=action_url,
        dedupe_key=key, source_entity_type=entity_type, source_entity_id=entity_id,
        status="unread", expires_at=utcnow() + timedelta(days=90),
    ))
    return True


def _emit_below_target_alerts(db: Session) -> int:
    """Onaylı sınavlarda hedef altı kalan Öğrenim Çıktıları için dersin hocasına uygulama içi uyarı üretir (tekrarsız)."""
    from .analytics import exam_analytics
    created = 0
    exams = db.scalars(select(m.Exam).where(m.Exam.status == "approved").order_by(m.Exam.id.desc()).limit(200)).all()
    for exam in exams:
        course = db.get(m.Course, exam.course_id)
        if not course:
            continue
        try:
            an = exam_analytics(db, exam.id)
        except Exception:
            continue
        for lo in an.get("learning_outcomes", []):
            if lo.get("status") != "needs_improvement":
                continue
            key = f"below_target:{exam.id}:{lo['id']}"
            if _notification_exists(db, key):
                continue
            email, role = _target(course.instructor_email, "program_head")
            db.add(m.OperationalNotification(
                user_email=email, role_scope=role, program_id=course.program_id, notification_type="below_target",
                severity="high", title=f"Hedef altı çıktı: {course.code} · {lo['code']}"[:255],
                body=f"{exam.title}: gerçekleşme %{lo['attainment_percent']} (hedef %{lo['target_percent']}). İyileştirme aksiyonu planlayın.",
                action_url="/#courseanalytics", dedupe_key=key, source_entity_type="exam", source_entity_id=exam.id,
                status="unread", expires_at=utcnow() + timedelta(days=120),
            ))
            created += 1
    return created


def generate_due_notifications(db: Session) -> dict:
    lookahead = max(1, settings.notification_lookahead_days)
    max_due = date.today() + timedelta(days=lookahead)
    created = 0

    cycles = db.scalars(select(m.QualityCycle).where(
        m.QualityCycle.due_date.is_not(None), m.QualityCycle.due_date <= max_due,
        ~m.QualityCycle.status.in_(["closed", "completed", "cancelled"]),
    )).all()
    for x in cycles:
        created += int(_emit_due_notification(db, entity_type="quality_cycle", entity_id=x.id, program_id=x.program_id,
            title=f"PUKÖ: {x.title}", due=x.due_date, owner=x.owner, action_url="/#quality360", default_role="program_head"))

    events = db.scalars(select(m.QualityCalendarEvent).where(
        m.QualityCalendarEvent.due_date.is_not(None), m.QualityCalendarEvent.due_date <= max_due,
        ~m.QualityCalendarEvent.status.in_(["closed", "completed", "cancelled"]),
    )).all()
    for x in events:
        created += int(_emit_due_notification(db, entity_type="quality_calendar_event", entity_id=x.id, program_id=x.program_id,
            title=f"Kalite Takvimi: {x.title}", due=x.due_date, owner=x.owner, action_url="/#quality360"))

    requests = db.scalars(select(m.AccreditationDocumentRequest).where(
        m.AccreditationDocumentRequest.due_date.is_not(None), m.AccreditationDocumentRequest.due_date <= max_due,
        ~m.AccreditationDocumentRequest.status.in_(["closed", "answered", "cancelled"]),
    )).all()
    for x in requests:
        app = db.get(m.AccreditationApplication, x.application_id)
        created += int(_emit_due_notification(db, entity_type="accreditation_document_request", entity_id=x.id, program_id=app.program_id if app else None,
            title=f"Akreditasyon Belge Talebi: {x.title}", due=x.due_date, owner=(app.owner if app else ""), action_url="/#quality360"))

    findings = db.scalars(select(m.AccreditationFinding).where(
        m.AccreditationFinding.due_date.is_not(None), m.AccreditationFinding.due_date <= max_due,
        ~m.AccreditationFinding.status.in_(["closed", "resolved", "cancelled"]),
    )).all()
    for x in findings:
        app = db.get(m.AccreditationApplication, x.application_id)
        created += int(_emit_due_notification(db, entity_type="accreditation_finding", entity_id=x.id, program_id=app.program_id if app else None,
            title=f"Akreditasyon Bulgusu: {x.title}", due=x.due_date, owner=x.owner or (app.owner if app else ""), action_url="/#quality360"))

    items = db.scalars(select(m.AssessmentPlanItem).where(
        m.AssessmentPlanItem.due_date.is_not(None), m.AssessmentPlanItem.due_date <= max_due,
        ~m.AssessmentPlanItem.status.in_(["collected", "reviewed", "cancelled"]),
    )).all()
    for x in items:
        plan = db.get(m.AssessmentPlan, x.assessment_plan_id)
        created += int(_emit_due_notification(db, entity_type="assessment_plan_item", entity_id=x.id, program_id=plan.program_id if plan else None,
            title=f"Ölçme Güvence Planı: {x.method_label}", due=x.due_date, owner=x.owner or (plan.owner if plan else ""), action_url="/#assessmentassurance", default_role="program_head"))

    created += _emit_below_target_alerts(db)

    _audit(db, "notification_sweep", "operational_notification", None, {"created": created, "lookahead_days": lookahead})
    return {"created": created, "lookahead_days": lookahead}


def _last_success(db: Session, job_type: str) -> m.OperationalJob | None:
    return db.scalar(select(m.OperationalJob).where(m.OperationalJob.job_type == job_type, m.OperationalJob.status == "succeeded").order_by(m.OperationalJob.finished_at.desc(), m.OperationalJob.id.desc()).limit(1))


def scheduler_tick(db: Session) -> dict:
    now = utcnow()
    recovered = recover_stale_jobs(db)
    generated = generate_due_notifications(db)
    enqueued: list[int] = []

    # Daily integrity scan, scheduled by hour bucket to remain idempotent after restarts.
    last_integrity = _last_success(db, "evidence_integrity_scan")
    integrity_due = not last_integrity or not last_integrity.finished_at or (now - _aware(last_integrity.finished_at)) >= timedelta(hours=max(1, settings.evidence_integrity_interval_hours))
    if integrity_due:
        bucket = now.strftime("%Y%m%d%H")
        job = enqueue_job(db, "evidence_integrity_scan", dedupe_key=f"integrity:{bucket}", priority=20, created_by="system:scheduler")
        enqueued.append(job.id)

    if settings.backup_automation_enabled:
        last_backup = _last_success(db, "backup_create")
        backup_due = not last_backup or not last_backup.finished_at or (now - _aware(last_backup.finished_at)) >= timedelta(hours=max(1, settings.backup_interval_hours))
        if backup_due:
            bucket_hours = max(1, settings.backup_interval_hours)
            bucket = int(now.timestamp() // (bucket_hours * 3600))
            job = enqueue_job(db, "backup_create", dedupe_key=f"backup:{bucket}", priority=50, created_by="system:scheduler")
            enqueued.append(job.id)
    db.commit()
    return {"recovered_stale_jobs": recovered, "notifications": generated, "enqueued_job_ids": sorted(set(enqueued)), "at": now.isoformat()}


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def execute_job(db: Session, job: m.OperationalJob) -> dict:
    try:
        if job.job_type == "evidence_integrity_scan":
            result = scan_evidence_integrity(db)
            for failure in result.get("failures", []):
                _audit(db, "integrity_scan_failure", failure["entity_type"], failure["id"], failure)
        elif job.job_type == "notification_sweep":
            result = generate_due_notifications(db)
        elif job.job_type == "backup_create":
            result = create_operational_backup()
            # Verify the archive immediately. A backup is not successful until checksums/container parse pass.
            verify = verify_operational_backup(result["path"])
            if verify["status"] != "pass":
                raise RuntimeError(f"Backup verification failed: {verify['failures']}")
            result["verification"] = verify
            result["prune"] = prune_operational_backups()
        elif job.job_type == "backup_verify":
            result = verify_operational_backup((job.payload or {}).get("path"))
            if result["status"] != "pass":
                raise RuntimeError(f"Backup verification failed: {result['failures']}")
        elif job.job_type == "backup_prune":
            result = prune_operational_backups()
        else:
            raise RuntimeError(f"Unsupported operational job type: {job.job_type}")
        _job_success(db, job, result)
        return result
    except Exception as exc:
        db.rollback()
        fresh = db.get(m.OperationalJob, job.id)
        if fresh:
            _job_failure(db, fresh, exc)
        raise
