from __future__ import annotations

from pathlib import Path
from io import BytesIO
import json

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import select

from app.db import Base, engine, SessionLocal
from app.main import app
from app import models as m


Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)


def post(path, data):
    r = client.post(path, json=data)
    assert r.status_code in (200, 201), (path, r.status_code, r.text)
    return r.json()


def make_minimal_pdf() -> bytes:
    from reportlab.pdfgen import canvas
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(200, 200))
    c.drawString(20, 100, "DOU Assess test")
    c.showPage(); c.save()
    return buf.getvalue()


def make_workbook(valid=True) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Programlar"
    ws.append(["program_code","program_name","faculty","department"])
    ws.append(["IAT","İnternet ve Ağ Teknolojileri","MYO","Bilgisayar Teknolojileri"])

    ws = wb.create_sheet("Dersler")
    ws.append(["program_code","course_code","course_name","academic_year","term","instructor_email"])
    ws.append(["IAT","BLP 276","Python Programlama","2026-2027","Güz","ogretim@dogus.edu.tr"])

    ws = wb.create_sheet("Ogrenciler")
    ws.append(["program_code","student_no","full_name","class_name"])
    ws.append(["IAT","20260001","Pilot Öğrenci 01","1. Sınıf"])
    ws.append(["IAT","20260002","Pilot Öğrenci 02","1. Sınıf"])

    ws = wb.create_sheet("Ders_Kayitlari")
    ws.append(["program_code","course_code","academic_year","term","student_no"])
    ws.append(["IAT","BLP 276","2026-2027","Güz","20260001"])
    ws.append(["IAT","BLP 276","2026-2027","Güz","99999999" if not valid else "20260002"])

    ws = wb.create_sheet("OC_PC")
    ws.append(["program_code","course_code","academic_year","term","learning_outcome_code","learning_outcome_description","target","program_outcome_code","program_outcome_description","contribution"])
    ws.append(["IAT","BLP 276","2026-2027","Güz","Ö1","Temel Python yapılarını kullanır",70,"PÇ1","Alan bilgisini kullanır",5])
    ws.append(["IAT","BLP 276","2026-2027","Güz","Ö2","Problemi analiz eder",65,"PÇ2","Problem çözer",4])

    buf = BytesIO(); wb.save(buf); return buf.getvalue()


def test_health_ready_sqlite_unit_environment():
    assert client.get("/api/health").json()["status"] == "ok"
    ready = client.get("/api/ready").json()
    assert ready["status"] == "ready"
    assert ready["database_dialect"] == "sqlite"


def test_atomic_import_validation_and_success():
    invalid = make_workbook(valid=False)
    r = client.post("/api/import/pilot-workbook", files={"file": ("bad.xlsx", invalid, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 422, r.text
    with SessionLocal() as db:
        assert db.scalar(select(m.Program).where(m.Program.code == "IAT")) is None

    valid = make_workbook(valid=True)
    r = client.post("/api/import/pilot-workbook", files={"file": ("good.xlsx", valid, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["summary"]["programs"] == 1
    assert payload["summary"]["courses"] == 1
    assert payload["summary"]["students"] == 2
    assert payload["summary"]["enrollments"] == 2


def test_exam_snapshot_grading_analytics_and_evidence():
    programs = client.get("/api/programs").json()
    program = next(x for x in programs if x["code"] == "IAT")
    course = next(x for x in client.get("/api/courses").json() if x["code"] == "BLP 276")

    exam = post("/api/exams", {
        "course_id": course["id"], "title": "Final", "exam_type": "Final",
        "exam_date": "2026-06-10", "duration_minutes": 50, "instructions": "Test", "sync_students": True,
    })
    assert exam["id"] > 0
    assert exam["student_count"] == 2
    assert {x["code"] for x in exam["learning_outcomes"]} == {"Ö1", "Ö2"}

    q1 = post(f"/api/exams/{exam['id']}/questions", {
        "order_no": 1, "question_type": "mcq", "text": "2+2?", "points": 40,
        "correct_answer": "4", "choices": {"A":"3","B":"4"}, "learning_outcome_code": "Ö1",
    })
    q2 = post(f"/api/exams/{exam['id']}/questions", {
        "order_no": 2, "question_type": "classic", "text": "Analiz", "points": 60,
        "learning_outcome_code": "Ö2", "expected_answer":"Analiz adımları ve gerekçeleri açıklanmalıdır.", "bloom_level":"analyze",
        "rubric":{"criteria":[{"id":"analysis","label":"Analiz","max_points":60,"outcome_codes":["Ö2"]}]},
    })

    assert client.post(f"/api/exams/{exam['id']}/status", json={"status":"ready"}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/status", json={"status":"grading"}).status_code == 200

    students = client.get(f"/api/exams/{exam['id']}/students").json()
    assert len(students) == 2
    s1, s2 = students
    post(f"/api/exams/{exam['id']}/students/{s1['id']}/responses", {"responses":[
        {"question_id":q1["id"],"answer_text":"4"}, {"question_id":q2["id"],"answer_text":"x","rubric_scores":{"analysis":60}}
    ]})
    post(f"/api/exams/{exam['id']}/students/{s2['id']}/responses", {"responses":[
        {"question_id":q1["id"],"answer_text":"3"}, {"question_id":q2["id"],"answer_text":"x","rubric_scores":{"analysis":20}}
    ]})

    an = client.get(f"/api/exams/{exam['id']}/analytics").json()
    assert an["student_count"] == 2
    assert an["evidence_selection"]["min"]["total_score"] == 20
    assert an["evidence_selection"]["max"]["total_score"] == 100
    lo1 = next(x for x in an["learning_outcomes"] if x["code"] == "Ö1")
    assert lo1["target_percent"] == 70

    # Change live source target after exam creation; snapshot must remain at 70.
    with SessionLocal() as db:
        source = db.scalar(select(m.LearningOutcome).where(m.LearningOutcome.course_id == course["id"], m.LearningOutcome.code == "Ö1"))
        source.target_percent = 5
        db.commit()
    an2 = client.get(f"/api/exams/{exam['id']}/analytics").json()
    lo1b = next(x for x in an2["learning_outcomes"] if x["code"] == "Ö1")
    assert lo1b["target_percent"] == 70

    # 6.7 reporting export must carry the same snapshot-based analytics into Excel.
    xlsx = client.get(f"/api/exams/{exam['id']}/results.xlsx")
    assert xlsx.status_code == 200, xlsx.text
    assert xlsx.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    wb = load_workbook(BytesIO(xlsx.content), data_only=True)
    assert {"Ozet", "Ogrenci_Sonuclari", "Sorular", "OC_Basarisi", "PC_Basarisi", "Kanit_Secimi"} <= set(wb.sheetnames)
    ws = wb["Ogrenci_Sonuclari"]
    assert ws.max_row == 3
    assert ws["C2"].value in (20, 100)
    lo_ws = wb["OC_Basarisi"]
    lo_rows = {lo_ws.cell(row=i, column=1).value: lo_ws.cell(row=i, column=3).value for i in range(2, lo_ws.max_row + 1)}
    assert lo_rows["Ö1"] == 70

    pdf = make_minimal_pdf()
    r = client.post(f"/api/exams/{exam['id']}/evidence", data={"kind":"exam_paper","student_id":str(s1["id"])}, files={"file": ("paper.pdf", pdf, "application/pdf")})
    assert r.status_code == 201, r.text
    assert len(client.get(f"/api/exams/{exam['id']}/evidence").json()) == 1
    z = client.get(f"/api/exams/{exam['id']}/evidence-package")
    assert z.status_code == 200
    assert z.headers["content-type"] == "application/zip"


def test_61_management_lifecycle_question_bank_and_audit():
    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    program = next(x for x in client.get('/api/programs').json() if x['code'] == 'IAT')

    # Search/filter works.
    assert client.get('/api/courses', params={'q':'Python'}).json()[0]['id'] == course['id']
    assert len(client.get('/api/students', params={'q':'Pilot Öğrenci 01'}).json()) == 1

    # Safe updates.
    r = client.patch(f"/api/courses/{course['id']}", json={'instructor_email':'yeni@dogus.edu.tr'})
    assert r.status_code == 200, r.text
    assert r.json()['instructor_email'] == 'yeni@dogus.edu.tr'

    # Delete of a course with dependencies must be blocked rather than cascade silently.
    r = client.delete(f"/api/courses/{course['id']}")
    assert r.status_code == 409, r.text

    # Question bank supports course/ÖÇ validation and creates reusable questions.
    bank = post('/api/question-bank', {
        'course_id': course['id'], 'question_type':'mcq', 'text':'Python hangi tür dildir?',
        'default_points':15, 'correct_answer':'Yüksek seviye', 'choices':{'A':'Makine','B':'Yüksek seviye'},
        'learning_outcome_code':'Ö1', 'tags':['python','temel']
    })
    assert bank['is_active'] is True
    assert client.get('/api/question-bank', params={'course_id':course['id'], 'q':'Python'}).json()[0]['id'] == bank['id']

    # New exam: bank question is copied as a snapshot, then lifecycle locks questions.
    exam = post('/api/exams', {
        'course_id': course['id'], 'title':'6.1 Yaşam Döngüsü', 'exam_type':'Quiz',
        'exam_date':'2026-06-11', 'duration_minutes':30, 'instructions':'', 'sync_students':True,
    })
    copied = post(f"/api/exams/{exam['id']}/questions/from-bank", {'bank_question_id':bank['id'], 'order_no':1, 'points':100})
    assert copied['bank_question_id'] == bank['id']
    assert copied['text'] == bank['text']

    r = client.post(f"/api/exams/{exam['id']}/status", json={'status':'ready'})
    assert r.status_code == 200, r.text
    assert r.json()['status'] == 'ready'

    r = client.post(f"/api/exams/{exam['id']}/questions", json={
        'order_no':2,'question_type':'classic','text':'Kilit testi','points':10
    })
    assert r.status_code == 409, r.text

    # Allowed and disallowed state transitions.
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'grading'}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'draft'}).status_code == 409
    exam_students = client.get(f"/api/exams/{exam['id']}/students").json()
    for st in exam_students:
        assert client.post(f"/api/exams/{exam['id']}/students/{st['id']}/responses", json={'responses':[{'question_id':copied['id'],'answer_text':'Yüksek seviye'}]}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'approved'}).status_code == 200
    assert client.patch(f"/api/exams/{exam['id']}", json={'title':'Değişmemeli'}).status_code == 409
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'archived'}).status_code == 200

    # Question-bank edits do not retroactively mutate copied exam question.
    r = client.patch(f"/api/question-bank/{bank['id']}", json={'text':'Havuzda değişti'})
    assert r.status_code == 200, r.text
    saved_exam = client.get(f"/api/exams/{exam['id']}").json()
    assert saved_exam['questions'][0]['text'] == 'Python hangi tür dildir?'

    # Archive bank item; active list hides it.
    assert client.delete(f"/api/question-bank/{bank['id']}").status_code == 200
    assert all(x['id'] != bank['id'] for x in client.get('/api/question-bank', params={'course_id':course['id']}).json())

    # Audit trail contains lifecycle and bank operations.
    logs = client.get('/api/audit-logs', params={'limit':200}).json()
    actions = {(x['action'], x['entity_type']) for x in logs}
    assert ('status_change','exam') in actions
    assert ('create','question_bank') in actions
    assert ('archive','question_bank') in actions

    # Program delete blocked while dependent records remain.
    assert client.delete(f"/api/programs/{program['id']}").status_code == 409



def test_69_exam_builder_batch_reorder_and_normalize():
    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    banks = []
    for idx, (lo, pts) in enumerate([('Ö1', 15), ('Ö2', 25), ('Ö1', 35)], start=1):
        banks.append(post('/api/question-bank', {
            'course_id': course['id'], 'question_type':'mcq', 'text':f'6.9 toplu havuz sorusu {idx}',
            'default_points':pts, 'correct_answer':'A', 'choices':{'A':'Doğru','B':'Yanlış'},
            'learning_outcome_code':lo, 'tags':['6.9','builder']
        }))
    exam = post('/api/exams', {
        'course_id': course['id'], 'title':'6.9 Builder Studio', 'exam_type':'Final',
        'exam_date':'2026-06-20', 'duration_minutes':50, 'instructions':'', 'sync_students':False,
    })
    batch = client.post(f"/api/exams/{exam['id']}/questions/from-bank/batch", json={
        'bank_question_ids':[x['id'] for x in banks], 'skip_existing':True,
    })
    assert batch.status_code == 201, batch.text
    assert batch.json()['added'] == 3
    detail = client.get(f"/api/exams/{exam['id']}").json()
    assert [q['order_no'] for q in detail['questions']] == [1,2,3]
    assert [q['bank_question_id'] for q in detail['questions']] == [x['id'] for x in banks]

    duplicate = client.post(f"/api/exams/{exam['id']}/questions/from-bank/batch", json={
        'bank_question_ids':[banks[0]['id'], banks[1]['id']], 'skip_existing':True,
    })
    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()['added'] == 0
    assert set(duplicate.json()['skipped']) == {banks[0]['id'], banks[1]['id']}

    ids = [q['id'] for q in detail['questions']][::-1]
    reordered = client.put(f"/api/exams/{exam['id']}/questions/reorder", json={'question_ids':ids})
    assert reordered.status_code == 200, reordered.text
    detail = client.get(f"/api/exams/{exam['id']}").json()
    assert [q['id'] for q in detail['questions']] == ids
    assert [q['order_no'] for q in detail['questions']] == [1,2,3]

    normalized = client.post(f"/api/exams/{exam['id']}/questions/normalize-points", json={'precision':2})
    assert normalized.status_code == 200, normalized.text
    assert abs(normalized.json()['total_points'] - 100) < 0.001
    detail = client.get(f"/api/exams/{exam['id']}").json()
    assert abs(sum(float(q['points']) for q in detail['questions']) - 100) < 0.001
    readiness = client.get(f"/api/exams/{exam['id']}/readiness").json()
    assert readiness['ready'] is True, readiness


def test_62_official_paper_readiness_booklets_and_snapshot_stability():
    from pypdf import PdfReader
    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')

    # A draft without a date and without 100 total points is intentionally blocked.
    exam = post('/api/exams', {
        'course_id': course['id'], 'title':'6.2 Resmi Kağıt', 'exam_type':'Final',
        'duration_minutes':50, 'instructions':'', 'sync_students':False,
    })
    q1 = post(f"/api/exams/{exam['id']}/questions", {
        'order_no':1,'question_type':'mcq','text':'Python yorum satırı hangi karakterle başlar?',
        'points':25,'correct_answer':'A','choices':{'A':'#','B':'//','C':'--','D':'/*','E':'REM'},'learning_outcome_code':'Ö1'
    })
    q2 = post(f"/api/exams/{exam['id']}/questions", {
        'order_no':2,'question_type':'mcq','text':'Bir koşul yapısı seçiniz.',
        'points':25,'correct_answer':'B','choices':{'A':'print','B':'if','C':'import','D':'def','E':'class'},'learning_outcome_code':'Ö1'
    })
    post(f"/api/exams/{exam['id']}/questions", {
        'order_no':3,'question_type':'classic','text':'Koşul yapısını kısa bir örnekle açıklayınız.',
        'points':50,'answer_lines':10,'learning_outcome_code':'Ö2','expected_answer':'if koşulu ve gövdesiyle geçerli bir örnek açıklanmalıdır.','bloom_level':'apply',
        'rubric':{'criteria':[{'id':'concept','label':'Kavram','max_points':20,'outcome_codes':['Ö2']},{'id':'example','label':'Örnek','max_points':30,'outcome_codes':['Ö2']}]}
    })
    readiness = client.get(f"/api/exams/{exam['id']}/readiness").json()
    assert readiness['ready'] is False
    assert any('tarihi' in x for x in readiness['issues'])

    assert client.patch(f"/api/exams/{exam['id']}", json={'exam_date':'2026-06-12'}).status_code == 200
    readiness = client.get(f"/api/exams/{exam['id']}/readiness").json()
    assert readiness['ready'] is True, readiness
    assert readiness['total_points'] == 100
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'ready'}).status_code == 200
    assert client.patch(f"/api/exams/{exam['id']}", json={'exam_date':'2026-06-13'}).status_code == 409

    meta_a = client.get(f"/api/exams/{exam['id']}/paper-metadata", params={'booklet':'A'}).json()
    meta_b = client.get(f"/api/exams/{exam['id']}/paper-metadata", params={'booklet':'B'}).json()
    assert meta_a['booklet'] == 'A' and meta_b['booklet'] == 'B'
    assert meta_a['token'] != meta_b['token']
    assert set(meta_a['answer_key'].values()) == {'A','B'}
    assert [x['question_id'] for x in meta_a['question_order']] != [x['question_id'] for x in meta_b['question_order']]

    pdf = client.get(f"/api/exams/{exam['id']}/paper.pdf", params={'booklet':'A'})
    assert pdf.status_code == 200, pdf.text
    assert pdf.content.startswith(b'%PDF')
    reader = PdfReader(BytesIO(pdf.content))
    assert len(reader.pages) >= 2
    text = '\n'.join((page.extract_text() or '') for page in reader.pages[:2])
    assert 'DOĞUŞ ÜNİVERSİTESİ' in text
    assert 'CEVAP FORMU' in text
    assert 'FINAL EXAM' in text.upper()
    assert '6.2 RESMI KAĞIT' not in text.upper()

    # Live course edits must not retroactively mutate the official paper snapshot.
    original_snapshot = meta_a['snapshot'].copy()
    assert client.patch(f"/api/courses/{course['id']}", json={'name':'SONRADAN DEĞİŞEN DERS', 'instructor_name':'Yeni Öğretim Elemanı'}).status_code == 200
    meta_after = client.get(f"/api/exams/{exam['id']}/paper-metadata", params={'booklet':'A'}).json()
    assert meta_after['snapshot'] == original_snapshot
    assert meta_after['snapshot']['course_name'] != 'SONRADAN DEĞİŞEN DERS'

    # Evidence package contains the generated official paper and metadata.
    z = client.get(f"/api/exams/{exam['id']}/evidence-package")
    assert z.status_code == 200
    import zipfile
    with zipfile.ZipFile(BytesIO(z.content)) as archive:
        names = set(archive.namelist())
        assert 'generated/exam-paper-booklet-A.pdf' in names
        assert 'generated/exam-paper-booklet-A.metadata.json' in names


def test_62_paper_service_supports_40_mcq_dynamic_omr():
    from types import SimpleNamespace
    from datetime import date
    from pypdf import PdfReader
    from app.services.paper import build_exam_pdf

    def fake_q(i: int):
        return SimpleNamespace(
            id=1000+i, order_no=i, question_type='mcq', text=f'Dinamik OMR soru {i}', points=2.5,
            correct_answer='A', choices={'A':'A seçeneği','B':'B seçeneği','C':'C seçeneği','D':'D seçeneği','E':'E seçeneği'},
            answer_lines=8, learning_outcome=SimpleNamespace(code='Ö1'), bank_question_id=None,
        )

    exam = SimpleNamespace(
        id=4040, questions=[fake_q(i) for i in range(1,41)], faculty_snapshot='Meslek Yüksekokulu',
        academic_year_snapshot='2026-2027', term_snapshot='Güz', exam_type='Final', exam_date=date(2026,12,20),
        duration_minutes=60, instructions='', course_name_snapshot='Dinamik OMR Testi', course_code_snapshot='TST 404',
        instructor_snapshot='Öğr. Gör. Test', paper_template_version='dou-official-v1', program_name_snapshot='Test Programı',
        department_snapshot='Test', title='Bu iç başlık kağıtta görünmemeli',
    )
    pdf, meta = build_exam_pdf(exam, 'A')
    assert pdf.startswith(b'%PDF')
    assert len(meta['answer_key']) == 40
    assert len(meta['question_order']) == 40
    assert len(PdfReader(BytesIO(pdf)).pages) >= 2


def test_62_static_frontend_id_contract():
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    js = (root / 'app/static/app.js').read_text(encoding='utf-8')
    html = (root / 'app/static/index.html').read_text(encoding='utf-8')
    html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html))
    js_ids = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", js))
    assert js_ids - html_ids == set()


def test_63_generated_personalized_omr_is_machine_readable():
    from types import SimpleNamespace
    from datetime import date
    import fitz, cv2, numpy as np
    from app.services.paper import build_exam_pdf
    from app.services.scan import decode_qr, parse_qr_payload, find_registration_marks, analyze_page

    lo = SimpleNamespace(code='Ö1')
    questions=[]
    for i in range(1,6):
        questions.append(SimpleNamespace(id=8000+i, order_no=i, question_type='mcq', text=f'OMR soru {i}', points=20.0,
            correct_answer='ABCDE'[i-1], choices={k:f'{k} seçeneği' for k in 'ABCDE'}, answer_lines=8, learning_outcome=lo, bank_question_id=None))
    exam=SimpleNamespace(id=6301, questions=questions, faculty_snapshot='Meslek Yüksekokulu', academic_year_snapshot='2026-2027',
        term_snapshot='Güz', exam_type='Final', exam_date=date(2026,12,20), duration_minutes=50, instructions='',
        course_name_snapshot='OMR Pilot', course_code_snapshot='OMR 101', instructor_snapshot='Öğr. Gör. Test',
        paper_template_version='dou-official-v1', program_name_snapshot='Test Programı', department_snapshot='Test', title='OMR')
    student=SimpleNamespace(id=77, student_no='20261234', full_name='Pilot Öğrenci')
    pdf, meta=build_exam_pdf(exam,'A',student=student)
    doc=fitz.open(stream=pdf,filetype='pdf'); pix=doc[0].get_pixmap(matrix=fitz.Matrix(2.5,2.5),alpha=False)
    image=cv2.imdecode(np.frombuffer(pix.tobytes('png'),np.uint8),cv2.IMREAD_COLOR)
    qr,_=decode_qr(image); parsed=parse_qr_payload(qr)
    assert parsed['exam_id']==6301 and parsed['student_no']=='20261234' and parsed['booklet']=='A'
    marks=find_registration_marks(image); assert marks is not None
    tl,tr,br,bl=marks
    expected={str(i):'ABCDE'[i-1] for i in range(1,6)}
    # Mark the intended bubbles directly on the rendered scan using the exact normalized layout.
    for b in meta['omr_layout']['bubbles']:
        if expected[str(b['display_no'])] != b['letter']:
            continue
        x=float(b['x']); y=float(b['y'])
        pos=tl + x*(tr-tl) + y*(bl-tl)
        cv2.circle(image,(int(pos[0]),int(pos[1])),10,(0,0,0),-1)
    result=analyze_page(image,meta)
    assert result['kind']=='omr', result
    assert result['issues']==[], result['issues']
    assert result['answers']==expected, (result['answers'], result['diagnostics'])


def test_63_scan_api_duplicate_and_regrade_flow():
    import fitz, cv2, numpy as np
    from app.services.scan import find_registration_marks

    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    exam = post('/api/exams', {
        'course_id': course['id'], 'title':'6.3 OMR API', 'exam_type':'Final', 'exam_date':'2026-12-20',
        'duration_minutes':50, 'instructions':'', 'sync_students':True,
    })
    for i, letter in enumerate('ABCDE', start=1):
        post(f"/api/exams/{exam['id']}/questions", {
            'order_no':i,'question_type':'mcq','text':f'OMR API soru {i}','points':20,
            'correct_answer':letter,'choices':{k:f'{k} şıkkı' for k in 'ABCDE'},'learning_outcome_code':'Ö1'
        })
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'ready'}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'grading'}).status_code == 200
    students=client.get(f"/api/exams/{exam['id']}/students").json(); student=students[0]
    pdf=client.get(f"/api/exams/{exam['id']}/students/{student['id']}/paper.pdf", params={'booklet':'A'})
    assert pdf.status_code==200, pdf.text
    meta=client.get(f"/api/exams/{exam['id']}/paper-metadata", params={'booklet':'A'}).json()
    # Generic metadata and personalized metadata share the same token/layout.
    doc=fitz.open(stream=pdf.content,filetype='pdf'); pix=doc[0].get_pixmap(matrix=fitz.Matrix(2.5,2.5),alpha=False)
    image=cv2.imdecode(np.frombuffer(pix.tobytes('png'),np.uint8),cv2.IMREAD_COLOR)
    marks=find_registration_marks(image); assert marks is not None
    tl,tr,br,bl=marks
    expected={str(i):'ABCDE'[i-1] for i in range(1,6)}
    for b in meta['omr_layout']['bubbles']:
        if expected[str(b['display_no'])] == b['letter']:
            pos=tl+float(b['x'])*(tr-tl)+float(b['y'])*(bl-tl)
            cv2.circle(image,(int(pos[0]),int(pos[1])),10,(0,0,0),-1)
    ok,png=cv2.imencode('.png',image); assert ok
    r=client.post(f"/api/exams/{exam['id']}/scans", files={'file':('marked.png',bytes(png),'image/png')})
    assert r.status_code==201, r.text
    session=r.json(); assert session['accepted_count']==1 and session['review_count']==0, session
    responses=client.get(f"/api/exams/{exam['id']}/students/{student['id']}/responses").json()
    assert len(responses)==5 and all(x['is_correct'] for x in responses), responses
    dup=client.post(f"/api/exams/{exam['id']}/scans", files={'file':('marked-again.png',bytes(png),'image/png')})
    assert dup.status_code==409
    # 6.10: multiple files can be submitted in one station batch. A visually identical
    # form with a different source hash is accepted as a session but classified as a
    # duplicate page; unsupported files fail independently without rolling back it.
    image2=image.copy(); image2[0,0]=(250,250,250)
    ok,png2=cv2.imencode('.png',image2); assert ok
    batch=client.post(f"/api/exams/{exam['id']}/scans-batch", files=[
        ('files',('marked-copy.png',bytes(png2),'image/png')),
        ('files',('bad.txt',b'not-a-scan','text/plain')),
    ])
    assert batch.status_code==201, batch.text
    bp=batch.json(); assert bp['totals']['completed_files']==1 and bp['totals']['failed_files']==1, bp
    assert bp['totals']['pages']==1, bp
    qid=client.get(f"/api/exams/{exam['id']}").json()['questions'][0]['id']
    rg=client.post(f"/api/exams/{exam['id']}/answer-key/regrade", json={'corrections':{str(qid):'B'},'reason':'test correction'})
    assert rg.status_code==200, rg.text
    assert rg.json()['affected_responses'] >= 1
    rev=client.get(f"/api/exams/{exam['id']}/answer-key/revisions").json()
    assert rev and rev[0]['reason']=='test correction'


def test_64_accreditation_period_representative_freeze_and_package():
    import zipfile

    program = post('/api/programs', {
        'code':'ACC64','name':'Akreditasyon Test Programı','faculty':'MYO','department':'Kalite Test'
    })
    course = post('/api/courses', {
        'program_id':program['id'],'code':'ACC 640','name':'Akreditasyon Pilot Dersi','academic_year':'2030-2031','term':'Güz',
        'instructor_email':'kalite@dogus.edu.tr','instructor_name':'Öğr. Gör. Kalite'
    })
    s1 = post('/api/students', {'program_id':program['id'],'student_no':'ACC64001','full_name':'Akreditasyon Öğrenci 1','class_name':'1'})
    s2 = post('/api/students', {'program_id':program['id'],'student_no':'ACC64002','full_name':'Akreditasyon Öğrenci 2','class_name':'1'})
    assert client.post(f"/api/courses/{course['id']}/enrollments/bulk", json={'student_ids':[s1['id'],s2['id']]}).status_code == 200
    lo1 = post(f"/api/courses/{course['id']}/learning-outcomes", {'code':'Ö1','description':'Temel yeterliği uygular','target_percent':70})
    lo2 = post(f"/api/courses/{course['id']}/learning-outcomes", {'code':'Ö2','description':'Analiz yapar','target_percent':80})
    po = post(f"/api/programs/{program['id']}/program-outcomes", {'academic_year':'2030-2031','code':'PÇ1','description':'Mesleki problemi çözer'})
    post('/api/outcome-mappings', {'learning_outcome_id':lo1['id'],'program_outcome_id':po['id'],'contribution':5})
    post('/api/outcome-mappings', {'learning_outcome_id':lo2['id'],'program_outcome_id':po['id'],'contribution':4})

    exam = post('/api/exams', {
        'course_id':course['id'],'title':'ACC64 Final','exam_type':'Final','exam_date':'2031-01-10','duration_minutes':50,'instructions':'','sync_students':True
    })
    q1 = post(f"/api/exams/{exam['id']}/questions", {'order_no':1,'question_type':'mcq','text':'Temel soru','points':50,'correct_answer':'A','choices':{'A':'Doğru','B':'Yanlış'},'learning_outcome_code':'Ö1'})
    q2 = post(f"/api/exams/{exam['id']}/questions", {'order_no':2,'question_type':'classic','text':'Analiz sorusu','points':50,'answer_lines':6,'learning_outcome_code':'Ö2','expected_answer':'Analiz gerekçeli ve sistematik olmalıdır.','bloom_level':'analyze','rubric':{'criteria':[{'id':'analysis','label':'Analiz','max_points':50,'outcome_codes':['Ö2']}]}})
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'ready'}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'grading'}).status_code == 200
    students = client.get(f"/api/exams/{exam['id']}/students").json()
    for idx, st in enumerate(students):
        classic = 10 if idx == 0 else 30
        answer = 'B' if idx == 0 else 'A'
        r = client.post(f"/api/exams/{exam['id']}/students/{st['id']}/responses", json={'responses':[
            {'question_id':q1['id'],'answer_text':answer},
            {'question_id':q2['id'],'answer_text':'yanıt','rubric_scores':{'analysis':classic}},
        ]})
        assert r.status_code == 200, r.text
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'approved'}).status_code == 200

    profile = post('/api/accreditation/profiles', {
        'code':'DOU-TEST','name':'DOU Akreditasyon Test Profili','version':'6.4-test',
        'required_general_evidence_kinds':[], 'required_representative_evidence_kinds':['answer_sheet'],
        'requires_representatives':True,'requires_improvement_for_gaps':True,
    })
    period = post('/api/accreditation/periods', {
        'program_id':program['id'],'profile_id':profile['id'],'academic_year':'2030-2031','term':'Güz','title':'2030-2031 Güz Akreditasyon Testi'
    })
    dash = client.get(f"/api/accreditation/periods/{period['id']}/dashboard").json()
    assert dash['summary']['exam_count'] == 1
    assert dash['summary']['ready'] is False
    assert dash['summary']['lo_measurement_count'] == 2
    assert dash['program_outcomes'] and dash['program_outcomes'][0]['code'] == 'PÇ1'
    assert dash['courses'][0]['po']['PÇ1']['exam_count'] == 1
    assert dash['gap_register'], dash
    assert any('Dondurulmamış' in w for w in dash['exams'][0]['warnings'])

    frozen_period = client.post(f"/api/accreditation/periods/{period['id']}/representatives/freeze-all", json={})
    assert frozen_period.status_code == 200, frozen_period.text
    assert frozen_period.json()['frozen_count'] == 1
    reps = client.get(f"/api/exams/{exam['id']}/representatives")
    assert reps.status_code == 200, reps.text
    rep_rows = reps.json()
    assert {x['slot'] for x in rep_rows} == {'MIN','AVG','MAX'}
    frozen_before = [(x['slot'],x['student_id'],x['total_score']) for x in rep_rows]

    # The archived evidence selection remains frozen even if source scoring data is later corrected.
    with SessionLocal() as db:
        any_response = db.scalar(select(m.Response).join(m.ExamStudent).where(m.ExamStudent.exam_id == exam['id']))
        any_response.awarded_points = float(any_response.awarded_points) + 7
        db.commit()
    frozen_after = client.get(f"/api/exams/{exam['id']}/representatives").json()
    assert [(x['slot'],x['student_id'],x['total_score']) for x in frozen_after] == frozen_before
    frozen_again = client.post(f"/api/exams/{exam['id']}/representatives/freeze", json={}).json()
    assert [(x['slot'],x['student_id'],x['total_score']) for x in frozen_again] == frozen_before

    # Upload required answer-sheet evidence for each unique representative student.
    minimal_pdf = make_minimal_pdf()
    for sid in sorted({x['student_id'] for x in rep_rows}):
        r = client.post(f"/api/exams/{exam['id']}/evidence", data={'kind':'answer_sheet','student_id':str(sid)}, files={'file':(f'{sid}.pdf',minimal_pdf,'application/pdf')})
        assert r.status_code == 201, r.text

    dash = client.get(f"/api/accreditation/periods/{period['id']}/dashboard").json()
    gaps = dash['exams'][0]['improvement_gap_codes']
    assert gaps, dash
    for code in gaps:
        post(f"/api/exams/{exam['id']}/improvements", {'outcome_code':code,'action_text':f'{code} için iyileştirme','owner':'Program Başkanı','due_date':'2031-02-01'})

    dash = client.get(f"/api/accreditation/periods/{period['id']}/dashboard").json()
    assert dash['summary']['ready'] is True, dash
    assert dash['summary']['complete_exam_count'] == 1
    assert client.post(f"/api/accreditation/periods/{period['id']}/status", json={'status':'ready'}).status_code == 200

    period_report = client.get(f"/api/accreditation/periods/{period['id']}/report.xlsx")
    assert period_report.status_code == 200, period_report.text
    report_wb = load_workbook(BytesIO(period_report.content), data_only=True)
    assert {'Yonetici_Ozeti','Ders_PC_Matrisi','PC_Donem_Ozeti','Basarisiz_OC','Iyilestirme_Aksiyonlari','MIN_AVG_MAX_Kanit','Sinav_Kontrol_Listesi'} <= set(report_wb.sheetnames)

    package = client.get(f"/api/accreditation/periods/{period['id']}/evidence-package")
    assert package.status_code == 200, package.text
    with zipfile.ZipFile(BytesIO(package.content)) as z:
        names = set(z.namelist())
        assert '00-dashboard.json' in names
        assert '00-Akreditasyon-Degerlendirme-Raporu.xlsx' in names
        assert '00-PAKET-OKU.txt' in names
        assert '01-profile.json' in names
        assert '02-PC-Matrisi.json' in names
        assert '03-Basarisiz-OC.json' in names
        assert '04-Iyilestirme-Aksiyonlari.json' in names
        assert '05-MIN-AVG-MAX.json' in names
        assert 'SHA256SUMS.json' in names
        assert any(x.endswith('/representatives.json') for x in names)
        assert any('/evidence/' in x for x in names)
        assert any(x.endswith('/generated/exam-paper-booklet-A.pdf') for x in names)

    assert client.post(f"/api/accreditation/periods/{period['id']}/status", json={'status':'archived'}).status_code == 200


def test_65_scoped_roles_pilot_identity_and_audit_actor():
    admin_headers = {}
    # Dedicated two-program scope so visibility assertions are deterministic.
    pa = post('/api/programs', {'code':'RB65A','name':'RBAC Program A','faculty':'MYO','department':'Bilgisayar'})
    pb = post('/api/programs', {'code':'RB65B','name':'RBAC Program B','faculty':'MYO','department':'Elektronik'})
    ca = post('/api/courses', {'program_id':pa['id'],'code':'RB 651','name':'Yetki Dersi A','academic_year':'2032-2033','term':'Güz','instructor_email':'inst65@dogus.edu.tr','instructor_name':'Öğr. Gör. Yetkili'})
    cb = post('/api/courses', {'program_id':pb['id'],'code':'RB 652','name':'Yetki Dersi B','academic_year':'2032-2033','term':'Güz','instructor_email':'other65@dogus.edu.tr','instructor_name':'Öğr. Gör. Diğer'})
    bank_a = post('/api/question-bank', {'course_id':ca['id'],'question_type':'mcq','text':'RBAC soru havuzu A','default_points':10,'correct_answer':'A','choices':{'A':'Doğru','B':'Yanlış'},'tags':['rbac','a']})
    bank_b = post('/api/question-bank', {'course_id':cb['id'],'question_type':'classic','text':'RBAC soru havuzu B','default_points':10,'answer_lines':6,'tags':['rbac','b']})

    def mkuser(email, name):
        r=client.post('/api/users',json={'email':email,'display_name':name,'auth_source':'pilot','is_active':True})
        assert r.status_code==201,r.text
        return r.json()
    inst=mkuser('inst65@dogus.edu.tr','Öğr. Gör. Yetkili')
    head=mkuser('head65@dogus.edu.tr','Program Başkanı 65')
    quality=mkuser('quality65@dogus.edu.tr','Kalite Yetkilisi 65')
    assert client.post(f"/api/users/{inst['id']}/roles",json={'role':'instructor'}).status_code==400
    assert client.post(f"/api/users/{inst['id']}/roles",json={'role':'instructor','course_id':ca['id']}).status_code==201
    assert client.post(f"/api/users/{head['id']}/roles",json={'role':'program_head','program_id':pa['id']}).status_code==201
    assert client.post(f"/api/users/{quality['id']}/roles",json={'role':'quality'}).status_code==201

    hi={'X-DOU-Pilot-User':'inst65@dogus.edu.tr'}
    hh={'X-DOU-Pilot-User':'head65@dogus.edu.tr'}
    hq={'X-DOU-Pilot-User':'quality65@dogus.edu.tr'}

    me=client.get('/api/auth/me',headers=hi); assert me.status_code==200 and 'instructor' in me.json()['role_names']
    visible=client.get('/api/courses',headers=hi).json()
    ids={x['id'] for x in visible}; assert ca['id'] in ids and cb['id'] not in ids
    # 6.8 question library: no course filter means all authorized courses, never all institution courses.
    inst_bank=client.get('/api/question-bank',headers=hi).json()
    assert {x['id'] for x in inst_bank} == {bank_a['id']}
    assert client.get('/api/question-bank',headers=hi,params={'course_id':cb['id']}).json() == []
    assert {x['id'] for x in client.get('/api/question-bank',headers=hi,params={'program_id':pa['id']}).json()} == {bank_a['id']}
    assert client.get('/api/users',headers=hi).status_code==403
    # Instructor can operate their exam but cannot alter academic master data.
    assert client.patch(f"/api/courses/{ca['id']}",headers=hi,json={'name':'Yetkisiz Ders Değişikliği'}).status_code==403

    good=client.post('/api/exams',headers=hi,json={'course_id':ca['id'],'title':'RBAC Instructor Exam','exam_type':'Quiz','exam_date':'2032-12-01','duration_minutes':30,'instructions':'','sync_students':False})
    assert good.status_code==201,good.text
    denied=client.post('/api/exams',headers=hi,json={'course_id':cb['id'],'title':'Yasak','exam_type':'Quiz','exam_date':'2032-12-01','duration_minutes':30,'instructions':'','sync_students':False})
    assert denied.status_code==403,denied.text
    assert client.post('/api/accreditation/profiles',headers=hi,json={'code':'NO','name':'Yasak','version':'1','required_general_evidence_kinds':[],'required_representative_evidence_kinds':[],'requires_representatives':False,'requires_improvement_for_gaps':False}).status_code==403

    # Program head can manage assigned program, not another program.
    ok_course=client.post('/api/courses',headers=hh,json={'program_id':pa['id'],'code':'RB 653','name':'Başkan Dersi','academic_year':'2032-2033','term':'Güz','instructor_email':'','instructor_name':''})
    assert ok_course.status_code==201,ok_course.text
    no_course=client.post('/api/courses',headers=hh,json={'program_id':pb['id'],'code':'RB 654','name':'Yasak Dersi','academic_year':'2032-2033','term':'Güz','instructor_email':'','instructor_name':''})
    assert no_course.status_code==403,no_course.text

    # Quality is globally read-only for exam content but can manage accreditation profiles.
    assert client.get('/api/courses',headers=hq).status_code==200
    assert client.patch(f"/api/exams/{good.json()['id']}",headers=hq,json={'title':'Kalite değiştirmemeli'}).status_code==403
    prof=client.post('/api/accreditation/profiles',headers=hq,json={'code':'Q65','name':'Kalite Profili','version':'1','required_general_evidence_kinds':[],'required_representative_evidence_kinds':[],'requires_representatives':False,'requires_improvement_for_gaps':False})
    assert prof.status_code==201,prof.text

    logs=client.get('/api/audit-logs',headers=hq,params={'limit':500}).json()
    actor_logs=[x for x in logs if x.get('actor_email')=='inst65@dogus.edu.tr' and x.get('entity_type')=='exam' and x.get('action')=='create']
    assert actor_logs and 'instructor' in actor_logs[0]['actor_roles']


def test_65_auth_config_and_offline_entra_v2_validation(monkeypatch):
    from types import SimpleNamespace
    from datetime import datetime, timedelta, timezone
    from cryptography.hazmat.primitives.asymmetric import rsa
    import jwt as pyjwt
    import app.authz as authz

    cfg=client.get('/api/auth/config').json()
    assert cfg['auth_required'] is False and cfg['auth_provider']=='pilot'
    assert cfg['entra']['mode']=='single-tenant-v2-access-token'

    tenant='11111111-2222-3333-4444-555555555555'
    audience='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
    fake_settings=SimpleNamespace(
        entra_tenant_id=tenant, entra_audience=audience, entra_client_id=audience,
        entra_auto_link_by_email=False, auth_required=True, auth_provider='entra',
        pilot_admin_email='pilot-admin@local', app_env='pilot'
    )
    monkeypatch.setattr(authz,'settings',fake_settings)
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    now=datetime.now(timezone.utc)
    claims={'aud':audience,'iss':f'https://login.microsoftonline.com/{tenant}/v2.0','iat':now,'exp':now+timedelta(minutes=5),'tid':tenant,'oid':'object-65','ver':'2.0','preferred_username':'user@dogus.edu.tr'}
    token=pyjwt.encode(claims,key,algorithm='RS256',headers={'kid':'test65'})
    class FakeJWK:
        def __init__(self,*a,**k): pass
        def get_signing_key_from_jwt(self,_token): return SimpleNamespace(key=key.public_key())
    monkeypatch.setattr(authz,'PyJWKClient',FakeJWK)
    decoded=authz.validate_entra_access_token(token)
    assert decoded['oid']=='object-65' and decoded['tid']==tenant


def test_66_security_headers_request_id_diagnostics_and_security_events():
    r = client.get('/api/health', headers={'X-Request-ID':'dou-test-request-660001'})
    assert r.status_code == 200
    assert r.headers['x-request-id'] == 'dou-test-request-660001'
    assert r.headers['x-content-type-options'] == 'nosniff'
    assert r.headers['x-frame-options'] == 'DENY'
    assert "default-src 'self'" in r.headers['content-security-policy']

    diag = client.get('/api/system/diagnostics')
    assert diag.status_code == 200, diag.text
    payload = diag.json()
    assert payload['version'].startswith('6.70')
    assert payload['security']['security_headers'] is True
    assert payload['database_dialect'] == 'sqlite'

    denied = client.get('/api/dashboard', headers={'X-DOU-Pilot-User':'missing66@dogus.edu.tr','X-Request-ID':'dou-auth-denied-660001'})
    assert denied.status_code == 403, denied.text
    assert denied.headers['x-request-id'] == 'dou-auth-denied-660001'
    events = client.get('/api/security/events', params={'event_type':'auth_denied','limit':50})
    assert events.status_code == 200, events.text
    rows = events.json()
    assert any(x['request_id'] == 'dou-auth-denied-660001' and x['event_type'] == 'auth_denied' for x in rows)


def test_66_request_size_guard_rejects_before_endpoint_processing():
    from app.config import settings as cfg
    too_large = (cfg.max_request_mb * 1024 * 1024) + 1
    r = client.post('/api/dashboard', content=b'x', headers={'Content-Length':str(too_large),'X-Request-ID':'dou-large-660001'})
    assert r.status_code == 413, r.text
    assert r.json()['error']['code'] == 'REQUEST_TOO_LARGE'
    assert r.headers['x-request-id'] == 'dou-large-660001'


def test_66_production_security_preflight_contract():
    from dataclasses import replace
    from app.config import settings as cfg
    from app.security import production_security_issues, production_security_warnings

    secure = replace(
        cfg,
        app_env='production',
        database_url='postgresql+psycopg://user:secret@db:5432/dou_assess',
        auth_required=True,
        auth_provider='entra',
        entra_tenant_id='11111111-2222-3333-4444-555555555555',
        entra_client_id='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        entra_audience='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        entra_allowed_client_ids=('bbbbbbbb-1111-2222-3333-cccccccccccc',),
        entra_required_scopes=('Assess.Access',),
        entra_login_scopes=('api://aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/Assess.Access',),
        entra_redirect_uri='https://assess.dogus.edu.tr/',
        entra_auto_link_by_email=False,
        public_hostname='assess.dogus.edu.tr',
        require_https=True,
        trusted_proxy_cidrs=('172.16.0.0/12',),
        rate_limit_enabled=True,
        max_upload_mb=20,
        max_batch_upload_mb=60,
        max_request_mb=64,
    )
    assert production_security_issues(secure) == []
    assert production_security_warnings(secure) == []

    insecure = replace(secure, auth_required=False, public_hostname='', require_https=False, entra_allowed_client_ids=())
    issues = production_security_issues(insecure)
    assert any('AUTH_REQUIRED' in x for x in issues)
    assert any('PUBLIC_HOSTNAME' in x for x in issues)
    assert any('REQUIRE_HTTPS' in x for x in issues)
    assert any('ENTRA_ALLOWED_CLIENT_IDS' in x for x in issues)

    bypass = replace(secure, strict_production_security=False)
    assert any('STRICT_PRODUCTION_SECURITY' in x for x in production_security_issues(bypass))
    bad_proxy = replace(secure, trusted_proxy_cidrs=('not-a-network',))
    assert any('TRUSTED_PROXY_CIDRS' in x for x in production_security_issues(bad_proxy))


def test_66_entra_delegated_actor_and_scope_validation(monkeypatch):
    from types import SimpleNamespace
    from datetime import datetime, timedelta, timezone
    from cryptography.hazmat.primitives.asymmetric import rsa
    import jwt as pyjwt
    from fastapi import HTTPException
    import app.authz as authz

    tenant='66111111-2222-3333-4444-555555555555'
    audience='66aaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
    client_id='66bbbbbb-1111-2222-3333-cccccccccccc'
    fake_settings=SimpleNamespace(
        entra_tenant_id=tenant, entra_audience=audience, entra_client_id=audience,
        entra_auto_link_by_email=False, auth_required=True, auth_provider='entra',
        pilot_admin_email='pilot-admin@local', app_env='production',
        entra_require_delegated_user=True, entra_allowed_client_ids=(client_id,),
        entra_required_scopes=('access_as_user',),
    )
    monkeypatch.setattr(authz,'settings',fake_settings)
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    now=datetime.now(timezone.utc)
    base={'aud':audience,'iss':f'https://login.microsoftonline.com/{tenant}/v2.0','iat':now,'exp':now+timedelta(minutes=5),'tid':tenant,'oid':'object-66','ver':'2.0','preferred_username':'user@dogus.edu.tr','scp':'access_as_user','azp':client_id}
    class FakeJWK:
        def __init__(self,*a,**k): pass
        def get_signing_key_from_jwt(self,_token): return SimpleNamespace(key=key.public_key())
    monkeypatch.setattr(authz,'PyJWKClient',FakeJWK)

    good=pyjwt.encode(base,key,algorithm='RS256',headers={'kid':'test66'})
    assert authz.validate_entra_access_token(good)['oid']=='object-66'

    bad_actor=dict(base);bad_actor['azp']='unauthorized-client'
    bad=pyjwt.encode(bad_actor,key,algorithm='RS256',headers={'kid':'test66'})
    try:
        authz.validate_entra_access_token(bad)
        assert False, 'unauthorized client token should fail'
    except HTTPException as exc:
        assert exc.status_code == 401

    no_scope=dict(base);no_scope['scp']='other_scope'
    bad_scope=pyjwt.encode(no_scope,key,algorithm='RS256',headers={'kid':'test66'})
    try:
        authz.validate_entra_access_token(bad_scope)
        assert False, 'missing API scope should fail'
    except HTTPException as exc:
        assert exc.status_code == 403


def test_661_outcome_matrix_upsert_and_exam_mapping_context():
    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    data = client.get(f"/api/courses/{course['id']}/outcomes").json()
    lo = next(x for x in data['learning_outcomes'] if x['code'] == 'Ö1')
    po = next(x for x in data['program_outcomes'] if x['code'] == 'PÇ1')
    original = next(x for x in data['mappings'] if x['learning_outcome_id'] == lo['id'] and x['program_outcome_id'] == po['id'])['contribution']

    r = client.put('/api/outcome-mappings', json={
        'learning_outcome_id': lo['id'], 'program_outcome_id': po['id'], 'contribution': 3,
    })
    assert r.status_code == 200, r.text
    assert r.json()['contribution'] == 3
    changed = client.get(f"/api/courses/{course['id']}/outcomes").json()
    assert next(x for x in changed['mappings'] if x['learning_outcome_id'] == lo['id'] and x['program_outcome_id'] == po['id'])['contribution'] == 3

    r = client.put('/api/outcome-mappings', json={
        'learning_outcome_id': lo['id'], 'program_outcome_id': po['id'], 'contribution': 0,
    })
    assert r.status_code == 422, r.text
    unchanged = client.get(f"/api/courses/{course['id']}/outcomes").json()
    assert next(x for x in unchanged['mappings'] if x['learning_outcome_id'] == lo['id'] and x['program_outcome_id'] == po['id'])['contribution'] == 3

    # Restore the live curriculum mapping so later/manual work sees the original source data.
    assert client.put('/api/outcome-mappings', json={
        'learning_outcome_id': lo['id'], 'program_outcome_id': po['id'], 'contribution': original,
    }).status_code == 200

    exam = post('/api/exams', {
        'course_id': course['id'], 'title': '6.6.1 UX Mapping Snapshot', 'exam_type': 'Final',
        'exam_date': '2026-12-20', 'duration_minutes': 50, 'instructions': '', 'sync_students': True,
    })
    detail = client.get(f"/api/exams/{exam['id']}").json()
    assert detail['outcome_mappings']
    mp = next(x for x in detail['outcome_mappings'] if x['learning_outcome_code'] == 'Ö1' and x['program_outcome_code'] == 'PÇ1')
    assert mp['contribution'] == original

    # Draft wizard can explicitly refresh its immutable outcome snapshot before questions exist.
    alternate = 4 if original != 4 else 5
    assert client.put('/api/outcome-mappings', json={
        'learning_outcome_id': lo['id'], 'program_outcome_id': po['id'], 'contribution': alternate,
    }).status_code == 200
    refreshed = client.post(f"/api/exams/{exam['id']}/refresh-outcome-snapshot", json={})
    assert refreshed.status_code == 200, refreshed.text
    mp2 = next(x for x in refreshed.json()['outcome_mappings'] if x['learning_outcome_code'] == 'Ö1' and x['program_outcome_code'] == 'PÇ1')
    assert mp2['contribution'] == alternate

    # Restore live curriculum and refresh once more so test data remains canonical.
    assert client.put('/api/outcome-mappings', json={
        'learning_outcome_id': lo['id'], 'program_outcome_id': po['id'], 'contribution': original,
    }).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/refresh-outcome-snapshot", json={}).status_code == 200

    q = post(f"/api/exams/{exam['id']}/questions", {
        'order_no': 1, 'question_type': 'mcq', 'text': 'UX snapshot kilit testi', 'points': 100,
        'correct_answer': 'A', 'choices': {'A': 'Doğru', 'B': 'Yanlış'}, 'learning_outcome_code': 'Ö1',
    })
    assert q['id'] > 0
    blocked = client.post(f"/api/exams/{exam['id']}/refresh-outcome-snapshot", json={})
    assert blocked.status_code == 409



def test_610_scan_review_confidence_reject_and_live_session_counts():
    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    exam = post('/api/exams', {
        'course_id': course['id'], 'title':'6.10 Review Station', 'exam_type':'Final',
        'exam_date':'2027-01-10', 'duration_minutes':50, 'instructions':'', 'sync_students':True,
    })
    with SessionLocal() as db:
        session = m.ScanSession(exam_id=exam['id'], source_name='ambiguous.pdf', source_sha256='610' * 21 + 'x', status='completed_with_review', page_count=1, review_count=1)
        db.add(session); db.flush()
        item = m.ScanItem(
            session_id=session.id, exam_id=exam['id'], page_no=1, status='review', booklet='A',
            student_no_detected=None, answers={'1': None},
            diagnostics={'1': {'A': .32, 'B': .30, 'C': .08, 'D': .06, 'E': .05}},
            issue_summary=[{'code':'AMBIGUOUS_MARK','question_no':1,'message':'1. soruda belirsiz işaret var'}],
        )
        db.add(item); db.flush()
        db.add(m.ScanReview(scan_item_id=item.id, exam_id=exam['id'], reason='Belirsiz işaret'))
        db.commit(); item_id=item.id; session_id=session.id

    rows = client.get(f"/api/exams/{exam['id']}/scan-reviews").json()
    row = next(x for x in rows if x['scan_item_id'] == item_id)
    assert row['issue_codes'] == ['AMBIGUOUS_MARK']
    assert row['attention_questions'] == [1]
    assert row['confidence_percent'] < 50
    assert row['diagnostic_summary'][0]['top_candidates'][0]['letter'] == 'A'

    rejected = client.post(f"/api/scan-items/{item_id}/resolve", json={'action':'reject','answers':{},'note':'Fiziksel form doğrulanamadı'})
    assert rejected.status_code == 200, rejected.text
    payload = rejected.json()
    assert payload['status'] == 'rejected'
    assert payload['session']['review_count'] == 0
    assert payload['session']['skipped_count'] == 1
    detail = client.get(f"/api/scan-sessions/{session_id}").json()
    assert detail['status'] == 'completed' and detail['items'][0]['status'] == 'rejected'



def test_612_academic_period_lock_obs_bridge_and_pilot_status():
    # Corporate-pilot period lock must be enforced server-side, not only in the UI.
    program = post('/api/programs', {'code':'CYB612','name':'6.12 Siber Pilot','faculty':'MYO','department':'Bilgisayar Teknolojileri'})
    period = post('/api/academic-periods', {
        'academic_year':'2027-2028','term':'Güz','title':'2027-2028 Güz Kurumsal Pilot',
        'starts_on':'2027-09-15','ends_on':'2028-01-30',
    })
    assert period['status'] == 'planned'
    course = post('/api/courses', {
        'program_id':program['id'],'code':'SEC 612','name':'Kurumsal Pilot Test Dersi',
        'academic_year':'2027-2028','term':'Güz','instructor_email':'pilot612@dogus.edu.tr','instructor_name':'Pilot Öğretim Elemanı',
    })
    exam = post('/api/exams', {
        'course_id':course['id'],'title':'Kilit Öncesi Taslak','exam_type':'Quiz','exam_date':'2027-10-10',
        'duration_minutes':20,'instructions':'','sync_students':False,
    })
    blocked_lock = client.post(f"/api/academic-periods/{period['id']}/status", json={'status':'locked'})
    assert blocked_lock.status_code == 409, blocked_lock.text
    assert client.delete(f"/api/exams/{exam['id']}").status_code == 200
    locked = client.post(f"/api/academic-periods/{period['id']}/status", json={'status':'locked'})
    assert locked.status_code == 200, locked.text
    assert locked.json()['status'] == 'locked' and locked.json()['locked_at']

    blocked_exam = client.post('/api/exams', json={
        'course_id':course['id'],'title':'Kilit Sonrası','exam_type':'Quiz','exam_date':'2027-11-01',
        'duration_minutes':20,'instructions':'','sync_students':False,
    })
    assert blocked_exam.status_code == 409, blocked_exam.text
    blocked_bank = client.post('/api/question-bank', json={
        'course_id':course['id'],'question_type':'classic','text':'Kilitli dönemde yazılamaz','default_points':10,
        'answer_lines':5,'tags':['lock']
    })
    assert blocked_bank.status_code == 409, blocked_bank.text

    reopened = client.post(f"/api/academic-periods/{period['id']}/status", json={'status':'planned'})
    assert reopened.status_code == 200 and reopened.json()['locked_at'] is None
    assert client.post('/api/question-bank', json={
        'course_id':course['id'],'question_type':'classic','text':'Kilit açıldıktan sonra yazılabilir','default_points':10,
        'answer_lines':5,'tags':['lock']
    }).status_code == 201

    # OBS bridge reuses the atomic workbook contract and leaves a durable sync history.
    wb = make_workbook(valid=True)
    validation = client.post('/api/integrations/obs/workbook/validate', files={'file':('obs-612.xlsx',wb,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert validation.status_code == 200, validation.text
    assert validation.json()['ok'] is True and validation.json()['instructor_count'] == 1
    sync = client.post('/api/integrations/obs/workbook/sync', files={'file':('obs-612.xlsx',wb,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert sync.status_code == 200, sync.text
    assert sync.json()['summary']['created_roles'] >= 0
    runs = client.get('/api/integrations/sync-runs').json()
    assert runs and runs[0]['status'] == 'success' and runs[0]['provider'] == 'obs-workbook'
    second_validation = client.post('/api/integrations/obs/workbook/validate', files={'file':('obs-612.xlsx',wb,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert second_validation.json()['duplicate_source'] is True

    with SessionLocal() as db:
        imported_course = db.scalar(select(m.Course).where(m.Course.code == 'BLP 276'))
        assert imported_course.external_source == 'obs-workbook'
        assert db.scalar(select(m.AcademicPeriod).where(m.AcademicPeriod.academic_year == '2026-2027', m.AcademicPeriod.term == 'Güz')) is not None

    status = client.get('/api/pilot/status')
    assert status.status_code == 200, status.text
    payload = status.json()
    assert payload['last_sync']['status'] == 'success'
    assert payload['programs'] >= 2 and payload['courses'] >= 2
    audits = client.get('/api/audit-logs', params={'action':'obs_sync','limit':20}).json()
    assert audits and audits[0]['entity_type'] == 'integration_sync_run'


def test_612_entra_pkce_public_config_and_csp_contract():
    cfg = client.get('/api/auth/config').json()
    assert cfg['entra']['login_mode'] == 'authorization-code-pkce'
    assert 'login_scopes_configured' in cfg['entra']
    r = client.get('/api/health')
    assert 'https://login.microsoftonline.com' in r.headers['content-security-policy']
    for compose_name in ('docker-compose.yml', 'docker-compose.production.yml'):
        compose = Path(compose_name).read_text(encoding='utf-8')
        assert 'ENTRA_LOGIN_SCOPES:' in compose
        assert 'ENTRA_REDIRECT_URI:' in compose



def test_613_management_quality_heatmap_course_lo_question_drilldown_and_export():
    program = next(x for x in client.get('/api/programs').json() if x['code'] == 'IAT')
    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    exam = post('/api/exams', {
        'course_id': course['id'], 'title':'6.13 Kalite Drilldown', 'exam_type':'Final',
        'exam_date':'2026-12-28', 'duration_minutes':50, 'instructions':'', 'sync_students':True,
    })
    q = post(f"/api/exams/{exam['id']}/questions", {
        'order_no':1, 'question_type':'classic', 'text':'Problemi analiz ederek çözüm adımlarını açıklayın.',
        'points':100, 'answer_lines':8, 'learning_outcome_code':'Ö2','expected_answer':'Problem, neden ve çözüm adımları sistematik biçimde açıklanmalıdır.','bloom_level':'analyze',
        'rubric':{'criteria':[{'id':'problem','label':'Problem analizi','max_points':40,'outcome_codes':['Ö2']},{'id':'solution','label':'Çözüm adımları','max_points':60,'outcome_codes':['Ö2']}]},
    })
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'ready'}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'grading'}).status_code == 200
    students = client.get(f"/api/exams/{exam['id']}/students").json()
    assert len(students) == 2
    assert client.post(f"/api/exams/{exam['id']}/students/{students[0]['id']}/responses", json={'responses':[{'question_id':q['id'],'answer_text':'x','rubric_scores':{'problem':40,'solution':60}}]}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/students/{students[1]['id']}/responses", json={'responses':[{'question_id':q['id'],'answer_text':'x','rubric_scores':{'problem':0,'solution':0}}]}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'approved'}).status_code == 200

    r = client.get('/api/quality/dashboard', params={'academic_year':'2026-2027','term':'Güz','program_id':program['id']})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d['summary']['program_count'] == 1
    assert d['summary']['official_exam_count'] >= 1
    assert 'PÇ2' in d['program_outcome_codes']
    prog = d['programs'][0]
    assert prog['program_code'] == 'IAT'
    assert prog['learning_outcome_achievement_percent'] < 100
    risk = next(x for x in d['risk_courses'] if x['course_id'] == course['id'])
    assert risk['risk_level'] in ('critical','watch') and risk['gap_count'] >= 1

    drill = client.get(f"/api/quality/courses/{course['id']}/drilldown")
    assert drill.status_code == 200, drill.text
    detail = drill.json()
    lo = next(x for x in detail['learning_outcomes'] if x['code'] == 'Ö2')
    assert lo['attainment_percent'] < lo['target_percent']
    question = next(x for x in detail['questions'] if x['question_id'] == q['id'])
    assert question['learning_outcome_code'] == 'Ö2'
    assert question['status'] == 'needs_improvement'
    assert question['gap_points'] > 0

    xlsx = client.get('/api/quality/dashboard.xlsx', params={'academic_year':'2026-2027','term':'Güz','program_id':program['id']})
    assert xlsx.status_code == 200, xlsx.text
    wb = load_workbook(BytesIO(xlsx.content), data_only=True)
    assert {'Yonetici_Ozeti','Program_PC_Heatmap','Riskli_Dersler','Donem_Trendi'} <= set(wb.sheetnames)

    # Management dashboard must obey the same academic scope rules as the rest of the system.
    head = post('/api/users', {'email':'quality-head-613@local','display_name':'6.13 Program Başkanı','auth_source':'pilot','is_active':True})
    role = client.post(f"/api/users/{head['id']}/roles", json={'role':'program_head','program_id':program['id']})
    assert role.status_code == 201, role.text
    hh = {'X-DOU-Pilot-User':'quality-head-613@local'}
    scoped = client.get('/api/quality/dashboard', headers=hh, params={'academic_year':'2026-2027','term':'Güz'})
    assert scoped.status_code == 200 and {x['program_id'] for x in scoped.json()['programs']} == {program['id']}
    outside = next(x for x in client.get('/api/programs').json() if x['id'] != program['id'])
    assert client.get('/api/quality/dashboard', headers=hh, params={'program_id':outside['id']}).status_code == 403



def test_614_pilot_readiness_uat_issues_performance_and_ops_contract():
    ready = client.get('/api/pilot/readiness')
    assert ready.status_code == 200, ready.text
    payload = ready.json()
    assert payload['version'].startswith('6.70')
    assert 0 <= payload['score'] <= 100
    keys = {x['key'] for x in payload['checks']}
    assert {'database','admin','period','programs','courses','students','backup','restore'} <= keys

    issues = client.get('/api/pilot/issues')
    assert issues.status_code == 200, issues.text
    assert isinstance(issues.json(), list)

    perf = client.get('/api/pilot/performance')
    assert perf.status_code == 200, perf.text
    p = perf.json()
    assert p['status'] == 'ok'
    assert {'program_count','course_count','student_count','exam_count','response_count'} <= set(p['counts'])

    run = client.post('/api/pilot/uat/run')
    assert run.status_code == 201, run.text
    u = run.json()
    assert u['status'] in {'passed','warning','failed'}
    assert 0 <= u['score'] <= 100
    assert len(u['checks']) >= 7

    history = client.get('/api/pilot/uat/runs')
    assert history.status_code == 200, history.text
    assert history.json() and history.json()[0]['id'] == u['id']


def test_615_final_ux_feedback_demo_scenario_and_dashboard_contract():
    dash = client.get('/api/dashboard')
    assert dash.status_code == 200, dash.text
    d = dash.json()
    assert {'bank_questions','open_reviews','open_improvements','official_exams','feedback_open','roles'} <= set(d)

    fb = client.post('/api/feedback', json={'category':'usability','rating':4,'page':'Soru Havuzu','message':'Filtreler anlaşılır; toplu seçim akışı pilotta test edildi.'})
    assert fb.status_code == 201, fb.text
    feedback_id = fb.json()['id']
    rows = client.get('/api/feedback').json()
    assert any(x['id'] == feedback_id for x in rows)
    resolved = client.patch(f'/api/feedback/{feedback_id}', json={'status':'resolved','resolution_note':'Pilot kararına alındı.'})
    assert resolved.status_code == 200 and resolved.json()['status'] == 'resolved'

    demo = client.post('/api/pilot/demo-scenario')
    assert demo.status_code == 201, demo.text
    payload = demo.json()
    assert payload['program_id'] and payload['course_id']
    if payload.get('created'):
        assert payload['student_count'] == 30 and payload['question_count'] == 10
        assert payload['draft_exam_id'] != payload['completed_exam_id']
    assert any(x['code'] == 'DEMO-BP' for x in client.get('/api/programs').json())
    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'DEMO-PY101')
    assert len([x for x in client.get('/api/question-bank', params={'course_id':course['id']}).json() if x['is_active']]) == 10
    demo_again = client.post('/api/pilot/demo-scenario')
    assert demo_again.status_code == 201 and demo_again.json()['created'] is False

    ih = {'X-DOU-Pilot-User':'demo-ogretim@local'}
    own = client.post('/api/feedback', headers=ih, json={'category':'exam','rating':5,'page':'Sınav Hazırla','message':'Öğretim elemanı pilot notu.'})
    assert own.status_code == 201, own.text
    own_rows = client.get('/api/feedback', headers=ih)
    assert own_rows.status_code == 200 and own_rows.json()
    assert all(x['created_by'] == 'demo-ogretim@local' for x in own_rows.json())
    assert client.patch(f"/api/feedback/{own.json()['id']}", headers=ih, json={'status':'resolved'}).status_code == 403


def test_616_rate_limit_defense_in_depth(monkeypatch):
    from dataclasses import replace
    import app.security as sec
    from app.config import settings as cfg
    sec.reset_rate_limiter_for_tests()
    monkeypatch.setattr(sec, 'settings', replace(cfg, rate_limit_enabled=True, api_rate_limit_per_minute=2, upload_rate_limit_per_minute=1))
    r1 = client.get('/api/dashboard', headers={'X-Request-ID':'rate-616-test-0001'})
    r2 = client.get('/api/dashboard', headers={'X-Request-ID':'rate-616-test-0002'})
    r3 = client.get('/api/dashboard', headers={'X-Request-ID':'rate-616-test-0003'})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r3.status_code == 429, r3.text
    assert r3.json()['error']['code'] == 'RATE_LIMITED'
    assert int(r3.headers['retry-after']) >= 1
    sec.reset_rate_limiter_for_tests()


def test_616_upload_container_and_document_guards(monkeypatch):
    from dataclasses import replace
    import zipfile
    from app.config import settings as cfg
    import app.security as sec

    # A normal workbook remains accepted by the safe container guard.
    sec.validate_xlsx_container(make_workbook(valid=True))

    # A tiny compressed XLSX-shaped bomb is rejected by its expanded size.
    monkeypatch.setattr(sec, 'settings', replace(cfg, max_xlsx_uncompressed_mb=1, max_xlsx_members=5000))
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<Types/>')
        z.writestr('xl/worksheets/sheet1.xml', b'0' * (2 * 1024 * 1024))
    try:
        sec.validate_xlsx_container(buf.getvalue())
        assert False, 'oversized expanded XLSX must fail'
    except Exception as exc:
        assert getattr(exc, 'status_code', None) == 413

    # Structural PDF validation rejects the old fake-header-only fixture.
    try:
        sec.validate_pdf_payload(b'%PDF-1.4\n%%EOF', purpose='Test PDF')
        assert False, 'truncated PDF must fail'
    except Exception as exc:
        assert getattr(exc, 'status_code', None) == 400


def test_616_cached_jwks_client_reused(monkeypatch):
    from types import SimpleNamespace
    import app.authz as authz
    calls = {'init': 0}
    class FakeJWKClient:
        def __init__(self, *args, **kwargs):
            calls['init'] += 1
    monkeypatch.setattr(authz, 'PyJWKClient', FakeJWKClient)
    monkeypatch.setattr(authz, '_jwks_client_cache', None)
    a = authz._jwks_client('https://example.test/keys')
    b = authz._jwks_client('https://example.test/keys')
    assert a is b and calls['init'] == 1


def test_616_security_performance_migration_contract():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    migration = (root / 'migrations/versions/0012_security_performance_indexes.py').read_text(encoding='utf-8')
    assert 'revision = "0012_security_performance_indexes"' in migration
    # PostgreSQL Alembic version_num defaults to VARCHAR(32); the 0012 revision id
    # is 33 chars, so the migration must widen the column before Alembic records it.
    assert '"alembic_version"' in migration
    assert 'type_=sa.String(length=64)' in migration
    assert 'bind.dialect.name == "postgresql"' in migration
    for token in ['ix_exams_course_status_date','ix_question_bank_course_active_type','ix_scan_reviews_exam_status','ix_audit_logs_entity']:
        assert token in migration
    production = (root / 'docker-compose.production.yml').read_text(encoding='utf-8')
    nginx = (root / 'nginx/production.conf').read_text(encoding='utf-8')
    assert '--workers", "2"' in production
    assert '--no-proxy-headers' in production and '--forwarded-allow-ips' not in production
    assert 'read_only: true' in production and 'no-new-privileges:true' in production and 'cap_drop:' in production
    assert 'RATE_LIMIT_ENABLED: "true"' in production
    assert 'limit_req_status 429' in nginx and 'client_max_body_size 64m' in nginx


def test_6161_multi_outcome_question_mapping_snapshot_analytics_and_bank_filter():
    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    exam = post('/api/exams', {
        'course_id': course['id'], 'title': 'Çoklu ÖÇ Doğrulama', 'exam_type': 'UAT',
        'exam_date': '2026-08-21', 'duration_minutes': 30, 'instructions': 'Multi ÖÇ', 'sync_students': True,
    })
    assert {'Ö1','Ö2'} <= {x['code'] for x in exam['learning_outcomes']}

    q = post(f"/api/exams/{exam['id']}/questions", {
        'order_no': 1, 'question_type': 'mcq', 'text': 'Birden fazla kazanımı ölçen soru',
        'points': 100, 'correct_answer': 'A', 'choices': {'A':'Doğru','B':'Yanlış'},
        'learning_outcome_codes': ['Ö1','Ö2'],
    })
    assert q['learning_outcome_code'] == 'Ö1'
    assert q['learning_outcome_codes'] == ['Ö1','Ö2']

    detail = client.get(f"/api/exams/{exam['id']}").json()
    dq = next(x for x in detail['questions'] if x['id'] == q['id'])
    assert dq['learning_outcome_codes'] == ['Ö1','Ö2']

    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'ready'}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'grading'}).status_code == 200
    students = client.get(f"/api/exams/{exam['id']}/students").json()
    for student in students:
        post(f"/api/exams/{exam['id']}/students/{student['id']}/responses", {
            'responses':[{'question_id':q['id'],'answer_text':'A'}]
        })
    analytics = client.get(f"/api/exams/{exam['id']}/analytics").json()
    los = {x['code']:x for x in analytics['learning_outcomes']}
    assert los['Ö1']['question_count'] == 1
    assert los['Ö2']['question_count'] == 1
    assert los['Ö1']['attainment_percent'] == 100
    assert los['Ö2']['attainment_percent'] == 100

    metadata = client.get(f"/api/exams/{exam['id']}/paper-metadata?booklet=A").json()
    mq = next(x for x in metadata['question_order'] if x['question_id'] == q['id'])
    assert mq['learning_outcome_codes'] == ['Ö1','Ö2']

    bank = post('/api/question-bank', {
        'course_id':course['id'], 'question_type':'classic', 'text':'Çoklu ÖÇ havuz sorusu 6161',
        'default_points':20, 'answer_lines':5, 'learning_outcome_codes':['Ö1','Ö2'], 'tags':['multi-oc']
    })
    assert bank['learning_outcome_codes'] == ['Ö1','Ö2']
    by_o2 = client.get('/api/question-bank', params={'course_id':course['id'],'learning_outcome_code':'Ö2'}).json()
    assert any(x['id'] == bank['id'] and x['learning_outcome_codes'] == ['Ö1','Ö2'] for x in by_o2)



def test_617_final_exam_workspace_and_outcome_center_contract():
    program = post('/api/programs', {'code':'F17','name':'6.17 Final Program','faculty':'MYO','department':'Final UX'})
    course = post('/api/courses', {'program_id':program['id'],'code':'F17-101','name':'Final Sınav Tasarımı','academic_year':'2027-2028','term':'Güz','instructor_email':'final617@dogus.edu.tr','instructor_name':'Final Öğretim Elemanı'})
    student = post('/api/students', {'program_id':program['id'],'student_no':'6170001','full_name':'Final Öğrenci','class_name':'1'})
    enr = client.post(f"/api/courses/{course['id']}/enrollments/bulk", json={'student_ids':[student['id']]})
    assert enr.status_code == 200, enr.text
    lo1 = post(f"/api/courses/{course['id']}/learning-outcomes", {'code':'Ö1','description':'Sınav planlar','target_percent':70})
    lo2 = post(f"/api/courses/{course['id']}/learning-outcomes", {'code':'Ö2','description':'Çıktı analizi yapar','target_percent':65})
    po = post(f"/api/programs/{program['id']}/program-outcomes", {'academic_year':'2027-2028','code':'PÇ1','description':'Ölçme değerlendirme yeterliği'})
    for lo in (lo1, lo2):
        r=client.put('/api/outcome-mappings',json={'learning_outcome_id':lo['id'],'program_outcome_id':po['id'],'contribution':5})
        assert r.status_code == 200, r.text
    summary = client.get(f"/api/courses/{course['id']}/outcome-summary").json()
    assert summary['ready_for_exam_snapshot'] is True
    out = client.get(f"/api/courses/{course['id']}/outcomes").json()
    assert out['program_outcomes'][0]['academic_year'] == '2027-2028'

    exam = post('/api/exams', {
        'course_id':course['id'],'title':'Final 6.17 Sınavı','exam_type':'Final','exam_date':'2027-12-20','start_time':'10:30',
        'location':'D-204','duration_minutes':60,'assessment_weight_percent':45,'booklet_count':2,
        'instructions':'Kimlik bilgilerinizi yazınız.','staff_notes':'Salon 15 dk önce açılacak.','sync_students':True
    })
    assert exam['start_time']=='10:30' and exam['location']=='D-204' and exam['booklet_count']==2
    assert exam['assessment_weight_percent']==45
    q = post(f"/api/exams/{exam['id']}/questions", {'order_no':1,'question_type':'mcq','text':'Birden fazla ÖÇ ölçen soru','points':100,'correct_answer':'A','choices':{'A':'Doğru','B':'Yanlış'},'learning_outcome_codes':['Ö1','Ö2']})
    assert q['learning_outcome_codes'] == ['Ö1','Ö2']
    ws = client.get(f"/api/exams/{exam['id']}/workspace-summary")
    assert ws.status_code == 200, ws.text
    payload=ws.json()
    assert payload['allowed_booklets']==['A','B']
    assert payload['next_action']['code']=='mark_ready'
    assert payload['progress']['students']==1 and payload['progress']['questions']==1
    assert {x['code'] for x in payload['outcome_coverage']}=={'Ö1','Ö2'}
    assert isinstance(payload['recent_activity'],list)

    assert client.get(f"/api/exams/{exam['id']}/paper-metadata", params={'booklet':'C'}).status_code == 400
    assert client.get(f"/api/exams/{exam['id']}/students/{student['id']}/paper.pdf", params={'booklet':'D'}).status_code == 400
    assert client.get(f"/api/exams/{exam['id']}/papers-batch.pdf", params={'booklet_strategy':'invalid'}).status_code == 400

    clone = client.post(f"/api/exams/{exam['id']}/duplicate",json={'title':'Final 6.17 Kopya'})
    assert clone.status_code == 201, clone.text
    copied=clone.json()
    assert copied['status']=='draft' and copied['booklet_count']==2 and copied['location']=='D-204'
    assert len(copied['questions'])==1 and copied['questions'][0]['learning_outcome_codes']==['Ö1','Ö2']


def test_scan_review_openapi_contract_exposes_preview_urls():
    spec = client.get("/openapi.json").json()
    payload = json.dumps(spec, ensure_ascii=False)
    assert "/api/exams/{exam_id}/scan-reviews" in payload
    assert "/api/scan-items/{item_id}/review-preview" in payload
    assert '"preview_url"' in payload
    assert '"raw_preview_url"' in payload


def make_618_academic_workbook() -> bytes:
    wb = Workbook()
    ws = wb.active; ws.title = "Programlar"
    ws.append(["program_code","program_name","faculty","department","external_id"])
    ws.append(["A618","6.18 Analiz Programı","MYO","Analiz Bölümü",""])
    ws = wb.create_sheet("Dersler")
    ws.append(["program_code","course_code","course_name","academic_year","term","instructor_name","instructor_email","external_id"])
    ws.append(["A618","A618-101","Analiz ve Ölçme","2028-2029","Güz","Analiz Hocası","analiz618@dogus.edu.tr",""])
    ws = wb.create_sheet("Ogrenciler")
    ws.append(["program_code","student_no","full_name","class_name","external_id"])
    ws.append(["A618","6180001","Analiz Öğrencisi","1",""])
    ws = wb.create_sheet("Ders_Kayitlari")
    ws.append(["program_code","course_code","academic_year","term","student_no"])
    ws.append(["A618","A618-101","2028-2029","Güz","6180001"])
    ws = wb.create_sheet("OC_PC")
    ws.append(["program_code","course_code","academic_year","term","learning_outcome_code","learning_outcome_description","target","program_outcome_code","program_outcome_description","contribution"])
    ws.append(["A618","A618-101","2028-2029","Güz","Ö1","Veri analiz eder",60,"PÇ1","Analitik düşünür",4])
    ws.append(["A618","A618-101","2028-2029","Güz","Ö2","Sonuç yorumlar",65,"PÇ1","Analitik düşünür",5])
    ws = wb.create_sheet("Sinavlar")
    ws.append(["program_code","course_code","academic_year","term","exam_title","exam_type","exam_date","start_time","location","duration_minutes","assessment_weight_percent","booklet_count","instructions","staff_notes","status","sync_students"])
    ws.append(["A618","A618-101","2028-2029","Güz","6.18 Vize","Vize","2028-11-10","10:00","B-204",50,40,2,"Tek şık işaretleyiniz.","Excel UAT","draft","Evet"])
    ws = wb.create_sheet("Sorular")
    ws.append(["program_code","course_code","academic_year","term","exam_title","order_no","question_type","question_text","points","learning_outcome_codes","choice_A","choice_B","choice_C","choice_D","choice_E","correct_answer","answer_lines","tags","add_to_bank"])
    ws.append(["A618","A618-101","2028-2029","Güz","6.18 Vize",1,"mcq","Analiz sonucu hangisidir?",100,"Ö1,Ö2","Doğru","Yanlış","","","","A",8,"analiz,618","Evet"])
    buf=BytesIO(); wb.save(buf); return buf.getvalue()


def test_618_analysis_center_and_academic_excel_import():
    template = client.get('/api/import/academic-workbook/template')
    assert template.status_code == 200, template.text
    twb = load_workbook(BytesIO(template.content), data_only=True)
    assert {'Kullanim','Programlar','Dersler','Ogrenciler','Ders_Kayitlari','OC_PC','Sinavlar','Sorular'} <= set(twb.sheetnames)

    payload = make_618_academic_workbook()
    validate = client.post('/api/import/academic-workbook/validate', files={'file':('academic-618.xlsx',payload,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert validate.status_code == 200, validate.text
    assert validate.json()['rows']['Sinavlar'] == 1 and validate.json()['rows']['Sorular'] == 1

    imported = client.post('/api/import/academic-workbook', files={'file':('academic-618.xlsx',payload,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert imported.status_code == 200, imported.text
    summary = imported.json()['summary']
    assert summary['programs'] == 1 and summary['courses'] == 1 and summary['students'] == 1
    assert summary['exams'] == 1 and summary['questions'] == 1 and summary['bank_questions'] == 1
    assert summary['exam_students'] == 1

    exams = client.get('/api/exams').json()
    exam = next(x for x in exams if x['title'] == '6.18 Vize')
    detail = client.get(f"/api/exams/{exam['id']}").json()
    assert detail['booklet_count'] == 2 and detail['location'] == 'B-204'
    assert detail['questions'][0]['learning_outcome_codes'] == ['Ö1','Ö2']

    # Re-import while the exam is still draft must update rather than duplicate entities.
    again = client.post('/api/import/academic-workbook', files={'file':('academic-618.xlsx',payload,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert again.status_code == 200, again.text
    assert again.json()['summary']['exams'] == 0
    assert again.json()['summary']['questions'] == 0

    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'ready'}).status_code == 200
    assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'grading'}).status_code == 200
    student = client.get(f"/api/exams/{exam['id']}/students").json()[0]
    qid = detail['questions'][0]['id']
    saved = client.post(f"/api/exams/{exam['id']}/students/{student['id']}/responses", json={'responses':[{'question_id':qid,'answer_text':'A'}]})
    assert saved.status_code == 200, saved.text

    analytics = client.get(f"/api/exams/{exam['id']}/analytics").json()
    assert analytics['student_count'] == 1
    assert analytics['median_score'] == 100 and analytics['standard_deviation'] == 0
    assert analytics['pass_percent'] == 100
    assert len(analytics['score_distribution']) == 10
    assert analytics['question_analysis'][0]['attainment_percent'] == 100
    assert analytics['question_analysis'][0]['learning_outcome_codes'] == ['Ö1','Ö2']
    assert {x['code'] for x in analytics['learning_outcomes']} == {'Ö1','Ö2'}

    student_detail = client.get(f"/api/exams/{exam['id']}/students/{student['exam_student_id']}/analytics")
    assert student_detail.status_code == 200, student_detail.text
    sd = student_detail.json()
    assert sd['score_percent'] == 100
    assert {x['code'] for x in sd['learning_outcomes']} == {'Ö1','Ö2'}
    assert sd['questions'][0]['learning_outcome_codes'] == ['Ö1','Ö2']

    report = client.get(f"/api/exams/{exam['id']}/results.xlsx")
    assert report.status_code == 200, report.text
    rwb = load_workbook(BytesIO(report.content), data_only=True)
    assert {'Soru_Analizi','Not_Dagilimi','OC_Basarisi','PC_Basarisi'} <= set(rwb.sheetnames)



def test_618_instructor_scoped_excel_import_only_existing_authorized_course():
    program = post('/api/programs', {'code':'T618','name':'6.18 Öğretmen Programı','faculty':'MYO','department':'Excel'})
    course = post('/api/courses', {'program_id':program['id'],'code':'T618-101','name':'Excel ile Ders','academic_year':'2029-2030','term':'Güz','instructor_email':'teacher618@dogus.edu.tr','instructor_name':'Excel Hocası'})
    user = post('/api/users', {'email':'teacher618@dogus.edu.tr','display_name':'Excel Hocası','auth_source':'pilot'})
    role = client.post(f"/api/users/{user['id']}/roles", json={'role':'instructor','course_id':course['id']})
    assert role.status_code == 201, role.text

    wb = Workbook()
    ws=wb.active;ws.title='Programlar';ws.append(['program_code','program_name']);ws.append(['T618','6.18 Öğretmen Programı'])
    ws=wb.create_sheet('Dersler');ws.append(['program_code','course_code','course_name','academic_year','term','instructor_name','instructor_email']);ws.append(['T618','T618-101','Excel ile Ders','2029-2030','Güz','Excel Hocası','teacher618@dogus.edu.tr'])
    ws=wb.create_sheet('Ogrenciler');ws.append(['program_code','student_no','full_name']);ws.append(['T618','T6180001','Excel Öğrencisi'])
    ws=wb.create_sheet('Ders_Kayitlari');ws.append(['program_code','course_code','academic_year','term','student_no']);ws.append(['T618','T618-101','2029-2030','Güz','T6180001'])
    ws=wb.create_sheet('OC_PC');ws.append(['program_code','course_code','academic_year','term','learning_outcome_code','learning_outcome_description','target','program_outcome_code','program_outcome_description','contribution']);ws.append(['T618','T618-101','2029-2030','Güz','Ö1','Excel aktarımı yapar',60,'PÇ1','Veri yönetir',4])
    ws=wb.create_sheet('Sinavlar');ws.append(['program_code','course_code','academic_year','term','exam_title','exam_type','booklet_count','status','sync_students']);ws.append(['T618','T618-101','2029-2030','Güz','Öğretmen Excel Vize','Vize',1,'draft','Evet'])
    ws=wb.create_sheet('Sorular');ws.append(['program_code','course_code','academic_year','term','exam_title','order_no','question_type','question_text','points','learning_outcome_codes','choice_A','choice_B','correct_answer','add_to_bank']);ws.append(['T618','T618-101','2029-2030','Güz','Öğretmen Excel Vize',1,'mcq','Excel aktarımı çalışıyor mu?',100,'Ö1','Evet','Hayır','A','Evet'])
    buf=BytesIO();wb.save(buf);payload=buf.getvalue();headers={'X-DOU-Pilot-User':'teacher618@dogus.edu.tr'}
    validated=client.post('/api/import/academic-workbook/validate',headers=headers,files={'file':('teacher618.xlsx',payload,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert validated.status_code==200,validated.text
    assert validated.json()['mode']=='course-scoped'
    imported=client.post('/api/import/academic-workbook',headers=headers,files={'file':('teacher618.xlsx',payload,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert imported.status_code==200,imported.text
    assert imported.json()['mode']=='course-scoped'
    assert imported.json()['summary']['students']==1 and imported.json()['summary']['exams']==1


def make_question_bank_workbook() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Soru_Havuzu"
    ws.append([
        "program_code","course_code","academic_year","term","question_type","question_text","default_points",
        "choice_A","choice_B","choice_C","choice_D","choice_E","correct_answer","answer_lines",
        "learning_outcome_codes","tags","topic","unit","difficulty","bloom_level","author","reviewer","rubric","expected_answer"
    ])
    ws.append(["IAT","BLP 276","2026-2027","Güz","mcq","Excel toplu soru 1",10,"3","4","5","6","","B",8,"Ö1","excel;test","Temel","Ünite 1","easy","remember","Test","","",""])
    ws.append(["IAT","BLP 276","2026-2027","Güz","classic","Excel klasik soru 2",10,"","","","","","",10,"Ö2","excel;klasik","Analiz","Ünite 2","hard","create","Test","","Analiz | 4 | ÖÇ=Ö2; Kod | 4 | ÖÇ=Ö2; Sonuç | 2 | ÖÇ=Ö2","Analiz, kod ve sonuç birlikte açıklanmalıdır."])
    buf = BytesIO(); wb.save(buf); return buf.getvalue()


def test_question_bank_excel_bulk_validate_import_and_duplicate_skip():
    payload = make_question_bank_workbook()
    files = {"file": ("soru-havuzu.xlsx", payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r = client.post('/api/import/question-bank/validate', files=files)
    assert r.status_code == 200, r.text
    assert r.json()['ready'] == 2
    assert r.json()['duplicates'] == 0

    r = client.post('/api/import/question-bank', files={"file": ("soru-havuzu.xlsx", payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 200, r.text
    assert r.json()['summary']['created'] == 2
    assert r.json()['summary']['skipped_duplicates'] == 0

    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    rows = client.get('/api/question-bank', params={'course_id': course['id'], 'q': 'Excel'}).json()
    assert len(rows) == 2
    classic = next(x for x in rows if x['question_type'] == 'classic')
    assert classic['rubric']['criteria'][0]['label'] == 'Analiz'
    assert set(classic['learning_outcome_codes']) == {'Ö2'}

    # Re-importing the exact same questions must be idempotent: skip exact duplicates.
    r = client.post('/api/import/question-bank', files={"file": ("soru-havuzu.xlsx", payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 200, r.text
    assert r.json()['summary']['created'] == 0
    assert r.json()['summary']['skipped_duplicates'] == 2


def test_exam_student_assignment_explicit_selection_replace_flow():
    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    enrolled = client.get(f"/api/courses/{course['id']}/enrollments").json()
    assert len(enrolled) >= 2
    exam = post('/api/exams', {
        'course_id': course['id'], 'title': 'Öğrenci Atama Testi', 'exam_type': 'Quiz',
        'exam_date': '2035-05-10', 'duration_minutes': 30, 'instructions': '', 'sync_students': False,
    })
    assignment = client.get(f"/api/exams/{exam['id']}/student-assignment")
    assert assignment.status_code == 200, assignment.text
    payload = assignment.json()
    assert payload['course_enrollment_count'] == len(enrolled)
    assert payload['assigned_count'] == 0
    assert all(x['assigned'] is False for x in payload['students'])

    first_id = payload['students'][0]['id']
    second_id = payload['students'][1]['id']
    saved = client.put(f"/api/exams/{exam['id']}/students", json={'student_ids':[first_id]})
    assert saved.status_code == 200, saved.text
    assert saved.json()['student_count'] == 1
    rows = client.get(f"/api/exams/{exam['id']}/students").json()
    assert [x['id'] for x in rows] == [first_id]

    saved = client.put(f"/api/exams/{exam['id']}/students", json={'student_ids':[first_id, second_id]})
    assert saved.status_code == 200, saved.text
    assert saved.json()['created'] == 1 and saved.json()['student_count'] == 2

    saved = client.put(f"/api/exams/{exam['id']}/students", json={'student_ids':[second_id]})
    assert saved.status_code == 200, saved.text
    assert saved.json()['removed'] == 1 and saved.json()['student_count'] == 1
    assignment = client.get(f"/api/exams/{exam['id']}/student-assignment").json()
    selected = {x['id'] for x in assignment['students'] if x['assigned']}
    assert selected == {second_id}


def test_622_question_bank_survives_course_year_and_remains_reusable():
    """Institutional bank follows program + course code, not a single yearly course row."""
    base_course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    bank = post('/api/question-bank', {
        'course_id': base_course['id'], 'question_type':'mcq',
        'text':'Kurumsal hafıza sorusu', 'default_points':10,
        'correct_answer':'A', 'choices':{'A':'Doğru','B':'Yanlış'},
        'tags':['kurumsal','gecmis']
    })
    future = post('/api/courses', {
        'program_id': base_course['program_id'], 'code': base_course['code'],
        'name': base_course['name'], 'academic_year':'2027-2028', 'term':base_course['term'],
        'instructor_name':'Yeni Öğretim Elemanı', 'instructor_email':'yeni.hoca@dogus.edu.tr',
        'pass_threshold_percent':50
    })
    rows = client.get('/api/question-bank', params={'course_id': future['id'], 'q':'Kurumsal hafıza'}).json()
    found = next(x for x in rows if x['id'] == bank['id'])
    assert found['is_historical'] is True
    assert found['source_academic_year'] == base_course['academic_year']
    assert found['institutional_scope'] == 'course_lineage'

    exam = post('/api/exams', {
        'course_id': future['id'], 'title':'Yeni Hoca Kurumsal Havuz Sınavı', 'exam_type':'Final',
        'exam_date':'2027-12-20', 'duration_minutes':50, 'instructions':'', 'sync_students':False,
    })
    copied = post(f"/api/exams/{exam['id']}/questions/from-bank", {
        'bank_question_id': bank['id'], 'order_no':1, 'points':100
    })
    assert copied['text'] == 'Kurumsal hafıza sorusu'
    assert copied['bank_question_id'] == bank['id']


def test_623_question_review_lifecycle_and_filter():
    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    bank = post('/api/question-bank', {
        'course_id': course['id'], 'question_type':'mcq', 'text':'6.23 onay akışı sorusu',
        'default_points':10, 'correct_answer':'A', 'choices':{'A':'Doğru','B':'Yanlış'}
    })
    assert bank['review_status'] == 'draft'
    r=client.post(f"/api/question-bank/{bank['id']}/review",json={'status':'review','note':'Kontrol','reviewer':'Kontrolör'})
    assert r.status_code==200 and r.json()['review_status']=='review'
    r=client.post(f"/api/question-bank/{bank['id']}/review",json={'status':'approved','note':'Uygun','reviewer':'Kontrolör'})
    assert r.status_code==200 and r.json()['review_status']=='approved'
    filtered=client.get('/api/question-bank',params={'course_id':course['id'],'review_status':'approved'}).json()
    assert any(x['id']==bank['id'] for x in filtered)
    r=client.post(f"/api/question-bank/{bank['id']}/review",json={'status':'draft'})
    assert r.status_code==400


def test_623_blueprint_validates_question_total_and_bank_coverage():
    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    bank = post('/api/question-bank', {'course_id':course['id'],'question_type':'mcq','text':'Belirtke havuz sorusu','default_points':10,'correct_answer':'A','choices':{'A':'1','B':'2'},'topic':'Fonksiyonlar','difficulty':'medium','bloom_level':'apply'})
    post(f"/api/question-bank/{bank['id']}/review", {'status':'review'})
    post(f"/api/question-bank/{bank['id']}/review", {'status':'approved'})
    bad=client.post('/api/blueprints',json={'course_id':course['id'],'exam_type':'Final','title':'Hatalı','total_questions':2,'total_points':100,'items':[{'topic':'Fonksiyonlar','bloom_level':'apply','difficulty':'medium','question_count':1,'points':10}]})
    assert bad.status_code==400
    bp=post('/api/blueprints',{'course_id':course['id'],'exam_type':'Final','title':'Python Final Belirtkesi','total_questions':1,'total_points':100,'items':[{'topic':'Fonksiyonlar','bloom_level':'apply','difficulty':'medium','question_count':1,'points':100}]})
    assert bp['planned_questions']==1 and bp['coverage'][0]['available']>=1 and bp['ready'] is True
    approved=client.patch(f"/api/blueprints/{bp['id']}/status",json={'status':'approved','approved_by':'Program Başkanı'})
    assert approved.status_code==200 and approved.json()['status']=='approved'


def test_623_revision_question_cannot_be_added_to_exam():
    course = next(x for x in client.get('/api/courses').json() if x['code'] == 'BLP 276')
    bank=post('/api/question-bank',{'course_id':course['id'],'question_type':'mcq','text':'Revizyondaki soru','default_points':10,'correct_answer':'A','choices':{'A':'x','B':'y'}})
    post(f"/api/question-bank/{bank['id']}/review",{'status':'review'})
    post(f"/api/question-bank/{bank['id']}/review",{'status':'revision','note':'Çeldirici geliştirilmeli'})
    exam=post('/api/exams',{'course_id':course['id'],'title':'6.23 Revizyon Kuralı','exam_type':'Final','duration_minutes':50,'instructions':'','sync_students':False})
    r=client.post(f"/api/exams/{exam['id']}/questions/from-bank",json={'bank_question_id':bank['id'],'order_no':1,'points':100})
    assert r.status_code==400
