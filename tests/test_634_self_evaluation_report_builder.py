from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/"app/main.py").read_text(encoding="utf-8")
API=(ROOT/"app/quality360_api.py").read_text(encoding="utf-8")
SVC=(ROOT/"app/services/quality360.py").read_text(encoding="utf-8")
HTML=(ROOT/"app/static/index.html").read_text(encoding="utf-8")
JS=(ROOT/"app/static/app.js").read_text(encoding="utf-8")

def test_634_version():
    assert "6.70-production-hardening" in MAIN

def test_self_evaluation_endpoints_present():
    assert "/self-evaluation" in API and "/self-evaluation.docx" in API
    assert "build_self_evaluation_report" in SVC and "build_self_evaluation_docx" in SVC

def test_self_evaluation_is_traceable_and_human_approved():
    assert "human_approval_required" in SVC
    assert "evidence_refs" in SVC
    assert "Nihai rapor" in SVC or "Nihai yayımdan" in SVC

def test_self_evaluation_ui_present():
    assert 'data-q360-workspace="selfeval"' in HTML
    assert 'q360SelfEvalDownload' in HTML
    assert 'loadQ360SelfEvaluation' in JS
