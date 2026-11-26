from __future__ import annotations
import os, tempfile
from pathlib import Path
from io import BytesIO
TMP=Path(tempfile.mkdtemp(prefix='dou_assess_lifecycle_')); DB=TMP/'validation.db'
os.environ['DATABASE_URL']=f"sqlite+pysqlite:///{DB.as_posix()}"; os.environ['APP_ENV']='pilot'; os.environ['EVIDENCE_STORAGE_PATH']=str(TMP/'evidence')
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from pypdf import PdfReader
from app.db import Base, engine, SessionLocal
from app.main import app
from app import models as m
Base.metadata.create_all(engine); c=TestClient(app)
def post(p,d):
 r=c.post(p,json=d); assert r.status_code in (200,201),(p,r.status_code,r.text); return r.json()
pr=post('/api/programs',{'code':'LC','name':'Lifecycle','faculty':'MYO'})
co=post('/api/courses',{'program_id':pr['id'],'code':'LC101','name':'Lifecycle','academic_year':'2032-2033','term':'Güz','instructor_email':'teacher@dogus.edu.tr','pass_threshold_percent':55})
lo=post(f"/api/courses/{co['id']}/learning-outcomes",{'code':'Ö1','description':'Test','target_percent':60})
st=post('/api/students',{'program_id':pr['id'],'student_no':'LC001','full_name':'Lifecycle Student'})
assert c.post(f"/api/courses/{co['id']}/enrollments/bulk",json={'student_ids':[st['id']]}).status_code==200
bank=post('/api/question-bank',{'course_id':co['id'],'question_type':'mcq','text':'Bank v1','default_points':100,'correct_answer':'A','choices':{'A':'Evet','B':'Hayır'},'learning_outcome_codes':['Ö1'],'topic':'Konu','difficulty':'medium','bloom_level':'understand'})
r=c.patch(f"/api/question-bank/{bank['id']}",json={'text':'Bank v2','reviewer':'Reviewer'}); assert r.status_code==200,r.text; assert r.json()['version_no']==2
exam=post('/api/exams',{'course_id':co['id'],'title':'Revizyon','exam_type':'Quiz','exam_date':'2032-11-01','location':'C-1','assessment_weight_percent':100,'sync_students':True})
q=post(f"/api/exams/{exam['id']}/questions/from-bank",{'bank_question_id':bank['id'],'order_no':1,'points':100})
bank_after=next(x for x in c.get('/api/question-bank',params={'course_id':co['id']}).json() if x['id']==bank['id']); assert bank_after['usage_count']==1 and bank_after['version_no']==2,bank_after
assert c.post(f"/api/exams/{exam['id']}/status",json={'status':'ready'}).status_code==200
assert c.post(f"/api/exams/{exam['id']}/status",json={'status':'grading'}).status_code==200
es=c.get(f"/api/exams/{exam['id']}/students").json()[0]
assert c.post(f"/api/exams/{exam['id']}/students/{es['id']}/responses",json={'responses':[{'question_id':q['id'],'answer_text':'A'}]}).status_code==200
assert c.post(f"/api/exams/{exam['id']}/approval-request",json={'note':'Kontrol'}).status_code==200
rej=c.post(f"/api/exams/{exam['id']}/approval-reject",json={'note':'Düzelt'}); assert rej.status_code==200,rej.text
saved=c.get(f"/api/exams/{exam['id']}").json(); assert saved['status']=='draft' and saved['revision_no']==2,(saved['status'],saved['revision_no'])
with SessionLocal() as db:
 assert (db.scalar(select(func.count()).select_from(m.Response).join(m.ExamStudent, m.Response.exam_student_id == m.ExamStudent.id).where(m.ExamStudent.exam_id==exam['id'])) or 0)==0
# A5 portrait physical output
a5=post('/api/exams',{'course_id':co['id'],'title':'A5','exam_type':'Quiz','exam_date':'2032-11-02','location':'C-2','paper_size':'A5','paper_orientation':'portrait','omr_mode':'embedded','sync_students':True})
post(f"/api/exams/{a5['id']}/questions",{'order_no':1,'question_type':'classic','text':'A5 fiziksel boyut','points':100,'learning_outcome_codes':['Ö1'],'expected_answer':'Geçerli kısa açıklama','bloom_level':'understand','rubric':{'criteria':[{'id':'content','label':'İçerik','max_points':100,'outcome_codes':['Ö1']}]}})
pdf=c.get(f"/api/exams/{a5['id']}/paper.pdf?booklet=A"); assert pdf.status_code==200,pdf.text
reader=PdfReader(BytesIO(pdf.content)); box=reader.pages[0].mediabox; w,h=float(box.width),float(box.height); assert w<h and 415<w<425 and 590<h<600,(w,h)
# invalid rubric must be rejected
bad=c.post(f"/api/exams/{a5['id']}/questions",json={'order_no':2,'question_type':'classic','text':'Bad rubric','points':10,'learning_outcome_codes':['Ö1'],'rubric':{'criteria':[{'id':'x','label':'x','max_points':5}]}}); assert bad.status_code in (400,422),(bad.status_code,bad.text)
print({'bank_version':bank_after['version_no'],'bank_usage':bank_after['usage_count'],'rejected_status':saved['status'],'revision':saved['revision_no'],'responses_after_reject':0,'a5_size':[round(w,3),round(h,3)],'invalid_rubric_status':bad.status_code})
