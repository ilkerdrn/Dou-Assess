from __future__ import annotations
import os, threading, json, base64, tempfile
from io import BytesIO
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

received=[]
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n=int(self.headers.get('content-length','0')); raw=self.rfile.read(n); received.append(json.loads(raw.decode()))
        self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(b'{"accepted":true}')
    def log_message(self, *args): pass
server=HTTPServer(('127.0.0.1',0),H)
threading.Thread(target=server.serve_forever,daemon=True).start()

TMP=Path(tempfile.mkdtemp(prefix='dou_assess_complete_'))
DB=TMP/'validation.db'
os.environ['DATABASE_URL']=f"sqlite+pysqlite:///{DB.as_posix()}"
os.environ['APP_ENV']='pilot'
os.environ['OBS_RESULTS_ENDPOINT']=f'http://127.0.0.1:{server.server_port}/results'
os.environ['EVIDENCE_STORAGE_PATH']=str(TMP/'evidence')

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader
from openpyxl import load_workbook
from app.db import Base, engine
from app.main import app
Base.metadata.create_all(engine)
client=TestClient(app)

def post(path,data):
    r=client.post(path,json=data); assert r.status_code in (200,201),(path,r.status_code,r.text); return r.json()

program=post('/api/programs',{'code':'VAL','name':'Validation Program','faculty':'MYO','department':'Test'})
course=post('/api/courses',{'program_id':program['id'],'code':'VAL101','name':'Complete Engine','academic_year':'2031-2032','term':'Güz','instructor_email':'teacher@dogus.edu.tr','instructor_name':'Teacher','pass_threshold_percent':65})
lo=post(f"/api/courses/{course['id']}/learning-outcomes",{'code':'Ö1','description':'Ölçer','target_percent':60})
students=[]
for i in range(3): students.append(post('/api/students',{'program_id':program['id'],'student_no':f'VAL00{i+1}','full_name':f'Öğrenci {i+1}','class_name':'1'}))
r=client.post(f"/api/courses/{course['id']}/enrollments/bulk",json={'student_ids':[x['id'] for x in students]}); assert r.status_code==200,r.text

# tiny real PNG data URL
im=Image.new('RGB',(120,60),'white'); buf=BytesIO(); im.save(buf,format='PNG'); img='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()

vize=post('/api/exams',{'course_id':course['id'],'title':'Vize','exam_type':'Vize','exam_date':'2031-11-01','location':'B-101','duration_minutes':45,'assessment_weight_percent':40,'paper_size':'A3','paper_orientation':'landscape','omr_mode':'separate','duplex_print':True,'sync_students':True})
q1=post(f"/api/exams/{vize['id']}/questions",{'order_no':1,'question_type':'mcq','text':'Görselli soru','points':50,'correct_answer':'A','choices':{'A':'Doğru','B':'Yanlış'},'learning_outcome_codes':['Ö1'],'topic':'Temel','unit':'1','difficulty':'medium','bloom_level':'apply','image_data':img})
q2=post(f"/api/exams/{vize['id']}/questions",{'order_no':2,'question_type':'mcq','text':'İkinci soru','points':50,'correct_answer':'A','choices':{'A':'Doğru','B':'Yanlış'},'learning_outcome_codes':['Ö1'],'topic':'Temel','unit':'1','difficulty':'hard','bloom_level':'analyze'})
assert client.post(f"/api/exams/{vize['id']}/status",json={'status':'ready'}).status_code==200
assert client.post(f"/api/exams/{vize['id']}/status",json={'status':'grading'}).status_code==200
rows=client.get(f"/api/exams/{vize['id']}/students").json()
answers=[('A','A'),('A','B'),('B','B')]
for st,ans in zip(rows,answers):
    r=client.post(f"/api/exams/{vize['id']}/students/{st['id']}/responses",json={'responses':[{'question_id':q1['id'],'answer_text':ans[0]},{'question_id':q2['id'],'answer_text':ans[1]}]}); assert r.status_code==200,r.text
assert client.post(f"/api/exams/{vize['id']}/approval-request",json={'note':'Vize onayı'}).status_code==200
assert client.post(f"/api/exams/{vize['id']}/status",json={'status':'approved','note':'Onay'}).status_code==200
an=client.get(f"/api/exams/{vize['id']}/analytics").json(); assert 'cronbach_alpha' in an['reliability'] and 'kr20' in an['reliability']; assert all('discrimination_index' in q for q in an['question_analysis'])

paper=client.get(f"/api/exams/{vize['id']}/paper.pdf?booklet=A"); assert paper.status_code==200,paper.text
reader=PdfReader(BytesIO(paper.content)); box=reader.pages[0].mediabox; assert float(box.width)>float(box.height), (box.width,box.height); assert len(reader.pages)%2==0, len(reader.pages)

final=post('/api/exams',{'course_id':course['id'],'title':'Final','exam_type':'Final','exam_date':'2032-01-10','location':'B-102','duration_minutes':60,'assessment_weight_percent':60,'paper_size':'A4','paper_orientation':'portrait','omr_mode':'embedded','sync_students':True})
rubric={'criteria':[{'id':'alg','label':'Algoritma','max_points':60,'outcome_codes':['Ö1']},{'id':'out','label':'Çıktı','max_points':40,'outcome_codes':['Ö1']}]}
qf=post(f"/api/exams/{final['id']}/questions",{'order_no':1,'question_type':'classic','text':'Klasik rubrikli soru','points':100,'learning_outcome_codes':['Ö1'],'rubric':rubric,'bloom_level':'create','expected_answer':'Algoritma doğru kurulmalı ve beklenen çıktı açıklanmalıdır.'})
assert client.post(f"/api/exams/{final['id']}/status",json={'status':'ready'}).status_code==200
assert client.post(f"/api/exams/{final['id']}/status",json={'status':'grading'}).status_code==200
rowsf=client.get(f"/api/exams/{final['id']}/students").json(); scores=[{'alg':30,'out':20},{'alg':60,'out':40},{'alg':0,'out':0}]
for st,sc in zip(rowsf,scores):
    r=client.post(f"/api/exams/{final['id']}/students/{st['id']}/responses",json={'responses':[{'question_id':qf['id'],'answer_text':'yanıt','rubric_scores':sc}]}); assert r.status_code==200,r.text
assert client.post(f"/api/exams/{final['id']}/approval-request",json={'note':'Final onayı'}).status_code==200
assert client.post(f"/api/exams/{final['id']}/status",json={'status':'approved'}).status_code==200

gb=client.get(f"/api/courses/{course['id']}/gradebook").json(); assert gb['weights_valid'] is True and gb['assessment_weight_total']==100
vals={x['student_no']:x['final_grade'] for x in gb['students']}; assert vals['VAL001']==70 and vals['VAL002']==80 and vals['VAL003']==0,vals
xlsx=client.get(f"/api/courses/{course['id']}/gradebook.xlsx"); assert xlsx.status_code==200; wb=load_workbook(BytesIO(xlsx.content),data_only=True); assert {'Ders_Notlari','Agirlikli_OC','Agirlikli_PC','Ozet'}-set(wb.sheetnames)==set()
obsxlsx=client.get(f"/api/courses/{course['id']}/obs-results.xlsx"); assert obsxlsx.status_code==200
push=client.post(f"/api/courses/{course['id']}/obs-results/push",json={}); assert push.status_code==200,push.text; assert received and len(received[-1]['results'])==3

# evidence version, preview, download
png=buf.getvalue()
for n in range(2):
    rr=client.post(f"/api/exams/{final['id']}/evidence",data={'kind':'graded-paper','student_id':str(students[0]['id']),'category':'assessment','description':f'sürüm {n+1}'},files={'file':('kanit.png',png,'image/png')}); assert rr.status_code==201,rr.text
elist=client.get(f"/api/exams/{final['id']}/evidence").json(); assert {x['version_no'] for x in elist}=={1,2}; eid=elist[0]['id']; assert client.get(f'/api/evidence/{eid}/preview').status_code==200

anon=client.post(f"/api/students/{students[2]['id']}/anonymize",json={'confirm':True,'reason':'validation'}); assert anon.status_code==200,anon.text; assert anon.json()['student']['student_no'].startswith('ANON-')

report=client.get(f"/api/exams/{vize['id']}/results.xlsx"); assert report.status_code==200; rwb=load_workbook(BytesIO(report.content),data_only=True); headers=[c.value for c in rwb['Soru_Analizi'][1]]; assert 'Ayırt Edicilik' in headers and 'Çeldirici Dağılımı' in headers
print(json.dumps({'weighted_grades':vals,'reliability':an['reliability'],'paper_pages':len(reader.pages),'paper_size':[float(box.width),float(box.height)],'obs_push_records':len(received[-1]['results']),'evidence_versions':sorted(x['version_no'] for x in elist),'anonymized':anon.json()['student']['student_no']},ensure_ascii=False,indent=2))
server.shutdown()
