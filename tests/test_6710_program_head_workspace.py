from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')

def test_6710_asset_key_and_nav_label():
    assert '6710-program-workspace' in HTML
    assert '<b>Program Çalışma Alanı</b>' in HTML

def test_program_workspace_has_decision_and_quick_actions():
    assert 'id="programWorkspaceDecision"' in HTML
    assert 'id="programWorkspaceActions"' in HTML
    for target in ['outcomes','courses','programreview','evidencehub','quality','accreditation']:
        assert f'data-program-workspace-go="{target}"' in HTML

def test_program_workspace_combines_analytics_and_review():
    assert 'renderProgramWorkspaceReview' in JS
    assert '/program-reviews' in JS
    assert 'ŞİMDİ NE YAPMALIYIM?' in JS
    assert 'Önce ölçülmeyen dersleri tamamlayın' in JS
    assert 'Aksiyonsuz açıkları PUKÖ’ye bağlayın' in JS

def test_program_context_is_carried_to_other_workspaces():
    for element_id in ['programReviewProgram','evidenceHubProgram','qualityProgram','accredProgram','curriculumMapProgram']:
        assert element_id in JS
    assert 'openProgramWorkspaceTarget' in JS

def test_program_workspace_responsive_css():
    assert '.program-workspace-actions' in CSS
    assert '.program-workspace-decision' in CSS
    assert '@media(max-width:680px)' in CSS
