from __future__ import annotations
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app import models as m
from app.services.quality360 import mudek_discipline_specific_catalog

client=TestClient(app)

def _post(path,payload):
    r=client.post(path,json=payload); assert r.status_code in (200,201),r.text; return r.json()

def _framework(version='3.1'):
    rows=client.get('/api/quality360/frameworks').json()
    return next(x for x in rows if x['framework_family']=='MÜDEK' and x['version']==version)

def _program(name='Bilgisayar Mühendisliği'):
    suf=uuid.uuid4().hex[:8]
    return _post('/api/programs',{'code':f'BM647-{suf}','name':name,'faculty':'Mühendislik Fakültesi','department':'Bilgisayar Mühendisliği'})

def test_647_release_and_official_ek1_semantics():
    from app.main import APP_VERSION
    assert APP_VERSION=='6.70-production-hardening'
    cat=mudek_discipline_specific_catalog('Bilgisayar Mühendisliği','3.1')
    assert cat['match_status']=='exact'
    codes={x['code'] for x in cat['topics']}
    assert {'EK1-CS-01','EK1-CS-02','EK1-CS-COMP-01'} <= codes
    assert not any(x.startswith('10') for x in codes)

def test_647_software_and_ai_variant_topics_are_name_driven():
    sw=mudek_discipline_specific_catalog('Yazılım Mühendisliği','3.1')
    ai=mudek_discipline_specific_catalog('Yapay Zeka ve Veri Bilimi Mühendisliği','3.1')
    assert sw['required_count']==5
    assert ai['required_count']==7
    assert any(x['code']=='EK1-CS-SW-02' for x in sw['topics'])
    assert any(x['code']=='EK1-CS-AI-05' for x in ai['topics'])

def test_647_direct_evidence_is_required_for_green_ek1():
    p=_program(); fw=_framework()
    before=client.get(f"/api/quality360/programs/{p['id']}/mudek-discipline-specific",params={'framework_id':fw['id']})
    assert before.status_code==200,before.text
    assert before.json()['ready_count']==0
    with SessionLocal() as db:
        db.add(m.QualityEvidenceAsset(program_id=p['id'],criterion_code='5.1',entity_type='program',kind='document',category='quality',description='Genel müfredat',original_name='mufredat.pdf',stored_name=f'{uuid.uuid4().hex}.pdf',mime_type='application/pdf',size_bytes=10,sha256='a'*64))
        db.commit()
    review=client.get(f"/api/quality360/programs/{p['id']}/mudek-discipline-specific",params={'framework_id':fw['id']}).json()
    assert review['review_count']==review['required_count'] and review['ready_count']==0
    first=review['topics'][0]['code']
    with SessionLocal() as db:
        db.add(m.QualityEvidenceAsset(program_id=p['id'],criterion_code=first,entity_type='program',kind='document',category='quality',description='EK-1 doğrudan kanıt',original_name='ek1.pdf',stored_name=f'{uuid.uuid4().hex}.pdf',mime_type='application/pdf',size_bytes=10,sha256='b'*64))
        db.commit()
    after=client.get(f"/api/quality360/programs/{p['id']}/mudek-discipline-specific",params={'framework_id':fw['id']}).json()
    assert after['ready_count']==1 and next(x for x in after['topics'] if x['code']==first)['status']=='ready'

def test_647_bbo_fbo_readiness_uses_official_folder_codes():
    p=_program(); fw=_framework(); year='2026-2027'
    bbo=client.get(f"/api/quality360/programs/{p['id']}/mudek-evidence-room-readiness",params={'academic_year':year,'room_type':'BBO','framework_id':fw['id']})
    fbo=client.get(f"/api/quality360/programs/{p['id']}/mudek-evidence-room-readiness",params={'academic_year':year,'room_type':'FBO','framework_id':fw['id']})
    assert bbo.status_code==200,bbo.text; assert fbo.status_code==200,fbo.text
    assert bbo.json()['summary']['mandatory_total']==21 and fbo.json()['summary']['mandatory_total']==21
    with SessionLocal() as db:
        db.add(m.QualityEvidenceAsset(program_id=p['id'],criterion_code='BBO.3.2',entity_type='program',kind='document',category='mudek-bbo',description='PÇ ölçme',original_name='pc.pdf',stored_name=f'{uuid.uuid4().hex}.pdf',mime_type='application/pdf',size_bytes=10,sha256='c'*64))
        db.add(m.QualityEvidenceAsset(program_id=p['id'],criterion_code='FBO.LIB.INFO',entity_type='program',kind='document',category='mudek-fbo',description='Kütüphane',original_name='kutuphane.pdf',stored_name=f'{uuid.uuid4().hex}.pdf',mime_type='application/pdf',size_bytes=10,sha256='d'*64))
        db.commit()
    bbo=client.get(f"/api/quality360/programs/{p['id']}/mudek-evidence-room-readiness",params={'academic_year':year,'room_type':'BBO','framework_id':fw['id']}).json()
    fbo=client.get(f"/api/quality360/programs/{p['id']}/mudek-evidence-room-readiness",params={'academic_year':year,'room_type':'FBO','framework_id':fw['id']}).json()
    assert next(x for x in bbo['items'] if x['code']=='BBO.3.2')['status']=='ready'
    assert next(x for x in fbo['items'] if x['code']=='FBO.LIB.INFO')['status']=='ready'

def test_647_frontend_exposes_mudek_readiness_workspace():
    js=open('app/static/app.js',encoding='utf-8').read(); html=open('app/static/index.html',encoding='utf-8').read()
    assert '/mudek-ek1' in js and '/mudek-evidence-room-readiness' in js
    assert 'q647MudekEk1' in html and 'MÜDEK 3.1 · EK-1 + BELGE ODASI' in html


def test_647_precision_ek1_requires_curriculum_direct_evidence_and_manual_review():
    p=_program('Bilgisayar Mühendisliği'); fw=_framework('3.1'); year='2026-2027'
    _post('/api/quality360/curriculum',{
        'program_id':p['id'],'academic_year':year,'term':'Güz','class_level':'1. Sınıf',
        'course_code':f'MAT647-{uuid.uuid4().hex[:4]}','course_name':'Olasılık ve İstatistik',
        'ects':6,'course_category':'Genel / Zorunlu','is_professional':False,'is_program_specific':False,
        'is_external_stakeholder_supported':False,'is_applied_or_current_tech':False,'quality_status':'implemented','notes':'İleri matematik ve olasılık'
    })
    before=client.get(f"/api/quality360/programs/{p['id']}/mudek-ek1",params={'academic_year':year,'framework_id':fw['id']})
    assert before.status_code==200,before.text
    data=before.json(); assert data['matched'] is True
    topic=next(x for x in data['topics'] if x['code']=='EK1-CS-01')
    assert topic['matched_course_count']>=1 and topic['status']=='review' and topic['evidence_count']==0

    up=client.post(f"/api/quality360/programs/{p['id']}/evidence",data={'criterion_code':'EK1-CS-01','category':'mudek-ek1','description':'EK-1 matematik kapsam kanıtı'},files={'file':('ek1-math.txt',b'MUDEK EK1 evidence','text/plain')})
    assert up.status_code in (200,201),up.text
    mid=client.get(f"/api/quality360/programs/{p['id']}/mudek-ek1",params={'academic_year':year,'framework_id':fw['id']}).json()
    topic=next(x for x in mid['topics'] if x['code']=='EK1-CS-01')
    assert topic['evidence_count']>=1 and topic['status']=='review' and topic['manual_review_completed'] is False

    review=client.put('/api/quality360/criterion-assessments',json={
        'program_id':p['id'],'framework_profile_id':fw['id'],'academic_year':year,
        'criterion_code':'EK1-CS-01','maturity_level':4,'quality_status':'measured',
        'note':'MÜDEK EK-1 kalite doğrulaması','evidence_refs':[]
    })
    assert review.status_code in (200,201),review.text
    after=client.get(f"/api/quality360/programs/{p['id']}/mudek-ek1",params={'academic_year':year,'framework_id':fw['id']}).json()
    topic=next(x for x in after['topics'] if x['code']=='EK1-CS-01')
    assert topic['status']=='ready' and topic['manual_review_completed'] is True


def test_647_ek1_manual_review_isolated_by_framework_version():
    p=_program('Bilgisayar Mühendisliği'); fw31=_framework('3.1'); fw30=_framework('3.0'); year='2026-2027'
    _post('/api/quality360/curriculum',{
        'program_id':p['id'],'academic_year':year,'term':'Güz','class_level':'1. Sınıf',
        'course_code':f'MATISO-{uuid.uuid4().hex[:4]}','course_name':'Olasılık ve İstatistik',
        'ects':6,'course_category':'Genel / Zorunlu','is_professional':False,'is_program_specific':False,
        'is_external_stakeholder_supported':False,'is_applied_or_current_tech':False,'quality_status':'implemented','notes':''
    })
    up=client.post(f"/api/quality360/programs/{p['id']}/evidence",data={'criterion_code':'EK1-CS-01','category':'mudek-ek1','description':'EK1 evidence'},files={'file':('ek1-iso.txt',b'isolation evidence','text/plain')})
    assert up.status_code in (200,201),up.text
    review=client.put('/api/quality360/criterion-assessments',json={
        'program_id':p['id'],'framework_profile_id':fw30['id'],'academic_year':year,
        'criterion_code':'EK1-CS-01','maturity_level':5,'quality_status':'measured','note':'3.0 only','evidence_refs':[]
    })
    assert review.status_code in (200,201),review.text
    data=client.get(f"/api/quality360/programs/{p['id']}/mudek-ek1",params={'academic_year':year,'framework_id':fw31['id']}).json()
    topic=next(x for x in data['topics'] if x['code']=='EK1-CS-01')
    assert topic['manual_review_completed'] is False and topic['status']=='review'


def test_647_bbo_zip_routes_mc_evidence_and_contains_readiness_matrix():
    import io, json, zipfile
    p=_program('Bilgisayar Mühendisliği'); fw=_framework('3.1'); year='2026-2027'
    up=client.post(f"/api/quality360/programs/{p['id']}/evidence",data={'criterion_code':'BBO.3.3.MC1','category':'mudek-bbo','description':'MÇ-1 öğrenci kanıtı'},files={'file':('mc1.txt',b'MC1 evidence bytes','text/plain')})
    assert up.status_code in (200,201),up.text
    resp=client.get(f"/api/compliance/programs/{p['id']}/evidence-room.zip",params={'academic_year':year,'room_type':'BBO','framework_id':fw['id']})
    assert resp.status_code==200,resp.text
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        names=z.namelist()
        assert any('/3 - Program Çıktıları/3.3/MÇ-1/' in n and 'mc1' in n.lower() for n in names)
        matrix_name=next(n for n in names if n.endswith('/KANIT-HAZIRLIK-MATRISI.json'))
        matrix=json.loads(z.read(matrix_name).decode('utf-8'))
        row=next(x for x in matrix['items'] if x['code']=='BBO.3.3.MC1')
        assert row['status']=='ready' and row['exact_evidence_count']>=1
        assert matrix['framework']['version']=='3.1'


def test_647_fbo_zip_uses_detailed_evidence_subfolders():
    import io, zipfile
    p=_program('Bilgisayar Mühendisliği'); fw=_framework('3.1'); year='2026-2027'
    up=client.post(f"/api/quality360/programs/{p['id']}/evidence",data={'criterion_code':'FBO.PHYS.EXP','category':'mudek-fbo','description':'Fizik deney kanıtı'},files={'file':('fizik-deney.txt',b'physics experiment evidence','text/plain')})
    assert up.status_code in (200,201),up.text
    resp=client.get(f"/api/compliance/programs/{p['id']}/evidence-room.zip",params={'academic_year':year,'room_type':'FBO','framework_id':fw['id']})
    assert resp.status_code==200,resp.text
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        names=z.namelist()
        assert any('/2 - Ortak Fizik Dersleri/Deney Listeleri ve Raporları/' in n and 'fizik-deney' in n.lower() for n in names)


def test_647_fbo_evidence_is_shared_within_same_faculty_only():
    fw=_framework('3.1'); year='2026-2027'
    p1=_program('Bilgisayar Mühendisliği')
    # Same faculty, different program
    suf=uuid.uuid4().hex[:8]
    p2=_post('/api/programs',{'code':f'EE647-{suf}','name':'Elektrik-Elektronik Mühendisliği','faculty':'Mühendislik Fakültesi','department':'Elektrik-Elektronik Mühendisliği'})
    other=_post('/api/programs',{'code':f'OT647-{suf}','name':'Başka Program','faculty':'Başka Fakülte','department':'Başka Bölüm'})

    up=client.post(f"/api/quality360/programs/{p2['id']}/evidence",data={'criterion_code':'FBO.LIB.INFO','category':'mudek-fbo','description':'Fakülte ortak kütüphane kanıtı'},files={'file':('ortak-kutuphane.txt',b'faculty shared library evidence','text/plain')})
    assert up.status_code in (200,201),up.text
    up2=client.post(f"/api/quality360/programs/{other['id']}/evidence",data={'criterion_code':'FBO.HEALTH','category':'mudek-fbo','description':'Başka fakülte sağlık kanıtı'},files={'file':('other-health.txt',b'other faculty evidence','text/plain')})
    assert up2.status_code in (200,201),up2.text

    data=client.get(f"/api/quality360/programs/{p1['id']}/mudek-evidence-room-readiness",params={'academic_year':year,'room_type':'FBO','framework_id':fw['id']}).json()
    assert data['evidence_scope']['type']=='faculty'
    assert p2['id'] in data['evidence_scope']['program_ids'] and other['id'] not in data['evidence_scope']['program_ids']
    lib=next(x for x in data['items'] if x['code']=='FBO.LIB.INFO')
    health=next(x for x in data['items'] if x['code']=='FBO.HEALTH')
    assert lib['status']=='ready' and any(e['program_id']==p2['id'] for e in lib['evidence'])
    assert health['status']!='ready'


def test_647_missing_room_evidence_flows_into_action_center():
    p=_program('Bilgisayar Mühendisliği'); fw=_framework('3.1'); year='2026-2027'
    r=client.get(f"/api/quality360/programs/{p['id']}/action-recommendations",params={'academic_year':year,'framework_id':fw['id']})
    assert r.status_code==200,r.text
    proposals=r.json()['proposals']
    codes={x['criterion_code'] for x in proposals}
    assert any(str(x).startswith('BBO.') for x in codes)
    assert any(str(x).startswith('FBO.') for x in codes)
    room=next(x for x in proposals if str(x['criterion_code']).startswith('BBO.'))
    assert room['expected_evidence'] and room['owner_role']
