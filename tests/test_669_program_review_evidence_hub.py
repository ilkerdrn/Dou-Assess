from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import uuid

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app import models as m

Base.metadata.create_all(engine)
client=TestClient(app)
SUFFIX=uuid.uuid4().hex[:8]


def test_669_migration_and_router_contract():
    root=Path(__file__).resolve().parents[1]
    mig=(root/'migrations/versions/0041_program_review_evidence_hub.py').read_text()
    assert 'revision = "0041_program_review_evidence_hub"' in mig
    assert 'down_revision = "0040_operations_automation"' in mig
    main=(root/'app/main.py').read_text()
    assert 'program_review_router' in main


def _create_program():
    local=uuid.uuid4().hex[:8]
    r=client.post('/api/programs',json={'code':f'PR-{local}','name':f'Program Review {local}','faculty':'MYO','department':'Bilgisayar'})
    assert r.status_code==201,r.text
    return r.json()['id']


def _create_template():
    local=uuid.uuid4().hex[:8]
    r=client.post('/api/program-review/templates',json={
        'code':f'PRT-{local}','version':'1.0','title':'Beş Yıllık Program Değerlendirme',
        'sections':[{'key':'profile','title':'Program Profili','guidance':'Programın kapsamını açıklayın.'},{'key':'outcomes','title':'Öğrenme Sonuçları','guidance':'Doğrudan ve dolaylı kanıtları yorumlayın.'}]
    })
    assert r.status_code==201,r.text
    return r.json()['id']


def test_669_program_review_maker_checker_and_final_snapshot():
    pid=_create_program();tid=_create_template()
    r=client.post(f'/api/programs/{pid}/program-reviews',json={'template_id':tid,'academic_year':'2026-2027','title':'Kurumsal Program Review','owner':'owner@dogus.edu.tr'})
    assert r.status_code==201,r.text
    rid=r.json()['id']
    dash=client.get(f'/api/program-reviews/{rid}').json();assert dash['progress']['total']==2
    for sec in dash['sections']:
        u=client.patch(f"/api/program-review-sections/{sec['id']}",json={'narrative':f"{sec['title']} için kanıta dayalı değerlendirme.",'contributor_email':'contributor@dogus.edu.tr','reviewer_email':'reviewer@dogus.edu.tr'})
        assert u.status_code==200,u.text
        sub=client.post(f"/api/program-review-sections/{sec['id']}/submit")
        assert sub.status_code==200 and sub.json()['status']=='submitted'
        rev=client.post(f"/api/program-review-sections/{sec['id']}/review",json={'decision':'approve','note':'Kanıt ve anlatım uygun.'})
        assert rev.status_code==200,rev.text
        assert rev.json()['status']=='approved'
    fin=client.post(f'/api/program-reviews/{rid}/finalize')
    assert fin.status_code==200,fin.text
    assert fin.json()['status']=='final' and len(fin.json()['final_sha256'])==64
    blocked=client.patch(f"/api/program-review-sections/{dash['sections'][0]['id']}",json={'narrative':'Sonradan değişiklik'})
    assert blocked.status_code==409


def test_669_evidence_hub_search_tags_duplicate_and_review_usage():
    pid=_create_program();tid=_create_template()
    review=client.post(f'/api/programs/{pid}/program-reviews',json={'template_id':tid,'academic_year':'2027-2028','owner':'owner2@dogus.edu.tr'}).json()
    sec=client.get(f"/api/program-reviews/{review['id']}").json()['sections'][0]
    sha=hashlib.sha256(b'same-evidence').hexdigest()
    with SessionLocal() as db:
        a=m.QualityEvidenceAsset(program_id=pid,criterion_code='3.1',entity_type='program',kind='document',category='assessment',description='Program çıktıları ölçme raporu',original_name=f'pc-report-{SUFFIX}.pdf',stored_name=f'{uuid.uuid4().hex}.pdf',mime_type='application/pdf',size_bytes=12,sha256=sha,integrity_status='verified',integrity_checked_at=datetime.now(timezone.utc),version_no=1,created_at=datetime.now(timezone.utc))
        b=m.QualityEvidenceAsset(program_id=pid,criterion_code='3.2',entity_type='program',kind='document',category='assessment',description='Aynı içerik ikinci kayıt',original_name=f'pc-report-copy-{SUFFIX}.pdf',stored_name=f'{uuid.uuid4().hex}.pdf',mime_type='application/pdf',size_bytes=12,sha256=sha,integrity_status='verified',integrity_checked_at=datetime.now(timezone.utc),version_no=1,created_at=datetime.now(timezone.utc))
        db.add_all([a,b]);db.commit();db.refresh(a);db.refresh(b);aid,bid=a.id,b.id
    link=client.post(f"/api/program-review-sections/{sec['id']}/evidence",json={'source_type':'quality','source_id':aid,'note':'Program çıktıları bölümünü destekler.'})
    assert link.status_code==201,link.text
    tag=client.post(f'/api/evidence-hub/item/quality/{aid}/tags',json={'label':'Program Çıktıları'})
    assert tag.status_code==201,tag.text
    hub=client.get(f'/api/evidence-hub?program_id={pid}&q=Program&limit=20')
    assert hub.status_code==200,hub.text
    item=next(x for x in hub.json()['items'] if x['source_type']=='quality' and x['source_id']==aid)
    assert item['review_usage_count']==1 and any(t['label']=='Program Çıktıları' for t in item['tags'])
    detail=client.get(f'/api/evidence-hub/item/quality/{aid}')
    assert detail.status_code==200 and detail.json()['program_review_usage'][0]['review_id']==review['id']
    dup=client.get(f'/api/evidence-hub/duplicates/sha256?program_id={pid}')
    assert dup.status_code==200,dup.text
    group=next(x for x in dup.json()['items'] if x['sha256']==sha)
    assert group['count']>=2 and {i['source_id'] for i in group['items']} >= {aid,bid}


def test_669_evidence_hub_pagination_contract():
    r=client.get('/api/evidence-hub?limit=1&offset=0')
    assert r.status_code==200,r.text
    assert r.json()['limit']==1 and len(r.json()['items'])<=1 and 'total' in r.json()


def test_669_program_review_governance_and_final_evidence_manifest():
    pid=_create_program()
    local=uuid.uuid4().hex[:8]
    tid=client.post('/api/program-review/templates',json={
        'code':f'ONE-{local}','version':'1.0','title':'Tek Bölüm Review',
        'sections':[{'key':'evidence','title':'Kanıtlı Bölüm','guidance':'Kanıtla destekleyin.'}]
    }).json()['id']
    review=client.post(f'/api/programs/{pid}/program-reviews',json={'template_id':tid,'academic_year':'2028-2029','owner':'pilot-admin@local'}).json()
    sec=client.get(f"/api/program-reviews/{review['id']}").json()['sections'][0]
    contributor=f'contrib-{local}@dogus.edu.tr'
    reviewer=f'reviewer-{local}@dogus.edu.tr'
    with SessionLocal() as db:
        course=m.Course(program_id=pid,code=f'PRC-{local}',name='Program Review Katkı Dersi',academic_year='2028-2029',term='Güz',instructor_email=contributor,instructor_name='Katkı Veren')
        db.add(course);db.flush()
        user=m.AppUser(email=contributor,display_name='Katkı Veren',auth_source='pilot',is_active=True);db.add(user);db.flush()
        db.add(m.UserRoleAssignment(user_id=user.id,role='instructor',course_id=course.id))
        ev=m.QualityEvidenceAsset(program_id=pid,criterion_code='PR.1',entity_type='program',kind='document',category='program_review',description='Final manifest kanıtı',original_name=f'final-manifest-{local}.pdf',stored_name=f'{uuid.uuid4().hex}.pdf',mime_type='application/pdf',size_bytes=18,sha256=hashlib.sha256(b'final-manifest').hexdigest(),integrity_status='verified',integrity_checked_at=datetime.now(timezone.utc),version_no=1,created_at=datetime.now(timezone.utc))
        db.add(ev);db.commit();db.refresh(ev);evidence_id=ev.id
    assigned=client.patch(f"/api/program-review-sections/{sec['id']}",json={'contributor_email':contributor,'reviewer_email':reviewer,'narrative':'İlk kanıta dayalı değerlendirme.'})
    assert assigned.status_code==200,assigned.text
    contributor_headers={'X-DOU-Pilot-User':contributor}
    blocked=client.patch(f"/api/program-review-sections/{sec['id']}",headers=contributor_headers,json={'reviewer_email':'someone-else@dogus.edu.tr'})
    assert blocked.status_code==403,blocked.text
    own_edit=client.patch(f"/api/program-review-sections/{sec['id']}",headers=contributor_headers,json={'narrative':'Katkı veren anlatımı güncelledi.'})
    assert own_edit.status_code==200,own_edit.text
    linked=client.post(f"/api/program-review-sections/{sec['id']}/evidence",json={'source_type':'quality','source_id':evidence_id,'note':'Final snapshot kanıtı'})
    assert linked.status_code==201,linked.text
    submitted=client.post(f"/api/program-review-sections/{sec['id']}/submit",headers=contributor_headers)
    assert submitted.status_code==200,submitted.text
    approved=client.post(f"/api/program-review-sections/{sec['id']}/review",json={'decision':'approve','note':'Onaylandı'})
    assert approved.status_code==200,approved.text
    final=client.post(f"/api/program-reviews/{review['id']}/finalize")
    assert final.status_code==200,final.text
    snap=client.get(f"/api/program-reviews/{review['id']}/final-snapshot")
    assert snap.status_code==200,snap.text
    body=snap.json();assert body['integrity_status']=='verified' and body['sha256']==body['actual_sha256']
    frozen=body['snapshot']['sections'][0]['evidence'][0]
    assert frozen['source_type']=='quality' and frozen['source_id']==evidence_id and len(frozen['sha256'])==64


def test_669_frontend_workspaces_are_bound():
    root=Path(__file__).resolve().parents[1]
    html=(root/'app/static/index.html').read_text(encoding='utf-8')
    js=(root/'app/static/app.js').read_text(encoding='utf-8')
    assert 'id="programReviewNav"' in html and 'id="evidenceHubNav"' in html
    assert "if(name==='programreview') prepareProgramReview();" in js
    assert "if(name==='evidencehub') prepareEvidenceHub();" in js
    assert '/final-snapshot' in js and 'data-evidence-link' in js
