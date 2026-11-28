from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')

def test_6709_asset_key():
    assert '6709-decision-dashboard' in HTML

def test_student_card_has_decision_brief():
    assert 'id="studentCardDecision"' in HTML
    assert 'SONRAKİ ADIM' in JS
    assert 'data-student-action="focus"' in JS

def test_analytics_starts_with_manager_summary():
    assert 'YÖNETİCİ ÖZETİ' in JS
    assert 'analytics-technical-details' in JS
    assert 'ÖÇ açıklarını gör' in JS

def test_quality_dashboard_is_action_first():
    assert 'id="qualityDecisionSummary"' in HTML
    assert 'id="qualityNextSteps"' in HTML
    assert 'Detaylı kalite analizi' in HTML
    assert 'KALİTE KARARI' in JS
    assert 'Riskli dersleri kapat' in JS

def test_6709_responsive_decision_css():
    assert '.student-decision-brief' in CSS
    assert '.quality-advanced-details' in CSS
    assert '.analytics-decision-brief' in CSS
