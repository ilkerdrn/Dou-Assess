from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/styles.css').read_text(encoding='utf-8')
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
HOT=(ROOT/'app/static/question-bank-hotfix-6401.js').read_text(encoding='utf-8')
MIG=(ROOT/'migrations/versions/0024_mapping_contribution_1_5.py').read_text(encoding='utf-8')
MODELS=(ROOT/'app/models.py').read_text(encoding='utf-8')


def test_question_bank_button_has_independent_runtime_binding():
    # 6.66.1 closes the old standalone 6.40.1 runtime hotfix into app.js.
    assert 'question-bank-hotfix-6401.js' not in HTML
    assert 'window.openNewBankQuestion=openNewBankQuestion' in JS
    assert "closest?.('#bankFocusCreate')" in JS
    body=JS.split('async function openNewBankQuestion()',1)[1].split("document.getElementById('bankCourse')",1)[0]
    assert 'refreshCore()' in body
    full=JS.split('async function openNewBankQuestion()',1)[1].split("document.getElementById('bankCourse')?.addEventListener",1)[0]
    assert full.index('setBankEditorOpen(true)') < full.index('updateBankCourseContext()')


def test_evaluation_semantic_colors_are_real_css_not_escaped_text():
    block=CSS.split('/* 6.40 evaluation semantics + mapping scale */',1)[1]
    assert '\\n.grade-' not in block
    assert '.grade-choice-buttons button.is-student-selected' in block
    assert '#f6c344' in block
    assert '.grade-choice-buttons button.is-correct-answer' in block and '#21a366' in block
    assert '.grade-choice-buttons button.is-wrong-selection' in block and '#d92d20' in block


def test_contribution_migration_normalizes_legacy_zero_and_guards_both_tables():
    assert 'UPDATE outcome_mappings SET contribution = 1 WHERE contribution < 1' in MIG
    assert 'UPDATE exam_outcome_mappings SET contribution = 1 WHERE contribution < 1' in MIG
    assert 'contribution >= 1 AND contribution <= 5' in MIG
    assert 'ck_exam_contribution_1_5' in MODELS
