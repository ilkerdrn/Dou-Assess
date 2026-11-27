from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from tests.test_641_accreditation_compliance_core import context, AY

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')
MAIN=(ROOT/'app/main.py').read_text(encoding='utf-8')
client=TestClient(app)

def test_642_version_and_no_schema_bump():
    assert 'APP_VERSION = "6.70-production-hardening"' in MAIN
    assert 'EXPECTED_SCHEMA_REVISION = "0044_outcome_source_and_print_confirm"' in MAIN

def test_642_action_center_and_student_workspace_contract():
    assert 'YAPILACAKLAR' in HTML and 'Sıradaki işiniz' in HTML
    assert 'id="dashboardActionCenter"' in HTML
    assert 'id="studentCardsNav"' in HTML
    assert 'id="page-studentcards"' in HTML
    assert "prepareStudentCards()" in JS
    assert "renderActionCenter(d)" in JS
    assert '.student-card-summary' in CSS
    assert '.action-center-row' in CSS

def test_642_student_card_contains_lo_po_summary_and_pdf():
    ctx=context(); sid=ctx['student']['id']
    r=client.get(f'/api/compliance/students/{sid}/outcome-card',params={'academic_year':AY})
    assert r.status_code==200, r.text
    data=r.json()
    assert 'learning_outcomes' in data and 'program_outcomes' in data and 'courses' in data
    assert 'summary' in data and 'verification_code' in data and len(data['verification_code'])==16
    assert all('learning_outcomes' in c for c in data['courses'])
    pdf=client.get(f'/api/compliance/students/{sid}/outcome-card.pdf',params={'academic_year':AY})
    assert pdf.status_code==200, pdf.text
    assert pdf.headers['content-type'].startswith('application/pdf')
    assert pdf.content[:4]==b'%PDF'
