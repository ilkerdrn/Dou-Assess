from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')
JS = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
CSS = (ROOT / 'app/static/styles.css').read_text(encoding='utf-8')


def test_workflow_modal_is_structural_and_no_native_prompt_remains():
    assert 'id="workflowModal"' in HTML
    assert 'function workflowForm' in JS
    assert 'prompt(' not in JS
    assert 'window.prompt(' not in JS
    assert '.workflow-modal-overlay' in CSS


def test_legacy_admin_pages_use_reference_workspace_language():
    for page in ['import','data','accreditation','evidence','feedback','security','users']:
        marker = f'id="page-{page}" class="page'
        pos = HTML.index(marker)
        assert 'reference-workspace-page' in HTML[pos:pos+180]
        assert 'modern-admin-page' in HTML[pos:pos+180]


def test_security_users_and_evidence_have_page_headers():
    assert 'Production Operasyon Merkezi' in HTML
    assert 'Kullanıcı ve Akademik Kapsam Yönetimi' in HTML
    assert 'Sınav Kanıtları' in HTML


def test_structured_quality_workflows_replace_prompt_chains():
    for token in [
        "title:'PDR maddesi ekle'",
        "title:'Akreditasyon bulgusu ekle'",
        "title:'Ziyaret notu ekle'",
        "title:'Final akreditasyon kararını kaydet'",
        "title:'Sınavı onaya gönder'",
        "title:'Revizyon iste'",
        "title:'Ölçme güvence planını dondur'",
        "title:'Kanıtı Program Değerlendirmesi bölümüne bağla'",
    ]:
        assert token in JS


def test_cache_busts_6701_without_breaking_release_contract():
    assert '/styles.css?v=6.70-production-hardening&h=6701-671ux' in HTML
    assert '/runtime-core.js?v=6.70-production-hardening&h=6701-671ux' in HTML
    assert '/app.js?v=6.70-production-hardening&h=6701-671ux' in HTML


def test_question_bank_specificity_fix_survives_closure():
    marker = CSS.rindex('/* 6.70.1 — targeted UI/runtime hotfix')
    tail = CSS[marker:]
    assert '#page-bank .bank-editor-card.is-open' in tail
    assert 'transform:translateX(0)!important' in tail.replace(' ', '')
