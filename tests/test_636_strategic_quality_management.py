from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/"app/main.py").read_text()
API=(ROOT/"app/quality360_api.py").read_text()
MODELS=(ROOT/"app/models.py").read_text()
HTML=(ROOT/"app/static/index.html").read_text()
JS=(ROOT/"app/static/app.js").read_text()
MIG=(ROOT/"migrations/versions/0023_strategic_quality.py").read_text()

def test_version_and_migration():
    assert "6.70-production-hardening" in MAIN
    assert 'revision="0023_strategic_quality"' in MIG
    assert 'down_revision="0022_quality_calendar"' in MIG

def test_strategy_models_and_api():
    assert 'class StrategicObjective' in MODELS and 'class StrategicKPI' in MODELS
    assert '/api/quality360/strategy/dashboard' in API
    assert '/api/quality360/strategy/objectives' in API
    assert '/api/quality360/strategy/kpis' in API
    assert 'human_approval_required' in API

def test_strategy_ui():
    assert 'data-q360-workspace="strategy"' in HTML
    assert 'Stratejik Plan → KPI → PUKÖ → Kanıt' in HTML
    assert 'q360StrategySummary' in HTML and 'q360StrategyObjectives' in HTML
    assert 'loadStrategicQuality' in JS
