"""One-off maintenance script: rewrites app/static/examples/*.xlsx with Turkish column headers, Turkish enum values,
Turkish dropdown lists and Turkish guidance text. Importers accept both Turkish and the older English headers.
Run:  python tools/localize_example_workbooks.py
"""
from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.excel_tr import ENUM_BY_FIELD, HEADER_TR, header_tr, value_tr  # noqa: E402

warnings.filterwarnings("ignore")
GUIDE_SHEETS = {"README", "Kullanim"}
LIST_MAP = {
    '"mcq,classic"': '"Çoktan Seçmeli,Klasik"',
    '"easy,medium,hard"': '"Kolay,Orta,Zor"',
    '"remember,understand,apply,analyze,evaluate,create"': '"Hatırlama,Anlama,Uygulama,Analiz,Değerlendirme,Yaratma"',
    '"draft"': '"Taslak"',
}
WORDS = {"mcq": "Çoktan Seçmeli", "classic": "Klasik", "warning ile": "uyarı ile", "tüm import": "tüm içe aktarma", "Import": "İçe aktarma"}
KEY_RX = re.compile(r"\b(" + "|".join(sorted(map(re.escape, HEADER_TR), key=len, reverse=True)) + r")\b")


def localize_text(text: str) -> str:
    text = KEY_RX.sub(lambda m: header_tr(m.group(1)), text)
    for a, b in WORDS.items():
        text = re.sub(rf"\b{re.escape(a)}\b" if a.isalpha() else re.escape(a), b, text)
    return text


def convert(path: Path) -> None:
    wb = openpyxl.load_workbook(path)
    for ws in wb:
        if ws.title in GUIDE_SHEETS:
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str):
                        c.value = localize_text(c.value)
            continue
        keys = [c.value for c in ws[1]]
        if not any(k in HEADER_TR for k in keys):
            continue
        for col, key in enumerate(keys, 1):
            if key in HEADER_TR:
                ws.cell(row=1, column=col).value = header_tr(key)
                if key in ENUM_BY_FIELD:
                    for r in range(2, ws.max_row + 1):
                        cell = ws.cell(row=r, column=col)
                        cell.value = value_tr(key, cell.value)
                width = ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width or 10
                ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = max(width, min(34, len(header_tr(key)) + 4))
        if ws.data_validations:
            for dv in ws.data_validations.dataValidation:
                if dv.formula1 in LIST_MAP:
                    dv.formula1 = LIST_MAP[dv.formula1]
    wb.save(path)
    print("converted", path.name)


if __name__ == "__main__":
    for f in sorted((ROOT / "app/static/examples").glob("*.xlsx")):
        convert(f)
