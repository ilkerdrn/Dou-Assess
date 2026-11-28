from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')

def test_6708_asset_key():
    assert '6708-friction-closure' in HTML

def test_6708_question_bank_progressive_disclosure_and_serial_entry():
    assert 'bank-advanced-fields' in HTML
    assert 'id="saveBankAndNew"' in HTML
    assert 'bankSaveContinue' in JS
    assert "document.getElementById('bankText')?.focus()" in JS

def test_6708_exam_can_jump_to_questions_after_create():
    assert 'id="examCreateAndQuestions"' in HTML
    assert 'data-exam-create-next="3"' in HTML
    assert 'examCreateNextStep' in JS
    assert 'setExamWizardStep(nextStep)' in JS

def test_6708_grading_single_active_exam_is_auto_opened():
    assert "const grading=gradeQueueRows().filter(x=>x.status==='grading')" in JS
    assert 'grading.length===1' in JS
    assert 'await loadCurrentGrade()' in JS

def test_6708_quality_cycle_is_progressive():
    assert 'puko-progressive-details' in HTML
    assert 'Ne iyileştirilecek ve hedef ne?' in HTML
    assert "PUKÖ'yü başlat" in HTML

def test_6708_evidence_can_continue_to_cycle():
    assert 'id="q360EvidenceThenCycle"' in HTML
    assert 'q360EvidenceThenCycle' in JS
    assert "setQ360Workspace('cycle')" in JS

def test_6708_mobile_layout_for_new_actions():
    assert '.exam-create-actions' in CSS
    assert '.bank-save-actions' in CSS
