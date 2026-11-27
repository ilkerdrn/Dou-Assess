from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import base64
import html
import json
import math
import random

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, A4, A5, landscape, portrait
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

RED = colors.HexColor("#D71920")
DARK = colors.HexColor("#1D1D1F")
LIGHT = colors.HexColor("#F7F7F8")
LINE = colors.HexColor("#444444")

BOOKLETS = {"A", "B", "C", "D"}
TEMPLATE_VERSION = "dou-official-v2"

_FONT_READY = False


_PAGE_SIZES = {"A3": A3, "A4": A4, "A5": A5}


def _page_size(exam) -> tuple[float, float]:
    base = _PAGE_SIZES.get(str(getattr(exam, "paper_size", "A4") or "A4").upper(), A4)
    orientation = str(getattr(exam, "paper_orientation", "portrait") or "portrait").lower()
    return landscape(base) if orientation == "landscape" else portrait(base)


def _begin_logical_page(c: canvas.Canvas, exam) -> None:
    """Fit the established A4 layout safely onto A3/A4/A5 and portrait/landscape pages."""
    actual_w, actual_h = _page_size(exam)
    logical_w, logical_h = A4
    scale = min(actual_w / logical_w, actual_h / logical_h)
    offset_x = max(0.0, (actual_w - logical_w * scale) / 2.0)
    offset_y = max(0.0, (actual_h - logical_h * scale) / 2.0)
    c.translate(offset_x, offset_y)
    c.scale(scale, scale)


def _register_fonts() -> None:
    global _FONT_READY
    if _FONT_READY:
        return
    candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
        ("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Italic.ttf"),
    ]
    for regular, bold, italic in candidates:
        if Path(regular).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont("DOU-Regular", regular))
            pdfmetrics.registerFont(TTFont("DOU-Bold", bold))
            if Path(italic).exists():
                pdfmetrics.registerFont(TTFont("DOU-Italic", italic))
            else:
                pdfmetrics.registerFont(TTFont("DOU-Italic", regular))
            _FONT_READY = True
            return
    raise RuntimeError("PDF için Türkçe karakter destekli font bulunamadı. Docker image içinde fonts-dejavu-core kurulmalıdır.")


def _esc(value: object) -> str:
    return html.escape(str(value or ""))


def normalize_choices(choices: dict | None) -> dict[str, str] | None:
    if not choices:
        return None
    out: dict[str, str] = {}
    for k, v in choices.items():
        key = str(k).strip().upper()
        if key and v is not None and str(v).strip():
            out[key] = str(v).strip()
    return out or None


def normalize_correct_answer(correct_answer: str | None, choices: dict | None) -> str | None:
    if correct_answer is None:
        return None
    raw = str(correct_answer).strip()
    if not raw:
        return None
    normalized = normalize_choices(choices) or {}
    key = raw.upper()
    if key in normalized:
        return key
    for k, v in normalized.items():
        if raw.casefold() == str(v).strip().casefold():
            return k
    return key


def _question_payload(q) -> dict:
    choices = normalize_choices(q.choices)
    outcome_codes = sorted({x.code for x in getattr(q, "learning_outcomes", []) if x}, key=lambda x: x.casefold())
    if not outcome_codes and getattr(q, "learning_outcome", None):
        outcome_codes = [q.learning_outcome.code]
    return {
        "id": q.id,
        "original_order": q.order_no,
        "question_type": q.question_type,
        "text": q.text,
        "points": float(q.points),
        "correct_answer": normalize_correct_answer(q.correct_answer, choices),
        "choices": choices,
        "answer_lines": int(getattr(q, "answer_lines", 8) or 8),
        "learning_outcome_code": outcome_codes[0] if outcome_codes else None,
        "learning_outcome_codes": outcome_codes,
        "topic": getattr(q, "topic", "") or "",
        "unit": getattr(q, "unit", "") or "",
        "difficulty": getattr(q, "difficulty", "medium") or "medium",
        "bloom_level": getattr(q, "bloom_level", "") or "",
        "image_data": getattr(q, "image_data", None),
        "rubric": getattr(q, "rubric", None) or {},
    }


def ordered_questions(exam, booklet: str) -> list[dict]:
    booklet = booklet.upper()
    if booklet not in BOOKLETS:
        raise ValueError("Kitapçık A, B, C veya D olmalıdır")
    rows = [_question_payload(q) for q in sorted(exam.questions, key=lambda x: x.order_no)]
    if booklet != "A":
        mcq_positions = [i for i, q in enumerate(rows) if q["question_type"] == "mcq"]
        mcqs = [rows[i] for i in mcq_positions]
        original_ids = [q["id"] for q in mcqs]
        rnd = random.Random(f"DOU-ASSESS:{exam.id}:{booklet}:{TEMPLATE_VERSION}")
        rnd.shuffle(mcqs)
        # With a very small MCQ set a deterministic shuffle can occasionally be
        # identical to booklet A. Force a stable rotation so every non-A booklet
        # is actually distinguishable whenever at least two MCQs exist.
        if len(mcqs) > 1 and [q["id"] for q in mcqs] == original_ids:
            shift = {"B": 1, "C": 2, "D": 3}.get(booklet, 1) % len(mcqs)
            shift = shift or 1
            mcqs = mcqs[shift:] + mcqs[:shift]
        for pos, q in zip(mcq_positions, mcqs):
            rows[pos] = q
    for i, q in enumerate(rows, start=1):
        q["display_no"] = i
    return rows


def _omr_normalized_layout(rows: list[dict]) -> dict:
    mcqs = [q for q in rows if q["question_type"] == "mcq"]
    n = len(mcqs)
    cols = 2 if n <= 20 else 3 if n <= 30 else 4
    rows_per_col = max(1, math.ceil(n / cols)) if n else 1
    bubbles = []
    letters = ["A", "B", "C", "D", "E"]
    for idx, q in enumerate(mcqs):
        col = idx // rows_per_col
        row = idx % rows_per_col
        col_w = 0.92 / cols
        col_left = 0.04 + col * col_w
        y = 0.30 if rows_per_col == 1 else 0.30 + row * (0.62 / (rows_per_col - 1))
        n_choices = len(q.get("choices") or {}) or 5  # bubbles follow the question's real choice count (2..5)
        for j, letter in enumerate(letters[:max(2, min(5, n_choices))]):
            x = col_left + col_w * (0.27 + j * 0.125)
            bubbles.append({
                "display_no": q["display_no"], "question_id": q["id"],
                "letter": letter, "x": round(x, 6), "y": round(y, 6),
            })
    return {"columns": cols if n else 0, "rows_per_column": rows_per_col if n else 0, "bubbles": bubbles}


def paper_metadata(exam, booklet: str = "A", student=None) -> dict:
    booklet = booklet.upper()
    rows = ordered_questions(exam, booklet)
    order_ids = [q["id"] for q in rows]
    token_source = json.dumps({"exam": exam.id, "booklet": booklet, "order": order_ids, "template": TEMPLATE_VERSION}, sort_keys=True).encode("utf-8")
    token = sha256(token_source).hexdigest()[:20]
    answer_key = {str(q["display_no"]): q["correct_answer"] for q in rows if q["question_type"] == "mcq"}
    student_no = getattr(student, "student_no", None) if student is not None else None
    qr_payload = f"DOUASSESS|v2|exam={exam.id}|booklet={booklet}|token={token}|student={student_no or '-'}"
    return {
        "exam_id": exam.id,
        "booklet": booklet,
        "template_version": getattr(exam, "paper_template_version", None) or TEMPLATE_VERSION,
        "token": token,
        "qr_payload": qr_payload,
        "question_order": [
            {
                "display_no": q["display_no"],
                "question_id": q["id"],
                "original_order": q["original_order"],
                "question_type": q["question_type"],
                "points": q["points"],
                "learning_outcome_code": q["learning_outcome_code"],
                "learning_outcome_codes": q.get("learning_outcome_codes", []),
            }
            for q in rows
        ],
        "answer_key": answer_key,
        "omr_layout": _omr_normalized_layout(rows),
        "student": {"id": getattr(student, "id", None), "student_no": student_no, "full_name": getattr(student, "full_name", None)} if student is not None else None,
        "schedule": {
            "date": exam.exam_date.isoformat() if getattr(exam, "exam_date", None) else None,
            "start_time": getattr(exam, "start_time", None),
            "location": getattr(exam, "location", "") or "",
            "duration_minutes": getattr(exam, "duration_minutes", None),
            "assessment_weight_percent": getattr(exam, "assessment_weight_percent", None),
            "booklet_count": getattr(exam, "booklet_count", 4) or 4,
        },
        "paper": {
            "size": str(getattr(exam, "paper_size", "A4") or "A4").upper(),
            "orientation": str(getattr(exam, "paper_orientation", "portrait") or "portrait"),
            "omr_mode": str(getattr(exam, "omr_mode", "embedded") or "embedded"),
            "duplex_print": bool(getattr(exam, "duplex_print", False)),
            "page_size_points": list(_page_size(exam)),
        },
        "snapshot": {
            "course_code": getattr(exam, "course_code_snapshot", None),
            "course_name": getattr(exam, "course_name_snapshot", None),
            "academic_year": getattr(exam, "academic_year_snapshot", None),
            "term": getattr(exam, "term_snapshot", None),
            "instructor": getattr(exam, "instructor_snapshot", None),
            "program_name": getattr(exam, "program_name_snapshot", None),
            "department": getattr(exam, "department_snapshot", None),
            "faculty": getattr(exam, "faculty_snapshot", None),
        },
    }


def _paragraph(c: canvas.Canvas, text: str, x: float, y_top: float, width: float, style: ParagraphStyle) -> float:
    p = Paragraph(text, style)
    _, h = p.wrap(width, 1000)
    p.drawOn(c, x, y_top - h)
    return h


def _draw_logo(c: canvas.Canvas, x: float, y: float, size: float) -> None:
    logo = Path(__file__).resolve().parents[1] / "static" / "dou-logo.png"
    if logo.exists():
        c.drawImage(ImageReader(str(logo)), x, y, size, size, preserveAspectRatio=True, mask="auto")


def _faculty_title(value: str | None) -> str:
    raw = (value or "").strip()
    low = raw.casefold()
    if raw and ("meslek yüksek" in low or low in {"myo", "meslek yüksekokulu"}):
        return "DOĞUŞ ÜNİVERSİTESİ MESLEK YÜKSEKOKULU"
    if raw:
        return raw.upper()
    return "DOĞUŞ ÜNİVERSİTESİ"


def _term_title(term: str | None) -> str:
    t = (term or "").strip().casefold()
    if "güz" in t or "fall" in t:
        return "GÜZ DÖNEMİ / FALL SEMESTER"
    if "bahar" in t or "spring" in t:
        return "BAHAR DÖNEMİ / SPRING SEMESTER"
    if "yaz" in t or "summer" in t:
        return "YAZ DÖNEMİ / SUMMER SEMESTER"
    return f"{(term or 'DÖNEM').upper()} / SEMESTER"


def _exam_heading(exam_type: str | None) -> str:
    raw = (exam_type or "Sınav").strip()
    low = raw.casefold()
    if "final" in low:
        return "FİNAL SINAVI / FINAL EXAM"
    if "vize" in low or "midterm" in low:
        return "VİZE SINAVI / MIDTERM EXAM"
    if "bütün" in low or "butun" in low or "make-up" in low or "makeup" in low:
        return "BÜTÜNLEME SINAVI / MAKE-UP EXAM"
    if "tek ders" in low:
        return "TEK DERS SINAVI / SINGLE COURSE EXAM"
    if "quiz" in low or "kısa" in low or "kisa" in low:
        return "KISA SINAV / QUIZ"
    return f"{raw.upper()} SINAVI / EXAM"


def _paper_type(rows: list[dict]) -> str:
    types = {q["question_type"] for q in rows}
    if types == {"mcq", "classic"}:
        return "Çoktan seçmeli ve klasik / Multiple choice and classic"
    if types == {"mcq"}:
        return "Çoktan seçmeli / Multiple choice"
    if types == {"classic"}:
        return "Klasik / Open-ended"
    return "Sınav / Exam"


def _default_rules(rows: list[dict]) -> str:
    mcq = [q for q in rows if q["question_type"] == "mcq"]
    classic = [q for q in rows if q["question_type"] == "classic"]
    tr = f"Bu sınav toplam {len(rows)} sorudan oluşmaktadır; {len(mcq)} çoktan seçmeli (test), {len(classic)} klasik (açık uçlu) soru bulunmaktadır. Çoktan seçmeli soruların cevapları ön sayfadaki cevap formuna işaretlenmelidir. Açık uçlu cevaplar ilgili soru altında ayrılan alana yazılmalıdır. Cevap formunda her soru için yalnızca bir şıkkın balonunu koyu renkli kalemle tamamen doldurun; silinti, çift işaret veya balon dışına taşan işaretler geçersiz sayılabilir."
    en = f"This exam consists of {len(rows)} questions: {len(mcq)} multiple-choice and {len(classic)} open-ended questions. Multiple-choice answers must be marked on the answer area on the front page. Open-ended answers must be written in the space provided under the relevant question. On the answer sheet, fill in exactly one bubble per question completely with a dark pen; erasures, double marks or marks outside the bubble may be invalid."
    return tr + " " + en


def _draw_first_page(c: canvas.Canvas, exam, rows: list[dict], metadata: dict) -> None:
    _begin_logical_page(c, exam)
    w, h = A4
    margin = 30
    c.setStrokeColor(LINE)
    c.setFillColor(DARK)

    _draw_logo(c, 105, h - 91, 54)
    c.setFont("DOU-Bold", 22)
    c.drawCentredString(w / 2 + 45, h - 60, "DOĞUŞ ÜNİVERSİTESİ")

    top = h - 112
    box_x, box_w = margin, w - 2 * margin
    header_h = 78
    c.rect(box_x, top - header_h, box_w, header_h)
    c.setFont("DOU-Bold", 13)
    c.drawCentredString(w / 2, top - 22, _faculty_title(getattr(exam, "faculty_snapshot", None)))
    c.setFont("DOU-Bold", 11)
    c.drawCentredString(w / 2, top - 42, f"{getattr(exam, 'academic_year_snapshot', None) or ''} EĞİTİM - ÖĞRETİM YILI / ACADEMIC YEAR")
    c.drawCentredString(w / 2, top - 61, f"{_term_title(getattr(exam, 'term_snapshot', None))}  {_exam_heading(exam.exam_type)}")

    y = top - header_h
    student_h = 88
    score_w = 165
    c.rect(box_x, y - student_h, box_w - score_w, student_h)
    c.rect(box_x + box_w - score_w, y - student_h, score_w, student_h)
    c.setFont("DOU-Bold", 9)
    c.drawString(box_x + 7, y - 15, "Öğrencinin / Student's")
    c.setFont("DOU-Regular", 9)
    student = metadata.get("student") or {}
    student_values = [student.get("full_name") or "", student.get("student_no") or "", getattr(exam, "program_name_snapshot", None) or "", ""]
    for i, label in enumerate(["Adı Soyadı / Name, Surname :", "Numarası / Number :", "Bölüm - Program / Department-Programme :", "İmzası / Signature :"]):
        c.drawString(box_x + 7, y - 32 - i * 14, label + (" " + str(student_values[i]) if student_values[i] else ""))
    score_style = ParagraphStyle("scorehead", fontName="DOU-Bold", fontSize=7.1, leading=8.2, alignment=TA_LEFT)
    _paragraph(c, "Toplam Not - Paraf / Total Credit - Initials", box_x + box_w - score_w + 6, y - 8, score_w - 12, score_style)

    y -= student_h + 5
    table_h = 92
    left_label_w = 43
    middle_w = box_w * 0.58
    right_label_w = 45
    right_x = box_x + left_label_w + middle_w
    detail_x = right_x + right_label_w
    right_detail_w = box_x + box_w - detail_x
    c.rect(box_x, y - table_h, box_w, table_h)
    c.line(box_x + left_label_w, y, box_x + left_label_w, y - table_h)
    c.line(right_x, y, right_x, y - table_h)
    c.line(detail_x, y, detail_x, y - table_h)
    c.setFont("DOU-Bold", 11)
    c.drawCentredString(box_x + left_label_w / 2, y - 39, "DERS")
    c.setFont("DOU-Italic", 8)
    c.drawCentredString(box_x + left_label_w / 2, y - 52, "Course")
    c.setFont("DOU-Bold", 10.5)
    c.drawCentredString(right_x + right_label_w / 2, y - 39, "SINAV")
    c.setFont("DOU-Italic", 8)
    c.drawCentredString(right_x + right_label_w / 2, y - 52, "Exam")
    # inner horizontal separators - DERS/SINAV label columns remain merged vertically.
    for yy in [y - 31, y - 60]:
        c.line(box_x + left_label_w, yy, right_x, yy)
        c.line(detail_x, yy, box_x + box_w, yy)
    c.setFont("DOU-Bold", 8.2)
    c.drawString(box_x + left_label_w + 5, y - 18, "Adı / Name")
    c.drawString(box_x + left_label_w + 5, y - 48, "Kodu / Code")
    c.drawString(box_x + left_label_w + 5, y - 77, "Sorumlusu / Lecturer")
    c.setFont("DOU-Regular", 8.2)
    c.drawString(box_x + left_label_w + 118, y - 18, f": {getattr(exam, 'course_name_snapshot', None) or ''}")
    c.drawString(box_x + left_label_w + 118, y - 48, f": {getattr(exam, 'course_code_snapshot', None) or ''}")
    instructor_style = ParagraphStyle("instructor", fontName="DOU-Regular", fontSize=7.8, leading=8.5)
    _paragraph(c, ": " + _esc(getattr(exam, 'instructor_snapshot', None) or ''), box_x + left_label_w + 118, y - 66, max(80, right_x - (box_x + left_label_w + 118) - 4), instructor_style)
    detail_w = right_detail_w - 10
    date_txt = exam.exam_date.strftime("%d.%m.%Y") if exam.exam_date else "-"
    time_txt = getattr(exam, "start_time", None) or "-"
    location_txt = getattr(exam, "location", None) or "-"
    date_style = ParagraphStyle("date-detail", fontName="DOU-Regular", fontSize=7.2, leading=8.0)
    duration_style = ParagraphStyle("duration", fontName="DOU-Regular", fontSize=6.9, leading=7.6)
    type_style = ParagraphStyle("type", fontName="DOU-Regular", fontSize=6.5, leading=7.0)
    _paragraph(c, f"<b>Tarih / Date:</b> {_esc(date_txt)} · <b>Saat:</b> {_esc(time_txt)}", detail_x + 5, y - 7, detail_w, date_style)
    _paragraph(c, f"<b>Süre / Duration:</b> {exam.duration_minutes} dk · <b>Salon:</b> {_esc(location_txt)}", detail_x + 5, y - 36, detail_w, duration_style)
    _paragraph(c, "<b>Türü / Type:</b> " + _esc(_paper_type(rows)), detail_x + 5, y - 64, detail_w, type_style)

    y -= table_h + 5
    rules = (exam.instructions or "").strip() or _default_rules(rows)
    rule_style = ParagraphStyle("rules", fontName="DOU-Regular", fontSize=7.3, leading=8.5, alignment=TA_LEFT)
    label_style = ParagraphStyle("rulelabel", fontName="DOU-Bold", fontSize=7.5, leading=8.5)
    p = Paragraph("<b>SINAV KURALLARI / Exam Rules:</b> " + _esc(rules), rule_style)
    _, rules_h = p.wrap(box_w - 10, 1000)
    rules_h = max(43, min(rules_h + 10, 72))
    c.rect(box_x, y - rules_h, box_w, rules_h)
    p.drawOn(c, box_x + 5, y - rules_h + 5)
    y -= rules_h + 5

    # Score grid, max 20 questions per band.
    all_nums = [q["display_no"] for q in rows]
    bands = [all_nums[i:i+20] for i in range(0, len(all_nums), 20)] or [[]]
    for band in bands[:2]:
        row_h = 22
        label_w = 143
        c.rect(box_x, y - row_h * 2, box_w, row_h * 2)
        c.line(box_x + label_w, y, box_x + label_w, y - row_h * 2)
        c.line(box_x, y - row_h, box_x + box_w, y - row_h)
        c.setFont("DOU-Bold", 8.5)
        c.drawString(box_x + 5, y - 14, "Soru Numarası / Question No")
        c.drawString(box_x + 5, y - row_h - 14, "Alınan Not / Scored Points")
        if band:
            cell = (box_w - label_w) / len(band)
            for i, no in enumerate(band):
                x = box_x + label_w + i * cell
                if i:
                    c.line(x, y, x, y - row_h * 2)
                c.setFont("DOU-Regular", 7.2)
                c.drawCentredString(x + cell / 2, y - 14, str(no))
        y -= row_h * 2 + 4

    # OMR can be embedded on the cover or emitted as a dedicated page.
    omr_top = y - 3
    omr_bottom = 34
    omr_h = max(145, omr_top - omr_bottom)
    if str(getattr(exam, "omr_mode", "embedded") or "embedded") == "separate":
        c.setStrokeColor(RED); c.setLineWidth(1.2)
        c.roundRect(box_x + 20, omr_bottom, box_w - 40, omr_h, 10, stroke=1, fill=0)
        c.setFillColor(DARK); c.setFont("DOU-Bold", 12)
        c.drawCentredString(w / 2, omr_bottom + omr_h / 2 + 8, "CEVAP FORMU AYRI SAYFADADIR")
        c.setFont("DOU-Regular", 8.5)
        c.drawCentredString(w / 2, omr_bottom + omr_h / 2 - 10, "Answer sheet is provided on a separate page")
    else:
        _draw_omr_panel(c, exam, rows, metadata, box_x + 20, box_w - 40, omr_top, omr_bottom, metadata.get("student") or {})
    c.setFillColor(DARK); c.setFont("DOU-Regular", 6.5)
    c.drawRightString(w - margin, 17, f"DOU Assess · {metadata['template_version']} · {metadata['token']}")


def _qr_image_reader(payload: str) -> ImageReader:
    qr = qrcode.QRCode(version=2, box_size=3, border=1)
    qr.add_data(payload); qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buf = BytesIO(); qr_img.save(qr_buf, format="PNG"); qr_buf.seek(0)
    return ImageReader(qr_buf)


def _page_identity_payload(metadata: dict, page_no: int, role: str = "questions") -> str:
    student = metadata.get("student") or {}
    return (
        f"DOUASSESS|v3|exam={metadata['exam_id']}|booklet={metadata['booklet']}|token={metadata['token']}"
        f"|student={student.get('student_no') or '-'}|role={role}|page={int(page_no)}"
    )


def _draw_page_identity_qr(c: canvas.Canvas, metadata: dict, page_no: int, role: str = "questions") -> None:
    # Compact page-level QR makes every scanned question page independently
    # attributable to the exam/student even when pages are shuffled by an ADF.
    c.drawImage(_qr_image_reader(_page_identity_payload(metadata, page_no, role)), A4[0] - 82, A4[1] - 94, 48, 48, mask="auto")


def _draw_omr_panel(c: canvas.Canvas, exam, rows: list[dict], metadata: dict, panel_x: float, panel_w: float, omr_top: float, omr_bottom: float, student: dict) -> None:
    omr_h = max(145, omr_top - omr_bottom)
    c.setLineWidth(1.2); c.setStrokeColor(RED)
    c.roundRect(panel_x, omr_bottom, panel_w, omr_h, 10, stroke=1, fill=0)
    c.setStrokeColor(LINE); c.setFillColor(DARK)
    c.setFont("DOU-Bold", 11); c.drawString(panel_x + 25, omr_top - 29, "CEVAP FORMU / ANSWER SHEET")
    c.setFont("DOU-Regular", 7.2)
    c.drawString(panel_x + 25, omr_top - 43, f"Kitapçık / Booklet: {metadata['booklet']}    Sınav ID: {exam.id}")
    c.drawString(panel_x + 25, omr_top - 56, f"Öğrenci No / Student No: {student.get('student_no') or '____________________'}")

    c.drawImage(_qr_image_reader(metadata["qr_payload"]), panel_x + panel_w - 71, omr_top - 76, 48, 48, mask="auto")

    marker_left = panel_x + 8; marker_right = panel_x + panel_w - 8
    marker_bottom = omr_bottom + 9; marker_top = omr_top - 9; marker_size = 10
    for cx, cy in [(marker_left, marker_bottom), (marker_right, marker_bottom), (marker_left, marker_top), (marker_right, marker_top)]:
        c.setFillColor(colors.black); c.rect(cx - marker_size/2, cy - marker_size/2, marker_size, marker_size, stroke=0, fill=1)
    c.setFillColor(DARK)
    mcqs = [q for q in rows if q["question_type"] == "mcq"]
    if mcqs:
        layout = metadata["omr_layout"]; seen = set(); c.setFont("DOU-Bold", 7)
        for b in layout["bubbles"]:
            x = marker_left + b["x"] * (marker_right - marker_left)
            yy = marker_top - b["y"] * (marker_top - marker_bottom)
            key = b["display_no"]
            if key not in seen:
                c.setFillColor(RED); c.drawRightString(x - 10, yy - 2, str(key)); seen.add(key)
            c.setFillColor(DARK); c.circle(x, yy, 4.8, stroke=1, fill=0)
            c.setFont("DOU-Regular", 5.5); c.drawCentredString(x, yy - 1.7, b["letter"])
    else:
        c.setFont("DOU-Regular", 9); c.drawCentredString(A4[0] / 2, omr_bottom + omr_h / 2, "Bu sınavda çoktan seçmeli soru bulunmamaktadır.")


def _draw_separate_omr_page(c: canvas.Canvas, exam, rows: list[dict], metadata: dict, page_no: int) -> None:
    _begin_logical_page(c, exam)
    w, h = A4
    c.setFillColor(DARK); c.setFont("DOU-Bold", 10)
    c.drawString(32, h - 31, "DOĞUŞ ÜNİVERSİTESİ · AYRI CEVAP FORMU")
    c.setFont("DOU-Regular", 7.5)
    c.drawRightString(w - 32, h - 31, f"{getattr(exam,'course_code_snapshot',None) or ''} · Kitapçık {metadata['booklet']}")
    c.line(32, h - 38, w - 32, h - 38)
    _draw_omr_panel(c, exam, rows, metadata, 45, w - 90, h - 70, 55, metadata.get("student") or {})
    c.setFont("DOU-Regular", 6.5); c.drawCentredString(w / 2, 17, f"Sayfa / Page {page_no} · Sınav ID {exam.id} · {metadata['token']}")


def _new_question_page(c: canvas.Canvas, exam, metadata: dict, page_no: int) -> float:
    _begin_logical_page(c, exam)
    w, h = A4
    c.setStrokeColor(colors.HexColor("#D9DDE2")); c.setFillColor(DARK)
    c.setFont("DOU-Bold", 9)
    c.drawString(32, h - 31, "DOĞUŞ ÜNİVERSİTESİ")
    c.setFont("DOU-Regular", 7.5)
    c.drawRightString(w - 32, h - 31, f"{getattr(exam,'course_code_snapshot',None) or ''} · {exam.exam_type} · Kitapçık {metadata['booklet']}")
    c.line(32, h - 38, w - 32, h - 38)
    _draw_page_identity_qr(c, metadata, page_no, "questions")
    c.setFont("DOU-Bold", 6.2); c.drawRightString(w - 88, h - 61, "SCAN PAGE ID")
    c.setFont("DOU-Regular", 6.5)
    c.drawCentredString(w / 2, 17, f"Sayfa / Page {page_no} · Sınav ID {exam.id} · {metadata['token']}")
    return h - 105


def _question_image_reader(image_data: str | None):
    if not image_data or not str(image_data).startswith("data:image/") or "," not in str(image_data):
        return None
    try:
        raw = base64.b64decode(str(image_data).split(",", 1)[1], validate=True)
        return ImageReader(BytesIO(raw))
    except Exception:
        return None


def _logical_rect_normalized(exam, x1: float, y1: float, x2: float, y2: float) -> list[float]:
    actual_w, actual_h = _page_size(exam)
    logical_w, logical_h = A4
    scale = min(actual_w / logical_w, actual_h / logical_h)
    offset_x = max(0.0, (actual_w - logical_w * scale) / 2.0)
    offset_y = max(0.0, (actual_h - logical_h * scale) / 2.0)
    ax1, ax2 = offset_x + x1 * scale, offset_x + x2 * scale
    ay1, ay2 = offset_y + y1 * scale, offset_y + y2 * scale
    # Image coordinates are top-left based.
    return [
        round(max(0.0, min(1.0, ax1 / actual_w)), 6),
        round(max(0.0, min(1.0, (actual_h - ay2) / actual_h)), 6),
        round(max(0.0, min(1.0, ax2 / actual_w)), 6),
        round(max(0.0, min(1.0, (actual_h - ay1) / actual_h)), 6),
    ]


def question_regions(exam, booklet: str = "A", legacy_layout: bool = False) -> dict[int, dict]:
    """Deterministically reproduce paper layout and return classic-answer crop hints.

    The same ReportLab measurements used by the PDF renderer are reused here so
    scan-time grading can crop the handwritten answer without OCR.
    """
    _register_fonts()
    rows = ordered_questions(exam, booklet)
    w, h = A4
    x, width = 38, w - 76
    q_style = ParagraphStyle("q-region", fontName="DOU-Regular", fontSize=9.3, leading=12, spaceAfter=0)
    choice_style = ParagraphStyle("choice-region", fontName="DOU-Regular", fontSize=8.7, leading=11)
    page_no = 2 + (1 if str(getattr(exam, "omr_mode", "embedded") or "embedded") == "separate" else 0)
    y = h - (55 if legacy_layout else 105)
    out: dict[int, dict] = {}
    for q in rows:
        title_html = f"<b>{q['display_no']}.</b> {_esc(q['text'])} <b>({q['points']:g} Puan / Points)</b>"
        p = Paragraph(title_html, q_style); _, qh = p.wrap(width, 1000)
        choices = q.get("choices") or {}
        image_reader = _question_image_reader(q.get("image_data"))
        image_h = 0.0
        if image_reader:
            try:
                iw, ih = image_reader.getSize(); max_w, max_h = width - 26, 125
                image_h = float(ih) * min(max_w / max(float(iw), 1.0), max_h / max(float(ih), 1.0), 1.0)
            except Exception:
                image_h = 0.0
        choice_heights = []
        if q["question_type"] == "mcq":
            for key in ["A", "B", "C", "D", "E"]:
                if key in choices:
                    cp = Paragraph(f"<b>{key})</b> {_esc(choices[key])}", choice_style); _, ch = cp.wrap(width - 18, 1000); choice_heights.append(ch)
        needed = qh + 16 + (145 if image_reader else 0)
        if q["question_type"] == "mcq":
            needed += max(30, len(choices) * 13)
        else:
            needed += q["answer_lines"] * 14 + 10
        if y - needed < 38:
            page_no += 1; y = h - (55 if legacy_layout else 105)
        question_top = y
        y -= qh + 8
        if image_h:
            y -= image_h + 10
        answer_top = None; answer_bottom = None
        if q["question_type"] == "mcq":
            for ch in choice_heights:
                y -= ch + 3
            y -= 8
        else:
            answer_top = y
            y -= q["answer_lines"] * 14
            answer_bottom = y
            y -= 8
        region = {
            "question_id": q["id"], "display_no": q["display_no"], "page_no": page_no,
            "question_type": q["question_type"],
            "question_crop": _logical_rect_normalized(exam, x - 5, y - 3, x + width + 5, question_top + 4),
        }
        if answer_top is not None and answer_bottom is not None:
            region["answer_crop"] = _logical_rect_normalized(exam, x + 3, answer_bottom - 5, x + width - 3, answer_top + 5)
        out[int(q["id"])] = region
    return out


def _draw_question(c: canvas.Canvas, exam, q: dict, y: float, metadata: dict, page_no: int) -> tuple[float, int]:
    w, h = A4
    x = 38
    width = w - 76
    q_style = ParagraphStyle("q", fontName="DOU-Regular", fontSize=9.3, leading=12, spaceAfter=0)
    choice_style = ParagraphStyle("choice", fontName="DOU-Regular", fontSize=8.7, leading=11)
    title_html = f"<b>{q['display_no']}.</b> {_esc(q['text'])} <b>({q['points']:g} Puan / Points)</b>"
    p = Paragraph(title_html, q_style)
    _, qh = p.wrap(width, 1000)
    choices = q.get("choices") or {}
    image_reader = _question_image_reader(q.get("image_data"))
    needed = qh + 16 + (145 if image_reader else 0)
    if q["question_type"] == "mcq":
        needed += max(30, len(choices) * 13)
    else:
        needed += q["answer_lines"] * 14 + 10
    if y - needed < 38:
        c.showPage(); page_no += 1; y = _new_question_page(c, exam, metadata, page_no)
    p.drawOn(c, x, y - qh); y -= qh + 8
    if image_reader:
        try:
            iw, ih = image_reader.getSize()
            max_w, max_h = width - 26, 125
            scale = min(max_w / max(float(iw), 1.0), max_h / max(float(ih), 1.0), 1.0)
            dw, dh = float(iw) * scale, float(ih) * scale
            c.drawImage(image_reader, x + (width - dw) / 2, y - dh, dw, dh, preserveAspectRatio=True, mask="auto")
            y -= dh + 10
        except Exception:
            pass
    if q["question_type"] == "mcq":
        for key in ["A", "B", "C", "D", "E"]:
            if key not in choices:
                continue
            cp = Paragraph(f"<b>{key})</b> {_esc(choices[key])}", choice_style)
            _, ch = cp.wrap(width - 18, 1000)
            cp.drawOn(c, x + 13, y - ch)
            y -= ch + 3
        y -= 8
    else:
        c.setStrokeColor(colors.HexColor("#C8CDD3"))
        for _ in range(q["answer_lines"]):
            c.line(x + 8, y, x + width - 8, y)
            y -= 14
        c.setStrokeColor(LINE)
        y -= 8
    return y, page_no


def build_exam_pdf(exam, booklet: str = "A", student=None) -> tuple[bytes, dict]:
    _register_fonts()
    metadata = paper_metadata(exam, booklet, student=student)
    rows = ordered_questions(exam, booklet)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=_page_size(exam), pageCompression=1)
    c.setTitle(f"DOU Assess - {getattr(exam,'course_code_snapshot',None) or ''} - {exam.title} - {booklet}")
    c.setAuthor("DOU Assess")
    c.setSubject("Doğuş Üniversitesi sınav kağıdı")
    _draw_first_page(c, exam, rows, metadata)
    c.showPage()
    page_no = 2
    if str(getattr(exam, "omr_mode", "embedded") or "embedded") == "separate":
        _draw_separate_omr_page(c, exam, rows, metadata, page_no)
        c.showPage(); page_no += 1
    y = _new_question_page(c, exam, metadata, page_no)
    for q in rows:
        y, page_no = _draw_question(c, exam, q, y, metadata, page_no)
    metadata["duplex_padding_added"] = False
    if bool(getattr(exam, "duplex_print", False)) and c.getPageNumber() % 2 == 1:
        c.showPage(); _begin_logical_page(c, exam)
        c.setFillColor(colors.HexColor("#777777")); c.setFont("DOU-Regular", 7)
        c.drawCentredString(A4[0] / 2, A4[1] / 2, "Çift taraflı baskı düzeni için bilinçli olarak boş bırakılmıştır.")
        metadata["duplex_padding_added"] = True
    c.save()
    data = buf.getvalue()
    metadata["pdf_sha256"] = sha256(data).hexdigest()
    metadata["pdf_size_bytes"] = len(data)
    return data, metadata


def build_attendance_sheet_pdf(exam, rows: list[dict]) -> bytes:
    """Yoklama / imza listesi: one line per student with assigned booklet and a signature cell."""
    from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle
    _register_fonts()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36, title="Yoklama / İmza Listesi")
    head = ParagraphStyle("h", fontName="DOU-Bold", fontSize=13, leading=17)
    small = ParagraphStyle("s", fontName="DOU-Regular", fontSize=9, leading=12)
    cell = ParagraphStyle("c", fontName="DOU-Regular", fontSize=9, leading=11)
    date = exam.exam_date.strftime("%d.%m.%Y") if getattr(exam, "exam_date", None) else "—"
    story = [Paragraph(f"{_esc(exam.course_code_snapshot or '')} {_esc(exam.course_name_snapshot or '')} — {_esc(exam.title)}", head),
             Paragraph(f"Yoklama / İmza Listesi · Tarih: {date} · Salon: {_esc(exam.location or '—')} · Süre: {exam.duration_minutes} dk · Öğrenci: {len(rows)}", small), Spacer(1, 10)]
    data = [["#", "Öğrenci No", "Ad Soyad", "Kitapçık", "İmza"]] + [[str(i), r["student_no"], Paragraph(_esc(r["full_name"]), cell), r["booklet"], ""] for i, r in enumerate(rows, 1)]
    t = Table(data, colWidths=[24, 78, 190, 50, 170], repeatRows=1, rowHeights=[20] + [24] * len(rows))
    t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "DOU-Regular"), ("FONTNAME", (0, 0), (-1, 0), "DOU-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
                           ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efece4")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [t, Spacer(1, 14), Paragraph("Gözetmen: ______________________   İmza: ______________________   Teslim alınan kâğıt sayısı: ______", small)]
    doc.build(story)
    return buf.getvalue()
