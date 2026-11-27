from __future__ import annotations

from io import BytesIO
from pathlib import Path
import uuid

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter

from app import models as m
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.main import app, APP_VERSION, EXPECTED_SCHEMA_REVISION

Base.metadata.create_all(engine)
client = TestClient(app)
SUFFIX = uuid.uuid4().hex[:8]


def _program() -> dict:
    local=uuid.uuid4().hex[:6].upper()
    r=client.post('/api/programs',json={'code':f'Q667-{SUFFIX}-{local}','name':f'6.67 Güvenlik Programı {local}','faculty':'MYO','department':'Bilgisayar'})
    assert r.status_code in (200,201),r.text
    return r.json()


def _png_bytes() -> bytes:
    out=BytesIO();Image.new('RGB',(8,8),(255,255,255)).save(out,format='PNG');return out.getvalue()


def _pdf_bytes() -> bytes:
    out=BytesIO();w=PdfWriter();w.add_blank_page(width=100,height=100);w.write(out);return out.getvalue()




def test_667_release_contract_and_migration_present():
    assert APP_VERSION == "6.70-production-hardening"
    assert EXPECTED_SCHEMA_REVISION == "0044_outcome_source_and_print_confirm"
    root = Path(__file__).resolve().parents[1]
    migration = (root / "migrations/versions/0039_evidence_integrity_security.py").read_text(encoding="utf-8")
    assert 'revision = "0039_evidence_integrity_security"' in migration
    assert 'down_revision = "0038_institution_acceptance_gate"' in migration

def test_667_quality_evidence_magic_and_read_time_sha_verification():
    p=_program();pid=p['id']
    bad=client.post(f'/api/quality360/programs/{pid}/evidence',data={'criterion_code':'3','category':'quality'},files={'file':('fake.pdf',b'not-a-pdf','application/pdf')})
    assert bad.status_code==400

    up=client.post(f'/api/quality360/programs/{pid}/evidence',data={'criterion_code':'3','category':'quality','description':'integrity test'},files={'file':('proof.txt',b'original-evidence','text/plain')})
    assert up.status_code==201,up.text
    row=up.json();assert row['integrity_status']=='verified'
    ok=client.get(f"/api/quality360/evidence/{row['id']}/download");assert ok.status_code==200 and ok.content==b'original-evidence'

    with SessionLocal() as db:
        obj=db.get(m.QualityEvidenceAsset,row['id']);path=Path(settings.evidence_storage_path)/'quality360'/obj.stored_name
        path.write_bytes(b'tampered-evidence')
    broken=client.get(f"/api/quality360/evidence/{row['id']}/download")
    assert broken.status_code==409
    with SessionLocal() as db:
        obj=db.get(m.QualityEvidenceAsset,row['id']);assert obj.integrity_status=='mismatch' and obj.integrity_checked_at is not None


def test_667_exam_evidence_integrity_blocks_tampered_download_and_package():
    with SessionLocal() as db:
        program=m.Program(code=f'E667-{SUFFIX}',name='Evidence Program',faculty='MYO',department='Ağ');db.add(program);db.flush()
        course=m.Course(program_id=program.id,code=f'C667-{SUFFIX}',name='Evidence Course',academic_year='2026-2027',term='Güz',instructor_email='pilot-admin@local',instructor_name='Pilot')
        db.add(course);db.flush()
        exam=m.Exam(course_id=course.id,title='Evidence Exam',exam_type='Final',course_code_snapshot=course.code,course_name_snapshot=course.name,academic_year_snapshot=course.academic_year,term_snapshot=course.term,program_name_snapshot=program.name)
        db.add(exam);db.commit();exam_id=exam.id
    up=client.post(f'/api/exams/{exam_id}/evidence',data={'kind':'exam_paper','category':'test','description':'sha'},files={'file':('paper.pdf',_pdf_bytes(),'application/pdf')})
    assert up.status_code==201,up.text
    row=up.json();assert row['integrity_status']=='verified'
    with SessionLocal() as db:
        obj=db.get(m.EvidenceAsset,row['id']);path=Path(settings.evidence_storage_path)/obj.stored_name;path.write_bytes(_pdf_bytes()+b'changed')
    assert client.get(f"/api/evidence/{row['id']}/download").status_code==409
    assert client.get(f'/api/exams/{exam_id}/evidence-package').status_code==409


def test_667_controlled_document_maker_checker_and_secure_binary_upload():
    p=_program();pid=p['id']
    doc=client.post('/api/compliance/documents',json={'program_id':pid,'document_code':f'POL-{SUFFIX}','document_type':'policy','title':'Güvenlik Politikası','owner':'Kalite','status':'active','retention_years':5})
    assert doc.status_code==201,doc.text;doc=doc.json()

    unsafe=client.post(f"/api/compliance/documents/{doc['id']}/revisions",json={'revision_no':1,'status':'approved','change_summary':'unsafe','content_text':'x','approved_by':'client'})
    assert unsafe.status_code==409
    draft=client.post(f"/api/compliance/documents/{doc['id']}/revisions",json={'revision_no':1,'status':'draft','change_summary':'v1','content_text':'secure policy','approved_by':'client'})
    assert draft.status_code==201,draft.text;draft=draft.json();assert draft['status']=='draft' and draft['approved_by']==''

    reviewer_email=f'reviewer-{SUFFIX}@local'
    with SessionLocal() as db:
        user=m.AppUser(email=reviewer_email,display_name='Reviewer',auth_source='pilot',is_active=True);db.add(user);db.flush();db.add(m.UserRoleAssignment(user_id=user.id,role='quality'));db.commit()
    h={'X-DOU-Pilot-User':reviewer_email}
    assert client.post(f"/api/compliance/document-revisions/{draft['id']}/submit").status_code==200
    same=client.post(f"/api/compliance/document-revisions/{draft['id']}/review")
    assert same.status_code==409
    reviewed=client.post(f"/api/compliance/document-revisions/{draft['id']}/review",headers=h);assert reviewed.status_code==200,reviewed.text
    approved=client.post(f"/api/compliance/document-revisions/{draft['id']}/approve",headers=h);assert approved.status_code==200,approved.text
    assert approved.json()['approved_by']==reviewer_email

    badfile=client.post(f"/api/compliance/documents/{doc['id']}/revisions/upload",data={'revision_no':'2','status':'draft','change_summary':'bad'},files={'file':('bad.docx',b'not-a-docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
    assert badfile.status_code==400


def test_667_evaluator_token_is_one_time_visible_enforced_and_revocable():
    p=_program();pid=p['id']
    with SessionLocal() as db:
        fw=m.QualityFrameworkProfile(code=f'FW-{SUFFIX}',name='Test Framework',version='1.0',framework_family='TEST',criteria=[],thresholds={},source_meta={},is_builtin=False)
        db.add(fw);db.flush()
        snap=m.QualityFrameworkSnapshot(program_id=pid,academic_year='2026-2027',framework_profile_id=fw.id,framework_code=fw.code,framework_version=fw.version,framework_family=fw.framework_family,criteria=[],thresholds={},source_meta={},content_sha256='a'*64,frozen_by='test')
        db.add(snap);db.flush()
        application=m.AccreditationApplication(program_id=pid,framework_profile_id=fw.id,framework_snapshot_id=snap.id,academic_year='2026-2027',application_type='general',owner='Quality')
        db.add(application);db.commit();aid=application.id
    r=client.post('/api/compliance/evaluator-workspaces',json={'application_id':aid,'evaluator_email':f'eval-{SUFFIX}@example.org','evaluator_name':'External Evaluator','access_mode':'read_only','expires_at':None})
    assert r.status_code==201,r.text
    ws=r.json();token=ws.get('invitation_token');assert token and 'invitation_token_hash' not in ws and ws['expires_at'];assert ws['invitation_path'].startswith(f"/evaluator.html?workspace={ws['id']}#token=")
    bad=client.get(f"/api/public/evaluator-workspaces/{ws['id']}/snapshot",headers={'X-DOU-Evaluator-Token':'wrong'});assert bad.status_code==401
    ok=client.get(f"/api/public/evaluator-workspaces/{ws['id']}/snapshot",headers={'X-DOU-Evaluator-Token':token});assert ok.status_code==200,ok.text
    listed=client.get(f'/api/compliance/applications/{aid}/evaluator-workspaces');assert listed.status_code==200 and 'invitation_token_hash' not in listed.json()[0]
    off=client.patch(f"/api/compliance/evaluator-workspaces/{ws['id']}/access",json={'active':False});assert off.status_code==200
    gone=client.get(f"/api/public/evaluator-workspaces/{ws['id']}/snapshot",headers={'X-DOU-Evaluator-Token':token});assert gone.status_code==410


def test_667_frontend_exposes_integrity_scan_and_read_only_evaluator_portal():
    root = Path(__file__).resolve().parents[1]
    html = (root / 'app/static/index.html').read_text(encoding='utf-8')
    js = (root / 'app/static/app.js').read_text(encoding='utf-8')
    portal = (root / 'app/static/evaluator.html').read_text(encoding='utf-8')
    portal_js = (root / 'app/static/evaluator.js').read_text(encoding='utf-8')
    assert 'runEvidenceIntegrityScan' in html
    assert '/api/operations/jobs/integrity-scan' in js
    assert 'Değerlendirici Alanı' in portal and 'SALT OKUNUR' in portal
    assert 'X-DOU-Evaluator-Token' in portal_js
    assert 'history.replaceState' in portal_js
