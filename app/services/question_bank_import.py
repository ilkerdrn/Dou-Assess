from __future__ import annotations

from io import BytesIO
import re
from typing import Any

from openpyxl import load_workbook

from ..security import validate_xlsx_container

from .excel_tr import canonical_header, canonical_value, header_tr, localize

SHEET_NAME = "Soru_Havuzu"
REQUIRED_COLUMNS = [
    "program_code", "course_code", "academic_year", "term",
    "question_type", "question_text", "default_points",
]
OPTIONAL_COLUMNS = [
    "choice_A", "choice_B", "choice_C", "choice_D", "choice_E",
    "correct_answer", "answer_lines", "learning_outcome_codes", "tags",
    "topic", "unit", "difficulty", "bloom_level", "author", "reviewer", "rubric", "expected_answer",
]
ALLOWED_TYPES = {"mcq", "classic"}
ALLOWED_DIFFICULTY = {"easy", "medium", "hard"}
ALLOWED_BLOOM = {"remember", "understand", "apply", "analyze", "evaluate", "create"}


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _split(value: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in re.split(r"[,;|\n]", _text(value)):
        item = raw.strip()
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def parse_rubric(value: Any) -> dict | None:
    raw = _text(value)
    if not raw:
        return None
    criteria = []
    chunks = [x.strip() for x in re.split(r"[;\n]+", raw) if x.strip()]
    for idx, chunk in enumerate(chunks, start=1):
        parts = [x.strip() for x in chunk.split("|")]
        if len(parts) < 2 or not parts[0]:
            raise ValueError("rubric 'Ölçüt | Puan' biçiminde olmalıdır")
        try:
            points = float(parts[1].replace(",", "."))
        except ValueError as exc:
            raise ValueError(f"rubric {idx}. ölçüt puanı sayı olmalıdır") from exc
        outcome_codes = []
        description = ""
        for extra in parts[2:]:
            if extra.upper().startswith("ÖÇ=") or extra.upper().startswith("OC="):
                outcome_codes = _split(extra.split("=", 1)[1])
            elif extra:
                description = extra
        criteria.append({
            "id": f"c{idx}",
            "label": parts[0],
            "max_points": points,
            "description": description,
            "outcome_codes": outcome_codes,
        })
    return {"criteria": criteria}


def parse_question_bank_workbook(data: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        validate_xlsx_container(data)
    except Exception as exc:
        return [], [str(getattr(exc, "detail", None) or exc)]
    try:
        wb = load_workbook(BytesIO(data), read_only=True, data_only=True, keep_links=False)
    except Exception as exc:
        return [], [f"Excel dosyası açılamadı: {exc}"]
    if SHEET_NAME not in wb.sheetnames:
        return [], [f"Eksik sayfa: {SHEET_NAME}"]

    ws = wb[SHEET_NAME]
    values = list(ws.iter_rows(values_only=True))
    if not values:
        return [], [f"{SHEET_NAME} sayfası boş"]
    headers = [canonical_header(x) for x in values[0]]  # Turkish or English column headers
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        return [], ["Eksik sütunlar: " + ", ".join(header_tr(c) for c in missing)]

    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for row_no, values_row in enumerate(values[1:], start=2):
        if all(_text(x) == "" for x in values_row):
            continue
        row = {headers[i]: canonical_value(headers[i], values_row[i] if i < len(values_row) else None) for i in range(len(headers)) if headers[i]}
        row["__row__"] = row_no
        for col in REQUIRED_COLUMNS:
            if not _text(row.get(col)):
                errors.append(f"{SHEET_NAME} satır {row_no}: '{col}' zorunludur")

        qtype = _text(row.get("question_type")).casefold()
        if qtype not in ALLOWED_TYPES:
            errors.append(f"{SHEET_NAME} satır {row_no}: question_type mcq veya classic olmalıdır")
        row["question_type"] = qtype

        try:
            points = float(str(row.get("default_points")).replace(",", "."))
            if not 0 < points <= 100:
                raise ValueError
            row["default_points"] = points
        except Exception:
            errors.append(f"{SHEET_NAME} satır {row_no}: default_points 0-100 arasında sayı olmalıdır")

        difficulty = _text(row.get("difficulty") or "medium").casefold()
        if difficulty not in ALLOWED_DIFFICULTY:
            errors.append(f"{SHEET_NAME} satır {row_no}: difficulty easy, medium veya hard olmalıdır")
        row["difficulty"] = difficulty or "medium"

        bloom = _text(row.get("bloom_level") or "understand").casefold()
        if bloom not in ALLOWED_BLOOM:
            errors.append(f"{SHEET_NAME} satır {row_no}: bloom_level geçersiz")
        row["bloom_level"] = bloom or "understand"

        try:
            answer_lines = int(row.get("answer_lines") or 8)
            if not 1 <= answer_lines <= 40:
                raise ValueError
            row["answer_lines"] = answer_lines
        except Exception:
            errors.append(f"{SHEET_NAME} satır {row_no}: answer_lines 1-40 arasında tam sayı olmalıdır")

        row["learning_outcome_codes"] = _split(row.get("learning_outcome_codes"))
        row["tags"] = _split(row.get("tags"))
        row["choices"] = {letter: _text(row.get(f"choice_{letter}")) for letter in "ABCDE" if _text(row.get(f"choice_{letter}"))}
        row["correct_answer"] = _text(row.get("correct_answer")).upper()
        try:
            row["rubric_obj"] = parse_rubric(row.get("rubric"))
        except ValueError as exc:
            errors.append(f"{SHEET_NAME} satır {row_no}: {exc}")
            row["rubric_obj"] = None

        if qtype == "mcq":
            if len(row["choices"]) < 2:
                errors.append(f"{SHEET_NAME} satır {row_no}: mcq için en az iki seçenek zorunludur")
            if row["correct_answer"] not in row["choices"]:
                errors.append(f"{SHEET_NAME} satır {row_no}: correct_answer dolu seçeneklerden biri olmalıdır")
            if row["rubric_obj"]:
                errors.append(f"{SHEET_NAME} satır {row_no}: rubric yalnız classic sorularda kullanılabilir")
        elif qtype == "classic":
            row["choices"] = None
            row["correct_answer"] = None
            if not _text(row.get("expected_answer")):
                errors.append(f"{SHEET_NAME} satır {row_no}: classic için expected_answer zorunludur")
            if not row["learning_outcome_codes"]:
                errors.append(f"{SHEET_NAME} satır {row_no}: classic için en az bir learning_outcome_codes zorunludur")
            if not row["rubric_obj"]:
                errors.append(f"{SHEET_NAME} satır {row_no}: classic için rubric zorunludur")
            elif abs(sum(float(c.get("max_points") or 0) for c in row["rubric_obj"].get("criteria", [])) - float(row.get("default_points") or 0)) > 0.01:
                errors.append(f"{SHEET_NAME} satır {row_no}: rubric toplamı default_points ile eşit olmalıdır")

        rows.append(row)

    if not rows and not errors:
        errors.append(f"{SHEET_NAME} sayfasında içe aktarılacak soru yok")
    return rows, [localize(e) for e in errors]
