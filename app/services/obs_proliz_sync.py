from __future__ import annotations

"""Maps raw Proliz OBS responses into DOU Assess's own academic structure
(app/models.py), reusing the same external_source="proliz"/external_id upsert
pattern already used by app/services/imports.py for the Excel import path.

Scope of this module: a teacher logs in with their own OBS (Sicil No)
credentials; we verify them against Proliz, resolve their Tck, pull the
courses they teach and the students enrolled in each, and provision a local
DOU Assess account (instructor role) for them — mirroring the existing
_sync_instructor_users_internal() helper in app/main.py.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import obs_proliz
from ..config import settings
from .connectors import CanonCourse, CanonPeriod, CanonStudent, CanonTeacher, sync_canonical
from .. import models as m


class ObsLoginError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class TeacherProfile:
    tck: str
    sicil_no: str
    ad: str
    soyad: str
    eposta: str

    @property
    def display_name(self) -> str:
        return f"{self.ad} {self.soyad}".strip()


def _text(v: object) -> str:
    return str(v).strip() if v is not None else ""


def resolve_teacher_by_sicil(sicil_no: str) -> TeacherProfile:
    """Akademisyen with an empty Tck returns the full staff roster; find the
    record whose SICIL_NO matches the login username."""
    roster = obs_proliz.fetch_akademisyen(None)
    rows = roster if isinstance(roster, list) else ([roster] if isinstance(roster, dict) else [])
    for row in rows:
        if _text(row.get("SICIL_NO")) == sicil_no:
            tck = _text(row.get("TCK"))
            if not tck:
                raise ObsLoginError("Proliz akademisyen kaydında T.C. kimlik no eksik", status_code=502)
            return TeacherProfile(tck=tck, sicil_no=sicil_no, ad=_text(row.get("AD")), soyad=_text(row.get("SOYAD")), eposta=_text(row.get("EPOSTA")))
    raise ObsLoginError("Sicil numarasına karşılık gelen akademisyen kaydı bulunamadı", status_code=502)


def pick_latest_donem_id(donemler: object) -> str | None:
    rows = donemler if isinstance(donemler, list) else ([donemler] if isinstance(donemler, dict) else [])
    ids: list[tuple[int, str]] = []
    for row in rows:
        raw = _text(row.get("ID"))
        if raw.isdigit():
            ids.append((int(raw), raw))
    if not ids:
        return None
    return max(ids, key=lambda x: x[0])[1]


def _parse_donem_ad(donem_ad: str) -> tuple[str, str]:
    """'2024-2025 Güz' -> ('2024-2025', 'Güz'); falls back gracefully."""
    parts = donem_ad.rsplit(" ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return donem_ad.strip(), ""


class ProlizConnector:
    """Proliz OBS -> canonical records (the only Proliz-specific code in the sync path)."""
    source = "proliz"

    def resolve_period(self, period_ref: str) -> CanonPeriod:
        donem_ad = ""
        donemler = obs_proliz.fetch_akademik_donem()
        for row in (donemler if isinstance(donemler, list) else ([donemler] if isinstance(donemler, dict) else [])):
            if _text(row.get("ID")) == period_ref:
                donem_ad = _text(row.get("AD"))
                break
        year, term = _parse_donem_ad(donem_ad) if donem_ad else (period_ref, "")
        return CanonPeriod(academic_year=year, term=term)

    def teacher_courses(self, teacher_ref: str, period_ref: str) -> list[CanonCourse]:
        courses = obs_proliz.fetch_akademisyen_verdigi_ders(teacher_ref, period_ref)
        rows = courses if isinstance(courses, list) else ([courses] if isinstance(courses, dict) else [])
        out = []
        for row in rows:
            ders_id = _text(row.get("DERS_ID")); ders_kod = _text(row.get("DERS_KOD")) or ders_id
            prog_id = _text(row.get("PROG_ID"))
            roster = obs_proliz.fetch_akademisyen_verdigi_dersi_alan_ogrenci(teacher_ref, period_ref, ders_id)
            roster_rows = roster if isinstance(roster, list) else ([roster] if isinstance(roster, dict) else [])
            out.append(CanonCourse(code=ders_kod, name=_text(row.get("DERS_AD")) or ders_kod, external_id=ders_id, program_external_id=prog_id, program_name=_text(row.get("PROG_AD")),
                                   faculty=_text(row.get("FAKULTE_AD")), department=_text(row.get("BOLUM_AD")), program_code=f"PRZ-{prog_id}",
                                   students=[CanonStudent(student_no=_text(r.get("OGR_NO")), external_id=_text(r.get("OGR_NO"))) for r in roster_rows if _text(r.get("OGR_NO"))]))
        return out


def get_connector(name: str | None = None):
    """Registry of institution connectors; add a new university here."""
    return {"proliz": ProlizConnector}.get((name or "proliz").lower(), ProlizConnector)()


def sync_teacher_courses(db: Session, profile: TeacherProfile, donem_id: str, connector=None) -> dict:
    """Pulls the teacher's own courses + enrolled students for one dönem through the connector and upserts them."""
    return sync_canonical(db, connector or get_connector("proliz"), CanonTeacher(email=profile.eposta, display_name=profile.display_name), profile.tck, donem_id)


def provision_teacher_account(db: Session, profile: TeacherProfile) -> m.AppUser:
    """Mirrors app/main.py::_sync_instructor_users_internal for a single
    teacher: find-or-create the AppUser and an instructor role assignment."""
    email = profile.eposta.strip().lower()
    if not email:
        raise ObsLoginError("Proliz akademisyen kaydında e-posta eksik; giriş sağlanamıyor", status_code=502)
    user = db.scalar(select(m.AppUser).where(m.AppUser.email == email))
    if not user:
        user = m.AppUser(email=email, display_name=profile.display_name or email, auth_source="obs", is_active=True)
        db.add(user); db.flush()
    elif not user.is_active:
        raise ObsLoginError("Kullanıcı pasif durumda", status_code=403)
    existing_role = db.scalar(select(m.UserRoleAssignment).where(m.UserRoleAssignment.user_id == user.id, m.UserRoleAssignment.role == "instructor", m.UserRoleAssignment.course_id.is_(None)))
    if not existing_role:
        db.add(m.UserRoleAssignment(user_id=user.id, role="instructor"))
    if email in settings.bootstrap_admin_emails:
        # Operator-configured first administrator (BOOTSTRAP_ADMIN_EMAILS); everyone else is promoted from the Users screen.
        if not db.scalar(select(m.UserRoleAssignment).where(m.UserRoleAssignment.user_id == user.id, m.UserRoleAssignment.role == "admin")):
            db.add(m.UserRoleAssignment(user_id=user.id, role="admin"))
            db.add(m.AuditLog(actor_user_id=user.id, actor_email=email, actor_roles=["admin"], action="bootstrap_admin_granted", entity_type="app_user", entity_id=user.id, payload={"source": "BOOTSTRAP_ADMIN_EMAILS"}))
    return user


def teacher_login_and_sync(db: Session, sicil_no: str, password: str, donem_id: str | None = None) -> tuple[m.AppUser, dict]:
    check = obs_proliz.check_akademik_user(sicil_no, obs_proliz.hash_obs_password(password))
    if not isinstance(check, dict) or str(check.get("SonucDurum", "")).strip().lower() != "true":
        raise ObsLoginError(str(check.get("SonucAciklama")) if isinstance(check, dict) else "Proliz OBS kimlik doğrulaması başarısız")

    profile = resolve_teacher_by_sicil(sicil_no)
    resolved_donem_id = donem_id or pick_latest_donem_id(obs_proliz.fetch_akademik_donem())
    stats: dict = {"courses": 0, "students": 0, "enrollments": 0, "donem_id": resolved_donem_id}
    if resolved_donem_id:
        stats.update(sync_teacher_courses(db, profile, resolved_donem_id))
        stats["donem_id"] = resolved_donem_id
    user = provision_teacher_account(db, profile)
    return user, stats
