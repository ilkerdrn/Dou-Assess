from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'app/main.py').read_text(encoding='utf-8')
API=(ROOT/'app/quality360_api.py').read_text(encoding='utf-8')
QUALITY=(ROOT/'app/services/quality360.py').read_text(encoding='utf-8')
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')

def test_version_629():
    assert '6.70-production-hardening' in MAIN

def test_quality_action_backend_contract():
    assert 'quality_action_recommendations' in QUALITY
    assert '/action-recommendations' in API
    assert 'quality_action_accept' in API
    assert 'Bu ölçüt için açık bir PUKÖ döngüsü zaten var' in API

def test_quality_action_ui_contract():
    assert 'qualityActionRecommendations' in HTML and 'loadQualityActions' in JS
    assert 'PUKÖ olarak başlat' in JS and '.quality-action-card' in CSS

def test_action_engine_is_explainable_and_human_approved():
    for x in ['gap_signals','expected_evidence','owner_role','suggested_due_date','plan_text','check_text']:
        assert x in QUALITY
    assert "require_roles(\"admin\", \"quality\", \"program_head\")" in API
