from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")

def test_626_progressive_disclosure_contract():
    soup = BeautifulSoup(HTML, "html.parser")
    assert soup.find(id="academicDrawerClose") is not None
    assert soup.find(id="academicDrawerBackdrop") is not None
    assert soup.find(id="academicNewRecord") is not None
    assert "drawer-open" in JS and "closeAcademicDrawer" in JS
    assert "openProgramWorkspace" in JS
    assert ".academic-create-panel.drawer-open" in CSS

def test_626_grading_focus_contract():
    assert "grade-student-identity" in JS
    assert "grade-student-metrics" in JS
    assert "Bu sınavda değerlendirilecek soru yok" in JS
    assert ".grade-student-summary" in CSS
    assert ".grade-empty" in CSS

def test_626_premium_program_cards_and_version():
    assert "premium-program-card" in JS
    assert "program-card-metrics" in JS
    assert "Programa gir" in JS
    assert "6.26 PREMIUM EXPERIENCE" in CSS
    assert "6.70-production-hardening" in MAIN
