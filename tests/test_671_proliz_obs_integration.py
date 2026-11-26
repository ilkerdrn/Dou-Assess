import base64
import json
from dataclasses import replace
from urllib.parse import urlsplit, parse_qs

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.services import obs_proliz

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _mock_urlopen(captured: list, body: object):
    def _urlopen(req, timeout=None):
        captured.append(req)
        return _FakeResponse(json.dumps(body).encode("utf-8"))
    return _urlopen


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


def test_671_check_akademik_user_sends_credentials_as_query_params(monkeypatch):
    monkeypatch.setattr(obs_proliz, "settings", replace(obs_proliz.settings, obs_proliz_username="svc", obs_proliz_password="svc-pass"))
    captured: list = []
    monkeypatch.setattr(obs_proliz.urlrequest, "urlopen", _mock_urlopen(captured, True))
    result = obs_proliz.check_akademik_user("teacher@dogus.edu.tr", "teacher-pass")
    assert result is True
    assert len(captured) == 1
    req = captured[0]
    parsed = urlsplit(req.full_url)
    qs = parse_qs(parsed.query)
    assert qs["userName"] == ["teacher@dogus.edu.tr"]
    assert qs["Pass"] == ["teacher-pass"]
    # The service account authenticates the call itself; it must not leak into the URL.
    assert "svc-pass" not in req.full_url
    assert req.headers["Authorization"].startswith("Basic ")


def test_671_fetch_akademisyen_verdigi_dersi_alan_ogrenci_builds_expected_query(monkeypatch):
    monkeypatch.setattr(obs_proliz, "settings", replace(obs_proliz.settings, obs_proliz_username="svc", obs_proliz_password="svc-pass"))
    captured: list = []
    monkeypatch.setattr(obs_proliz.urlrequest, "urlopen", _mock_urlopen(captured, [{"OgrenciNo": "20260001"}]))
    result = obs_proliz.fetch_akademisyen_verdigi_dersi_alan_ogrenci("12345678901", donem_id="2026-2027-Guz", ders_id="BLP1001")
    assert result == [{"OgrenciNo": "20260001"}]
    qs = parse_qs(urlsplit(captured[0].full_url).query)
    assert qs["Tck"] == ["12345678901"]
    assert qs["DonemId"] == ["2026-2027-Guz"]
    assert qs["DersId"] == ["BLP1001"]
