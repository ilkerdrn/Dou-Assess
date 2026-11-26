from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')
CSS = (ROOT / 'app/static/styles.css').read_text(encoding='utf-8')
JS = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')


def test_question_bank_drawer_open_selector_beats_closed_id_rule():
    assert '#page-bank .bank-editor-card.is-open' in CSS
    open_rule = CSS.rindex('#page-bank .bank-editor-card.is-open')
    closed_rule = CSS.rindex('#page-bank .bank-editor-card{')
    assert open_rule > closed_rule
    assert 'transform:translateX(0)!important' in CSS[open_rule:open_rule + 220]
    assert "card?.classList.toggle('is-open',!!open)" in JS
    assert "const btn=ev.target.closest?.('#bankFocusCreate')" in JS


def test_login_canvas_is_centered_and_uses_desktop_width():
    marker = CSS.rindex('/* 6.70.1 — targeted UI/runtime hotfix')
    hotfix = CSS[marker:]
    assert 'place-items:center!important' in hotfix
    assert 'width:min(1440px,100%)!important' in hotfix
    assert 'margin:auto!important' in hotfix


def test_sidebar_active_item_has_single_indicator():
    marker = CSS.rindex('/* 6.70.1 — targeted UI/runtime hotfix')
    hotfix = CSS[marker:]
    assert '.grouped-nav.final-nav .nav-submenu:before' in hotfix
    assert 'display:none!important' in hotfix
    assert 'box-shadow:inset 3px 0 0 #d42240!important' in hotfix


def test_hotfix_busts_static_asset_cache_without_changing_release_contract():
    assert '/styles.css?v=6.70-production-hardening&h=6701' in HTML
    assert '/runtime-core.js?v=6.70-production-hardening&h=6701' in HTML
    assert '/app.js?v=6.70-production-hardening&h=6701' in HTML
