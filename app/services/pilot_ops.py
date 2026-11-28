from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import models as m


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _age_hours(iso_value: str | None) -> float | None:
    if not iso_value:
        return None
    try:
        dt = datetime.fromisoformat(str(iso_value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600)
    except Exception:
        return None


def _check(key: str, label: str, status: str, detail: str, action: str = "", required: bool = True) -> dict:
    return {"key": key, "label": label, "status": status, "detail": detail, "action": action, "required": required}


def build_pilot_readiness(db: Session, settings, version: str) -> dict:
    t0 = perf_counter()
    db.execute(text("SELECT 1")).scalar_one()
    program_count = db.scalar(select(func.count()).select_from(m.Program)) or 0
    course_count = db.scalar(select(func.count()).select_from(m.Course)) or 0
    student_count = db.scalar(select(func.count()).select_from(m.Student)) or 0
    user_count = db.scalar(select(func.count()).select_from(m.AppUser).where(m.AppUser.is_active.is_(True))) or 0
    admin_count = db.scalar(select(func.count(func.distinct(m.UserRoleAssignment.user_id))).where(m.UserRoleAssignment.role == "admin")) or 0
    active_period = db.scalar(select(m.AcademicPeriod).where(m.AcademicPeriod.status == "active").order_by(m.AcademicPeriod.id.desc()).limit(1))
    last_sync = db.scalar(select(m.IntegrationSyncRun).order_by(m.IntegrationSyncRun.id.desc()).limit(1))
    assigned_courses = db.scalar(select(func.count()).select_from(m.Course).where(m.Course.instructor_email != "")) or 0
    lo_course_count = db.scalar(select(func.count(func.distinct(m.LearningOutcome.course_id)))) or 0
    mapped_lo_count = db.scalar(select(func.count(func.distinct(m.OutcomeMapping.learning_outcome_id)))) or 0
    official_exam_count = db.scalar(select(func.count()).select_from(m.Exam).where(m.Exam.status.in_(["approved", "archived"]))) or 0
    open_reviews = db.scalar(select(func.count()).select_from(m.ScanReview).where(m.ScanReview.status == "open")) or 0
    failed_syncs = db.scalar(select(func.count()).select_from(m.IntegrationSyncRun).where(m.IntegrationSyncRun.status == "failed")) or 0

    ops_root = Path(settings.ops_storage_path)
    backup = _read_json(ops_root / "backup-status.json")
    restore = _read_json(ops_root / "restore-status.json")
    backup_age = _age_hours(backup.get("created_at"))
    restore_age = _age_hours(restore.get("created_at"))

    checks = [
        _check("database", "Veritabanı bağlantısı", "pass", "Veritabanı sorgusu başarılı.", "", True),
        _check("admin", "Sistem yöneticisi", "pass" if admin_count else "fail", f"{admin_count} admin rolü bulundu.", "Kullanıcı & Yetki", True),
        _check("period", "Aktif akademik dönem", "pass" if active_period else "fail", active_period.title if active_period else "Aktif dönem seçilmedi.", "Kurumsal Pilot", True),
        _check("programs", "Program verisi", "pass" if program_count else "fail", f"{program_count} program kayıtlı.", "Kurumsal Pilot", True),
        _check("courses", "Ders verisi", "pass" if course_count else "fail", f"{course_count} ders kayıtlı.", "Kurumsal Pilot", True),
        _check("students", "Öğrenci verisi", "pass" if student_count else "fail", f"{student_count} öğrenci kayıtlı.", "Kurumsal Pilot", True),
        _check("instructors", "Ders–öğretim elemanı eşleşmesi", "pass" if course_count and assigned_courses == course_count else ("warn" if assigned_courses else "fail"), f"{assigned_courses}/{course_count} derste öğretim elemanı tanımlı.", "Kullanıcı & Yetki", True),
        _check("outcomes", "ÖÇ/PÇ ölçüm altyapısı", "pass" if lo_course_count and mapped_lo_count else "warn", f"{lo_course_count} derste ÖÇ; {mapped_lo_count} ÖÇ en az bir PÇ ile eşleşmiş.", "ÖÇ ↔ PÇ Haritası", False),
        _check("obs", "OBS senkronu", "pass" if last_sync and last_sync.status == "success" else "warn", (f"Son senkron: {last_sync.filename} · {last_sync.status}" if last_sync else "Henüz OBS senkron kaydı yok."), "Kurumsal Pilot", False),
        _check("obs_mode", "OBS veri yönü", "pass" if not settings.obs_writeback_enabled else ("pass" if settings.obs_results_endpoint else "warn"), ("Read-only güvenli mod aktif; OBS'ye otomatik yazma kapalı." if not settings.obs_writeback_enabled else ("Kurumsal onaylı write-back açık ve endpoint tanımlı." if settings.obs_results_endpoint else "Write-back açık ancak OBS_RESULTS_ENDPOINT tanımlı değil.")), "Kurumsal Pilot", True),
        _check("obs_outbound", "OBS sonuç geri gönderimi", "pass" if settings.obs_writeback_enabled and bool(settings.obs_results_endpoint) else "warn", ("Kurumsal onaylı OBS write-back etkin." if settings.obs_writeback_enabled and settings.obs_results_endpoint else "Write-back kapalı; sonuçlar yalnız OBS-uyumlu Excel olarak dışa aktarılır."), "Kurumsal Pilot", False),
        _check("privacy", "KVKK veri yaşam döngüsü", "pass" if settings.evidence_retention_days > 0 and settings.student_data_retention_days > 0 else "fail", f"Kanıt: {settings.evidence_retention_days} gün · öğrenci kaydı: {settings.student_data_retention_days} gün.", "Sistem & Güvenlik", True),
        _check("backup", "Güncel yedek", "pass" if backup_age is not None and backup_age <= 168 else "warn", (f"Son yedek {backup_age:.1f} saat önce." if backup_age is not None else "Backup-Pilot.ps1 henüz başarıyla çalıştırılmamış."), "Backup-Pilot.ps1", True),
        _check("restore", "Restore doğrulaması", "pass" if restore_age is not None and restore_age <= 720 else "warn", (f"Son restore doğrulaması {restore_age:.1f} saat önce." if restore_age is not None else "Restore testi kaydı yok."), "Restore-Pilot.ps1", False),
        _check("identity", "Kurumsal kimlik", "pass" if settings.auth_required and settings.auth_provider == "entra" else "warn", ("Microsoft Entra zorunlu giriş aktif." if settings.auth_required else "Pilot kullanıcı seçimi açık; gerçek pilot öncesi Entra etkinleştirilmeli."), "ENTRA-PILOT-SETUP", False),
        _check("reviews", "Açık tarama incelemeleri", "pass" if open_reviews == 0 else "warn", f"{open_reviews} tarama incelemesi açık.", "Optik Okuma", False),
        _check("official_exam", "Uçtan uca resmî sınav", "pass" if official_exam_count else "warn", f"{official_exam_count} onaylı/arşivlenmiş sınav var.", "Sınav Hazırla", False),
        _check("sync_errors", "OBS hata kuyruğu", "pass" if failed_syncs == 0 else "warn", f"{failed_syncs} başarısız senkron kaydı var.", "Kurumsal Pilot", False),
    ]
    required = [x for x in checks if x["required"]]
    earned = sum(1 for x in required if x["status"] == "pass")
    score = round(100 * earned / len(required)) if required else 100
    overall = "ready" if score == 100 and not any(x["status"] == "fail" for x in checks) else ("blocked" if any(x["status"] == "fail" and x["required"] for x in checks) else "attention")
    return {
        "version": version, "status": overall, "score": score, "checks": checks,
        "counts": {"programs": int(program_count), "courses": int(course_count), "students": int(student_count), "users": int(user_count), "official_exams": int(official_exam_count), "open_reviews": int(open_reviews)},
        "backup": backup or None, "restore": restore or None,
        "generated_at": datetime.now(timezone.utc).isoformat(), "duration_ms": round((perf_counter() - t0) * 1000, 2),
    }


def operational_issues(db: Session, settings, version: str) -> list[dict]:
    readiness = build_pilot_readiness(db, settings, version)
    issues = []
    for c in readiness["checks"]:
        if c["status"] != "pass":
            issues.append({"severity": "critical" if c["status"] == "fail" else "warning", "source": "readiness", "title": c["label"], "message": c["detail"], "action": c["action"]})
    for row in db.scalars(select(m.SecurityEvent).where(m.SecurityEvent.severity.in_(["warning", "error", "critical"])).order_by(m.SecurityEvent.id.desc()).limit(20)).all():
        issues.append({"severity": "warning" if row.severity == "warning" else "critical", "source": "security", "title": row.event_type.replace("_", " ").title(), "message": f"{row.method} {row.path} · istek {row.request_id or '—'}", "action": "Sistem & Güvenlik", "created_at": row.created_at.isoformat() if row.created_at else None})
    return issues[:50]


def build_uat_checks(db: Session, settings, version: str) -> dict:
    readiness = build_pilot_readiness(db, settings, version)
    exam_count = db.scalar(select(func.count()).select_from(m.Exam)) or 0
    approved = db.scalar(select(func.count()).select_from(m.Exam).where(m.Exam.status.in_(["approved", "archived"]))) or 0
    grading_exam_count = db.scalar(select(func.count()).select_from(m.Exam).where(m.Exam.status == "grading")) or 0
    scan_sessions = db.scalar(select(func.count()).select_from(m.ScanSession)) or 0
    response_count = db.scalar(select(func.count()).select_from(m.Response)) or 0
    evidence_count = db.scalar(select(func.count()).select_from(m.EvidenceAsset)) or 0
    quality_evidence_count = db.scalar(select(func.count()).select_from(m.QualityEvidenceAsset)) or 0
    bank_question_count = db.scalar(select(func.count()).select_from(m.QuestionBank).where(m.QuestionBank.is_active.is_(True))) or 0
    improvements = db.scalar(select(func.count()).select_from(m.ImprovementAction)) or 0
    quality_cycles = db.scalar(select(func.count()).select_from(m.QualityCycle)) or 0
    program_reviews = db.scalar(select(func.count()).select_from(m.ProgramReview)) or 0
    outcome_maps = db.scalar(select(func.count()).select_from(m.OutcomeMapping)) or 0

    instructor_users = db.scalar(select(func.count(func.distinct(m.UserRoleAssignment.user_id))).where(m.UserRoleAssignment.role == "instructor")) or 0
    program_leads = db.scalar(select(func.count(func.distinct(m.UserRoleAssignment.user_id))).where(m.UserRoleAssignment.role.in_(["program_head", "department_head", "faculty_admin"]))) or 0
    quality_users = db.scalar(select(func.count(func.distinct(m.UserRoleAssignment.user_id))).where(m.UserRoleAssignment.role == "quality")) or 0

    def journey(key: str, role: str, title: str, target_minutes: int, items: list[dict]) -> dict:
        passed = sum(1 for item in items if item["status"] == "pass")
        score = round(100 * passed / len(items)) if items else 100
        blocking = any(item["status"] == "fail" for item in items)
        return {
            "key": key, "role": role, "title": title, "target_minutes": target_minutes,
            "status": "blocked" if blocking else ("ready" if score == 100 else "attention"),
            "score": score, "checks": items,
        }

    journeys = [
        journey("instructor", "instructor", "Öğretim Elemanı Yolculuğu", 7, [
            _check("role", "Rol ve ders erişimi", "pass" if instructor_users else "fail", f"{instructor_users} öğretim elemanı rolü tanımlı.", "Kullanıcı & Yetki"),
            _check("bank", "Soru Bankası", "pass" if bank_question_count else "warn", f"{bank_question_count} aktif soru bankası kaydı var.", "Soru Bankası", False),
            _check("exam", "Sınav hazırlama", "pass" if exam_count else "warn", f"{exam_count} sınav kaydı var.", "Sınav Hazırla", False),
            _check("grade", "Değerlendirme", "pass" if response_count or grading_exam_count else "warn", f"{grading_exam_count} puanlama durumunda sınav · {response_count} cevap/puan.", "Değerlendirme", False),
        ]),
        journey("program_head", "program_head", "Program Başkanı Yolculuğu", 8, [
            _check("role", "Program yönetim rolü", "pass" if program_leads else "fail", f"{program_leads} program/bölüm/fakülte yöneticisi tanımlı.", "Kullanıcı & Yetki"),
            _check("mapping", "Çıktı haritası", "pass" if outcome_maps else "warn", f"{outcome_maps} ÖÇ↔PÇ eşleşmesi var.", "ÖÇ ↔ PÇ Haritası", False),
            _check("review", "Program Değerlendirmesi", "pass" if program_reviews else "warn", f"{program_reviews} Program Değerlendirmesi kaydı var.", "Program Değerlendirmesi", False),
            _check("evidence", "Kanıt görünürlüğü", "pass" if evidence_count or quality_evidence_count else "warn", f"{evidence_count + quality_evidence_count} erişilebilir kanıt kaydı var.", "Kanıt Yönetimi", False),
        ]),
        journey("quality", "quality", "Kalite Kullanıcısı Yolculuğu", 8, [
            _check("role", "Kalite rolü", "pass" if quality_users else "fail", f"{quality_users} kalite kullanıcısı tanımlı.", "Kullanıcı & Yetki"),
            _check("cycle", "PUKÖ döngüsü", "pass" if quality_cycles else "warn", f"{quality_cycles} kalite/PUKÖ döngüsü var.", "Akreditasyon Merkezi", False),
            _check("evidence", "Kalite kanıtı", "pass" if quality_evidence_count else "warn", f"{quality_evidence_count} kalite kanıtı var.", "Kanıt Yönetimi", False),
            _check("improvement", "İyileştirme aksiyonu", "pass" if improvements else "warn", f"{improvements} iyileştirme aksiyonu var.", "Akreditasyon Merkezi", False),
        ]),
    ]

    checks = [
        _check("setup", "Kurumsal kurulum", "pass" if readiness["score"] == 100 else ("fail" if readiness["status"] == "blocked" else "warn"), f"Pilot hazırlık skoru %{readiness['score']}.", "Kurumsal Pilot"),
        _check("exam", "Sınav oluşturma akışı", "pass" if exam_count else "warn", f"{exam_count} sınav kaydı bulundu.", "Sınav Hazırla"),
        _check("approved", "Tamamlanmış sınav", "pass" if approved else "warn", f"{approved} onaylı/arşiv sınav bulundu.", "Değerlendirme"),
        _check("scan", "Optik okuma akışı", "pass" if scan_sessions else "warn", f"{scan_sessions} tarama oturumu bulundu.", "Optik Okuma"),
        _check("responses", "Puan/cevap verisi", "pass" if response_count else "warn", f"{response_count} soru cevabı/puanı bulundu.", "Değerlendirme"),
        _check("evidence", "Akreditasyon kanıtı", "pass" if evidence_count or quality_evidence_count else "warn", f"{evidence_count + quality_evidence_count} kanıt kaydı bulundu.", "Kanıt Yönetimi"),
        _check("improvement", "İyileştirme döngüsü", "pass" if improvements else "warn", f"{improvements} iyileştirme aksiyonu bulundu.", "Akreditasyon Merkezi"),
    ]
    passes = sum(1 for x in checks if x["status"] == "pass")
    score = round(100 * passes / len(checks))
    status = "passed" if score == 100 else ("failed" if any(x["status"] == "fail" for x in checks) else "warning")
    return {"status": status, "score": score, "checks": checks, "journeys": journeys, "readiness": readiness}
