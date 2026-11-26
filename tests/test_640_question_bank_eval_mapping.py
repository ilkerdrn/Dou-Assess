from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_640_question_bank_create_wiring_and_validation():
    js=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
    html=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
    assert 'openNewBankQuestion' in js
    assert "bankFocusCreate" in js
    assert 'Soru havuzuna kaydet' in html
    assert "en az iki seçenek doldurun" in js

def test_640_evaluation_color_semantics():
    js=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
    css=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')
    for token in ['is-student-selected','is-correct-answer','is-wrong-selection']:
        assert token in js and token in css
    assert 'Öğrencinin işareti' in js and 'Doğru cevap' in js and 'Yanlış işaret' in js

def test_640_contribution_scale_is_one_to_five():
    schema=(ROOT/'app/schemas.py').read_text(encoding='utf-8')
    js=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
    html=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
    assert 'contribution: int = Field(ge=1, le=5)' in schema
    assert '[1,2,3,4,5]' in js
    assert '1–5 KATKI MATRİSİ' in html
    assert '0–5 KATKI MATRİSİ' not in html
