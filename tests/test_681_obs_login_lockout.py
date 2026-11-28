from dataclasses import replace

from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app import main as main_module
from app.services import obs_proliz

Base.metadata.create_all(engine)
client = TestClient(app)


def _wrong(monkeypatch, calls):
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, auth_provider="obs", obs_proliz_enabled=True))
    def check(user, pwd):
        calls.append(user); return {"SonucDurum": "false", "SonucAciklama": "Yetkisiz kullanıcı"}
    monkeypatch.setattr(obs_proliz, "check_akademik_user", check)


def test_obs_login_locks_after_five_bad_passwords_without_calling_proliz(monkeypatch):
    calls: list[str] = []
    _wrong(monkeypatch, calls)
    user = "LOCK-S1"
    for _ in range(5):
        assert client.post("/api/auth/obs-login", json={"username": user, "password": "x"}).status_code == 401
    assert len(calls) == 5
    r = client.post("/api/auth/obs-login", json={"username": user, "password": "x"})
    assert r.status_code == 429 and "dakika" in r.text
    assert len(calls) == 5  # kilitliyken Proliz'e istek gitmedi (OBS hesabı korunur)
    # başka kullanıcı etkilenmez
    assert client.post("/api/auth/obs-login", json={"username": "LOCK-OTHER", "password": "x"}).status_code == 401


def test_network_errors_do_not_count_toward_lockout(monkeypatch):
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, auth_provider="obs", obs_proliz_enabled=True))
    def boom(user, pwd): raise obs_proliz.ProlizError("bağlantı hatası")
    monkeypatch.setattr(obs_proliz, "check_akademik_user", boom)
    for _ in range(7):
        assert client.post("/api/auth/obs-login", json={"username": "LOCK-NET", "password": "x"}).status_code == 502
