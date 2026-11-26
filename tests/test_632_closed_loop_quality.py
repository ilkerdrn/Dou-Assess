from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/"app/main.py").read_text(encoding="utf-8")
API=(ROOT/"app/quality360_api.py").read_text(encoding="utf-8")
SCHEMAS=(ROOT/"app/schemas.py").read_text(encoding="utf-8")
JS=(ROOT/"app/static/app.js").read_text(encoding="utf-8")
HTML=(ROOT/"app/static/index.html").read_text(encoding="utf-8")
CSS=(ROOT/"app/static/styles.css").read_text(encoding="utf-8")

def test_version_632_and_schema_stable():
    assert "6.70-production-hardening" in MAIN
    assert "0042_performance_production_hardening" in MAIN

def test_governance_decision_to_action_contract():
    assert '/api/quality360/governance/{decision_id}/start-action' in API
    assert 'GovernanceDecisionActionCreate' in SCHEMAS
    assert 'decision:' in API
    assert 'Bu kurul kararı için açık bir PUKÖ zaten var' in API

def test_evidence_gated_closure_contract():
    assert '/api/quality360/programs/{program_id}/closure-readiness' in API
    assert '/api/quality360/quality-cycles/{cycle_id}/close' in API
    assert 'en az bir gerçek kalite kanıtı' in API
    assert 'QualityCycleCloseRequest' in SCHEMAS

def test_closed_loop_ui_contract():
    for token in ['q360GovernanceList','q360ClosureList','loadQ360GovernanceActions','loadQualityClosureReadiness','data-gov-action','data-cycle-close']:
        assert token in HTML or token in JS
    assert '.quality-decision-row' in CSS and '.quality-closure-row' in CSS
