from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import uuid

from fastapi.testclient import TestClient

from app import models as m
from app.db import Base, SessionLocal, engine
from app.main import app, APP_VERSION, EXPECTED_SCHEMA_REVISION
from app.services.operations import claim_next_job, execute_job, create_operational_backup, verify_operational_backup
from app.config import settings

Base.metadata.create_all(engine)
client = TestClient(app)
SUFFIX = uuid.uuid4().hex[:8]


def test_668_release_migration_worker_scheduler_contract():
    assert APP_VERSION == "6.70-production-hardening"
    assert EXPECTED_SCHEMA_REVISION == "0043_response_grade_revisions"
    root = Path(__file__).resolve().parents[1]
    migration = (root / "migrations/versions/0040_operations_automation.py").read_text(encoding="utf-8")
    assert 'revision = "0040_operations_automation"' in migration
    assert 'down_revision = "0039_evidence_integrity_security"' in migration
    compose = (root / "docker-compose.production.yml").read_text(encoding="utf-8")
    assert "  worker:" in compose and '["python", "-m", "app.worker"]' in compose
    assert "  scheduler:" in compose and '["python", "-m", "app.scheduler"]' in compose
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    assert "postgresql-client" in dockerfile
    for script_name in ["Install-Server.sh", "Upgrade-Server.sh", "Backup-Server.sh", "Restore-Server.sh"]:
        script = (root / script_name).read_text(encoding="utf-8")
        assert 'docker compose -p "$PROJECT_NAME"' in script
    restore = (root / "Restore-Server.sh").read_text(encoding="utf-8")
    assert "stop api worker scheduler nginx migrate" in restore
    assert "up -d api worker scheduler nginx" in restore


def test_668_job_queue_claim_execute_and_pagination():
    with SessionLocal() as db:
        for old in db.query(m.OperationalJob).filter(m.OperationalJob.status.in_(["queued", "running"])).all():
            old.status = "cancelled"
        db.commit()
    r = client.post("/api/operations/jobs/integrity-scan")
    assert r.status_code == 200, r.text
    queued = r.json(); assert queued["status"] == "queued"
    with SessionLocal() as db:
        job = db.get(m.OperationalJob, queued["id"])
        claimed = claim_next_job(db, "pytest-worker")
        assert claimed and claimed.id == job.id and claimed.status == "running"
        execute_job(db, claimed)
    done = client.get(f"/api/operations/jobs/{queued['id']}")
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "succeeded"
    listed = client.get("/api/operations/jobs?limit=1&offset=0")
    assert listed.status_code == 200 and listed.json()["limit"] == 1
    assert listed.json()["total"] >= 1 and len(listed.json()["items"]) <= 1


def test_668_scheduler_creates_deduplicated_deadline_notification():
    code = f"OPS-{SUFFIX}"
    with SessionLocal() as db:
        p = m.Program(code=code, name="Operations Program", faculty="MYO", department="Bilgisayar")
        db.add(p); db.flush()
        cycle = m.QualityCycle(
            program_id=p.id, academic_year="2026-2027", criterion_code="3.1",
            title=f"PUKO {SUFFIX}", owner="pilot-admin@local",
            due_date=date.today() + timedelta(days=1), status="planned",
        )
        db.add(cycle); db.commit(); cycle_id = cycle.id
    first = client.post("/api/operations/scheduler/run")
    assert first.status_code == 200, first.text
    inbox = client.get("/api/operations/notifications?status=unread&limit=200")
    assert inbox.status_code == 200, inbox.text
    matches = [x for x in inbox.json()["items"] if x["source_entity_type"] == "quality_cycle" and x["source_entity_id"] == cycle_id]
    assert len(matches) == 1 and matches[0]["severity"] in {"warning", "critical"}
    second = client.post("/api/operations/scheduler/run")
    assert second.status_code == 200
    inbox2 = client.get("/api/operations/notifications?status=unread&limit=200").json()["items"]
    matches2 = [x for x in inbox2 if x["source_entity_type"] == "quality_cycle" and x["source_entity_id"] == cycle_id]
    assert len(matches2) == 1
    marked = client.patch(f"/api/operations/notifications/{matches2[0]['id']}/read")
    assert marked.status_code == 200 and marked.json()["status"] == "read"


def test_668_operations_summary_and_manual_backup_enqueue():
    summary = client.get("/api/operations/summary")
    assert summary.status_code == 200, summary.text
    data = summary.json()
    assert {"queued", "running", "failed"} <= set(data["jobs"])
    assert "automation" in data and "backup_enabled" in data["automation"]
    backup = client.post("/api/operations/jobs/backup")
    assert backup.status_code == 200, backup.text
    assert backup.json()["job_type"] == "backup_create"


def test_668_frontend_operations_center_uses_async_jobs():
    root = Path(__file__).resolve().parents[1]
    html = (root / "app/static/index.html").read_text(encoding="utf-8")
    js = (root / "app/static/app.js").read_text(encoding="utf-8")
    assert "OPERATIONS &amp; AUTOMATION" in html
    assert "queueBackupNow" in html and "runSchedulerNow" in html
    assert "notificationBtn" in html and "notificationModal" in html
    assert "/api/operations/jobs/integrity-scan" in js
    assert "/api/operations/notifications" in js and "refreshNotificationBadge" in js
    assert "pollOperationalJob" in js


def test_668_backup_artifact_is_verified_before_success(tmp_path):
    old_ops, old_ev, old_scan = settings.ops_storage_path, settings.evidence_storage_path, settings.scan_storage_path
    try:
        object.__setattr__(settings, "ops_storage_path", str(tmp_path / "ops"))
        object.__setattr__(settings, "evidence_storage_path", str(tmp_path / "evidence"))
        object.__setattr__(settings, "scan_storage_path", str(tmp_path / "scans"))
        Path(settings.evidence_storage_path).mkdir(parents=True); Path(settings.scan_storage_path).mkdir(parents=True)
        (Path(settings.evidence_storage_path) / "e.txt").write_text("evidence", encoding="utf-8")
        (Path(settings.scan_storage_path) / "s.txt").write_text("scan", encoding="utf-8")
        result = create_operational_backup()
        verified = verify_operational_backup(result["path"])
        assert verified["status"] == "pass" and not verified["failures"]
        assert (Path(result["path"]) / "manifest.json").is_file()
        assert (Path(settings.ops_storage_path) / "backup-status.json").is_file()
    finally:
        object.__setattr__(settings, "ops_storage_path", old_ops)
        object.__setattr__(settings, "evidence_storage_path", old_ev)
        object.__setattr__(settings, "scan_storage_path", old_scan)
