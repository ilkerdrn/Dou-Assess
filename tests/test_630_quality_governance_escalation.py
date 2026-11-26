from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/"app/main.py").read_text(encoding="utf-8")
API=(ROOT/"app/quality360_api.py").read_text(encoding="utf-8")
QUALITY=(ROOT/"app/services/quality360.py").read_text(encoding="utf-8")
JS=(ROOT/"app/static/app.js").read_text(encoding="utf-8")
HTML=(ROOT/"app/static/index.html").read_text(encoding="utf-8")
CSS=(ROOT/"app/static/styles.css").read_text(encoding="utf-8")

def test_version_630():
    assert "6.70-production-hardening" in MAIN

def test_escalation_backend_contract():
    assert "quality_escalation_queue" in QUALITY
    assert "/api/quality360/escalations" in API
    for role in ["Aksiyon sorumlusu","Bölüm / Program Başkanlığı","Fakülte / MYO Yönetimi","Üniversite Kalite Birimi"]:
        assert role in QUALITY

def test_escalation_policy_is_deterministic_and_non_destructive():
    for threshold in ["days_overdue >= 30","days_overdue >= 15","days_overdue >= 8"]:
        assert threshold in QUALITY
    assert "does not send messages or change permissions" in QUALITY
    assert 'require_roles("admin", "quality", "faculty_admin", "department_head", "program_head")' in API

def test_escalation_ui_contract():
    assert "qualityEscalationQueue" in HTML
    assert "loadQualityEscalations" in JS
    assert "Termin & eskalasyon kuyruğu" in HTML
    assert ".quality-escalation-row" in CSS
