from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')
API=(ROOT/'app/program_review_api.py').read_text(encoding='utf-8')

def test_6711_asset_key():
    assert '6711-accreditation-evidence' in HTML

def test_accreditation_is_action_first():
    assert 'id="accredDecision"' in HTML
    assert 'Detaylı akreditasyon analizi' in HTML
    assert 'renderAccredDecision' in JS
    assert 'data-accred-next' in JS
    for phrase in ['ders henüz ölçülmedi','Öğrenim Çıktısı açığı aksiyonsuz','Temsilî öğrenci kanıtları eksik','kontrol kaldı']:
        assert phrase in JS

def test_evidence_hub_has_health_summary_and_decision():
    assert 'id="evidenceHubDecision"' in HTML
    assert 'id="evidenceHubKpis"' in HTML
    assert 'Eksik / kontrol bekleyen' in HTML
    assert 'loadEvidenceHubSummary' in JS
    assert 'KANIT KARARI' in JS

def test_evidence_summary_endpoint_aggregates_health():
    assert '@router.get("/api/evidence-hub/summary")' in API
    for key in ['verified','attention','unchecked','mismatch','missing','used_in_review','duplicate_groups']:
        assert f'"{key}"' in API

def test_integrity_labels_are_human_readable():
    for label in ['Doğrulanmış','Kontrol bekliyor','Hash uyuşmazlığı','Dosya eksik']:
        assert label in JS

def test_6711_responsive_decision_css():
    assert '.accred-decision-brief' in CSS
    assert '.evidence-decision-brief' in CSS
    assert '.evidence-health-kpis' in CSS
    assert '.accred-advanced-details' in CSS
