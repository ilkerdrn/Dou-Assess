from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/"app/static/app.js").read_text(encoding="utf-8")
HTML=(ROOT/"app/static/index.html").read_text(encoding="utf-8")


def test_question_bank_create_is_owned_by_main_runtime():
    assert "window.openNewBankQuestion=openNewBankQuestion" in JS
    assert "closest?.('#bankFocusCreate')" in JS
    assert "if(!Array.isArray(state.courses)||!state.courses.length) await refreshCore()" in JS
    assert "setBankEditorOpen(true)" in JS
    assert "question-bank-hotfix-6401.js" not in HTML
    assert "/app.js?v=6.70-production-hardening" in HTML

def test_question_bank_create_api_still_present():
    main=(ROOT/"app/main.py").read_text(encoding="utf-8")
    assert '@app.post("/api/question-bank", status_code=201)' in main
