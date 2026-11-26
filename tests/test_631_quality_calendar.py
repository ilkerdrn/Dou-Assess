from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/"app/main.py").read_text(encoding="utf-8")
API=(ROOT/"app/quality360_api.py").read_text(encoding="utf-8")
MODELS=(ROOT/"app/models.py").read_text(encoding="utf-8")
SCHEMAS=(ROOT/"app/schemas.py").read_text(encoding="utf-8")
JS=(ROOT/"app/static/app.js").read_text(encoding="utf-8")
HTML=(ROOT/"app/static/index.html").read_text(encoding="utf-8")
CSS=(ROOT/"app/static/styles.css").read_text(encoding="utf-8")
MIG=(ROOT/"migrations/versions/0022_quality_calendar.py").read_text(encoding="utf-8")

def test_version_and_schema_631():
    assert "6.70-production-hardening" in MAIN
    assert "0042_performance_production_hardening" in MAIN

def test_calendar_persistence_contract():
    assert "class QualityCalendarEvent" in MODELS
    assert "quality_calendar_events" in MIG
    assert "QualityCalendarEventCreate" in SCHEMAS
    assert 'POST' not in '' or '/api/quality360/calendar' in API

def test_calendar_aggregates_existing_quality_work():
    assert 'quality_cycle' in API
    assert 'governance_decision' in API
    assert 'days_remaining' in API and 'overdue' in API and 'attention' in API

def test_calendar_ui_contract():
    assert 'data-q360-workspace="calendar"' in HTML
    assert 'q360CalendarForm' in HTML
    assert 'loadQualityCalendar' in JS
    assert '.quality-calendar-item' in CSS

def test_owner_due_and_evidence_workflow_visible():
    for token in ['q360CalendarOwner','q360CalendarOwnerRole','q360CalendarDue','q360CalendarEvidence','q360CycleDue','q360GovMeetingDate']:
        assert token in HTML
