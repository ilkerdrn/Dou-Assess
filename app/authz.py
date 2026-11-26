from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Request
from sqlalchemy import and_, exists, false, func, or_, select
from sqlalchemy.orm import Session

from .config import settings
from . import models as m

ROLE_LABELS = {
    "admin": "Sistem Yöneticisi",
    "quality": "Kalite Müdürü",
    "instructor": "Öğretim Görevlisi",
    "program_head": "Program Başkanı",
    "department_head": "Bölüm Başkanı",
    "faculty_admin": "Fakülte / MYO Yöneticisi",
}
VALID_ROLES = set(ROLE_LABELS)
PILOT_HEADER = "X-DOU-Pilot-User"
_current_user: ContextVar[dict[str, Any] | None] = ContextVar("dou_current_user", default=None)
_jwks_client_cache: tuple[str, type, Any] | None = None


def _role_out(r: m.UserRoleAssignment) -> dict[str, Any]:
    return {
        "id": r.id,
        "role": r.role,
        "role_label": ROLE_LABELS.get(r.role, r.role),
        "program_id": r.program_id,
        "course_id": r.course_id,
        "scope_faculty": r.scope_faculty or "",
        "scope_department": r.scope_department or "",
        "scope_program": r.scope_program or "",
    }


def user_context(db: Session, user: m.AppUser) -> dict[str, Any]:
    roles = db.scalars(
        select(m.UserRoleAssignment)
        .where(m.UserRoleAssignment.user_id == user.id)
        .order_by(m.UserRoleAssignment.id)
    ).all()
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "external_object_id": user.external_object_id,
        "tenant_id": user.tenant_id,
        "auth_source": user.auth_source,
        "is_active": user.is_active,
        "roles": [_role_out(r) for r in roles],
        "role_names": sorted({r.role for r in roles}),
    }


def set_current_user(ctx: dict[str, Any] | None):
    return _current_user.set(ctx)


def reset_current_user(token) -> None:
    _current_user.reset(token)


def current_user() -> dict[str, Any]:
    ctx = _current_user.get()
    if not ctx:
        raise HTTPException(401, "Kullanıcı bağlamı bulunamadı")
    return ctx


def has_role(*roles: str) -> bool:
    names = set(current_user().get("role_names") or [])
    return any(r in names for r in roles)


def require_roles(*roles: str) -> dict[str, Any]:
    ctx = current_user()
    if not set(ctx.get("role_names") or []).intersection(roles):
        raise HTTPException(403, "Bu işlem için yetkiniz yok")
    return ctx


def _entra_urls() -> tuple[str, str]:
    tenant = settings.entra_tenant_id.strip()
    issuer = f"https://login.microsoftonline.com/{tenant}/v2.0"
    jwks = f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys"
    return issuer, jwks


def _jwks_client(jwks_uri: str):
    global _jwks_client_cache
    client_type = PyJWKClient
    if _jwks_client_cache and _jwks_client_cache[0] == jwks_uri and _jwks_client_cache[1] is client_type:
        return _jwks_client_cache[2]
    kwargs = {
        "cache_keys": True,
        "cache_jwk_set": True,
        "lifespan": int(getattr(settings, "jwks_cache_lifespan_seconds", 600)),
        "timeout": int(getattr(settings, "jwks_http_timeout_seconds", 5)),
    }
    try:
        client = client_type(jwks_uri, **kwargs)
    except TypeError:
        # Test doubles / older PyJWT clients may expose a smaller constructor.
        client = client_type(jwks_uri, cache_keys=True)
    _jwks_client_cache = (jwks_uri, client_type, client)
    return client


def validate_entra_access_token(token: str) -> dict[str, Any]:
    if not settings.entra_tenant_id or not settings.entra_audience:
        raise HTTPException(503, "Microsoft Entra yapılandırması tamamlanmamış")
    issuer, jwks_uri = _entra_urls()
    try:
        signing_key = _jwks_client(jwks_uri).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.entra_audience,
            issuer=issuer,
            leeway=30,
            options={"require": ["exp", "iat", "iss", "aud", "tid"]},
        )
    except Exception as exc:
        detail = f": {exc}" if settings.app_env == "pilot" else ""
        raise HTTPException(401, f"Microsoft Entra erişim belirteci doğrulanamadı{detail}")
    if claims.get("tid") != settings.entra_tenant_id:
        raise HTTPException(401, "Microsoft Entra tenant eşleşmedi")
    if str(claims.get("ver") or "2.0") != "2.0":
        raise HTTPException(401, "Bu sürüm yalnız Microsoft Entra v2.0 access token kabul eder")
    if not claims.get("oid"):
        raise HTTPException(401, "Microsoft Entra token içinde oid claim bulunamadı")
    if getattr(settings, "entra_require_delegated_user", False) and not str(claims.get("scp") or "").strip():
        raise HTTPException(401, "Kullanıcı adına verilmiş delegated access token gerekli")
    allowed_clients = tuple(getattr(settings, "entra_allowed_client_ids", ()) or ())
    if allowed_clients:
        actor = str(claims.get("azp") or claims.get("appid") or "").strip()
        if actor not in set(allowed_clients):
            raise HTTPException(401, "Microsoft Entra istemci uygulaması yetkili değil")
    required_scopes = tuple(getattr(settings, "entra_required_scopes", ()) or ())
    if required_scopes:
        granted = set(str(claims.get("scp") or "").split())
        missing = [scope for scope in required_scopes if scope not in granted]
        if missing:
            raise HTTPException(403, "Microsoft Entra API scope yetkisi eksik")
    return claims


def resolve_request_user(db: Session, request: Request) -> dict[str, Any]:
    if settings.auth_required:
        if settings.auth_provider != "entra":
            raise HTTPException(503, "AUTH_REQUIRED açık ancak AUTH_PROVIDER=entra değil")
        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer "):
            raise HTTPException(401, "Bearer access token gerekli")
        claims = validate_entra_access_token(auth.split(" ", 1)[1].strip())
        oid = str(claims["oid"])
        tid = str(claims["tid"])
        email = str(claims.get("preferred_username") or claims.get("email") or claims.get("upn") or "").strip().lower()
        user = db.scalar(select(m.AppUser).where(m.AppUser.external_object_id == oid, m.AppUser.tenant_id == tid))
        if not user and settings.entra_auto_link_by_email and email:
            user = db.scalar(select(m.AppUser).where(m.AppUser.email == email))
            if user and not user.external_object_id:
                user.external_object_id = oid
                user.tenant_id = tid
                user.auth_source = "entra"
        if not user:
            raise HTTPException(403, "Bu Microsoft hesabı DOU Assess kullanıcısı olarak yetkilendirilmemiş")
    else:
        if not getattr(settings, "pilot_auth_enabled", True):
            raise HTTPException(503, "Pilot kimlik doğrulaması bu ortamda devre dışı")
        email = request.headers.get(PILOT_HEADER, "").strip().lower() or settings.pilot_admin_email.lower()
        user = db.scalar(select(m.AppUser).where(m.AppUser.email == email))
        if not user and email == settings.pilot_admin_email.lower() and settings.app_env == "pilot":
            # Test/local pilot bootstrap. Production Entra mode never uses this path.
            user = m.AppUser(email=email, display_name="Pilot Sistem Yöneticisi", auth_source="pilot", is_active=True)
            db.add(user); db.flush()
            db.add(m.UserRoleAssignment(user_id=user.id, role="admin"))
            db.commit()
        if not user:
            raise HTTPException(403, f"Pilot kullanıcı bulunamadı: {email}")
    if not user.is_active:
        raise HTTPException(403, "Kullanıcı pasif durumda")
    now = datetime.now(timezone.utc)
    last_seen = user.last_seen_at
    if last_seen is not None and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    write_interval = max(30, int(getattr(settings, "auth_last_seen_write_seconds", 300)))
    if last_seen is None or now - last_seen >= timedelta(seconds=write_interval):
        user.last_seen_at = now
        db.commit()
    return user_context(db, user)


def _assignment_matches_program(a: dict[str, Any], program: m.Program) -> bool:
    if a.get("program_id") and int(a["program_id"]) == int(program.id):
        return True
    scope_program = str(a.get("scope_program") or "").strip().casefold()
    if scope_program and scope_program in {program.name.casefold(), program.code.casefold()}:
        return True
    scope_department = str(a.get("scope_department") or "").strip().casefold()
    scope_faculty = str(a.get("scope_faculty") or "").strip().casefold()
    if a.get("role") == "department_head" and scope_department:
        return program.department.casefold() == scope_department and (not scope_faculty or program.faculty.casefold() == scope_faculty)
    if a.get("role") == "faculty_admin" and scope_faculty:
        return program.faculty.casefold() == scope_faculty
    return False


def can_access_program(db: Session, program: m.Program, *, write: bool = False, accreditation: bool = False) -> bool:
    ctx = current_user()
    roles = ctx.get("roles") or []
    names = set(ctx.get("role_names") or [])
    if "admin" in names:
        return True
    if "quality" in names:
        return not write or accreditation
    for a in roles:
        role = a.get("role")
        if role in {"program_head", "department_head", "faculty_admin"} and _assignment_matches_program(a, program):
            return True
    if not write:
        # Instructors may read the program that contains one of their courses.
        email = (ctx.get("email") or "").casefold()
        course_ids = {int(a["course_id"]) for a in roles if a.get("role") == "instructor" and a.get("course_id")}
        stmt = select(m.Course.id).where(m.Course.program_id == program.id)
        if email:
            stmt = stmt.where((m.Course.instructor_email.ilike(email)) | (m.Course.id.in_(course_ids) if course_ids else False))
        elif course_ids:
            stmt = stmt.where(m.Course.id.in_(course_ids))
        else:
            return False
        return db.scalar(stmt.limit(1)) is not None
    return False


def can_access_course(db: Session, course: m.Course, *, write: bool = False, accreditation: bool = False) -> bool:
    ctx = current_user()
    names = set(ctx.get("role_names") or [])
    if "admin" in names:
        return True
    if "quality" in names:
        return not write or accreditation
    program = db.get(m.Program, course.program_id)
    if program and any(
        a.get("role") in {"program_head", "department_head", "faculty_admin"} and _assignment_matches_program(a, program)
        for a in (ctx.get("roles") or [])
    ):
        return True
    email = str(ctx.get("email") or "").strip().casefold()
    if email and course.instructor_email.strip().casefold() == email:
        return True
    return any(a.get("role") == "instructor" and a.get("course_id") and int(a["course_id"]) == int(course.id) for a in (ctx.get("roles") or []))


def can_access_exam(db: Session, exam: m.Exam, *, write: bool = False, accreditation: bool = False) -> bool:
    course = db.get(m.Course, exam.course_id)
    return bool(course and can_access_course(db, course, write=write, accreditation=accreditation))




def academic_period_for_course(db: Session, course: m.Course) -> m.AcademicPeriod | None:
    return db.scalar(
        select(m.AcademicPeriod).where(
            m.AcademicPeriod.academic_year == course.academic_year,
            m.AcademicPeriod.term == course.term,
        )
    )


def ensure_course_period_writable(db: Session, course: m.Course) -> None:
    period = academic_period_for_course(db, course)
    if period and period.status in {"locked", "archived"}:
        raise HTTPException(409, f"{period.title} akademik dönemi kilitli. Akademik/operasyonel kayıtlar değiştirilemez; önce dönem kilidi yönetici tarafından açılmalıdır.")


def ensure_period_values_writable(db: Session, academic_year: str, term: str) -> None:
    period = db.scalar(select(m.AcademicPeriod).where(m.AcademicPeriod.academic_year == academic_year, m.AcademicPeriod.term == term))
    if period and period.status in {"locked", "archived"}:
        raise HTTPException(409, f"{period.title} akademik dönemi kilitli. Bu döneme yeni ders/operasyonel kayıt eklenemez.")

def require_program_access(db: Session, program_id: int, *, write: bool = False, accreditation: bool = False) -> m.Program:
    obj = db.get(m.Program, program_id)
    if not obj:
        raise HTTPException(404, "Program bulunamadı")
    if not can_access_program(db, obj, write=write, accreditation=accreditation):
        raise HTTPException(403, "Bu programa erişim yetkiniz yok")
    return obj


def require_course_access(db: Session, course_id: int, *, write: bool = False, accreditation: bool = False) -> m.Course:
    obj = db.get(m.Course, course_id)
    if not obj:
        raise HTTPException(404, "Ders bulunamadı")
    if not can_access_course(db, obj, write=write, accreditation=accreditation):
        raise HTTPException(403, "Bu derse erişim yetkiniz yok")
    if write and not accreditation:
        ensure_course_period_writable(db, obj)
    return obj


def require_exam_access(db: Session, exam_id: int, *, write: bool = False, accreditation: bool = False) -> m.Exam:
    obj = db.get(m.Exam, exam_id)
    if not obj:
        raise HTTPException(404, "Sınav bulunamadı")
    if not can_access_exam(db, obj, write=write, accreditation=accreditation):
        raise HTTPException(403, "Bu sınava erişim yetkiniz yok")
    if write and not accreditation:
        course = db.get(m.Course, obj.course_id)
        if course:
            ensure_course_period_writable(db, course)
    return obj


def _scope_eq(column, value: str):
    """Case-insensitive exact scope comparison that works on PostgreSQL and SQLite."""
    return func.lower(column) == str(value or "").strip().lower()


def visible_program_id_select():
    """Return a SQL select containing program ids visible to the current user.

    6.70 replaces the previous N+1/Python filtering implementation.  The role
    semantics intentionally mirror ``can_access_program(..., write=False)``.
    """
    ctx = current_user()
    roles = ctx.get("roles") or []
    names = set(ctx.get("role_names") or [])
    stmt = select(m.Program.id)
    if names.intersection({"admin", "quality"}):
        return stmt

    conditions = []
    for a in roles:
        role = a.get("role")
        if role not in {"program_head", "department_head", "faculty_admin"}:
            continue
        if a.get("program_id"):
            conditions.append(m.Program.id == int(a["program_id"]))
        scope_program = str(a.get("scope_program") or "").strip()
        if scope_program:
            conditions.append(or_(_scope_eq(m.Program.code, scope_program), _scope_eq(m.Program.name, scope_program)))
        scope_department = str(a.get("scope_department") or "").strip()
        scope_faculty = str(a.get("scope_faculty") or "").strip()
        if role == "department_head" and scope_department:
            c = _scope_eq(m.Program.department, scope_department)
            if scope_faculty:
                c = and_(c, _scope_eq(m.Program.faculty, scope_faculty))
            conditions.append(c)
        if role == "faculty_admin" and scope_faculty:
            conditions.append(_scope_eq(m.Program.faculty, scope_faculty))

    # Instructors may read programs containing one of their own/assigned courses.
    email = str(ctx.get("email") or "").strip().lower()
    instructor_course_ids = {
        int(a["course_id"]) for a in roles
        if a.get("role") == "instructor" and a.get("course_id")
    }
    instructor_conditions = []
    if email:
        instructor_conditions.append(_scope_eq(m.Course.instructor_email, email))
    if instructor_course_ids:
        instructor_conditions.append(m.Course.id.in_(instructor_course_ids))
    if instructor_conditions:
        conditions.append(exists(select(m.Course.id).where(
            m.Course.program_id == m.Program.id,
            or_(*instructor_conditions),
        )))
    return stmt.where(or_(*conditions)) if conditions else stmt.where(false())


def visible_course_id_select():
    """Return a SQL select containing course ids visible to the current user."""
    ctx = current_user()
    roles = ctx.get("roles") or []
    names = set(ctx.get("role_names") or [])
    stmt = select(m.Course.id)
    if names.intersection({"admin", "quality"}):
        return stmt

    conditions = []
    # Academic managers can read every course in their managed program scope.
    manager_program_conditions = []
    for a in roles:
        role = a.get("role")
        if role not in {"program_head", "department_head", "faculty_admin"}:
            continue
        if a.get("program_id"):
            manager_program_conditions.append(m.Program.id == int(a["program_id"]))
        scope_program = str(a.get("scope_program") or "").strip()
        if scope_program:
            manager_program_conditions.append(or_(_scope_eq(m.Program.code, scope_program), _scope_eq(m.Program.name, scope_program)))
        scope_department = str(a.get("scope_department") or "").strip()
        scope_faculty = str(a.get("scope_faculty") or "").strip()
        if role == "department_head" and scope_department:
            c = _scope_eq(m.Program.department, scope_department)
            if scope_faculty:
                c = and_(c, _scope_eq(m.Program.faculty, scope_faculty))
            manager_program_conditions.append(c)
        if role == "faculty_admin" and scope_faculty:
            manager_program_conditions.append(_scope_eq(m.Program.faculty, scope_faculty))
    if manager_program_conditions:
        conditions.append(m.Course.program_id.in_(select(m.Program.id).where(or_(*manager_program_conditions))))

    email = str(ctx.get("email") or "").strip().lower()
    if email:
        conditions.append(_scope_eq(m.Course.instructor_email, email))
    assigned = {
        int(a["course_id"]) for a in roles
        if a.get("role") == "instructor" and a.get("course_id")
    }
    if assigned:
        conditions.append(m.Course.id.in_(assigned))
    return stmt.where(or_(*conditions)) if conditions else stmt.where(false())


def visible_program_ids(db: Session) -> set[int]:
    return set(db.scalars(visible_program_id_select()).all())


def visible_course_ids(db: Session) -> set[int]:
    return set(db.scalars(visible_course_id_select()).all())


def auth_config() -> dict[str, Any]:
    entra_ready = bool(settings.entra_tenant_id and settings.entra_client_id and settings.entra_audience)
    return {
        "app_env": settings.app_env,
        "auth_required": settings.auth_required,
        "auth_provider": settings.auth_provider,
        "pilot_header": PILOT_HEADER if not settings.auth_required else None,
        "integrations": {
            "obs": {
                "mode": "writeback-enabled" if settings.obs_writeback_enabled else "read-only",
                "writeback_enabled": settings.obs_writeback_enabled,
                "endpoint_configured": bool(settings.obs_results_endpoint),
                "token_configured": bool(settings.obs_results_token),
                "production_https_required": settings.app_env == "production",
            }
        },
        "entra": {
            "configured": entra_ready,
            "tenant_id_configured": bool(settings.entra_tenant_id),
            "client_id_configured": bool(settings.entra_client_id),
            "audience_configured": bool(settings.entra_audience),
            "auto_link_by_email": settings.entra_auto_link_by_email,
            "allowed_client_ids_configured": bool(settings.entra_allowed_client_ids),
            "required_scopes_configured": bool(settings.entra_required_scopes),
            "login_scopes_configured": bool(settings.entra_login_scopes),
            "require_delegated_user": settings.entra_require_delegated_user,
            "tenant_id": settings.entra_tenant_id if entra_ready else "",
            "client_id": settings.entra_client_id if entra_ready else "",
            "login_scopes": list(settings.entra_login_scopes) if entra_ready else [],
            "redirect_uri": settings.entra_redirect_uri if entra_ready else "",
            "authority": f"https://login.microsoftonline.com/{settings.entra_tenant_id}" if entra_ready else "",
            "mode": "single-tenant-v2-access-token",
            "login_mode": "authorization-code-pkce",
        },
    }


def can_manage_accreditation_program(db: Session, program_id: int, *, write: bool = True) -> bool:
    program = db.get(m.Program, program_id)
    if not program:
        return False
    ctx = current_user()
    names = set(ctx.get("role_names") or [])
    if "admin" in names or "quality" in names:
        return True
    return any(
        a.get("role") in {"program_head", "department_head", "faculty_admin"} and _assignment_matches_program(a, program)
        for a in (ctx.get("roles") or [])
    )


def can_write_exam_operational(db: Session, exam: m.Exam) -> bool:
    """Exam content/grading/scanning writes: quality is deliberately read-only."""
    return can_access_exam(db, exam, write=True, accreditation=False)


def can_write_exam_accreditation(db: Session, exam: m.Exam) -> bool:
    """Evidence/representative/improvement writes may be performed by quality."""
    return can_access_exam(db, exam, write=True, accreditation=True)


def require_student_access(db: Session, student_id: int, *, write: bool = False) -> m.Student:
    student = db.get(m.Student, student_id)
    if not student:
        raise HTTPException(404, "Öğrenci bulunamadı")
    ctx = current_user()
    names = set(ctx.get("role_names") or [])
    if "admin" in names or ("quality" in names and not write):
        return student
    program = db.get(m.Program, student.program_id)
    if program and can_access_program(db, program, write=write):
        return student
    if not write:
        visible = visible_course_ids(db)
        if visible:
            enrolled = db.scalar(
                select(m.Enrollment.id).where(
                    m.Enrollment.student_id == student.id,
                    m.Enrollment.course_id.in_(visible),
                ).limit(1)
            )
            if enrolled:
                return student
    raise HTTPException(403, "Bu öğrenciye erişim yetkiniz yok")


def require_course_management(db: Session, course_id: int) -> m.Course:
    course = db.get(m.Course, course_id)
    if not course:
        raise HTTPException(404, "Ders bulunamadı")
    program = db.get(m.Program, course.program_id)
    if not program or not can_access_program(db, program, write=True):
        raise HTTPException(403, "Bu dersin akademik ana verisini yönetme yetkiniz yok")
    ensure_course_period_writable(db, course)
    return course
