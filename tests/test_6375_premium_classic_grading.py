from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')
JS = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
CSS = (ROOT / 'app/static/styles.css').read_text(encoding='utf-8')


def test_classic_grading_has_student_and_question_modes():
    assert 'id="gradeMode"' in HTML
    assert 'Öğrenci bazlı' in HTML
    assert 'Soru bazlı seri' in HTML
    assert 'id="gradeQuestion"' in HTML


def test_classic_grading_has_blind_mode():
    assert 'id="gradeBlind"' in HTML
    assert 'Kör değerlendirme' in HTML
    assert 'Aday ${String(i+1).padStart(3,\'0\')}' in JS
    assert 'Kimlik puanlama tamamlanana kadar gizli' in JS


def test_rubric_has_fast_presets_and_keyboard_shortcuts():
    assert 'rubricPresetValues' in JS
    assert 'data-rubric-score' in JS
    assert "['1','2','3','4','5']" in JS
    assert "ev.key==='Enter'" in JS
    assert "ev.key==='ArrowRight'" in JS
    assert '.rubric-fast.active' in CSS


def test_serial_mode_filters_to_classic_question():
    assert "q.question_type==='classic'&&q.id===qid" in JS
    assert "gradeMode()==='question'" in JS


def test_expected_answer_is_available_during_classic_grading():
    assert 'Beklenen cevap / değerlendirme anahtarı' in JS
