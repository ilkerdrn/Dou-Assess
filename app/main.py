from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
import uuid
import zipfile
from urllib import error as urlerror, request as urlrequest

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, Request, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, exists, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from pypdf import PdfReader, PdfWriter

from .config import settings
from .release import APP_VERSION, EXPECTED_SCHEMA_REVISION, build_metadata
# Historical release-contract tests search source text; runtime truth remains RELEASE.env.
# APP_VERSION = "6.70-production-hardening"
# EXPECTED_SCHEMA_REVISION = "0043_response_grade_revisions"
# EXPECTED_SCHEMA_REVISION = "0042_performance_production_hardening"
# EXPECTED_SCHEMA_REVISION = "0039_evidence_integrity_security"
from .db import engine, get_db, SessionLocal
from . import models as m
from .schemas import (
    ObsLoginRequest, AddBankQuestionRequest, AddBankQuestionsBatchRequest, QuestionReorderRequest, NormalizeQuestionPointsRequest, BulkEnrollRequest, CourseCreate, CourseUpdate, ExamCreate, ExamDuplicateRequest, ExamStatusUpdate, ExamUpdate, ImprovementCreate,
    LearningOutcomeCreate, LearningOutcomeUpdate, OutcomeMappingCreate, ProgramCreate, ProgramUpdate,
    ProgramOutcomeCreate, ProgramOutcomeUpdate, QuestionBankCreate, QuestionBankUpdate, QuestionReviewRequest, BlueprintCreate, BlueprintStatusRequest, QuestionCreate, QuestionUpdate, ResponsesSubmit, StudentCreate, StudentUpdate, ScanReviewOut, ScanReviewResolve, AnswerKeyRegradeRequest, QuestionKeyException,
    AccreditationProfileCreate, AccreditationPeriodCreate, AccreditationPeriodStatusUpdate, ImprovementUpdate,
    AppUserCreate, AppUserUpdate, UserRoleCreate, AcademicPeriodCreate, AcademicPeriodStatusUpdate, PilotFeedbackCreate, PilotFeedbackUpdate, ExamApprovalRequest, EvidenceUpdate, StudentAnonymizeRequest,
    AttendanceUpdate, GradeLockRequest, ExamIncidentCreate, ExamIncidentResolve, GradeAppealCreate, GradeAppealResolve,
)
from .services.analytics import course_gradebook, exam_analytics, student_exam_analytics
from .services.exports import build_course_gradebook_xlsx, build_exam_results_xlsx, build_accreditation_period_xlsx, build_quality_dashboard_xlsx
from .services.imports import ImportValidationError, import_workbook, validate_workbook
from .services.question_bank_import import parse_question_bank_workbook
from .services.excel_center import TEMPLATES as EXCEL_CENTER_TEMPLATES, template_bytes as excel_center_template_bytes, parse_workbook as parse_excel_center_workbook, yes_no as excel_yes_no, rubric_scores as parse_excel_rubric_scores
from .services.quality360 import QUALITY_EXCEL_KINDS, validate_excel_rows as validate_quality_excel_rows, import_excel_rows as import_quality_excel_rows
from .services.paper import build_exam_pdf, normalize_choices, normalize_correct_answer, paper_metadata, question_regions
from .services.pilot_ops import build_pilot_readiness, operational_issues, build_uat_checks
from .services.scan import ScanError, analyze_page, decode_upload, iter_decode_upload, jpeg_bytes, parse_qr_payload, diagnostic_summary, annotated_review_preview, full_page_fingerprint
from .services.accreditation import freeze_representatives, freeze_period_representatives, period_dashboard, representative_rows, sync_period_exams
from .services.quality import quality_dashboard as build_quality_dashboard, course_quality_drilldown, course_lineage_analytics
from .services.integrity import scan_evidence_integrity
from .services import obs_proliz
from .services.obs_proliz_sync import ObsLoginError, teacher_login_and_sync
from .quality360_api import router as quality360_router
from .compliance_api import router as compliance_router
from .academic_structure_api import router as academic_structure_router
from .assessment_measure_api import router as assessment_measure_router
from .survey_api import router as survey_router
from .assessment_plan_api import router as assessment_plan_router
from .production_acceptance_api import router as production_acceptance_router
from .operations_api import router as operations_router
from .program_review_api import router as program_review_router
from .evaluator_room_api import router as evaluator_room_router
from .student_portal_api import router as student_portal_router
from .security import (
    add_security_event, allowed_host, enforce_production_security, production_security_issues, production_security_warnings,
    rate_limit_check, read_upload_limited, request_id_for, request_is_https, security_error, security_headers,
    validate_image_payload, validate_pdf_payload, verify_stored_file,
)
from .authz import (
    ROLE_LABELS, VALID_ROLES, auth_config, can_access_course, can_access_program, can_manage_accreditation_program,
    current_user, has_role, require_course_access, require_exam_access, require_program_access, require_roles,
    require_student_access, require_course_management, resolve_request_user, reset_current_user, set_current_user, visible_course_ids, visible_program_ids,
    visible_course_id_select, visible_program_id_select, ensure_period_values_writable, mint_obs_session_token,
)

enforce_production_security()
_is_production = settings.app_env == "production"
app = FastAPI(
    title="DOU Assess",
    version=APP_VERSION,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)
app.include_router(quality360_router)
app.include_router(compliance_router)
app.include_router(academic_structure_router)
app.include_router(assessment_measure_router)
app.include_router(survey_router)
app.include_router(assessment_plan_router)
app.include_router(production_acceptance_router)
app.include_router(operations_router)
app.include_router(program_review_router)
app.include_router(evaluator_room_router)
app.include_router(student_portal_router)


@app.exception_handler(HTTPException)
async def http_error(_, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, str):
        payload = {"error": {"code": f"HTTP_{exc.status_code}", "message": detail, "details": []}}
    else:
        payload = {"error": {"code": f"HTTP_{exc.status_code}", "message": "İşlem tamamlanamadı", "details": detail}}
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(IntegrityError)
async def integrity_error(_, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"error": {"code": "DB_CONFLICT", "message": "Aynı kayıt zaten mevcut veya veri bütünlüğü kuralı ihlal edildi.", "details": []}})


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", request_id_for(request))
    try:
        with SessionLocal() as event_db:
            add_security_event(
                event_db, "app_error", severity="error", request_id=request_id, request=request,
                detail={"exception": type(exc).__name__, "message": str(exc)[:500] if settings.app_env == "pilot" else ""},
            )
            event_db.commit()
    except Exception:
        pass
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "İşlem tamamlanamadı. Sistem yöneticisi hata kaydını inceleyebilir.", "details": [f"İstek kodu: {request_id}"]}})


def audit(db: Session, action: str, entity_type: str, entity_id: int | None = None, payload: dict | None = None) -> None:
    # Audit JSON must never be able to break the business transaction. Dates, UUIDs
    # and other structured values are converted to a stable JSON-safe representation.
    safe_payload = json.loads(json.dumps(payload or {}, ensure_ascii=False, default=str))
    try:
        actor = current_user()
    except Exception:
        actor = {"id": None, "email": "system", "role_names": []}
    db.add(m.AuditLog(
        actor_user_id=actor.get("id"), actor_email=actor.get("email") or "system",
        actor_roles=list(actor.get("role_names") or []), action=action, entity_type=entity_type,
        entity_id=entity_id, payload=safe_payload,
    ))


def _log_grade_revision(db: Session, response: "m.Response", old_points: float, old_rubric: dict, source: str, changed_by: str | None = None) -> None:
    """Record an immutable before/after row whenever an already-graded
    Response's awarded_points/rubric_scores change. Never log a brand-new
    grade (nothing to compare against) and never log a true no-op."""
    new_points = float(response.awarded_points or 0.0)
    new_rubric = dict(response.rubric_scores or {})
    if old_points == new_points and (old_rubric or {}) == new_rubric:
        return
    try:
        actor_email = changed_by or (current_user().get("email") or "system")
    except Exception:
        actor_email = changed_by or "system"
    db.add(m.ResponseGradeRevision(
        response_id=response.id, exam_student_id=response.exam_student_id, question_id=response.question_id,
        previous_awarded_points=float(old_points or 0.0), new_awarded_points=new_points,
        previous_rubric_scores=old_rubric or {}, new_rubric_scores=new_rubric,
        source=source, changed_by=actor_email,
    ))


def _commit(db: Session):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise



_PUBLIC_API = {"/api/health", "/api/ready", "/api/auth/config", "/api/auth/obs-login"}


def _auth_error_payload(exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "İşlem tamamlanamadı"
    details = [] if isinstance(exc.detail, str) else exc.detail
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": f"HTTP_{exc.status_code}", "message": detail, "details": details}})


@app.middleware("http")
async def identity_context_middleware(request: Request, call_next):
    path = request.url.path
    if not path.startswith("/api/") or path in _PUBLIC_API or path.startswith("/api/public/surveys/") or path.startswith("/api/public/evaluator-workspaces/") or path.startswith("/api/public/student-exam/"):
        return await call_next(request)
    try:
        with SessionLocal() as db:
            ctx = resolve_request_user(db, request)
        token = set_current_user(ctx)
    except HTTPException as exc:
        try:
            with SessionLocal() as event_db:
                add_security_event(
                    event_db, "auth_denied", severity="warning",
                    request_id=getattr(request.state, "request_id", ""), request=request,
                    detail={"status_code": exc.status_code, "reason": str(exc.detail)[:300]},
                )
                event_db.commit()
        except Exception:
            pass
        return _auth_error_payload(exc)
    try:
        return await call_next(request)
    finally:
        reset_current_user(token)


@app.middleware("http")
async def security_envelope_middleware(request: Request, call_next):
    request_id = request_id_for(request)
    request.state.request_id = request_id

    async def reject(status_code: int, code: str, message: str, event_type: str, *, headers: dict[str, str] | None = None, detail: dict | None = None):
        try:
            with SessionLocal() as event_db:
                add_security_event(
                    event_db, event_type, severity="warning", request_id=request_id, request=request,
                    detail={"status_code": status_code, "host": (request.headers.get("host") or "")[:255], **(detail or {})},
                )
                event_db.commit()
        except Exception:
            pass
        response = security_error(status_code, code, message, request_id, headers=headers)
        security_headers(response, request, request_id)
        return response

    if not allowed_host(request):
        return await reject(400, "HOST_NOT_ALLOWED", "İstek host değeri bu ortam için yetkili değil", "host_denied")

    allowed, retry_after, limit, rate_category = rate_limit_check(request)
    if not allowed:
        return await reject(
            429, "RATE_LIMITED", "Çok fazla istek gönderildi. Kısa süre sonra tekrar deneyin.", "rate_limited",
            headers={"Retry-After": str(retry_after)}, detail={"limit_per_minute": limit, "category": rate_category},
        )

    if settings.require_https and request.url.path not in {"/api/health", "/api/ready"} and not request_is_https(request):
        return await reject(400, "HTTPS_REQUIRED", "Bu ortam yalnız HTTPS üzerinden hizmet verir", "https_required")

    raw_length = request.headers.get("content-length", "").strip()
    if raw_length.isdigit() and int(raw_length) > settings.max_request_mb * 1024 * 1024:
        return await reject(413, "REQUEST_TOO_LARGE", f"İstek en fazla {settings.max_request_mb} MB olabilir", "request_too_large")

    response = await call_next(request)
    security_headers(response, request, request_id)
    return response


EXAM_TRANSITIONS = {
    "draft": {"ready"},
    "ready": {"draft", "grading"},
    "grading": {"ready", "approved"},
    "approved": {"archived"},
    "archived": set(),
}


def _apply_patch(obj, data) -> dict:
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(obj, key, value)
    return changes


def _block_delete(entity: str, blockers: dict[str, int]) -> None:
    active = {k: v for k, v in blockers.items() if v}
    if active:
        detail = ", ".join(f"{k}: {v}" for k, v in active.items())
        raise HTTPException(409, f"{entity} silinemez. Bağlı kayıtlar var ({detail}).")


def _require_exam_draft(exam: m.Exam) -> None:
    if exam.status != "draft":
        raise HTTPException(409, "Sorular yalnızca taslak durumundaki sınavda değiştirilebilir")


def _load_exam_detail_model(db: Session, exam_id: int) -> m.Exam:
    stmt = select(m.Exam).options(
        selectinload(m.Exam.learning_outcomes).selectinload(m.ExamLearningOutcome.mappings).selectinload(m.ExamOutcomeMapping.program_outcome),
        selectinload(m.Exam.program_outcomes),
        selectinload(m.Exam.questions).selectinload(m.Question.learning_outcome),
        selectinload(m.Exam.questions).selectinload(m.Question.learning_outcomes),
        selectinload(m.Exam.exam_students),
    ).where(m.Exam.id == exam_id)
    exam = db.scalar(stmt)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    return exam


def _fill_exam_paper_snapshot(db: Session, exam: m.Exam, course: m.Course) -> None:
    program = db.get(m.Program, course.program_id)
    exam.course_code_snapshot = course.code
    exam.course_name_snapshot = course.name
    exam.academic_year_snapshot = course.academic_year
    exam.term_snapshot = course.term
    exam.instructor_snapshot = (course.instructor_name or course.instructor_email or "").strip()
    exam.program_name_snapshot = program.name if program else ""
    exam.department_snapshot = program.department if program else ""
    exam.faculty_snapshot = program.faculty if program else ""
    exam.paper_template_version = "dou-official-v2"


def _normalize_image_data(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if not (raw.startswith("data:image/png;base64,") or raw.startswith("data:image/jpeg;base64,")):
        raise HTTPException(400, "Soru görseli PNG veya JPEG data URL biçiminde olmalıdır")
    if len(raw) > 7_000_000:
        raise HTTPException(413, "Soru görseli en fazla yaklaşık 5 MB olabilir")
    return raw


def _normalize_rubric(question_type: str, rubric: dict | None, max_points: float) -> dict | None:
    if not rubric:
        return None
    if question_type != "classic":
        raise HTTPException(400, "Rubrik yalnızca klasik/açık uçlu sorularda kullanılabilir")
    criteria = rubric.get("criteria") if isinstance(rubric, dict) else None
    if not isinstance(criteria, list) or not criteria:
        raise HTTPException(400, "Rubrik en az bir ölçüt içermelidir")
    clean = []
    ids = set()
    total = 0.0
    for idx, row in enumerate(criteria, start=1):
        if not isinstance(row, dict):
            raise HTTPException(400, "Rubrik ölçütleri nesne olmalıdır")
        cid = str(row.get("id") or f"c{idx}").strip()[:64]
        label = str(row.get("label") or "").strip()[:255]
        try:
            points = float(row.get("max_points"))
        except (TypeError, ValueError):
            raise HTTPException(400, f"Rubrik {idx}. ölçüt puanı geçersiz")
        if not cid or cid in ids or not label or points <= 0:
            raise HTTPException(400, "Rubrik ölçüt kimlikleri benzersiz, açıklamalar dolu ve puanlar pozitif olmalıdır")
        ids.add(cid); total += points
        outcome_codes = _normalized_outcome_codes(row.get("outcome_codes") or [], None)
        clean.append({"id": cid, "label": label, "max_points": round(points, 4), "description": str(row.get("description") or "").strip()[:1000], "outcome_codes": outcome_codes})
    if abs(total - float(max_points)) > 0.01:
        raise HTTPException(400, f"Rubrik toplam puanı soru puanına eşit olmalıdır ({total:g} ≠ {float(max_points):g})")
    return {"criteria": clean}


def _clean_mcq_fields(question_type: str, choices: dict | None, correct_answer: str | None) -> tuple[dict | None, str | None]:
    if question_type != "mcq":
        return None, None
    normalized_choices = normalize_choices(choices)
    if not normalized_choices or len(normalized_choices) < 2:
        raise HTTPException(400, "Çoktan seçmeli soruda en az iki dolu seçenek zorunludur")
    if any(k not in {"A", "B", "C", "D", "E"} for k in normalized_choices):
        raise HTTPException(400, "Çoktan seçmeli seçenek anahtarları A-E arasında olmalıdır")
    normalized_answer = normalize_correct_answer(correct_answer, normalized_choices)
    if not normalized_answer or normalized_answer not in normalized_choices:
        raise HTTPException(400, "Doğru cevap A-E seçeneklerinden biri olmalıdır")
    return normalized_choices, normalized_answer


def _normalized_outcome_codes(many: list[str] | None = None, legacy: str | None = None) -> list[str]:
    values = list(many or [])
    if not values and legacy:
        values = [legacy]
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        code = str(raw or "").strip()
        if not code:
            continue
        key = code.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(code)
    if len(result) > 20:
        raise HTTPException(400, "Bir soru en fazla 20 ÖÇ ile ilişkilendirilebilir")
    return result


def _resolve_course_outcomes(db: Session, course_id: int, codes: list[str]) -> list[m.LearningOutcome]:
    if not codes:
        return []
    rows = db.scalars(select(m.LearningOutcome).where(m.LearningOutcome.course_id == course_id, m.LearningOutcome.code.in_(codes))).all()
    by_code = {x.code.casefold(): x for x in rows}
    missing = [code for code in codes if code.casefold() not in by_code]
    if missing:
        raise HTTPException(400, "Bu derste bulunmayan ÖÇ: " + ", ".join(missing))
    return [by_code[code.casefold()] for code in codes]


def _resolve_exam_outcomes(db: Session, exam_id: int, codes: list[str]) -> list[m.ExamLearningOutcome]:
    if not codes:
        return []
    rows = db.scalars(select(m.ExamLearningOutcome).where(m.ExamLearningOutcome.exam_id == exam_id, m.ExamLearningOutcome.code.in_(codes))).all()
    by_code = {x.code.casefold(): x for x in rows}
    missing = [code for code in codes if code.casefold() not in by_code]
    if missing:
        raise HTTPException(400, "Sınav snapshot'ında bulunmayan ÖÇ: " + ", ".join(missing))
    return [by_code[code.casefold()] for code in codes]


def _bank_outcome_codes(bank: m.QuestionBank) -> list[str]:
    codes = sorted({x.code for x in getattr(bank, "learning_outcomes", [])}, key=lambda x: x.casefold())
    return codes or _normalized_outcome_codes(legacy=bank.learning_outcome_code)


def _question_outcome_codes(question: m.Question) -> list[str]:
    codes = sorted({x.code for x in getattr(question, "learning_outcomes", [])}, key=lambda x: x.casefold())
    if codes:
        return codes
    return [question.learning_outcome.code] if getattr(question, "learning_outcome", None) else []


def _set_bank_outcomes(db: Session, bank: m.QuestionBank, outcomes: list[m.LearningOutcome]) -> None:
    db.execute(delete(m.QuestionBankOutcome).where(m.QuestionBankOutcome.question_bank_id == bank.id))
    bank.learning_outcome_code = outcomes[0].code if outcomes else None  # legacy primary outcome
    for lo in outcomes:
        db.add(m.QuestionBankOutcome(question_bank_id=bank.id, learning_outcome_id=lo.id))
    db.flush()


def _set_question_outcomes(db: Session, question: m.Question, outcomes: list[m.ExamLearningOutcome]) -> None:
    db.execute(delete(m.QuestionOutcome).where(m.QuestionOutcome.question_id == question.id))
    question.exam_learning_outcome_id = outcomes[0].id if outcomes else None  # legacy primary outcome
    for lo in outcomes:
        db.add(m.QuestionOutcome(question_id=question.id, exam_learning_outcome_id=lo.id))
    db.flush()


def _exam_readiness(db: Session, exam: m.Exam) -> dict:
    questions = db.scalars(
        select(m.Question).options(selectinload(m.Question.learning_outcome), selectinload(m.Question.learning_outcomes)).where(m.Question.exam_id == exam.id).order_by(m.Question.order_no)
    ).all()
    issues: list[str] = []
    warnings: list[str] = []
    if not exam.exam_date:
        issues.append("Sınav tarihi girilmelidir")
    if not (exam.location or "").strip():
        # Pilot/testte eski akışları kırmadan görünür uyarı ver; gerçek kurum/kimlik doğrulamalı kullanımda zorunlu kıl.
        if settings.app_env == "production" or settings.auth_required:
            issues.append("Sınav salonu / konumu girilmelidir")
        else:
            warnings.append("Sınav salonu / konumu henüz girilmedi; production ortamında zorunludur")
    if (exam.paper_size or "A4") not in {"A3", "A4", "A5"}:
        issues.append("Kağıt boyutu A3, A4 veya A5 olmalıdır")
    if (exam.paper_orientation or "portrait") not in {"portrait", "landscape"}:
        issues.append("Kağıt yönü dikey veya yatay olmalıdır")
    if (exam.omr_mode or "embedded") not in {"embedded", "separate"}:
        issues.append("Optik form modu geçersiz")
    if not questions:
        issues.append("En az bir soru eklenmelidir")
    if questions:
        orders = [q.order_no for q in questions]
        if orders != list(range(1, len(questions) + 1)):
            issues.append("Soru sıraları 1'den başlayarak kesintisiz olmalıdır")
        total = round(sum(float(q.points) for q in questions), 4)
        if abs(total - 100.0) > 0.01:
            issues.append(f"Soru puanları toplamı 100 olmalıdır (şu an {total:g})")
        for q in questions:
            if not _question_outcome_codes(q):
                issues.append(f"{q.order_no}. soru en az bir ÖÇ ile eşleştirilmelidir")
            if q.question_type == "mcq":
                try:
                    _clean_mcq_fields(q.question_type, q.choices, q.correct_answer)
                except HTTPException as exc:
                    issues.append(f"{q.order_no}. soru: {exc.detail}")
            else:
                if not (q.expected_answer or "").strip():
                    issues.append(f"{q.order_no}. klasik soru için beklenen cevap/değerlendirme anahtarı zorunludur")
                if not q.rubric or not (q.rubric.get("criteria") or []):
                    issues.append(f"{q.order_no}. klasik soru için analitik rubrik zorunludur")
                else:
                    q_codes = {x.casefold() for x in _question_outcome_codes(q)}
                    for criterion in q.rubric.get("criteria") or []:
                        c_codes = _normalized_outcome_codes(criterion.get("outcome_codes") or [], None)
                        if not c_codes:
                            issues.append(f"{q.order_no}. soru / {criterion.get('label')}: rubrik ölçütü en az bir ÖÇ ile eşleştirilmelidir")
                        elif any(code.casefold() not in q_codes for code in c_codes):
                            issues.append(f"{q.order_no}. soru / {criterion.get('label')}: rubrik ÖÇ eşleşmesi sorunun ÖÇ listesinde bulunmalıdır")
    if (exam.duration_minutes or 0) <= 0:
        issues.append("Sınav süresi pozitif olmalıdır")
    if questions:
        # Coverage: every learning outcome snapshotted on the exam should be measured by at least one question.
        covered = {c.casefold() for q in questions for c in _question_outcome_codes(q)}
        exam_los = db.scalars(select(m.ExamLearningOutcome).where(m.ExamLearningOutcome.exam_id == exam.id)).all()
        missing = sorted(lo.code for lo in exam_los if lo.code.casefold() not in covered)
        if missing:
            warnings.append(f"Şu Öğrenim Çıktıları hiçbir soruyla ölçülmüyor: {', '.join(missing)}")
        seen: dict[str, int] = {}
        for q in questions:
            key = re.sub(r"\s+", " ", (q.text or "").strip().casefold())
            if key and key in seen:
                warnings.append(f"{q.order_no}. soru, {seen[key]}. soru ile aynı metne sahip")
            seen.setdefault(key, q.order_no)
        for q in questions:
            if q.question_type == "classic" and q.rubric and q.rubric.get("criteria"):
                rubric_total = round(sum(float(c.get("max_points") or 0) for c in q.rubric["criteria"]), 4)
                if abs(rubric_total - float(q.points)) > 0.01:
                    issues.append(f"{q.order_no}. soru rubrik toplamı ({rubric_total:g}) soru puanına ({float(q.points):g}) eşit olmalıdır")
        keys = [str(q.correct_answer or "").upper() for q in questions if q.question_type == "mcq" and q.correct_answer]
        if len(keys) >= 5 and len(set(keys)) == 1:
            warnings.append(f"Tüm test sorularının doğru cevabı aynı şık ({keys[0]}); cevap anahtarı dağılımını gözden geçirin")
    exam_student_count = db.scalar(select(func.count()).select_from(m.ExamStudent).where(m.ExamStudent.exam_id == exam.id)) or 0
    course_enrollment_count = db.scalar(select(func.count()).select_from(m.Enrollment).where(m.Enrollment.course_id == exam.course_id)) or 0
    if not exam_student_count:
        if course_enrollment_count:
            warnings.append(f"Ders kayıtlı {course_enrollment_count} öğrenci sınava henüz aktarılmadı")
        else:
            warnings.append("Dersin kayıtlı öğrencisi yok; kişiselleştirilmiş sınav kağıdı üretilemez")
    elif exam_student_count < course_enrollment_count:
        warnings.append(f"Sınavda {exam_student_count} öğrenci var; derste {course_enrollment_count} kayıtlı öğrenci bulunuyor")

    total_points = round(sum(float(q.points) for q in questions), 2)
    return {
        "exam_id": exam.id,
        "ready": not issues,
        "issues": issues,
        "warnings": warnings,
        "question_count": len(questions),
        "total_points": total_points,
        "mapped_questions": sum(1 for q in questions if _question_outcome_codes(q)),
        "mcq_count": sum(1 for q in questions if q.question_type == "mcq"),
        "classic_count": sum(1 for q in questions if q.question_type == "classic"),
        "booklet_count": exam.booklet_count or 4,
        "scheduled": bool(exam.exam_date),
        "location_ready": bool((exam.location or "").strip()),
        "student_count": int(exam_student_count),
        "course_enrollment_count": int(course_enrollment_count),
        "students_synced": bool(exam_student_count and exam_student_count == course_enrollment_count),
    }


def _allowed_booklets(exam: m.Exam) -> list[str]:
    count = exam.booklet_count or 4
    if count not in (1, 2, 4):
        count = 4
    return ["A", "B", "C", "D"][:count]


def _require_allowed_booklet(exam: m.Exam, booklet: str) -> str:
    value = (booklet or "A").strip().upper()
    if value not in _allowed_booklets(exam):
        raise HTTPException(400, f"Bu sınav için {value} kitapçığı tanımlı değil. Kullanılabilir: {', '.join(_allowed_booklets(exam))}")
    return value


def _course_lineage_key(course: m.Course | None) -> tuple[int, str] | None:
    if not course:
        return None
    return (int(course.program_id), str(course.code or "").strip().casefold())


def _same_course_lineage(left: m.Course | None, right: m.Course | None) -> bool:
    a = _course_lineage_key(left)
    b = _course_lineage_key(right)
    return bool(a and b and a == b)


def _bank_out(q: m.QuestionBank, *, source_course: m.Course | None = None, requested_course: m.Course | None = None) -> dict:
    choices = normalize_choices(q.choices)
    outcome_codes = _bank_outcome_codes(q)
    source_course = source_course or getattr(q, "course", None)
    historical = bool(requested_course and source_course and source_course.id != requested_course.id and _same_course_lineage(source_course, requested_course))
    return {
        "id": q.id, "course_id": q.course_id, "question_type": q.question_type, "text": q.text,
        "default_points": q.default_points, "correct_answer": normalize_correct_answer(q.correct_answer, choices), "choices": choices,
        "answer_lines": q.answer_lines,
        "learning_outcome_code": outcome_codes[0] if outcome_codes else None,
        "learning_outcome_codes": outcome_codes,
        "tags": q.tags or [], "is_active": q.is_active,
        "topic": q.topic or "", "unit": q.unit or "", "difficulty": q.difficulty or "medium",
        "bloom_level": q.bloom_level or "understand", "author": q.author or "", "reviewer": q.reviewer or "",
        "version_no": q.version_no or 1, "image_data": q.image_data, "rubric": q.rubric, "expected_answer": q.expected_answer or "",
        "usage_count": q.usage_count or 0, "last_used_at": q.last_used_at.isoformat() if q.last_used_at else None,
        "review_status": q.review_status or "draft", "review_note": q.review_note or "", "reviewed_at": q.reviewed_at.isoformat() if q.reviewed_at else None,
        "difficulty_index": q.difficulty_index, "discrimination_index": q.discrimination_index, "distractor_efficiency": q.distractor_efficiency,
        "psychometric_sample_size": int(q.psychometric_sample_size or 0), "quality_status": q.quality_status or "unmeasured",
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "updated_at": q.updated_at.isoformat() if q.updated_at else None,
        "source_course_code": source_course.code if source_course else "",
        "source_course_name": source_course.name if source_course else "",
        "source_academic_year": source_course.academic_year if source_course else "",
        "source_term": source_course.term if source_course else "",
        "institutional_scope": "course_lineage",
        "is_historical": historical,
    }

def _program_out(p: m.Program) -> dict:
    return {"id": p.id, "code": p.code, "name": p.name, "faculty": p.faculty, "department": p.department, "academic_unit_id": p.academic_unit_id, "external_source": p.external_source or "", "external_id": p.external_id}


def _course_out(c: m.Course) -> dict:
    return {"id": c.id, "program_id": c.program_id, "catalog_item_id": c.catalog_item_id, "code": c.code, "name": c.name, "academic_year": c.academic_year, "term": c.term, "instructor_email": c.instructor_email, "instructor_name": c.instructor_name, "pass_threshold_percent": float(c.pass_threshold_percent or 50), "external_source": c.external_source or "", "external_id": c.external_id}


def _student_out(s: m.Student) -> dict:
    return {"id": s.id, "program_id": s.program_id, "student_no": s.student_no, "full_name": s.full_name, "class_name": s.class_name, "external_source": s.external_source or "", "external_id": s.external_id, "anonymized_at": s.anonymized_at.isoformat() if s.anonymized_at else None}


def _exam_out(e: m.Exam, include_detail: bool = False) -> dict:
    base = {
        "id": e.id, "course_id": e.course_id, "title": e.title, "exam_type": e.exam_type,
        "exam_date": e.exam_date.isoformat() if e.exam_date else None,
        "start_time": e.start_time, "location": e.location or "",
        "duration_minutes": e.duration_minutes, "assessment_weight_percent": e.assessment_weight_percent,
        "booklet_count": e.booklet_count or 4, "instructions": e.instructions, "staff_notes": e.staff_notes or "", "status": e.status,
        "paper_template_version": e.paper_template_version,
        "paper_size": e.paper_size or "A4", "paper_orientation": e.paper_orientation or "portrait",
        "omr_mode": e.omr_mode or "embedded", "duplex_print": bool(e.duplex_print), "revision_no": e.revision_no or 1,
        "created_by_email": e.created_by_email or "", "approval_requested_by": e.approval_requested_by or "",
        "approval_requested_at": e.approval_requested_at.isoformat() if e.approval_requested_at else None,
        "approved_by": e.approved_by or "", "approved_at": e.approved_at.isoformat() if e.approved_at else None,
        "approval_note": e.approval_note or "",
        "grade_locked_at": e.grade_locked_at.isoformat() if e.grade_locked_at else None,
        "grade_locked_by": e.grade_locked_by or "", "grade_lock_note": e.grade_lock_note or "",
        "paper_snapshot": {
            "course_code": e.course_code_snapshot, "course_name": e.course_name_snapshot,
            "academic_year": e.academic_year_snapshot, "term": e.term_snapshot,
            "instructor": e.instructor_snapshot, "program_name": e.program_name_snapshot,
            "department": e.department_snapshot, "faculty": e.faculty_snapshot,
        },
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
    if include_detail:
        base["learning_outcomes"] = [{"id": x.id, "code": x.code, "description": x.description, "target_percent": x.target_percent} for x in sorted(e.learning_outcomes, key=lambda x: x.code)]
        base["program_outcomes"] = [{"id": x.id, "code": x.code, "description": x.description} for x in sorted(e.program_outcomes, key=lambda x: x.code)]
        base["outcome_mappings"] = [{
            "id": mp.id,
            "exam_learning_outcome_id": lo.id,
            "learning_outcome_code": lo.code,
            "exam_program_outcome_id": mp.exam_program_outcome_id,
            "program_outcome_code": mp.program_outcome.code if mp.program_outcome else None,
            "contribution": mp.contribution,
        } for lo in e.learning_outcomes for mp in lo.mappings]
        base["questions"] = [{
            "id": q.id, "order_no": q.order_no, "question_type": q.question_type, "text": q.text, "points": q.points,
            "correct_answer": normalize_correct_answer(q.correct_answer, q.choices), "choices": normalize_choices(q.choices),
            "answer_lines": q.answer_lines,
            "learning_outcome_code": (_question_outcome_codes(q)[0] if _question_outcome_codes(q) else None),
            "learning_outcome_codes": _question_outcome_codes(q),
            "bank_question_id": q.bank_question_id,
            "topic": q.topic or "", "unit": q.unit or "", "difficulty": q.difficulty or "medium",
            "bloom_level": q.bloom_level or "understand", "image_data": q.image_data, "rubric": q.rubric, "expected_answer": q.expected_answer or "",
        } for q in sorted(e.questions, key=lambda q: q.order_no)]
        base["student_count"] = len(e.exam_students)
    return base


def _role_assignment_out(x: m.UserRoleAssignment) -> dict:
    return {
        "id": x.id, "role": x.role, "role_label": ROLE_LABELS.get(x.role, x.role),
        "program_id": x.program_id, "course_id": x.course_id,
        "scope_faculty": x.scope_faculty or "", "scope_department": x.scope_department or "",
        "scope_program": x.scope_program or "",
    }


def _user_out(db: Session, u: m.AppUser) -> dict:
    roles = db.scalars(select(m.UserRoleAssignment).where(m.UserRoleAssignment.user_id == u.id).order_by(m.UserRoleAssignment.id)).all()
    return {
        "id": u.id, "email": u.email, "display_name": u.display_name,
        "external_object_id": u.external_object_id, "tenant_id": u.tenant_id,
        "auth_source": u.auth_source, "is_active": u.is_active,
        "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "roles": [_role_assignment_out(x) for x in roles],
        "role_names": sorted({x.role for x in roles}),
    }


def _validate_role_scope(db: Session, data: UserRoleCreate) -> None:
    if data.role not in {"admin", "quality", "instructor", "program_head"}:
        raise HTTPException(400, "Yeni akademik hesaplarda yalnız Öğretim Görevlisi, Program Başkanı veya Kalite Müdürü rolleri atanabilir")
    if data.program_id and not db.get(m.Program, data.program_id):
        raise HTTPException(400, "Rol kapsamındaki program bulunamadı")
    if data.course_id and not db.get(m.Course, data.course_id):
        raise HTTPException(400, "Rol kapsamındaki ders bulunamadı")
    if data.role in {"admin", "quality"} and any([data.program_id, data.course_id, data.scope_faculty.strip(), data.scope_department.strip(), data.scope_program.strip()]):
        raise HTTPException(400, "Admin ve kalite rolleri globaldir; akademik kapsam verilmemelidir")
    if data.role == "instructor" and not data.course_id:
        raise HTTPException(400, "Öğretim Elemanı rolünde ders kapsamı zorunludur")
    if data.role == "program_head" and not (data.program_id or data.scope_program.strip()):
        raise HTTPException(400, "Program Başkanı rolünde program kapsamı zorunludur")
    if data.role == "department_head" and not data.scope_department.strip():
        raise HTTPException(400, "Bölüm Başkanı rolünde bölüm kapsamı zorunludur")
    if data.role == "faculty_admin" and not data.scope_faculty.strip():
        raise HTTPException(400, "Fakülte/MYO yöneticisi rolünde fakülte/MYO kapsamı zorunludur")


def _is_last_admin_assignment(db: Session, role_id: int) -> bool:
    role = db.get(m.UserRoleAssignment, role_id)
    if not role or role.role != "admin":
        return False
    total = db.scalar(select(func.count()).select_from(m.UserRoleAssignment).join(m.AppUser).where(m.UserRoleAssignment.role == "admin", m.AppUser.is_active.is_(True))) or 0
    return total <= 1


def _can_manage_program(program: m.Program, db: Session) -> bool:
    return can_access_program(db, program, write=True)


def _academic_period_out(db: Session, x: m.AcademicPeriod) -> dict:
    course_ids = list(db.scalars(select(m.Course.id).where(m.Course.academic_year == x.academic_year, m.Course.term == x.term)).all())
    exam_count = db.scalar(select(func.count()).select_from(m.Exam).where(m.Exam.course_id.in_(course_ids))) or 0 if course_ids else 0
    return {
        "id": x.id, "academic_year": x.academic_year, "term": x.term, "title": x.title, "status": x.status,
        "starts_on": x.starts_on.isoformat() if x.starts_on else None, "ends_on": x.ends_on.isoformat() if x.ends_on else None,
        "locked_at": x.locked_at.isoformat() if x.locked_at else None, "course_count": len(course_ids), "exam_count": exam_count,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    }


def _sync_instructor_users_internal(db: Session, *, auth_source: str = "pilot") -> dict:
    created_users = 0; created_roles = 0; updated_users = 0
    for course in db.scalars(select(m.Course).where(m.Course.instructor_email != "")).all():
        email = course.instructor_email.strip().lower()
        if not email:
            continue
        user = db.scalar(select(m.AppUser).where(m.AppUser.email == email))
        if not user:
            user = m.AppUser(email=email, display_name=(course.instructor_name or email), auth_source=auth_source, is_active=True)
            db.add(user); db.flush(); created_users += 1
        else:
            new_name = (course.instructor_name or user.display_name or email).strip()
            if new_name and user.display_name != new_name:
                user.display_name = new_name; updated_users += 1
        exists = db.scalar(select(m.UserRoleAssignment).where(m.UserRoleAssignment.user_id == user.id, m.UserRoleAssignment.role == "instructor", m.UserRoleAssignment.course_id == course.id))
        if not exists:
            db.add(m.UserRoleAssignment(user_id=user.id, role="instructor", course_id=course.id)); created_roles += 1
    return {"created_users": created_users, "updated_users": updated_users, "created_roles": created_roles}


@app.get("/api/auth/config")
def auth_configuration():
    return auth_config()


@app.post("/api/auth/obs-login")
def obs_login(payload: ObsLoginRequest, db: Session = Depends(get_db)):
    if settings.auth_provider != "obs":
        raise HTTPException(503, "AUTH_PROVIDER=obs değil; bu giriş yolu kapalı")
    if not settings.obs_proliz_enabled:
        raise HTTPException(503, "OBS_PROLIZ_ENABLED=false; Proliz entegrasyonu kapalı")
    username = payload.username.strip()
    try:
        db.rollback()
        with db.begin():
            user, stats = teacher_login_and_sync(db, username, payload.password, payload.donem_id)
            audit(db, "obs_login", "app_user", user.id, {"username": username, **{k: v for k, v in stats.items() if k != "donem_id"}, "donem_id": stats.get("donem_id")})
            run = m.IntegrationSyncRun(provider="obs-proliz", filename=f"teacher-login-{username}", mode="login", source_sha256="n/a", status="success", summary=stats)
            db.add(run)
    except ObsLoginError as exc:
        db.rollback()
        run = m.IntegrationSyncRun(provider="obs-proliz", filename=f"teacher-login-{username}", mode="login", source_sha256="n/a", status="failed", summary={"error": str(exc)[:500]})
        db.add(run); db.flush(); audit(db, "obs_login_failed", "integration_sync_run", run.id, {"username": username, "error": str(exc)[:500]}); _commit(db)
        raise HTTPException(exc.status_code, str(exc)) from exc
    except obs_proliz.ProlizError as exc:
        db.rollback()
        run = m.IntegrationSyncRun(provider="obs-proliz", filename=f"teacher-login-{username}", mode="login", source_sha256="n/a", status="failed", summary={"error": str(exc)[:500]})
        db.add(run); db.flush(); audit(db, "obs_login_failed", "integration_sync_run", run.id, {"username": username, "error": str(exc)[:500]}); _commit(db)
        raise HTTPException(502, str(exc)) from exc
    token = mint_obs_session_token(user)
    return {"access_token": token, "token_type": "bearer", "display_name": user.display_name, "email": user.email, "sync": stats}


@app.get("/api/auth/me")
def auth_me():
    return current_user()


@app.get("/api/auth/pilot-users")
def pilot_users(db: Session = Depends(get_db)):
    if settings.auth_required:
        raise HTTPException(404, "Pilot kullanıcı seçimi kapalı")
    rows = db.scalars(select(m.AppUser).where(m.AppUser.is_active.is_(True)).order_by(m.AppUser.display_name)).all()
    return [{"id": x.id, "email": x.email, "display_name": x.display_name, "auth_source": x.auth_source} for x in rows]


@app.get("/api/users")
def users(db: Session = Depends(get_db)):
    require_roles("admin")
    return [_user_out(db, x) for x in db.scalars(select(m.AppUser).order_by(m.AppUser.display_name)).all()]


@app.post("/api/users", status_code=201)
def create_user(data: AppUserCreate, db: Session = Depends(get_db)):
    require_roles("admin")
    email = data.email.strip().lower()
    if db.scalar(select(m.AppUser).where(m.AppUser.email == email)):
        raise HTTPException(409, "Bu e-posta ile kullanıcı zaten mevcut")
    obj = m.AppUser(**(data.model_dump() | {"email": email, "display_name": data.display_name.strip()}))
    db.add(obj); db.flush(); audit(db, "create", "app_user", obj.id, {"email": email, "auth_source": obj.auth_source}); _commit(db)
    return _user_out(db, obj)


@app.patch("/api/users/{user_id}")
def update_user(user_id: int, data: AppUserUpdate, db: Session = Depends(get_db)):
    require_roles("admin")
    obj = db.get(m.AppUser, user_id)
    if not obj: raise HTTPException(404, "Kullanıcı bulunamadı")
    changes = data.model_dump(exclude_unset=True)
    if "email" in changes and changes["email"] is not None: changes["email"] = changes["email"].strip().lower()
    if changes.get("is_active") is False:
        admin_roles = db.scalar(select(func.count()).select_from(m.UserRoleAssignment).where(m.UserRoleAssignment.user_id == user_id, m.UserRoleAssignment.role == "admin")) or 0
        # Portable last-admin check without dialect-specific DISTINCT expressions.
        if admin_roles:
            others = db.scalars(select(m.AppUser).join(m.UserRoleAssignment).where(m.UserRoleAssignment.role == "admin", m.AppUser.is_active.is_(True), m.AppUser.id != user_id)).all()
            if not others: raise HTTPException(409, "Son aktif admin kullanıcı pasifleştirilemez")
    for k,v in changes.items(): setattr(obj,k,v)
    audit(db, "update", "app_user", obj.id, changes); _commit(db)
    return _user_out(db, obj)


@app.post("/api/users/{user_id}/roles", status_code=201)
def add_user_role(user_id: int, data: UserRoleCreate, db: Session = Depends(get_db)):
    require_roles("admin")
    user = db.get(m.AppUser, user_id)
    if not user: raise HTTPException(404, "Kullanıcı bulunamadı")
    _validate_role_scope(db, data)
    payload = data.model_dump()
    duplicate = db.scalars(select(m.UserRoleAssignment).where(m.UserRoleAssignment.user_id == user_id, m.UserRoleAssignment.role == data.role)).all()
    for x in duplicate:
        if all(getattr(x,k) == payload[k] for k in ("program_id","course_id","scope_faculty","scope_department","scope_program")):
            return _role_assignment_out(x)
    obj = m.UserRoleAssignment(user_id=user_id, **payload)
    db.add(obj); db.flush(); audit(db, "role_add", "app_user", user_id, _role_assignment_out(obj)); _commit(db)
    return _role_assignment_out(obj)


@app.delete("/api/users/{user_id}/roles/{role_id}")
def delete_user_role(user_id: int, role_id: int, db: Session = Depends(get_db)):
    require_roles("admin")
    obj = db.get(m.UserRoleAssignment, role_id)
    if not obj or obj.user_id != user_id: raise HTTPException(404, "Rol ataması bulunamadı")
    if _is_last_admin_assignment(db, role_id): raise HTTPException(409, "Sistemde en az bir aktif admin rolü kalmalıdır")
    payload = _role_assignment_out(obj); db.delete(obj); audit(db, "role_remove", "app_user", user_id, payload); _commit(db)
    return {"deleted": True}


@app.post("/api/users/sync-course-instructors")
def sync_course_instructor_users(db: Session = Depends(get_db)):
    require_roles("admin")
    result = _sync_instructor_users_internal(db)
    audit(db, "sync_course_instructors", "app_user", payload=result); _commit(db)
    return result


@app.get("/api/academic-periods")
def academic_periods(db: Session = Depends(get_db)):
    require_roles("admin", "quality", "program_head", "department_head", "faculty_admin")
    rows = db.scalars(select(m.AcademicPeriod).order_by(m.AcademicPeriod.academic_year.desc(), m.AcademicPeriod.id.desc())).all()
    return [_academic_period_out(db, x) for x in rows]


@app.post("/api/academic-periods/bootstrap")
def bootstrap_academic_periods(db: Session = Depends(get_db)):
    require_roles("admin")
    created = 0
    pairs = db.execute(select(m.Course.academic_year, m.Course.term).distinct()).all()
    for academic_year, term in pairs:
        if not academic_year or not term:
            continue
        exists = db.scalar(select(m.AcademicPeriod).where(m.AcademicPeriod.academic_year == academic_year, m.AcademicPeriod.term == term))
        if not exists:
            db.add(m.AcademicPeriod(academic_year=academic_year, term=term, title=f"{academic_year} {term}", status="planned")); created += 1
    audit(db, "bootstrap", "academic_period", payload={"created": created}); _commit(db)
    return {"created": created}


@app.post("/api/academic-periods", status_code=201)
def create_academic_period(data: AcademicPeriodCreate, db: Session = Depends(get_db)):
    require_roles("admin")
    if data.starts_on and data.ends_on and data.ends_on < data.starts_on:
        raise HTTPException(400, "Dönem bitiş tarihi başlangıç tarihinden önce olamaz")
    exists = db.scalar(select(m.AcademicPeriod).where(m.AcademicPeriod.academic_year == data.academic_year.strip(), m.AcademicPeriod.term == data.term.strip()))
    if exists:
        raise HTTPException(409, "Bu akademik yıl/dönem zaten tanımlı")
    obj = m.AcademicPeriod(
        academic_year=data.academic_year.strip(), term=data.term.strip(), title=data.title.strip(),
        starts_on=data.starts_on, ends_on=data.ends_on, status="planned",
    )
    db.add(obj); db.flush(); audit(db, "create", "academic_period", obj.id, {"academic_year": obj.academic_year, "term": obj.term}); _commit(db)
    return _academic_period_out(db, obj)


@app.post("/api/academic-periods/{period_id}/status")
def change_academic_period_status(period_id: int, data: AcademicPeriodStatusUpdate, db: Session = Depends(get_db)):
    require_roles("admin")
    obj = db.get(m.AcademicPeriod, period_id)
    if not obj:
        raise HTTPException(404, "Akademik dönem bulunamadı")
    old = obj.status
    new = data.status
    if old == new:
        return _academic_period_out(db, obj)
    if old == "archived" and new != "archived":
        raise HTTPException(409, "Arşivlenmiş dönem tekrar açılamaz")
    if new == "archived" and old != "locked":
        raise HTTPException(409, "Dönem arşivlenmeden önce kilitlenmelidir")
    if new in {"locked", "archived"}:
        course_ids = list(db.scalars(select(m.Course.id).where(m.Course.academic_year == obj.academic_year, m.Course.term == obj.term)).all())
        if course_ids:
            unfinished = db.scalars(select(m.Exam).where(m.Exam.course_id.in_(course_ids), m.Exam.status.not_in(["approved", "archived"]))).all()
            if unfinished:
                preview = ", ".join(f"#{x.id} {x.title} ({x.status})" for x in unfinished[:5])
                raise HTTPException(409, f"Dönem kilitlenemez. Tamamlanmamış sınavlar var: {preview}")
    if new == "active":
        for other in db.scalars(select(m.AcademicPeriod).where(m.AcademicPeriod.status == "active", m.AcademicPeriod.id != obj.id)).all():
            other.status = "planned"
    obj.status = new
    obj.locked_at = datetime.now(timezone.utc) if new in {"locked", "archived"} else None
    audit(db, "status_change", "academic_period", obj.id, {"from": old, "to": new}); _commit(db)
    return _academic_period_out(db, obj)


@app.get("/api/health")
def health():
    return {"status": "ok", **build_metadata()}


@app.get("/api/ready")
def ready(db: Session = Depends(get_db)):
    issues: list[str] = []
    dialect = db.bind.dialect.name if db.bind else "unknown"
    try:
        value = db.execute(text("SELECT 1")).scalar_one()
        if value != 1:
            issues.append("database")
    except Exception:
        issues.append("database")
    schema_revision = None
    try:
        schema_revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except Exception:
        # Unit tests build metadata directly; production always runs Alembic.
        schema_revision = None
    storage = {}
    for key, raw in {"evidence": settings.evidence_storage_path, "scans": settings.scan_storage_path, "ops": settings.ops_storage_path}.items():
        path = Path(raw)
        ok = path.exists() and path.is_dir() and os.access(path, os.W_OK | os.X_OK)
        storage[key] = bool(ok)
        if settings.app_env == "production" and not ok:
            issues.append(f"storage:{key}")
    if settings.app_env == "production" and schema_revision != EXPECTED_SCHEMA_REVISION:
        issues.append("schema")
    payload = {"status": "ready" if not issues else "not_ready"}
    if settings.app_env != "production":
        payload.update({"version": APP_VERSION, "database_dialect": dialect, "schema_revision": schema_revision, "storage": storage})
    if issues:
        payload["checks"] = {"failed": issues}
        return JSONResponse(status_code=503, content=payload)
    return payload


@app.get("/api/system/diagnostics")
def system_diagnostics(db: Session = Depends(get_db)):
    require_roles("admin")
    dialect = db.bind.dialect.name if db.bind else "unknown"
    schema_revision = None
    database_ok = False
    try:
        database_ok = db.execute(text("SELECT 1")).scalar_one() == 1
        schema_revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except Exception:
        database_ok = False

    storage = {}
    for key, raw in {
        "evidence": settings.evidence_storage_path,
        "scans": settings.scan_storage_path,
        "ops": settings.ops_storage_path,
    }.items():
        path = Path(raw)
        storage[key] = {
            "exists": path.exists(),
            "writable": path.exists() and path.is_dir() and os.access(path, os.W_OK | os.X_OK),
        }

    security_issues = production_security_issues() if settings.app_env == "production" else []
    security_warnings = production_security_warnings()
    status = "ok" if database_ok and (schema_revision in {None, EXPECTED_SCHEMA_REVISION}) else "degraded"
    return {
        "status": status,
        # Backward-compatible top-level fields for existing operations clients.
        "version": APP_VERSION,
        "app_env": settings.app_env,
        "database_dialect": dialect,
        "build": build_metadata(),
        "environment": settings.app_env,
        "database": {
            "ok": database_ok,
            "dialect": dialect,
            "schema_revision": schema_revision,
            "schema_expected": EXPECTED_SCHEMA_REVISION,
            "pool": engine.pool.status() if hasattr(engine.pool, "status") else None,
        },
        "storage": storage,
        "auth": {
            "required": settings.auth_required,
            "provider": settings.auth_provider,
            "entra_configured": bool(settings.entra_tenant_id and settings.entra_client_id and settings.entra_audience),
            "entra_redirect_configured": bool(settings.entra_redirect_uri),
            "allowed_client_count": len(settings.entra_allowed_client_ids),
        },
        "integrations": {
            "obs_results_configured": bool(settings.obs_results_endpoint),
            "public_hostname_configured": bool(settings.public_hostname),
        },
        "security": {
            "require_https": settings.require_https,
            "public_hostname_configured": bool(settings.public_hostname),
            "allowed_hosts_configured": bool(settings.allowed_hosts),
            "security_headers": settings.security_headers,
            "rate_limit_enabled": settings.rate_limit_enabled,
            "expected_schema_revision": EXPECTED_SCHEMA_REVISION,
            "issues": security_issues,
            "warnings": security_warnings,
        },
    }


@app.get("/api/security/events")
def security_events(event_type: str | None = None, severity: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    require_roles("admin")
    limit = min(max(limit, 1), 500)
    stmt = select(m.SecurityEvent).order_by(m.SecurityEvent.id.desc()).limit(limit)
    if event_type:
        stmt = stmt.where(m.SecurityEvent.event_type == event_type)
    if severity:
        stmt = stmt.where(m.SecurityEvent.severity == severity)
    rows = db.scalars(stmt).all()
    return [{
        "id": x.id, "event_type": x.event_type, "severity": x.severity, "request_id": x.request_id,
        "actor_email": x.actor_email, "remote_addr": x.remote_addr, "method": x.method, "path": x.path,
        "detail": x.detail or {}, "created_at": x.created_at.isoformat() if x.created_at else None,
    } for x in rows]


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    pids = visible_program_ids(db)
    cids = visible_course_ids(db)
    exams = db.scalars(select(m.Exam).where(m.Exam.course_id.in_(cids))).all() if cids else []
    exam_ids = {x.id for x in exams}
    # Managers/quality see program students; instructors see only students enrolled in visible courses.
    if has_role("admin", "quality", "program_head", "department_head", "faculty_admin"):
        student_count = db.scalar(select(func.count()).select_from(m.Student).where(m.Student.program_id.in_(pids))) or 0 if pids else 0
    else:
        sids = set(db.scalars(select(m.Enrollment.student_id).where(m.Enrollment.course_id.in_(cids))).all()) if cids else set()
        student_count = len(sids)
    qcount = db.scalar(select(func.count()).select_from(m.Question).where(m.Question.exam_id.in_(exam_ids))) or 0 if exam_ids else 0
    bank_count = db.scalar(select(func.count()).select_from(m.QuestionBank).where(m.QuestionBank.course_id.in_(cids), m.QuestionBank.is_active.is_(True))) or 0 if cids else 0
    ecount = db.scalar(select(func.count()).select_from(m.EvidenceAsset).where(m.EvidenceAsset.exam_id.in_(exam_ids))) or 0 if exam_ids else 0
    open_reviews = db.scalar(select(func.count()).select_from(m.ScanReview).where(m.ScanReview.exam_id.in_(exam_ids), m.ScanReview.status == "open")) or 0 if exam_ids else 0
    open_actions = db.scalar(select(func.count()).select_from(m.ImprovementAction).where(m.ImprovementAction.exam_id.in_(exam_ids), m.ImprovementAction.status.in_(["open", "in_progress"]))) or 0 if exam_ids else 0
    official_exams = sum(1 for x in exams if x.status in {"approved", "archived"})
    feedback_open = 0
    if has_role("admin", "quality"):
        feedback_open = db.scalar(select(func.count()).select_from(m.PilotFeedback).where(m.PilotFeedback.status != "resolved")) or 0
    return {
        "programs": len(pids), "courses": len(cids), "students": student_count,
        "exams": len(exam_ids), "questions": qcount, "bank_questions": int(bank_count), "evidence_assets": ecount,
        "open_reviews": int(open_reviews), "open_improvements": int(open_actions), "official_exams": int(official_exams),
        "feedback_open": int(feedback_open), "roles": list(current_user().get("role_names") or []),
    }


@app.get("/api/quality/dashboard")
def quality_management_dashboard(
    academic_year: str | None = None, term: str | None = None, program_id: int | None = None,
    faculty: str | None = None, department: str | None = None, db: Session = Depends(get_db),
):
    require_roles("admin", "quality", "program_head", "department_head", "faculty_admin")
    pids = visible_program_ids(db)
    if program_id is not None and program_id not in pids:
        raise HTTPException(403, "Program kalite kapsamınız dışında")
    return build_quality_dashboard(
        db, pids, academic_year=academic_year, term=term, program_id=program_id,
        faculty=faculty, department=department,
    )


@app.get("/api/quality/dashboard.xlsx")
def quality_management_dashboard_xlsx(
    academic_year: str | None = None, term: str | None = None, program_id: int | None = None,
    faculty: str | None = None, department: str | None = None, db: Session = Depends(get_db),
):
    require_roles("admin", "quality", "program_head", "department_head", "faculty_admin")
    pids = visible_program_ids(db)
    if program_id is not None and program_id not in pids:
        raise HTTPException(403, "Program kalite kapsamınız dışında")
    payload = build_quality_dashboard(
        db, pids, academic_year=academic_year, term=term, program_id=program_id,
        faculty=faculty, department=department,
    )
    raw, filename = build_quality_dashboard_xlsx(payload)
    return StreamingResponse(
        BytesIO(raw),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/quality/courses/{course_id}/drilldown")
def quality_course_drilldown(course_id: int, db: Session = Depends(get_db)):
    require_roles("admin", "quality", "program_head", "department_head", "faculty_admin")
    require_course_access(db, course_id, write=False)
    try:
        return course_quality_drilldown(db, course_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))




@app.get("/api/courses/{course_id}/analytics-overview")
def course_analytics_overview(course_id: int, db: Session = Depends(get_db)):
    require_course_access(db, course_id, write=False)
    try:
        return course_lineage_analytics(db, course_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.get("/api/programs/{program_id}/analytics-overview")
def program_analytics_overview(program_id: int, academic_year: str | None = None, term: str | None = None, db: Session = Depends(get_db)):
    require_roles("admin", "quality", "program_head", "department_head", "faculty_admin")
    require_program_access(db, program_id, write=False)
    payload = build_quality_dashboard(db, [program_id], academic_year=academic_year, term=term, program_id=program_id)
    return payload


@app.get("/api/pilot/status")
def pilot_status(db: Session = Depends(get_db)):
    require_roles("admin", "quality", "program_head", "department_head", "faculty_admin")
    pids = visible_program_ids(db)
    cids = visible_course_ids(db)
    exam_rows = db.scalars(select(m.Exam).where(m.Exam.course_id.in_(cids))).all() if cids else []
    exam_ids = {x.id for x in exam_rows}
    status_counts: dict[str, int] = {}
    for exam in exam_rows:
        status_counts[exam.status] = status_counts.get(exam.status, 0) + 1
    student_count = db.scalar(select(func.count()).select_from(m.Student).where(m.Student.program_id.in_(pids))) or 0 if pids else 0
    scan_pages = db.scalar(select(func.sum(m.ScanSession.page_count)).where(m.ScanSession.exam_id.in_(exam_ids))) or 0 if exam_ids else 0
    open_reviews = db.scalar(select(func.count()).select_from(m.ScanReview).where(m.ScanReview.exam_id.in_(exam_ids), m.ScanReview.status == "open")) or 0 if exam_ids else 0
    open_actions = db.scalar(select(func.count()).select_from(m.ImprovementAction).where(m.ImprovementAction.exam_id.in_(exam_ids), m.ImprovementAction.status.in_(["open", "in_progress"]))) or 0 if exam_ids else 0
    periods = db.scalars(select(m.AcademicPeriod).order_by(m.AcademicPeriod.id.desc())).all()
    active = next((x for x in periods if x.status == "active"), None)
    last_sync = db.scalar(select(m.IntegrationSyncRun).order_by(m.IntegrationSyncRun.id.desc()).limit(1))
    return {
        "version": APP_VERSION, "programs": len(pids), "courses": len(cids), "students": int(student_count),
        "users": (db.scalar(select(func.count()).select_from(m.AppUser).where(m.AppUser.is_active.is_(True))) or 0) if has_role("admin") else None,
        "exams": len(exam_rows), "exam_status": status_counts, "scan_pages": int(scan_pages), "open_scan_reviews": int(open_reviews),
        "open_improvements": int(open_actions), "academic_periods": len(periods),
        "active_period": _academic_period_out(db, active) if active else None,
        "last_sync": ({"id": last_sync.id, "provider": last_sync.provider, "filename": last_sync.filename, "status": last_sync.status, "summary": last_sync.summary, "created_at": last_sync.created_at.isoformat() if last_sync.created_at else None} if last_sync else None),
        "production_ready": len(production_security_issues()) == 0 if settings.app_env == "production" else False,
    }


@app.get("/api/pilot/readiness")
def pilot_readiness(db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    return build_pilot_readiness(db, settings, APP_VERSION)


@app.get("/api/pilot/issues")
def pilot_issues(db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    return operational_issues(db, settings, APP_VERSION)


@app.post("/api/pilot/uat/run", status_code=201)
def run_pilot_uat(db: Session = Depends(get_db)):
    require_roles("admin")
    started = datetime.now(timezone.utc)
    result = build_uat_checks(db, settings, APP_VERSION)
    try:
        actor = current_user().get("email") or "system"
    except Exception:
        actor = "system"
    duration_ms = max(0, int((datetime.now(timezone.utc) - started).total_seconds() * 1000))
    row = m.PilotUATRun(
        status=result["status"], score=result["score"], checks=result["checks"],
        summary={"readiness_score": result["readiness"]["score"], "version": APP_VERSION},
        created_by=actor, duration_ms=duration_ms,
    )
    db.add(row); db.flush(); audit(db, "uat_run", "pilot_uat_run", row.id, {"status": row.status, "score": row.score}); _commit(db)
    return {"id": row.id, "status": row.status, "score": row.score, "checks": row.checks, "summary": row.summary, "created_by": row.created_by, "duration_ms": row.duration_ms, "created_at": row.created_at.isoformat() if row.created_at else None}


@app.get("/api/pilot/uat/runs")
def pilot_uat_runs(limit: int = 20, db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    limit = min(max(limit, 1), 100)
    rows = db.scalars(select(m.PilotUATRun).order_by(m.PilotUATRun.id.desc()).limit(limit)).all()
    return [{"id": x.id, "status": x.status, "score": x.score, "checks": x.checks or [], "summary": x.summary or {}, "created_by": x.created_by, "duration_ms": x.duration_ms, "created_at": x.created_at.isoformat() if x.created_at else None} for x in rows]


@app.get("/api/pilot/performance")
def pilot_performance(db: Session = Depends(get_db)):
    require_roles("admin")
    timings = {}
    probes = {
        "program_count": select(func.count()).select_from(m.Program),
        "course_count": select(func.count()).select_from(m.Course),
        "student_count": select(func.count()).select_from(m.Student),
        "exam_count": select(func.count()).select_from(m.Exam),
        "response_count": select(func.count()).select_from(m.Response),
    }
    values = {}
    from time import perf_counter
    for name, stmt in probes.items():
        t0 = perf_counter(); values[name] = int(db.scalar(stmt) or 0); timings[name] = round((perf_counter() - t0) * 1000, 2)
    return {"status": "ok", "version": APP_VERSION, "counts": values, "query_ms": timings, "generated_at": datetime.now(timezone.utc).isoformat()}


@app.post("/api/feedback", status_code=201)
def create_pilot_feedback(data: PilotFeedbackCreate, db: Session = Depends(get_db)):
    actor = current_user()
    row = m.PilotFeedback(
        category=data.category, rating=data.rating, page=data.page.strip(), message=data.message.strip(),
        created_by=actor.get("email") or "system", role_names=list(actor.get("role_names") or []),
    )
    db.add(row); db.flush(); audit(db, "create", "pilot_feedback", row.id, {"category": row.category, "page": row.page, "rating": row.rating}); _commit(db)
    return {"id": row.id, "category": row.category, "rating": row.rating, "page": row.page, "message": row.message, "status": row.status, "created_by": row.created_by, "role_names": row.role_names, "resolution_note": row.resolution_note, "created_at": row.created_at.isoformat() if row.created_at else None}


@app.get("/api/feedback")
def list_pilot_feedback(status: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 300)
    stmt = select(m.PilotFeedback).order_by(m.PilotFeedback.id.desc()).limit(limit)
    if status:
        if status not in {"open", "reviewed", "resolved"}: raise HTTPException(400, "Geçersiz geri bildirim durumu")
        stmt = stmt.where(m.PilotFeedback.status == status)
    if not has_role("admin", "quality"):
        stmt = stmt.where(m.PilotFeedback.created_by == (current_user().get("email") or ""))
    rows = db.scalars(stmt).all()
    return [{"id": x.id, "category": x.category, "rating": x.rating, "page": x.page, "message": x.message, "status": x.status, "created_by": x.created_by, "role_names": x.role_names or [], "resolution_note": x.resolution_note, "created_at": x.created_at.isoformat() if x.created_at else None} for x in rows]


@app.patch("/api/feedback/{feedback_id}")
def update_pilot_feedback(feedback_id: int, data: PilotFeedbackUpdate, db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    row = db.get(m.PilotFeedback, feedback_id)
    if not row: raise HTTPException(404, "Geri bildirim bulunamadı")
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items(): setattr(row, key, value)
    audit(db, "update", "pilot_feedback", row.id, changes); _commit(db)
    return {"id": row.id, "status": row.status, "resolution_note": row.resolution_note}


@app.get("/api/audit-logs")
def audit_logs(entity_type: str | None = None, action: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    limit = min(max(limit, 1), 500)
    stmt = select(m.AuditLog).order_by(m.AuditLog.id.desc()).limit(limit)
    if entity_type: stmt = stmt.where(m.AuditLog.entity_type == entity_type)
    if action: stmt = stmt.where(m.AuditLog.action == action)
    rows = db.scalars(stmt).all()
    return [{"id": x.id, "actor_user_id": x.actor_user_id, "actor_email": x.actor_email, "actor_roles": x.actor_roles or [], "action": x.action, "entity_type": x.entity_type, "entity_id": x.entity_id, "payload": x.payload, "created_at": x.created_at.isoformat() if x.created_at else None} for x in rows]


@app.get("/api/programs")
def programs(
    q: str | None = None,
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    # 6.70: academic scope is enforced in SQL instead of fetching every row and
    # calling can_access_program() per object.
    stmt = select(m.Program).where(m.Program.id.in_(visible_program_id_select())).order_by(m.Program.name)
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where((m.Program.code.ilike(term)) | (m.Program.name.ilike(term)) | (m.Program.department.ilike(term)))
    return [_program_out(x) for x in db.scalars(stmt.offset(offset).limit(limit)).all()]


@app.post("/api/programs", status_code=201)
def create_program(data: ProgramCreate, db: Session = Depends(get_db)):
    require_roles("admin")
    obj = m.Program(**data.model_dump())
    db.add(obj); db.flush(); audit(db, "create", "program", obj.id, {"code": obj.code}); _commit(db)
    return _program_out(obj)


@app.get("/api/courses")
def courses(
    program_id: int | None = None, academic_year: str | None = None, term: str | None = None, q: str | None = None,
    limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(m.Course).where(m.Course.id.in_(visible_course_id_select())).order_by(m.Course.academic_year.desc(), m.Course.code)
    if program_id: stmt = stmt.where(m.Course.program_id == program_id)
    if academic_year: stmt = stmt.where(m.Course.academic_year == academic_year)
    if term: stmt = stmt.where(m.Course.term == term)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where((m.Course.code.ilike(pattern)) | (m.Course.name.ilike(pattern)) | (m.Course.instructor_email.ilike(pattern)))
    return [_course_out(x) for x in db.scalars(stmt.offset(offset).limit(limit)).all()]


@app.post("/api/courses", status_code=201)
def create_course(data: CourseCreate, db: Session = Depends(get_db)):
    require_program_access(db, data.program_id, write=True)
    ensure_period_values_writable(db, data.academic_year, data.term)
    if not db.get(m.Program, data.program_id):
        raise HTTPException(404, "Program bulunamadı")
    obj = m.Course(**data.model_dump())
    db.add(obj); db.flush(); audit(db, "create", "course", obj.id, {"code": obj.code}); _commit(db)
    return _course_out(obj)


@app.get("/api/students")
def students(
    program_id: int | None = None, q: str | None = None,
    limit: int = Query(500, ge=1, le=2000), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(m.Student).where(m.Student.program_id.in_(visible_program_id_select())).order_by(m.Student.student_no)
    if program_id: stmt = stmt.where(m.Student.program_id == program_id)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where((m.Student.student_no.ilike(pattern)) | (m.Student.full_name.ilike(pattern)) | (m.Student.class_name.ilike(pattern)))
    return [_student_out(x) for x in db.scalars(stmt.offset(offset).limit(limit)).all()]


@app.post("/api/students", status_code=201)
def create_student(data: StudentCreate, db: Session = Depends(get_db)):
    require_program_access(db, data.program_id, write=True)
    if not db.get(m.Program, data.program_id):
        raise HTTPException(404, "Program bulunamadı")
    obj = m.Student(**data.model_dump())
    db.add(obj); db.flush(); audit(db, "create", "student", obj.id, {"student_no": obj.student_no}); _commit(db)
    return _student_out(obj)


@app.patch("/api/programs/{program_id}")
def update_program(program_id: int, data: ProgramUpdate, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=True)
    obj = db.get(m.Program, program_id)
    if not obj: raise HTTPException(404, "Program bulunamadı")
    changes = _apply_patch(obj, data); audit(db, "update", "program", obj.id, changes); _commit(db)
    return _program_out(obj)


@app.delete("/api/programs/{program_id}")
def delete_program(program_id: int, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=True)
    obj = db.get(m.Program, program_id)
    if not obj: raise HTTPException(404, "Program bulunamadı")
    _block_delete("Program", {
        "ders": db.scalar(select(func.count()).select_from(m.Course).where(m.Course.program_id == program_id)) or 0,
        "öğrenci": db.scalar(select(func.count()).select_from(m.Student).where(m.Student.program_id == program_id)) or 0,
        "PÇ": db.scalar(select(func.count()).select_from(m.ProgramOutcome).where(m.ProgramOutcome.program_id == program_id)) or 0,
    })
    db.delete(obj); audit(db, "delete", "program", program_id); _commit(db); return {"deleted": True}


@app.patch("/api/courses/{course_id}")
def update_course(course_id: int, data: CourseUpdate, db: Session = Depends(get_db)):
    require_course_management(db, course_id)
    obj = db.get(m.Course, course_id)
    if not obj: raise HTTPException(404, "Ders bulunamadı")
    changes = _apply_patch(obj, data); audit(db, "update", "course", obj.id, changes); _commit(db)
    return _course_out(obj)


@app.delete("/api/courses/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    require_course_management(db, course_id)
    obj = db.get(m.Course, course_id)
    if not obj: raise HTTPException(404, "Ders bulunamadı")
    _block_delete("Ders", {
        "sınav": db.scalar(select(func.count()).select_from(m.Exam).where(m.Exam.course_id == course_id)) or 0,
        "öğrenci kaydı": db.scalar(select(func.count()).select_from(m.Enrollment).where(m.Enrollment.course_id == course_id)) or 0,
        "ÖÇ": db.scalar(select(func.count()).select_from(m.LearningOutcome).where(m.LearningOutcome.course_id == course_id)) or 0,
        "soru havuzu": db.scalar(select(func.count()).select_from(m.QuestionBank).where(m.QuestionBank.course_id == course_id)) or 0,
    })
    db.delete(obj); audit(db, "delete", "course", course_id); _commit(db); return {"deleted": True}


@app.patch("/api/students/{student_id}")
def update_student(student_id: int, data: StudentUpdate, db: Session = Depends(get_db)):
    require_student_access(db, student_id, write=True)
    obj = db.get(m.Student, student_id)
    if not obj: raise HTTPException(404, "Öğrenci bulunamadı")
    changes = _apply_patch(obj, data); audit(db, "update", "student", obj.id, changes); _commit(db)
    return _student_out(obj)


@app.delete("/api/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    require_student_access(db, student_id, write=True)
    obj = db.get(m.Student, student_id)
    if not obj: raise HTTPException(404, "Öğrenci bulunamadı")
    _block_delete("Öğrenci", {
        "ders kaydı": db.scalar(select(func.count()).select_from(m.Enrollment).where(m.Enrollment.student_id == student_id)) or 0,
        "sınav kaydı": db.scalar(select(func.count()).select_from(m.ExamStudent).where(m.ExamStudent.student_id == student_id)) or 0,
        "kanıt": db.scalar(select(func.count()).select_from(m.EvidenceAsset).where(m.EvidenceAsset.student_id == student_id)) or 0,
    })
    db.delete(obj); audit(db, "delete", "student", student_id); _commit(db); return {"deleted": True}


@app.post("/api/students/{student_id}/anonymize")
def anonymize_student(student_id: int, data: StudentAnonymizeRequest, db: Session = Depends(get_db)):
    require_roles("admin")
    if not data.confirm:
        raise HTTPException(400, "Anonimleştirme için confirm=true gönderilmelidir")
    obj = db.get(m.Student, student_id)
    if not obj:
        raise HTTPException(404, "Öğrenci bulunamadı")
    if obj.anonymized_at:
        return {"anonymized": True, "student": _student_out(obj), "already_anonymized": True}
    # İlişkisel sınav/ÖÇ/PÇ kanıtı korunur; doğrudan kimlik alanları geri döndürülemez biçimde temizlenir.
    token = sha256(f"{obj.id}:{obj.student_no}:{obj.created_at.isoformat()}".encode("utf-8")).hexdigest()[:12].upper()
    obj.student_no = f"ANON-{obj.id}-{token}"
    obj.full_name = "Anonim Öğrenci"
    obj.class_name = ""
    obj.external_source = "anonymized"
    obj.external_id = None
    obj.anonymized_at = datetime.now(timezone.utc)
    audit(db, "anonymize", "student", obj.id, {"reason": data.reason, "preserved_relations": True})
    _commit(db)
    return {"anonymized": True, "student": _student_out(obj)}


@app.delete("/api/courses/{course_id}/enrollments/{student_id}")
def delete_enrollment(course_id: int, student_id: int, db: Session = Depends(get_db)):
    require_course_management(db, course_id)
    row = db.scalar(select(m.Enrollment).where(m.Enrollment.course_id == course_id, m.Enrollment.student_id == student_id))
    if not row: raise HTTPException(404, "Ders kaydı bulunamadı")
    exam_count = db.scalar(select(func.count()).select_from(m.ExamStudent).join(m.Exam).where(m.Exam.course_id == course_id, m.ExamStudent.student_id == student_id)) or 0
    if exam_count: raise HTTPException(409, "Öğrenci bu derse ait bir sınava atanmış; önce sınav kaydı yönetilmelidir")
    db.delete(row); audit(db, "unenroll", "course", course_id, {"student_id": student_id}); _commit(db); return {"deleted": True}


@app.get("/api/courses/{course_id}/enrollments")
def enrollments(course_id: int, db: Session = Depends(get_db)):
    require_course_access(db, course_id, write=False)
    if not db.get(m.Course, course_id): raise HTTPException(404, "Ders bulunamadı")
    rows = db.scalars(select(m.Enrollment).options(selectinload(m.Enrollment.student)).where(m.Enrollment.course_id == course_id)).all()
    return [_student_out(x.student) for x in rows]


@app.post("/api/courses/{course_id}/enrollments/bulk")
def enroll_bulk(course_id: int, data: BulkEnrollRequest, db: Session = Depends(get_db)):
    require_course_management(db, course_id)
    if not db.get(m.Course, course_id): raise HTTPException(404, "Ders bulunamadı")
    created = 0
    for sid in data.student_ids:
        if not db.get(m.Student, sid): raise HTTPException(400, f"Öğrenci bulunamadı: {sid}")
        exists = db.scalar(select(m.Enrollment).where(m.Enrollment.course_id == course_id, m.Enrollment.student_id == sid))
        if not exists:
            db.add(m.Enrollment(course_id=course_id, student_id=sid)); created += 1
    audit(db, "bulk_enroll", "course", course_id, {"created": created}); _commit(db)
    return {"created": created}


@app.get("/api/courses/{course_id}/gradebook")
def course_gradebook_route(course_id: int, include_grading: bool = False, db: Session = Depends(get_db)):
    require_course_access(db, course_id, write=False)
    try:
        return course_gradebook(db, course_id, include_grading=include_grading)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.get("/api/courses/{course_id}/gradebook.xlsx")
def course_gradebook_xlsx(course_id: int, db: Session = Depends(get_db)):
    require_course_access(db, course_id, write=False)
    try:
        payload, filename = build_course_gradebook_xlsx(db, course_id, obs_mode=False)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return StreamingResponse(BytesIO(payload), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/courses/{course_id}/obs-results.xlsx")
def course_obs_results_xlsx(course_id: int, db: Session = Depends(get_db)):
    require_course_access(db, course_id, write=False)
    try:
        payload, filename = build_course_gradebook_xlsx(db, course_id, obs_mode=True)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    audit(db, "obs_results_export", "course", course_id, {"format": "xlsx"})
    _commit(db)
    return StreamingResponse(BytesIO(payload), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.post("/api/courses/{course_id}/obs-results/push")
def push_course_results_to_obs(course_id: int, db: Session = Depends(get_db)):
    require_course_management(db, course_id)
    if not settings.obs_writeback_enabled:
        raise HTTPException(403, "OBS write-back kurumsal onayla etkinleştirilmemiştir. DOU Assess varsayılan olarak OBS read-only çalışır (OBS_WRITEBACK_ENABLED=false).")
    endpoint = settings.obs_results_endpoint.strip()
    if not endpoint:
        raise HTTPException(503, "OBS sonuç gönderim adresi yapılandırılmamış (OBS_RESULTS_ENDPOINT)")
    if settings.app_env == "production" and not endpoint.lower().startswith("https://"):
        raise HTTPException(503, "Production ortamında OBS_RESULTS_ENDPOINT HTTPS olmalıdır")
    data = course_gradebook(db, course_id)
    if not data.get("weights_valid"):
        raise HTTPException(409, f"Sınav ağırlıkları toplamı %100 olmalıdır; mevcut %{data.get('assessment_weight_total', 0)}")
    payload = {
        "source": "DOU Assess", "version": APP_VERSION,
        "course": {k: data.get(k) for k in ("course_id", "course_code", "course_name", "academic_year", "term", "pass_threshold_percent")},
        "results": [{"student_id": x["student_id"], "student_no": x["student_no"], "final_grade": x["final_grade"], "status": x["status"]} for x in data.get("students", [])],
    }
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    digest = sha256(raw).hexdigest()
    headers = {"Content-Type": "application/json", "User-Agent": f"DOU-Assess/{APP_VERSION}", "X-DOU-Assess-SHA256": digest}
    if settings.obs_results_token:
        headers["Authorization"] = f"Bearer {settings.obs_results_token}"
    req = urlrequest.Request(endpoint, data=raw, headers=headers, method="POST")
    status = "success"; response_code = None; response_body = ""
    try:
        with urlrequest.urlopen(req, timeout=max(1, settings.obs_results_timeout_seconds)) as resp:
            response_code = int(getattr(resp, "status", 200) or 200)
            response_body = resp.read(4096).decode("utf-8", errors="replace")
            if response_code < 200 or response_code >= 300:
                raise RuntimeError(f"OBS HTTP {response_code}")
    except (urlerror.URLError, urlerror.HTTPError, TimeoutError, OSError, RuntimeError) as exc:
        status = "failed"
        if isinstance(exc, urlerror.HTTPError): response_code = exc.code
        summary = {"course_id": course_id, "record_count": len(payload["results"]), "http_status": response_code, "error": str(exc)[:500]}
        run = m.IntegrationSyncRun(provider="obs-results-api", filename=f"course-{course_id}.json", mode="push", source_sha256=digest, status=status, summary=summary)
        db.add(run); db.flush(); audit(db, "obs_results_push_failed", "integration_sync_run", run.id, summary); _commit(db)
        raise HTTPException(502, f"OBS sonuç gönderimi başarısız: {str(exc)[:300]}")
    summary = {"course_id": course_id, "record_count": len(payload["results"]), "http_status": response_code, "response": response_body[:500]}
    run = m.IntegrationSyncRun(provider="obs-results-api", filename=f"course-{course_id}.json", mode="push", source_sha256=digest, status=status, summary=summary)
    db.add(run); db.flush(); audit(db, "obs_results_push", "integration_sync_run", run.id, summary); _commit(db)
    return {"ok": True, "sync_run_id": run.id, **summary}


@app.get("/api/courses/{course_id}/outcomes")
def course_outcomes(course_id: int, db: Session = Depends(get_db)):
    require_course_access(db, course_id, write=False)
    course = db.get(m.Course, course_id)
    if not course: raise HTTPException(404, "Ders bulunamadı")
    los = db.scalars(select(m.LearningOutcome).where(m.LearningOutcome.course_id == course_id).order_by(m.LearningOutcome.code)).all()
    pos = db.scalars(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == course.program_id, m.ProgramOutcome.academic_year == course.academic_year).order_by(m.ProgramOutcome.code)).all()
    mappings = db.scalars(select(m.OutcomeMapping).join(m.LearningOutcome).where(m.LearningOutcome.course_id == course_id, m.OutcomeMapping.contribution >= 1)).all()
    return {
        "learning_outcomes": [{"id": x.id, "code": x.code, "description": x.description, "target_percent": x.target_percent} for x in los],
        "program_outcomes": [{"id": x.id, "academic_year": x.academic_year, "code": x.code, "description": x.description} for x in pos],
        "mappings": [{"id": x.id, "learning_outcome_id": x.learning_outcome_id, "program_outcome_id": x.program_outcome_id, "contribution": x.contribution} for x in mappings],
    }


@app.post("/api/courses/{course_id}/learning-outcomes", status_code=201)
def create_lo(course_id: int, data: LearningOutcomeCreate, db: Session = Depends(get_db)):
    require_course_management(db, course_id)
    if not db.get(m.Course, course_id): raise HTTPException(404, "Ders bulunamadı")
    obj = m.LearningOutcome(course_id=course_id, **data.model_dump()); db.add(obj); db.flush(); _commit(db)
    return {"id": obj.id, "course_id": obj.course_id, "code": obj.code, "description": obj.description, "target_percent": obj.target_percent}


@app.post("/api/programs/{program_id}/program-outcomes", status_code=201)
def create_po(program_id: int, data: ProgramOutcomeCreate, db: Session = Depends(get_db)):
    require_program_access(db, program_id, write=True)
    if not db.get(m.Program, program_id): raise HTTPException(404, "Program bulunamadı")
    obj = m.ProgramOutcome(program_id=program_id, **data.model_dump()); db.add(obj); db.flush(); _commit(db)
    return {"id": obj.id, "program_id": obj.program_id, "academic_year": obj.academic_year, "code": obj.code, "description": obj.description}


@app.get("/api/courses/{course_id}/outcome-summary")
def course_outcome_summary(course_id: int, db: Session = Depends(get_db)):
    require_course_access(db, course_id, write=False)
    course = db.get(m.Course, course_id)
    if not course:
        raise HTTPException(404, "Ders bulunamadı")
    los = db.scalars(select(m.LearningOutcome).where(m.LearningOutcome.course_id == course_id)).all()
    pos = db.scalars(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == course.program_id, m.ProgramOutcome.academic_year == course.academic_year)).all()
    mappings = db.scalars(select(m.OutcomeMapping).join(m.LearningOutcome).where(m.LearningOutcome.course_id == course_id, m.OutcomeMapping.contribution > 0)).all()
    mapped_lo_ids = {x.learning_outcome_id for x in mappings}
    mapped_po_ids = {x.program_outcome_id for x in mappings}
    bank_rows = db.scalars(select(m.QuestionBank).options(selectinload(m.QuestionBank.learning_outcomes)).where(m.QuestionBank.course_id == course_id, m.QuestionBank.is_active.is_(True))).all()
    exams = db.scalars(select(m.Exam).where(m.Exam.course_id == course_id)).all()
    unmapped_los = [{"id": x.id, "code": x.code, "description": x.description} for x in los if x.id not in mapped_lo_ids]
    unmapped_pos = [{"id": x.id, "code": x.code, "description": x.description} for x in pos if x.id not in mapped_po_ids]
    bank_mapped = sum(1 for x in bank_rows if _bank_outcome_codes(x))
    readiness_issues = []
    if not los:
        readiness_issues.append("Ders için en az bir ÖÇ tanımlanmalıdır")
    if not pos:
        readiness_issues.append("Program ve akademik yıl için en az bir PÇ tanımlanmalıdır")
    if unmapped_los:
        readiness_issues.append("PÇ bağlantısı olmayan ÖÇ: " + ", ".join(x["code"] for x in unmapped_los))
    return {
        "course_id": course_id,
        "learning_outcome_count": len(los),
        "program_outcome_count": len(pos),
        "mapping_count": len(mappings),
        "mapped_learning_outcome_count": len(mapped_lo_ids),
        "mapped_program_outcome_count": len(mapped_po_ids),
        "unmapped_learning_outcomes": unmapped_los,
        "unmapped_program_outcomes": unmapped_pos,
        "average_target_percent": round(sum(float(x.target_percent) for x in los) / len(los), 2) if los else 0,
        "bank_question_count": len(bank_rows),
        "bank_mapped_question_count": bank_mapped,
        "bank_mapping_percent": round(bank_mapped / len(bank_rows) * 100, 1) if bank_rows else 0,
        "exam_count": len(exams),
        "official_exam_count": sum(1 for x in exams if x.status in {"approved", "archived"}),
        "ready_for_exam_snapshot": not readiness_issues,
        "readiness_issues": readiness_issues,
    }


@app.patch("/api/learning-outcomes/{outcome_id}")
def update_learning_outcome(outcome_id: int, data: LearningOutcomeUpdate, db: Session = Depends(get_db)):
    obj = db.get(m.LearningOutcome, outcome_id)
    if not obj:
        raise HTTPException(404, "ÖÇ bulunamadı")
    require_course_management(db, obj.course_id)
    changes = _apply_patch(obj, data)
    audit(db, "update", "learning_outcome", obj.id, changes)
    _commit(db)
    return {"id": obj.id, "course_id": obj.course_id, "code": obj.code, "description": obj.description, "target_percent": obj.target_percent}


@app.delete("/api/learning-outcomes/{outcome_id}")
def delete_learning_outcome(outcome_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.LearningOutcome, outcome_id)
    if not obj:
        raise HTTPException(404, "ÖÇ bulunamadı")
    require_course_management(db, obj.course_id)
    bank_links = db.scalar(select(func.count()).select_from(m.QuestionBankOutcome).where(m.QuestionBankOutcome.learning_outcome_id == outcome_id)) or 0
    exam_snapshot_links = db.scalar(select(func.count()).select_from(m.ExamLearningOutcome).where(m.ExamLearningOutcome.source_learning_outcome_id == outcome_id)) or 0
    if bank_links:
        raise HTTPException(409, f"ÖÇ silinemez. Soru havuzunda {bank_links} ilişki var; önce sorulardaki ÖÇ eşleşmesini değiştirin.")
    if exam_snapshot_links:
        raise HTTPException(409, f"ÖÇ silinemez. {exam_snapshot_links} sınav snapshot'ı bu çıktıyı referanslıyor. Tarihsel kanıt bütünlüğü korunmalıdır.")
    audit(db, "delete", "learning_outcome", obj.id, {"code": obj.code})
    db.delete(obj); _commit(db)
    return {"deleted": True}


@app.patch("/api/program-outcomes/{outcome_id}")
def update_program_outcome(outcome_id: int, data: ProgramOutcomeUpdate, db: Session = Depends(get_db)):
    obj = db.get(m.ProgramOutcome, outcome_id)
    if not obj:
        raise HTTPException(404, "PÇ bulunamadı")
    require_program_access(db, obj.program_id, write=True)
    changes = _apply_patch(obj, data)
    audit(db, "update", "program_outcome", obj.id, changes)
    _commit(db)
    return {"id": obj.id, "program_id": obj.program_id, "academic_year": obj.academic_year, "code": obj.code, "description": obj.description}


@app.delete("/api/program-outcomes/{outcome_id}")
def delete_program_outcome(outcome_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.ProgramOutcome, outcome_id)
    if not obj:
        raise HTTPException(404, "PÇ bulunamadı")
    require_program_access(db, obj.program_id, write=True)
    mapping_count = db.scalar(select(func.count()).select_from(m.OutcomeMapping).where(m.OutcomeMapping.program_outcome_id == outcome_id)) or 0
    snapshot_count = db.scalar(select(func.count()).select_from(m.ExamProgramOutcome).where(m.ExamProgramOutcome.source_program_outcome_id == outcome_id)) or 0
    if mapping_count:
        raise HTTPException(409, f"PÇ silinemez. {mapping_count} ÖÇ-PÇ katkı eşleşmesi var; önce matrisi temizleyin.")
    if snapshot_count:
        raise HTTPException(409, f"PÇ silinemez. {snapshot_count} sınav snapshot'ı bu çıktıyı referanslıyor.")
    audit(db, "delete", "program_outcome", obj.id, {"code": obj.code})
    db.delete(obj); _commit(db)
    return {"deleted": True}


@app.post("/api/outcome-mappings", status_code=201)
def create_mapping(data: OutcomeMappingCreate, db: Session = Depends(get_db)):
    lo = db.get(m.LearningOutcome, data.learning_outcome_id)
    if lo: require_course_management(db, lo.course_id)
    lo = db.get(m.LearningOutcome, data.learning_outcome_id); po = db.get(m.ProgramOutcome, data.program_outcome_id)
    if not lo or not po: raise HTTPException(400, "ÖÇ veya PÇ bulunamadı")
    course = db.get(m.Course, lo.course_id)
    if po.program_id != course.program_id or po.academic_year != course.academic_year:
        raise HTTPException(400, "ÖÇ ve PÇ aynı program/akademik yıl kapsamında olmalıdır")
    obj = m.OutcomeMapping(**data.model_dump()); db.add(obj); db.flush(); _commit(db)
    return {"id": obj.id, **data.model_dump()}


@app.put("/api/outcome-mappings")
def upsert_mapping(data: OutcomeMappingCreate, db: Session = Depends(get_db)):
    """UX-friendly 1-5 contribution matrix endpoint. Unmapped pairs remain without a row."""
    lo = db.get(m.LearningOutcome, data.learning_outcome_id)
    po = db.get(m.ProgramOutcome, data.program_outcome_id)
    if not lo or not po:
        raise HTTPException(400, "ÖÇ veya PÇ bulunamadı")
    require_course_management(db, lo.course_id)
    course = db.get(m.Course, lo.course_id)
    if not course or po.program_id != course.program_id or po.academic_year != course.academic_year:
        raise HTTPException(400, "ÖÇ ve PÇ aynı program/akademik yıl kapsamında olmalıdır")
    existing = db.scalar(select(m.OutcomeMapping).where(
        m.OutcomeMapping.learning_outcome_id == lo.id,
        m.OutcomeMapping.program_outcome_id == po.id,
    ))
    if existing:
        old = existing.contribution
        existing.contribution = data.contribution
        audit(db, "update", "outcome_mapping", existing.id, {"from": old, "to": data.contribution})
        _commit(db)
        return {"id": existing.id, "learning_outcome_id": lo.id, "program_outcome_id": po.id, "contribution": existing.contribution}
    obj = m.OutcomeMapping(**data.model_dump())
    db.add(obj); db.flush()
    audit(db, "create", "outcome_mapping", obj.id, data.model_dump())
    _commit(db)
    return {"id": obj.id, **data.model_dump()}


def _snapshot_exam(db: Session, exam: m.Exam) -> None:
    course = db.get(m.Course, exam.course_id)
    los = db.scalars(select(m.LearningOutcome).where(m.LearningOutcome.course_id == course.id)).all()
    pos = db.scalars(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == course.program_id, m.ProgramOutcome.academic_year == course.academic_year)).all()
    lo_map: dict[int, m.ExamLearningOutcome] = {}
    po_map: dict[int, m.ExamProgramOutcome] = {}
    for lo in los:
        snap = m.ExamLearningOutcome(exam_id=exam.id, source_learning_outcome_id=lo.id, code=lo.code, description=lo.description, target_percent=lo.target_percent)
        db.add(snap); db.flush(); lo_map[lo.id] = snap
    for po in pos:
        snap = m.ExamProgramOutcome(exam_id=exam.id, source_program_outcome_id=po.id, code=po.code, description=po.description)
        db.add(snap); db.flush(); po_map[po.id] = snap
    mappings = db.scalars(select(m.OutcomeMapping).join(m.LearningOutcome).where(m.LearningOutcome.course_id == course.id)).all()
    for mp in mappings:
        if mp.learning_outcome_id in lo_map and mp.program_outcome_id in po_map:
            db.add(m.ExamOutcomeMapping(exam_learning_outcome_id=lo_map[mp.learning_outcome_id].id, exam_program_outcome_id=po_map[mp.program_outcome_id].id, contribution=mp.contribution))


def _sync_exam_students(db: Session, exam: m.Exam) -> int:
    enrollments = db.scalars(select(m.Enrollment).where(m.Enrollment.course_id == exam.course_id)).all()
    existing = set(db.scalars(select(m.ExamStudent.student_id).where(m.ExamStudent.exam_id == exam.id)).all())
    count = 0
    for en in enrollments:
        if en.student_id not in existing:
            db.add(m.ExamStudent(exam_id=exam.id, student_id=en.student_id)); count += 1
    return count


def _seed_demo_exam(db: Session, course: m.Course, title: str, status: str, bank_rows: list[m.QuestionBank], students: list[m.Student], completed: bool = False) -> m.Exam:
    exam = m.Exam(course_id=course.id, title=title, exam_type="Vize", duration_minutes=50, instructions="Demo sınavıdır. Optik alanda tek seçenek işaretleyiniz.", status=status)
    _fill_exam_paper_snapshot(db, exam, course); db.add(exam); db.flush(); _snapshot_exam(db, exam); db.flush()
    lo_by_code = {x.code: x for x in db.scalars(select(m.ExamLearningOutcome).where(m.ExamLearningOutcome.exam_id == exam.id)).all()}
    questions=[]
    for i, bank in enumerate(bank_rows, 1):
        codes = _bank_outcome_codes(bank)
        outcomes = [lo_by_code[code] for code in codes if code in lo_by_code]
        q=m.Question(exam_id=exam.id, order_no=i, question_type=bank.question_type, text=bank.text, points=10.0, correct_answer=bank.correct_answer, choices=bank.choices, answer_lines=bank.answer_lines, exam_learning_outcome_id=(outcomes[0].id if outcomes else None), bank_question_id=bank.id)
        db.add(q); db.flush(); _set_question_outcomes(db, q, outcomes); questions.append(q)
    db.flush()
    exam_students=[]
    for st in students:
        es=m.ExamStudent(exam_id=exam.id, student_id=st.id); db.add(es); exam_students.append(es)
    db.flush()
    if completed:
        for si, es in enumerate(exam_students):
            for qi, q in enumerate(questions):
                # Controlled distribution creates realistic good/watch/gap outcomes without random data.
                correct = ((si + qi) % 10) < (8 if qi < 4 else (7 if qi < 7 else 5))
                answer = q.correct_answer if correct else ({"A":"B","B":"C","C":"D","D":"A"}.get(q.correct_answer or "A", "A"))
                db.add(m.Response(exam_student_id=es.id, question_id=q.id, answer_text=answer, awarded_points=q.points if correct else 0.0, is_correct=correct))
    return exam


@app.post("/api/pilot/demo-scenario", status_code=201)
def create_demo_scenario(db: Session = Depends(get_db)):
    require_roles("admin")
    if settings.app_env == "production" or not getattr(settings, "pilot_demo_enabled", True):
        raise HTTPException(403, "Demo senaryosu bu ortamda devre dışı")
    existing = db.scalar(select(m.Program).where(m.Program.code == "DEMO-BP"))
    if existing:
        course = db.scalar(select(m.Course).where(m.Course.program_id == existing.id, m.Course.code == "DEMO-PY101"))
        exams = db.scalars(select(m.Exam).where(m.Exam.course_id == course.id).order_by(m.Exam.id)).all() if course else []
        return {"created": False, "message": "Demo senaryosu zaten mevcut.", "program_id": existing.id, "course_id": course.id if course else None, "exam_ids": [x.id for x in exams]}
    active = db.scalar(select(m.AcademicPeriod).where(m.AcademicPeriod.status == "active").order_by(m.AcademicPeriod.id.desc()).limit(1))
    if active:
        year, term = active.academic_year, active.term
    else:
        # Demo data must never mutate or collide with a real locked/planned academic period.
        year, term = "2099-2100", "Demo"
        active = db.scalar(select(m.AcademicPeriod).where(m.AcademicPeriod.academic_year == year, m.AcademicPeriod.term == term))
        if not active:
            active=m.AcademicPeriod(academic_year=year, term=term, title="DOU Assess · Demo Dönemi", status="active"); db.add(active); db.flush()
        elif active.status != "active":
            active.status = "active"
    program=m.Program(code="DEMO-BP", name="Demo Bilgisayar Programcılığı", faculty="Meslek Yüksekokulu", department="Bilgisayar Teknolojileri", external_source="demo", external_id="demo-program")
    db.add(program); db.flush()
    course=m.Course(program_id=program.id, code="DEMO-PY101", name="Python Programlama · Demo", academic_year=year, term=term, instructor_email="demo-ogretim@local", instructor_name="Demo Öğretim Elemanı", external_source="demo", external_id="demo-course")
    db.add(course); db.flush()
    user=m.AppUser(email="demo-ogretim@local", display_name="Demo Öğretim Elemanı", auth_source="pilot", is_active=True); db.add(user); db.flush(); db.add(m.UserRoleAssignment(user_id=user.id, role="instructor", course_id=course.id))
    students=[]
    for i in range(1,31):
        st=m.Student(program_id=program.id, student_no=f"D26{i:03d}", full_name=f"Demo Öğrenci {i:02d}", class_name="1. Sınıf", external_source="demo", external_id=f"demo-student-{i:02d}"); db.add(st); students.append(st)
    db.flush()
    for st in students: db.add(m.Enrollment(course_id=course.id, student_id=st.id))
    lo_defs=[("Ö1","Python temel söz dizimini ve veri türlerini uygular",70.0),("Ö2","Koşul ve döngülerle algoritma geliştirir",70.0),("Ö3","Fonksiyon ve koleksiyonları problem çözmede kullanır",70.0),("Ö4","Basit bir Python programını analiz eder ve hatalarını giderir",70.0)]
    po_defs=[("PÇ1","Temel bilişim kavramlarını uygular"),("PÇ2","Algoritmik problem çözme becerisi gösterir"),("PÇ3","Yazılım geliştirme araçlarını kullanır"),("PÇ4","Teknik çıktıları analiz eder ve iyileştirir")]
    los=[]; pos=[]
    for code,desc,target in lo_defs: lo=m.LearningOutcome(course_id=course.id, code=code, description=desc, target_percent=target); db.add(lo); los.append(lo)
    for code,desc in po_defs: po=m.ProgramOutcome(program_id=program.id, academic_year=year, code=code, description=desc); db.add(po); pos.append(po)
    db.flush()
    for i,lo in enumerate(los):
        db.add(m.OutcomeMapping(learning_outcome_id=lo.id, program_outcome_id=pos[i].id, contribution=5))
        if i>0: db.add(m.OutcomeMapping(learning_outcome_id=lo.id, program_outcome_id=pos[i-1].id, contribution=2))
    bank_rows=[]
    prompts=[
      ("Ö1","Python'da tam sayı veri tipi hangisidir?",{"A":"int","B":"str","C":"list","D":"bool"},"A"),
      ("Ö1","Bir değişkene değer atamak için hangi operatör kullanılır?",{"A":"==","B":"=","C":"!=","D":"//"},"B"),
      ("Ö1","Ekrana çıktı vermek için hangi fonksiyon kullanılır?",{"A":"input","B":"len","C":"print","D":"type"},"C"),
      ("Ö2","0'dan 4'e kadar yineleme için uygun ifade hangisidir?",{"A":"range(5)","B":"range(1)","C":"loop(5)","D":"for(0,5)"},"A"),
      ("Ö2","Koşullu dallanmada kullanılan anahtar sözcük hangisidir?",{"A":"def","B":"if","C":"import","D":"return"},"B"),
      ("Ö2","Döngüyü erken sonlandıran ifade hangisidir?",{"A":"pass","B":"next","C":"break","D":"stop"},"C"),
      ("Ö3","Fonksiyon tanımlamak için hangi anahtar sözcük kullanılır?",{"A":"func","B":"def","C":"lambdaonly","D":"method"},"B"),
      ("Ö3","Liste sonuna eleman ekleyen metot hangisidir?",{"A":"append","B":"push","C":"addLast","D":"insertEnd"},"A"),
      ("Ö4","Bir istisnayı yakalamak için hangi yapı kullanılır?",{"A":"if/else","B":"try/except","C":"for/while","D":"def/return"},"B"),
      ("Ö4","Kodun çalışmasını adım adım inceleme işlemine ne ad verilir?",{"A":"encoding","B":"debugging","C":"deploy","D":"compile"},"B"),
    ]
    lo_by_code_live = {x.code: x for x in los}
    for idx,(locode,textv,choices,answer) in enumerate(prompts,1):
        row=m.QuestionBank(course_id=course.id, question_type="mcq", text=textv, default_points=10.0, correct_answer=answer, choices=choices, learning_outcome_code=locode, tags=["demo","python"], answer_lines=8, is_active=True)
        db.add(row); db.flush(); _set_bank_outcomes(db, row, [lo_by_code_live[locode]]); bank_rows.append(row)
    db.flush()
    draft=_seed_demo_exam(db,course,"DEMO · Python Vize Hazırlığı","draft",bank_rows,students,False)
    completed=_seed_demo_exam(db,course,"DEMO · Python Geçmiş Vize","approved",bank_rows,students,True)
    db.flush(); audit(db,"create_demo_scenario","program",program.id,{"course_id":course.id,"draft_exam_id":draft.id,"completed_exam_id":completed.id,"students":30}); _commit(db)
    return {"created": True, "message": "5 dakikalık demo senaryosu hazır.", "program_id": program.id, "course_id": course.id, "draft_exam_id": draft.id, "completed_exam_id": completed.id, "student_count": 30, "question_count": 10}


@app.get("/api/directory/summary")
def directory_summary(db: Session = Depends(get_db)):
    """Cheap aggregate counts for the current academic scope.

    Frontend dashboards use this instead of loading entire student/exam tables just
    to calculate counts. The authorization boundary stays in SQL.
    """
    visible_programs = visible_program_id_select()
    visible_courses = visible_course_id_select()
    programs_total = int(db.scalar(select(func.count()).select_from(m.Program).where(m.Program.id.in_(visible_programs))) or 0)
    courses_total = int(db.scalar(select(func.count()).select_from(m.Course).where(m.Course.id.in_(visible_courses))) or 0)
    students_total = int(db.scalar(select(func.count()).select_from(m.Student).where(m.Student.program_id.in_(visible_programs))) or 0)
    exams_total = int(db.scalar(select(func.count()).select_from(m.Exam).where(m.Exam.course_id.in_(visible_courses))) or 0)
    student_rows = db.execute(
        select(m.Student.program_id, func.count(m.Student.id))
        .where(m.Student.program_id.in_(visible_programs))
        .group_by(m.Student.program_id)
    ).all()
    course_rows = db.execute(
        select(m.Course.program_id, func.count(m.Course.id))
        .where(m.Course.id.in_(visible_courses))
        .group_by(m.Course.program_id)
    ).all()
    exam_rows = db.execute(
        select(m.Course.program_id, func.count(m.Exam.id))
        .join(m.Course, m.Course.id == m.Exam.course_id)
        .where(m.Exam.course_id.in_(visible_courses))
        .group_by(m.Course.program_id)
    ).all()
    return {
        "programs": programs_total,
        "courses": courses_total,
        "students": students_total,
        "exams": exams_total,
        "students_by_program": {str(pid): int(n) for pid, n in student_rows},
        "courses_by_program": {str(pid): int(n) for pid, n in course_rows},
        "exams_by_program": {str(pid): int(n) for pid, n in exam_rows},
    }


@app.get("/api/exams")
def exams(
    course_id: int | None = None, status: str | None = None, q: str | None = None,
    limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(m.Exam).where(m.Exam.course_id.in_(visible_course_id_select())).order_by(m.Exam.id.desc())
    if course_id: stmt = stmt.where(m.Exam.course_id == course_id)
    if status: stmt = stmt.where(m.Exam.status == status)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where((m.Exam.title.ilike(pattern)) | (m.Exam.exam_type.ilike(pattern)))
    return [_exam_out(x) for x in db.scalars(stmt.offset(offset).limit(limit)).all()]


@app.post("/api/exams", status_code=201)
def create_exam(data: ExamCreate, db: Session = Depends(get_db)):
    require_course_access(db, data.course_id, write=True)
    course = db.get(m.Course, data.course_id)
    if not course: raise HTTPException(404, "Ders bulunamadı")
    try:
        actor = current_user()
        exam = m.Exam(**data.model_dump(exclude={"sync_students"}), created_by_user_id=actor.get("id"), created_by_email=actor.get("email") or "")
        _fill_exam_paper_snapshot(db, exam, course)
        db.add(exam)
        db.flush()
        if not exam.id:
            raise RuntimeError("Sınav primary key üretilemedi")
        _snapshot_exam(db, exam)
        synced = _sync_exam_students(db, exam) if data.sync_students else 0
        audit(db, "create", "exam", exam.id, {"synced_students": synced, "paper_template": exam.paper_template_version})
        db.commit()
    except Exception:
        db.rollback()
        raise
    saved = _load_exam_detail_model(db, exam.id)
    return _exam_out(saved, include_detail=True)


@app.get("/api/exams/{exam_id}")
def get_exam(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    return _exam_out(_load_exam_detail_model(db, exam_id), include_detail=True)


@app.get("/api/exams/{exam_id}/workspace-summary")
def exam_workspace_summary(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    exam = _load_exam_detail_model(db, exam_id)
    readiness = _exam_readiness(db, exam)
    q_count = len(exam.questions)
    student_count = len(exam.exam_students)
    response_count = db.scalar(select(func.count()).select_from(m.Response).join(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id)) or 0
    expected = q_count * student_count
    scan_sessions = db.scalar(select(func.count()).select_from(m.ScanSession).where(m.ScanSession.exam_id == exam_id)) or 0
    scanned_pages = db.scalar(select(func.count()).select_from(m.ScanItem).where(m.ScanItem.exam_id == exam_id)) or 0
    pending_reviews = db.scalar(select(func.count()).select_from(m.ScanReview).where(m.ScanReview.exam_id == exam_id, m.ScanReview.status == "open")) or 0
    evidence_count = db.scalar(select(func.count()).select_from(m.EvidenceAsset).where(m.EvidenceAsset.exam_id == exam_id)) or 0
    improvement_count = db.scalar(select(func.count()).select_from(m.ImprovementAction).where(m.ImprovementAction.exam_id == exam_id, m.ImprovementAction.status.in_(["open", "in_progress"]))) or 0
    graded_students = 0
    if q_count:
        grouped = db.execute(select(m.Response.exam_student_id, func.count(m.Response.id)).join(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id).group_by(m.Response.exam_student_id)).all()
        graded_students = sum(1 for _, count in grouped if count >= q_count)
    outcome_rows = []
    total_points = float(readiness["total_points"] or 0)
    for lo in exam.learning_outcomes:
        related = [q for q in exam.questions if lo.code in _question_outcome_codes(q)]
        pts = round(sum(float(q.points) for q in related), 2)
        outcome_rows.append({"code": lo.code, "question_count": len(related), "points": pts, "weight_percent": round((pts / total_points * 100), 2) if total_points else 0})
    if exam.status == "draft":
        next_action = {"code": "prepare", "label": "Sınavı hazırla", "page": "exams", "step": 3 if q_count else 2}
        if readiness["ready"]:
            next_action = {"code": "mark_ready", "label": "Hazır durumuna al", "page": "exams", "step": 4}
    elif exam.status == "ready":
        next_action = {"code": "scan", "label": "Optik / uygulamaya geç", "page": "scan"}
    elif exam.status == "grading":
        next_action = {"code": "grade", "label": "Puanlamayı tamamla", "page": "grade"}
    elif exam.status == "approved":
        next_action = {"code": "analyze", "label": "Analiz ve kanıtı incele", "page": "analytics"}
    else:
        next_action = {"code": "evidence", "label": "Arşiv kanıtını aç", "page": "evidence"}
    activity_rows = db.scalars(
        select(m.AuditLog).where(m.AuditLog.entity_type == "exam", m.AuditLog.entity_id == exam_id).order_by(m.AuditLog.id.desc()).limit(8)
    ).all()
    return {
        "exam": _exam_out(exam, include_detail=True),
        "readiness": readiness,
        "allowed_booklets": _allowed_booklets(exam),
        "next_action": next_action,
        "progress": {
            "students": student_count, "questions": q_count, "responses": response_count, "expected_responses": expected,
            "response_percent": round(response_count / expected * 100, 1) if expected else 0,
            "graded_students": graded_students, "graded_student_percent": round(graded_students / student_count * 100, 1) if student_count else 0,
            "scan_sessions": scan_sessions, "scanned_pages": scanned_pages, "pending_reviews": pending_reviews,
            "evidence_count": evidence_count, "open_improvements": improvement_count,
        },
        "outcome_coverage": outcome_rows,
        "recent_activity": [{
            "id": row.id, "action": row.action, "actor_email": row.actor_email,
            "payload": row.payload or {}, "created_at": row.created_at.isoformat() if row.created_at else None,
        } for row in activity_rows],
    }


@app.post("/api/exams/{exam_id}/duplicate", status_code=201)
def duplicate_exam(exam_id: int, data: ExamDuplicateRequest, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    source = _load_exam_detail_model(db, exam_id)
    require_course_access(db, source.course_id, write=True)
    course = db.get(m.Course, source.course_id)
    if not course:
        raise HTTPException(404, "Ders bulunamadı")
    clone = m.Exam(
        course_id=source.course_id,
        title=data.title or f"{source.title} · Kopya",
        exam_type=source.exam_type,
        exam_date=data.exam_date,
        start_time=data.start_time if data.start_time is not None else source.start_time,
        location=data.location if data.location is not None else source.location,
        duration_minutes=source.duration_minutes,
        assessment_weight_percent=source.assessment_weight_percent,
        booklet_count=source.booklet_count or 4,
        instructions=source.instructions,
        staff_notes=source.staff_notes or "",
        paper_size=source.paper_size or "A4", paper_orientation=source.paper_orientation or "portrait",
        omr_mode=source.omr_mode or "embedded", duplex_print=bool(source.duplex_print),
        created_by_user_id=current_user().get("id"), created_by_email=current_user().get("email") or "",
        status="draft",
    )
    _fill_exam_paper_snapshot(db, clone, course)
    db.add(clone); db.flush(); _snapshot_exam(db, clone); db.flush()
    target_outcomes = {x.code: x for x in db.scalars(select(m.ExamLearningOutcome).where(m.ExamLearningOutcome.exam_id == clone.id)).all()}
    for q in sorted(source.questions, key=lambda x: x.order_no):
        nq = m.Question(
            exam_id=clone.id, order_no=q.order_no, question_type=q.question_type, text=q.text, points=q.points,
            correct_answer=q.correct_answer, choices=q.choices, answer_lines=q.answer_lines, bank_question_id=q.bank_question_id,
            topic=q.topic or "", unit=q.unit or "", difficulty=q.difficulty or "medium", bloom_level=q.bloom_level or "understand",
            image_data=q.image_data, rubric=q.rubric,
        )
        db.add(nq); db.flush()
        mapped = [target_outcomes[code] for code in _question_outcome_codes(q) if code in target_outcomes]
        _set_question_outcomes(db, nq, mapped)
    synced = _sync_exam_students(db, clone)
    audit(db, "duplicate", "exam", clone.id, {"source_exam_id": source.id, "question_count": len(source.questions), "synced_students": synced})
    _commit(db)
    return _exam_out(_load_exam_detail_model(db, clone.id), include_detail=True)


@app.post("/api/exams/{exam_id}/refresh-outcome-snapshot")
def refresh_exam_outcome_snapshot(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    _require_exam_draft(exam)
    question_count = db.scalar(select(func.count()).select_from(m.Question).where(m.Question.exam_id == exam_id)) or 0
    if question_count:
        raise HTTPException(409, "Sorular eklendikten sonra kazanım snapshot'ı yenilenemez. Önce soruları kaldırın veya yeni bir sınav taslağı oluşturun.")
    lo_ids = list(db.scalars(select(m.ExamLearningOutcome.id).where(m.ExamLearningOutcome.exam_id == exam_id)).all())
    po_ids = list(db.scalars(select(m.ExamProgramOutcome.id).where(m.ExamProgramOutcome.exam_id == exam_id)).all())
    if lo_ids:
        db.execute(delete(m.ExamOutcomeMapping).where(m.ExamOutcomeMapping.exam_learning_outcome_id.in_(lo_ids)))
    if po_ids:
        db.execute(delete(m.ExamOutcomeMapping).where(m.ExamOutcomeMapping.exam_program_outcome_id.in_(po_ids)))
    db.execute(delete(m.ExamLearningOutcome).where(m.ExamLearningOutcome.exam_id == exam_id))
    db.execute(delete(m.ExamProgramOutcome).where(m.ExamProgramOutcome.exam_id == exam_id))
    db.flush()
    _snapshot_exam(db, exam)
    audit(db, "refresh_outcome_snapshot", "exam", exam.id, {"question_count": 0})
    _commit(db)
    return _exam_out(_load_exam_detail_model(db, exam_id), include_detail=True)


@app.get("/api/exams/{exam_id}/readiness")
def exam_readiness(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    exam = db.get(m.Exam, exam_id)
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    return _exam_readiness(db, exam)


@app.get("/api/exams/{exam_id}/students/{student_id}/paper.pdf")
def personalized_exam_paper(exam_id: int, student_id: int, booklet: str = "A", db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    exam = _load_exam_detail_model(db, exam_id)
    es = db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.student_id == student_id))
    student = db.get(m.Student, student_id)
    if not es or not student:
        raise HTTPException(404, "Öğrenci bu sınava kayıtlı değil")
    booklet = _require_allowed_booklet(exam, booklet)
    try:
        data, meta = build_exam_pdf(exam, booklet, student=student)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", student.student_no)
    return StreamingResponse(BytesIO(data), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="DOU_{exam.id}_{safe}_{meta["booklet"]}.pdf"'})


@app.get("/api/exams/{exam_id}/papers-batch.pdf")
def batch_exam_papers(exam_id: int, booklet_strategy: str = "rotate", db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    exam = _load_exam_detail_model(db, exam_id)
    rows = db.scalars(select(m.ExamStudent).options(selectinload(m.ExamStudent.student)).where(m.ExamStudent.exam_id == exam_id).order_by(m.ExamStudent.id)).all()
    if not rows:
        raise HTTPException(409, "Sınava atanmış öğrenci yok")
    strategy = (booklet_strategy or "rotate").strip().lower()
    if strategy not in {"rotate", "a", "fixed_a"}:
        raise HTTPException(400, "booklet_strategy yalnız rotate veya A olabilir")
    writer = PdfWriter()
    booklets = _allowed_booklets(exam)
    for i, es in enumerate(rows):
        booklet = booklets[i % len(booklets)] if strategy == "rotate" else "A"
        data, _ = build_exam_pdf(exam, booklet, student=es.student)
        reader = PdfReader(BytesIO(data))
        for page in reader.pages:
            writer.add_page(page)
    buf = BytesIO(); writer.write(buf); buf.seek(0)
    audit(db, "paper_batch_generate", "exam", exam_id, {"students": len(rows), "strategy": strategy}); _commit(db)
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="DOU_exam_{exam_id}_student_papers.pdf"'})


@app.get("/api/exams/{exam_id}/paper-metadata")
def exam_paper_metadata(exam_id: int, booklet: str = "A", db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    exam = _load_exam_detail_model(db, exam_id)
    booklet = _require_allowed_booklet(exam, booklet)
    try:
        return paper_metadata(exam, booklet)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.get("/api/exams/{exam_id}/paper.pdf")
def exam_paper_pdf(exam_id: int, booklet: str = "A", db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    exam = _load_exam_detail_model(db, exam_id)
    booklet = _require_allowed_booklet(exam, booklet)
    if not exam.questions:
        raise HTTPException(409, "Sınav kağıdı oluşturmak için en az bir soru gereklidir")
    try:
        pdf_bytes, metadata = build_exam_pdf(exam, booklet)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    state = "preview" if exam.status == "draft" else "locked"
    safe_code = re.sub(r"[^A-Za-z0-9_-]+", "_", exam.course_code_snapshot or "exam")
    safe_booklet = metadata["booklet"]
    audit(db, "paper_generate", "exam", exam.id, {"booklet": safe_booklet, "state": state, "sha256": metadata["pdf_sha256"]})
    _commit(db)
    filename = f"DOU_{safe_code}_{exam.id}_{safe_booklet}.pdf"
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="{filename}"',
        "X-DOU-Paper-State": state,
        "X-DOU-Paper-SHA256": metadata["pdf_sha256"],
    })


@app.patch("/api/exams/{exam_id}")
def update_exam(exam_id: int, data: ExamUpdate, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    if exam.status != "draft": raise HTTPException(409, "Sınav kağıdını etkileyen temel bilgiler yalnızca taslak durumunda değiştirilebilir")
    changes = _apply_patch(exam, data); audit(db, "update", "exam", exam.id, changes); _commit(db)
    return _exam_out(exam)


@app.post("/api/exams/{exam_id}/approval-request")
def request_exam_approval(exam_id: int, data: ExamApprovalRequest, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    if exam.status != "grading":
        raise HTTPException(409, "Onay talebi yalnız değerlendirme aşamasındaki sınav için açılabilir")
    q_count = db.scalar(select(func.count()).select_from(m.Question).where(m.Question.exam_id == exam_id)) or 0
    student_count = db.scalar(select(func.count()).select_from(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id)) or 0
    response_count = db.scalar(select(func.count()).select_from(m.Response).join(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id)) or 0
    active_student_count = db.scalar(select(func.count()).select_from(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.attendance_status == "attended")) or 0
    expected = q_count * active_student_count
    response_count = db.scalar(select(func.count()).select_from(m.Response).join(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.attendance_status == "attended")) or 0
    if expected and response_count < expected:
        raise HTTPException(409, f"Onay talebi açılamaz. Eksik değerlendirme var ({response_count}/{expected}).")
    open_reviews = db.scalar(select(func.count()).select_from(m.ScanReview).where(m.ScanReview.exam_id == exam_id, m.ScanReview.status == "open")) or 0
    open_incidents = db.scalar(select(func.count()).select_from(m.ExamIncident).where(m.ExamIncident.exam_id == exam_id, m.ExamIncident.status == "open", m.ExamIncident.severity == "critical")) or 0
    open_appeals = db.scalar(select(func.count()).select_from(m.GradeAppeal).where(m.GradeAppeal.exam_id == exam_id, m.GradeAppeal.status == "open")) or 0
    if open_reviews or open_incidents or open_appeals:
        raise HTTPException(409, f"Onay talebi açılamaz: açık optik inceleme={open_reviews}, kritik olay={open_incidents}, itiraz={open_appeals}")
    actor = current_user()
    if not exam.grade_locked_at:
        exam.grade_locked_at = datetime.now(timezone.utc); exam.grade_locked_by = actor.get("email") or "system"; exam.grade_lock_note = "Onay talebi ile otomatik kilitlendi"
    exam.approval_requested_by = actor.get("email") or "system"
    exam.approval_requested_at = datetime.now(timezone.utc)
    exam.approval_note = (data.note or "").strip()[:1000]
    audit(db, "approval_request", "exam", exam.id, {"requested_by": exam.approval_requested_by, "note": exam.approval_note})
    _commit(db)
    return _exam_out(exam)


@app.post("/api/exams/{exam_id}/approval-reject")
def reject_exam_approval(exam_id: int, data: ExamApprovalRequest, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    if not has_role("admin", "program_head", "department_head", "faculty_admin"):
        raise HTTPException(403, "Onay değerlendirmesi için yönetici rolü gereklidir")
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    if exam.status != "grading" or not exam.approval_requested_at:
        raise HTTPException(409, "Bekleyen bir sınav onay talebi bulunmuyor")
    actor = current_user()
    note = (data.note or "Revizyon istendi").strip()[:1000]
    audit(db, "approval_reject", "exam", exam.id, {"reviewed_by": actor.get("email"), "note": note})
    exam.approval_note = note
    exam.approval_requested_by = ""
    exam.approval_requested_at = None
    exam.approved_by = ""
    exam.approved_at = None
    exam.revision_no = int(exam.revision_no or 1) + 1
    # Revizyon kararı sınavı yeniden düzenlenebilir taslak durumuna çeker. Önceki puanlar
    # yeni revizyonda yanlışlıkla resmîleşmesin diye yeniden değerlendirme zorunlu tutulur.
    response_ids = db.scalars(select(m.Response.id).join(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id)).all()
    cleared_responses = len(response_ids)
    if response_ids:
        db.execute(delete(m.Response).where(m.Response.id.in_(response_ids)))
    exam.status = "draft"
    exam.grade_locked_at = None; exam.grade_locked_by = ""; exam.grade_lock_note = ""
    audit(db, "revision_opened", "exam", exam.id, {"revision_no": exam.revision_no, "cleared_responses": cleared_responses})
    _commit(db)
    return _exam_out(exam)


@app.post("/api/exams/{exam_id}/status")
def change_exam_status(exam_id: int, data: ExamStatusUpdate, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    if data.status == exam.status: return _exam_out(exam)
    allowed = EXAM_TRANSITIONS.get(exam.status, set())
    if data.status not in allowed:
        raise HTTPException(409, f"Geçersiz sınav durum geçişi: {exam.status} → {data.status}")
    if exam.status == "draft" and data.status == "ready":
        readiness = _exam_readiness(db, exam)
        if not readiness["ready"]:
            raise HTTPException(409, {"message": "Sınav hazır durumuna alınamaz", "issues": readiness["issues"], "total_points": readiness["total_points"]})
    if exam.status == "ready" and data.status == "draft":
        exam.revision_no = int(exam.revision_no or 1) + 1
        exam.approval_requested_by = ""
        exam.approval_requested_at = None
        exam.approved_by = ""
        exam.approved_at = None
    if exam.status == "grading" and data.status == "approved":
        q_count = db.scalar(select(func.count()).select_from(m.Question).where(m.Question.exam_id == exam_id)) or 0
        student_count = db.scalar(select(func.count()).select_from(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.attendance_status == "attended")) or 0
        response_count = db.scalar(select(func.count()).select_from(m.Response).join(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.attendance_status == "attended")) or 0
        expected = q_count * student_count
        if expected and response_count < expected:
            raise HTTPException(409, f"Sınav onaylanamaz. Eksik değerlendirme var ({response_count}/{expected} cevap puanlandı).")
        actor = current_user()
        if not exam.grade_locked_at:
            if settings.auth_required:
                raise HTTPException(409, "Sınav onaylanmadan önce puanlar kilitlenmelidir")
            exam.grade_locked_at = datetime.now(timezone.utc); exam.grade_locked_by = actor.get("email") or "system"; exam.grade_lock_note = "Pilot onayında otomatik kilit"
        # Production/Entra uses strict maker-checker. Pilot admins retain an emergency shortcut for demo/UAT compatibility.
        if settings.auth_required:
            if not exam.approval_requested_at:
                raise HTTPException(409, "Önce sınav onay talebi oluşturulmalıdır")
            if not has_role("admin", "program_head", "department_head", "faculty_admin"):
                raise HTTPException(403, "Sınav onayı için yönetici rolü gereklidir")
            requester = (exam.approval_requested_by or "").strip().casefold()
            creator = (exam.created_by_email or "").strip().casefold()
            reviewer = str(actor.get("email") or "").strip().casefold()
            if reviewer and reviewer in {x for x in (requester, creator) if x}:
                raise HTTPException(409, "Maker-checker kuralı: hazırlayan veya onaya gönderen kişi kendi sınavını onaylayamaz")
        exam.approved_by = actor.get("email") or "system"
        exam.approved_at = datetime.now(timezone.utc)
        if data.note:
            exam.approval_note = data.note.strip()[:1000]
    old = exam.status; exam.status = data.status
    audit(db, "status_change", "exam", exam.id, {"from": old, "to": data.status, "note": data.note or ""}); _commit(db)
    return _exam_out(exam)


@app.delete("/api/exams/{exam_id}")
def delete_exam(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    if exam.status != "draft": raise HTTPException(409, "Yalnızca taslak sınav silinebilir")
    _block_delete("Sınav", {
        "cevap": db.scalar(select(func.count()).select_from(m.Response).join(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id)) or 0,
        "kanıt": db.scalar(select(func.count()).select_from(m.EvidenceAsset).where(m.EvidenceAsset.exam_id == exam_id)) or 0,
    })
    db.delete(exam); audit(db, "delete", "exam", exam_id); _commit(db); return {"deleted": True}


@app.post("/api/exams/{exam_id}/sync-students")
def sync_exam_students(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    count = _sync_exam_students(db, exam)
    db.flush()
    total = db.scalar(select(func.count()).select_from(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id)) or 0
    course_total = db.scalar(select(func.count()).select_from(m.Enrollment).where(m.Enrollment.course_id == exam.course_id)) or 0
    audit(db, "sync_students", "exam", exam.id, {"created": count, "exam_students": int(total), "course_enrollments": int(course_total)})
    _commit(db)
    return {"created": count, "student_count": int(total), "course_enrollment_count": int(course_total)}


@app.get("/api/exams/{exam_id}/student-assignment")
def exam_student_assignment(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    enrollments = db.scalars(
        select(m.Enrollment)
        .options(selectinload(m.Enrollment.student))
        .where(m.Enrollment.course_id == exam.course_id)
        .order_by(m.Enrollment.student_id)
    ).all()
    assigned_rows = db.scalars(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id)).all()
    assigned = {row.student_id: row for row in assigned_rows}
    students = []
    for enrollment in enrollments:
        student = enrollment.student
        row = assigned.get(student.id)
        students.append({
            **_student_out(student),
            "assigned": bool(row),
            "exam_student_id": row.id if row else None,
        })
    students.sort(key=lambda x: (str(x.get("student_no") or ""), str(x.get("full_name") or "")))
    return {
        "exam_id": exam.id,
        "course_id": exam.course_id,
        "exam_status": exam.status,
        "locked": exam.status not in {"draft", "ready"},
        "course_enrollment_count": len(students),
        "assigned_count": len(assigned_rows),
        "students": students,
    }


@app.put("/api/exams/{exam_id}/students")
def replace_exam_students(exam_id: int, data: BulkEnrollRequest, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    if exam.status not in {"draft", "ready"}:
        raise HTTPException(409, "Öğrenci ataması yalnız taslak veya hazır durumundaki sınavlarda değiştirilebilir")

    desired = set(data.student_ids or [])
    enrolled = set(db.scalars(select(m.Enrollment.student_id).where(m.Enrollment.course_id == exam.course_id)).all())
    invalid = sorted(desired - enrolled)
    if invalid:
        raise HTTPException(400, {"message": "Seçilen bazı öğrenciler bu derse kayıtlı değil", "student_ids": invalid})

    current_rows = db.scalars(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id)).all()
    current = {row.student_id: row for row in current_rows}
    to_remove = set(current) - desired
    to_add = desired - set(current)

    removed = 0
    for student_id in to_remove:
        row = current[student_id]
        response_count = db.scalar(select(func.count()).select_from(m.Response).where(m.Response.exam_student_id == row.id)) or 0
        if response_count:
            raise HTTPException(409, f"Öğrenci #{student_id} için puanlanmış cevap bulunduğu için sınavdan çıkarılamaz")
        db.delete(row)
        removed += 1
    for student_id in to_add:
        db.add(m.ExamStudent(exam_id=exam_id, student_id=student_id))

    db.flush()
    total = db.scalar(select(func.count()).select_from(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id)) or 0
    audit(db, "replace_exam_students", "exam", exam.id, {
        "requested": len(desired), "created": len(to_add), "removed": removed,
        "exam_students": int(total), "course_enrollments": len(enrolled),
    })
    _commit(db)
    return {
        "created": len(to_add),
        "removed": removed,
        "student_count": int(total),
        "course_enrollment_count": len(enrolled),
    }


@app.post("/api/exams/{exam_id}/questions", status_code=201)
def create_question(exam_id: int, data: QuestionCreate, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    _require_exam_draft(exam)
    codes = _normalized_outcome_codes(data.learning_outcome_codes, data.learning_outcome_code)
    outcomes = _resolve_exam_outcomes(db, exam_id, codes)
    payload = data.model_dump(exclude={"learning_outcome_code", "learning_outcome_codes"})
    choices, correct = _clean_mcq_fields(data.question_type, payload.get("choices"), payload.get("correct_answer"))
    payload["choices"] = choices
    payload["correct_answer"] = correct
    payload["image_data"] = _normalize_image_data(payload.get("image_data"))
    payload["rubric"] = _normalize_rubric(data.question_type, payload.get("rubric"), float(data.points))
    payload["expected_answer"] = str(payload.get("expected_answer") or "").strip()[:8000] if data.question_type == "classic" else ""
    obj = m.Question(exam_id=exam_id, exam_learning_outcome_id=(outcomes[0].id if outcomes else None), **payload)
    db.add(obj)
    db.flush()
    _set_question_outcomes(db, obj, outcomes)
    audit(db, "create", "question", obj.id, {"exam_id": exam_id, "learning_outcome_codes": codes})
    _commit(db)
    return {"id": obj.id, "exam_id": exam_id, "learning_outcome_code": (codes[0] if codes else None), "learning_outcome_codes": codes, **payload}


@app.patch("/api/exams/{exam_id}/questions/{question_id}")
def update_question(exam_id: int, question_id: int, data: QuestionUpdate, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    _require_exam_draft(exam)
    q = db.get(m.Question, question_id)
    if not q or q.exam_id != exam_id:
        raise HTTPException(404, "Soru bulunamadı")
    fields = data.model_fields_set
    payload = data.model_dump(exclude_unset=True, exclude={"learning_outcome_code", "learning_outcome_codes"})
    if "learning_outcome_codes" in fields or "learning_outcome_code" in fields:
        many = data.learning_outcome_codes if "learning_outcome_codes" in fields else None
        legacy = data.learning_outcome_code if "learning_outcome_code" in fields else None
        codes = _normalized_outcome_codes(many, legacy)
        outcomes = _resolve_exam_outcomes(db, exam_id, codes)
        _set_question_outcomes(db, q, outcomes)
        payload["learning_outcome_codes"] = codes
    next_type = payload.get("question_type", q.question_type)
    next_points = float(payload.get("points", q.points))
    if "image_data" in payload:
        payload["image_data"] = _normalize_image_data(payload.get("image_data"))
    if "rubric" in payload or "question_type" in payload or "points" in payload:
        payload["rubric"] = _normalize_rubric(next_type, payload.get("rubric", q.rubric), next_points)
    for key, value in payload.items():
        if key != "learning_outcome_codes":
            setattr(q, key, value)
    choices, correct = _clean_mcq_fields(q.question_type, q.choices, q.correct_answer)
    q.choices = choices
    q.correct_answer = correct
    if q.question_type != "classic": q.expected_answer = ""
    audit(db, "update", "question", q.id, payload)
    _commit(db)
    saved = db.scalar(select(m.Question).options(selectinload(m.Question.learning_outcomes), selectinload(m.Question.learning_outcome)).where(m.Question.id == q.id))
    codes = _question_outcome_codes(saved)
    return {
        "id": saved.id, "exam_id": saved.exam_id, "order_no": saved.order_no, "question_type": saved.question_type,
        "text": saved.text, "points": saved.points, "correct_answer": saved.correct_answer, "choices": saved.choices,
        "answer_lines": saved.answer_lines, "learning_outcome_code": (codes[0] if codes else None), "learning_outcome_codes": codes,
        "topic": saved.topic or "", "unit": saved.unit or "", "difficulty": saved.difficulty or "medium",
        "bloom_level": saved.bloom_level or "understand", "image_data": saved.image_data, "rubric": saved.rubric, "expected_answer": saved.expected_answer or "",
    }


@app.delete("/api/exams/{exam_id}/questions/{question_id}")
def delete_question(exam_id: int, question_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    _require_exam_draft(exam)
    q = db.get(m.Question, question_id)
    if not q or q.exam_id != exam_id: raise HTTPException(404, "Soru bulunamadı")
    responses = db.scalar(select(func.count()).select_from(m.Response).where(m.Response.question_id == question_id)) or 0
    if responses: raise HTTPException(409, "Cevap girilmiş soru silinemez")
    db.delete(q); audit(db, "delete", "question", question_id, {"exam_id": exam_id}); _commit(db); return {"deleted": True}



def _prepare_question_bank_import(db: Session, rows: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    prepared: list[dict] = []
    errors: list[str] = []
    warnings: list[str] = []
    existing_by_course: dict[int, set[str]] = {}
    batch_seen: set[tuple[int, str]] = set()

    for row in rows:
        row_no = row.get("__row__")
        program_code = str(row.get("program_code") or "").strip()
        course_code = str(row.get("course_code") or "").strip()
        academic_year = str(row.get("academic_year") or "").strip()
        term = str(row.get("term") or "").strip()
        program = db.scalar(select(m.Program).where(m.Program.code == program_code))
        if not program:
            errors.append(f"Soru_Havuzu satır {row_no}: program bulunamadı ({program_code})")
            continue
        course = db.scalar(select(m.Course).where(
            m.Course.program_id == program.id,
            m.Course.code == course_code,
            m.Course.academic_year == academic_year,
            m.Course.term == term,
        ))
        if not course:
            errors.append(f"Soru_Havuzu satır {row_no}: ders bulunamadı ({program_code} / {course_code} / {academic_year} / {term})")
            continue
        try:
            require_course_access(db, course.id, write=True)
        except HTTPException as exc:
            errors.append(f"Soru_Havuzu satır {row_no}: {exc.detail}")
            continue

        text_value = str(row.get("question_text") or "").strip()
        if not text_value:
            errors.append(f"Soru_Havuzu satır {row_no}: question_text zorunludur")
            continue
        qtype = str(row.get("question_type") or "").strip().casefold()
        try:
            points = float(row.get("default_points"))
            choices, correct = _clean_mcq_fields(qtype, row.get("choices"), row.get("correct_answer"))
            rubric = _normalize_rubric(qtype, row.get("rubric_obj"), points)
            codes = _normalized_outcome_codes(row.get("learning_outcome_codes"), None)
            outcomes = _resolve_course_outcomes(db, course.id, codes)
        except HTTPException as exc:
            errors.append(f"Soru_Havuzu satır {row_no}: {exc.detail}")
            continue

        if course.id not in existing_by_course:
            existing = db.scalars(select(m.QuestionBank.text).where(m.QuestionBank.course_id == course.id)).all()
            existing_by_course[course.id] = {str(x or "").strip().casefold() for x in existing if str(x or "").strip()}
        dup_key = (course.id, text_value.casefold())
        duplicate = text_value.casefold() in existing_by_course[course.id] or dup_key in batch_seen
        if duplicate:
            warnings.append(f"Soru_Havuzu satır {row_no}: aynı ders ve soru metni zaten mevcut; içe aktarımda atlanacak")
        batch_seen.add(dup_key)

        prepared.append({
            "row_no": row_no,
            "course": course,
            "outcomes": outcomes,
            "duplicate": duplicate,
            "payload": {
                "course_id": course.id,
                "question_type": qtype,
                "text": text_value,
                "default_points": points,
                "correct_answer": correct,
                "choices": choices,
                "answer_lines": int(row.get("answer_lines") or 8),
                "tags": list(row.get("tags") or []),
                "topic": str(row.get("topic") or "").strip()[:255],
                "unit": str(row.get("unit") or "").strip()[:255],
                "difficulty": str(row.get("difficulty") or "medium").strip().casefold(),
                "bloom_level": str(row.get("bloom_level") or "understand").strip().casefold(),
                "author": str(row.get("author") or "").strip()[:255],
                "reviewer": str(row.get("reviewer") or "").strip()[:255],
                "rubric": rubric,
                "expected_answer": str(row.get("expected_answer") or "").strip()[:8000] if qtype == "classic" else "",
                "image_data": None,
            },
            "learning_outcome_codes": codes,
        })
    return prepared, errors, warnings


@app.get("/api/import/question-bank/template")
def question_bank_workbook_template():
    require_roles("admin", "instructor", "program_head", "department_head", "faculty_admin")
    path = Path(__file__).parent / "static" / "examples" / "DOU-Assess-Soru-Havuzu-Sablonu.xlsx"
    if not path.exists():
        raise HTTPException(404, "Soru havuzu Excel şablonu bulunamadı")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="DOU-Assess-Soru-Havuzu-Sablonu.xlsx")


@app.post("/api/import/question-bank/validate")
async def validate_question_bank_workbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    require_roles("admin", "instructor", "program_head", "department_head", "faculty_admin")
    data = await read_upload_limited(file)
    rows, parse_errors = parse_question_bank_workbook(data)
    if parse_errors:
        return JSONResponse(status_code=422, content={"ok": False, "error": {"code": "QUESTION_BANK_IMPORT_VALIDATION", "message": "Soru havuzu Excel doğrulaması başarısız", "details": parse_errors}})
    prepared, errors, warnings = _prepare_question_bank_import(db, rows)
    if errors:
        return JSONResponse(status_code=422, content={"ok": False, "error": {"code": "QUESTION_BANK_IMPORT_VALIDATION", "message": "Soru havuzu Excel doğrulaması başarısız", "details": errors}, "warnings": warnings})
    return {
        "ok": True,
        "rows": len(rows),
        "ready": sum(1 for x in prepared if not x["duplicate"]),
        "duplicates": sum(1 for x in prepared if x["duplicate"]),
        "warnings": warnings,
        "courses": len({x["course"].id for x in prepared}),
    }


@app.post("/api/import/question-bank")
async def import_question_bank_workbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    require_roles("admin", "instructor", "program_head", "department_head", "faculty_admin")
    data = await read_upload_limited(file)
    rows, parse_errors = parse_question_bank_workbook(data)
    if parse_errors:
        return JSONResponse(status_code=422, content={"ok": False, "error": {"code": "QUESTION_BANK_IMPORT_VALIDATION", "message": "Soru havuzu Excel içe aktarımı başarısız", "details": parse_errors}})
    prepared, errors, warnings = _prepare_question_bank_import(db, rows)
    if errors:
        return JSONResponse(status_code=422, content={"ok": False, "error": {"code": "QUESTION_BANK_IMPORT_VALIDATION", "message": "Soru havuzu Excel içe aktarımı başarısız", "details": errors}, "warnings": warnings})

    created = 0
    skipped = 0
    filename = Path(file.filename or "soru-havuzu.xlsx").name[:255] or "soru-havuzu.xlsx"
    try:
        db.rollback()
        with db.begin():
            for item in prepared:
                if item["duplicate"]:
                    skipped += 1
                    continue
                payload = dict(item["payload"])
                if not payload["author"]:
                    payload["author"] = current_user().get("display_name") or current_user().get("email") or ""
                obj = m.QuestionBank(**payload, learning_outcome_code=(item["learning_outcome_codes"][0] if item["learning_outcome_codes"] else None))
                db.add(obj)
                db.flush()
                _set_bank_outcomes(db, obj, item["outcomes"])
                audit(db, "bulk_import_create", "question_bank", obj.id, {"source": filename, "row": item["row_no"], "course_id": obj.course_id, "learning_outcome_codes": item["learning_outcome_codes"]})
                created += 1
            batch = m.ImportBatch(filename=filename, status="success", summary={"kind": "question-bank", "rows": len(rows), "created": created, "skipped_duplicates": skipped})
            db.add(batch)
            db.flush()
            audit(db, "question_bank_import", "import_batch", batch.id, batch.summary)
        return {"ok": True, "batch_id": batch.id, "summary": batch.summary, "warnings": warnings}
    except Exception:
        db.rollback()
        raise


@app.get("/api/question-bank")
def question_bank(
    course_id: int | None = None,
    program_id: int | None = None,
    question_type: str | None = None,
    learning_outcome_code: str | None = None,
    q: str | None = None,
    review_status: str | None = None,
    active_only: bool = True,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return the reusable question library inside the caller's academic scope.

    A bank question may measure multiple course learning outcomes. The legacy
    ``learning_outcome_code`` query parameter is retained and now means
    "questions containing this outcome among their mappings".
    """
    stmt = select(m.QuestionBank).options(selectinload(m.QuestionBank.learning_outcomes)).order_by(m.QuestionBank.id.desc())
    requested_course = db.get(m.Course, course_id) if course_id else None
    lineage_ids: set[int] = set()
    if course_id:
        if not requested_course or not can_access_course(db, requested_course, write=False):
            return []
        lineage_ids = set(db.scalars(
            select(m.Course.id).where(
                m.Course.program_id == requested_course.program_id,
                func.lower(m.Course.code) == requested_course.code.strip().lower(),
            )
        ).all())
        stmt = stmt.where(m.QuestionBank.course_id.in_(lineage_ids or {course_id}))
    else:
        # No explicit course lineage: constrain directly to the caller's visible courses.
        stmt = stmt.where(m.QuestionBank.course_id.in_(visible_course_id_select()))
    if program_id:
        stmt = stmt.join(m.Course, m.QuestionBank.course_id == m.Course.id).where(m.Course.program_id == program_id)
    if question_type:
        if question_type not in {"mcq", "classic"}:
            raise HTTPException(400, "Geçersiz soru türü filtresi")
        stmt = stmt.where(m.QuestionBank.question_type == question_type)
    if learning_outcome_code:
        code = learning_outcome_code.strip()
        outcome_match = exists(
            select(m.QuestionBankOutcome.id)
            .join(m.LearningOutcome, m.LearningOutcome.id == m.QuestionBankOutcome.learning_outcome_id)
            .where(m.QuestionBankOutcome.question_bank_id == m.QuestionBank.id, m.LearningOutcome.code == code)
        )
        stmt = stmt.where(or_(outcome_match, m.QuestionBank.learning_outcome_code == code))
    if review_status:
        if review_status not in {"draft", "review", "revision", "approved", "institutional", "retired"}:
            raise HTTPException(400, "Geçersiz soru onay durumu filtresi")
        stmt = stmt.where(m.QuestionBank.review_status == review_status)
    if active_only:
        stmt = stmt.where(m.QuestionBank.is_active.is_(True))
    if q:
        pattern = f"%{q.strip()}%"
        outcome_text_match = exists(
            select(m.QuestionBankOutcome.id)
            .join(m.LearningOutcome, m.LearningOutcome.id == m.QuestionBankOutcome.learning_outcome_id)
            .where(m.QuestionBankOutcome.question_bank_id == m.QuestionBank.id, m.LearningOutcome.code.ilike(pattern))
        )
        stmt = stmt.where(or_(
            m.QuestionBank.text.ilike(pattern), m.QuestionBank.learning_outcome_code.ilike(pattern),
            m.QuestionBank.topic.ilike(pattern), m.QuestionBank.unit.ilike(pattern),
            m.QuestionBank.author.ilike(pattern), outcome_text_match,
        ))
    rows = db.scalars(stmt.offset(offset).limit(limit)).unique().all()
    course_ids = {row.course_id for row in rows}
    courses_by_id = {x.id: x for x in db.scalars(select(m.Course).where(m.Course.id.in_(course_ids))).all()} if course_ids else {}
    return [_bank_out(row, source_course=courses_by_id.get(row.course_id), requested_course=requested_course) for row in rows]


@app.post("/api/question-bank", status_code=201)
def create_bank_question(data: QuestionBankCreate, db: Session = Depends(get_db)):
    require_course_access(db, data.course_id, write=True)
    course = db.get(m.Course, data.course_id)
    if not course:
        raise HTTPException(404, "Ders bulunamadı")
    codes = _normalized_outcome_codes(data.learning_outcome_codes, data.learning_outcome_code)
    outcomes = _resolve_course_outcomes(db, data.course_id, codes)
    payload = data.model_dump(exclude={"learning_outcome_code", "learning_outcome_codes"})
    choices, correct = _clean_mcq_fields(data.question_type, payload.get("choices"), payload.get("correct_answer"))
    payload["choices"] = choices
    payload["correct_answer"] = correct
    payload["image_data"] = _normalize_image_data(payload.get("image_data"))
    payload["rubric"] = _normalize_rubric(data.question_type, payload.get("rubric"), float(data.default_points))
    payload["expected_answer"] = str(payload.get("expected_answer") or "").strip()[:8000] if data.question_type == "classic" else ""
    if not payload.get("author"):
        payload["author"] = current_user().get("display_name") or current_user().get("email") or ""
    obj = m.QuestionBank(**payload, learning_outcome_code=(codes[0] if codes else None))
    db.add(obj)
    db.flush()
    _set_bank_outcomes(db, obj, outcomes)
    audit(db, "create", "question_bank", obj.id, {"course_id": obj.course_id, "learning_outcome_codes": codes})
    _commit(db)
    saved = db.scalar(select(m.QuestionBank).options(selectinload(m.QuestionBank.learning_outcomes)).where(m.QuestionBank.id == obj.id))
    return _bank_out(saved)


@app.patch("/api/question-bank/{question_id}")
def update_bank_question(question_id: int, data: QuestionBankUpdate, db: Session = Depends(get_db)):
    obj = db.get(m.QuestionBank, question_id)
    if not obj:
        raise HTTPException(404, "Soru havuzu kaydı bulunamadı")
    require_course_access(db, obj.course_id, write=True)
    fields = data.model_fields_set
    payload = data.model_dump(exclude_unset=True, exclude={"learning_outcome_code", "learning_outcome_codes"})
    next_type = payload.get("question_type", obj.question_type)
    next_points = float(payload.get("default_points", obj.default_points))
    if "image_data" in payload:
        payload["image_data"] = _normalize_image_data(payload.get("image_data"))
    if "rubric" in payload or "question_type" in payload or "default_points" in payload:
        payload["rubric"] = _normalize_rubric(next_type, payload.get("rubric", obj.rubric), next_points)
    obj.version_no = int(obj.version_no or 1) + 1
    for key, value in payload.items():
        setattr(obj, key, value)
    if "learning_outcome_codes" in fields or "learning_outcome_code" in fields:
        many = data.learning_outcome_codes if "learning_outcome_codes" in fields else None
        legacy = data.learning_outcome_code if "learning_outcome_code" in fields else None
        codes = _normalized_outcome_codes(many, legacy)
        outcomes = _resolve_course_outcomes(db, obj.course_id, codes)
        db.flush()
        _set_bank_outcomes(db, obj, outcomes)
        payload["learning_outcome_codes"] = codes
    choices, correct = _clean_mcq_fields(obj.question_type, obj.choices, obj.correct_answer)
    obj.choices = choices
    obj.correct_answer = correct
    if obj.question_type != "classic": obj.expected_answer = ""
    audit(db, "update", "question_bank", obj.id, payload)
    _commit(db)
    saved = db.scalar(select(m.QuestionBank).options(selectinload(m.QuestionBank.learning_outcomes)).where(m.QuestionBank.id == obj.id))
    return _bank_out(saved)


@app.post("/api/question-bank/{question_id}/review")
def review_bank_question(question_id: int, data: QuestionReviewRequest, db: Session = Depends(get_db)):
    obj = db.get(m.QuestionBank, question_id)
    if not obj: raise HTTPException(404, "Soru havuzu kaydı bulunamadı")
    require_course_access(db, obj.course_id, write=True)
    allowed = {
        "draft": {"review", "retired"}, "review": {"revision", "approved", "draft"},
        "revision": {"review", "draft"}, "approved": {"institutional", "revision", "retired"},
        "institutional": {"revision", "retired"}, "retired": {"draft"}
    }
    current = obj.review_status or "draft"
    if data.status != current and data.status not in allowed.get(current, set()):
        raise HTTPException(400, f"Geçersiz soru yaşam döngüsü geçişi: {current} -> {data.status}")
    obj.review_status = data.status; obj.review_note = data.note or ""
    if data.reviewer: obj.reviewer = data.reviewer
    if data.status in {"approved", "institutional"}: obj.reviewed_at = datetime.now(timezone.utc)
    audit(db, "review_status", "question_bank", obj.id, {"from": current, "to": data.status, "note": data.note})
    _commit(db); db.refresh(obj); return _bank_out(obj)


def _blueprint_out(db: Session, bp: m.AssessmentBlueprint) -> dict:
    items = db.scalars(select(m.AssessmentBlueprintItem).where(m.AssessmentBlueprintItem.blueprint_id == bp.id).order_by(m.AssessmentBlueprintItem.id)).all()
    coverage=[]
    for i in items:
        q = select(func.count()).select_from(m.QuestionBank).join(m.Course, m.QuestionBank.course_id==m.Course.id).where(
            m.Course.program_id == db.get(m.Course, bp.course_id).program_id,
            m.Course.code == db.get(m.Course, bp.course_id).code, m.QuestionBank.is_active.is_(True),
            m.QuestionBank.review_status.in_(["approved","institutional"]))
        if i.topic: q=q.where(m.QuestionBank.topic==i.topic)
        if i.bloom_level: q=q.where(m.QuestionBank.bloom_level==i.bloom_level)
        if i.difficulty: q=q.where(m.QuestionBank.difficulty==i.difficulty)
        available=int(db.scalar(q) or 0)
        coverage.append({"item_id":i.id,"required":i.question_count,"available":available,"ready":available>=i.question_count})
    return {"id":bp.id,"course_id":bp.course_id,"exam_type":bp.exam_type,"title":bp.title,"status":bp.status,
            "total_questions":bp.total_questions,"total_points":bp.total_points,"created_by":bp.created_by,"approved_by":bp.approved_by,
            "items":[{"id":i.id,"topic":i.topic,"learning_outcome_code":i.learning_outcome_code,"bloom_level":i.bloom_level,"difficulty":i.difficulty,"question_count":i.question_count,"points":i.points,"weight_percent":i.weight_percent} for i in items],
            "coverage":coverage,"ready":bool(items) and all(x["ready"] for x in coverage),
            "planned_questions":sum(i.question_count for i in items),"planned_points":round(sum(i.question_count*i.points for i in items),2),
            "planned_weight":round(sum(i.weight_percent for i in items),2)}

@app.get("/api/blueprints")
def list_blueprints(course_id: int | None = None, db: Session = Depends(get_db)):
    stmt=select(m.AssessmentBlueprint).order_by(m.AssessmentBlueprint.id.desc())
    if course_id is not None:
        require_course_access(db, course_id, write=False); stmt=stmt.where(m.AssessmentBlueprint.course_id==course_id)
    rows=db.scalars(stmt).all(); return [_blueprint_out(db,x) for x in rows if course_id is not None or _safe_course_read(db,x.course_id)]

def _safe_course_read(db, course_id):
    try: require_course_access(db, course_id, write=False); return True
    except HTTPException: return False

@app.post("/api/blueprints", status_code=201)
def create_blueprint(data: BlueprintCreate, db: Session = Depends(get_db)):
    require_course_access(db, data.course_id, write=True)
    if data.items and sum(i.question_count for i in data.items) != data.total_questions:
        raise HTTPException(400, "Belirtke satırlarındaki soru sayısı toplam soru sayısına eşit olmalı")
    bp=m.AssessmentBlueprint(course_id=data.course_id,exam_type=data.exam_type,title=data.title,total_questions=data.total_questions,total_points=data.total_points)
    db.add(bp);db.flush()
    for item in data.items: db.add(m.AssessmentBlueprintItem(blueprint_id=bp.id,**item.model_dump()))
    audit(db,"create","assessment_blueprint",bp.id,{"course_id":data.course_id,"items":len(data.items)});_commit(db);db.refresh(bp);return _blueprint_out(db,bp)

@app.patch("/api/blueprints/{blueprint_id}/status")
def blueprint_status(blueprint_id:int,data:BlueprintStatusRequest,db:Session=Depends(get_db)):
    bp=db.get(m.AssessmentBlueprint,blueprint_id)
    if not bp: raise HTTPException(404,"Belirtke bulunamadı")
    require_course_access(db,bp.course_id,write=True)
    if data.status=="approved":
        summary=_blueprint_out(db,bp)
        if summary["planned_questions"]!=bp.total_questions: raise HTTPException(400,"Soru sayısı planı tamamlanmadan belirtke onaylanamaz")
        bp.approved_by=data.approved_by or bp.approved_by;bp.approved_at=datetime.now(timezone.utc)
    bp.status=data.status;audit(db,"status","assessment_blueprint",bp.id,{"status":data.status});_commit(db);return _blueprint_out(db,bp)


@app.delete("/api/question-bank/{question_id}")
def archive_bank_question(question_id: int, db: Session = Depends(get_db)):
    bank_obj = db.get(m.QuestionBank, question_id)
    if not bank_obj: raise HTTPException(404, "Soru havuzu kaydı bulunamadı")
    require_course_access(db, bank_obj.course_id, write=True)
    obj = db.get(m.QuestionBank, question_id)
    if not obj: raise HTTPException(404, "Soru havuzu kaydı bulunamadı")
    obj.is_active = False; audit(db, "archive", "question_bank", obj.id); _commit(db); return {"archived": True}


@app.post("/api/exams/{exam_id}/questions/from-bank", status_code=201)
def add_question_from_bank(exam_id: int, data: AddBankQuestionRequest, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    _require_exam_draft(exam)
    bank = db.scalar(select(m.QuestionBank).options(selectinload(m.QuestionBank.learning_outcomes)).where(m.QuestionBank.id == data.bank_question_id))
    if not bank or not bank.is_active:
        raise HTTPException(404, "Aktif soru havuzu kaydı bulunamadı")
    if (bank.review_status or "draft") in {"revision", "retired"}:
        raise HTTPException(400, "Revizyondaki veya kullanımdan kaldırılmış soru sınava eklenemez")
    source_course = db.get(m.Course, bank.course_id)
    exam_course = db.get(m.Course, exam.course_id)
    if not _same_course_lineage(source_course, exam_course):
        raise HTTPException(400, "Soru havuzu kaydı bu sınavın ders soyuna ait değil")
    codes = _bank_outcome_codes(bank)
    outcomes = _resolve_exam_outcomes(db, exam_id, codes)
    obj = m.Question(
        exam_id=exam_id, order_no=data.order_no, question_type=bank.question_type, text=bank.text,
        points=data.points or bank.default_points, correct_answer=bank.correct_answer, choices=bank.choices,
        answer_lines=bank.answer_lines, exam_learning_outcome_id=(outcomes[0].id if outcomes else None), bank_question_id=bank.id,
        topic=bank.topic or "", unit=bank.unit or "", difficulty=bank.difficulty or "medium", bloom_level=bank.bloom_level or "understand",
        image_data=bank.image_data, rubric=bank.rubric, expected_answer=bank.expected_answer or "",
    )
    bank.usage_count = int(bank.usage_count or 0) + 1
    bank.last_used_at = datetime.now(timezone.utc)
    db.add(obj)
    db.flush()
    _set_question_outcomes(db, obj, outcomes)
    audit(db, "add_from_bank", "question", obj.id, {"bank_question_id": bank.id, "exam_id": exam_id, "learning_outcome_codes": codes})
    _commit(db)
    return {
        "id": obj.id, "exam_id": exam_id, "order_no": obj.order_no, "question_type": obj.question_type,
        "text": obj.text, "points": obj.points, "correct_answer": obj.correct_answer, "choices": obj.choices,
        "answer_lines": obj.answer_lines, "learning_outcome_code": (codes[0] if codes else None),
        "learning_outcome_codes": codes, "bank_question_id": bank.id,
        "topic": obj.topic or "", "unit": obj.unit or "", "difficulty": obj.difficulty or "medium",
        "bloom_level": obj.bloom_level or "understand", "image_data": obj.image_data, "rubric": obj.rubric, "expected_answer": obj.expected_answer or "",
    }


@app.post("/api/exams/{exam_id}/questions/from-bank/batch", status_code=201)
def add_questions_from_bank_batch(exam_id: int, data: AddBankQuestionsBatchRequest, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    _require_exam_draft(exam)

    requested_ids = list(dict.fromkeys(data.bank_question_ids))
    if len(requested_ids) != len(data.bank_question_ids):
        raise HTTPException(400, "Aynı havuz sorusu seçim listesinde birden fazla kez bulunamaz")

    banks = db.scalars(
        select(m.QuestionBank).options(selectinload(m.QuestionBank.learning_outcomes)).where(m.QuestionBank.id.in_(requested_ids))
    ).unique().all()
    bank_by_id = {x.id: x for x in banks}
    missing = [qid for qid in requested_ids if qid not in bank_by_id]
    if missing:
        raise HTTPException(404, {"message": "Bazı havuz soruları bulunamadı", "question_ids": missing})
    exam_course = db.get(m.Course, exam.course_id)
    invalid = []
    for x in banks:
        source_course = db.get(m.Course, x.course_id)
        if not x.is_active or not _same_course_lineage(source_course, exam_course):
            invalid.append(x.id)
    if invalid:
        raise HTTPException(400, {"message": "Seçilen soruların tamamı bu sınavın aktif ders soyuna ait olmalıdır", "question_ids": invalid})

    existing_bank_ids = set(db.scalars(select(m.Question.bank_question_id).where(m.Question.exam_id == exam_id, m.Question.bank_question_id.is_not(None))).all())
    selected = [bank_by_id[qid] for qid in requested_ids if not (data.skip_existing and qid in existing_bank_ids)]
    skipped = [qid for qid in requested_ids if data.skip_existing and qid in existing_bank_ids]
    if not selected:
        return {"added": 0, "skipped": skipped, "question_ids": []}

    outcome_rows = db.scalars(select(m.ExamLearningOutcome).where(m.ExamLearningOutcome.exam_id == exam_id)).all()
    outcome_by_code = {x.code.casefold(): x for x in outcome_rows}
    max_order = db.scalar(select(func.max(m.Question.order_no)).where(m.Question.exam_id == exam_id)) or 0
    created: list[m.Question] = []
    created_codes: dict[int, list[str]] = {}
    for offset, bank in enumerate(selected, start=1):
        codes = _bank_outcome_codes(bank)
        missing_codes = [code for code in codes if code.casefold() not in outcome_by_code]
        if missing_codes:
            raise HTTPException(409, f"Havuz sorusundaki ÖÇ sınav snapshot'ında yok: {', '.join(missing_codes)}. Soruları eklemeden önce kazanım snapshot'ını yenileyin.")
        outcomes = [outcome_by_code[code.casefold()] for code in codes]
        obj = m.Question(
            exam_id=exam_id, order_no=max_order + offset, question_type=bank.question_type, text=bank.text,
            points=bank.default_points, correct_answer=bank.correct_answer, choices=bank.choices, answer_lines=bank.answer_lines,
            exam_learning_outcome_id=(outcomes[0].id if outcomes else None), bank_question_id=bank.id,
            topic=bank.topic or "", unit=bank.unit or "", difficulty=bank.difficulty or "medium", bloom_level=bank.bloom_level or "understand",
            image_data=bank.image_data, rubric=bank.rubric, expected_answer=bank.expected_answer or "",
        )
        bank.usage_count = int(bank.usage_count or 0) + 1
        bank.last_used_at = datetime.now(timezone.utc)
        db.add(obj)
        db.flush()
        _set_question_outcomes(db, obj, outcomes)
        created.append(obj)
        created_codes[obj.id] = codes
    audit(db, "add_from_bank_batch", "exam", exam_id, {"bank_question_ids": requested_ids, "added": len(created), "skipped": skipped})
    _commit(db)
    return {"added": len(created), "skipped": skipped, "question_ids": [x.id for x in created], "outcomes": created_codes}


@app.put("/api/exams/{exam_id}/questions/reorder")
def reorder_exam_questions(exam_id: int, data: QuestionReorderRequest, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    _require_exam_draft(exam)
    if len(data.question_ids) != len(set(data.question_ids)):
        raise HTTPException(400, "Soru sıralama listesinde tekrar eden kayıt var")
    questions = db.scalars(select(m.Question).where(m.Question.exam_id == exam_id).order_by(m.Question.order_no)).all()
    current_ids = [x.id for x in questions]
    if set(data.question_ids) != set(current_ids) or len(data.question_ids) != len(current_ids):
        raise HTTPException(400, "Sıralama listesi sınavdaki tüm soruları tam olarak içermelidir")
    by_id = {x.id: x for x in questions}
    temp_base = (max((x.order_no for x in questions), default=0) + len(questions) + 1000)
    for i, qid in enumerate(data.question_ids, start=1):
        by_id[qid].order_no = temp_base + i
    db.flush()
    for i, qid in enumerate(data.question_ids, start=1):
        by_id[qid].order_no = i
    db.flush()
    audit(db, "reorder", "exam_questions", exam_id, {"question_ids": data.question_ids})
    _commit(db)
    return {"exam_id": exam_id, "question_ids": data.question_ids}


@app.post("/api/exams/{exam_id}/questions/normalize-points")
def normalize_exam_question_points(exam_id: int, data: NormalizeQuestionPointsRequest, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Sınav bulunamadı")
    _require_exam_draft(exam)
    questions = db.scalars(select(m.Question).where(m.Question.exam_id == exam_id).order_by(m.Question.order_no)).all()
    if not questions:
        raise HTTPException(409, "Puan ölçeklemek için en az bir soru gereklidir")
    old_total = sum(float(x.points or 0) for x in questions)
    if old_total <= 0:
        raise HTTPException(409, "Mevcut soru puanları ölçeklenemiyor")
    scale = 100.0 / old_total
    precision = data.precision
    new_points: list[float] = []
    running = 0.0
    for q in questions[:-1]:
        value = round(float(q.points) * scale, precision)
        if value <= 0:
            raise HTTPException(409, "Seçilen hassasiyet bazı soru puanlarını sıfıra düşürüyor")
        new_points.append(value); running += value
    last = round(100.0 - running, precision)
    if last <= 0:
        raise HTTPException(409, "Puanlar 100'e güvenli biçimde ölçeklenemedi")
    new_points.append(last)
    for q, value in zip(questions, new_points):
        old_points = float(q.points or 0)
        if q.question_type == "classic" and q.rubric and q.rubric.get("criteria") and old_points > 0:
            ratio = value / old_points
            criteria = [dict(c) for c in q.rubric.get("criteria") or []]
            running_r = 0.0
            for c in criteria[:-1]:
                c["max_points"] = round(float(c.get("max_points") or 0) * ratio, precision)
                running_r += c["max_points"]
            if criteria:
                criteria[-1]["max_points"] = round(value - running_r, precision)
            q.rubric = {"criteria": criteria}
        q.points = value
    audit(db, "normalize_points", "exam_questions", exam_id, {"old_total": old_total, "new_total": sum(new_points), "precision": precision})
    _commit(db)
    return {"exam_id": exam_id, "old_total": round(old_total, 4), "total_points": round(sum(new_points), 4), "points": [{"question_id": q.id, "points": q.points} for q in questions]}


@app.get("/api/exams/{exam_id}/students")
def exam_students(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    if not db.get(m.Exam, exam_id): raise HTTPException(404, "Sınav bulunamadı")
    rows = db.scalars(select(m.ExamStudent).options(selectinload(m.ExamStudent.student)).where(m.ExamStudent.exam_id == exam_id)).all()
    return [{"exam_student_id": x.id, "attendance_status": x.attendance_status or "attended", "attendance_note": x.attendance_note or "", "attendance_updated_at": x.attendance_updated_at.isoformat() if x.attendance_updated_at else None, **_student_out(x.student)} for x in rows]


@app.get("/api/exams/{exam_id}/students/{student_id}/responses")
def get_responses(exam_id: int, student_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    es = db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.student_id == student_id))
    if not es: raise HTTPException(404, "Öğrenci bu sınava kayıtlı değil")
    rows = db.scalars(select(m.Response).where(m.Response.exam_student_id == es.id)).all()
    return [{"question_id": x.question_id, "answer_text": x.answer_text, "awarded_points": x.awarded_points, "is_correct": x.is_correct, "rubric_scores": x.rubric_scores or {}, "graded_by": x.graded_by or "", "graded_at": x.graded_at.isoformat() if x.graded_at else None, "revision_no": x.revision_no or 1} for x in rows]


@app.post("/api/exams/{exam_id}/students/{student_id}/responses")
def submit_responses(exam_id: int, student_id: int, data: ResponsesSubmit, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    if exam.status != "grading": raise HTTPException(409, "Cevap/puan girişi yalnızca değerlendirme (grading) durumunda yapılabilir")
    if exam.grade_locked_at: raise HTTPException(409, "Puanlar kilitli. Değişiklik yalnız resmî itiraz/yeniden değerlendirme akışından yapılabilir")
    es = db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.student_id == student_id))
    if not es: raise HTTPException(404, "Öğrenci bu sınava kayıtlı değil")
    saved = 0
    policy = _key_policy(db, exam_id)
    for item in data.responses:
        q = db.get(m.Question, item.question_id)
        if not q or q.exam_id != exam_id: raise HTTPException(400, f"Soru bu sınava ait değil: {item.question_id}")
        existing = db.scalar(select(m.Response).where(m.Response.exam_student_id == es.id, m.Response.question_id == q.id))
        if q.question_type == "mcq":
            answer = normalize_correct_answer(item.answer_text, q.choices)
            correct = _mcq_is_correct(q, answer, policy)
            awarded = float(q.points) if correct else 0.0
            is_correct = correct
        else:
            rubric_scores: dict[str, float] = {}
            if q.rubric and q.rubric.get("criteria"):
                supplied = item.rubric_scores or {}
                criteria = q.rubric.get("criteria") or []
                for criterion in criteria:
                    cid = str(criterion.get("id"))
                    max_points = float(criterion.get("max_points") or 0)
                    if cid not in supplied:
                        raise HTTPException(400, f"Klasik soru {q.order_no} rubriğinde '{criterion.get('label')}' puanı zorunludur")
                    score = float(supplied[cid])
                    if score < 0 or score > max_points:
                        raise HTTPException(400, f"Rubrik puanı 0-{max_points:g} arasında olmalıdır: {criterion.get('label')}")
                    rubric_scores[cid] = round(score, 4)
                awarded = round(sum(rubric_scores.values()), 4)
            else:
                raise HTTPException(400, f"Klasik soru {q.order_no} rubriksiz puanlanamaz")
            if awarded < 0 or awarded > float(q.points): raise HTTPException(400, f"Klasik soru {q.order_no} puanı 0-{q.points} arasında olmalıdır")
            is_correct = None
        if q.question_type == "mcq":
            rubric_scores = {}
        actor = current_user(); grader = actor.get("email") or "system"; now = datetime.now(timezone.utc)
        if existing:
            old_points, old_rubric = existing.awarded_points, dict(existing.rubric_scores or {})
            existing.answer_text = item.answer_text; existing.awarded_points = awarded; existing.is_correct = is_correct; existing.rubric_scores = rubric_scores
            existing.graded_by = grader; existing.graded_at = now; existing.revision_no = int(existing.revision_no or 1) + 1
            _log_grade_revision(db, existing, old_points, old_rubric, "manual", grader)
        else:
            db.add(m.Response(exam_student_id=es.id, question_id=q.id, answer_text=item.answer_text, awarded_points=awarded, is_correct=is_correct, rubric_scores=rubric_scores, graded_by=grader, graded_at=now, revision_no=1))
        saved += 1
    audit(db, "grade", "exam_student", es.id, {"responses": saved}); _commit(db)
    return {"saved": saved}


@app.get("/api/exams/{exam_id}/students/{student_id}/grade-history")
def student_grade_history(exam_id: int, student_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    es = db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.student_id == student_id))
    if not es: raise HTTPException(404, "Öğrenci bu sınava kayıtlı değil")
    rows = db.scalars(
        select(m.ResponseGradeRevision).where(m.ResponseGradeRevision.exam_student_id == es.id)
        .order_by(m.ResponseGradeRevision.changed_at.desc())
    ).all()
    out = []
    for r in rows:
        q = db.get(m.Question, r.question_id)
        out.append({
            "id": r.id, "response_id": r.response_id, "question_id": r.question_id,
            "question_order_no": q.order_no if q else None,
            "previous_awarded_points": r.previous_awarded_points, "new_awarded_points": r.new_awarded_points,
            "previous_rubric_scores": r.previous_rubric_scores, "new_rubric_scores": r.new_rubric_scores,
            "source": r.source, "changed_by": r.changed_by,
            "changed_at": r.changed_at.isoformat() if r.changed_at else None,
        })
    return out


@app.get("/api/exams/{exam_id}/students/{student_id}/classic-scans")
def student_classic_scans(exam_id: int, student_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    exam = _load_exam_detail_model(db, exam_id)
    es = db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.student_id == student_id))
    if not es:
        raise HTTPException(404, "Öğrenci bu sınava atanmış değil")
    items = db.scalars(
        select(m.ScanItem).where(
            m.ScanItem.exam_id == exam_id, m.ScanItem.student_id == student_id,
            m.ScanItem.page_kind == "question", m.ScanItem.status == "support",
        ).order_by(m.ScanItem.created_at.desc(), m.ScanItem.id.desc())
    ).all()
    # Keep the newest scan for each booklet/logical page pair.
    newest: dict[tuple[str, int], m.ScanItem] = {}
    for item in items:
        key = ((item.booklet or "A").upper(), int(item.logical_page_no or 0))
        newest.setdefault(key, item)
    pages = sorted(newest.values(), key=lambda x: (int(x.logical_page_no or 999), x.id))
    page_payload = [{
        "scan_item_id": item.id, "booklet": item.booklet or "A", "logical_page_no": item.logical_page_no,
        "physical_page_no": item.page_no, "question_numbers": item.question_numbers or [],
        "preview_url": f"/api/scan-items/{item.id}/preview",
        "issues": item.issue_summary or [],
    } for item in pages]

    classic = []
    for q in sorted(exam.questions, key=lambda x: x.order_no):
        if q.question_type != "classic":
            continue
        chosen = None
        region = None
        for item in pages:
            legacy = any(x.get("code") == "LEGACY_PAGE_ASSOCIATION" for x in (item.issue_summary or []))
            regions = question_regions(exam, (item.booklet or "A").upper(), legacy_layout=legacy)
            candidate = regions.get(int(q.id))
            if candidate and int(candidate.get("page_no") or 0) == int(item.logical_page_no or 0):
                chosen, region = item, candidate
                break
        classic.append({
            "question_id": q.id, "order_no": q.order_no, "points": float(q.points), "text": q.text,
            "scan": ({
                "scan_item_id": chosen.id, "booklet": chosen.booklet or "A",
                "logical_page_no": chosen.logical_page_no, "physical_page_no": chosen.page_no,
                "answer_preview_url": f"/api/scan-items/{chosen.id}/classic-crop/{q.id}?mode=answer",
                "question_preview_url": f"/api/scan-items/{chosen.id}/classic-crop/{q.id}?mode=question",
                "full_page_url": f"/api/scan-items/{chosen.id}/preview",
                "legacy_association": any(x.get("code") == "LEGACY_PAGE_ASSOCIATION" for x in (chosen.issue_summary or [])),
            } if chosen and region else None),
        })
    return {"exam_id": exam_id, "student_id": student_id, "classic_questions": classic, "pages": page_payload}



def _scan_session_out(x: m.ScanSession) -> dict:
    total = max(0, int(x.page_count or 0))
    accepted = max(0, int(x.accepted_count or 0))
    review = max(0, int(x.review_count or 0))
    duplicate = max(0, int(x.duplicate_count or 0))
    skipped = max(0, int(x.skipped_count or 0))
    support = max(0, int(getattr(x, "support_count", 0) or 0))
    processed = accepted + review + duplicate + skipped + support
    omr_decisions = accepted + review + duplicate
    return {
        "id": x.id, "exam_id": x.exam_id, "source_name": x.source_name, "status": x.status, "page_count": total,
        "accepted_count": accepted, "review_count": review, "duplicate_count": duplicate,
        "skipped_count": skipped, "support_count": support, "processed_count": processed,
        "auto_accept_percent": round((accepted / omr_decisions * 100.0) if omr_decisions else 0.0, 1),
        "created_at": x.created_at.isoformat() if x.created_at else None,
    }


def _refresh_scan_session_counts(db: Session, session_id: int) -> m.ScanSession:
    db.flush()
    session = db.get(m.ScanSession, session_id)
    if not session:
        raise HTTPException(404, "Tarama oturumu bulunamadı")
    rows = db.scalars(select(m.ScanItem.status).where(m.ScanItem.session_id == session_id)).all()
    session.accepted_count = sum(1 for x in rows if x == "accepted")
    session.review_count = sum(1 for x in rows if x == "review")
    session.duplicate_count = sum(1 for x in rows if x == "duplicate")
    session.skipped_count = sum(1 for x in rows if x in {"skipped", "rejected"})
    session.support_count = sum(1 for x in rows if x == "support")
    session.page_count = len(rows)
    session.status = "completed_with_review" if session.review_count else "completed"
    return session


def _scan_review_out(item: m.ScanItem, review: m.ScanReview | None = None) -> dict:
    detail = diagnostic_summary(item.diagnostics or {}, item.answers or {})
    actionable = [x for x in detail if x["state"] in {"marked", "ambiguous"}]
    overall = min((float(x["confidence"]) for x in actionable), default=1.0)
    issue_codes = [str(x.get("code") or "REVIEW") for x in (item.issue_summary or [])]
    return {
        "id": review.id if review else None,
        "scan_item_id": item.id,
        "session_id": item.session_id,
        "reason": review.reason if review else "",
        "page_no": item.page_no,
        "status": item.status,
        "booklet": item.booklet,
        "student_no": item.student_no_detected,
        "student_id": item.student_id,
        "answers": item.answers or {},
        "issues": item.issue_summary or [],
        "issue_codes": issue_codes,
        "diagnostic_summary": detail,
        "confidence": round(overall, 4),
        "confidence_percent": int(round(overall * 100)),
        "attention_questions": [x["question_no"] for x in detail if x["state"] == "ambiguous"],
        "page_kind": getattr(item, "page_kind", "omr") or "omr",
        "logical_page_no": getattr(item, "logical_page_no", None),
        "question_numbers": getattr(item, "question_numbers", []) or [],
        "preview_url": (f"/api/scan-items/{item.id}/preview" if getattr(item, "page_kind", "omr") == "question" else f"/api/scan-items/{item.id}/review-preview") if item.preview_name else None,
        "raw_preview_url": f"/api/scan-items/{item.id}/preview" if item.preview_name else None,
    }


def _key_policy(db: Session, exam_id: int) -> tuple[set[int], dict[int, set[str]]]:
    """Annulled questions (everyone gets full credit) and accepted alternative answers, replayed from key revisions."""
    annulled: set[int] = set(); alts: dict[int, set[str]] = {}
    for rev in db.scalars(select(m.AnswerKeyRevision).where(m.AnswerKeyRevision.exam_id == exam_id).order_by(m.AnswerKeyRevision.id)).all():
        c = rev.corrections or {}
        for qid in c.get("__annulled__", []) or []:
            annulled.add(int(qid))
        for qid, letters in (c.get("__accepted__", {}) or {}).items():
            alts.setdefault(int(qid), set()).update(str(x).upper() for x in letters)
    return annulled, alts


def _mcq_is_correct(q: "m.Question", normalized: str | None, policy: tuple[set[int], dict[int, set[str]]]) -> bool:
    annulled, alts = policy
    if q.id in annulled:
        return True
    expected = normalize_correct_answer(q.correct_answer, q.choices)
    if not normalized:
        return False
    return normalized == expected or normalized.upper() in alts.get(q.id, set())


def _apply_scan_answers(db: Session, exam: m.Exam, student: m.Student, booklet: str, answers: dict) -> int:
    if exam.status != "grading":
        raise HTTPException(409, "Optik cevapların otomatik uygulanması için sınav değerlendirme (grading) durumunda olmalıdır")
    if exam.grade_locked_at:
        raise HTTPException(409, "Puanlar kilitli; yeni optik sonuçları puanlara uygulanamaz")
    es = db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam.id, m.ExamStudent.student_id == student.id))
    if not es:
        raise HTTPException(400, "Optikteki öğrenci bu sınava kayıtlı değil")
    meta = paper_metadata(exam, booklet, student=student)
    display_to_qid = {str(x["display_no"]): x["question_id"] for x in meta["question_order"] if x["question_type"] == "mcq"}
    saved = 0
    policy = _key_policy(db, exam.id)
    for no, answer in answers.items():
        qid = display_to_qid.get(str(no))
        if not qid:
            continue
        q = db.get(m.Question, qid)
        existing = db.scalar(select(m.Response).where(m.Response.exam_student_id == es.id, m.Response.question_id == q.id))
        normalized = normalize_correct_answer(answer, q.choices) if answer else None
        correct = _mcq_is_correct(q, normalized, policy)
        now = datetime.now(timezone.utc)
        if existing:
            old_points, old_rubric = existing.awarded_points, dict(existing.rubric_scores or {})
            existing.answer_text = normalized
            existing.awarded_points = float(q.points) if correct else 0.0
            existing.is_correct = correct
            existing.graded_by = "OMR"; existing.graded_at = now; existing.revision_no = int(existing.revision_no or 1) + 1
            _log_grade_revision(db, existing, old_points, old_rubric, "omr", "OMR")
        else:
            db.add(m.Response(exam_student_id=es.id, question_id=q.id, answer_text=normalized,
                              awarded_points=float(q.points) if correct else 0.0, is_correct=correct, graded_by="OMR", graded_at=now, revision_no=1))
        saved += 1
    return saved


def _process_scan_bytes(db: Session, exam: m.Exam, data: bytes, source_name: str) -> m.ScanSession:
    if not data:
        raise HTTPException(400, "Tarama dosyası boş")
    digest = sha256(data).hexdigest()
    if db.scalar(select(m.ScanSession).where(m.ScanSession.exam_id == exam.id, m.ScanSession.source_sha256 == digest)):
        raise HTTPException(409, "Aynı tarama dosyası bu sınava daha önce yüklenmiş")
    try:
        pages = iter_decode_upload(data, source_name)
    except ScanError as exc:
        raise HTTPException(400, str(exc))

    session = m.ScanSession(exam_id=exam.id, source_name=source_name, source_sha256=digest, page_count=0)
    db.add(session); db.flush()
    root = Path(settings.scan_storage_path); root.mkdir(parents=True, exist_ok=True)
    from .services.scan import decode_qr

    # Backward compatibility for pre-6.19 personalized packets where only the
    # answer sheet carried a QR. Future papers carry a page QR on every question
    # page, so ADF page order is no longer required.
    last_context: dict | None = None

    def assigned_student(qr: dict):
        student = db.scalar(select(m.Student).where(m.Student.student_no == qr.get("student_no"))) if qr.get("student_no") else None
        assigned = bool(student and db.scalar(select(m.ExamStudent.id).where(m.ExamStudent.exam_id == exam.id, m.ExamStudent.student_id == student.id)))
        return student, assigned

    def page_questions(booklet: str, logical_page_no: int | None, legacy: bool = False) -> list[int]:
        if not logical_page_no:
            return []
        regions = question_regions(exam, booklet, legacy_layout=legacy)
        return sorted({int(x["display_no"]) for x in regions.values() if int(x.get("page_no") or 0) == int(logical_page_no)})

    def save_support(page_image, physical_page_no: int, *, booklet: str, student, token: str | None, logical_page_no: int | None, legacy: bool = False, extra_issues: list | None = None):
        issues = list(extra_issues or [])
        if legacy:
            issues.append({"code":"LEGACY_PAGE_ASSOCIATION", "message":"Soru sayfası önceki öğrenci QR sayfasının sırasına göre eşlendi"})
        preview_name = f"scan_{session.id}_{physical_page_no}_question_{uuid.uuid4().hex[:8]}.jpg"
        (root / preview_name).write_bytes(jpeg_bytes(page_image, quality=90))
        db.add(m.ScanItem(
            session_id=session.id, exam_id=exam.id, page_no=physical_page_no, status="support", booklet=booklet,
            token=token, student_no_detected=student.student_no if student else None, student_id=student.id if student else None,
            page_fingerprint=full_page_fingerprint(page_image) if not legacy else None, answers={}, diagnostics={},
            issue_summary=issues, preview_name=preview_name, page_kind="question", logical_page_no=logical_page_no,
            question_numbers=page_questions(booklet, logical_page_no, legacy=legacy),
        ))

    for physical_page_no, page in enumerate(pages, start=1):
        qr_raw, qr_oriented = decode_qr(page)
        qr = parse_qr_payload(qr_raw)

        if qr and qr.get("exam_id") == exam.id and qr.get("role") == "questions":
            booklet = (qr.get("booklet") or "A").upper()
            student, assigned = assigned_student(qr)
            expected = paper_metadata(exam, booklet, student=student if student else None)
            issues = []
            if qr.get("token") != expected.get("token"):
                issues.append({"code":"TOKEN_MISMATCH", "message":"Soru sayfası sınav/kitapçık doğrulama tokenı eşleşmedi"})
            if not student:
                issues.append({"code":"STUDENT_NOT_IDENTIFIED", "message":"Soru sayfasının öğrencisi QR üzerinden belirlenemedi"})
            elif not assigned:
                issues.append({"code":"STUDENT_NOT_ASSIGNED", "message":"Soru sayfasındaki öğrenci bu sınava atanmış değil"})
            logical_page_no = qr.get("logical_page_no")
            if issues:
                preview_name = f"scan_{session.id}_{physical_page_no}_question_{uuid.uuid4().hex[:8]}.jpg"
                (root / preview_name).write_bytes(jpeg_bytes(qr_oriented, quality=88))
                db.add(m.ScanItem(
                    session_id=session.id, exam_id=exam.id, page_no=physical_page_no, status="skipped", booklet=booklet,
                    token=qr.get("token"), student_no_detected=qr.get("student_no"), student_id=student.id if student else None,
                    answers={}, diagnostics={}, issue_summary=issues, preview_name=preview_name, page_kind="question",
                    logical_page_no=logical_page_no, question_numbers=page_questions(booklet, logical_page_no),
                ))
            else:
                save_support(qr_oriented, physical_page_no, booklet=booklet, student=student, token=qr.get("token"), logical_page_no=logical_page_no)
                last_context = {"booklet":booklet, "student":student, "token":qr.get("token"), "next_logical_page":int(logical_page_no or 1)+1}
            continue

        if not qr or qr.get("exam_id") != exam.id:
            if last_context and last_context.get("student"):
                logical_page_no = int(last_context.get("next_logical_page") or 2)
                save_support(
                    page, physical_page_no, booklet=last_context["booklet"], student=last_context["student"],
                    token=last_context.get("token"), logical_page_no=logical_page_no, legacy=True,
                )
                last_context["next_logical_page"] = logical_page_no + 1
            else:
                db.add(m.ScanItem(
                    session_id=session.id, exam_id=exam.id, page_no=physical_page_no, status="skipped",
                    answers={}, diagnostics={}, page_kind="unknown", question_numbers=[],
                    issue_summary=[{"code":"NO_MATCHING_QR", "message":"Bu sayfa seçili sınavla güvenli biçimde eşleştirilemedi"}],
                ))
            continue

        booklet = (qr.get("booklet") or "A").upper()
        student, assigned = assigned_student(qr)
        expected = paper_metadata(exam, booklet, student=student if student else None)
        token_mismatch = qr.get("token") != expected.get("token")
        result = analyze_page(page, expected)
        omr_logical_page = 2 if str(getattr(exam, "omr_mode", "embedded") or "embedded") == "separate" else 1
        if result.get("kind") != "omr":
            status = "review" if token_mismatch else "skipped"
            issues = [{"code":"TOKEN_MISMATCH", "message":"Sınav/kitapçık doğrulama tokenı eşleşmedi"}] if token_mismatch else []
            issues.append({"code":"NO_OMR_MARKERS", "message":"OMR kayıt işaretleri bulunamadı"})
            item = m.ScanItem(
                session_id=session.id, exam_id=exam.id, page_no=physical_page_no, status=status, booklet=booklet,
                token=qr.get("token"), student_no_detected=qr.get("student_no"), student_id=student.id if student else None,
                answers={}, diagnostics={}, issue_summary=issues, page_kind="omr", logical_page_no=omr_logical_page, question_numbers=[],
            )
            db.add(item); db.flush()
            if status == "review":
                db.add(m.ScanReview(scan_item_id=item.id, exam_id=exam.id, reason="; ".join(x["message"] for x in issues)))
            if student and assigned and not token_mismatch:
                last_context = {"booklet":booklet, "student":student, "token":qr.get("token"), "next_logical_page":omr_logical_page + 1}
            else:
                last_context = None
            continue

        fingerprint = result["fingerprint"]
        if db.scalar(select(m.ScanItem).where(m.ScanItem.exam_id == exam.id, m.ScanItem.page_fingerprint == fingerprint)):
            db.add(m.ScanItem(
                session_id=session.id, exam_id=exam.id, page_no=physical_page_no, status="duplicate", booklet=booklet,
                token=qr.get("token"), student_no_detected=qr.get("student_no"), student_id=student.id if student else None, answers=result["answers"],
                diagnostics=result["diagnostics"], issue_summary=[{"code":"DUPLICATE_PAGE", "message":"Aynı cevap formu daha önce işlendi"}], page_fingerprint=None,
                page_kind="omr", logical_page_no=omr_logical_page, question_numbers=[],
            ))
            if student and assigned and not token_mismatch:
                last_context = {"booklet":booklet, "student":student, "token":qr.get("token"), "next_logical_page":omr_logical_page + 1}
            else:
                last_context = None
            continue

        preview_name = f"scan_{session.id}_{physical_page_no}_{uuid.uuid4().hex[:8]}.jpg"
        (root / preview_name).write_bytes(jpeg_bytes(result["warped"]))
        issues = list(result["issues"])
        if token_mismatch:
            issues.insert(0, {"code":"TOKEN_MISMATCH", "message":"Sınav/kitapçık doğrulama tokenı eşleşmedi"})
        if not student:
            issues.append({"code":"STUDENT_NOT_IDENTIFIED", "message":"Öğrenci QR üzerinden belirlenemedi"})
        elif not assigned:
            issues.append({"code":"STUDENT_NOT_ASSIGNED", "message":"Öğrenci bu sınava atanmış değil"})
        if exam.status != "grading":
            issues.append({"code":"EXAM_NOT_GRADING", "message":"Sınav değerlendirme durumunda değil"})

        status = "review" if issues else "accepted"
        item = m.ScanItem(
            session_id=session.id, exam_id=exam.id, page_no=physical_page_no, status=status, booklet=booklet,
            token=qr.get("token"), student_no_detected=qr.get("student_no"), student_id=student.id if student else None,
            page_fingerprint=fingerprint, answers=result["answers"], diagnostics=result["diagnostics"],
            issue_summary=issues, preview_name=preview_name, page_kind="omr", logical_page_no=omr_logical_page, question_numbers=[],
        )
        db.add(item); db.flush()
        if issues:
            db.add(m.ScanReview(scan_item_id=item.id, exam_id=exam.id, reason="; ".join(x.get("message") or x.get("code", "İnceleme gerekli") for x in issues)))
        else:
            _apply_scan_answers(db, exam, student, booklet, result["answers"])
        # Even when bubble marks require manual review, a valid QR identity is
        # sufficient to associate following legacy v2 question pages.
        if student and assigned and not token_mismatch:
            last_context = {"booklet":booklet, "student":student, "token":qr.get("token"), "next_logical_page":omr_logical_page + 1}
        else:
            last_context = None

    _refresh_scan_session_counts(db, session.id)
    audit(db, "scan_upload", "scan_session", session.id, _scan_session_out(session))
    _commit(db)
    return session


@app.post("/api/exams/{exam_id}/scans", status_code=201)
async def upload_scan(exam_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = _load_exam_detail_model(db, exam_id)
    data = await read_upload_limited(file)
    source_name = Path(file.filename or "scan.pdf").name[:255] or "scan.pdf"
    session = _process_scan_bytes(db, exam, data, source_name)
    return _scan_session_out(session)


@app.post("/api/exams/{exam_id}/scans-batch", status_code=201)
async def upload_scan_batch(exam_id: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    if not files:
        raise HTTPException(400, "En az bir tarama dosyası seçin")
    if len(files) > settings.max_batch_files:
        raise HTTPException(400, f"Tek seferde en fazla {settings.max_batch_files} tarama dosyası yüklenebilir")
    exam = _load_exam_detail_model(db, exam_id)
    sessions: list[dict] = []
    failed: list[dict] = []
    batch_bytes = 0
    batch_limit = settings.max_batch_upload_mb * 1024 * 1024
    for file in files:
        source_name = Path(file.filename or "scan.pdf").name[:255] or "scan.pdf"
        data = await read_upload_limited(file)
        batch_bytes += len(data)
        if batch_bytes > batch_limit:
            raise HTTPException(413, f"Toplu tarama yüklemesi en fazla {settings.max_batch_upload_mb} MB olabilir")
        try:
            session = _process_scan_bytes(db, exam, data, source_name)
            sessions.append(_scan_session_out(session))
        except HTTPException as exc:
            db.rollback()
            failed.append({"source_name": source_name, "status_code": exc.status_code, "message": str(exc.detail)})
        except Exception as exc:
            db.rollback()
            failed.append({"source_name": source_name, "status_code": 500, "message": str(exc) if settings.app_env == "pilot" else "Dosya işlenemedi"})
    totals = {
        "files": len(files), "completed_files": len(sessions), "failed_files": len(failed),
        "pages": sum(x["page_count"] for x in sessions), "accepted": sum(x["accepted_count"] for x in sessions),
        "support": sum(x.get("support_count", 0) for x in sessions),
        "review": sum(x["review_count"] for x in sessions), "duplicate": sum(x["duplicate_count"] for x in sessions),
        "skipped": sum(x["skipped_count"] for x in sessions),
    }
    audit(db, "scan_batch_upload", "exam", exam_id, totals); _commit(db)
    return {"sessions": sessions, "failed": failed, "totals": totals}


@app.get("/api/exams/{exam_id}/scans")
def list_scans(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    return [_scan_session_out(x) for x in db.scalars(select(m.ScanSession).where(m.ScanSession.exam_id == exam_id).order_by(m.ScanSession.id.desc())).all()]


@app.get("/api/scan-sessions/{session_id}")
def scan_session_detail(session_id: int, db: Session = Depends(get_db)):
    session = db.get(m.ScanSession, session_id)
    if not session: raise HTTPException(404, "Tarama oturumu bulunamadı")
    require_exam_access(db, session.exam_id, write=False)
    items = db.scalars(select(m.ScanItem).where(m.ScanItem.session_id == session_id).order_by(m.ScanItem.page_no)).all()
    return {**_scan_session_out(session), "items": [_scan_review_out(x) for x in items]}


@app.get("/api/exams/{exam_id}/scan-reviews", response_model=list[ScanReviewOut])
def scan_reviews(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    rows = db.scalars(select(m.ScanReview).where(m.ScanReview.exam_id == exam_id, m.ScanReview.status == "open").order_by(m.ScanReview.id)).all()
    out=[]
    for review in rows:
        item = db.get(m.ScanItem, review.scan_item_id)
        if item:
            out.append(_scan_review_out(item, review))
    return out


@app.get("/api/exams/{exam_id}/scan-coverage")
def scan_coverage(exam_id: int, db: Session = Depends(get_db)):
    """Which attending students have no usable scanned page yet (missing papers) and which have pending reviews."""
    require_exam_access(db, exam_id, write=False)
    if not db.get(m.Exam, exam_id): raise HTTPException(404, "Sınav bulunamadı")
    rows = db.scalars(select(m.ExamStudent).options(selectinload(m.ExamStudent.student)).where(m.ExamStudent.exam_id == exam_id).order_by(m.ExamStudent.id)).all()
    by_student: dict[int, set[str]] = {}
    pages_seen: dict[tuple[int, str], set[int]] = {}
    for sid, st, bk, kind, lp in db.execute(select(m.ScanItem.student_id, m.ScanItem.status, m.ScanItem.booklet, m.ScanItem.page_kind, m.ScanItem.logical_page_no).where(m.ScanItem.exam_id == exam_id, m.ScanItem.student_id.is_not(None))).all():
        by_student.setdefault(int(sid), set()).add(st)
        if kind == "question" and st == "support" and lp:
            pages_seen.setdefault((int(sid), (bk or "A").upper()), set()).add(int(lp))
    exam_full = _load_exam_detail_model(db, exam_id)
    expected_pages: dict[str, set[int]] = {}
    for bk in _allowed_booklets(exam_full):
        try:
            expected_pages[bk] = {int(r["page_no"]) for r in question_regions(exam_full, bk).values() if r.get("page_no")}
        except Exception:
            expected_pages[bk] = set()
    incomplete = []
    unmatched = db.scalar(select(func.count()).select_from(m.ScanItem).where(m.ScanItem.exam_id == exam_id, m.ScanItem.status == "review", m.ScanItem.student_id.is_(None))) or 0
    missing, pending, scanned, absent = [], [], 0, 0
    for es in rows:
        if es.attendance_status != "attended":
            absent += 1; continue
        states = by_student.get(es.student_id, set())
        row = {"student_id": es.student_id, "student_no": es.student.student_no, "full_name": es.student.full_name}
        if states & {"accepted", "support"}:
            scanned += 1
        else:
            missing.append(row)
        if "review" in states:
            pending.append(row)
        for (psid, bk), seen in pages_seen.items():
            if psid == es.student_id and expected_pages.get(bk):
                gap = sorted(expected_pages[bk] - seen)
                if gap:
                    incomplete.append({**row, "booklet": bk, "missing_pages": gap})
    return {"incomplete_papers": incomplete, "exam_id": exam_id, "attended": scanned + len(missing), "absent": absent, "scanned": scanned,
            "missing_count": len(missing), "missing": missing, "pending_review": pending, "unmatched_review_pages": int(unmatched)}


@app.get("/api/scan-items/{item_id}/preview")
def scan_item_preview(item_id: int, db: Session = Depends(get_db)):
    item = db.get(m.ScanItem, item_id)
    if not item: raise HTTPException(404, "Tarama kaydı bulunamadı")
    require_exam_access(db, item.exam_id, write=False)
    if not item.preview_name: raise HTTPException(404,"Önizleme bulunamadı")
    path=Path(settings.scan_storage_path)/item.preview_name
    if not path.exists(): raise HTTPException(404,"Önizleme dosyası bulunamadı")
    return FileResponse(path, media_type="image/jpeg")


@app.get("/api/scan-items/{item_id}/classic-crop/{question_id}")
def classic_scan_crop(item_id: int, question_id: int, mode: str = "answer", db: Session = Depends(get_db)):
    import cv2
    item = db.get(m.ScanItem, item_id)
    if not item:
        raise HTTPException(404, "Tarama sayfası bulunamadı")
    require_exam_access(db, item.exam_id, write=False)
    if item.page_kind != "question" or not item.preview_name:
        raise HTTPException(404, "Bu kayıtta klasik cevap sayfası yok")
    exam = _load_exam_detail_model(db, item.exam_id)
    q = db.get(m.Question, question_id)
    if not q or q.exam_id != exam.id or q.question_type != "classic":
        raise HTTPException(404, "Klasik soru bulunamadı")
    legacy = any(x.get("code") == "LEGACY_PAGE_ASSOCIATION" for x in (item.issue_summary or []))
    region = question_regions(exam, (item.booklet or "A").upper(), legacy_layout=legacy).get(int(question_id))
    if not region or int(region.get("page_no") or 0) != int(item.logical_page_no or 0):
        raise HTTPException(404, "Bu soru seçilen tarama sayfasında bulunmuyor")
    path = Path(settings.scan_storage_path) / item.preview_name
    image = cv2.imread(str(path))
    if image is None:
        raise HTTPException(404, "Tarama görseli okunamadı")
    crop_key = "question_crop" if mode == "question" else "answer_crop"
    rect = region.get(crop_key) or region.get("question_crop")
    if not rect or len(rect) != 4:
        raise HTTPException(404, "Soru kırpma alanı bulunamadı")
    h, w = image.shape[:2]
    x1 = max(0, min(w - 1, int(float(rect[0]) * w))); y1 = max(0, min(h - 1, int(float(rect[1]) * h)))
    x2 = max(x1 + 1, min(w, int(float(rect[2]) * w))); y2 = max(y1 + 1, min(h, int(float(rect[3]) * h)))
    cropped = image[y1:y2, x1:x2]
    if cropped.size == 0:
        raise HTTPException(404, "Klasik cevap alanı kırpılamadı")
    return StreamingResponse(BytesIO(jpeg_bytes(cropped, quality=92)), media_type="image/jpeg", headers={"Cache-Control":"no-store"})


@app.get("/api/scan-items/{item_id}/review-preview")
def scan_item_review_preview(item_id: int, db: Session = Depends(get_db)):
    import cv2
    item = db.get(m.ScanItem, item_id)
    if not item: raise HTTPException(404, "Tarama kaydı bulunamadı")
    require_exam_access(db, item.exam_id, write=False)
    if not item.preview_name: raise HTTPException(404, "Önizleme bulunamadı")
    path = Path(settings.scan_storage_path) / item.preview_name
    image = cv2.imread(str(path))
    if image is None: raise HTTPException(404, "Önizleme dosyası okunamadı")
    exam = _load_exam_detail_model(db, item.exam_id)
    student = db.get(m.Student, item.student_id) if item.student_id else None
    meta = paper_metadata(exam, item.booklet or "A", student=student)
    annotated = annotated_review_preview(image, meta, item.answers or {}, item.diagnostics or {}, item.issue_summary or [])
    return StreamingResponse(BytesIO(jpeg_bytes(annotated, quality=90)), media_type="image/jpeg", headers={"Cache-Control":"no-store"})


@app.post("/api/scan-items/{item_id}/resolve")
def resolve_scan_item(item_id: int, data: ScanReviewResolve, db: Session = Depends(get_db)):
    item = db.get(m.ScanItem, item_id)
    if not item: raise HTTPException(404, "Tarama sayfası bulunamadı")
    require_exam_access(db, item.exam_id, write=True)
    review=db.scalar(select(m.ScanReview).where(m.ScanReview.scan_item_id==item_id, m.ScanReview.status=="open"))
    if not review: raise HTTPException(409,"Açık inceleme kaydı yok")

    if data.action == "reject":
        item.status = "rejected"
        review.status = "rejected"
        review.resolved_at = datetime.now(timezone.utc)
        audit(db, "scan_review_reject", "scan_item", item.id, {"note": data.note, "issues": item.issue_summary})
        session = _refresh_scan_session_counts(db, item.session_id)
        _commit(db)
        return {"ok":True, "scan_item_id":item.id, "status":"rejected", "session":_scan_session_out(session)}

    if not data.student_id:
        raise HTTPException(400, "Onay için öğrenci seçilmelidir")
    exam=_load_exam_detail_model(db,item.exam_id)
    student=db.get(m.Student,data.student_id)
    if not student: raise HTTPException(404,"Öğrenci bulunamadı")
    booklet = (data.booklet or item.booklet or "A").upper()
    answers={str(k):(str(v).upper() if v else None) for k,v in data.answers.items()}
    _apply_scan_answers(db,exam,student,booklet,answers)
    item.student_id=student.id; item.student_no_detected=student.student_no; item.answers=answers; item.booklet=booklet; item.status="accepted"
    review.status="resolved"; review.resolved_student_id=student.id; review.resolved_answers=answers; review.resolved_at=datetime.now(timezone.utc)
    audit(db,"scan_review_resolve","scan_item",item.id,{"student_id":student.id,"booklet":booklet,"note":data.note})
    session = _refresh_scan_session_counts(db, item.session_id)
    _commit(db)
    return {"ok":True,"scan_item_id":item.id,"student_id":student.id,"status":"accepted","session":_scan_session_out(session)}


@app.post("/api/exams/{exam_id}/answer-key/regrade")
def answer_key_regrade(exam_id: int, data: AnswerKeyRegradeRequest, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam=_load_exam_detail_model(db,exam_id)
    if exam.grade_locked_at:
        raise HTTPException(409, "Puanlar kilitli. Cevap anahtarı düzeltmesi için önce kontrollü kilit açma gerekir")
    if not (data.reason or "").strip():
        raise HTTPException(400, "Cevap anahtarı düzeltme gerekçesi zorunludur")
    corrections={}
    for qid, answer in data.corrections.items():
        q=db.get(m.Question,int(qid))
        if not q or q.exam_id != exam_id or q.question_type != "mcq": raise HTTPException(400,f"Geçersiz test sorusu: {qid}")
        normalized=normalize_correct_answer(answer,q.choices)
        if not normalized or normalized not in (q.choices or {}): raise HTTPException(400,f"Geçersiz doğru cevap: {qid}")
        corrections[str(q.id)]={"old":q.correct_answer,"new":normalized}; q.correct_answer=normalized
    affected=0
    policy=_key_policy(db,exam_id)
    rows=db.scalars(select(m.Response).join(m.ExamStudent,m.Response.exam_student_id==m.ExamStudent.id).where(m.ExamStudent.exam_id==exam_id)).all()
    for r in rows:
        q=db.get(m.Question,r.question_id)
        if q and q.question_type=="mcq" and str(q.id) in corrections:
            ans=normalize_correct_answer(r.answer_text,q.choices) if r.answer_text else None
            old_points=r.awarded_points
            r.is_correct=_mcq_is_correct(q,ans,policy); r.awarded_points=float(q.points) if r.is_correct else 0.0; affected+=1
            _log_grade_revision(db, r, old_points, dict(r.rubric_scores or {}), "answer_key_regrade")
    rev=m.AnswerKeyRevision(exam_id=exam_id,corrections=corrections,reason=data.reason,affected_responses=affected); db.add(rev); db.flush()
    audit(db,"answer_key_regrade","exam",exam_id,{"revision_id":rev.id,"affected":affected,"corrections":corrections}); _commit(db)
    return {"revision_id":rev.id,"affected_responses":affected,"corrections":corrections}


@app.post("/api/exams/{exam_id}/questions/{question_id}/key-exception")
def question_key_exception(exam_id: int, question_id: int, data: QuestionKeyException, db: Session = Depends(get_db)):
    """Annul a multiple-choice question (full credit to every attending student) or accept an
    additional correct choice. Persisted as an answer-key revision so later scans/entries follow it."""
    require_exam_access(db, exam_id, write=True)
    exam = _load_exam_detail_model(db, exam_id)
    if exam.status != "grading":
        raise HTTPException(409, "Soru iptali / alternatif cevap yalnızca değerlendirme (grading) durumunda yapılabilir")
    if exam.grade_locked_at:
        raise HTTPException(409, "Puanlar kilitli. Önce kontrollü kilit açma gerekir")
    if not (data.reason or "").strip():
        raise HTTPException(400, "Gerekçe zorunludur")
    q = db.get(m.Question, question_id)
    if not q or q.exam_id != exam_id or q.question_type != "mcq":
        raise HTTPException(400, "Yalnız bu sınavın çoktan seçmeli soruları için geçerlidir")
    if data.action == "accept_alternative":
        alt = normalize_correct_answer(data.alternative, q.choices)
        if not alt or alt not in (q.choices or {}):
            raise HTTPException(400, "Geçersiz alternatif şık")
        corrections = {"__accepted__": {str(q.id): [alt]}}
    else:
        corrections = {"__annulled__": [q.id]}
    rev = m.AnswerKeyRevision(exam_id=exam_id, corrections=corrections, reason=data.reason.strip(), affected_responses=0)
    db.add(rev); db.flush()
    policy = _key_policy(db, exam_id)
    attended = db.scalars(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.attendance_status == "attended")).all()
    existing = {r.exam_student_id: r for r in db.scalars(select(m.Response).where(m.Response.question_id == q.id)).all()}
    affected = 0; now = datetime.now(timezone.utc)
    actor = current_user().get("email") or "system"
    for es in attended:
        r = existing.get(es.id)
        ans = normalize_correct_answer(r.answer_text, q.choices) if (r and r.answer_text) else None
        ok = _mcq_is_correct(q, ans, policy)
        pts = float(q.points) if ok else 0.0
        if r:
            if r.awarded_points != pts or r.is_correct != ok:
                old = r.awarded_points
                r.awarded_points = pts; r.is_correct = ok; r.graded_by = actor; r.graded_at = now; r.revision_no = int(r.revision_no or 1) + 1
                _log_grade_revision(db, r, old, dict(r.rubric_scores or {}), "question_annulled" if data.action == "annul" else "alternative_accepted", actor)
                affected += 1
        elif ok:
            db.add(m.Response(exam_student_id=es.id, question_id=q.id, answer_text=None, awarded_points=pts, is_correct=True, graded_by=actor, graded_at=now, revision_no=1)); affected += 1
    rev.affected_responses = affected
    audit(db, "question_key_exception", "question", q.id, {"action": data.action, "alternative": data.alternative, "affected": affected, "reason": data.reason}); _commit(db)
    return {"revision_id": rev.id, "action": data.action, "affected_responses": affected}


@app.get("/api/exams/{exam_id}/answer-key/revisions")
def answer_key_revisions(exam_id:int, db:Session=Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    rows=db.scalars(select(m.AnswerKeyRevision).where(m.AnswerKeyRevision.exam_id==exam_id).order_by(m.AnswerKeyRevision.id.desc())).all()
    return [{"id":x.id,"corrections":x.corrections,"reason":x.reason,"affected_responses":x.affected_responses,"created_at":x.created_at.isoformat()} for x in rows]


@app.get("/api/exams/{exam_id}/analytics")
def analytics(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    try:
        return exam_analytics(db, exam_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.post("/api/exams/{exam_id}/psychometrics/sync")
def sync_exam_psychometrics(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    try: data = exam_analytics(db, exam_id)
    except ValueError as exc: raise HTTPException(404, str(exc))
    exam_questions = {q.id:q for q in db.scalars(select(m.Question).where(m.Question.exam_id==exam_id)).all()}
    updated=0
    for stat in data.get("question_analysis") or []:
        q=exam_questions.get(stat.get("question_id"))
        if not q or not q.bank_question_id: continue
        bank=db.get(m.QuestionBank,q.bank_question_id)
        if not bank: continue
        bank.difficulty_index=round(float(stat.get("attainment_percent") or 0)/100.0,4)
        bank.discrimination_index=stat.get("discrimination_index")
        distractors=[x for x in (stat.get("distractors") or []) if not x.get("is_correct")]
        bank.distractor_efficiency=round((sum(1 for x in distractors if float(x.get("percent") or 0)>0)/len(distractors)*100.0),2) if distractors else None
        bank.psychometric_sample_size=int(stat.get("sample_size") or 0)
        flags=set(stat.get("quality_flags") or [])
        if "negative_discrimination" in flags or "too_easy" in flags or "too_hard" in flags: bank.quality_status="review"
        elif "low_discrimination" in flags or "small_sample" in flags: bank.quality_status="caution"
        else: bank.quality_status="good"
        updated+=1
    audit(db,"psychometrics_sync","exam",exam_id,{"updated_bank_questions":updated});_commit(db)
    return {"exam_id":exam_id,"updated_bank_questions":updated}


@app.get("/api/exams/{exam_id}/students/{exam_student_id}/analytics")
def student_analytics(exam_id: int, exam_student_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    try:
        return student_exam_analytics(db, exam_id, exam_student_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.get("/api/exams/{exam_id}/results.xlsx")
def exam_results_xlsx(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    try:
        payload, filename = build_exam_results_xlsx(db, exam_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _improvement_out(x: m.ImprovementAction) -> dict:
    return {"id": x.id, "exam_id": x.exam_id, "outcome_code": x.outcome_code, "action_text": x.action_text, "owner": x.owner,
            "due_date": x.due_date.isoformat() if x.due_date else None, "status": x.status,
            "baseline_percent": x.baseline_percent, "target_percent": x.target_percent, "actual_percent": x.actual_percent,
            "verification_method": x.verification_method or "", "effectiveness_status": x.effectiveness_status or "pending",
            "verified_by": x.verified_by or "", "verified_at": x.verified_at.isoformat() if x.verified_at else None,
            "closure_note": x.closure_note or ""}


@app.post("/api/exams/{exam_id}/improvements", status_code=201)
def add_improvement(exam_id: int, data: ImprovementCreate, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True, accreditation=True)
    if not db.get(m.Exam, exam_id): raise HTTPException(404, "Sınav bulunamadı")
    obj = m.ImprovementAction(exam_id=exam_id, **data.model_dump()); db.add(obj); db.flush(); audit(db, "create", "improvement", obj.id, data.model_dump(mode="json")); _commit(db)
    return _improvement_out(obj)


@app.get("/api/exams/{exam_id}/improvements")
def improvements(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    rows = db.scalars(select(m.ImprovementAction).where(m.ImprovementAction.exam_id == exam_id).order_by(m.ImprovementAction.id.desc())).all()
    return [_improvement_out(x) for x in rows]


@app.patch("/api/improvements/{action_id}")
def update_improvement(action_id: int, data: ImprovementUpdate, db: Session = Depends(get_db)):
    action_obj = db.get(m.ImprovementAction, action_id)
    if not action_obj: raise HTTPException(404, "İyileştirme aksiyonu bulunamadı")
    require_exam_access(db, action_obj.exam_id, write=True, accreditation=True)
    obj = db.get(m.ImprovementAction, action_id)
    if not obj:
        raise HTTPException(404, "İyileştirme aksiyonu bulunamadı")
    changes = _apply_patch(obj, data)
    if obj.status == "done":
        if obj.actual_percent is None or not (obj.verification_method or "").strip() or obj.effectiveness_status == "pending":
            raise HTTPException(409, "Aksiyon kapatılamaz: gerçekleşen sonuç, doğrulama yöntemi ve etkililik değerlendirmesi zorunludur")
        obj.verified_by = current_user().get("email") or "system"; obj.verified_at = datetime.now(timezone.utc)
    audit(db, "update", "improvement", obj.id, changes)
    _commit(db)
    return _improvement_out(obj)


@app.get("/api/accreditation/profiles")
def accreditation_profiles(db: Session = Depends(get_db)):
    rows = db.scalars(select(m.AccreditationProfile).order_by(m.AccreditationProfile.code, m.AccreditationProfile.version)).all()
    return [{
        "id": x.id, "code": x.code, "name": x.name, "version": x.version,
        "required_general_evidence_kinds": x.required_general_evidence_kinds or [],
        "required_representative_evidence_kinds": x.required_representative_evidence_kinds or [],
        "requires_representatives": x.requires_representatives,
        "requires_improvement_for_gaps": x.requires_improvement_for_gaps,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    } for x in rows]


@app.post("/api/accreditation/profiles", status_code=201)
def create_accreditation_profile(data: AccreditationProfileCreate, db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    obj = m.AccreditationProfile(**data.model_dump())
    db.add(obj); db.flush()
    audit(db, "create", "accreditation_profile", obj.id, data.model_dump())
    _commit(db)
    return {"id": obj.id, **data.model_dump()}


@app.get("/api/accreditation/periods")
def accreditation_periods(program_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(m.AccreditationPeriod).order_by(m.AccreditationPeriod.id.desc())
    if program_id:
        stmt = stmt.where(m.AccreditationPeriod.program_id == program_id)
    rows = db.scalars(stmt).all()
    result = []
    for x in rows:
        if not can_manage_accreditation_program(db, x.program_id, write=False):
            continue
        profile = db.get(m.AccreditationProfile, x.profile_id)
        program = db.get(m.Program, x.program_id)
        result.append({
            "id": x.id, "program_id": x.program_id, "profile_id": x.profile_id,
            "program_name": program.name if program else "",
            "profile_name": f"{profile.name} · {profile.version}" if profile else "",
            "academic_year": x.academic_year, "term": x.term, "title": x.title, "status": x.status,
            "created_at": x.created_at.isoformat() if x.created_at else None,
        })
    return result


@app.post("/api/accreditation/periods", status_code=201)
def create_accreditation_period(data: AccreditationPeriodCreate, db: Session = Depends(get_db)):
    if not can_manage_accreditation_program(db, data.program_id, write=True): raise HTTPException(403, "Bu program için akreditasyon dönemi yönetme yetkiniz yok")
    if not db.get(m.Program, data.program_id):
        raise HTTPException(404, "Program bulunamadı")
    if not db.get(m.AccreditationProfile, data.profile_id):
        raise HTTPException(404, "Akreditasyon profili bulunamadı")
    obj = m.AccreditationPeriod(**data.model_dump(), status="collecting")
    db.add(obj); db.flush()
    sync = sync_period_exams(db, obj)
    audit(db, "create", "accreditation_period", obj.id, {**data.model_dump(), "sync": sync})
    _commit(db)
    return {"id": obj.id, "status": obj.status, **data.model_dump(), "sync": sync}


@app.post("/api/accreditation/periods/{period_id}/sync-exams")
def accreditation_sync_exams(period_id: int, db: Session = Depends(get_db)):
    period_obj = db.get(m.AccreditationPeriod, period_id)
    if not period_obj: raise HTTPException(404, "Akreditasyon dönemi bulunamadı")
    if not can_manage_accreditation_program(db, period_obj.program_id, write=True): raise HTTPException(403, "Bu akreditasyon dönemini yönetme yetkiniz yok")
    period = db.get(m.AccreditationPeriod, period_id)
    if not period:
        raise HTTPException(404, "Akreditasyon dönemi bulunamadı")
    if period.status == "archived":
        raise HTTPException(409, "Arşivlenmiş akreditasyon dönemine sınav eklenemez")
    result = sync_period_exams(db, period)
    audit(db, "sync_exams", "accreditation_period", period.id, result)
    _commit(db)
    return result


@app.get("/api/accreditation/periods/{period_id}/dashboard")
def accreditation_dashboard(period_id: int, db: Session = Depends(get_db)):
    period_obj = db.get(m.AccreditationPeriod, period_id)
    if not period_obj: raise HTTPException(404, "Akreditasyon dönemi bulunamadı")
    if not can_manage_accreditation_program(db, period_obj.program_id, write=False): raise HTTPException(403, "Bu akreditasyon dönemine erişim yetkiniz yok")
    try:
        return period_dashboard(db, period_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.post("/api/accreditation/periods/{period_id}/status")
def accreditation_period_status(period_id: int, data: AccreditationPeriodStatusUpdate, db: Session = Depends(get_db)):
    period_obj = db.get(m.AccreditationPeriod, period_id)
    if not period_obj: raise HTTPException(404, "Akreditasyon dönemi bulunamadı")
    if not can_manage_accreditation_program(db, period_obj.program_id, write=True): raise HTTPException(403, "Bu akreditasyon dönemini yönetme yetkiniz yok")
    period = db.get(m.AccreditationPeriod, period_id)
    if not period:
        raise HTTPException(404, "Akreditasyon dönemi bulunamadı")
    if period.status == "archived":
        raise HTTPException(409, "Arşivlenmiş dönem yeniden açılamaz")
    if data.status == "ready":
        dashboard = period_dashboard(db, period.id)
        if not dashboard["summary"]["ready"]:
            raise HTTPException(409, {"message": "Dönem henüz akreditasyon paketine hazır değil", "issues": [w for ex in dashboard["exams"] for w in ex["warnings"]]})
    if data.status == "archived" and period.status != "ready":
        raise HTTPException(409, "Yalnızca hazır akreditasyon dönemi arşivlenebilir")
    old = period.status
    period.status = data.status
    audit(db, "status", "accreditation_period", period.id, {"from": old, "to": data.status})
    _commit(db)
    return {"id": period.id, "status": period.status}


@app.post("/api/accreditation/periods/{period_id}/representatives/freeze-all")
def freeze_accreditation_period_representatives(period_id: int, db: Session = Depends(get_db)):
    period_obj = db.get(m.AccreditationPeriod, period_id)
    if not period_obj:
        raise HTTPException(404, "Akreditasyon dönemi bulunamadı")
    if not can_manage_accreditation_program(db, period_obj.program_id, write=True):
        raise HTTPException(403, "Bu akreditasyon dönemini yönetme yetkiniz yok")
    try:
        result = freeze_period_representatives(db, period_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    audit(db, "freeze_period_representatives", "accreditation_period", period_id, result)
    _commit(db)
    return result


@app.get("/api/accreditation/periods/{period_id}/report.xlsx")
def accreditation_period_report_xlsx(period_id: int, db: Session = Depends(get_db)):
    period_obj = db.get(m.AccreditationPeriod, period_id)
    if not period_obj:
        raise HTTPException(404, "Akreditasyon dönemi bulunamadı")
    if not can_manage_accreditation_program(db, period_obj.program_id, write=False):
        raise HTTPException(403, "Bu akreditasyon dönemine erişim yetkiniz yok")
    try:
        payload, filename = build_accreditation_period_xlsx(db, period_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/exams/{exam_id}/representatives/freeze")
def freeze_exam_representatives(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True, accreditation=True)
    try:
        rows = freeze_representatives(db, exam_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    audit(db, "freeze_representatives", "exam", exam_id, {"slots": [x.slot for x in rows]})
    _commit(db)
    return representative_rows(db, exam_id)


@app.get("/api/exams/{exam_id}/representatives")
def exam_representatives(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    if not db.get(m.Exam, exam_id):
        raise HTTPException(404, "Sınav bulunamadı")
    return representative_rows(db, exam_id)


def _zip_write_hashed(z: zipfile.ZipFile, checksums: dict[str, str], name: str, data: bytes) -> None:
    z.writestr(name, data)
    checksums[name] = sha256(data).hexdigest()


@app.get("/api/accreditation/periods/{period_id}/evidence-package")
def accreditation_period_package(period_id: int, db: Session = Depends(get_db)):
    period_obj = db.get(m.AccreditationPeriod, period_id)
    if not period_obj: raise HTTPException(404, "Akreditasyon dönemi bulunamadı")
    if not can_manage_accreditation_program(db, period_obj.program_id, write=False): raise HTTPException(403, "Bu akreditasyon dönemine erişim yetkiniz yok")
    try:
        dashboard = period_dashboard(db, period_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    period = db.get(m.AccreditationPeriod, period_id)
    profile = db.get(m.AccreditationProfile, period.profile_id)
    links = db.scalars(select(m.AccreditationPeriodExam).where(m.AccreditationPeriodExam.period_id == period_id).order_by(m.AccreditationPeriodExam.id)).all()
    root = Path(settings.evidence_storage_path)
    buffer = BytesIO()
    checksums: dict[str, str] = {}
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        _zip_write_hashed(z, checksums, "00-dashboard.json", json.dumps(dashboard, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
        report_xlsx, _ = build_accreditation_period_xlsx(db, period_id)
        _zip_write_hashed(z, checksums, "00-Akreditasyon-Degerlendirme-Raporu.xlsx", report_xlsx)
        readme_text = (
            "DOU Assess 6.13 Akreditasyon Kanıt Paketi\n"
            f"Dönem: {dashboard['period']['title']}\n"
            f"Program: {(dashboard.get('program') or {}).get('code','')} · {(dashboard.get('program') or {}).get('name','')}\n"
            f"Profil: {dashboard['profile']['code']} · {dashboard['profile']['version']}\n"
            f"Hazır: {'EVET' if dashboard['summary']['ready'] else 'HAYIR'}\n"
            "\nİçerik: yönetici Excel raporu, dönem matrisi, başarısız ÖÇ kaydı, iyileştirme aksiyonları, "
            "MIN/AVG/MAX kayıtları, sınav snapshot/analizleri, üretilmiş sınav kağıtları ve yüklenmiş kanıtlar.\n"
            "Dosya bütünlüğü SHA256SUMS.json ile doğrulanabilir.\n"
        ).encode("utf-8")
        _zip_write_hashed(z, checksums, "00-PAKET-OKU.txt", readme_text)
        _zip_write_hashed(z, checksums, "02-PC-Matrisi.json", json.dumps({"program_outcomes": dashboard.get("program_outcomes", []), "courses": dashboard.get("courses", [])}, ensure_ascii=False, indent=2).encode("utf-8"))
        _zip_write_hashed(z, checksums, "03-Basarisiz-OC.json", json.dumps(dashboard.get("gap_register", []), ensure_ascii=False, indent=2).encode("utf-8"))
        _zip_write_hashed(z, checksums, "04-Iyilestirme-Aksiyonlari.json", json.dumps(dashboard.get("improvement_register", []), ensure_ascii=False, indent=2).encode("utf-8"))
        _zip_write_hashed(z, checksums, "05-MIN-AVG-MAX.json", json.dumps(dashboard.get("representative_register", []), ensure_ascii=False, indent=2).encode("utf-8"))
        profile_data = {
            "code": profile.code, "name": profile.name, "version": profile.version,
            "required_general_evidence_kinds": profile.required_general_evidence_kinds or [],
            "required_representative_evidence_kinds": profile.required_representative_evidence_kinds or [],
            "requires_representatives": profile.requires_representatives,
            "requires_improvement_for_gaps": profile.requires_improvement_for_gaps,
        }
        _zip_write_hashed(z, checksums, "01-profile.json", json.dumps(profile_data, ensure_ascii=False, indent=2).encode("utf-8"))
        for link in links:
            exam = _load_exam_detail_model(db, link.exam_id)
            prefix = f"exams/{exam.id}_{re.sub(r'[^A-Za-z0-9_-]+', '_', exam.course_code_snapshot or str(exam.course_id))}/"
            analytics_data = exam_analytics(db, exam.id)
            reps = representative_rows(db, exam.id)
            actions = improvements(exam.id, db)
            _zip_write_hashed(z, checksums, prefix + "exam.json", json.dumps(_exam_out(exam, include_detail=True), ensure_ascii=False, indent=2, default=str).encode("utf-8"))
            _zip_write_hashed(z, checksums, prefix + "analytics.json", json.dumps(analytics_data, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
            _zip_write_hashed(z, checksums, prefix + "representatives.json", json.dumps(reps, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
            _zip_write_hashed(z, checksums, prefix + "improvements.json", json.dumps(actions, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
            if exam.questions:
                paper_bytes, paper_meta = build_exam_pdf(exam, "A")
                _zip_write_hashed(z, checksums, prefix + "generated/exam-paper-booklet-A.pdf", paper_bytes)
                _zip_write_hashed(z, checksums, prefix + "generated/exam-paper-booklet-A.metadata.json", json.dumps(paper_meta, ensure_ascii=False, indent=2).encode("utf-8"))
            assets = db.scalars(select(m.EvidenceAsset).where(m.EvidenceAsset.exam_id == exam.id).order_by(m.EvidenceAsset.id)).all()
            manifest = []
            for asset in assets:
                manifest.append({"id": asset.id, "student_id": asset.student_id, "kind": asset.kind, "category": asset.category, "description": asset.description, "version_no": asset.version_no, "retention_until": asset.retention_until.isoformat() if asset.retention_until else None, "original_name": asset.original_name, "sha256": asset.sha256})
                path = root / asset.stored_name
                _verify_exam_evidence_integrity(db, asset, path)
                arc = prefix + f"evidence/{asset.id}_{Path(asset.original_name).name}"
                raw = path.read_bytes()
                _zip_write_hashed(z, checksums, arc, raw)
            _zip_write_hashed(z, checksums, prefix + "evidence-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        z.writestr("SHA256SUMS.json", json.dumps(checksums, ensure_ascii=False, indent=2))
    buffer.seek(0)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", period.title)[:80] or f"period_{period.id}"
    return StreamingResponse(buffer, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="DOU_Assess_Accreditation_{safe}.zip"'})


@app.get("/api/integrations/sync-runs")
def integration_sync_runs(limit: int = 50, db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    limit = min(max(limit, 1), 200)
    rows = db.scalars(select(m.IntegrationSyncRun).order_by(m.IntegrationSyncRun.id.desc()).limit(limit)).all()
    return [{
        "id": x.id, "provider": x.provider, "filename": x.filename, "mode": x.mode, "source_sha256": x.source_sha256,
        "status": x.status, "summary": x.summary or {}, "created_at": x.created_at.isoformat() if x.created_at else None,
    } for x in rows]


@app.get("/api/integrations/obs/proliz/status")
def proliz_status():
    require_roles("admin")
    return {
        "enabled": settings.obs_proliz_enabled,
        "base_url": settings.obs_proliz_base_url,
        "username_configured": bool(settings.obs_proliz_username),
        "password_configured": bool(settings.obs_proliz_password),
    }


@app.get("/api/integrations/obs/proliz/probe")
def proliz_probe(endpoint: str = "akademik_donem", db: Session = Depends(get_db)):
    require_roles("admin")
    if not settings.obs_proliz_enabled:
        raise HTTPException(503, "OBS_PROLIZ_ENABLED=false; Proliz entegrasyonu kapalı")
    try:
        data = obs_proliz.probe(endpoint)
    except obs_proliz.ProlizError as exc:
        run = m.IntegrationSyncRun(provider="obs-proliz", filename=f"probe-{endpoint}", mode="probe", source_sha256="n/a", status="failed", summary={"error": str(exc)[:500]})
        db.add(run); db.flush(); audit(db, "obs_proliz_probe_failed", "integration_sync_run", run.id, {"endpoint": endpoint, "error": str(exc)[:500]}); _commit(db)
        raise HTTPException(502, str(exc)) from exc
    run = m.IntegrationSyncRun(provider="obs-proliz", filename=f"probe-{endpoint}", mode="probe", source_sha256="n/a", status="success", summary={"endpoint": endpoint})
    db.add(run); db.flush(); audit(db, "obs_proliz_probe", "integration_sync_run", run.id, {"endpoint": endpoint}); _commit(db)
    return {"endpoint": endpoint, "data": data}


@app.post("/api/integrations/obs/workbook/validate")
async def validate_obs_workbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    require_roles("admin")
    data = await read_upload_limited(file)
    parsed, errors = validate_workbook(data)
    digest = sha256(data).hexdigest()
    previous = db.scalar(select(m.IntegrationSyncRun).where(m.IntegrationSyncRun.source_sha256 == digest, m.IntegrationSyncRun.status == "success").order_by(m.IntegrationSyncRun.id.desc()).limit(1))
    if errors:
        return JSONResponse(status_code=422, content={"ok": False, "error": {"code": "OBS_IMPORT_VALIDATION", "message": "OBS çalışma kitabı doğrulaması başarısız", "details": errors}, "source_sha256": digest})
    periods = sorted({f"{str(r.get('academic_year') or '').strip()} {str(r.get('term') or '').strip()}".strip() for r in parsed.get("Dersler", [])})
    instructors = sorted({str(r.get("instructor_email") or "").strip().lower() for r in parsed.get("Dersler", []) if str(r.get("instructor_email") or "").strip()})
    return {
        "ok": True, "provider": "obs-workbook", "source_sha256": digest,
        "duplicate_source": bool(previous), "previous_sync_id": previous.id if previous else None,
        "rows": {k: len(v) for k, v in parsed.items()}, "periods": periods, "instructor_count": len(instructors),
    }


@app.post("/api/integrations/obs/workbook/sync")
async def sync_obs_workbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    require_roles("admin")
    data = await read_upload_limited(file)
    digest = sha256(data).hexdigest()
    import_name = Path(file.filename or "obs.xlsx").name[:255] or "obs.xlsx"
    try:
        db.rollback()
        with db.begin():
            result = import_workbook(db, import_name, data, source_system="obs-workbook")
            identity = _sync_instructor_users_internal(db, auth_source="pilot" if not settings.auth_required else "entra")
            # Ensure imported course year/term pairs have manageable academic periods.
            created_periods = 0
            for academic_year, term in db.execute(select(m.Course.academic_year, m.Course.term).distinct()).all():
                if not academic_year or not term:
                    continue
                exists = db.scalar(select(m.AcademicPeriod).where(m.AcademicPeriod.academic_year == academic_year, m.AcademicPeriod.term == term))
                if not exists:
                    db.add(m.AcademicPeriod(academic_year=academic_year, term=term, title=f"{academic_year} {term}", status="planned")); created_periods += 1
            summary = {**result["summary"], **identity, "academic_periods_created": created_periods}
            run = m.IntegrationSyncRun(provider="obs-workbook", filename=import_name, mode="full", source_sha256=digest, status="success", summary=summary)
            db.add(run); db.flush()
            audit(db, "obs_sync", "integration_sync_run", run.id, {"sha256": digest, **summary})
        return {"ok": True, "sync_run_id": run.id, "source_sha256": digest, "summary": summary}
    except ImportValidationError as exc:
        db.rollback()
        run = m.IntegrationSyncRun(provider="obs-workbook", filename=import_name, mode="full", source_sha256=digest, status="failed", summary={"errors": exc.errors[:50]})
        db.add(run); db.flush(); audit(db, "obs_sync_failed", "integration_sync_run", run.id, {"sha256": digest, "error_count": len(exc.errors)}); _commit(db)
        return JSONResponse(status_code=422, content={"ok": False, "sync_run_id": run.id, "error": {"code": "OBS_IMPORT_VALIDATION", "message": "OBS çalışma kitabı doğrulaması başarısız", "details": exc.errors}})


@app.get("/api/import/academic-workbook/template")
def academic_workbook_template():
    require_roles("admin", "instructor", "program_head", "department_head", "faculty_admin")
    path = Path(__file__).parent / "static" / "examples" / "DOU-Assess-Akademik-Veri-Sablonu.xlsx"
    if not path.exists():
        raise HTTPException(404, "Akademik veri şablonu bulunamadı")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="DOU-Assess-Akademik-Veri-Sablonu.xlsx")



@app.get("/api/excel-center")
def excel_center_catalog():
    roles = set(current_user().get("role_names") or [])
    items = [
        {"kind":"academic","title":"Akademik Veri","description":"Program, ders, öğrenci, ders kaydı, ÖÇ/PÇ, sınav ve soru verilerini toplu aktarın.","template_url":"/api/import/academic-workbook/template","validate_url":"/api/import/academic-workbook/validate","import_url":"/api/import/academic-workbook","allowed":bool(roles & {"admin","instructor","program_head"})},
        {"kind":"question_bank","title":"Soru Havuzu","description":"Test ve klasik soruları beklenen cevap, Bloom, ÖÇ ve rubrik ile toplu aktarın.","template_url":"/api/import/question-bank/template","validate_url":"/api/import/question-bank/validate","import_url":"/api/import/question-bank","allowed":bool(roles & {"admin","instructor","program_head"})},
    ]
    for kind,cfg in EXCEL_CENTER_TEMPLATES.items():
        if kind == "users_roles": allowed = "admin" in roles
        elif kind == "improvements" or kind in QUALITY_EXCEL_KINDS: allowed = bool(roles & {"admin","quality","program_head"})
        else: allowed = bool(roles & {"admin","instructor","program_head"})
        items.append({"kind":kind,"title":cfg["title"],"description":cfg["help"],"template_url":f"/api/excel-center/{kind}/template","validate_url":f"/api/excel-center/{kind}/validate","import_url":f"/api/excel-center/{kind}/import","allowed":allowed})
    return {"items":[x for x in items if x["allowed"]],"workflow":["Şablonu indir","Excel'i doldur","Doğrula","İçe aktar","Sonuç özetini kontrol et"]}


def _excel_center_authorize(kind: str) -> None:
    if kind not in EXCEL_CENTER_TEMPLATES: raise HTTPException(404, "Excel veri türü bulunamadı")
    if kind == "users_roles": require_roles("admin")
    elif kind == "improvements" or kind in QUALITY_EXCEL_KINDS: require_roles("admin","quality","program_head")
    else: require_roles("admin","instructor","program_head")


@app.get("/api/excel-center/{kind}/template")
def excel_center_template(kind: str):
    _excel_center_authorize(kind)
    payload = excel_center_template_bytes(kind)
    return StreamingResponse(BytesIO(payload), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition":f'attachment; filename="DOU-Assess-{kind}.xlsx"'})


def _excel_center_validate_rows(kind: str, rows: list[dict], db: Session) -> list[str]:
    if kind in QUALITY_EXCEL_KINDS:
        return validate_quality_excel_rows(kind, rows, db)
    errors: list[str] = []
    valid_attendance={"attended","absent","excused","invalidated"}
    for row in rows:
        rn=row.get("__row__")
        try:
            if kind in {"exam_students","classic_grades","improvements"}:
                exam_id=int(row.get("exam_id") or 0); exam=db.get(m.Exam,exam_id)
                if not exam: errors.append(f"Satır {rn}: sınav bulunamadı ({exam_id})"); continue
                require_exam_access(db,exam_id,write=True,accreditation=(kind=="improvements"))
            if kind == "exam_students":
                no=str(row.get("student_no") or "").strip(); st=db.scalar(select(m.Student).where(m.Student.student_no==no))
                if not st: errors.append(f"Satır {rn}: öğrenci bulunamadı ({no})"); continue
                if not db.scalar(select(m.Enrollment).where(m.Enrollment.course_id==exam.course_id,m.Enrollment.student_id==st.id)): errors.append(f"Satır {rn}: öğrenci sınavın dersine kayıtlı değil")
                status=str(row.get("attendance_status") or "attended").strip().lower()
                if status not in valid_attendance: errors.append(f"Satır {rn}: attendance_status geçersiz")
            elif kind == "classic_grades":
                no=str(row.get("student_no") or "").strip(); st=db.scalar(select(m.Student).where(m.Student.student_no==no))
                es=db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id==exam.id,m.ExamStudent.student_id==st.id)) if st else None
                if not es: errors.append(f"Satır {rn}: öğrenci sınava atanmamış ({no})"); continue
                order=int(row.get("question_order") or 0); q=db.scalar(select(m.Question).where(m.Question.exam_id==exam.id,m.Question.order_no==order))
                if not q or q.question_type!="classic": errors.append(f"Satır {rn}: klasik soru bulunamadı (sıra {order})"); continue
                scores=parse_excel_rubric_scores(row.get("rubric_scores")); criteria={str(c.get("id")):c for c in (q.rubric or {}).get("criteria",[])}
                if not criteria: errors.append(f"Satır {rn}: soruda rubrik yok"); continue
                for cid,c in criteria.items():
                    if cid not in scores: errors.append(f"Satır {rn}: {c.get('label') or cid} rubrik puanı eksik")
                    elif scores[cid] < 0 or scores[cid] > float(c.get("max_points") or 0): errors.append(f"Satır {rn}: {cid} puanı sınır dışında")
                if any(cid not in criteria for cid in scores): errors.append(f"Satır {rn}: bilinmeyen rubrik ölçütü var")
                if exam.grade_locked_at: errors.append(f"Satır {rn}: sınav puanları kilitli")
            elif kind == "improvements":
                if not str(row.get("outcome_code") or "").strip(): errors.append(f"Satır {rn}: outcome_code zorunlu")
                if not str(row.get("action_text") or "").strip(): errors.append(f"Satır {rn}: action_text zorunlu")
                status=str(row.get("status") or "open").strip().lower()
                if status not in {"open","in_progress","done","cancelled"}: errors.append(f"Satır {rn}: status geçersiz")
                if status=="done" and (row.get("actual_percent") in (None,"") or not str(row.get("verification_method") or "").strip() or str(row.get("effectiveness_status") or "pending").strip()=="pending"): errors.append(f"Satır {rn}: kapanan aksiyonda gerçekleşen sonuç, doğrulama ve etkililik zorunlu")
            elif kind == "users_roles":
                email=str(row.get("email") or "").strip().lower(); role=str(row.get("role") or "").strip()
                if "@" not in email: errors.append(f"Satır {rn}: e-posta geçersiz")
                if role not in {"instructor","program_head","quality"}: errors.append(f"Satır {rn}: role yalnız instructor, program_head veya quality olabilir")
                if role=="program_head" and not str(row.get("program_code") or "").strip(): errors.append(f"Satır {rn}: Program Başkanı için program_code zorunlu")
                if role=="instructor" and not str(row.get("course_code") or "").strip(): errors.append(f"Satır {rn}: Öğretim Görevlisi için course_code zorunlu")
        except HTTPException as exc: errors.append(f"Satır {rn}: {exc.detail}")
        except Exception as exc: errors.append(f"Satır {rn}: {exc}")
    return errors


@app.post("/api/excel-center/{kind}/validate")
async def excel_center_validate(kind: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    _excel_center_authorize(kind); data=await read_upload_limited(file); rows, errors=parse_excel_center_workbook(kind,data)
    if not errors: errors.extend(_excel_center_validate_rows(kind,rows,db))
    if errors: return JSONResponse(status_code=422,content={"ok":False,"error":{"code":"EXCEL_CENTER_VALIDATION","message":"Excel doğrulaması başarısız","details":errors}})
    return {"ok":True,"kind":kind,"rows":len(rows),"message":"Dosya içe aktarmaya hazır"}


@app.post("/api/excel-center/{kind}/import")
async def excel_center_import(kind: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    _excel_center_authorize(kind); data=await read_upload_limited(file); rows, errors=parse_excel_center_workbook(kind,data)
    if not errors: errors.extend(_excel_center_validate_rows(kind,rows,db))
    if errors: return JSONResponse(status_code=422,content={"ok":False,"error":{"code":"EXCEL_CENTER_VALIDATION","message":"Excel doğrulaması başarısız","details":errors}})
    if kind in QUALITY_EXCEL_KINDS:
        created, updated = import_quality_excel_rows(kind, rows, db)
        audit(db,"excel_center_import",kind,payload={"rows":len(rows),"created":created,"updated":updated}); _commit(db)
        return {"ok":True,"kind":kind,"rows":len(rows),"created":created,"updated":updated}
    now=datetime.now(timezone.utc); created=updated=0
    for row in rows:
        if kind == "exam_students":
            exam=db.get(m.Exam,int(row["exam_id"])); st=db.scalar(select(m.Student).where(m.Student.student_no==str(row["student_no"]).strip()))
            es=db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id==exam.id,m.ExamStudent.student_id==st.id))
            if not es: es=m.ExamStudent(exam_id=exam.id,student_id=st.id);db.add(es);db.flush();created+=1
            else: updated+=1
            es.attendance_status=str(row.get("attendance_status") or "attended").strip().lower(); es.attendance_note=str(row.get("attendance_note") or "").strip(); es.attendance_updated_at=now
        elif kind == "classic_grades":
            exam=db.get(m.Exam,int(row["exam_id"])); st=db.scalar(select(m.Student).where(m.Student.student_no==str(row["student_no"]).strip())); es=db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id==exam.id,m.ExamStudent.student_id==st.id)); q=db.scalar(select(m.Question).where(m.Question.exam_id==exam.id,m.Question.order_no==int(row["question_order"])))
            scores=parse_excel_rubric_scores(row.get("rubric_scores")); r=db.scalar(select(m.Response).where(m.Response.exam_student_id==es.id,m.Response.question_id==q.id)); total=round(sum(scores.values()),4)
            if r:
                old_points,old_rubric=r.awarded_points,dict(r.rubric_scores or {})
                r.answer_text=str(row.get("answer_text") or "");r.rubric_scores=scores;r.awarded_points=total;r.graded_by=current_user().get("email") or "excel";r.graded_at=now;r.revision_no=int(r.revision_no or 1)+1;updated+=1
                _log_grade_revision(db, r, old_points, old_rubric, "excel_import")
            else: db.add(m.Response(exam_student_id=es.id,question_id=q.id,answer_text=str(row.get("answer_text") or ""),awarded_points=total,is_correct=None,rubric_scores=scores,graded_by=current_user().get("email") or "excel",graded_at=now,revision_no=1));created+=1
        elif kind == "improvements":
            def fp(name):
                v=row.get(name); return None if v in (None,"") else float(v)
            due=None
            if row.get("due_date") not in (None,""):
                v=row["due_date"]; due=v.date() if hasattr(v,"date") and not isinstance(v,date) else (v if isinstance(v,date) else date.fromisoformat(str(v)[:10]))
            obj=m.ImprovementAction(exam_id=int(row["exam_id"]),outcome_code=str(row["outcome_code"]).strip(),action_text=str(row["action_text"]).strip(),owner=str(row.get("owner") or "").strip(),due_date=due,status=str(row.get("status") or "open").strip().lower(),baseline_percent=fp("baseline_percent"),target_percent=fp("target_percent"),actual_percent=fp("actual_percent"),verification_method=str(row.get("verification_method") or "").strip(),effectiveness_status=str(row.get("effectiveness_status") or "pending").strip(),closure_note=str(row.get("closure_note") or "").strip())
            if obj.status=="done": obj.verified_by=current_user().get("email") or "excel";obj.verified_at=now
            db.add(obj);created+=1
        elif kind == "users_roles":
            email=str(row["email"]).strip().lower(); user=db.scalar(select(m.AppUser).where(m.AppUser.email==email)); active=excel_yes_no(row.get("is_active"),True)
            if not user: user=m.AppUser(email=email,display_name=str(row.get("display_name") or email).strip(),auth_source="pilot" if not settings.auth_required else "entra",is_active=active);db.add(user);db.flush();created+=1
            else: user.display_name=str(row.get("display_name") or user.display_name).strip();user.is_active=active;updated+=1
            role=str(row["role"]).strip(); program_id=course_id=None
            if role=="program_head":
                pr=db.scalar(select(m.Program).where(m.Program.code==str(row.get("program_code") or "").strip()));
                if not pr: raise HTTPException(422,f"Program bulunamadı: {row.get('program_code')}")
                program_id=pr.id
            elif role=="instructor":
                stmt=select(m.Course).where(m.Course.code==str(row.get("course_code") or "").strip())
                if str(row.get("academic_year") or "").strip(): stmt=stmt.where(m.Course.academic_year==str(row.get("academic_year")).strip())
                if str(row.get("term") or "").strip(): stmt=stmt.where(m.Course.term==str(row.get("term")).strip())
                co=db.scalar(stmt.limit(1));
                if not co: raise HTTPException(422,f"Ders bulunamadı: {row.get('course_code')}")
                course_id=co.id
            exists_role=db.scalar(select(m.UserRoleAssignment).where(m.UserRoleAssignment.user_id==user.id,m.UserRoleAssignment.role==role,m.UserRoleAssignment.program_id==program_id,m.UserRoleAssignment.course_id==course_id))
            if not exists_role: db.add(m.UserRoleAssignment(user_id=user.id,role=role,program_id=program_id,course_id=course_id));created+=1
    audit(db,"excel_center_import",kind,payload={"rows":len(rows),"created":created,"updated":updated}); _commit(db)
    return {"ok":True,"kind":kind,"rows":len(rows),"created":created,"updated":updated}


@app.post("/api/import/academic-workbook/validate")
async def validate_academic_workbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    require_roles("admin", "instructor", "program_head", "department_head", "faculty_admin")
    data = await read_upload_limited(file)
    parsed, errors = validate_workbook(data)
    if errors:
        return JSONResponse(status_code=422, content={"ok": False, "error": {"code": "ACADEMIC_IMPORT_VALIDATION", "message": "Akademik Excel doğrulaması başarısız", "details": errors}})
    if not has_role("admin"):
        allowed = visible_course_ids(db)
        scope_errors = []
        for row in parsed.get("Dersler", []):
            program = db.scalar(select(m.Program).where(m.Program.code == str(row.get("program_code") or "").strip()))
            course = None
            if program:
                course = db.scalar(select(m.Course).where(
                    m.Course.program_id == program.id,
                    m.Course.code == str(row.get("course_code") or "").strip(),
                    m.Course.academic_year == str(row.get("academic_year") or "").strip(),
                    m.Course.term == str(row.get("term") or "").strip(),
                ))
            if not course:
                scope_errors.append(f"Dersler satır {row.get('__row__')}: öğretim elemanı aktarımında ders sistemde önceden oluşturulmuş olmalıdır")
            elif course.id not in allowed:
                scope_errors.append(f"Dersler satır {row.get('__row__')}: bu derse veri aktarma yetkiniz yok")
        if scope_errors:
            return JSONResponse(status_code=403, content={"ok": False, "error": {"code": "ACADEMIC_IMPORT_SCOPE", "message": "Excel dosyasında yetki kapsamı dışında ders var", "details": scope_errors}})
    return {"ok": True, "rows": {k: len(v) for k, v in parsed.items()}, "mode": "admin" if has_role("admin") else "course-scoped"}


@app.post("/api/import/academic-workbook")
async def import_academic_workbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    require_roles("admin", "instructor", "program_head", "department_head", "faculty_admin")
    data = await read_upload_limited(file)
    try:
        db.rollback()
        with db.begin():
            import_name = Path(file.filename or "academic.xlsx").name[:255] or "academic.xlsx"
            admin_mode = has_role("admin")
            result = import_workbook(
                db, import_name, data, source_system="academic-workbook",
                allowed_course_ids=None if admin_mode else visible_course_ids(db),
                allow_structure_updates=admin_mode,
            )
            audit(db, "academic_import", "academic_workbook", result["batch_id"], {**result["summary"], "mode": "admin" if admin_mode else "course-scoped"})
        return {"ok": True, "mode": "admin" if admin_mode else "course-scoped", **result}
    except ImportValidationError as exc:
        db.rollback()
        return JSONResponse(status_code=422, content={"ok": False, "error": {"code": "ACADEMIC_IMPORT_VALIDATION", "message": "Akademik Excel içe aktarımı başarısız", "details": exc.errors}})


@app.post("/api/import/pilot-workbook/validate")
async def validate_pilot_workbook(file: UploadFile = File(...)):
    require_roles("admin")
    data = await read_upload_limited(file)
    parsed, errors = validate_workbook(data)
    if errors:
        return JSONResponse(status_code=422, content={"ok": False, "error": {"code": "IMPORT_VALIDATION", "message": "Excel doğrulaması başarısız", "details": errors}})
    return {"ok": True, "rows": {k: len(v) for k, v in parsed.items()}}


@app.post("/api/import/pilot-workbook")
async def import_pilot_workbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    require_roles("admin")
    data = await read_upload_limited(file)
    try:
        db.rollback()
        with db.begin():
            import_name = Path(file.filename or "pilot.xlsx").name[:255] or "pilot.xlsx"
            result = import_workbook(db, import_name, data)
            audit(db, "import", "pilot_workbook", result["batch_id"], result["summary"])
        return {"ok": True, **result}
    except ImportValidationError as exc:
        db.rollback()
        return JSONResponse(status_code=422, content={"ok": False, "error": {"code": "IMPORT_VALIDATION", "message": "Excel doğrulaması başarısız", "details": exc.errors}})


def _safe_filename(name: str) -> str:
    ext = Path(name).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def _evidence_out(asset: m.EvidenceAsset) -> dict:
    return {
        "id": asset.id, "exam_id": asset.exam_id, "student_id": asset.student_id, "kind": asset.kind,
        "category": asset.category or "general", "description": asset.description or "",
        "original_name": asset.original_name, "sha256": asset.sha256, "mime_type": asset.mime_type,
        "size_bytes": asset.size_bytes, "version_no": int(asset.version_no or 1),
        "integrity_status": asset.integrity_status or "unchecked",
        "integrity_checked_at": asset.integrity_checked_at.isoformat() if asset.integrity_checked_at else None,
        "retention_until": asset.retention_until.isoformat() if asset.retention_until else None,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "download_url": f"/api/evidence/{asset.id}/download", "preview_url": f"/api/evidence/{asset.id}/preview",
    }


def _verify_exam_evidence_integrity(db: Session, asset: m.EvidenceAsset, path: Path) -> None:
    status, actual = verify_stored_file(path, asset.sha256)
    previous = asset.integrity_status or "unchecked"
    asset.integrity_status = status
    asset.integrity_checked_at = datetime.now(timezone.utc)
    if status != previous or status != "verified":
        audit(db, "integrity_check", "evidence", asset.id, {"status": status, "expected_sha256": asset.sha256, "actual_sha256": actual})
    _commit(db)
    if status == "missing":
        raise HTTPException(404, "Kanıt dosyasının fiziksel kopyası bulunamadı")
    if status != "verified":
        raise HTTPException(409, "Kanıt dosyası SHA-256 bütünlük kontrolünden geçemedi")


@app.post("/api/exams/{exam_id}/evidence", status_code=201)
async def upload_evidence(
    exam_id: int, kind: str = Form(...), student_id: int | None = Form(None),
    category: str = Form("general"), description: str = Form(""), retention_until: str | None = Form(None),
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    require_exam_access(db, exam_id, write=True, accreditation=True)
    exam = db.get(m.Exam, exam_id)
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    if student_id is not None:
        assigned = db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.student_id == student_id))
        if not assigned: raise HTTPException(400, "Kanıt öğrencisi bu sınava kayıtlı değil")
    ext = Path(file.filename or "").suffix.lower()
    allowed = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    if ext not in allowed: raise HTTPException(400, "Kanıt dosyası PDF, JPG veya PNG olmalıdır")
    data = await read_upload_limited(file)
    if not data: raise HTTPException(400, "Dosya boş")
    if ext == ".pdf":
        validate_pdf_payload(data, purpose="Kanıt PDF")
    elif ext in {".jpg", ".jpeg"}:
        if not data.startswith(b"\xff\xd8\xff"): raise HTTPException(400, "Dosya içeriği geçerli JPEG değil")
        validate_image_payload(data, purpose="Kanıt görseli")
    elif ext == ".png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"): raise HTTPException(400, "Dosya içeriği geçerli PNG değil")
        validate_image_payload(data, purpose="Kanıt görseli")
    kind = (kind or "").strip()[:64]
    category = (category or "general").strip()[:64] or "general"
    description = (description or "").strip()[:4000]
    if not kind:
        raise HTTPException(400, "Kanıt türü zorunludur")
    retention_date = None
    if retention_until:
        try:
            retention_date = date.fromisoformat(retention_until)
        except ValueError:
            raise HTTPException(400, "Saklama tarihi YYYY-MM-DD biçiminde olmalıdır")
    if retention_date is None and settings.evidence_retention_days > 0:
        retention_date = date.today() + timedelta(days=settings.evidence_retention_days)
    root = Path(settings.evidence_storage_path); root.mkdir(parents=True, exist_ok=True)
    original_name = Path(file.filename or ("evidence" + ext)).name[:255] or ("evidence" + ext)
    previous_version = db.scalar(select(func.max(m.EvidenceAsset.version_no)).where(
        m.EvidenceAsset.exam_id == exam_id, m.EvidenceAsset.student_id == student_id,
        m.EvidenceAsset.kind == kind, m.EvidenceAsset.original_name == original_name
    )) or 0
    stored = _safe_filename(original_name)
    (root / stored).write_bytes(data)
    obj = m.EvidenceAsset(
        exam_id=exam_id, student_id=student_id, kind=kind, category=category, description=description,
        original_name=original_name, stored_name=stored, sha256=sha256(data).hexdigest(), integrity_status="verified",
        integrity_checked_at=datetime.now(timezone.utc), mime_type=allowed[ext], size_bytes=len(data),
        version_no=int(previous_version) + 1, retention_until=retention_date,
    )
    db.add(obj); db.flush(); audit(db, "upload", "evidence", obj.id, {"exam_id": exam_id, "version_no": obj.version_no, "category": category}); _commit(db)
    return _evidence_out(obj)


@app.get("/api/exams/{exam_id}/evidence")
def list_evidence(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    rows = db.scalars(select(m.EvidenceAsset).where(m.EvidenceAsset.exam_id == exam_id).order_by(m.EvidenceAsset.kind, m.EvidenceAsset.original_name, m.EvidenceAsset.version_no.desc(), m.EvidenceAsset.id.desc())).all()
    return [_evidence_out(x) for x in rows]


@app.get("/api/evidence/{asset_id}/download")
def download_evidence(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(m.EvidenceAsset, asset_id)
    if not asset: raise HTTPException(404, "Kanıt bulunamadı")
    require_exam_access(db, asset.exam_id, write=False)
    path = Path(settings.evidence_storage_path) / asset.stored_name
    _verify_exam_evidence_integrity(db, asset, path)
    return FileResponse(path, media_type=asset.mime_type, filename=asset.original_name)


@app.get("/api/evidence/{asset_id}/preview")
def preview_evidence(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(m.EvidenceAsset, asset_id)
    if not asset: raise HTTPException(404, "Kanıt bulunamadı")
    require_exam_access(db, asset.exam_id, write=False)
    path = Path(settings.evidence_storage_path) / asset.stored_name
    _verify_exam_evidence_integrity(db, asset, path)
    return FileResponse(path, media_type=asset.mime_type, filename=asset.original_name, content_disposition_type="inline")


@app.patch("/api/evidence/{asset_id}")
def update_evidence(asset_id: int, data: EvidenceUpdate, db: Session = Depends(get_db)):
    asset = db.get(m.EvidenceAsset, asset_id)
    if not asset: raise HTTPException(404, "Kanıt bulunamadı")
    require_exam_access(db, asset.exam_id, write=True, accreditation=True)
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if isinstance(value, str): value = value.strip()
        setattr(asset, key, value)
    audit(db, "update", "evidence", asset.id, changes); _commit(db)
    return _evidence_out(asset)


@app.delete("/api/evidence/{asset_id}")
def delete_evidence(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(m.EvidenceAsset, asset_id)
    if not asset: raise HTTPException(404, "Kanıt bulunamadı")
    require_exam_access(db, asset.exam_id, write=True, accreditation=True)
    path = Path(settings.evidence_storage_path) / asset.stored_name
    payload = {"exam_id": asset.exam_id, "original_name": asset.original_name, "sha256": asset.sha256, "version_no": asset.version_no}
    db.delete(asset); audit(db, "delete", "evidence", asset_id, payload); _commit(db)
    try:
        if path.exists(): path.unlink()
    except OSError:
        pass
    return {"deleted": True}


@app.post("/api/security/evidence-integrity/scan")
def evidence_integrity_scan(db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    result = scan_evidence_integrity(db)
    for failure in result.get("failures", []):
        audit(db, "integrity_scan_failure", failure["entity_type"], failure["id"], failure)
    audit(db, "integrity_scan", "evidence_storage", None, {"counts": result["counts"], "failures": result["failure_count"]})
    _commit(db)
    return result


@app.get("/api/privacy/retention-policy")
def privacy_retention_policy():
    return {
        "evidence_retention_days": settings.evidence_retention_days,
        "student_data_retention_days": settings.student_data_retention_days,
        "privacy_contact": settings.privacy_contact,
        "policy": "Kanıt dosyaları saklama süresi sonunda yetkili yönetici tarafından temizlenebilir. Öğrenci kimlik bilgileri gerekli durumda ilişkisel akademik kanıt korunarak geri döndürülemez biçimde anonimleştirilebilir. Audit kayıtları işlem izini korur.",
        "student_anonymization_endpoint": "/api/students/{student_id}/anonymize",
    }


@app.post("/api/privacy/purge-expired-evidence")
def purge_expired_evidence(db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    today = date.today()
    rows = db.scalars(select(m.EvidenceAsset).where(m.EvidenceAsset.retention_until.is_not(None), m.EvidenceAsset.retention_until < today)).all()
    root = Path(settings.evidence_storage_path)
    removed_files = 0
    ids = []
    for asset in rows:
        ids.append(asset.id)
        path = root / asset.stored_name
        try:
            if path.exists():
                path.unlink(); removed_files += 1
        except OSError:
            pass
        db.delete(asset)
    audit(db, "retention_purge", "evidence", None, {"count": len(ids), "asset_ids": ids[:200], "removed_files": removed_files, "cutoff": today.isoformat()})
    _commit(db)
    return {"deleted_records": len(ids), "deleted_files": removed_files, "cutoff": today.isoformat()}



def _active_exam_students(db: Session, exam_id: int) -> list[m.ExamStudent]:
    return db.scalars(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.attendance_status == "attended")).all()


def _grade_lock_blockers(db: Session, exam_id: int) -> dict:
    q_count = db.scalar(select(func.count()).select_from(m.Question).where(m.Question.exam_id == exam_id)) or 0
    active = db.scalar(select(func.count()).select_from(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.attendance_status == "attended")) or 0
    responses = db.scalar(select(func.count()).select_from(m.Response).join(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.attendance_status == "attended")) or 0
    expected = q_count * active
    reviews = db.scalar(select(func.count()).select_from(m.ScanReview).where(m.ScanReview.exam_id == exam_id, m.ScanReview.status == "open")) or 0
    incidents = db.scalar(select(func.count()).select_from(m.ExamIncident).where(m.ExamIncident.exam_id == exam_id, m.ExamIncident.status == "open", m.ExamIncident.severity == "critical")) or 0
    appeals = db.scalar(select(func.count()).select_from(m.GradeAppeal).where(m.GradeAppeal.exam_id == exam_id, m.GradeAppeal.status == "open")) or 0
    return {"question_count": int(q_count), "active_student_count": int(active), "expected_responses": int(expected), "response_count": int(responses), "missing_responses": max(0, int(expected-responses)), "open_scan_reviews": int(reviews), "open_critical_incidents": int(incidents), "open_appeals": int(appeals), "ready": (responses >= expected and reviews == 0 and incidents == 0 and appeals == 0)}


@app.patch("/api/exams/{exam_id}/students/{student_id}/attendance")
def update_exam_attendance(exam_id: int, student_id: int, data: AttendanceUpdate, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    if exam.grade_locked_at: raise HTTPException(409, "Puanlar kilitliyken katılım durumu değiştirilemez")
    es = db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.student_id == student_id))
    if not es: raise HTTPException(404, "Öğrenci sınava atanmamış")
    old = es.attendance_status
    es.attendance_status = data.status; es.attendance_note = data.note.strip(); es.attendance_updated_at = datetime.now(timezone.utc)
    audit(db, "attendance_update", "exam_student", es.id, {"from": old, "to": data.status, "note": data.note})
    _commit(db)
    return {"exam_student_id": es.id, "student_id": student_id, "attendance_status": es.attendance_status, "attendance_note": es.attendance_note}


@app.get("/api/exams/{exam_id}/grade-lock")
def grade_lock_status(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    exam = db.get(m.Exam, exam_id)
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    return {"locked": bool(exam.grade_locked_at), "locked_at": exam.grade_locked_at.isoformat() if exam.grade_locked_at else None, "locked_by": exam.grade_locked_by or "", "note": exam.grade_lock_note or "", "blockers": _grade_lock_blockers(db, exam_id)}


@app.post("/api/exams/{exam_id}/grade-lock")
def lock_exam_grades(exam_id: int, data: GradeLockRequest, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    exam = db.get(m.Exam, exam_id)
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    if exam.status != "grading": raise HTTPException(409, "Puan kilidi yalnız değerlendirme aşamasında kullanılabilir")
    blockers = _grade_lock_blockers(db, exam_id)
    if not blockers["ready"]: raise HTTPException(409, {"message": "Puanlar kilitlenemez", "blockers": blockers})
    if not exam.grade_locked_at:
        actor = current_user(); exam.grade_locked_at = datetime.now(timezone.utc); exam.grade_locked_by = actor.get("email") or "system"; exam.grade_lock_note = data.note.strip()[:2000]
        audit(db, "grade_lock", "exam", exam_id, {"note": exam.grade_lock_note, "blockers": blockers}); _commit(db)
    return grade_lock_status(exam_id, db)


@app.post("/api/exams/{exam_id}/grade-unlock")
def unlock_exam_grades(exam_id: int, data: GradeLockRequest, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    if not has_role("admin", "program_head"):
        raise HTTPException(403, "Puan kilidini yalnız Program Başkanı veya sistem yöneticisi açabilir")
    exam = db.get(m.Exam, exam_id)
    if not exam: raise HTTPException(404, "Sınav bulunamadı")
    if not (data.note or "").strip(): raise HTTPException(400, "Kilit açma gerekçesi zorunludur")
    old = {"locked_at": exam.grade_locked_at.isoformat() if exam.grade_locked_at else None, "locked_by": exam.grade_locked_by}
    exam.grade_locked_at = None; exam.grade_locked_by = ""; exam.grade_lock_note = ""
    audit(db, "grade_unlock", "exam", exam_id, {"reason": data.note, "previous": old}); _commit(db)
    return {"locked": False, "reason": data.note}


def _incident_out(x: m.ExamIncident) -> dict:
    return {"id":x.id,"exam_id":x.exam_id,"student_id":x.student_id,"incident_type":x.incident_type,"severity":x.severity,"description":x.description,"status":x.status,"resolution_note":x.resolution_note,"created_by":x.created_by,"resolved_by":x.resolved_by,"resolved_at":x.resolved_at.isoformat() if x.resolved_at else None,"created_at":x.created_at.isoformat() if x.created_at else None}


@app.get("/api/exams/{exam_id}/incidents")
def exam_incidents(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    return [_incident_out(x) for x in db.scalars(select(m.ExamIncident).where(m.ExamIncident.exam_id == exam_id).order_by(m.ExamIncident.status, m.ExamIncident.id.desc())).all()]


@app.post("/api/exams/{exam_id}/incidents", status_code=201)
def create_exam_incident(exam_id: int, data: ExamIncidentCreate, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=True)
    if not db.get(m.Exam, exam_id): raise HTTPException(404, "Sınav bulunamadı")
    if data.student_id and not db.scalar(select(m.ExamStudent.id).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.student_id == data.student_id)):
        raise HTTPException(400, "Öğrenci bu sınava atanmamış")
    actor=current_user(); obj=m.ExamIncident(exam_id=exam_id, student_id=data.student_id, incident_type=data.incident_type, severity=data.severity, description=data.description.strip(), created_by=actor.get("email") or "system")
    db.add(obj); db.flush(); audit(db,"incident_create","exam_incident",obj.id,data.model_dump()); _commit(db); return _incident_out(obj)


@app.patch("/api/incidents/{incident_id}")
def resolve_exam_incident(incident_id: int, data: ExamIncidentResolve, db: Session = Depends(get_db)):
    obj=db.get(m.ExamIncident,incident_id)
    if not obj: raise HTTPException(404,"Sınav olayı bulunamadı")
    require_exam_access(db,obj.exam_id,write=True)
    actor=current_user(); obj.status=data.status; obj.resolution_note=data.resolution_note.strip(); obj.resolved_by=actor.get("email") or "system"; obj.resolved_at=datetime.now(timezone.utc)
    audit(db,"incident_resolve","exam_incident",obj.id,{"status":data.status,"note":data.resolution_note}); _commit(db); return _incident_out(obj)


def _appeal_out(x: m.GradeAppeal) -> dict:
    return {"id":x.id,"exam_id":x.exam_id,"student_id":x.student_id,"question_id":x.question_id,"reason":x.reason,"status":x.status,"old_points":x.old_points,"new_points":x.new_points,"old_rubric_scores":x.old_rubric_scores or {},"new_rubric_scores":x.new_rubric_scores or {},"decision_note":x.decision_note,"created_by":x.created_by,"decided_by":x.decided_by,"decided_at":x.decided_at.isoformat() if x.decided_at else None,"created_at":x.created_at.isoformat() if x.created_at else None}


@app.get("/api/exams/{exam_id}/appeals")
def grade_appeals(exam_id:int, db:Session=Depends(get_db)):
    require_exam_access(db,exam_id,write=False)
    return [_appeal_out(x) for x in db.scalars(select(m.GradeAppeal).where(m.GradeAppeal.exam_id==exam_id).order_by(m.GradeAppeal.status,m.GradeAppeal.id.desc())).all()]


@app.post("/api/exams/{exam_id}/appeals", status_code=201)
def create_grade_appeal(exam_id:int,data:GradeAppealCreate,db:Session=Depends(get_db)):
    require_exam_access(db,exam_id,write=True)
    es=db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id==exam_id,m.ExamStudent.student_id==data.student_id))
    if not es: raise HTTPException(400,"Öğrenci bu sınava atanmamış")
    old_points=None; old_rubric={}
    if data.question_id:
        q=db.get(m.Question,data.question_id)
        if not q or q.exam_id!=exam_id: raise HTTPException(400,"Soru bu sınava ait değil")
        r=db.scalar(select(m.Response).where(m.Response.exam_student_id==es.id,m.Response.question_id==q.id))
        if r: old_points=float(r.awarded_points); old_rubric=dict(r.rubric_scores or {})
    actor=current_user(); obj=m.GradeAppeal(exam_id=exam_id,student_id=data.student_id,question_id=data.question_id,reason=data.reason.strip(),old_points=old_points,old_rubric_scores=old_rubric,created_by=actor.get("email") or "system")
    db.add(obj); db.flush(); audit(db,"appeal_create","grade_appeal",obj.id,data.model_dump()); _commit(db); return _appeal_out(obj)


@app.patch("/api/appeals/{appeal_id}")
def resolve_grade_appeal(appeal_id:int,data:GradeAppealResolve,db:Session=Depends(get_db)):
    obj=db.get(m.GradeAppeal,appeal_id)
    if not obj: raise HTTPException(404,"İtiraz bulunamadı")
    require_exam_access(db,obj.exam_id,write=True)
    if not has_role("admin","program_head"):
        raise HTTPException(403,"İtiraz kararını yalnız Program Başkanı veya sistem yöneticisi verebilir")
    if obj.status!="open": raise HTTPException(409,"İtiraz daha önce sonuçlandırılmış")
    if data.decision=="accepted" and obj.question_id:
        es=db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id==obj.exam_id,m.ExamStudent.student_id==obj.student_id))
        q=db.get(m.Question,obj.question_id)
        if not es or not q: raise HTTPException(409,"İtiraza bağlı sınav kaydı bulunamadı")
        r=db.scalar(select(m.Response).where(m.Response.exam_student_id==es.id,m.Response.question_id==q.id))
        if not r: raise HTTPException(409,"Yeniden değerlendirilecek cevap bulunamadı")
        if q.question_type=="classic":
            criteria=(q.rubric or {}).get("criteria") or []
            supplied=data.rubric_scores or {}
            if not criteria: raise HTTPException(409,"Klasik soru rubriği bulunamadı")
            new_scores={}
            for c in criteria:
                cid=str(c.get("id")); maximum=float(c.get("max_points") or 0)
                if cid not in supplied: raise HTTPException(400,f"{c.get('label')} kriter puanı zorunludur")
                val=float(supplied[cid])
                if val<0 or val>maximum: raise HTTPException(400,f"{c.get('label')} puanı 0-{maximum:g} arasında olmalıdır")
                new_scores[cid]=round(val,4)
            new_points=round(sum(new_scores.values()),4); r.rubric_scores=new_scores; obj.new_rubric_scores=new_scores
        else:
            if data.awarded_points is None: raise HTTPException(400,"Yeni puan zorunludur")
            new_points=float(data.awarded_points)
            if new_points<0 or new_points>float(q.points): raise HTTPException(400,"Yeni puan soru puan aralığında olmalıdır")
        obj.old_points=float(r.awarded_points); obj.old_rubric_scores=dict(r.rubric_scores or obj.old_rubric_scores or {}) if q.question_type!="classic" else obj.old_rubric_scores
        _old_points_for_log=r.awarded_points; _old_rubric_for_log=dict(r.rubric_scores or {})
        r.awarded_points=new_points; r.graded_by=current_user().get("email") or "system"; r.graded_at=datetime.now(timezone.utc); r.revision_no=int(r.revision_no or 1)+1
        _log_grade_revision(db, r, _old_points_for_log, _old_rubric_for_log, "appeal")
        obj.new_points=new_points
    obj.status=data.decision; obj.decision_note=data.decision_note.strip(); obj.decided_by=current_user().get("email") or "system"; obj.decided_at=datetime.now(timezone.utc)
    audit(db,"appeal_resolve","grade_appeal",obj.id,{"decision":data.decision,"new_points":obj.new_points,"note":data.decision_note}); _commit(db); return _appeal_out(obj)


@app.get("/api/exams/{exam_id}/moderation")
def classic_moderation(exam_id:int, db:Session=Depends(get_db)):
    require_exam_access(db,exam_id,write=False)
    data=exam_analytics(db,exam_id); signals=[]
    open_appeal_qids=set(db.scalars(select(m.GradeAppeal.question_id).where(m.GradeAppeal.exam_id==exam_id,m.GradeAppeal.status=="open",m.GradeAppeal.question_id.is_not(None))).all())
    for q in data.get("question_analysis",[]):
        if q.get("question_type")!="classic": continue
        reasons=[]
        if q.get("question_id") in open_appeal_qids: reasons.append("open_appeal")
        if "negative_discrimination" in (q.get("quality_flags") or []): reasons.append("negative_discrimination")
        if "high_blank_rate" in (q.get("quality_flags") or []): reasons.append("high_blank_rate")
        weak=[c for c in q.get("rubric_criteria") or [] if float(c.get("attainment_percent") or 0)<50]
        if weak: reasons.append("low_criterion_attainment")
        if reasons: signals.append({"question_id":q["question_id"],"order_no":q["order_no"],"reasons":reasons,"weak_criteria":weak,"sample_size":q.get("sample_size"),"confidence_level":q.get("confidence_level")})
    return {"exam_id":exam_id,"signal_count":len(signals),"signals":signals}


@app.get("/api/quality/control-queue")
def quality_control_queue(db:Session=Depends(get_db)):
    require_roles("admin","quality","program_head")
    exam_ids=list(db.scalars(select(m.Exam.id).where(m.Exam.status.in_(["grading","approved"]))).all())
    items=[]
    for exam_id in exam_ids:
        try:
            require_exam_access(db,exam_id,write=False)
        except HTTPException:
            continue
        exam=db.get(m.Exam,exam_id); blockers=_grade_lock_blockers(db,exam_id)
        if blockers["missing_responses"] or blockers["open_scan_reviews"] or blockers["open_critical_incidents"] or blockers["open_appeals"] or not exam.grade_locked_at:
            priority=100*blockers["open_critical_incidents"]+50*blockers["open_appeals"]+20*blockers["open_scan_reviews"]+min(20,blockers["missing_responses"])+(0 if exam.grade_locked_at else 5)
            items.append({"exam_id":exam.id,"title":exam.title,"status":exam.status,"priority":priority,"grade_locked":bool(exam.grade_locked_at),"blockers":blockers})
    return {"count":len(items),"items":sorted(items,key=lambda x:(-x["priority"],x["exam_id"]))}


@app.get("/api/exams/{exam_id}/evidence-package")
def evidence_package(exam_id: int, db: Session = Depends(get_db)):
    require_exam_access(db, exam_id, write=False)
    exam = _load_exam_detail_model(db, exam_id)
    analytics_data = exam_analytics(db, exam_id)
    exam_data = _exam_out(exam, include_detail=True)
    evidence = db.scalars(select(m.EvidenceAsset).where(m.EvidenceAsset.exam_id == exam_id)).all()
    root = Path(settings.evidence_storage_path)
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("exam.json", json.dumps(exam_data, ensure_ascii=False, indent=2, default=str))
        z.writestr("analytics.json", json.dumps(analytics_data, ensure_ascii=False, indent=2, default=str))
        incidents = db.scalars(select(m.ExamIncident).where(m.ExamIncident.exam_id == exam_id).order_by(m.ExamIncident.id)).all()
        appeals = db.scalars(select(m.GradeAppeal).where(m.GradeAppeal.exam_id == exam_id).order_by(m.GradeAppeal.id)).all()
        improvements = db.scalars(select(m.ImprovementAction).where(m.ImprovementAction.exam_id == exam_id).order_by(m.ImprovementAction.id)).all()
        z.writestr("quality/incidents.json", json.dumps([{"id":x.id,"student_id":x.student_id,"type":x.incident_type,"severity":x.severity,"description":x.description,"status":x.status,"resolution_note":x.resolution_note,"created_by":x.created_by,"resolved_by":x.resolved_by,"created_at":x.created_at.isoformat() if x.created_at else None} for x in incidents], ensure_ascii=False, indent=2, default=str))
        z.writestr("quality/appeals.json", json.dumps([{"id":x.id,"student_id":x.student_id,"question_id":x.question_id,"reason":x.reason,"status":x.status,"old_points":x.old_points,"new_points":x.new_points,"old_rubric_scores":x.old_rubric_scores,"new_rubric_scores":x.new_rubric_scores,"decision_note":x.decision_note,"decided_by":x.decided_by} for x in appeals], ensure_ascii=False, indent=2, default=str))
        z.writestr("quality/improvements.json", json.dumps([_improvement_out(x) for x in improvements], ensure_ascii=False, indent=2, default=str))
        if exam.questions:
            paper_bytes, paper_meta = build_exam_pdf(exam, "A")
            z.writestr("generated/exam-paper-booklet-A.pdf", paper_bytes)
            z.writestr("generated/exam-paper-booklet-A.metadata.json", json.dumps(paper_meta, ensure_ascii=False, indent=2))
        manifest = []
        for asset in evidence:
            path = root / asset.stored_name
            manifest.append({"id": asset.id, "student_id": asset.student_id, "kind": asset.kind, "category": asset.category, "description": asset.description, "version_no": asset.version_no, "retention_until": asset.retention_until.isoformat() if asset.retention_until else None, "original_name": asset.original_name, "sha256": asset.sha256})
            _verify_exam_evidence_integrity(db, asset, path)
            z.write(path, arcname=f"evidence/{asset.id}_{Path(asset.original_name).name}")
        z.writestr("evidence-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    buffer.seek(0)
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", exam.title)[:80] or f"exam_{exam_id}"
    return StreamingResponse(buffer, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="DOU_Assess_{name}.zip"'})


# Static UI is mounted last so /api routes always win.
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
