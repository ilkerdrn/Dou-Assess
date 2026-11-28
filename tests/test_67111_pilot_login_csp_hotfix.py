from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')

def test_67111_login_direct_flow_and_cache_marker():
    assert '67111-login-csp-hotfix' in HTML
    assert 'async function completePilotLogin(email)' in JS
    assert "state.currentUser=await api('GET','/api/auth/me')" in JS
    assert "enterApplication();" in JS
    assert "showPage(isQualityOnly()?'quality360':'dashboard')" in JS

def test_67111_login_error_surface_exists():
    assert 'id="pilotLoginError"' in HTML
    assert '.login-mode-box .login-error' in CSS
    assert "setLoginBusy(false,err.message||'Pilot kullanıcı girişi başarısız.')" in JS

def test_67111_static_inline_style_csp_noise_closed():
    assert 'style="' not in HTML
    assert '.obs-results-course-grid{margin-top:16px}' in CSS
    assert '#accredProgressFill{width:0%}' in CSS
    assert '.student-score-ring{--score:0}' in CSS

def test_67111_logout_clears_pilot_identity():
    assert "localStorage.removeItem('douPilotSession')" in JS
    assert "localStorage.removeItem('douPilotUser')" in JS
