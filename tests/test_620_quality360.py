from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.main import app

c = TestClient(app)


def ensure_program(code: str = "Q620") -> dict:
    rows = c.get("/api/programs").json()
    found = next((x for x in rows if x["code"] == code), None)
    if found:
        return found
    r = c.post("/api/programs", json={"code": code, "name": "Quality 620 Programı", "faculty": "MYO", "department": "Bilgisayar Teknolojileri"})
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_620_catalogs_and_builtin_framework_profiles():
    cat = c.get("/api/catalogs")
    assert cat.status_code == 200, cat.text
    payload = cat.json()
    assert [x["value"] for x in payload["exam_types"]] == [
        "Vize", "Final", "Bütünleme", "Mazeret", "Tek Ders", "Muafiyet", "Kısa Sınav", "Uygulama"
    ]
    assert payload["class_levels"] == ["1. Sınıf", "2. Sınıf", "3. Sınıf", "4. Sınıf"]
    assert payload["terms"] == ["Güz", "Bahar", "Yaz"]

    r = c.get("/api/quality360/frameworks")
    assert r.status_code == 200, r.text
    frameworks = {x["code"]: x for x in r.json()}
    assert len(frameworks["MEDEK-2026"]["criteria"]) == 9
    assert len(frameworks["MEDEK-2028"]["criteria"]) == 8
    assert frameworks["MEDEK-2028"]["transition_from_year"] == 2028
    assert len(frameworks["YOKAK-2026"]["criteria"]) == 14
    assert frameworks["YOKAK-2026"]["thresholds"]["subcriteria_count"] == 46


def test_620_quality360_records_curriculum_dashboard_and_v2_mapping():
    pr = ensure_program("Q620")
    pid = pr["id"]
    curriculum = {
        "program_id": pid, "academic_year": "2026-2027", "term": "Güz", "class_level": "1. Sınıf",
        "course_code": "Q620-ALL", "course_name": "Kalite Tüm Eşikler", "ects": 60,
        "course_category": "Programa / Alana Özgü Mesleki", "is_professional": True, "is_program_specific": True,
        "is_external_stakeholder_supported": True, "is_applied_or_current_tech": True, "quality_status": "implemented", "notes": "",
    }
    r = c.post("/api/quality360/curriculum", json=curriculum); assert r.status_code in (200, 201), r.text
    r = c.post("/api/quality360/stakeholders", json={"program_id":pid,"stakeholder_type":"Sektör Temsilcisi","name":"Sektör Kurulu","organization":"Teknoloji","engagement_type":"Danışma Kurulu","feedback":"Bulut dersi","resulting_action":"Müfredat gündemine alındı","quality_status":"implemented","evidence_ref":""}); assert r.status_code==201,r.text
    r = c.post("/api/quality360/graduates", json={"program_id":pid,"graduate_key":"Q620-MZ-1","full_name":"Mezun","graduation_year":2026,"employment_status":"Çalışıyor - Alanında","employer":"BT AŞ","sector":"BT","job_title":"Uzman","related_field":True,"notes":""}); assert r.status_code in (200,201),r.text
    r = c.post("/api/quality360/faculty", json={"program_id":pid,"title":"Öğr. Gör.","full_name":"Örnek Hoca","email":"q620@dogus.edu.tr","employment_type":"Tam Zamanlı","expertise":"Ağ","highest_degree":"YL","industry_experience_years":4,"weekly_course_hours":12,"quality_status":"implemented"}); assert r.status_code in (200,201),r.text
    r = c.post("/api/quality360/infrastructure", json={"program_id":pid,"infrastructure_type":"Bilgisayar Laboratuvarı","name":"Lab Q620","location":"B Blok","capacity":24,"quality_status":"measured","accessibility_status":"measured","isg_status":"measured","notes":""}); assert r.status_code==201,r.text
    r = c.post("/api/quality360/quality-cycles", json={"program_id":pid,"academic_year":"2026-2027","criterion_code":"4","title":"PUKÖ Q620","plan_text":"Plan","do_text":"Uygula","check_text":"Kontrol","act_text":"Önlem","owner":"Program Başkanı","status":"closed","evidence_refs":[]}); assert r.status_code==201,r.text
    r = c.post("/api/quality360/governance", json={"program_id":pid,"body_type":"Program Kurulu","meeting_no":"Q620-1","decision_no":"1","subject":"Kalite","decision_text":"Karar alındı","related_criterion":"5","status":"implemented","evidence_ref":""}); assert r.status_code in (200,201),r.text

    chk = c.get(f"/api/quality360/programs/{pid}/curriculum-check?academic_year=2026-2027"); assert chk.status_code==200,chk.text
    assert chk.json()["passed"] == 4 and chk.json()["readiness_percent"] == 100

    dash = c.get(f"/api/quality360/programs/{pid}/dashboard?academic_year=2026-2027"); assert dash.status_code==200,dash.text
    d = dash.json(); assert d["framework"]["code"] == "MEDEK-2026" and len(d["criteria"]) == 9
    assert d["counts"]["stakeholders"] >= 1 and d["counts"]["faculty"] >= 1 and d["counts"]["infrastructure"] >= 1

    v2 = c.get(f"/api/quality360/programs/{pid}/dashboard?academic_year=2028-2029"); assert v2.status_code==200,v2.text
    d2=v2.json(); assert d2["framework"]["code"] == "MEDEK-2028" and len(d2["criteria"]) == 8
    criterion4=next(x for x in d2["criteria"] if x["code"]=="4")
    assert criterion4["name"] == "Öğretim Planı"
    assert any("Müfredat" in s["label"] for s in criterion4["signals"])


def test_620_quality_excel_templates_import_and_odr_docx():
    pr = ensure_program("Q620X")
    pid = pr["id"]
    kinds = {x["kind"] for x in c.get("/api/excel-center").json()["items"]}
    expected = {"curriculum","stakeholders","graduates","faculty","infrastructure","quality_cycles","governance"}
    assert expected <= kinds
    for kind in expected:
        r=c.get(f"/api/excel-center/{kind}/template"); assert r.status_code==200,(kind,r.text)
        wb=load_workbook(BytesIO(r.content),data_only=True); assert "KILAVUZ" in wb.sheetnames

    raw=c.get("/api/excel-center/curriculum/template").content
    wb=load_workbook(BytesIO(raw)); ws=wb["Mufredat"]; ws.delete_rows(2,1)
    ws.append(["Q620X","2026-2027","Güz","1. Sınıf","Q620X-101","Excel Müfredat",10,"Programa / Alana Özgü Mesleki","Evet","Evet","Evet","Evet","implemented",""])
    out=BytesIO(); wb.save(out); files={"file":("curriculum.xlsx",out.getvalue(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    vr=c.post("/api/excel-center/curriculum/validate",files=files); assert vr.status_code==200,vr.text
    ir=c.post("/api/excel-center/curriculum/import",files=files); assert ir.status_code==200,ir.text
    assert ir.json()["created"]==1

    odr=c.get(f"/api/quality360/programs/{pid}/odr.docx?academic_year=2026-2027")
    assert odr.status_code==200,odr.text
    assert odr.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert odr.content.startswith(b"PK")
    with ZipFile(BytesIO(odr.content)) as zf:
        assert "word/document.xml" in zf.namelist()
        xml=zf.read("word/document.xml").decode("utf-8")
        assert "ÖZ DEĞERLENDİRME RAPORU" in xml and "Q620X" in xml


def test_620_quality_evidence_and_frontend_contract():
    pr = ensure_program("Q620E")
    pid = pr["id"]
    r=c.post(f"/api/quality360/programs/{pid}/evidence",data={"criterion_code":"5","category":"medek","description":"Müfredat kurul kararı"},files={"file":("karar.txt",b"Q620 evidence","text/plain")})
    assert r.status_code==201,r.text
    evidence=r.json(); assert evidence["sha256"] and evidence["size_bytes"]==13
    dl=c.get(f"/api/quality360/evidence/{evidence['id']}/download"); assert dl.status_code==200 and dl.content==b"Q620 evidence"

    root=Path(__file__).resolve().parents[1]
    html=(root/"app/static/index.html").read_text(encoding="utf-8")
    js=(root/"app/static/app.js").read_text(encoding="utf-8")
    assert "Kalite & Akreditasyon" in html and 'id="page-quality360"' in html
    assert all(x in html for x in ["Mazeret","Tek Ders","Muafiyet","Kısa Sınav","Uygulama"])
    assert "prepareQuality360" in js and "/api/quality360/criterion-assessments" in js and "ÖDR" in html
