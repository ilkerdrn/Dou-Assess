from __future__ import annotations

from collections import defaultdict
from statistics import mean, median, pstdev
from math import sqrt
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from .thresholds import active_threshold


def _question_outcome_map(db: Session, questions: list[m.Question]) -> dict[int, set[int]]:
    result: dict[int, set[int]] = defaultdict(set)
    if questions:
        for question_id, lo_id in db.execute(
            select(m.QuestionOutcome.question_id, m.QuestionOutcome.exam_learning_outcome_id)
            .where(m.QuestionOutcome.question_id.in_([q.id for q in questions]))
        ).all():
            result[int(question_id)].add(int(lo_id))
    # Legacy fallback protects databases imported before 0013/backfill.
    for q in questions:
        if not result[q.id] and q.exam_learning_outcome_id:
            result[q.id].add(int(q.exam_learning_outcome_id))
    return result


def _distribution(student_rows: list[dict]) -> list[dict]:
    bins = [
        (0, 9, "0–9"), (10, 19, "10–19"), (20, 29, "20–29"), (30, 39, "30–39"),
        (40, 49, "40–49"), (50, 59, "50–59"), (60, 69, "60–69"), (70, 79, "70–79"),
        (80, 89, "80–89"), (90, 100, "90–100"),
    ]
    rows = []
    for low, high, label in bins:
        count = sum(1 for s in student_rows if low <= float(s.get("score_percent", 0)) <= high)
        rows.append({"label": label, "min": low, "max": high, "count": count})
    return rows



def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx, my = mean(xs), mean(ys)
    dx = [x - mx for x in xs]; dy = [y - my for y in ys]
    den = sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    if den <= 1e-12:
        return None
    return sum(x*y for x, y in zip(dx, dy)) / den


def _reliability(questions: list[m.Question], exam_students: list[m.ExamStudent], resp_map: dict) -> dict:
    n = len(exam_students)
    k = len(questions)
    if n < 2 or k < 2:
        return {"cronbach_alpha": None, "kr20": None, "interpretation": "insufficient_data"}
    normalized_items: list[list[float]] = []
    dichotomous: list[list[float]] = []
    for q in questions:
        vals=[]; binary=[]
        for es in exam_students:
            r=resp_map.get((es.id,q.id)); score=float(r.awarded_points if r else 0.0)
            vals.append(score / float(q.points) if float(q.points) > 0 else 0.0)
            if q.question_type == "mcq": binary.append(1.0 if r and r.is_correct else 0.0)
        normalized_items.append(vals)
        if binary: dichotomous.append(binary)
    total_scores=[sum(item[i] for item in normalized_items) for i in range(n)]
    var_total=pstdev(total_scores)**2 if n>1 else 0.0
    alpha=None
    if var_total>1e-12:
        item_var=sum((pstdev(item)**2 if len(item)>1 else 0.0) for item in normalized_items)
        alpha=(k/(k-1))*(1-(item_var/var_total))
        alpha=max(-1.0,min(1.0,alpha))
    kr20=None
    km=len(dichotomous)
    if km>=2:
        mcq_totals=[sum(item[i] for item in dichotomous) for i in range(n)]
        v=pstdev(mcq_totals)**2 if n>1 else 0.0
        if v>1e-12:
            pq=0.0
            for item in dichotomous:
                pp=sum(item)/n; pq += pp*(1-pp)
            kr20=(km/(km-1))*(1-(pq/v)); kr20=max(-1.0,min(1.0,kr20))
    score = alpha if alpha is not None else kr20
    interpretation = "insufficient_data" if score is None else "high" if score >= .80 else "acceptable" if score >= .70 else "questionable" if score >= .60 else "low"
    return {"cronbach_alpha": round(alpha,4) if alpha is not None else None, "kr20": round(kr20,4) if kr20 is not None else None, "interpretation": interpretation}


def exam_analytics(db: Session, exam_id: int) -> dict:
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise ValueError("Sınav bulunamadı")

    questions = db.scalars(select(m.Question).where(m.Question.exam_id == exam_id).order_by(m.Question.order_no)).all()
    exam_students = db.scalars(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id, m.ExamStudent.attendance_status == "attended")).all()
    responses = db.scalars(
        select(m.Response)
        .join(m.ExamStudent, m.ExamStudent.id == m.Response.exam_student_id)
        .where(m.ExamStudent.exam_id == exam_id)
    ).all()

    resp_map = {(r.exam_student_id, r.question_id): r for r in responses}
    total_possible = round(sum(float(q.points) for q in questions), 2)
    student_rows = []
    for es in exam_students:
        total = 0.0
        answered = 0
        for q in questions:
            r = resp_map.get((es.id, q.id))
            total += float(r.awarded_points if r else 0.0)
            if r and str(r.answer_text or "").strip():
                answered += 1
        pct = (total / total_possible * 100.0) if total_possible > 0 else 0.0
        student_rows.append({
            "exam_student_id": es.id,
            "student_id": es.student_id,
            "student_no": es.student.student_no,
            "full_name": es.student.full_name,
            "total_score": round(total, 2),
            "score_percent": round(pct, 2),
            "answered_questions": answered,
        })

    ordered_for_rank = sorted(student_rows, key=lambda x: (-x["total_score"], x["student_no"]))
    last_score = None; last_rank = 0
    for idx, row in enumerate(ordered_for_rank, 1):
        score = row["total_score"]
        if last_score is None or abs(float(score) - float(last_score)) > 1e-9:
            last_rank = idx; last_score = score
        row["rank"] = last_rank

    selected = {"min": None, "average": None, "max": None}
    if student_rows:
        ordered = sorted(student_rows, key=lambda x: (x["total_score"], x["student_no"]))
        avg = mean(x["total_score"] for x in student_rows)
        selected = {
            "min": ordered[0],
            "average": min(student_rows, key=lambda x: (abs(x["total_score"] - avg), x["student_no"])),
            "max": ordered[-1],
        }
        med = median(x["total_score"] for x in student_rows)
        std = pstdev(x["total_score"] for x in student_rows) if len(student_rows) > 1 else 0.0
        min_score = min(x["total_score"] for x in student_rows)
        max_score = max(x["total_score"] for x in student_rows)
    else:
        avg = med = std = min_score = max_score = 0.0

    lo_by_id = {x.id: x for x in db.scalars(select(m.ExamLearningOutcome).where(m.ExamLearningOutcome.exam_id == exam_id)).all()}
    question_outcomes = _question_outcome_map(db, questions)

    lo_stats: dict[int, dict] = {}
    for lo_id, lo in lo_by_id.items():
        qs = [q for q in questions if lo_id in question_outcomes.get(q.id, set())]
        possible_per_student = sum(float(q.points) for q in qs)
        possible = possible_per_student * len(exam_students)
        awarded = 0.0
        for es in exam_students:
            for q in qs:
                r = resp_map.get((es.id, q.id))
                awarded += float(r.awarded_points if r else 0.0)
        pct = (awarded / possible * 100.0) if possible > 0 else 0.0
        lo_stats[lo_id] = {
            "id": lo_id,
            "code": lo.code,
            "description": lo.description,
            "target_percent": float(lo.target_percent),
            "attainment_percent": round(pct, 2),
            "gap_percent": round(pct - float(lo.target_percent), 2),
            "status": "achieved" if pct >= float(lo.target_percent) else "needs_improvement",
            "question_count": len(qs),
            "possible_points": round(possible_per_student, 2),
        }

    po_rows = db.scalars(select(m.ExamProgramOutcome).where(m.ExamProgramOutcome.exam_id == exam_id)).all()
    po_result = []
    _course = db.get(m.Course, exam.course_id)
    po_override = active_threshold(db, _course.program_id, _course.academic_year, "po") if _course else None
    for po in po_rows:
        mappings = db.scalars(
            select(m.ExamOutcomeMapping).where(m.ExamOutcomeMapping.exam_program_outcome_id == po.id)
        ).all()
        numerator = 0.0
        target_numerator = 0.0
        denominator = 0.0
        contributors = []
        for mp in mappings:
            stat = lo_stats.get(mp.exam_learning_outcome_id)
            if not stat or mp.contribution <= 0:
                continue
            numerator += stat["attainment_percent"] * mp.contribution
            target_numerator += stat["target_percent"] * mp.contribution
            denominator += mp.contribution
            contributors.append({"learning_outcome": stat["code"], "contribution": mp.contribution})
        attainment = numerator / denominator if denominator else 0.0
        target = target_numerator / denominator if denominator else 0.0
        if po_override is not None and denominator:
            target = po_override  # institution/program success threshold (versioned)
        po_result.append({
            "id": po.id,
            "code": po.code,
            "description": po.description,
            "target_percent": round(target, 2),
            "attainment_percent": round(attainment, 2),
            "gap_percent": round(attainment - target, 2),
            "status": "achieved" if denominator > 0 and attainment >= target else "needs_improvement",
            "contributors": contributors,
        })

    total_by_student = {row["exam_student_id"]: float(row["total_score"]) for row in student_rows}
    question_analysis = []
    for q in questions:
        q_responses = [resp_map.get((es.id, q.id)) for es in exam_students]
        awarded = sum(float(r.awarded_points if r else 0.0) for r in q_responses)
        possible = float(q.points) * len(exam_students)
        attainment = (awarded / possible * 100.0) if possible > 0 else 0.0
        blank_count = sum(1 for r in q_responses if not r or not str(r.answer_text or "").strip())
        full_count = sum(1 for r in q_responses if r and float(r.awarded_points or 0) >= float(q.points) - 1e-6)
        outcome_ids = sorted(question_outcomes.get(q.id, set()))
        outcome_codes = [lo_by_id[x].code for x in outcome_ids if x in lo_by_id]
        outcome_targets = [float(lo_by_id[x].target_percent) for x in outcome_ids if x in lo_by_id]
        target = max(outcome_targets) if outcome_targets else 0.0
        if attainment >= 75:
            difficulty = "Kolay"
            difficulty_code = "easy"
        elif attainment >= 50:
            difficulty = "Orta"
            difficulty_code = "medium"
        else:
            difficulty = "Zor"
            difficulty_code = "hard"
        item_scores = [float(r.awarded_points if r else 0.0) for r in q_responses]
        rest_scores = [max(0.0, total_by_student.get(es.id, 0.0) - item_scores[i]) for i, es in enumerate(exam_students)]
        discrimination = _pearson(item_scores, rest_scores)
        distractors = []
        if q.question_type == "mcq":
            choice_keys = sorted((q.choices or {}).keys())
            for key in choice_keys:
                count = sum(1 for r in q_responses if r and str(r.answer_text or "").strip().upper() == str(key).upper())
                distractors.append({"choice": key, "count": count, "percent": round(count / len(exam_students) * 100.0, 2) if exam_students else 0.0, "is_correct": str(key).upper() == str(q.correct_answer or "").upper()})
        flags=[]
        sample_size = len(exam_students)
        confidence_level = "low" if sample_size < 10 else "caution" if sample_size < 20 else "usable"
        if sample_size < 10:
            flags.append("small_sample")
        if discrimination is not None and discrimination < 0:
            flags.append("negative_discrimination")
        elif discrimination is not None and discrimination < 0.20:
            flags.append("low_discrimination")
        if blank_count and exam_students and blank_count / len(exam_students) >= .20:
            flags.append("high_blank_rate")
        if q.question_type == "mcq" and attainment >= 95:
            flags.append("too_easy")
        if q.question_type == "mcq" and attainment <= 20:
            flags.append("too_hard")
        rubric_criteria = []
        if q.question_type == "classic" and q.rubric and q.rubric.get("criteria"):
            for criterion in q.rubric.get("criteria") or []:
                cid = str(criterion.get("id") or "")
                max_points = float(criterion.get("max_points") or 0)
                awarded_criterion = sum(float((r.rubric_scores or {}).get(cid, 0)) for r in q_responses if r)
                possible_criterion = max_points * len(exam_students)
                criterion_pct = (awarded_criterion / possible_criterion * 100.0) if possible_criterion else 0.0
                rubric_criteria.append({
                    "id": cid, "label": criterion.get("label") or cid, "max_points": max_points,
                    "outcome_codes": criterion.get("outcome_codes") or [],
                    "attainment_percent": round(criterion_pct, 2),
                    "average_points": round(awarded_criterion / len(exam_students), 2) if exam_students else 0.0,
                    "status": "achieved" if criterion_pct >= target else "needs_improvement",
                })
        question_analysis.append({
            "question_id": q.id,
            "order_no": q.order_no,
            "question_type": q.question_type,
            "text": q.text,
            "points": float(q.points),
            "attainment_percent": round(attainment, 2),
            "target_percent": round(target, 2),
            "gap_percent": round(attainment - target, 2) if outcome_targets else None,
            "difficulty": difficulty,
            "difficulty_code": difficulty_code,
            "blank_count": blank_count,
            "blank_percent": round(blank_count / len(exam_students) * 100.0, 2) if exam_students else 0.0,
            "full_score_count": full_count,
            "full_score_percent": round(full_count / len(exam_students) * 100.0, 2) if exam_students else 0.0,
            "average_points": round(awarded / len(exam_students), 2) if exam_students else 0.0,
            "learning_outcome_codes": outcome_codes,
            "configured_difficulty": q.difficulty or "medium", "bloom_level": q.bloom_level or "understand",
            "topic": q.topic or "", "unit": q.unit or "",
            "discrimination_index": round(discrimination, 4) if discrimination is not None else None,
            "point_biserial": round(discrimination, 4) if discrimination is not None and q.question_type == "mcq" else None,
            "distractors": distractors, "quality_flags": flags, "sample_size": sample_size, "confidence_level": confidence_level,
            "rubric_criteria": rubric_criteria,
        })

    course = db.get(m.Course, exam.course_id)
    pass_threshold = float(course.pass_threshold_percent if course else 50.0)
    pass_count = sum(1 for x in student_rows if float(x["score_percent"]) >= pass_threshold)
    reliability = _reliability(questions, exam_students, resp_map)
    return {
        "exam_id": exam.id,
        "exam_title": exam.title,
        "exam_type": exam.exam_type,
        "total_possible_points": total_possible,
        "student_count": len(student_rows),
        "class_average": round(avg, 2),
        "class_average_percent": round((avg / total_possible * 100.0) if total_possible else 0.0, 2),
        "median_score": round(med, 2),
        "standard_deviation": round(std, 2),
        "min_score": round(min_score, 2),
        "max_score": round(max_score, 2),
        "pass_threshold_percent": pass_threshold,
        "pass_count": pass_count,
        "pass_percent": round(pass_count / len(student_rows) * 100.0, 2) if student_rows else 0.0,
        "students": student_rows,
        "score_distribution": _distribution(student_rows),
        "question_analysis": question_analysis,
        "evidence_selection": selected,
        "learning_outcomes": list(lo_stats.values()),
        "program_outcomes": po_result,
        "reliability": reliability,
        "problem_question_count": sum(1 for x in question_analysis if x.get("quality_flags")),
    }


def course_gradebook(db: Session, course_id: int, include_grading: bool = False) -> dict:
    course = db.get(m.Course, course_id)
    if not course:
        raise ValueError("Ders bulunamadı")
    statuses = {"approved", "archived"} | ({"grading"} if include_grading else set())
    exams = db.scalars(select(m.Exam).where(m.Exam.course_id == course_id, m.Exam.status.in_(statuses)).order_by(m.Exam.exam_date, m.Exam.id)).all()
    weighted = [e for e in exams if e.assessment_weight_percent is not None and float(e.assessment_weight_percent) > 0]
    total_weight = round(sum(float(e.assessment_weight_percent or 0) for e in weighted), 4)
    analytics = {e.id: exam_analytics(db, e.id) for e in weighted}
    enrollments = db.scalars(select(m.Enrollment).where(m.Enrollment.course_id == course_id)).all()
    student_rows=[]
    for en in enrollments:
        parts=[]; final=0.0
        for e in weighted:
            an=analytics[e.id]
            row=next((x for x in an["students"] if x["student_id"] == en.student_id), None)
            pct=float(row["score_percent"]) if row else 0.0
            weight=float(e.assessment_weight_percent or 0)
            contribution=pct*weight/100.0; final += contribution
            parts.append({"exam_id": e.id, "title": e.title, "exam_type": e.exam_type, "weight_percent": weight, "score_percent": round(pct,2), "contribution": round(contribution,2)})
        student_rows.append({"student_id": en.student_id, "student_no": en.student.student_no, "full_name": en.student.full_name, "final_grade": round(final,2), "status": "passed" if final >= float(course.pass_threshold_percent or 50) else "failed", "exams": parts})
    lo_acc: dict[str, dict] = {}
    po_acc: dict[str, dict] = {}
    for e in weighted:
        w=float(e.assessment_weight_percent or 0)
        an=analytics[e.id]
        for row in an["learning_outcomes"]:
            item=lo_acc.setdefault(row["code"], {"code": row["code"], "description": row["description"], "target_percent": row["target_percent"], "weighted_sum":0.0, "weight":0.0})
            item["weighted_sum"] += float(row["attainment_percent"])*w; item["weight"] += w
        for row in an["program_outcomes"]:
            item=po_acc.setdefault(row["code"], {"code": row["code"], "description": row["description"], "target_sum":0.0, "weighted_sum":0.0, "weight":0.0})
            item["weighted_sum"] += float(row["attainment_percent"])*w; item["target_sum"] += float(row["target_percent"])*w; item["weight"] += w
    lo_rows=[]
    for item in lo_acc.values():
        att=item["weighted_sum"]/item["weight"] if item["weight"] else 0; target=float(item["target_percent"] or 0)
        lo_rows.append({"code":item["code"],"description":item["description"],"target_percent":round(target,2),"attainment_percent":round(att,2),"status":"achieved" if att>=target else "needs_improvement"})
    po_rows=[]
    for item in po_acc.values():
        att=item["weighted_sum"]/item["weight"] if item["weight"] else 0; target=item["target_sum"]/item["weight"] if item["weight"] else 0
        po_rows.append({"code":item["code"],"description":item["description"],"target_percent":round(target,2),"attainment_percent":round(att,2),"status":"achieved" if att>=target else "needs_improvement"})
    avg=mean([x["final_grade"] for x in student_rows]) if student_rows else 0.0
    return {"course_id":course.id,"course_code":course.code,"course_name":course.name,"academic_year":course.academic_year,"term":course.term,"pass_threshold_percent":float(course.pass_threshold_percent or 50),"assessment_weight_total":total_weight,"weights_valid":abs(total_weight-100.0)<=0.01,"exams":[{"id":e.id,"title":e.title,"exam_type":e.exam_type,"weight_percent":float(e.assessment_weight_percent or 0),"status":e.status} for e in weighted],"student_count":len(student_rows),"class_average":round(avg,2),"pass_count":sum(1 for x in student_rows if x["status"]=="passed"),"students":student_rows,"learning_outcomes":sorted(lo_rows,key=lambda x:x["code"]),"program_outcomes":sorted(po_rows,key=lambda x:x["code"])}


def student_exam_analytics(db: Session, exam_id: int, exam_student_id: int) -> dict:
    exam = db.get(m.Exam, exam_id)
    es = db.get(m.ExamStudent, exam_student_id)
    if not exam or not es or es.exam_id != exam_id:
        raise ValueError("Öğrenci sınav kaydı bulunamadı")
    questions = db.scalars(select(m.Question).where(m.Question.exam_id == exam_id).order_by(m.Question.order_no)).all()
    responses = db.scalars(select(m.Response).where(m.Response.exam_student_id == es.id)).all()
    resp_map = {r.question_id: r for r in responses}
    lo_rows = db.scalars(select(m.ExamLearningOutcome).where(m.ExamLearningOutcome.exam_id == exam_id)).all()
    lo_by_id = {x.id: x for x in lo_rows}
    q_outcomes = _question_outcome_map(db, questions)

    question_rows = []
    total = 0.0
    total_possible = sum(float(q.points) for q in questions)
    for q in questions:
        r = resp_map.get(q.id)
        awarded = float(r.awarded_points if r else 0.0)
        total += awarded
        question_rows.append({
            "question_id": q.id,
            "order_no": q.order_no,
            "text": q.text,
            "question_type": q.question_type,
            "points": float(q.points),
            "awarded_points": round(awarded, 2),
            "answer_text": (r.answer_text if r else "") or "",
            "is_correct": r.is_correct if r else None,
            "rubric": q.rubric, "rubric_scores": (r.rubric_scores if r else {}) or {},
            "learning_outcome_codes": [lo_by_id[x].code for x in sorted(q_outcomes.get(q.id, set())) if x in lo_by_id],
        })

    lo_stats: dict[int, dict] = {}
    for lo in lo_rows:
        qs = [q for q in questions if lo.id in q_outcomes.get(q.id, set())]
        possible = sum(float(q.points) for q in qs)
        awarded = sum(float(resp_map[q.id].awarded_points or 0) if q.id in resp_map else 0.0 for q in qs)
        pct = awarded / possible * 100.0 if possible else 0.0
        lo_stats[lo.id] = {
            "code": lo.code,
            "description": lo.description,
            "target_percent": float(lo.target_percent),
            "attainment_percent": round(pct, 2),
            "status": "achieved" if pct >= float(lo.target_percent) else "needs_improvement",
            "question_count": len(qs),
        }

    po_result = []
    _course = db.get(m.Course, exam.course_id)
    po_override = active_threshold(db, _course.program_id, _course.academic_year, "po") if _course else None
    for po in db.scalars(select(m.ExamProgramOutcome).where(m.ExamProgramOutcome.exam_id == exam_id)).all():
        mappings = db.scalars(select(m.ExamOutcomeMapping).where(m.ExamOutcomeMapping.exam_program_outcome_id == po.id)).all()
        numerator = target_numerator = denominator = 0.0
        contributors = []
        for mp in mappings:
            stat = lo_stats.get(mp.exam_learning_outcome_id)
            if not stat or mp.contribution <= 0:
                continue
            numerator += stat["attainment_percent"] * mp.contribution
            target_numerator += stat["target_percent"] * mp.contribution
            denominator += mp.contribution
            contributors.append({"learning_outcome": stat["code"], "contribution": mp.contribution})
        attainment = numerator / denominator if denominator else 0.0
        target = target_numerator / denominator if denominator else 0.0
        if po_override is not None and denominator:
            target = po_override
        po_result.append({
            "code": po.code,
            "description": po.description,
            "target_percent": round(target, 2),
            "attainment_percent": round(attainment, 2),
            "status": "achieved" if denominator and attainment >= target else "needs_improvement",
            "contributors": contributors,
        })

    return {
        "exam_id": exam.id,
        "exam_student_id": es.id,
        "student_id": es.student_id,
        "student_no": es.student.student_no,
        "full_name": es.student.full_name,
        "total_score": round(total, 2),
        "total_possible_points": round(total_possible, 2),
        "score_percent": round(total / total_possible * 100.0, 2) if total_possible else 0.0,
        "learning_outcomes": list(lo_stats.values()),
        "program_outcomes": po_result,
        "questions": question_rows,
    }
