from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')

def test_67112_login_cache_marker_and_direct_verified_flow():
    assert '67112-fullscreen-login' in HTML
    block=JS.split('async function completePilotLogin(email){',1)[1].split('function setLoginBusy',1)[0]
    assert "localStorage.removeItem('douPilotSession')" in block
    assert "state.currentUser=await api('GET','/api/auth/me')" in block
    assert "if(!state.currentUser?.email)throw new Error('Kullanıcı oturumu doğrulanamadı.')" in block
    assert block.index("state.currentUser=await api('GET','/api/auth/me')") < block.index("localStorage.setItem('douPilotSession','1')")
    assert "enterApplication();" in block

def test_67112_login_owns_entire_viewport():
    assert 'height:100dvh!important' in CSS
    assert 'width:100vw!important' in CSS
    assert 'border-radius:0!important' in CSS
    assert 'body.login-active{overflow:hidden!important}' in CSS
    assert '.login-card-wrap{' in CSS and 'overflow-y:auto!important' in CSS

def test_67112_gate_toggles_document_scroll_lock():
    show=JS.split('function showLoginGate(){',1)[1].split('function enterApplication',1)[0]
    enter=JS.split('function enterApplication(){',1)[1].split('function table',1)[0]
    assert "document.body.classList.add('login-active')" in show
    assert "document.body.classList.remove('login-active')" in enter

def test_67112_csp_inline_style_regression_stays_closed():
    assert 'style="' not in HTML
