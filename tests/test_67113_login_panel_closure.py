from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
INDEX = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')


def test_onboarding_does_not_auto_open_on_login_or_refresh():
    assert "setTimeout(()=>openOnboarding(false),350)" not in APP
    assert "enterApplication();return true;" in APP
    assert "function openOnboarding(force=false)" in APP
    assert "openOnboarding(true)" in APP


def test_cache_bust_marker_present():
    assert "67113-manual-onboarding" in INDEX
