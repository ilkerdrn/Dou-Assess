from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')
MAIN=(ROOT/'app/main.py').read_text(encoding='utf-8')
QUALITY=(ROOT/'app/services/quality360.py').read_text(encoding='utf-8')

def test_version_628():
    assert '6.70-production-hardening' in MAIN

def test_executive_quality_ui():
    for x in ['qualityExecutiveHealth','qualityExecutiveInsights','qualityFacultyOverview','qualityProgramPriority','qualityFrameworkDistribution']:
        assert x in HTML and x in JS
    assert '.executive-command-grid' in CSS and '.executive-score-ring' in CSS

def test_explainable_quality_health_backend():
    for x in ['university_quality_health','critical_program_count','quality_health','risk_level','executive_insights']:
        assert x in QUALITY

def test_program_drilldown():
    assert 'data-quality-program' in JS and "qualityProgramPriority" in JS
