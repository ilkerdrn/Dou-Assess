from app.main import APP_VERSION, EXPECTED_SCHEMA_REVISION
from app import models as m

def test_652_release_contract():
    assert APP_VERSION == '6.70-production-hardening'
    assert EXPECTED_SCHEMA_REVISION == '0047_institution_settings_outcome_approval'
    assert m.MedekPdrFormAnalysis.__tablename__ == 'quality_medek_pdr_form_analyses'

def test_652_api_contract_text():
    text=open('app/compliance_api.py',encoding='utf-8').read()
    assert '/medek-pdr-forms' in text
    assert '/medek-institution-report' in text
    assert 'FORM1' in text and 'FORM2' in text and 'FORM3' in text

def test_652_ui_contract_text():
    html=open('app/static/index.html',encoding='utf-8').read(); js=open('app/static/app.js',encoding='utf-8').read()
    assert '6.53 · MEDEK NİHAİ KARAR / KURUM RAPORU / FREEZE' in html
    assert 'q652LoadForms' in js
