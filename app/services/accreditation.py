from __future__ import annotations

from collections import defaultdict
from statistics import mean
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from .analytics import exam_analytics


FINAL_EXAM_STATUSES = {"approved", "archived"}
REPRESENTATIVE_SLOTS = ("MIN", "AVG", "MAX")


def freeze_representatives(db: Session, exam_id: int) -> list[m.RepresentativeSnapshot]:
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise ValueError("Sınav bulunamadı")
    if exam.status not in FINAL_EXAM_STATUSES:
        raise ValueError("MIN/AVG/MAX seçimi yalnızca onaylanmış veya arşivlenmiş sınavda dondurulabilir")
    existing = db.scalars(select(m.RepresentativeSnapshot).where(m.RepresentativeSnapshot.exam_id == exam_id)).all()
    if {x.slot for x in existing} == set(REPRESENTATIVE_SLOTS):
        # A frozen accreditation selection is historical evidence. Re-running freeze must
        # be idempotent and may not silently replace the archived selection.
        return existing

    data = exam_analytics(db, exam_id)
    selected = data.get("evidence_selection") or {}
    mapping = [("MIN", selected.get("min")), ("AVG", selected.get("average")), ("MAX", selected.get("max"))]
    if any(row is None for _, row in mapping):
        raise ValueError("Temsilci öğrenci seçimi için sınavda notlandırılmış öğrenci bulunmalıdır")

    for row in existing:
        db.delete(row)
    db.flush()

    created: list[m.RepresentativeSnapshot] = []
    for slot, row in mapping:
        snap = m.RepresentativeSnapshot(
            exam_id=exam_id,
            slot=slot,
            student_id=row["student_id"],
            student_no=row["student_no"],
            full_name=row["full_name"],
            total_score=float(row["total_score"]),
            class_average=float(data["class_average"]),
        )
        db.add(snap)
        created.append(snap)
    db.flush()
    return created


def representative_rows(db: Session, exam_id: int) -> list[dict]:
    rows = db.scalars(
        select(m.RepresentativeSnapshot)
        .where(m.RepresentativeSnapshot.exam_id == exam_id)
        .order_by(m.RepresentativeSnapshot.id)
    ).all()
    order = {"MIN": 0, "AVG": 1, "MAX": 2}
    result = [
        {
            "id": x.id,
            "exam_id": x.exam_id,
            "slot": x.slot,
            "student_id": x.student_id,
            "student_no": x.student_no,
            "full_name": x.full_name,
            "total_score": round(float(x.total_score), 2),
            "class_average": round(float(x.class_average), 2),
            "selected_at": x.selected_at.isoformat() if x.selected_at else None,
        }
        for x in rows
    ]
    return sorted(result, key=lambda x: order.get(x["slot"], 99))


def sync_period_exams(db: Session, period: m.AccreditationPeriod) -> dict:
    courses = db.scalars(
        select(m.Course).where(
            m.Course.program_id == period.program_id,
            m.Course.academic_year == period.academic_year,
            m.Course.term == period.term,
        )
    ).all()
    course_ids = [c.id for c in courses]
    exams = []
    if course_ids:
        exams = db.scalars(select(m.Exam).where(m.Exam.course_id.in_(course_ids))).all()

    existing = {
        x.exam_id: x
        for x in db.scalars(select(m.AccreditationPeriodExam).where(m.AccreditationPeriodExam.period_id == period.id)).all()
    }
    added = 0
    for exam in exams:
        if exam.id not in existing:
            db.add(m.AccreditationPeriodExam(period_id=period.id, exam_id=exam.id))
            added += 1
    db.flush()
    return {"period_id": period.id, "course_count": len(courses), "exam_count": len(exams), "added": added}


def freeze_period_representatives(db: Session, period_id: int) -> dict:
    period = db.get(m.AccreditationPeriod, period_id)
    if not period:
        raise ValueError("Akreditasyon dönemi bulunamadı")
    links = db.scalars(
        select(m.AccreditationPeriodExam)
        .where(m.AccreditationPeriodExam.period_id == period_id)
        .order_by(m.AccreditationPeriodExam.id)
    ).all()
    frozen: list[int] = []
    skipped: list[dict] = []
    for link in links:
        exam = db.get(m.Exam, link.exam_id)
        if not exam:
            continue
        if exam.status not in FINAL_EXAM_STATUSES:
            skipped.append({"exam_id": exam.id, "title": exam.title, "reason": "Sınav henüz onaylı/arşiv değil"})
            continue
        try:
            freeze_representatives(db, exam.id)
            frozen.append(exam.id)
        except ValueError as exc:
            skipped.append({"exam_id": exam.id, "title": exam.title, "reason": str(exc)})
    db.flush()
    return {"period_id": period_id, "frozen_exam_ids": frozen, "frozen_count": len(frozen), "skipped": skipped}


def _asset_index(db: Session, exam_id: int) -> tuple[set[str], dict[int, set[str]]]:
    rows = db.scalars(select(m.EvidenceAsset).where(m.EvidenceAsset.exam_id == exam_id)).all()
    general: set[str] = set()
    per_student: dict[int, set[str]] = defaultdict(set)
    for item in rows:
        if item.student_id is None:
            general.add(item.kind)
        else:
            per_student[item.student_id].add(item.kind)
    return general, per_student


def _exam_dashboard(db: Session, exam: m.Exam, profile: m.AccreditationProfile) -> dict:
    analytics = exam_analytics(db, exam.id)
    reps = representative_rows(db, exam.id)
    general_assets, student_assets = _asset_index(db, exam.id)
    improvements = db.scalars(select(m.ImprovementAction).where(m.ImprovementAction.exam_id == exam.id)).all()

    warnings: list[str] = []
    if exam.status not in FINAL_EXAM_STATUSES:
        warnings.append("Sınav henüz onaylanmış/arşivlenmiş değil")
    if analytics["student_count"] == 0:
        warnings.append("Notlandırılmış öğrenci bulunmuyor")

    if profile.requires_representatives:
        slots = {x["slot"] for x in reps}
        missing_slots = [x for x in REPRESENTATIVE_SLOTS if x not in slots]
        if missing_slots:
            warnings.append("Dondurulmamış temsilci seçimleri: " + ", ".join(missing_slots))

    missing_general = [kind for kind in (profile.required_general_evidence_kinds or []) if kind not in general_assets]
    if missing_general:
        warnings.append("Eksik genel kanıt: " + ", ".join(missing_general))

    missing_rep: list[dict] = []
    rep_evidence_complete = 0
    rep_evidence_total = 0
    if profile.requires_representatives:
        for rep in reps:
            required = profile.required_representative_evidence_kinds or []
            missing = [kind for kind in required if kind not in student_assets.get(rep["student_id"], set())]
            rep_evidence_total += len(required)
            rep_evidence_complete += len(required) - len(missing)
            if missing:
                missing_rep.append({"slot": rep["slot"], "student_id": rep["student_id"], "student_no": rep["student_no"], "kinds": missing})
        if missing_rep:
            warnings.append("Temsilci öğrenci kanıtları eksik")

    gap_codes = [x["code"] for x in analytics["learning_outcomes"] if x["status"] == "needs_improvement"]
    open_actions = [x for x in improvements if x.status not in {"done", "cancelled"}]
    covered_codes = {x.outcome_code for x in improvements if x.status != "cancelled"}
    missing_actions = [code for code in gap_codes if code not in covered_codes]
    if profile.requires_improvement_for_gaps and missing_actions:
        warnings.append("İyileştirme aksiyonu olmayan ÖÇ: " + ", ".join(missing_actions))

    improvement_rows = [{
        "id": x.id,
        "outcome_code": x.outcome_code,
        "action_text": x.action_text,
        "owner": x.owner,
        "due_date": x.due_date.isoformat() if x.due_date else None,
        "status": x.status,
    } for x in sorted(improvements, key=lambda x: x.id, reverse=True)]

    return {
        "exam_id": exam.id,
        "title": exam.title,
        "exam_type": exam.exam_type,
        "exam_date": exam.exam_date.isoformat() if exam.exam_date else None,
        "status": exam.status,
        "course_id": exam.course_id,
        "course_code": exam.course_code_snapshot or exam.course.code,
        "course_name": exam.course_name_snapshot or exam.course.name,
        "instructor": exam.instructor_snapshot or exam.course.instructor_name,
        "student_count": analytics["student_count"],
        "class_average": analytics["class_average"],
        "learning_outcomes": analytics["learning_outcomes"],
        "program_outcomes": analytics["program_outcomes"],
        "lo_achieved": sum(1 for x in analytics["learning_outcomes"] if x["status"] == "achieved"),
        "lo_total": len(analytics["learning_outcomes"]),
        "po_achieved": sum(1 for x in analytics["program_outcomes"] if x.get("status") == "achieved"),
        "po_total": len(analytics["program_outcomes"]),
        "representatives": reps,
        "representative_frozen": {x["slot"] for x in reps} == set(REPRESENTATIVE_SLOTS),
        "representative_evidence_complete": rep_evidence_complete,
        "representative_evidence_total": rep_evidence_total,
        "missing_general_evidence": missing_general,
        "missing_representative_evidence": missing_rep,
        "improvement_gap_codes": gap_codes,
        "missing_improvement_actions": missing_actions,
        "open_improvement_count": len(open_actions),
        "improvements": improvement_rows,
        "warning_count": len(warnings),
        "warnings": warnings,
        "complete": not warnings,
    }


def _aggregate_period(rows: list[dict], courses: list[m.Course], profile: m.AccreditationProfile) -> dict:
    course_groups: dict[int, dict] = {
        c.id: {
            "course_id": c.id,
            "course_code": c.code,
            "course_name": c.name,
            "instructor": c.instructor_name,
            "exam_count": 0,
            "complete_exam_count": 0,
            "warning_count": 0,
            "lo_measurement_count": 0,
            "lo_achieved_count": 0,
            "po_measurement_count": 0,
            "po_achieved_count": 0,
            "po": {},
        }
        for c in courses
    }

    po_period: dict[str, dict] = {}
    gap_register: list[dict] = []
    improvement_register: list[dict] = []
    rep_register: list[dict] = []
    lo_measurements = 0
    lo_achieved = 0
    po_measurements = 0
    po_achieved = 0
    rep_required_exams = 0
    rep_frozen_exams = 0
    rep_evidence_total = 0
    rep_evidence_complete = 0

    for row in rows:
        group = course_groups.setdefault(row["course_id"], {
            "course_id": row["course_id"], "course_code": row["course_code"], "course_name": row["course_name"],
            "instructor": row.get("instructor", ""), "exam_count": 0, "complete_exam_count": 0, "warning_count": 0,
            "lo_measurement_count": 0, "lo_achieved_count": 0, "po_measurement_count": 0, "po_achieved_count": 0, "po": {},
        })
        group["exam_count"] += 1
        group["complete_exam_count"] += 1 if row["complete"] else 0
        group["warning_count"] += row["warning_count"]

        action_by_code: dict[str, list[dict]] = defaultdict(list)
        for action in row.get("improvements", []):
            action_by_code[action["outcome_code"]].append(action)
            improvement_register.append({
                "exam_id": row["exam_id"], "exam_title": row["title"], "course_id": row["course_id"],
                "course_code": row["course_code"], "course_name": row["course_name"], **action,
            })

        for lo in row["learning_outcomes"]:
            lo_measurements += 1
            group["lo_measurement_count"] += 1
            if lo["status"] == "achieved":
                lo_achieved += 1
                group["lo_achieved_count"] += 1
            else:
                actions = action_by_code.get(lo["code"], [])
                gap_register.append({
                    "exam_id": row["exam_id"], "exam_title": row["title"], "exam_type": row["exam_type"],
                    "course_id": row["course_id"], "course_code": row["course_code"], "course_name": row["course_name"],
                    "instructor": row.get("instructor", ""), "outcome_code": lo["code"], "description": lo["description"],
                    "target_percent": round(float(lo["target_percent"]), 2),
                    "attainment_percent": round(float(lo["attainment_percent"]), 2),
                    "gap_points": round(float(lo["target_percent"]) - float(lo["attainment_percent"]), 2),
                    "has_action": bool([a for a in actions if a["status"] != "cancelled"]),
                    "action_statuses": [a["status"] for a in actions],
                    "action_ids": [a["id"] for a in actions],
                })

        for po in row["program_outcomes"]:
            po_measurements += 1
            group["po_measurement_count"] += 1
            if po.get("status") == "achieved":
                po_achieved += 1
                group["po_achieved_count"] += 1
            item = po_period.setdefault(po["code"], {
                "code": po["code"], "description": po["description"], "attainments": [], "targets": [],
                "exam_ids": set(), "course_ids": set(),
            })
            item["attainments"].append(float(po["attainment_percent"]))
            item["targets"].append(float(po.get("target_percent", 0)))
            item["exam_ids"].add(row["exam_id"])
            item["course_ids"].add(row["course_id"])
            cpo = group["po"].setdefault(po["code"], {"attainments": [], "targets": [], "exam_ids": []})
            cpo["attainments"].append(float(po["attainment_percent"]))
            cpo["targets"].append(float(po.get("target_percent", 0)))
            cpo["exam_ids"].append(row["exam_id"])

        if profile.requires_representatives:
            rep_required_exams += 1
            if row["representative_frozen"]:
                rep_frozen_exams += 1
            rep_evidence_total += row["representative_evidence_total"]
            rep_evidence_complete += row["representative_evidence_complete"]
            missing_map = {x["student_id"]: x["kinds"] for x in row["missing_representative_evidence"]}
            for rep in row["representatives"]:
                rep_register.append({
                    "exam_id": row["exam_id"], "exam_title": row["title"], "course_code": row["course_code"],
                    "course_name": row["course_name"], **rep,
                    "missing_evidence": missing_map.get(rep["student_id"], []),
                    "evidence_complete": not missing_map.get(rep["student_id"]),
                })

    po_rows = []
    for code, item in sorted(po_period.items()):
        attainment = mean(item["attainments"]) if item["attainments"] else 0.0
        target = mean(item["targets"]) if item["targets"] else 0.0
        po_rows.append({
            "code": code, "description": item["description"], "target_percent": round(target, 2),
            "attainment_percent": round(attainment, 2),
            "status": "achieved" if item["attainments"] and attainment >= target else "needs_improvement",
            "exam_count": len(item["exam_ids"]), "course_count": len(item["course_ids"]),
        })

    for group in course_groups.values():
        normalized = {}
        for code, item in group["po"].items():
            attainment = mean(item["attainments"]) if item["attainments"] else 0.0
            target = mean(item["targets"]) if item["targets"] else 0.0
            normalized[code] = {
                "attainment_percent": round(attainment, 2), "target_percent": round(target, 2),
                "status": "achieved" if item["attainments"] and attainment >= target else "needs_improvement",
                "exam_count": len(set(item["exam_ids"])),
            }
        group["po"] = normalized
        group["measurement_status"] = "measured" if group["exam_count"] else "no_exam"

    uncovered_gaps = [x for x in gap_register if not x["has_action"]]
    action_status_counts = {status: sum(1 for x in improvement_register if x["status"] == status) for status in ("open", "in_progress", "done", "cancelled")}
    active_actions = [x for x in improvement_register if x["status"] != "cancelled"]
    no_exam_courses = [x for x in course_groups.values() if not x["exam_count"]]

    return {
        "courses": sorted(course_groups.values(), key=lambda x: (x["course_code"], x["course_name"])),
        "program_outcomes": po_rows,
        "gap_register": sorted(gap_register, key=lambda x: (-x["gap_points"], x["course_code"], x["outcome_code"])),
        "improvement_register": sorted(improvement_register, key=lambda x: (x["status"] == "done", x["due_date"] or "9999", x["course_code"])),
        "representative_register": rep_register,
        "metrics": {
            "lo_measurement_count": lo_measurements,
            "lo_achieved_count": lo_achieved,
            "lo_achievement_percent": round((lo_achieved / lo_measurements * 100.0) if lo_measurements else 0.0, 2),
            "po_measurement_count": po_measurements,
            "po_achieved_count": po_achieved,
            "po_achievement_percent": round((po_achieved / po_measurements * 100.0) if po_measurements else 0.0, 2),
            "program_outcome_average": round(mean([x["attainment_percent"] for x in po_rows]), 2) if po_rows else 0.0,
            "gap_count": len(gap_register),
            "uncovered_gap_count": len(uncovered_gaps),
            "gap_action_coverage_percent": round(((len(gap_register)-len(uncovered_gaps))/len(gap_register)*100.0) if gap_register else 100.0, 2),
            "improvement_action_count": len(active_actions),
            "improvement_status_counts": action_status_counts,
            "representative_required_exam_count": rep_required_exams,
            "representative_frozen_exam_count": rep_frozen_exams,
            "representative_evidence_total": rep_evidence_total,
            "representative_evidence_complete": rep_evidence_complete,
            "representative_evidence_percent": round((rep_evidence_complete/rep_evidence_total*100.0) if rep_evidence_total else (100.0 if not profile.requires_representatives else 0.0), 2),
            "unmeasured_course_count": len(no_exam_courses),
        },
    }


def period_dashboard(db: Session, period_id: int) -> dict:
    period = db.get(m.AccreditationPeriod, period_id)
    if not period:
        raise ValueError("Akreditasyon dönemi bulunamadı")
    profile = db.get(m.AccreditationProfile, period.profile_id)
    program = db.get(m.Program, period.program_id)
    courses = db.scalars(
        select(m.Course).where(
            m.Course.program_id == period.program_id,
            m.Course.academic_year == period.academic_year,
            m.Course.term == period.term,
        ).order_by(m.Course.code, m.Course.name)
    ).all()
    links = db.scalars(
        select(m.AccreditationPeriodExam)
        .where(m.AccreditationPeriodExam.period_id == period.id)
        .order_by(m.AccreditationPeriodExam.id)
    ).all()
    exam_ids = [x.exam_id for x in links]
    exams = []
    if exam_ids:
        exams = db.scalars(
            select(m.Exam)
            .where(m.Exam.id.in_(exam_ids))
            .order_by(m.Exam.course_id, m.Exam.exam_date, m.Exam.id)
        ).all()
    rows = [_exam_dashboard(db, exam, profile) for exam in exams]
    aggregate = _aggregate_period(rows, courses, profile)
    course_rows = aggregate["courses"]
    no_exam_count = aggregate["metrics"]["unmeasured_course_count"]
    warnings = sum(x["warning_count"] for x in rows) + no_exam_count
    ready = bool(rows) and all(x["complete"] for x in rows) and no_exam_count == 0

    return {
        "period": {
            "id": period.id,
            "title": period.title,
            "program_id": period.program_id,
            "profile_id": period.profile_id,
            "academic_year": period.academic_year,
            "term": period.term,
            "status": period.status,
            "created_at": period.created_at.isoformat() if period.created_at else None,
        },
        "program": {
            "id": program.id, "code": program.code, "name": program.name,
            "faculty": program.faculty, "department": program.department,
        } if program else None,
        "profile": {
            "id": profile.id, "code": profile.code, "name": profile.name, "version": profile.version,
            "required_general_evidence_kinds": profile.required_general_evidence_kinds or [],
            "required_representative_evidence_kinds": profile.required_representative_evidence_kinds or [],
            "requires_representatives": profile.requires_representatives,
            "requires_improvement_for_gaps": profile.requires_improvement_for_gaps,
        },
        "summary": {
            "course_count": len(course_rows),
            "exam_count": len(rows),
            "complete_exam_count": sum(1 for x in rows if x["complete"]),
            "warning_count": warnings,
            "ready": ready,
            **aggregate["metrics"],
        },
        "courses": course_rows,
        "program_outcomes": aggregate["program_outcomes"],
        "gap_register": aggregate["gap_register"],
        "improvement_register": aggregate["improvement_register"],
        "representative_register": aggregate["representative_register"],
        "exams": rows,
    }
