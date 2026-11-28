from pathlib import Path
import uuid

from app.db import Base, SessionLocal, engine
from app import models as m
from app.config import settings
from app.services.pilot_ops import build_uat_checks

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')
CSS = (ROOT / 'app/static/styles.css').read_text(encoding='utf-8')
JS = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')


def test_role_uat_ui_contract():
    assert 'id="pilotRoleJourneys"' in HTML
    assert 'function renderPilotRoleJourneys' in JS
    assert 'Öğretim Elemanı Yolculuğu' in (ROOT / 'app/services/pilot_ops.py').read_text(encoding='utf-8')
    assert 'Program Başkanı Yolculuğu' in (ROOT / 'app/services/pilot_ops.py').read_text(encoding='utf-8')
    assert 'Kalite Kullanıcısı Yolculuğu' in (ROOT / 'app/services/pilot_ops.py').read_text(encoding='utf-8')
    assert '.uat-role-grid' in CSS and '.uat-role-card' in CSS


def test_pilot_friction_feedback_is_contextual_and_production_hidden():
    assert "state.authConfig?.app_env!=='production'" in JS
    assert 'Bu ekranda sürtünme bildir' in JS
    assert 'openQuickFrictionFeedback' in JS
    assert "category:'usability'" in JS
    assert "page:meta[0]||page" in JS


def test_uat_journeys_are_persisted_in_summary_contract():
    main = (ROOT / 'app/main.py').read_text(encoding='utf-8')
    assert '"journeys": result.get("journeys", [])' in main
    assert 'summary={"readiness_score": result["readiness"]["score"], "version": APP_VERSION, "journeys": result.get("journeys", [])}' in main


def test_build_uat_checks_exposes_three_role_journeys():
    Base.metadata.create_all(engine)
    suffix = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        # Guarantee each journey has at least one role in the test database without
        # depending on execution order of older tests.
        for role in ('instructor', 'program_head', 'quality'):
            email = f'uat6707-{role}-{suffix}@local'
            user = m.AppUser(email=email, display_name=f'UAT {role}', auth_source='pilot', is_active=True)
            db.add(user); db.flush()
            db.add(m.UserRoleAssignment(user_id=user.id, role=role))
        db.commit()
        result = build_uat_checks(db, settings, '6.70-production-hardening')
    journeys = result.get('journeys') or []
    assert [j['key'] for j in journeys] == ['instructor', 'program_head', 'quality']
    assert all(j['checks'] and 0 <= j['score'] <= 100 for j in journeys)
    assert all(j['target_minutes'] <= 8 for j in journeys)


def test_6707_asset_cache_key_present():
    assert '6707-role-uat' in HTML
