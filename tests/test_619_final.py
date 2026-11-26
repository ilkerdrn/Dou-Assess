from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.main import app

c=TestClient(app)

def post(path,payload):
    r=c.post(path,json=payload); assert r.status_code in (200,201),(path,r.status_code,r.text); return r.json()


def test_619_three_academic_roles_and_excel_catalog():
    bad=c.post('/api/users/1/roles',json={'role':'department_head','scope_department':'X'})
    assert bad.status_code==422
    catalog=c.get('/api/excel-center'); assert catalog.status_code==200,catalog.text
    kinds={x['kind'] for x in catalog.json()['items']}
    assert {'academic','question_bank','exam_students','classic_grades','improvements','users_roles'} <= kinds
    for kind in ['exam_students','classic_grades','improvements','users_roles']:
        r=c.get(f'/api/excel-center/{kind}/template'); assert r.status_code==200,(kind,r.text)
        wb=load_workbook(BytesIO(r.content),data_only=True); assert 'KILAVUZ' in wb.sheetnames


def test_619_attendance_grade_lock_and_classic_appeal():
    pr=post('/api/programs',{'code':'F619','name':'Final 619','faculty':'MYO','department':'Test'})
    co=post('/api/courses',{'program_id':pr['id'],'code':'F619-101','name':'Final test','academic_year':'2035-2036','term':'Güz','instructor_email':'f619@dogus.edu.tr','instructor_name':'Hoca'})
    post(f"/api/courses/{co['id']}/learning-outcomes",{'code':'Ö1','description':'Analiz eder','target_percent':70})
    s1=post('/api/students',{'program_id':pr['id'],'student_no':'F619001','full_name':'Bir','class_name':'1'})
    s2=post('/api/students',{'program_id':pr['id'],'student_no':'F619002','full_name':'İki','class_name':'1'})
    assert c.post(f"/api/courses/{co['id']}/enrollments/bulk",json={'student_ids':[s1['id'],s2['id']]}).status_code==200
    ex=post('/api/exams',{'course_id':co['id'],'title':'Final 619','exam_type':'Final','exam_date':'2036-01-02','location':'A1','duration_minutes':50,'sync_students':True})
    q=post(f"/api/exams/{ex['id']}/questions",{'order_no':1,'question_type':'classic','text':'Analiz','points':100,'learning_outcome_codes':['Ö1'],'expected_answer':'Gerekçeli analiz','bloom_level':'analyze','rubric':{'criteria':[{'id':'a','label':'Analiz','max_points':100,'outcome_codes':['Ö1']}]}})
    assert c.post(f"/api/exams/{ex['id']}/status",json={'status':'ready'}).status_code==200
    assert c.post(f"/api/exams/{ex['id']}/status",json={'status':'grading'}).status_code==200
    assert c.patch(f"/api/exams/{ex['id']}/students/{s2['id']}/attendance",json={'status':'absent','note':'Katılmadı'}).status_code==200
    es=c.get(f"/api/exams/{ex['id']}/students").json(); active=next(x for x in es if x['id']==s1['id'])
    assert c.post(f"/api/exams/{ex['id']}/students/{active['id']}/responses",json={'responses':[{'question_id':q['id'],'answer_text':'cevap','rubric_scores':{'a':80}}]}).status_code==200
    an=c.get(f"/api/exams/{ex['id']}/analytics").json(); assert an['student_count']==1
    lock=c.post(f"/api/exams/{ex['id']}/grade-lock",json={'note':'Puanlama tamamlandı'}); assert lock.status_code==200,lock.text
    blocked=c.post(f"/api/exams/{ex['id']}/students/{active['id']}/responses",json={'responses':[{'question_id':q['id'],'answer_text':'x','rubric_scores':{'a':90}}]}); assert blocked.status_code==409
    appeal=post(f"/api/exams/{ex['id']}/appeals",{'student_id':s1['id'],'question_id':q['id'],'reason':'Rubrik tekrar değerlendirilsin'})
    decided=c.patch(f"/api/appeals/{appeal['id']}",json={'decision':'accepted','decision_note':'Kriter yeniden değerlendirildi','rubric_scores':{'a':90}}); assert decided.status_code==200,decided.text
    saved=c.get(f"/api/exams/{ex['id']}/students/{active['id']}/responses").json()[0]; assert saved['awarded_points']==90 and saved['revision_no']>=2


def test_619_pdca_effectiveness_closure():
    # Reuse a visible exam from preceding test if test order changes, create tiny one.
    exams=c.get('/api/exams').json(); ex=next((x for x in exams if x['title']=='Final 619'),None)
    assert ex
    action=post(f"/api/exams/{ex['id']}/improvements",{'outcome_code':'Ö1','action_text':'Ek uygulama','owner':'Program Başkanı','baseline_percent':55,'target_percent':70})
    bad=c.patch(f"/api/improvements/{action['id']}",json={'status':'done'}); assert bad.status_code==409
    good=c.patch(f"/api/improvements/{action['id']}",json={'status':'done','actual_percent':74,'verification_method':'Sonraki sınav doğrudan ölçümü','effectiveness_status':'effective','closure_note':'Hedef aşıldı'})
    assert good.status_code==200,good.text; assert good.json()['effectiveness_status']=='effective' and good.json()['actual_percent']==74


def test_619_excel_users_roles_import():
    payload=c.get('/api/excel-center/users_roles/template').content
    wb=load_workbook(BytesIO(payload)); ws=wb['Kullanicilar_Roller']; ws.delete_rows(2,1); ws.append(['quality619@dogus.edu.tr','Kalite Müdürü 619','quality','','','','','Evet']); out=BytesIO();wb.save(out)
    files={'file':('users.xlsx',out.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    v=c.post('/api/excel-center/users_roles/validate',files=files); assert v.status_code==200,v.text
    imp=c.post('/api/excel-center/users_roles/import',files=files); assert imp.status_code==200,imp.text
    users=c.get('/api/users').json(); u=next(x for x in users if x['email']=='quality619@dogus.edu.tr'); assert 'quality' in u['role_names']


def test_619_usability_frontend_contract():
    root=Path(__file__).resolve().parents[1]
    html=(root/'app/static/index.html').read_text(encoding='utf-8'); js=(root/'app/static/app.js').read_text(encoding='utf-8')
    assert '? Kılavuz' in html and 'Excel Yükle' in html
    assert 'Öğretim Görevlisi' in html and 'Program Başkanı' in html and 'Kalite Müdürü' in html
    assert 'department_head' not in html and 'faculty_admin' not in html
    assert 'GUIDE_PAGES' in js and '/api/excel-center' in js and 'guidePersona' in js
