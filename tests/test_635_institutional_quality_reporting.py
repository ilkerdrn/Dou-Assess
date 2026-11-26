from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'app/main.py').read_text()
API=(ROOT/'app/quality360_api.py').read_text()
SVC=(ROOT/'app/services/quality360.py').read_text()
HTML=(ROOT/'app/static/index.html').read_text()
JS=(ROOT/'app/static/app.js').read_text()

def test_635_version_and_endpoints():
    assert '6.70-production-hardening' in MAIN
    assert '/api/quality360/institutional/self-evaluation' in API
    assert '/api/quality360/institutional/self-evaluation.docx' in API

def test_635_traceable_institutional_builder():
    assert 'build_institutional_self_evaluation_report' in SVC
    assert 'programme_level_trace' in SVC
    assert 'human_approval_required' in SVC
    assert 'KURUM İÇ DEĞERLENDİRME RAPORU' in SVC

def test_635_ui_workspace():
    assert 'data-q360-workspace="institutional"' in HTML
    assert 'q360InstitutionalPrograms' in HTML
    assert 'loadInstitutionalQualityReport' in JS
