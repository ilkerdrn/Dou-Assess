from __future__ import annotations

from datetime import date, datetime, time
from io import BytesIO
import re
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import models as m
from ..security import validate_xlsx_container


REQUIRED_SHEETS = {"Programlar", "Dersler", "Ogrenciler", "Ders_Kayitlari", "OC_PC"}
OPTIONAL_SHEETS = {"Sinavlar", "Sorular"}


from .excel_tr import canonical_header, canonical_value, localize

class ImportValidationError(Exception):
    def __init__(self, errors: list[str]):
        errors = [localize(e) for e in errors]  # Turkish column names in every message
        super().__init__("; ".join(errors))
        self.errors = errors


def _rows(ws) -> list[dict[str, Any]]:
    values = list(ws.iter_rows(values_only=True))
    if not values:
        return []
    headers = [canonical_header(x) for x in values[0]]  # Turkish or English column headers
    result = []
    for idx, row in enumerate(values[1:], start=2):
        if all(v is None or str(v).strip() == "" for v in row):
            continue
        item = {headers[i]: canonical_value(headers[i], row[i] if i < len(row) else None) for i in range(len(headers))}
        item["__row__"] = idx
        result.append(item)
    return result


def _text(v) -> str:
    return "" if v is None else str(v).strip()


def _yes(v) -> bool:
    return _text(v).casefold() in {"1", "true", "evet", "yes", "e", "y"}


def _date(v) -> date | None:
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    text = _text(v)
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError("Tarih YYYY-MM-DD, GG.AA.YYYY veya GG/AA/YYYY biçiminde olmalıdır")


def _time(v) -> str | None:
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.strftime("%H:%M")
    if isinstance(v, time):
        return v.strftime("%H:%M")
    text = _text(v)
    if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
        return text
    raise ValueError("Saat SS:DD biçiminde olmalıdır")


def _codes(v) -> list[str]:
    seen: set[str] = set()
    result = []
    for item in re.split(r"[,;|]", _text(v)):
        code = item.strip()
        if code and code not in seen:
            seen.add(code)
            result.append(code)
    return result


def validate_workbook(data: bytes) -> tuple[dict[str, list[dict]], list[str]]:
    try:
        validate_xlsx_container(data)
    except Exception as exc:
        detail = getattr(exc, "detail", None)
        return {}, [str(detail or exc)]
    try:
        wb = load_workbook(BytesIO(data), read_only=True, data_only=True, keep_links=False)
    except Exception as exc:
        return {}, [f"Excel dosyası açılamadı: {exc}"]

    errors: list[str] = []
    missing = REQUIRED_SHEETS.difference(wb.sheetnames)
    if missing:
        errors.append("Eksik sayfalar: " + ", ".join(sorted(missing)))
        return {}, errors

    parsed = {name: _rows(wb[name]) for name in REQUIRED_SHEETS}
    for name in OPTIONAL_SHEETS:
        parsed[name] = _rows(wb[name]) if name in wb.sheetnames else []

    required_cols = {
        "Programlar": ["program_code", "program_name"],
        "Dersler": ["program_code", "course_code", "course_name", "academic_year", "term"],
        "Ogrenciler": ["program_code", "student_no", "full_name"],
        "Ders_Kayitlari": ["program_code", "course_code", "academic_year", "term", "student_no"],
        "OC_PC": ["program_code", "course_code", "academic_year", "term", "learning_outcome_code", "learning_outcome_description", "target", "program_outcome_code", "program_outcome_description", "contribution"],
        "Sinavlar": ["program_code", "course_code", "academic_year", "term", "exam_title"],
        "Sorular": ["program_code", "course_code", "academic_year", "term", "exam_title", "order_no", "question_type", "question_text", "points"],
    }

    for sheet, cols in required_cols.items():
        for row in parsed.get(sheet, []):
            for col in cols:
                if _text(row.get(col)) == "":
                    errors.append(f"{sheet} satır {row['__row__']}: '{col}' zorunludur")
            if sheet == "OC_PC":
                try:
                    target = float(row.get("target"))
                    if not 0 <= target <= 100:
                        raise ValueError
                except Exception:
                    errors.append(f"OC_PC satır {row['__row__']}: target 0-100 arasında sayı olmalıdır")
                try:
                    c = int(row.get("contribution"))
                    if not 1 <= c <= 5:
                        raise ValueError
                except Exception:
                    errors.append(f"OC_PC satır {row['__row__']}: contribution 1-5 arasında tam sayı olmalıdır")
            elif sheet == "Sinavlar":
                try:
                    if _text(row.get("duration_minutes")) and not 1 <= int(row.get("duration_minutes")) <= 600:
                        raise ValueError
                except Exception:
                    errors.append(f"Sinavlar satır {row['__row__']}: duration_minutes 1-600 arasında tam sayı olmalıdır")
                try:
                    if _text(row.get("assessment_weight_percent")) and not 0 <= float(row.get("assessment_weight_percent")) <= 100:
                        raise ValueError
                except Exception:
                    errors.append(f"Sinavlar satır {row['__row__']}: assessment_weight_percent 0-100 arasında olmalıdır")
                try:
                    if _text(row.get("booklet_count")) and int(row.get("booklet_count")) not in {1, 2, 4}:
                        raise ValueError
                except Exception:
                    errors.append(f"Sinavlar satır {row['__row__']}: booklet_count yalnız 1, 2 veya 4 olabilir")
                if _text(row.get("status")) and _text(row.get("status")).casefold() != "draft":
                    errors.append(f"Sinavlar satır {row['__row__']}: Excel aktarımı yalnız draft/taslak sınav oluşturabilir")
                for key, parser in (("exam_date", _date), ("start_time", _time)):
                    if _text(row.get(key)):
                        try:
                            parser(row.get(key))
                        except ValueError as exc:
                            errors.append(f"Sinavlar satır {row['__row__']}: {key} - {exc}")
            elif sheet == "Sorular":
                try:
                    order_no = int(row.get("order_no"))
                    if order_no < 1:
                        raise ValueError
                except Exception:
                    errors.append(f"Sorular satır {row['__row__']}: order_no 1 veya daha büyük tam sayı olmalıdır")
                qtype = _text(row.get("question_type")).casefold()
                if qtype not in {"mcq", "classic"}:
                    errors.append(f"Sorular satır {row['__row__']}: question_type mcq veya classic olmalıdır")
                try:
                    points = float(row.get("points"))
                    if not 0 < points <= 100:
                        raise ValueError
                except Exception:
                    errors.append(f"Sorular satır {row['__row__']}: points 0-100 arasında olmalıdır")
                if qtype == "mcq":
                    ans = _text(row.get("correct_answer")).upper()
                    if ans not in {"A", "B", "C", "D", "E"}:
                        errors.append(f"Sorular satır {row['__row__']}: mcq için correct_answer A-E olmalıdır")

    programs = {_text(r.get("program_code")) for r in parsed["Programlar"]}
    for r in parsed["Dersler"]:
        if _text(r.get("program_code")) not in programs:
            errors.append(f"Dersler satır {r['__row__']}: program_code Programlar sayfasında yok")
    for r in parsed["Ogrenciler"]:
        if _text(r.get("program_code")) not in programs:
            errors.append(f"Ogrenciler satır {r['__row__']}: program_code Programlar sayfasında yok")

    course_keys = {(_text(r.get("program_code")), _text(r.get("course_code")), _text(r.get("academic_year")), _text(r.get("term"))) for r in parsed["Dersler"]}
    student_program = {_text(r.get("student_no")): _text(r.get("program_code")) for r in parsed["Ogrenciler"]}
    student_nos = set(student_program)
    for r in parsed["Ders_Kayitlari"]:
        key = (_text(r.get("program_code")), _text(r.get("course_code")), _text(r.get("academic_year")), _text(r.get("term")))
        if key not in course_keys:
            errors.append(f"Ders_Kayitlari satır {r['__row__']}: program/ders/dönem Dersler sayfasında yok")
        student_no = _text(r.get("student_no"))
        if student_no not in student_nos:
            errors.append(f"Ders_Kayitlari satır {r['__row__']}: student_no Ogrenciler sayfasında yok")
        elif student_program.get(student_no) != _text(r.get("program_code")):
            errors.append(f"Ders_Kayitlari satır {r['__row__']}: öğrenci farklı programa ait")
    outcome_codes_by_course: dict[tuple[str, str, str, str], set[str]] = {}
    for r in parsed["OC_PC"]:
        key = (_text(r.get("program_code")), _text(r.get("course_code")), _text(r.get("academic_year")), _text(r.get("term")))
        if key not in course_keys:
            errors.append(f"OC_PC satır {r['__row__']}: program/ders/dönem Dersler sayfasında yok")
        outcome_codes_by_course.setdefault(key, set()).add(_text(r.get("learning_outcome_code")))

    exam_keys: set[tuple[str, str, str, str, str]] = set()
    for r in parsed["Sinavlar"]:
        ckey = (_text(r.get("program_code")), _text(r.get("course_code")), _text(r.get("academic_year")), _text(r.get("term")))
        if ckey not in course_keys:
            errors.append(f"Sinavlar satır {r['__row__']}: program/ders/dönem Dersler sayfasında yok")
        ekey = (*ckey, _text(r.get("exam_title")))
        if ekey in exam_keys:
            errors.append(f"Sinavlar satır {r['__row__']}: aynı ders/dönem içinde exam_title tekrar ediyor")
        exam_keys.add(ekey)

    question_orders: set[tuple[tuple[str, str, str, str, str], int]] = set()
    for r in parsed["Sorular"]:
        ckey = (_text(r.get("program_code")), _text(r.get("course_code")), _text(r.get("academic_year")), _text(r.get("term")))
        ekey = (*ckey, _text(r.get("exam_title")))
        if ekey not in exam_keys:
            errors.append(f"Sorular satır {r['__row__']}: sınav Sinavlar sayfasında yok")
        try:
            order_no = int(r.get("order_no"))
        except Exception:
            order_no = -1
        marker = (ekey, order_no)
        if order_no > 0 and marker in question_orders:
            errors.append(f"Sorular satır {r['__row__']}: aynı sınavda order_no tekrar ediyor")
        question_orders.add(marker)
        known = outcome_codes_by_course.get(ckey, set())
        for code in _codes(r.get("learning_outcome_codes")):
            if code not in known:
                errors.append(f"Sorular satır {r['__row__']}: '{code}' ÖÇ kodu OC_PC sayfasında bu ders için tanımlı değil")

    return parsed, [localize(e) for e in errors]


def _ensure_exam_snapshot(db: Session, exam: m.Exam, course: m.Course) -> None:
    live_los = db.scalars(select(m.LearningOutcome).where(m.LearningOutcome.course_id == course.id, m.LearningOutcome.is_active.is_(True))).all()
    existing_los = {x.code: x for x in db.scalars(select(m.ExamLearningOutcome).where(m.ExamLearningOutcome.exam_id == exam.id)).all()}
    lo_map: dict[int, m.ExamLearningOutcome] = {}
    for lo in live_los:
        snap = existing_los.get(lo.code)
        if not snap:
            snap = m.ExamLearningOutcome(exam_id=exam.id, source_learning_outcome_id=lo.id, code=lo.code, description=lo.description, target_percent=lo.target_percent)
            db.add(snap); db.flush()
        else:
            snap.description = lo.description
            snap.target_percent = lo.target_percent
            if not snap.source_learning_outcome_id:
                snap.source_learning_outcome_id = lo.id
        lo_map[lo.id] = snap

    live_pos = db.scalars(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == course.program_id, m.ProgramOutcome.academic_year == course.academic_year)).all()
    existing_pos = {x.code: x for x in db.scalars(select(m.ExamProgramOutcome).where(m.ExamProgramOutcome.exam_id == exam.id)).all()}
    po_map: dict[int, m.ExamProgramOutcome] = {}
    for po in live_pos:
        snap = existing_pos.get(po.code)
        if not snap:
            snap = m.ExamProgramOutcome(exam_id=exam.id, source_program_outcome_id=po.id, code=po.code, description=po.description)
            db.add(snap); db.flush()
        else:
            snap.description = po.description
            if not snap.source_program_outcome_id:
                snap.source_program_outcome_id = po.id
        po_map[po.id] = snap

    mappings = db.scalars(select(m.OutcomeMapping).join(m.LearningOutcome).where(m.LearningOutcome.course_id == course.id)).all()
    for mp in mappings:
        lo_snap = lo_map.get(mp.learning_outcome_id)
        po_snap = po_map.get(mp.program_outcome_id)
        if not lo_snap or not po_snap:
            continue
        existing = db.scalar(select(m.ExamOutcomeMapping).where(m.ExamOutcomeMapping.exam_learning_outcome_id == lo_snap.id, m.ExamOutcomeMapping.exam_program_outcome_id == po_snap.id))
        if not existing:
            db.add(m.ExamOutcomeMapping(exam_learning_outcome_id=lo_snap.id, exam_program_outcome_id=po_snap.id, contribution=mp.contribution))
        else:
            existing.contribution = mp.contribution


def _fill_exam_snapshot_fields(exam: m.Exam, course: m.Course) -> None:
    program = course.program
    exam.course_code_snapshot = course.code
    exam.course_name_snapshot = course.name
    exam.academic_year_snapshot = course.academic_year
    exam.term_snapshot = course.term
    exam.instructor_snapshot = course.instructor_name or ""
    exam.program_name_snapshot = program.name if program else ""
    exam.department_snapshot = program.department if program else ""
    exam.faculty_snapshot = program.faculty if program else ""


def _sync_exam_students(db: Session, exam: m.Exam) -> int:
    enrollment_ids = set(db.scalars(select(m.Enrollment.student_id).where(m.Enrollment.course_id == exam.course_id)).all())
    existing_ids = set(db.scalars(select(m.ExamStudent.student_id).where(m.ExamStudent.exam_id == exam.id)).all())
    count = 0
    for student_id in enrollment_ids - existing_ids:
        db.add(m.ExamStudent(exam_id=exam.id, student_id=student_id))
        count += 1
    return count


def _set_question_outcomes(db: Session, question: m.Question, outcomes: list[m.ExamLearningOutcome]) -> None:
    db.execute(delete(m.QuestionOutcome).where(m.QuestionOutcome.question_id == question.id))
    for lo in outcomes:
        db.add(m.QuestionOutcome(question_id=question.id, exam_learning_outcome_id=lo.id))
    question.exam_learning_outcome_id = outcomes[0].id if outcomes else None


def _set_bank_outcomes(db: Session, bank: m.QuestionBank, outcomes: list[m.LearningOutcome]) -> None:
    db.execute(delete(m.QuestionBankOutcome).where(m.QuestionBankOutcome.question_bank_id == bank.id))
    for lo in outcomes:
        db.add(m.QuestionBankOutcome(question_bank_id=bank.id, learning_outcome_id=lo.id))
    bank.learning_outcome_code = outcomes[0].code if outcomes else None


def import_workbook(
    db: Session,
    filename: str,
    data: bytes,
    *,
    source_system: str = "manual",
    allowed_course_ids: set[int] | None = None,
    allow_structure_updates: bool = True,
) -> dict:
    parsed, errors = validate_workbook(data)
    if errors:
        raise ImportValidationError(errors)

    summary = {
        "programs": 0, "courses": 0, "students": 0, "enrollments": 0,
        "learning_outcomes": 0, "program_outcomes": 0, "mappings": 0,
        "exams": 0, "exam_students": 0, "questions": 0, "bank_questions": 0,
    }

    # Scope and period checks happen before any data mutation.
    scope_errors: list[str] = []
    if allowed_course_ids is not None:
        for row in parsed["Dersler"]:
            program = db.scalar(select(m.Program).where(m.Program.code == _text(row["program_code"])))
            course = None
            if program:
                course = db.scalar(select(m.Course).where(
                    m.Course.program_id == program.id,
                    m.Course.code == _text(row["course_code"]),
                    m.Course.academic_year == _text(row["academic_year"]),
                    m.Course.term == _text(row["term"]),
                ))
            if not course:
                scope_errors.append(f"Dersler satır {row['__row__']}: öğretim elemanı aktarımında ders sistemde önceden oluşturulmuş olmalıdır")
            elif course.id not in allowed_course_ids:
                scope_errors.append(f"Dersler satır {row['__row__']}: bu derse veri aktarma yetkiniz yok")
    period_pairs = {(_text(r.get("academic_year")), _text(r.get("term"))) for r in parsed["Dersler"]}
    for academic_year, term in period_pairs:
        period = db.scalar(select(m.AcademicPeriod).where(m.AcademicPeriod.academic_year == academic_year, m.AcademicPeriod.term == term))
        if period and period.status in {"locked", "archived"}:
            scope_errors.append(f"{academic_year} {term}: akademik dönem kilitli/arşiv; Excel aktarımı yapılamaz")
    if scope_errors:
        raise ImportValidationError(scope_errors)

    # The caller wraps this whole function in a single transaction.
    program_by_code: dict[str, m.Program] = {}
    for row in parsed["Programlar"]:
        code = _text(row["program_code"])
        obj = db.scalar(select(m.Program).where(m.Program.code == code))
        if not obj:
            if not allow_structure_updates:
                raise ImportValidationError([f"Programlar satır {row['__row__']}: program sistemde bulunamadı"])
            obj = m.Program(code=code, name=_text(row["program_name"]), faculty=_text(row.get("faculty")), department=_text(row.get("department")), external_source=source_system, external_id=_text(row.get("external_id")) or _text(row.get("obs_program_id")) or None)
            db.add(obj); db.flush(); summary["programs"] += 1
        elif allow_structure_updates:
            obj.name = _text(row["program_name"])
            obj.faculty = _text(row.get("faculty"))
            obj.department = _text(row.get("department"))
            if source_system != "manual":
                obj.external_source = source_system
            if _text(row.get("external_id")) or _text(row.get("obs_program_id")):
                obj.external_id = _text(row.get("external_id")) or _text(row.get("obs_program_id"))
                obj.external_source = source_system
        program_by_code[code] = obj

    course_by_key: dict[tuple[str, str, str, str], m.Course] = {}
    for row in parsed["Dersler"]:
        key = (_text(row["program_code"]), _text(row["course_code"]), _text(row["academic_year"]), _text(row["term"]))
        program = program_by_code[key[0]]
        obj = db.scalar(select(m.Course).where(m.Course.program_id == program.id, m.Course.code == key[1], m.Course.academic_year == key[2], m.Course.term == key[3]))
        if not obj:
            if not allow_structure_updates:
                raise ImportValidationError([f"Dersler satır {row['__row__']}: ders sistemde bulunamadı"])
            obj = m.Course(program_id=program.id, code=key[1], name=_text(row["course_name"]), academic_year=key[2], term=key[3], instructor_email=_text(row.get("instructor_email")), instructor_name=_text(row.get("instructor_name")), external_source=source_system, external_id=_text(row.get("external_id")) or _text(row.get("obs_course_id")) or None)
            db.add(obj); db.flush(); summary["courses"] += 1
        elif allow_structure_updates:
            obj.name = _text(row["course_name"])
            obj.instructor_email = _text(row.get("instructor_email"))
            obj.instructor_name = _text(row.get("instructor_name"))
            if source_system != "manual":
                obj.external_source = source_system
            if _text(row.get("external_id")) or _text(row.get("obs_course_id")):
                obj.external_id = _text(row.get("external_id")) or _text(row.get("obs_course_id"))
                obj.external_source = source_system
        course_by_key[key] = obj

    student_by_no: dict[str, m.Student] = {}
    for row in parsed["Ogrenciler"]:
        no = _text(row["student_no"])
        program = program_by_code[_text(row["program_code"])]
        obj = db.scalar(select(m.Student).where(m.Student.student_no == no))
        if not obj:
            obj = m.Student(program_id=program.id, student_no=no, full_name=_text(row["full_name"]), class_name=_text(row.get("class_name")), external_source=source_system, external_id=_text(row.get("external_id")) or _text(row.get("obs_student_id")) or None)
            db.add(obj); db.flush(); summary["students"] += 1
        else:
            obj.program_id = program.id; obj.full_name = _text(row["full_name"]); obj.class_name = _text(row.get("class_name"))
            if source_system != "manual":
                obj.external_source = source_system
            if _text(row.get("external_id")) or _text(row.get("obs_student_id")):
                obj.external_id = _text(row.get("external_id")) or _text(row.get("obs_student_id"))
                obj.external_source = source_system
        student_by_no[no] = obj

    for row in parsed["Ders_Kayitlari"]:
        key = (_text(row["program_code"]), _text(row["course_code"]), _text(row["academic_year"]), _text(row["term"]))
        course = course_by_key[key]
        student = student_by_no[_text(row["student_no"])]
        existing = db.scalar(select(m.Enrollment).where(m.Enrollment.course_id == course.id, m.Enrollment.student_id == student.id))
        if not existing:
            db.add(m.Enrollment(course_id=course.id, student_id=student.id)); summary["enrollments"] += 1

    lo_cache: dict[tuple[int, str], m.LearningOutcome] = {}
    po_cache: dict[tuple[int, str, str], m.ProgramOutcome] = {}
    seen_map: set[tuple[int, int]] = set()
    for row in parsed["OC_PC"]:
        key = (_text(row["program_code"]), _text(row["course_code"]), _text(row["academic_year"]), _text(row["term"]))
        course = course_by_key[key]
        lo_code = _text(row["learning_outcome_code"])
        lo_key = (course.id, lo_code)
        lo = lo_cache.get(lo_key) or db.scalar(select(m.LearningOutcome).where(m.LearningOutcome.course_id == course.id, m.LearningOutcome.code == lo_code))
        if not lo:
            lo = m.LearningOutcome(course_id=course.id, code=lo_code, description=_text(row["learning_outcome_description"]), target_percent=float(row["target"]), source="obs")
            db.add(lo); db.flush(); summary["learning_outcomes"] += 1
        else:
            lo.description = _text(row["learning_outcome_description"]); lo.target_percent = float(row["target"])
        lo_cache[lo_key] = lo

        po_code = _text(row["program_outcome_code"])
        po_key = (course.program_id, course.academic_year, po_code)
        po = po_cache.get(po_key) or db.scalar(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == course.program_id, m.ProgramOutcome.academic_year == course.academic_year, m.ProgramOutcome.code == po_code))
        if not po:
            po = m.ProgramOutcome(program_id=course.program_id, academic_year=course.academic_year, code=po_code, description=_text(row["program_outcome_description"]))
            db.add(po); db.flush(); summary["program_outcomes"] += 1
        else:
            po.description = _text(row["program_outcome_description"])
        po_cache[po_key] = po

        map_key = (lo.id, po.id)
        if map_key in seen_map:
            continue
        seen_map.add(map_key)
        mp = db.scalar(select(m.OutcomeMapping).where(m.OutcomeMapping.learning_outcome_id == lo.id, m.OutcomeMapping.program_outcome_id == po.id))
        if not mp:
            db.add(m.OutcomeMapping(learning_outcome_id=lo.id, program_outcome_id=po.id, contribution=int(row["contribution"]))); summary["mappings"] += 1
        else:
            mp.contribution = int(row["contribution"])

    exam_by_key: dict[tuple[str, str, str, str, str], m.Exam] = {}
    for row in parsed["Sinavlar"]:
        ckey = (_text(row["program_code"]), _text(row["course_code"]), _text(row["academic_year"]), _text(row["term"]))
        course = course_by_key[ckey]
        title = _text(row["exam_title"])
        ekey = (*ckey, title)
        exam = db.scalar(select(m.Exam).where(m.Exam.course_id == course.id, m.Exam.title == title).order_by(m.Exam.id.desc()).limit(1))
        if exam and exam.status != "draft":
            raise ImportValidationError([f"Sinavlar satır {row['__row__']}: mevcut sınav taslak değil; Excel ile değiştirilemez"])
        if not exam:
            exam = m.Exam(course_id=course.id, title=title, status="draft")
            db.add(exam); db.flush(); summary["exams"] += 1
        exam.exam_type = _text(row.get("exam_type")) or exam.exam_type or "Sınav"
        exam.exam_date = _date(row.get("exam_date")) if _text(row.get("exam_date")) else None
        exam.start_time = _time(row.get("start_time")) if _text(row.get("start_time")) else None
        exam.location = _text(row.get("location"))
        exam.duration_minutes = int(row.get("duration_minutes") or 50)
        exam.assessment_weight_percent = float(row.get("assessment_weight_percent")) if _text(row.get("assessment_weight_percent")) else None
        exam.booklet_count = int(row.get("booklet_count") or 4)
        exam.instructions = _text(row.get("instructions"))
        exam.staff_notes = _text(row.get("staff_notes"))
        _fill_exam_snapshot_fields(exam, course)
        _ensure_exam_snapshot(db, exam, course)
        if _yes(row.get("sync_students")):
            summary["exam_students"] += _sync_exam_students(db, exam)
        exam_by_key[ekey] = exam

    for row in parsed["Sorular"]:
        ckey = (_text(row["program_code"]), _text(row["course_code"]), _text(row["academic_year"]), _text(row["term"]))
        course = course_by_key[ckey]
        ekey = (*ckey, _text(row["exam_title"]))
        exam = exam_by_key[ekey]
        if exam.status != "draft":
            raise ImportValidationError([f"Sorular satır {row['__row__']}: sınav taslak değil"])
        exam_los = {x.code: x for x in db.scalars(select(m.ExamLearningOutcome).where(m.ExamLearningOutcome.exam_id == exam.id)).all()}
        live_los = {x.code: x for x in db.scalars(select(m.LearningOutcome).where(m.LearningOutcome.course_id == course.id)).all()}
        codes = _codes(row.get("learning_outcome_codes"))
        outcomes = [exam_los[c] for c in codes if c in exam_los]
        choices = {letter: _text(row.get(f"choice_{letter}")) for letter in "ABCDE" if _text(row.get(f"choice_{letter}"))}
        order_no = int(row["order_no"])
        question = db.scalar(select(m.Question).where(m.Question.exam_id == exam.id, m.Question.order_no == order_no))
        if not question:
            question = m.Question(exam_id=exam.id, order_no=order_no, question_type=_text(row["question_type"]).casefold(), text=_text(row["question_text"]), points=float(row["points"]))
            db.add(question); db.flush(); summary["questions"] += 1
        question.question_type = _text(row["question_type"]).casefold()
        question.text = _text(row["question_text"])
        question.points = float(row["points"])
        question.correct_answer = _text(row.get("correct_answer")).upper() or None
        question.choices = choices or None
        question.answer_lines = int(row.get("answer_lines") or 8)
        _set_question_outcomes(db, question, outcomes)

        if _yes(row.get("add_to_bank")):
            bank = db.scalar(select(m.QuestionBank).where(m.QuestionBank.course_id == course.id, m.QuestionBank.question_type == question.question_type, m.QuestionBank.text == question.text).order_by(m.QuestionBank.id.desc()).limit(1))
            if not bank:
                bank = m.QuestionBank(course_id=course.id, question_type=question.question_type, text=question.text, default_points=question.points)
                db.add(bank); db.flush(); summary["bank_questions"] += 1
            bank.default_points = question.points
            bank.correct_answer = question.correct_answer
            bank.choices = question.choices
            bank.answer_lines = question.answer_lines
            bank.tags = [x.strip() for x in re.split(r"[,;]", _text(row.get("tags"))) if x.strip()]
            _set_bank_outcomes(db, bank, [live_los[c] for c in codes if c in live_los])
            question.bank_question_id = bank.id

    batch = m.ImportBatch(filename=filename, status="success", summary=summary)
    db.add(batch)
    db.flush()
    return {"batch_id": batch.id, "summary": summary}
