from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'app/main.py').read_text()
API=(ROOT/'app/quality360_api.py').read_text()
SERVICE=(ROOT/'app/services/quality360.py').read_text()
HTML=(ROOT/'app/static/index.html').read_text()
JS=(ROOT/'app/static/app.js').read_text()
CSS=(ROOT/'app/static/styles.css').read_text()

def test_633_version_contract():
    assert '6.70-production-hardening' in MAIN

def test_accreditation_readiness_api_exists():
    assert '/api/quality360/programs/{program_id}/accreditation-readiness' in API
    assert 'accreditation_evidence_readiness' in SERVICE

def test_readiness_is_explainable_not_official_score():
    assert 'resmî akreditasyon kararı veya puanı değildir' in SERVICE
    assert 'missing_signals' in SERVICE and 'evidence_count' in SERVICE and 'closed_cycle_count' in SERVICE

def test_visit_mode_ui_contract():
    assert 'data-q360-workspace="readiness"' in HTML
    assert 'q360VisitMatrix' in HTML and 'q360VisitPriority' in HTML
    assert 'loadAccreditationReadiness' in JS

def test_visit_mode_is_read_only_focused():
    assert 'accreditation-visit-mode' in CSS
    assert 'Normal görünüme dön' in JS
    assert 'Kriter → kanıt → PUKÖ hazır olma matrisi' in HTML
