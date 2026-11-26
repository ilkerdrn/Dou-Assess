from __future__ import annotations
import os, tempfile, json
from pathlib import Path
from io import BytesIO

TMP = Path(tempfile.mkdtemp(prefix='dou_legacy_classic_scan_'))
os.environ['DATABASE_URL'] = f"sqlite+pysqlite:///{(TMP/'legacy.db').as_posix()}"
os.environ['APP_ENV'] = 'pilot'
os.environ['SCAN_STORAGE_PATH'] = str(TMP/'scans')
os.environ['EVIDENCE_STORAGE_PATH'] = str(TMP/'evidence')

from fastapi.testclient import TestClient
from PIL import Image
from app.db import Base, engine
from app.main import app
import app.services.paper as paper

Base.metadata.create_all(engine)
client = TestClient(app)

def post(path, data):
    r = client.post(path, json=data)
    assert r.status_code in (200, 201), (path, r.status_code, r.text)
    return r.json()

program = post('/api/programs', {'code':'LCG','name':'Legacy Classic','faculty':'MYO','department':'Test'})
course = post('/api/courses', {'program_id':program['id'],'code':'LCG101','name':'Legacy Tarama','academic_year':'2032-2033','term':'Güz','instructor_email':'teacher@dogus.edu.tr','instructor_name':'Teacher'})
lo = post(f"/api/courses/{course['id']}/learning-outcomes", {'code':'Ö1','description':'Klasik cevap değerlendirir','target_percent':60})
student = post('/api/students', {'program_id':program['id'],'student_no':'LEG001','full_name':'Legacy Öğrenci','class_name':'1'})
r = client.post(f"/api/courses/{course['id']}/enrollments/bulk", json={'student_ids':[student['id']]}); assert r.status_code == 200, r.text
exam = post('/api/exams', {'course_id':course['id'],'title':'Legacy Klasik','exam_type':'Final','exam_date':'2033-01-10','location':'A-101','duration_minutes':60,'sync_students':True})
rubric = {'criteria':[{'id':'content','label':'İçerik','max_points':6,'outcome_codes':['Ö1']},{'id':'logic','label':'Mantık','max_points':4,'outcome_codes':['Ö1']}]}
q1 = post(f"/api/exams/{exam['id']}/questions", {'order_no':1,'question_type':'classic','text':'Sunucu sorun giderme adımlarını açıklayınız.','points':10,'answer_lines':10,'learning_outcome_codes':['Ö1'],'rubric':rubric,'expected_answer':'Sorun belirtilir, tanılama adımları sistematik açıklanır.','bloom_level':'analyze'})
q2 = post(f"/api/exams/{exam['id']}/questions", {'order_no':2,'question_type':'mcq','text':'DNS ne yapar?','points':90,'choices':{'A':'Ad çözümleme','B':'Disk biçimleme'},'correct_answer':'A','learning_outcome_codes':['Ö1']})
assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'ready'}).status_code == 200
assert client.post(f"/api/exams/{exam['id']}/status", json={'status':'grading'}).status_code == 200

# Reproduce the pre-6.18.4 question-page header: no per-page QR and y starts at h-55.
original_new_question_page = paper._new_question_page
def legacy_new_question_page(c, exam_obj, metadata, page_no):
    paper._begin_logical_page(c, exam_obj)
    w, h = paper.A4
    c.setStrokeColor(paper.colors.HexColor('#D9DDE2')); c.setFillColor(paper.DARK)
    c.setFont('DOU-Bold', 9); c.drawString(32, h - 31, 'DOĞUŞ ÜNİVERSİTESİ')
    c.setFont('DOU-Regular', 7.5)
    c.drawRightString(w - 32, h - 31, f"{getattr(exam_obj,'course_code_snapshot',None) or ''} · {exam_obj.exam_type} · Kitapçık {metadata['booklet']}")
    c.line(32, h - 38, w - 32, h - 38)
    c.setFont('DOU-Regular', 6.5)
    c.drawCentredString(w / 2, 17, f"Sayfa / Page {page_no} · Sınav ID {exam_obj.id} · {metadata['token']}")
    return h - 55

paper._new_question_page = legacy_new_question_page
try:
    generated = paper.build_exam_pdf
    # Endpoint uses the same function object/global module; monkeypatch affects page rendering.
    resp = client.get(f"/api/exams/{exam['id']}/students/{student['id']}/paper.pdf?booklet=A")
    assert resp.status_code == 200, resp.text
    legacy_pdf = resp.content
finally:
    paper._new_question_page = original_new_question_page

scan = client.post(f"/api/exams/{exam['id']}/scans", files={'file':('legacy-student-paper.pdf', legacy_pdf, 'application/pdf')})
assert scan.status_code == 201, scan.text
summary = scan.json()
assert summary['support_count'] >= 1, summary
ctx = client.get(f"/api/exams/{exam['id']}/students/{student['id']}/classic-scans")
assert ctx.status_code == 200, ctx.text
row = next(x for x in ctx.json()['classic_questions'] if x['question_id'] == q1['id'])
assert row['scan'] is not None, row
assert row['scan']['legacy_association'] is True, row['scan']
answer = client.get(row['scan']['answer_preview_url'])
assert answer.status_code == 200, answer.text
image = Image.open(BytesIO(answer.content))
assert image.width > 250 and image.height > 80, image.size
print(json.dumps({'scan_summary':summary,'legacy_scan':row['scan'],'answer_crop_size':image.size}, ensure_ascii=False, indent=2))
