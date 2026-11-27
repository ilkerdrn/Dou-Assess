from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, APP_VERSION, EXPECTED_SCHEMA_REVISION
from app.release import build_metadata

ROOT = Path(__file__).resolve().parents[1]


def test_release_metadata_is_canonical():
    meta = build_metadata()
    assert APP_VERSION == "6.70-production-hardening"
    assert meta["version"] == APP_VERSION
    assert meta["schema_expected"] == EXPECTED_SCHEMA_REVISION == "0046_exam_student_extra_time"
    assert meta["asset_version"] == "6.70-production-hardening"


def test_health_exposes_build_metadata_in_all_environments():
    client = TestClient(app)
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["version"] == APP_VERSION
    assert body["schema_expected"] == EXPECTED_SCHEMA_REVISION
    assert "build_sha" in body and "build_time" in body


def test_deploy_scripts_use_release_env():
    verify = (ROOT / "Verify-Server.sh").read_text(encoding="utf-8")
    upgrade = (ROOT / "Upgrade-Server.sh").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert 'source "$ROOT/RELEASE.env"' in verify
    assert 'source "$ROOT/RELEASE.env"' in upgrade
    assert "COPY RELEASE.env ./" in dockerfile
    assert "6.70-production-hardening" in html
