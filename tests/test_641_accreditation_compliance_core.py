from __future__ import annotations

import hashlib
import uuid
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import models as m
from app.db import SessionLocal
from app.main import app
from app.services.compliance import YOKAK_2026_SUBCRITERIA

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)
SUFFIX = uuid.uuid4().hex[:8].upper()
AY = "2026-2027"


def _post(path: str, payload: dict, expected=(200, 201)) -> dict:
    r = client.post(path, json=payload)
    assert r.status_code in expected, (path, r.status_code, r.text)
    return r.json()


@lru_cache(maxsize=1)
def context() -> dict:
    program = _post("/api/programs", {
        "code": f"Q641-{SUFFIX}",
        "name": "6.41 Akreditasyon Uyum Programı",
        "faculty": "Mühendislik Fakültesi",
        "department": "Bilgisayar Mühendisliği",
    })
    pid = program["id"]
    po = _post(f"/api/programs/{pid}/program-outcomes", {
        "academic_year": AY,
        "code": "PÇ1",
        "description": "Mühendislik problemlerini analiz eder ve çözüm geliştirir.",
    })
    student = _post("/api/students", {
        "program_id": pid,
        "student_no": f"641{SUFFIX}",
        "full_name": "Akreditasyon Test Öğrencisi",
        "class_name": "4. Sınıf",
    })
    # Course creation is direct to avoid coupling this compliance test to academic-period lock state.
    with SessionLocal() as db:
        course = m.Course(
            program_id=pid, code=f"CMP-{SUFFIX}", name="Akreditasyon Uyum Dersi",
            academic_year=AY, term="Güz", instructor_email="quality641@dogus.edu.tr",
            instructor_name="Kalite Test Öğretim Elemanı", pass_threshold_percent=50,
        )
        db.add(course); db.commit(); db.refresh(course); course_id = course.id
    faculty = _post("/api/quality360/faculty", {
        "program_id": pid, "title": "Öğr. Gör.", "full_name": "Kalite Test Öğretim Elemanı",
        "email": f"quality641-{SUFFIX.lower()}@dogus.edu.tr", "employment_type": "Tam Zamanlı",
        "expertise": "Akreditasyon ve ölçme", "highest_degree": "Doktora",
        "industry_experience_years": 5, "weekly_course_hours": 12, "quality_status": "implemented",
    })
    graduate = _post("/api/quality360/graduates", {
        "program_id": pid, "graduate_key": f"GR-{SUFFIX}", "full_name": "Mezun Test",
        "graduation_year": 2026, "employment_status": "Çalışıyor - Alanında", "employer": "Teknoloji AŞ",
        "sector": "Yazılım", "job_title": "Mühendis", "related_field": True, "notes": "",
    })
    infra = _post("/api/quality360/infrastructure", {
        "program_id": pid, "infrastructure_type": "Bilgisayar Laboratuvarı", "name": f"Lab-{SUFFIX}",
        "location": "A Blok", "capacity": 30, "quality_status": "implemented",
        "accessibility_status": "implemented", "isg_status": "implemented", "notes": "",
    })
    return {"program": program, "pid": pid, "po": po, "student": student, "course_id": course_id,
            "faculty": faculty, "graduate": graduate, "infra": infra}


def test_641_release_schema_and_framework_registry_contract():
    main = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "6.70-production-hardening"' in main
    assert 'EXPECTED_SCHEMA_REVISION = "0047_institution_settings_outcome_approval"' in main
    assert len(YOKAK_2026_SUBCRITERIA) == 46

    r = client.get("/api/quality360/frameworks")
    assert r.status_code == 200, r.text
    rows = r.json()
    active = {(x["code"], x["version"]): x for x in rows}
    assert ("MUDEK-CORE", "3.1") in active
    assert ("TURAK-CORE", "2024-12-27") in active
    assert any(x["framework_family"] == "SABAK" for x in rows)
    assert any(x["framework_family"] == "EPDAD" for x in rows)
    assert not any(x["code"] in {"MUDEK-CORE", "TURAK-CORE"} and x["version"] == "configurable" for x in rows)
    yokak = next(x for x in rows if x["code"] == "YOKAK-2026")
    assert len(yokak["criteria"]) == 14
    assert yokak["thresholds"]["subcriteria_count"] == 46

    templates = client.get("/api/compliance/templates")
    assert templates.status_code == 200, templates.text
    keys = {(x["framework_family"], x["report_type"], x["version"]) for x in templates.json()}
    assert ("MÜDEK", "ODR", "3.1") in keys
    assert any(a == "MÜDEK" and b == "BBO" for a, b, _ in keys)
    assert any(a == "MÜDEK" and b == "FBO" for a, b, _ in keys)
    assert ("YÖKAK", "KIDR", "2026-14x46") in keys
    assert any(a == "TURAK" and b == "ODR" for a, b, _ in keys)
    assert any(a == "SABAK" and b == "ODR" for a, b, _ in keys)
    assert any(a == "EPDAD" and b == "ODR" for a, b, _ in keys)


def test_641_pea_po_components_framework_freeze_and_student_card():
    ctx = context(); pid = ctx["pid"]; po = ctx["po"]
    pea = _post("/api/compliance/pea", {
        "program_id": pid, "academic_year": AY, "code": "PEA1",
        "description": "Mezunlar mesleki uygulamalarda başarılı olur.",
        "stakeholder_basis": "Mezun ve işveren geribildirimi", "mission_alignment": "Üniversite misyonu",
        "review_cycle_years": 3, "target_indicator": "%70 alan içi istihdam", "quality_status": "implemented",
        "evidence_refs": [],
    })
    comp = _post("/api/compliance/program-outcome-components", {
        "program_outcome_id": po["id"], "code": "PÇ1.1", "description": "Problemi tanımlar ve analiz eder.",
        "component_type": "skill", "framework_family": "MÜDEK", "framework_version": "3.1",
        "framework_component_code": "3.1-PÇ1-a", "required": True, "evidence_refs": [],
    })
    mapping = _post("/api/compliance/pea/outcome-map", {
        "objective_id": pea["id"], "program_outcome_id": po["id"], "contribution": 5,
        "rationale": "PEA1 doğrudan PÇ1 ile izlenir.",
    })
    assert mapping["contribution"] == 5 and comp["framework_version"] == "3.1"

    frameworks = client.get("/api/quality360/frameworks").json()
    yokak = next(x for x in frameworks if x["code"] == "YOKAK-2026")
    snap = _post(f"/api/compliance/programs/{pid}/framework-freeze", {
        "framework_profile_id": yokak["id"], "academic_year": AY,
    })
    assert len(snap["content_sha256"]) == 64
    tree = client.get(f"/api/compliance/programs/{pid}/criteria-tree", params={
        "framework_profile_id": yokak["id"], "academic_year": AY,
    })
    assert tree.status_code == 200, tree.text
    assert tree.json()["source"] == "frozen"
    assert tree.json()["criteria_count"] == 14 and tree.json()["subcriteria_count"] == 46

    card = client.get(f"/api/compliance/students/{ctx['student']['id']}/outcome-card", params={"academic_year": AY})
    assert card.status_code == 200, card.text
    payload = card.json()
    assert any(x["code"] == "PÇ1" for x in payload["program_outcomes"])
    assert any(x["component_code"] == "PÇ1.1" for x in payload["program_outcome_components"])
    frozen = _post(f"/api/compliance/students/{ctx['student']['id']}/outcome-snapshots", {
        "academic_year": AY, "snapshot_type": "graduation", "freeze": True,
    })
    assert frozen["frozen"] is True and len(frozen["content_sha256"]) == 64


def test_641_controlled_documents_budget_cv_workload_graduate_infra_and_yokak_domains():
    ctx = context(); pid = ctx["pid"]
    doc = _post("/api/compliance/documents", {
        "program_id": pid, "document_code": f"POL-{SUFFIX}", "document_type": "policy",
        "title": "Program Kalite Politikası", "owner": "Program Başkanı", "status": "active", "retention_years": 10,
    })
    reviewer_email=f"quality-reviewer-{SUFFIX.lower()}@local"
    with SessionLocal() as db:
        reviewer=m.AppUser(email=reviewer_email,display_name="Kalite Reviewer",auth_source="pilot",is_active=True)
        db.add(reviewer);db.flush();db.add(m.UserRoleAssignment(user_id=reviewer.id,role="quality"));db.commit()
    reviewer_headers={"X-DOU-Pilot-User":reviewer_email}

    direct = client.post(f"/api/compliance/documents/{doc['id']}/revisions", json={
        "revision_no": 99, "status": "approved", "change_summary": "Güvensiz doğrudan onay",
        "content_text": "Olmamalı", "approved_by": "İstemci",
    })
    assert direct.status_code == 409

    r1 = _post(f"/api/compliance/documents/{doc['id']}/revisions", {
        "revision_no": 1, "status": "draft", "change_summary": "İlk yayın",
        "content_text": "Politika sürüm 1", "approved_by": "istemci-degeri-yok-sayilir",
    })
    assert r1["status"] == "draft" and r1["prepared_by"]
    assert client.post(f"/api/compliance/document-revisions/{r1['id']}/submit").status_code == 200
    assert client.post(f"/api/compliance/document-revisions/{r1['id']}/review",headers=reviewer_headers).status_code == 200
    a1=client.post(f"/api/compliance/document-revisions/{r1['id']}/approve",headers=reviewer_headers);assert a1.status_code==200,a1.text

    r2 = _post(f"/api/compliance/documents/{doc['id']}/revisions", {
        "revision_no": 2, "status": "draft", "change_summary": "Güncellendi",
        "content_text": "Politika sürüm 2", "approved_by": "",
    })
    assert client.post(f"/api/compliance/document-revisions/{r2['id']}/submit").status_code == 200
    assert client.post(f"/api/compliance/document-revisions/{r2['id']}/review",headers=reviewer_headers).status_code == 200
    a2=client.post(f"/api/compliance/document-revisions/{r2['id']}/approve",headers=reviewer_headers);assert a2.status_code==200,a2.text
    assert a2.json()["approved_by"] == reviewer_email
    revisions = client.get(f"/api/compliance/documents/{doc['id']}/revisions").json()
    assert len(r1["sha256"]) == 64 and len(r2["sha256"]) == 64
    assert {x["revision_no"]: x["status"] for x in revisions}[1] == "superseded"
    assert {x["revision_no"]: x["status"] for x in revisions}[2] == "approved"

    plan = _post("/api/compliance/budget-plans", {
        "program_id": pid, "academic_year": AY, "currency": "TRY", "allocated_amount": 100000,
        "spent_amount": 0, "owner": "Dekanlık", "quality_status": "implemented", "evidence_refs": [],
    })
    _post("/api/compliance/budget-lines", {
        "budget_plan_id": plan["id"], "category": "Laboratuvar", "description": "Ağ cihazları",
        "planned_amount": 30000, "actual_amount": 25000, "funding_source": "Kurum", "criterion_code": "8", "evidence_refs": [],
    })
    budget = client.get(f"/api/compliance/programs/{pid}/budget", params={"academic_year": AY}).json()
    assert budget["plan"]["spent_amount"] == 25000
    assert budget["variance"] == 75000 and budget["actual_lines"] == 25000

    cv = _post("/api/compliance/faculty-cv", {
        "faculty_record_id": ctx["faculty"]["id"], "format_type": "YOKSIS-UAK", "version_no": 1,
        "cv_data": {"education": ["Doktora"], "publications": ["Makale"]}, "approved": True,
    })
    assert len(cv["content_sha256"]) == 64
    _post("/api/compliance/faculty-workload", {
        "faculty_record_id": ctx["faculty"]["id"], "academic_year": AY, "term": "Güz",
        "course_code": f"CMP-{SUFFIX}", "workload_type": "course", "weekly_hours": 12,
        "source": "OBS", "notes": "Otomatik senkron kaynağı",
    })
    workload = client.get(f"/api/compliance/faculty/{ctx['faculty']['id']}/workload", params={"academic_year": AY}).json()
    assert workload["weekly_hours"] >= 12

    for year in (1, 3, 5):
        _post("/api/compliance/graduate-followups", {
            "graduate_record_id": ctx["graduate"]["id"], "followup_year": year,
            "employment_status": "Çalışıyor - Alanında", "employer": "Teknoloji AŞ", "job_title": "Mühendis",
            "related_field": True, "satisfaction_percent": 90, "employer_feedback": "Olumlu",
            "resulting_action": "Program içeriği korundu", "evidence_refs": [],
        })
    gd = client.get(f"/api/compliance/programs/{pid}/graduate-followup-dashboard").json()
    assert gd["coverage"] == {"1_year": 100.0, "3_year": 100.0, "5_year": 100.0}

    _post("/api/compliance/infrastructure-maintenance", {
        "infrastructure_id": ctx["infra"]["id"], "maintenance_type": "periodic",
        "planned_date": "2026-10-01", "completed_date": "2026-10-01", "status": "completed",
        "owner": "Bilgi İşlem", "notes": "Bakım ve İSG kontrolü tamamlandı", "evidence_refs": [],
    })
    maint = client.get(f"/api/compliance/programs/{pid}/infrastructure-maintenance").json()
    assert any(x["status"] == "completed" for x in maint)

    for idx, domain in enumerate(("research", "social_contribution", "internationalization"), start=1):
        _post("/api/compliance/mission-activities", {
            "program_id": pid, "academic_year": AY, "domain": domain, "scope_type": "program",
            "scope_name": "6.41 Akreditasyon Uyum Programı", "code": f"{domain[:3].upper()}-{SUFFIX}",
            "title": f"{domain} kalite faaliyeti", "activity_type": "KPI", "owner": "Kalite",
            "partner": "Paydaş", "country": "Türkiye", "participants": 10 + idx,
            "budget_amount": 1000 * idx, "target_value": 10, "actual_value": 10, "unit": "adet",
            "status": "completed", "outcome_text": "Hedef sağlandı", "evidence_refs": [{"ref": "kanıt"}],
        })
        dash = client.get(f"/api/compliance/mission/{domain}", params={"academic_year": AY, "program_id": pid})
        assert dash.status_code == 200, dash.text
        assert dash.json()["summary"]["activity_count"] >= 1
        assert dash.json()["summary"]["target_attainment_percent"] == 100.0


def test_641_accreditation_lifecycle_evaluator_snapshot_and_document_requests():
    ctx = context(); pid = ctx["pid"]
    frameworks = client.get("/api/quality360/frameworks").json()
    mudek = next(x for x in frameworks if x["code"] == "MUDEK-CORE" and x["version"] == "3.1")
    application = _post("/api/compliance/applications", {
        "program_id": pid, "framework_profile_id": mudek["id"], "academic_year": AY,
        "application_type": "general", "stage": "preparation", "status": "active",
        "application_date": "2026-09-10", "self_evaluation_due": "2026-12-31",
        "correction_due": "2027-01-31", "visit_date": "2027-03-15", "owner": "Program Başkanı",
        "notes": "6.41 yaşam döngüsü",
    })
    assert application["framework_snapshot_id"]
    moved = client.patch(f"/api/compliance/applications/{application['id']}", json={"stage": "submitted"})
    assert moved.status_code == 200, moved.text
    jump = client.patch(f"/api/compliance/applications/{application['id']}", json={"stage": "correction"})
    assert jump.status_code == 409

    request = _post("/api/compliance/document-requests", {
        "application_id": application["id"], "criterion_code": "3",
        "title": "Ek öğrenci çıktı kanıtı", "description": "Ziyaret öncesi ek belge",
        "requested_by": "Değerlendirici", "due_date": "2027-03-01", "evidence_refs": [],
    })
    assert request["status"] == "open"
    ws = _post("/api/compliance/evaluator-workspaces", {
        "application_id": application["id"], "evaluator_email": f"evaluator-{SUFFIX.lower()}@example.org",
        "evaluator_name": "Dış Değerlendirici", "access_mode": "read_only",
    })
    assert ws["access_mode"] == "read_only" and len(ws["snapshot_sha256"]) == 64
    snap = client.get(f"/api/compliance/evaluator-workspaces/{ws['id']}/snapshot")
    assert snap.status_code == 200, snap.text
    assert snap.json()["read_only"] is True
    assert snap.json()["framework_snapshot"]["content_sha256"]
    assert any(x["id"] == request["id"] for x in snap.json()["document_requests"])
    token=ws.get("invitation_token");assert token and "invitation_token_hash" not in ws
    public=client.get(f"/api/public/evaluator-workspaces/{ws['id']}/snapshot",headers={"X-DOU-Evaluator-Token":token})
    assert public.status_code==200,public.text
    bad=client.get(f"/api/public/evaluator-workspaces/{ws['id']}/snapshot",headers={"X-DOU-Evaluator-Token":"bad-token"});assert bad.status_code==401


def test_641_official_template_lock_render_and_virtual_evidence_room_embed():
    ctx = context(); pid = ctx["pid"]
    custom = _post("/api/compliance/templates", {
        "framework_family": f"TEST-{SUFFIX}", "report_type": "ODR", "version": "1.0",
        "title": "6.41 Fiziksel Resmî Şablon Testi", "sections": [], "folder_layout": [],
        "source_url": "https://example.invalid/official", "source_sha256": "", "locked": True,
    })
    doc = Document(); doc.add_heading("ÖZDEĞERLENDİRME RAPORU", 0)
    doc.add_paragraph("Program: {{PROGRAM_NAME}} | Kod: {{PROGRAM_CODE}} | Yıl: {{ACADEMIC_YEAR}}")
    raw = BytesIO(); doc.save(raw); template_bytes = raw.getvalue()
    up = client.post(f"/api/compliance/templates/{custom['id']}/upload", files={
        "file": ("official-template.docx", template_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    })
    assert up.status_code == 201, up.text
    assert up.json()["source_sha256"] == hashlib.sha256(template_bytes).hexdigest()
    assert up.json()["locked"] is True
    source = client.get(f"/api/compliance/templates/{custom['id']}/source")
    assert source.status_code == 200 and source.content == template_bytes
    rendered = client.get(f"/api/compliance/templates/{custom['id']}/render.docx", params={"program_id": pid, "academic_year": AY})
    assert rendered.status_code == 200, rendered.text
    with ZipFile(BytesIO(rendered.content)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
        assert "6.41 Akreditasyon Uyum Programı" in xml and f"Q641-{SUFFIX}" in xml and AY in xml

    evidence_bytes = b"DOU Assess 6.41 official evidence payload"
    ev = client.post(f"/api/quality360/programs/{pid}/evidence",
        data={"criterion_code": "2", "category": "mudek", "description": "Program Eğitim Amaçları kanıtı"},
        files={"file": ("PEA-kanit.txt", evidence_bytes, "text/plain")})
    assert ev.status_code == 201, ev.text
    bbo = client.get(f"/api/compliance/programs/{pid}/evidence-room.zip", params={"academic_year": AY, "room_type": "BBO"})
    assert bbo.status_code == 200, bbo.text
    with ZipFile(BytesIO(bbo.content)) as zf:
        names = zf.namelist()
        assert any("2 - Program Eğitim Amaçları" in x for x in names)
        assert any(x.endswith("KANIT-INDEKSI.json") for x in names)
        assert any(x.endswith("SHA256SUMS.txt") for x in names)
        embedded = [x for x in names if x.endswith("PEA-kanit.txt")]
        assert embedded and zf.read(embedded[0]) == evidence_bytes

    fbo = client.get(f"/api/compliance/programs/{pid}/evidence-room.zip", params={"academic_year": AY, "room_type": "FBO"})
    assert fbo.status_code == 200, fbo.text
    with ZipFile(BytesIO(fbo.content)) as zf:
        names = zf.namelist()
        assert any("12 - Diğer" in x for x in names)
        assert any("Ziyaret Öncesi İstenilen Ek Bilgi" in x for x in names)


def test_641_course_file_matrix_all_green_and_frontend_contract():
    ctx = context(); pid = ctx["pid"]
    course_doc = client.get(f"/api/compliance/courses/{ctx['course_id']}/course-file.docx")
    assert course_doc.status_code == 200, course_doc.text
    assert course_doc.content.startswith(b"PK")
    with ZipFile(BytesIO(course_doc.content)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
        assert "Standart Ders Dosyası" in xml and f"CMP-{SUFFIX}" in xml

    matrix = client.get(f"/api/compliance/programs/{pid}/matrix", params={"academic_year": AY})
    assert matrix.status_code == 200, matrix.text
    payload = matrix.json()
    assert payload["summary"]["green"] == 30 and payload["summary"]["total"] == 30
    assert all(x["status"] == "green" for x in payload["items"])
    matrix_doc = client.get(f"/api/compliance/programs/{pid}/matrix.docx", params={"academic_year": AY})
    assert matrix_doc.status_code == 200 and matrix_doc.content.startswith(b"PK")

    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
    assert 'data-q360-workspace="compliance"' in html and "Uyum Merkezi" in html
    for token in ["q641ComplianceMatrix", "q641PeaForm", "q641PoComponentForm", "q641StudentCard", "q641TemplateUploadForm"]:
        assert token in html
    assert "loadComplianceCenter" in js and "/api/compliance/programs/" in js
    assert ".compliance-matrix-grid" in css
