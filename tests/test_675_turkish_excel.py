import io, re
from openpyxl import Workbook, load_workbook
from app.services.excel_tr import canonical_header, header_tr, localize, canonical_value
from app.services.excel_center import TEMPLATES, template_bytes


def test_headers_roundtrip():
    for key in ("program_code", "student_no", "outcome_code", "choice_A", "target_percent"):
        assert canonical_header(header_tr(key)) == key
        assert canonical_header(key) == key


def test_templates_have_no_snake_case_headers():
    for kind in TEMPLATES:
        wb = load_workbook(io.BytesIO(template_bytes(kind)))
        for ws in wb.worksheets:
            for c in ws[1]:
                assert not re.fullmatch(r"[a-z]+(_[a-z0-9A-Z]+)+", str(c.value or "")), (kind, c.value)


def test_values_and_errors_turkish():
    assert canonical_value("question_type", "Çoktan Seçmeli") == "mcq"
    assert "mcq" not in localize("question_type mcq veya classic")
