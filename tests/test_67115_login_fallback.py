from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_67115_login_fallback_assets():
    html=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
    js=(ROOT/'app/static/login-fallback.js').read_text(encoding='utf-8')
    assert '67115-login-fallback' in html
    assert '/login-fallback.js' in html
    assert "X-DOU-Pilot-User" in js
    assert 'douPilotFallbackLogin' in js
    assert "stopImmediatePropagation" in js
    assert "Sunucu yanıt vermedi" in js
