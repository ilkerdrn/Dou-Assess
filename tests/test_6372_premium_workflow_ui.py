from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")

def test_academic_workflow_has_premium_status_rail():
    # 6.38 intentionally removes the setup rail from daily navigation.
    assert 'id="workflowProgressBar"' not in HTML
    assert 'Akademik Akış' not in HTML
    assert 'id="workspaceNavGroup"' in HTML
    assert 'id="managementNavGroup"' in HTML
    assert 'class="course-context-strip"' in HTML
    assert 'Öğrenim Çıktıları' in HTML and 'İyileştirme' in HTML
    assert '.course-context-strip>button.active' in CSS

def test_user_ui_uses_open_outcome_language():
    visible = HTML + JS
    assert 'ÖÇ / PÇ' not in visible
    assert 'ÖÇ/PÇ' not in visible
    assert 'Öğrenim Çıktısı / Program Çıktısı' not in visible
    assert 'Öğrenim ve Program Çıktıları' in visible

def test_workflow_ui_keeps_frozen_backend_contract():
    main = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert '6.70-production-hardening' in main
    assert '0042_performance_production_hardening' in main
