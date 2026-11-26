from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models as m
from .analytics import exam_analytics

OFFICIAL_EXAM_STATUSES = {"approved", "archived"}
TERM_ORDER = {"Güz": 1, "Guz": 1, "Bahar": 2, "Yaz": 3}


def _avg(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    return round(mean(vals), 2) if vals else 0.0


def _exam_weight(exam: m.Exam) -> float:
    return max(0.0, float(exam.assessment_weight_percent or 0.0))


def _weighted_avg(pairs: Iterable[tuple[float, float]]) -> float:
    rows = [(float(value), max(0.0, float(weight))) for value, weight in pairs]
    weighted = [(value, weight) for value, weight in rows if weight > 0]
    if weighted:
        total = sum(weight for _, weight in weighted)
        return round(sum(value * weight for value, weight in weighted) / total, 2) if total else 0.0
    return _avg(value for value, _ in rows)


def _period_sort_key(pair: tuple[str, str]) -> tuple[str, int, str]:
    year, term = pair
    return (year or "", TERM_ORDER.get(term, 99), term or "")


def _official_exams(db: Session, course_ids: list[int]) -> list[m.Exam]:
    if not course_ids:
        return []
    return db.scalars(
        select(m.Exam)
        .where(m.Exam.course_id.in_(course_ids), m.Exam.status.in_(OFFICIAL_EXAM_STATUSES))
        .order_by(m.Exam.exam_date, m.Exam.id)
    ).all()


def _all_exams(db: Session, course_ids: list[int]) -> list[m.Exam]:
    if not course_ids:
        return []
    return db.scalars(
        select(m.Exam).where(m.Exam.course_id.in_(course_ids)).order_by(m.Exam.exam_date, m.Exam.id)
    ).all()


def _question_attainment(db: Session, exam: m.Exam) -> list[dict]:
    questions = db.scalars(
        select(m.Question).where(m.Question.exam_id == exam.id).order_by(m.Question.order_no)
    ).all()
    exam_students = db.scalars(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam.id, m.ExamStudent.attendance_status == "attended")).all()
    student_count = len(exam_students)
    question_ids = [q.id for q in questions]
    awarded_by_question: dict[int, float] = defaultdict(float)
    response_count: dict[int, int] = defaultdict(int)
    if question_ids:
        for qid, awarded in db.execute(
            select(m.Response.question_id, func.sum(m.Response.awarded_points))
            .join(m.ExamStudent, m.ExamStudent.id == m.Response.exam_student_id)
            .where(m.ExamStudent.exam_id == exam.id, m.ExamStudent.attendance_status == "attended", m.Response.question_id.in_(question_ids))
            .group_by(m.Response.question_id)
        ).all():
            awarded_by_question[int(qid)] = float(awarded or 0.0)
        for qid, count in db.execute(
            select(m.Response.question_id, func.count(m.Response.id))
            .join(m.ExamStudent, m.ExamStudent.id == m.Response.exam_student_id)
            .where(m.ExamStudent.exam_id == exam.id, m.ExamStudent.attendance_status == "attended", m.Response.question_id.in_(question_ids))
            .group_by(m.Response.question_id)
        ).all():
            response_count[int(qid)] = int(count or 0)

    lo_by_id = {
        lo.id: lo for lo in db.scalars(select(m.ExamLearningOutcome).where(m.ExamLearningOutcome.exam_id == exam.id)).all()
    }
    links: dict[int, set[int]] = defaultdict(set)
    if question_ids:
        for qid, loid in db.execute(
            select(m.QuestionOutcome.question_id, m.QuestionOutcome.exam_learning_outcome_id)
            .where(m.QuestionOutcome.question_id.in_(question_ids))
        ).all():
            links[int(qid)].add(int(loid))
    for q in questions:
        if not links[q.id] and q.exam_learning_outcome_id:
            links[q.id].add(int(q.exam_learning_outcome_id))

    rows = []
    for q in questions:
        possible = float(q.points) * student_count
        awarded = awarded_by_question.get(q.id, 0.0)
        attainment = (awarded / possible * 100.0) if possible > 0 else 0.0
        outcomes = [lo_by_id[loid] for loid in sorted(links.get(q.id, set())) if loid in lo_by_id]
        outcome_rows = [{
            "code": lo.code,
            "description": lo.description,
            "target_percent": round(float(lo.target_percent), 2),
            "gap_points": round(float(lo.target_percent) - attainment, 2),
            "status": "achieved" if attainment >= float(lo.target_percent) else "needs_improvement",
        } for lo in outcomes]
        max_target = max((float(lo.target_percent) for lo in outcomes), default=None)
        gap = (max_target - attainment) if max_target is not None else None
        codes = [lo.code for lo in outcomes]
        rows.append({
            "question_id": q.id,
            "order_no": q.order_no,
            "question_type": q.question_type,
            "text": q.text,
            "points": float(q.points),
            "learning_outcome_code": codes[0] if codes else None,
            "learning_outcome_codes": codes,
            "learning_outcomes": outcome_rows,
            "learning_outcome_description": outcomes[0].description if outcomes else None,
            "target_percent": round(max_target, 2) if max_target is not None else None,
            "attainment_percent": round(attainment, 2),
            "gap_points": round(gap, 2) if gap is not None else None,
            "status": (
                "unmapped" if not outcomes else "achieved" if all(x["status"] == "achieved" for x in outcome_rows) else "needs_improvement"
            ),
            "response_count": response_count.get(q.id, 0),
        })
    return rows


def _program_snapshot(db: Session, program: m.Program, academic_year: str, term: str) -> dict:
    courses = db.scalars(
        select(m.Course)
        .where(
            m.Course.program_id == program.id,
            m.Course.academic_year == academic_year,
            m.Course.term == term,
        )
        .order_by(m.Course.code, m.Course.name)
    ).all()
    course_ids = [c.id for c in courses]
    exams_all = _all_exams(db, course_ids)
    exams_official = [e for e in exams_all if e.status in OFFICIAL_EXAM_STATUSES]
    exams_by_course: dict[int, list[m.Exam]] = defaultdict(list)
    official_by_course: dict[int, list[m.Exam]] = defaultdict(list)
    for exam in exams_all:
        exams_by_course[exam.course_id].append(exam)
        if exam.status in OFFICIAL_EXAM_STATUSES:
            official_by_course[exam.course_id].append(exam)

    analytics_by_exam = {exam.id: exam_analytics(db, exam.id) for exam in exams_official}
    actions = db.scalars(
        select(m.ImprovementAction).where(m.ImprovementAction.exam_id.in_([e.id for e in exams_official]))
    ).all() if exams_official else []
    actions_by_exam_code: dict[tuple[int, str], list[m.ImprovementAction]] = defaultdict(list)
    for action in actions:
        actions_by_exam_code[(action.exam_id, action.outcome_code)].append(action)

    po_acc: dict[str, dict] = {}
    lo_measurements = 0
    lo_achieved = 0
    gap_count = 0
    uncovered_gap_count = 0
    open_action_count = sum(1 for a in actions if a.status in {"open", "in_progress"})
    course_rows = []

    for course in courses:
        course_official = official_by_course.get(course.id, [])
        course_lo = []
        course_po = []
        for exam in course_official:
            an = analytics_by_exam[exam.id]
            for lo in an["learning_outcomes"]:
                lo_measurements += 1
                if lo["status"] == "achieved":
                    lo_achieved += 1
                else:
                    gap_count += 1
                    active_actions = [a for a in actions_by_exam_code.get((exam.id, lo["code"]), []) if a.status != "cancelled"]
                    if not active_actions:
                        uncovered_gap_count += 1
                weight = _exam_weight(exam)
                course_lo.append({**lo, "exam_id": exam.id, "exam_title": exam.title, "assessment_weight_percent": weight})
            for po in an["program_outcomes"]:
                weight = _exam_weight(exam)
                course_po.append({**po, "exam_id": exam.id, "exam_title": exam.title, "assessment_weight_percent": weight})
                item = po_acc.setdefault(po["code"], {
                    "code": po["code"], "description": po["description"], "attainments": [], "targets": [], "exam_ids": set(), "course_ids": set(),
                })
                item["attainments"].append((float(po["attainment_percent"]), weight))
                item["targets"].append((float(po.get("target_percent", 0)), weight))
                item["exam_ids"].add(exam.id)
                item["course_ids"].add(course.id)

        course_gaps = [x for x in course_lo if x["status"] != "achieved"]
        max_gap = max((float(x["target_percent"]) - float(x["attainment_percent"]) for x in course_gaps), default=0.0)
        course_avg = _weighted_avg((analytics_by_exam[e.id]["class_average"], _exam_weight(e)) for e in course_official)
        course_po_avg = _weighted_avg((x["attainment_percent"], x["assessment_weight_percent"]) for x in course_po)
        weight_total = round(sum(_exam_weight(e) for e in course_official), 2)
        if not course_official or not course_lo:
            risk_level = "no_data"
        elif any((float(x["target_percent"]) - float(x["attainment_percent"])) >= 10 for x in course_gaps):
            risk_level = "critical"
        elif course_gaps:
            risk_level = "watch"
        else:
            risk_level = "good"
        course_rows.append({
            "course_id": course.id,
            "course_code": course.code,
            "course_name": course.name,
            "instructor": course.instructor_name or course.instructor_email,
            "exam_count": len(exams_by_course.get(course.id, [])),
            "official_exam_count": len(course_official),
            "assessment_weight_total": weight_total,
            "weights_valid": abs(weight_total - 100.0) <= 0.01 if course_official else False,
            "pass_threshold_percent": round(float(course.pass_threshold_percent or 50.0), 2),
            "class_average": course_avg,
            "program_outcome_average": course_po_avg,
            "gap_count": len(course_gaps),
            "max_gap_points": round(max_gap, 2),
            "risk_level": risk_level,
            "learning_outcomes": course_lo,
        })

    po_rows = []
    for code, item in sorted(po_acc.items()):
        attainment = _weighted_avg(item["attainments"])
        target = _weighted_avg(item["targets"])
        po_rows.append({
            "code": code,
            "description": item["description"],
            "attainment_percent": attainment,
            "target_percent": target,
            "gap_points": round(target - attainment, 2),
            "status": "achieved" if item["attainments"] and attainment >= target else "needs_improvement",
            "weighted": any(weight > 0 for _, weight in item["attainments"]),
            "exam_count": len(item["exam_ids"]),
            "course_count": len(item["course_ids"]),
        })

    enrollment_student_ids = set()
    if course_ids:
        enrollment_student_ids = set(db.scalars(select(m.Enrollment.student_id).where(m.Enrollment.course_id.in_(course_ids))).all())
    measured_course_count = sum(1 for c in course_rows if c["risk_level"] != "no_data")
    measurement_percent = (measured_course_count / len(courses) * 100.0) if courses else 0.0
    lo_percent = (lo_achieved / lo_measurements * 100.0) if lo_measurements else 0.0
    po_avg = _avg([x["attainment_percent"] for x in po_rows])
    po_target_avg = _avg([x["target_percent"] for x in po_rows])

    if not courses or measured_course_count < len(courses):
        status = "incomplete"
    elif uncovered_gap_count > 0 or any(x["gap_points"] >= 10 for x in po_rows if x["status"] != "achieved"):
        status = "critical"
    elif gap_count > 0 or open_action_count > 0:
        status = "watch"
    else:
        status = "good"

    return {
        "program_id": program.id,
        "program_code": program.code,
        "program_name": program.name,
        "faculty": program.faculty,
        "department": program.department,
        "academic_year": academic_year,
        "term": term,
        "course_count": len(courses),
        "measured_course_count": measured_course_count,
        "measurement_percent": round(measurement_percent, 2),
        "student_count": len(enrollment_student_ids),
        "exam_count": len(exams_all),
        "official_exam_count": len(exams_official),
        "learning_outcome_measurement_count": lo_measurements,
        "learning_outcome_achieved_count": lo_achieved,
        "learning_outcome_achievement_percent": round(lo_percent, 2),
        "program_outcome_average": po_avg,
        "program_outcome_target_average": po_target_avg,
        "gap_count": gap_count,
        "uncovered_gap_count": uncovered_gap_count,
        "open_action_count": open_action_count,
        "status": status,
        "program_outcomes": po_rows,
        "courses": sorted(course_rows, key=lambda x: ({"critical": 0, "watch": 1, "no_data": 2, "good": 3}.get(x["risk_level"], 4), -x["max_gap_points"], x["course_code"])),
    }


def quality_dashboard(
    db: Session,
    program_ids: list[int],
    academic_year: str | None = None,
    term: str | None = None,
    program_id: int | None = None,
    faculty: str | None = None,
    department: str | None = None,
) -> dict:
    programs = db.scalars(select(m.Program).where(m.Program.id.in_(program_ids)).order_by(m.Program.code)).all() if program_ids else []
    if program_id is not None:
        programs = [p for p in programs if p.id == program_id]
    if faculty:
        programs = [p for p in programs if (p.faculty or "").strip().casefold() == faculty.strip().casefold()]
    if department:
        programs = [p for p in programs if (p.department or "").strip().casefold() == department.strip().casefold()]
    scoped_ids = [p.id for p in programs]

    period_pairs = []
    if scoped_ids:
        period_pairs = list({(str(y), str(t)) for y, t in db.execute(
            select(m.Course.academic_year, m.Course.term).where(m.Course.program_id.in_(scoped_ids))
        ).all() if y and t})
    period_pairs = sorted(period_pairs, key=_period_sort_key, reverse=True)
    if academic_year and term:
        selected_pair = (academic_year, term)
    elif period_pairs:
        selected_pair = period_pairs[0]
    else:
        selected_pair = (academic_year or "", term or "")
    selected_year, selected_term = selected_pair

    snapshots = [_program_snapshot(db, p, selected_year, selected_term) for p in programs] if selected_year and selected_term else []
    all_course_rows = []
    for snap in snapshots:
        for course in snap["courses"]:
            all_course_rows.append({
                **course,
                "program_id": snap["program_id"], "program_code": snap["program_code"], "program_name": snap["program_name"],
                "faculty": snap["faculty"], "department": snap["department"],
            })
    all_course_rows.sort(key=lambda x: ({"critical": 0, "watch": 1, "no_data": 2, "good": 3}.get(x["risk_level"], 4), -x["max_gap_points"], x["program_code"], x["course_code"]))

    po_codes = sorted({po["code"] for snap in snapshots for po in snap["program_outcomes"]})
    heatmap = []
    for snap in snapshots:
        po_map = {po["code"]: po for po in snap["program_outcomes"]}
        heatmap.append({
            "program_id": snap["program_id"], "program_code": snap["program_code"], "program_name": snap["program_name"],
            "cells": [po_map.get(code) for code in po_codes],
        })

    total_courses = sum(s["course_count"] for s in snapshots)
    measured_courses = sum(s["measured_course_count"] for s in snapshots)
    lo_total = sum(s["learning_outcome_measurement_count"] for s in snapshots)
    lo_achieved = sum(s["learning_outcome_achieved_count"] for s in snapshots)
    official_exams = sum(s["official_exam_count"] for s in snapshots)
    all_exams = sum(s["exam_count"] for s in snapshots)
    gaps = sum(s["gap_count"] for s in snapshots)
    uncovered = sum(s["uncovered_gap_count"] for s in snapshots)
    actions = sum(s["open_action_count"] for s in snapshots)
    po_values = [po["attainment_percent"] for s in snapshots for po in s["program_outcomes"]]
    po_targets = [po["target_percent"] for s in snapshots for po in s["program_outcomes"]]

    trend = []
    for year, trm in period_pairs[:8]:
        period_snaps = [_program_snapshot(db, p, year, trm) for p in programs]
        p_courses = sum(x["course_count"] for x in period_snaps)
        p_measured = sum(x["measured_course_count"] for x in period_snaps)
        p_lo_total = sum(x["learning_outcome_measurement_count"] for x in period_snaps)
        p_lo_ok = sum(x["learning_outcome_achieved_count"] for x in period_snaps)
        p_po = [po["attainment_percent"] for x in period_snaps for po in x["program_outcomes"]]
        trend.append({
            "academic_year": year, "term": trm, "label": f"{year} {trm}",
            "program_count": len(period_snaps),
            "course_count": p_courses,
            "measurement_percent": round((p_measured / p_courses * 100.0) if p_courses else 0.0, 2),
            "learning_outcome_achievement_percent": round((p_lo_ok / p_lo_total * 100.0) if p_lo_total else 0.0, 2),
            "program_outcome_average": _avg(p_po),
            "official_exam_count": sum(x["official_exam_count"] for x in period_snaps),
        })
    trend.sort(key=lambda x: _period_sort_key((x["academic_year"], x["term"])))

    faculty_values = sorted({p.faculty for p in programs if p.faculty})
    department_values = sorted({p.department for p in programs if p.department})
    return {
        "filters": {
            "academic_year": selected_year,
            "term": selected_term,
            "program_id": program_id,
            "faculty": faculty or "",
            "department": department or "",
            "available_periods": [{"academic_year": y, "term": t, "label": f"{y} {t}"} for y, t in period_pairs],
            "faculties": faculty_values,
            "departments": department_values,
        },
        "summary": {
            "program_count": len(snapshots),
            "course_count": total_courses,
            "measured_course_count": measured_courses,
            "measurement_percent": round((measured_courses / total_courses * 100.0) if total_courses else 0.0, 2),
            "exam_count": all_exams,
            "official_exam_count": official_exams,
            "learning_outcome_achievement_percent": round((lo_achieved / lo_total * 100.0) if lo_total else 0.0, 2),
            "program_outcome_average": _avg(po_values),
            "program_outcome_target_average": _avg(po_targets),
            "gap_count": gaps,
            "uncovered_gap_count": uncovered,
            "open_action_count": actions,
            "critical_program_count": sum(1 for x in snapshots if x["status"] in {"critical", "incomplete"}),
            "critical_course_count": sum(1 for x in all_course_rows if x["risk_level"] in {"critical", "no_data"}),
        },
        "program_outcome_codes": po_codes,
        "program_heatmap": heatmap,
        "programs": snapshots,
        "risk_courses": all_course_rows,
        "trend": trend,
    }


def course_quality_drilldown(db: Session, course_id: int) -> dict:
    course = db.get(m.Course, course_id)
    if not course:
        raise ValueError("Ders bulunamadı")
    program = db.get(m.Program, course.program_id)
    exams_all = db.scalars(select(m.Exam).where(m.Exam.course_id == course.id).order_by(m.Exam.exam_date, m.Exam.id)).all()
    official = [e for e in exams_all if e.status in OFFICIAL_EXAM_STATUSES]
    exam_rows = []
    lo_acc: dict[str, dict] = {}
    question_rows = []
    for exam in official:
        an = exam_analytics(db, exam.id)
        exam_rows.append({
            "exam_id": exam.id, "title": exam.title, "exam_type": exam.exam_type,
            "exam_date": exam.exam_date.isoformat() if exam.exam_date else None, "status": exam.status,
            "student_count": an["student_count"], "class_average": an["class_average"],
            "learning_outcome_achievement_percent": round((sum(1 for x in an["learning_outcomes"] if x["status"] == "achieved") / len(an["learning_outcomes"]) * 100.0) if an["learning_outcomes"] else 0.0, 2),
            "program_outcome_average": _avg([x["attainment_percent"] for x in an["program_outcomes"]]),
        })
        exam_weight = _exam_weight(exam)
        for lo in an["learning_outcomes"]:
            item = lo_acc.setdefault(lo["code"], {"code": lo["code"], "description": lo["description"], "attainments": [], "targets": [], "exam_ids": []})
            item["attainments"].append((float(lo["attainment_percent"]), exam_weight))
            item["targets"].append((float(lo["target_percent"]), exam_weight))
            item["exam_ids"].append(exam.id)
        for row in _question_attainment(db, exam):
            question_rows.append({**row, "exam_id": exam.id, "exam_title": exam.title, "exam_type": exam.exam_type})

    lo_rows = []
    for code, item in sorted(lo_acc.items()):
        attainment = _weighted_avg(item["attainments"])
        target = _weighted_avg(item["targets"])
        lo_rows.append({
            "code": code, "description": item["description"], "attainment_percent": attainment,
            "target_percent": target, "gap_points": round(target - attainment, 2),
            "status": "achieved" if attainment >= target else "needs_improvement",
            "exam_count": len(set(item["exam_ids"])),
        })
    question_rows.sort(key=lambda x: (0 if x["status"] == "needs_improvement" else 1 if x["status"] == "unmapped" else 2, -(x["gap_points"] or 0), x["exam_id"], x["order_no"]))
    actions = db.scalars(select(m.ImprovementAction).where(m.ImprovementAction.exam_id.in_([e.id for e in official])).order_by(m.ImprovementAction.id.desc())).all() if official else []
    return {
        "course": {
            "id": course.id, "code": course.code, "name": course.name,
            "academic_year": course.academic_year, "term": course.term,
            "instructor_name": course.instructor_name, "instructor_email": course.instructor_email,
            "program_id": program.id if program else None, "program_code": program.code if program else "", "program_name": program.name if program else "",
            "department": program.department if program else "", "faculty": program.faculty if program else "",
        },
        "summary": {
            "exam_count": len(exams_all), "official_exam_count": len(official),
            "learning_outcome_count": len(lo_rows),
            "learning_outcome_gap_count": sum(1 for x in lo_rows if x["status"] != "achieved"),
            "question_count": len(question_rows),
            "question_risk_count": sum(1 for x in question_rows if x["status"] == "needs_improvement"),
            "unmapped_question_count": sum(1 for x in question_rows if x["status"] == "unmapped"),
            "class_average": _avg([x["class_average"] for x in exam_rows]),
        },
        "learning_outcomes": sorted(lo_rows, key=lambda x: (x["status"] == "achieved", -x["gap_points"], x["code"])),
        "questions": question_rows,
        "exams": exam_rows,
        "improvements": [{
            "id": a.id, "exam_id": a.exam_id, "outcome_code": a.outcome_code,
            "action_text": a.action_text, "owner": a.owner,
            "due_date": a.due_date.isoformat() if a.due_date else None, "status": a.status,
        } for a in actions],
    }


def course_lineage_analytics(db: Session, course_id: int) -> dict:
    """Aggregate the same program+course code across academic periods for longitudinal course analysis."""
    seed = db.get(m.Course, course_id)
    if not seed:
        raise ValueError("Ders bulunamadı")
    lineage = db.scalars(
        select(m.Course)
        .where(m.Course.program_id == seed.program_id, m.Course.code == seed.code)
        .order_by(m.Course.academic_year, m.Course.term, m.Course.id)
    ).all()
    periods = []
    for course in lineage:
        drill = course_quality_drilldown(db, course.id)
        summary = drill["summary"]
        lo_rows = drill["learning_outcomes"]
        exam_rows = drill["exams"]
        student_counts = [int(x.get("student_count") or 0) for x in exam_rows]
        lo_ok = sum(1 for x in lo_rows if x.get("status") == "achieved")
        lo_rate = round((lo_ok / len(lo_rows) * 100.0) if lo_rows else 0.0, 2)
        pass_rate_values = []
        for exam in _official_exams(db, [course.id]):
            an = exam_analytics(db, exam.id)
            students = an.get("students") or []
            if students:
                passed = sum(1 for st in students if float(st.get("score_percent") or 0) >= float(an.get("pass_threshold_percent") or 50))
                pass_rate_values.append(passed / len(students) * 100.0)
        periods.append({
            "course_id": course.id,
            "academic_year": course.academic_year,
            "term": course.term,
            "label": f"{course.academic_year} {course.term}",
            "exam_count": summary.get("official_exam_count", 0),
            "student_count": max(student_counts, default=0),
            "class_average": summary.get("class_average", 0),
            "pass_rate_percent": _avg(pass_rate_values),
            "learning_outcome_achievement_percent": lo_rate,
            "risk_outcome_count": summary.get("learning_outcome_gap_count", 0),
            "question_risk_count": summary.get("question_risk_count", 0),
        })
    periods.sort(key=lambda x: _period_sort_key((x["academic_year"], x["term"])))
    current = next((x for x in periods if x["course_id"] == course_id), periods[-1] if periods else None)
    current_drill = course_quality_drilldown(db, course_id)
    prev = periods[-2] if len(periods) >= 2 else None
    change = round(float(current["class_average"]) - float(prev["class_average"]), 2) if current and prev else None
    return {
        "course": current_drill["course"],
        "summary": {**current_drill["summary"],
            "student_count": int(current.get("student_count", 0)) if current else 0,
            "pass_rate_percent": float(current.get("pass_rate_percent", 0)) if current else 0.0,
            "learning_outcome_achievement_percent": float(current.get("learning_outcome_achievement_percent", 0)) if current else 0.0,
            "class_average_change_points": change,
            "period_count": len(periods),
        },
        "learning_outcomes": current_drill["learning_outcomes"],
        "exams": current_drill["exams"],
        "questions": current_drill["questions"],
        "improvements": current_drill["improvements"],
        "trend": periods,
    }
