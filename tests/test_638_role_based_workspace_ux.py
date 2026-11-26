from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')

def test_role_based_navigation_contract():
    assert 'Akademik Akış' not in HTML
    assert 'id="workspaceNavGroup"' in HTML
    assert 'id="analysisNavGroup"' in HTML
    assert 'id="qualityNavGroup"' in HTML
    assert 'id="managementNavGroup"' in HTML
    assert "nav('managementNavGroup',management||hasAnyRole('quality'))" in JS
    assert "classList.toggle('hidden',!management)" in JS

def test_course_context_workspace_contract():
    for label in ['Genel Bakış','Öğrenim Çıktıları','Soru Bankası','Sınavlar','Değerlendirme','Analiz','İyileştirme']:
        assert label in HTML
    for action in ['overview','outcomes','bank','exams','grade','courseanalytics','improvement']:
        assert f'data-course-action="{action}"' in HTML
    assert '.course-context-strip>button.active' in CSS
    assert '.course-workspace-overview' in CSS

def test_instructor_lands_on_action_dashboard():
    assert "showPage(isQualityOnly()?'quality360':'dashboard')" in JS
    assert 'Bugün sizi bekleyen akademik işleri tamamlayın.' in JS
    assert 'Dersi aç →' in JS

def test_obsolete_workflow_dom_dependencies_removed():
    for token in ['workflowProgressBar','workflowSummaryText','academicSetupNavGroup']:
        assert token not in JS
