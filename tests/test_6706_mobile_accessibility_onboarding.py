from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')
CSS = (ROOT / 'app/static/styles.css').read_text(encoding='utf-8')
JS = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')


def test_skip_link_and_main_landmark_contract():
    assert 'class="skip-link" href="#mainContent"' in HTML
    assert '<main id="mainContent" tabindex="-1">' in HTML
    assert 'id="a11yLive"' in HTML and 'aria-live="polite"' in HTML


def test_mobile_quick_navigation_contract():
    assert 'id="mobileQuickNav"' in HTML
    assert 'function renderMobileQuickNav()' in JS
    assert "['dashboard','⌂','Ana']" in JS
    assert "['mycourses','D','Ders']" in JS
    assert "['quality360','◆','Kalite']" in JS
    assert '.mobile-quick-nav' in CSS


def test_dialog_keyboard_focus_contract():
    assert 'const dialogObserver=new MutationObserver' in JS
    assert "if(e.key!=='Tab')return;" in JS
    assert 'activateDialogA11y' in JS
    assert 'deactivateDialogA11y' in JS
    assert 'role="dialog" aria-modal="true" aria-label="Komut Merkezi"' in HTML


def test_first_use_onboarding_is_task_based():
    assert 'douOnboarding6706' in JS
    assert 'Dersinizi açın' in JS
    assert 'Sınavı dört adımda hazırlayın' in JS
    assert 'Kaliteyi standart görünümde yönetin' in JS
    assert "showPage(isQualityOnly()?'quality360':'mycourses')" in JS


def test_touch_and_contrast_accessibility_contract():
    assert '@media(pointer:coarse)' in CSS
    assert 'min-height:44px' in CSS
    assert '@media(prefers-contrast:more)' in CSS
    assert '@media(prefers-reduced-motion:reduce)' in CSS


def test_asset_cache_key_bumped_for_6706():
    assert '6706-accessibility' in HTML
