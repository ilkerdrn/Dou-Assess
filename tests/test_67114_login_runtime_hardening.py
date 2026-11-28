from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
APP=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
RUNTIME=(ROOT/'app/static/runtime-core.js').read_text(encoding='utf-8')

def test_67114_cache_marker_present():
    assert '67114-login-runtime' in HTML

def test_67114_runtime_owns_pilot_login_click():
    assert 'window.robustPilotLogin=robustPilotLogin' in RUNTIME
    assert "event.target?.closest?.('#loginPilotBtn')" in RUNTIME
    assert "event.stopImmediatePropagation()" in RUNTIME

def test_67114_auth_me_uses_explicit_selected_user_header():
    assert "headers:{'X-DOU-Pilot-User':chosen,'Cache-Control':'no-cache'}" in RUNTIME
    assert "localStorage.setItem(SESSION_KEY,'1')" in RUNTIME

def test_67114_verified_auth_opens_shell_even_if_later_init_fails():
    assert "document.getElementById('loginGate')?.classList.add('hidden')" in RUNTIME
    assert "document.querySelector('.shell')?.classList.remove('app-shell-hidden')" in RUNTIME
    assert "try{ if(typeof window.refreshCore==='function')await window.refreshCore(); }catch" in RUNTIME

def test_67114_onboarding_remains_manual_only():
    assert 'setTimeout(()=>openOnboarding(false),350)' not in APP
    assert 'openOnboarding(true)' in APP
