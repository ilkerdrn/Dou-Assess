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


def sync_teacher_courses(db: Session, profile: TeacherProfile, donem_id: str) -> dict:
    """Pulls the teacher's own courses + enrolled students for one dönem and
    upserts them, exactly like the Excel OBS import does for manual data."""
    stats = {"courses": 0, "students": 0, "enrollments": 0}
    courses = obs_proliz.fetch_akademisyen_verdigi_ders(profile.tck, donem_id)
    course_rows = courses if isinstance(courses, list) else ([courses] if isinstance(courses, dict) else [])

    donemler = obs_proliz.fetch_akademik_donem()
    donem_ad = ""
    for row in (donemler if isinstance(donemler, list) else ([donemler] if isinstance(donemler, dict) else [])):
        if _text(row.get("ID")) == donem_id:
            donem_ad = _text(row.get("AD"))
            break
    academic_year, term = _parse_donem_ad(donem_ad) if donem_ad else (donem_id, "")

    for row in course_rows:
        prog_id = _text(row.get("PROG_ID"))
        prog_ad = _text(row.get("PROG_AD"))
        if not prog_id or not prog_ad:
            continue
        program = db.scalar(select(m.Program).where(m.Program.external_source == "proliz", m.Program.external_id == prog_id))
        if not program:
            code = _text(row.get("FAKULTE_KOD")) + "-" + prog_id
            program = db.scalar(select(m.Program).where(m.Program.code == code))
        if not program:
            program = m.Program(
                code=f"PRZ-{prog_id}", name=prog_ad,
                faculty=_text(row.get("FAKULTE_AD")), department=_text(row.get("BOLUM_AD")),
                external_source="proliz", external_id=prog_id,
            )
            db.add(program); db.flush()
        elif not program.external_id:
            program.external_source = "proliz"; program.external_id = prog_id

        ders_id = _text(row.get("DERS_ID"))
        ders_kod = _text(row.get("DERS_KOD")) or ders_id
        course = db.scalar(select(m.Course).where(m.Course.program_id == program.id, m.Course.code == ders_kod, m.Course.academic_year == academic_year, m.Course.term == term))
        if not course:
            course = m.Course(
                program_id=program.id, code=ders_kod, name=_text(row.get("DERS_AD")) or ders_kod,
                academic_year=academic_year, term=term,
                instructor_email=profile.eposta, instructor_name=profile.display_name,
                external_source="proliz", external_id=ders_id,
            )
            db.add(course); db.flush(); stats["courses"] += 1
        else:
            course.instructor_email = profile.eposta; course.instructor_name = profile.display_name
            if not course.external_id:
                course.external_source = "proliz"; course.external_id = ders_id

        roster = obs_proliz.fetch_akademisyen_verdigi_dersi_alan_ogrenci(profile.tck, donem_id, ders_id)
        roster_rows = roster if isinstance(roster, list) else ([roster] if isinstance(roster, dict) else [])
        for student_row in roster_rows:
            ogr_no = _text(student_row.get("OGR_NO"))
            if not ogr_no:
                continue
            student = db.scalar(select(m.Student).where(m.Student.student_no == ogr_no))
            if not student:
                student = m.Student(program_id=program.id, student_no=ogr_no, full_name=ogr_no, external_source="proliz", external_id=ogr_no)
                db.add(student); db.flush(); stats["students"] += 1
            enrollment = db.scalar(select(m.Enrollment).where(m.Enrollment.course_id == course.id, m.Enrollment.student_id == student.id))
            if not enrollment:
                db.add(m.Enrollment(course_id=course.id, student_id=student.id)); stats["enrollments"] += 1

    return stats


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
