from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')

def test_command_center_searches_real_entities():
    assert 'loadCommandRemoteResults' in JS
    assert '/api/students?q=' in JS
    assert "group:'Dersler'" in JS
    assert "group:'Sınavlar'" in JS
    assert "group:'Öğrenciler'" in JS
    assert 'openStudentFromCommand' in JS

def test_notifications_route_to_work_context():
    assert 'data-notification-source' in JS
    assert "type==='quality_cycle'" in JS
    assert "setQ360Workspace('cycle')" in JS
    assert "type==='assessment_plan_item'" in JS
    assert "assessmentAssuranceProgram')?.dispatchEvent" in JS
    assert 'İşe git →' in JS

def test_guided_empty_states_have_actions():
    for token in ['data-empty-action="new-question"','data-empty-action="new-exam"','data-empty-action="open-exams"','clearBankFilters']:
        assert token in JS
    assert '.guided-empty' in CSS

def test_command_ui_copy_and_cache_key():
    assert 'Ders, öğrenci, sınav veya işlem ara...' in HTML
    assert '6705-guided-navigation' in HTML
