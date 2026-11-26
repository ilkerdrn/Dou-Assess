import base64
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.services import obs_proliz

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)


def test_671_auth_header_requires_credentials(monkeypatch):
    monkeypatch.setattr(obs_proliz, "settings", replace(obs_proliz.settings, obs_proliz_username="", obs_proliz_password=""))
    with pytest.raises(obs_proliz.ProlizError):
        obs_proliz._auth_header()


def test_671_auth_header_is_http_basic(monkeypatch):
    monkeypatch.setattr(obs_proliz, "settings", replace(obs_proliz.settings, obs_proliz_username="svc-dou-assess", obs_proliz_password="s3cr3t"))
    header = obs_proliz._auth_header()
    assert header.startswith("Basic ")
    decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
    assert decoded == "svc-dou-assess:s3cr3t"


def test_671_probe_rejects_unknown_endpoint():
    with pytest.raises(obs_proliz.ProlizError):
        obs_proliz.probe("not-a-real-endpoint")


def test_671_status_endpoint_reports_configuration():
    r = client.get("/api/integrations/obs/proliz/status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enabled"] is False
    assert "username_configured" in body and "password_configured" in body
    assert "password" not in str(body).lower().replace("password_configured", "")


def test_671_probe_disabled_returns_503(monkeypatch):
    import app.main as main_module
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, obs_proliz_enabled=False))
    r = client.get("/api/integrations/obs/proliz/probe", params={"endpoint": "fakulte"})
    assert r.status_code == 503, r.text


def test_671_probe_success_records_sync_run(monkeypatch):
    import app.main as main_module
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, obs_proliz_enabled=True))
    fake_payload = [{"FakulteKod": "MYO", "FakulteAd": "Meslek Yüksekokulu"}]
    monkeypatch.setattr(obs_proliz, "probe", lambda name: fake_payload)
    r = client.get("/api/integrations/obs/proliz/probe", params={"endpoint": "fakulte"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["endpoint"] == "fakulte"
    assert body["data"] == fake_payload

    runs = client.get("/api/integrations/sync-runs", params={"limit": 5}).json()
    assert any(x["provider"] == "obs-proliz" and x["status"] == "success" for x in runs)


def test_671_probe_failure_records_failed_sync_run(monkeypatch):
    import app.main as main_module
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, obs_proliz_enabled=True))

    def _boom(name):
        raise obs_proliz.ProlizError("Proliz OBS HTTP 403: /Obs/Genel/AkademikDonem")

    monkeypatch.setattr(obs_proliz, "probe", _boom)
    r = client.get("/api/integrations/obs/proliz/probe", params={"endpoint": "akademik_donem"})
    assert r.status_code == 502, r.text

    runs = client.get("/api/integrations/sync-runs", params={"limit": 5}).json()
    assert any(x["provider"] == "obs-proliz" and x["status"] == "failed" for x in runs)
