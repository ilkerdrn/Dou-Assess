from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')
CSS = (ROOT / 'app/static/styles.css').read_text(encoding='utf-8')


def test_feedback_utility_has_dedicated_copy_and_arrow():
    assert 'class="nav-copy"' in HTML
    assert 'nav-feedback-arrow' in HTML
    assert 'Sorun veya öneri gönder' in HTML


def test_sidebar_feedback_has_collision_safe_layout():
    assert 'grid-template-columns:32px minmax(0,1fr) 18px' in CSS
    assert '.nav-feedback .nav-copy' in CSS
    assert 'text-overflow:ellipsis' in CSS


def test_639_asset_cache_keys_are_current():
    assert '6.70-production-hardening' in HTML
