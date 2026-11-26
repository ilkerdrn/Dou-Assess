from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app import authz as authz_module
from app import main as main_module
from app.services import obs_proliz
from app.services import obs_proliz_sync as sync_module

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)


def test_672_hash_obs_password_is_md5_uppercase():
    # Known vector: md5("test") = 098f6bcd4621d373cade4e832627b4f6
    assert obs_proliz.hash_obs_password("test") == "098F6BCD4621D373CADE4E832627B4F6"


def test_672_resolve_teacher_by_sicil_matches_roster(monkeypatch):
    roster = [
        {"TCK": "11111111111", "SICIL_NO": "S100", "AD": "Ayşe", "SOYAD": "Yılmaz", "EPOSTA": "ayse.yilmaz@dogus.edu.tr"},
        {"TCK": "22222222222", "SICIL_NO": "S200", "AD": "Can", "SOYAD": "Demir", "EPOSTA": "can.demir@dogus.edu.tr"},
    ]
    monkeypatch.setattr(obs_proliz, "fetch_akademisyen", lambda tck=None: roster)
    profile = sync_module.resolve_teacher_by_sicil("S200")
    assert profile.tck == "22222222222"
    assert profile.display_name == "Can Demir"
    assert profile.eposta == "can.demir@dogus.edu.tr"


def test_672_resolve_teacher_by_sicil_not_found(monkeypatch):
    monkeypatch.setattr(obs_proliz, "fetch_akademisyen", lambda tck=None: [])
    with pytest.raises(sync_module.ObsLoginError):
        sync_module.resolve_teacher_by_sicil("NOPE")


def test_672_pick_latest_donem_id():
    donemler = [{"ID": "20151", "AD": "2015-2016 Güz"}, {"ID": "20242", "AD": "2024-2025 Bahar"}, {"ID": "20241", "AD": "2024-2025 Güz"}]
    assert sync_module.pick_latest_donem_id(donemler) == "20242"
    assert sync_module.pick_latest_donem_id([]) is None


def test_672_sync_teacher_courses_creates_program_course_student_enrollment(monkeypatch):
    from sqlalchemy.orm import Session
    from app.db import engine as db_engine

    profile = sync_module.TeacherProfile(tck="33333333333", sicil_no="S300", ad="Deniz", soyad="Kaya", eposta="deniz.kaya@dogus.edu.tr")
    monkeypatch.setattr(obs_proliz, "fetch_akademik_donem", lambda: [{"ID": "20241", "AD": "2024-2025 Güz"}])
    monkeypatch.setattr(obs_proliz, "fetch_akademisyen_verdigi_ders", lambda tck, donem_id=None: [{
        "DERS_ID": "900001", "DERS_KOD": "BLP1001", "DERS_AD": "Programlamaya Giriş",
        "PROG_ID": "146", "PROG_AD": "Bilgisayar Programcılığı",
        "FAKULTE_KOD": "66", "FAKULTE_AD": "Tunca Meslek Yüksekokulu", "BOLUM_AD": "Bilgisayar Programcılığı",
    }])
    monkeypatch.setattr(obs_proliz, "fetch_akademisyen_verdigi_dersi_alan_ogrenci", lambda tck, donem_id=None, ders_id=None: [
        {"OGR_NO": "1077102056"}, {"OGR_NO": "1077102057"},
    ])

    with Session(db_engine) as db:
        stats = sync_module.sync_teacher_courses(db, profile, "20241")
        db.commit()
        assert stats == {"courses": 1, "students": 2, "enrollments": 2}

        import app.models as m
        from sqlalchemy import select
        program = db.scalar(select(m.Program).where(m.Program.external_source == "proliz", m.Program.external_id == "146"))
        assert program is not None and program.name == "Bilgisayar Programcılığı"
        course = db.scalar(select(m.Course).where(m.Course.program_id == program.id, m.Course.code == "BLP1001"))
        assert course is not None and course.instructor_email == "deniz.kaya@dogus.edu.tr"
        assert course.academic_year == "2024-2025" and course.term == "Güz"
        enrollments = db.scalars(select(m.Enrollment).where(m.Enrollment.course_id == course.id)).all()
        assert len(enrollments) == 2


def test_672_login_rejected_when_auth_provider_not_obs(monkeypatch):
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, auth_provider="pilot"))
    r = client.post("/api/auth/obs-login", json={"username": "S999", "password": "whatever"})
    assert r.status_code == 503, r.text


def test_672_login_rejected_when_proliz_disabled(monkeypatch):
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, auth_provider="obs", obs_proliz_enabled=False))
    r = client.post("/api/auth/obs-login", json={"username": "S999", "password": "whatever"})
    assert r.status_code == 503, r.text


def test_672_login_rejects_invalid_credentials(monkeypatch):
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, auth_provider="obs", obs_proliz_enabled=True))
    monkeypatch.setattr(obs_proliz, "check_akademik_user", lambda user, pwd: {"SonucDurum": "false", "SonucAciklama": "Yetkisiz kullanıcı (Geçersiz veya yetkisiz kimlik)"})
    r = client.post("/api/auth/obs-login", json={"username": "S999", "password": "wrong"})
    assert r.status_code == 401, r.text
    assert "Yetkisiz" in r.text

    runs = client.get("/api/integrations/sync-runs", params={"limit": 5}).json()
    assert any(x["provider"] == "obs-proliz" and x["mode"] == "login" and x["status"] == "failed" for x in runs)


def test_672_login_success_issues_working_session_token(monkeypatch):
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, auth_provider="obs", obs_proliz_enabled=True, auth_required=True))
    monkeypatch.setattr(authz_module, "settings", replace(authz_module.settings, auth_provider="obs", auth_required=True, obs_jwt_secret="test-secret-01234567890123456789"))

    monkeypatch.setattr(obs_proliz, "check_akademik_user", lambda user, pwd: {"SonucDurum": "true", "SonucAciklama": "Doğrulama Başarılı"})
    monkeypatch.setattr(obs_proliz, "fetch_akademisyen", lambda tck=None: [{"TCK": "44444444444", "SICIL_NO": "S400", "AD": "Elif", "SOYAD": "Şahin", "EPOSTA": "elif.sahin@dogus.edu.tr"}])
    monkeypatch.setattr(obs_proliz, "fetch_akademik_donem", lambda: [{"ID": "20241", "AD": "2024-2025 Güz"}])
    monkeypatch.setattr(obs_proliz, "fetch_akademisyen_verdigi_ders", lambda tck, donem_id=None: [])
    monkeypatch.setattr(obs_proliz, "fetch_akademisyen_verdigi_dersi_alan_ogrenci", lambda tck, donem_id=None, ders_id=None: [])

    r = client.post("/api/auth/obs-login", json={"username": "S400", "password": "real-password"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "elif.sahin@dogus.edu.tr"
    token = body["access_token"]
    assert token

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "elif.sahin@dogus.edu.tr"
    assert "instructor" in me.json()["role_names"]

    unauth = client.get("/api/auth/me")
    assert unauth.status_code == 401, unauth.text
