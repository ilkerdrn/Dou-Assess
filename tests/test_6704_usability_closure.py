from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INDEX=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
APP=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')

def test_dashboard_has_single_next_action_and_progressive_work():
    assert 'id="dashboardNextAction"' in INDEX
    assert 'ŞİMDİ NE YAPMALIYIM?' in INDEX
    assert 'dashboard-secondary-work' in INDEX
    assert 'renderDashboardNextAction(rows)' in APP

def test_course_workspace_is_task_first():
    for action in ('bank','exams','grade','courseanalytics'):
        assert f'data-course-quick="{action}"' in INDEX
    assert 'Gelişmiş ders araçları' in INDEX
    assert 'course-quick-start' in CSS

def test_exam_progressive_disclosure():
    assert 'class="card blueprint-card advanced-feature"' in INDEX
    assert 'GELİŞMİŞ PLANLAMA' in INDEX
    assert 'Gelişmiş sınav ayarları' in INDEX
    assert '<b>Son Kontrol</b>' in INDEX

def test_grading_queue_exists():
    assert 'id="gradeQueue"' in INDEX
    assert 'id="gradeQueueCount"' in INDEX
    assert 'function renderGradeQueue()' in APP
    assert 'data-grade-exam' in APP

def test_quality_standard_expert_mode():
    assert 'id="qualityViewMode"' in INDEX
    assert 'data-quality-mode="standard"' in INDEX
    assert 'data-quality-mode="expert"' in INDEX
    assert 'function setQualityViewMode' in APP
    assert '[data-quality-mode]' in CSS
    assert 'data-quality-mode="standard"' in INDEX

def test_asset_cache_key_updated():
    assert '6704-usability-closure' in INDEX

def test_question_bank_drawer_fix_still_present():
    assert '#page-bank .bank-editor-card.is-open' in CSS
    assert 'translateX(0)' in CSS
