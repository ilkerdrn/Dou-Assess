from __future__ import annotations

from .excel_tr import localize_workbook
from io import BytesIO
from typing import Iterable
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from .analytics import exam_analytics


HEADER_FILL = PatternFill("solid", fgColor="B3132B")
HEADER_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(size=16, bold=True)
SUBTITLE_FONT = Font(size=11, bold=True)


def _fit_columns(ws, min_width: int = 10, max_width: int = 52) -> None:
    for idx, column_cells in enumerate(ws.columns, start=1):
        longest = 0
        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            if len(value) > longest:
                longest = len(value)
        ws.column_dimensions[get_column_letter(idx)].width = min(max(longest + 2, min_width), max_width)


def _header(ws, row: int = 1) -> None:
    for cell in ws[row]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def _tabular_sheet(wb: Workbook, title: str, headers: Iterable[str], rows: Iterable[Iterable]) -> None:
    ws = wb.create_sheet(title)
    ws.append(list(headers))
    for row in rows:
        ws.append(list(row))
    _header(ws)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    _fit_columns(ws)


def build_exam_results_xlsx(db: Session, exam_id: int) -> tuple[bytes, str]:
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise ValueError("Sınav bulunamadı")

    analytics = exam_analytics(db, exam_id)
    questions = db.scalars(
        select(m.Question).where(m.Question.exam_id == exam_id).order_by(m.Question.order_no)
    ).all()
    exam_students = db.scalars(
        select(m.ExamStudent).where(m.ExamStudent.exam_id == exam_id)
    ).all()
    exam_students = sorted(exam_students, key=lambda x: (x.student.student_no, x.student.full_name))
    responses = db.scalars(
        select(m.Response)
        .join(m.ExamStudent, m.ExamStudent.id == m.Response.exam_student_id)
        .where(m.ExamStudent.exam_id == exam_id)
    ).all()
    response_map = {(r.exam_student_id, r.question_id): r for r in responses}

    wb = Workbook()
    ws = wb.active
    ws.title = "Ozet"
    ws["A1"] = "DOU Assess · Sınav Sonuç Raporu"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:B1")

    course = exam.course
    program = course.program if course else None
    summary_rows = [
        ("Sınav ID", exam.id),
        ("Sınav", exam.title),
        ("Tür", exam.exam_type),
        ("Durum", exam.status),
        ("Tarih", exam.exam_date.isoformat() if exam.exam_date else ""),
        ("Ders", f"{exam.course_code_snapshot or (course.code if course else '')} · {exam.course_name_snapshot or (course.name if course else '')}".strip(" ·")),
        ("Program", exam.program_name_snapshot or (program.name if program else "")),
        ("Akademik Yıl", exam.academic_year_snapshot or (course.academic_year if course else "")),
        ("Dönem", exam.term_snapshot or (course.term if course else "")),
        ("Öğretim Elemanı", exam.instructor_snapshot or (course.instructor_name if course else "")),
        ("Öğrenci Sayısı", analytics["student_count"]),
        ("Sınıf Ortalaması", analytics["class_average"]),
        ("Toplam Soru", len(questions)),
        ("Toplam Puan", sum(float(q.points) for q in questions)),
        ("Geçme Eşiği %", analytics.get("pass_threshold_percent", 50)),
        ("Cronbach Alpha", analytics.get("reliability", {}).get("cronbach_alpha")),
        ("KR-20", analytics.get("reliability", {}).get("kr20")),
        ("Problemli Soru", analytics.get("problem_question_count", 0)),
    ]
    for key, value in summary_rows:
        ws.append([key, value])
    for row in range(2, ws.max_row + 1):
        ws.cell(row=row, column=1).font = SUBTITLE_FONT
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 58

    student_headers = ["Öğrenci No", "Ad Soyad", "Toplam Puan", "Başarı %", "Sıra"]
    for q in questions:
        student_headers.extend([f"S{q.order_no} Cevap", f"S{q.order_no} Puan"])
    student_rows = []
    analytics_student_map = {x["exam_student_id"]: x for x in analytics.get("students", [])}
    for es in exam_students:
        ast = analytics_student_map.get(es.id, {})
        row = [es.student.student_no, es.student.full_name]
        total = 0.0
        q_values: list[object] = []
        for q in questions:
            r = response_map.get((es.id, q.id))
            awarded = float(r.awarded_points if r else 0.0)
            total += awarded
            q_values.extend([(r.answer_text if r else "") or "", awarded])
        row.extend([round(total, 2), ast.get("score_percent", 0), ast.get("rank", "")])
        row.extend(q_values)
        student_rows.append(row)
    _tabular_sheet(wb, "Ogrenci_Sonuclari", student_headers, student_rows)

    question_rows = []
    for q in questions:
        question_rows.append([
            q.order_no,
            "Çoktan seçmeli" if q.question_type == "mcq" else "Klasik",
            q.text,
            float(q.points),
            ", ".join(x.code for x in getattr(q, "learning_outcomes", []) if x) or (q.learning_outcome.code if q.learning_outcome else ""),
            q.correct_answer or "", q.topic or "", q.unit or "", q.difficulty or "medium", q.bloom_level or "understand",
            "Evet" if q.image_data else "Hayır", "Evet" if q.rubric else "Hayır",
        ])
    _tabular_sheet(
        wb,
        "Sorular",
        ["Soru", "Tür", "Soru Metni", "Puan", "ÖÇ", "Doğru Cevap", "Konu", "Ünite", "Tanımlı Zorluk", "Bloom", "Görsel", "Rubrik"],
        question_rows,
    )

    qa_rows = [
        [
            x["order_no"],
            "Çoktan seçmeli" if x["question_type"] == "mcq" else "Klasik",
            x["text"], x["points"], x["average_points"], x["attainment_percent"],
            x.get("target_percent", 0), x.get("gap_percent", ""), x["difficulty"],
            x["blank_count"], x["blank_percent"], x["full_score_count"], x["full_score_percent"],
            ", ".join(x.get("learning_outcome_codes") or []),
            x.get("discrimination_index"), x.get("point_biserial"), x.get("configured_difficulty"), x.get("bloom_level"),
            x.get("topic", ""), x.get("unit", ""), ", ".join(x.get("quality_flags") or []),
            "; ".join(f"{d.get('choice')}:%{d.get('percent')}" for d in (x.get("distractors") or [])),
        ]
        for x in analytics.get("question_analysis", [])
    ]
    _tabular_sheet(
        wb, "Soru_Analizi",
        ["Soru", "Tür", "Soru Metni", "Puan", "Ort. Puan", "Başarı %", "ÖÇ Hedef %", "Fark", "İstatistiksel Zorluk", "Boş", "Boş %", "Tam Puan", "Tam Puan %", "ÖÇ", "Ayırt Edicilik", "Point-Biserial", "Tanımlı Zorluk", "Bloom", "Konu", "Ünite", "Kalite Uyarıları", "Çeldirici Dağılımı"],
        qa_rows,
    )

    distribution_rows = [[x["label"], x["count"]] for x in analytics.get("score_distribution", [])]
    _tabular_sheet(wb, "Not_Dagilimi", ["Başarı Aralığı %", "Öğrenci Sayısı"], distribution_rows)

    lo_rows = [
        [
            x["code"],
            x["description"],
            x["target_percent"],
            x["attainment_percent"],
            "Başarılı" if x["status"] == "achieved" else "İyileştirme Gerekli",
            x["question_count"],
        ]
        for x in analytics["learning_outcomes"]
    ]
    _tabular_sheet(
        wb,
        "OC_Basarisi",
        ["ÖÇ", "Açıklama", "Hedef %", "Başarı %", "Durum", "Soru Sayısı"],
        lo_rows,
    )

    po_rows = [
        [
            x["code"],
            x["description"],
            x.get("target_percent", 0),
            x["attainment_percent"],
            "Başarılı" if x.get("status") == "achieved" else "İyileştirme Gerekli",
            ", ".join(f"{c['learning_outcome']} ({c['contribution']})" for c in x["contributors"]),
        ]
        for x in analytics["program_outcomes"]
    ]
    _tabular_sheet(
        wb,
        "PC_Basarisi",
        ["PÇ", "Açıklama", "Hedef %", "Başarı %", "Durum", "Katkı Veren ÖÇ'ler"],
        po_rows,
    )

    evidence = analytics["evidence_selection"]
    evidence_rows = []
    for slot, label in (("min", "MIN"), ("average", "AVG"), ("max", "MAX")):
        selected = evidence.get(slot)
        if selected:
            evidence_rows.append([label, selected["student_no"], selected["full_name"], selected["total_score"]])
    _tabular_sheet(
        wb,
        "Kanit_Secimi",
        ["Seçim", "Öğrenci No", "Ad Soyad", "Toplam Puan"],
        evidence_rows,
    )

    for sheet in wb.worksheets:
        sheet.sheet_view.showGridLines = False

    buf = BytesIO()
    localize_workbook(wb)
    wb.save(buf)
    filename = f"DOU-Assess-Sinav-{exam.id}-Sonuclar.xlsx"
    return buf.getvalue(), filename



def build_accreditation_period_xlsx(db: Session, period_id: int) -> tuple[bytes, str]:
    """Build the program/period-level accreditation workbook used by 6.11.

    The workbook intentionally contains only derived/reporting data. Source evidence files
    stay in the evidence ZIP so the spreadsheet can be safely shared for committee review.
    """
    from .accreditation import period_dashboard

    dashboard = period_dashboard(db, period_id)
    period = dashboard["period"]
    program = dashboard.get("program") or {}
    profile = dashboard["profile"]
    summary = dashboard["summary"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Yonetici_Ozeti"
    ws["A1"] = "DOU Assess · Akreditasyon Dönem Raporu"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:B1")
    summary_rows = [
        ("Dönem", period["title"]),
        ("Program", f"{program.get('code','')} · {program.get('name','')}".strip(" ·")),
        ("Bölüm", program.get("department", "")),
        ("Fakülte / MYO", program.get("faculty", "")),
        ("Akademik Yıl", period["academic_year"]),
        ("Dönem Türü", period["term"]),
        ("Akreditasyon Profili", f"{profile['code']} · {profile['name']} · {profile['version']}"),
        ("Ders Sayısı", summary["course_count"]),
        ("Sınav Sayısı", summary["exam_count"]),
        ("Tamamlanan Sınav", summary["complete_exam_count"]),
        ("ÖÇ Başarı Oranı %", summary["lo_achievement_percent"]),
        ("PÇ Başarı Oranı %", summary["po_achievement_percent"]),
        ("PÇ Ortalama Başarı %", summary["program_outcome_average"]),
        ("İyileştirme Gereken ÖÇ", summary["gap_count"]),
        ("Aksiyonsuz ÖÇ", summary["uncovered_gap_count"]),
        ("Aksiyon Kapsama %", summary["gap_action_coverage_percent"]),
        ("Temsilci Kanıt Tamamlama %", summary["representative_evidence_percent"]),
        ("Ölçülmemiş Ders", summary["unmeasured_course_count"]),
        ("Açık Uyarı", summary["warning_count"]),
        ("Paket Hazır", "EVET" if summary["ready"] else "HAYIR"),
    ]
    for key, value in summary_rows:
        ws.append([key, value])
    for row in range(2, ws.max_row + 1):
        ws.cell(row=row, column=1).font = SUBTITLE_FONT
    ws.column_dimensions["A"].width = 31
    ws.column_dimensions["B"].width = 62

    po_codes = [x["code"] for x in dashboard["program_outcomes"]]
    matrix_headers = ["Ders Kodu", "Ders", "Öğretim Elemanı", "Sınav", "ÖÇ Başarı", "ÖÇ Ölçüm"]
    for code in po_codes:
        matrix_headers.extend([f"{code} Başarı %", f"{code} Hedef %", f"{code} Durum"])
    matrix_rows = []
    for c in dashboard["courses"]:
        row = [
            c["course_code"], c["course_name"], c.get("instructor", ""), c["exam_count"],
            c["lo_achieved_count"], c["lo_measurement_count"],
        ]
        for code in po_codes:
            cell = (c.get("po") or {}).get(code)
            if not cell:
                row.extend(["", "", "Ölçülmedi"])
            else:
                row.extend([
                    cell["attainment_percent"], cell["target_percent"],
                    "Başarılı" if cell["status"] == "achieved" else "İyileştirme Gerekli",
                ])
        matrix_rows.append(row)
    _tabular_sheet(wb, "Ders_PC_Matrisi", matrix_headers, matrix_rows)

    _tabular_sheet(
        wb,
        "PC_Donem_Ozeti",
        ["PÇ", "Açıklama", "Hedef %", "Başarı %", "Durum", "Ders Sayısı", "Sınav Sayısı"],
        [[
            x["code"], x["description"], x["target_percent"], x["attainment_percent"],
            "Başarılı" if x["status"] == "achieved" else "İyileştirme Gerekli",
            x["course_count"], x["exam_count"],
        ] for x in dashboard["program_outcomes"]],
    )

    _tabular_sheet(
        wb,
        "Basarisiz_OC",
        ["Ders", "Sınav", "ÖÇ", "Açıklama", "Hedef %", "Başarı %", "Fark (puan)", "Aksiyon Var", "Aksiyon Durumları"],
        [[
            f"{x['course_code']} · {x['course_name']}", x["exam_title"], x["outcome_code"], x["description"],
            x["target_percent"], x["attainment_percent"], x["gap_points"], "Evet" if x["has_action"] else "Hayır",
            ", ".join(x["action_statuses"]),
        ] for x in dashboard["gap_register"]],
    )

    _tabular_sheet(
        wb,
        "Iyilestirme_Aksiyonlari",
        ["Ders", "Sınav", "ÖÇ", "Aksiyon", "Sorumlu", "Termin", "Durum"],
        [[
            f"{x['course_code']} · {x['course_name']}", x["exam_title"], x["outcome_code"], x["action_text"],
            x["owner"], x["due_date"] or "", x["status"],
        ] for x in dashboard["improvement_register"]],
    )

    _tabular_sheet(
        wb,
        "MIN_AVG_MAX_Kanit",
        ["Ders", "Sınav", "Seçim", "Öğrenci No", "Ad Soyad", "Not", "Sınıf Ort.", "Kanıt Tamam", "Eksik Kanıt"],
        [[
            f"{x['course_code']} · {x['course_name']}", x["exam_title"], x["slot"], x["student_no"], x["full_name"],
            x["total_score"], x["class_average"], "Evet" if x["evidence_complete"] else "Hayır", ", ".join(x["missing_evidence"]),
        ] for x in dashboard["representative_register"]],
    )

    _tabular_sheet(
        wb,
        "Sinav_Kontrol_Listesi",
        ["Ders", "Sınav", "Durum", "Öğrenci", "ÖÇ", "PÇ", "Uyarı", "Tamam"],
        [[
            f"{x['course_code']} · {x['course_name']}", x["title"], x["status"], x["student_count"],
            f"{x['lo_achieved']}/{x['lo_total']}", f"{x['po_achieved']}/{x['po_total']}",
            " | ".join(x["warnings"]), "Evet" if x["complete"] else "Hayır",
        ] for x in dashboard["exams"]],
    )

    for sheet in wb.worksheets:
        sheet.sheet_view.showGridLines = False

    buf = BytesIO()
    localize_workbook(wb)
    wb.save(buf)
    return buf.getvalue(), f"DOU-Assess-Akreditasyon-Donem-{period['id']}.xlsx"


def build_quality_dashboard_xlsx(dashboard: dict) -> tuple[bytes, str]:
    """Export the management/quality dashboard payload without recalculating metrics."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Yonetici_Ozeti"
    ws["A1"] = "DOU Assess · Yönetim & Kalite Dashboard"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:B1")
    filters = dashboard.get("filters", {})
    summary = dashboard.get("summary", {})
    rows = [
        ("Akademik Yıl", filters.get("academic_year", "")),
        ("Dönem", filters.get("term", "")),
        ("Program Sayısı", summary.get("program_count", 0)),
        ("Ders Sayısı", summary.get("course_count", 0)),
        ("Ölçülen Ders", summary.get("measured_course_count", 0)),
        ("Ölçüm Kapsamı %", summary.get("measurement_percent", 0)),
        ("Onaylı/Arşiv Sınav", summary.get("official_exam_count", 0)),
        ("ÖÇ Başarı %", summary.get("learning_outcome_achievement_percent", 0)),
        ("PÇ Ortalama %", summary.get("program_outcome_average", 0)),
        ("PÇ Ortalama Hedef %", summary.get("program_outcome_target_average", 0)),
        ("Başarısız ÖÇ Ölçümü", summary.get("gap_count", 0)),
        ("Aksiyonsuz Açık", summary.get("uncovered_gap_count", 0)),
        ("Açık Aksiyon", summary.get("open_action_count", 0)),
        ("Riskli Program", summary.get("critical_program_count", 0)),
        ("Riskli / Ölçülmemiş Ders", summary.get("critical_course_count", 0)),
    ]
    for label, value in rows:
        ws.append([label, value])
    for r in range(2, ws.max_row + 1):
        ws.cell(r, 1).font = SUBTITLE_FONT
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 24

    po_codes = dashboard.get("program_outcome_codes", [])
    headers = ["Program", "Program Adı", "Birim", "Bölüm", "Ders", "Ölçülen Ders", "Ölçüm %", "ÖÇ Başarı %", "PÇ Ort. %", "Açık ÖÇ", "Aksiyonsuz", "Açık Aksiyon", "Durum"]
    for code in po_codes:
        headers.extend([f"{code} Başarı %", f"{code} Hedef %", f"{code} Durum"])
    program_rows = []
    for p in dashboard.get("programs", []):
        po_map = {x["code"]: x for x in p.get("program_outcomes", [])}
        row = [
            p["program_code"], p["program_name"], p.get("faculty", ""), p.get("department", ""),
            p["course_count"], p["measured_course_count"], p["measurement_percent"],
            p["learning_outcome_achievement_percent"], p["program_outcome_average"],
            p["gap_count"], p["uncovered_gap_count"], p["open_action_count"], p["status"],
        ]
        for code in po_codes:
            cell = po_map.get(code)
            row.extend([cell["attainment_percent"], cell["target_percent"], cell["status"]] if cell else ["", "", "Ölçülmedi"])
        program_rows.append(row)
    _tabular_sheet(wb, "Program_PC_Isi_Haritasi", headers, program_rows)

    _tabular_sheet(
        wb,
        "Riskli_Dersler",
        ["Program", "Ders", "Ders Adı", "Öğretim Elemanı", "Toplam Sınav", "Onaylı Sınav", "Sınıf Ort.", "PÇ Ort.", "Açık ÖÇ", "Maks. Fark", "Risk"],
        [[
            x["program_code"], x["course_code"], x["course_name"], x.get("instructor", ""),
            x["exam_count"], x["official_exam_count"], x["class_average"], x["program_outcome_average"],
            x["gap_count"], x["max_gap_points"], x["risk_level"],
        ] for x in dashboard.get("risk_courses", [])],
    )

    _tabular_sheet(
        wb,
        "Donem_Trendi",
        ["Dönem", "Program", "Ders", "Ölçüm %", "ÖÇ Başarı %", "PÇ Ort. %", "Onaylı Sınav"],
        [[
            x["label"], x["program_count"], x["course_count"], x["measurement_percent"],
            x["learning_outcome_achievement_percent"], x["program_outcome_average"], x["official_exam_count"],
        ] for x in dashboard.get("trend", [])],
    )

    for sheet in wb.worksheets:
        sheet.sheet_view.showGridLines = False
    localize_workbook(wb)
    buf = BytesIO(); wb.save(buf)
    raw_name = f"{filters.get('academic_year','donem')}-{filters.get('term','')}"
    ascii_name = raw_name.translate(str.maketrans({"ü":"u","Ü":"U","ö":"o","Ö":"O","ç":"c","Ç":"C","ş":"s","Ş":"S","ğ":"g","Ğ":"G","ı":"i","İ":"I"}))
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_name).strip("_") or "donem"
    return buf.getvalue(), f"DOU-Assess-Yonetim-Kalite-{safe}.xlsx"


def build_course_gradebook_xlsx(db: Session, course_id: int, *, obs_mode: bool = False) -> tuple[bytes, str]:
    """Build the weighted course gradebook and an OBS-friendly flat result sheet."""
    from .analytics import course_gradebook

    course = db.get(m.Course, course_id)
    if not course:
        raise ValueError("Ders bulunamadı")
    data = course_gradebook(db, course_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "OBS_Aktarim" if obs_mode else "Ders_Notlari"
    headers = ["Öğrenci No", "Ad Soyad"]
    for exam in data.get("exams", []):
        headers.append(f"{exam['title']} (%{exam['weight_percent']:g})")
    headers.extend(["Başarı Notu", "Geçme Eşiği", "Durum"])
    ws.append(headers)
    for student in data.get("students", []):
        row = [student["student_no"], student["full_name"]]
        scores = {x["exam_id"]: x for x in student.get("exams", [])}
        for exam in data.get("exams", []):
            row.append(scores.get(exam["id"], {}).get("score_percent", 0))
        row.extend([
            student.get("final_grade", 0),
            data.get("pass_threshold_percent", 50),
            "BAŞARILI" if student.get("status") == "passed" else "BAŞARISIZ",
        ])
        ws.append(row)
    _header(ws)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    _fit_columns(ws)

    if not obs_mode:
        summary = wb.create_sheet("Ozet")
        summary.append(["DOU Assess · Ders Değerlendirme Özeti", ""])
        summary["A1"].font = TITLE_FONT
        summary.merge_cells("A1:B1")
        summary_rows = [
            ("Ders", f"{course.code} · {course.name}"),
            ("Akademik Yıl", course.academic_year),
            ("Dönem", course.term),
            ("Geçme Eşiği", data.get("pass_threshold_percent", 50)),
            ("Sınav Ağırlıkları Toplamı", data.get("assessment_weight_total", 0)),
            ("Ağırlık Planı Geçerli", "Evet" if data.get("weights_valid") else "Hayır"),
            ("Sınıf Ortalaması", data.get("class_average", 0)),
            ("Başarılı Öğrenci", data.get("pass_count", 0)),
            ("Öğrenci Sayısı", len(data.get("students", []))),
        ]
        for key, value in summary_rows:
            summary.append([key, value])
        for row in range(2, summary.max_row + 1):
            summary.cell(row=row, column=1).font = SUBTITLE_FONT
        _fit_columns(summary)

        lo_rows = [[x["code"], x["description"], x["target_percent"], x["attainment_percent"], x["status"]] for x in data.get("learning_outcomes", [])]
        _tabular_sheet(wb, "Agirlikli_OC", ["ÖÇ", "Açıklama", "Hedef %", "Ağırlıklı Başarı %", "Durum"], lo_rows)
        po_rows = [[x["code"], x["description"], x["target_percent"], x["attainment_percent"], x["status"]] for x in data.get("program_outcomes", [])]
        _tabular_sheet(wb, "Agirlikli_PC", ["PÇ", "Açıklama", "Hedef %", "Ağırlıklı Başarı %", "Durum"], po_rows)

    for sheet in wb.worksheets:
        sheet.sheet_view.showGridLines = False
    buf = BytesIO()
    localize_workbook(wb)
    wb.save(buf)
    suffix = "OBS-Aktarim" if obs_mode else "Ders-Not-Defteri"
    return buf.getvalue(), f"DOU-Assess-{course.code}-{suffix}.xlsx"
