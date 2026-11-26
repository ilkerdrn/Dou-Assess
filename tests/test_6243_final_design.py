from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')
CSS = (ROOT / 'app/static/styles.css').read_text(encoding='utf-8')
MAIN = (ROOT / 'app/main.py').read_text(encoding='utf-8')


def test_6243_final_design_contract():
    soup = BeautifulSoup(HTML, 'html.parser')
    ids = [node['id'] for node in soup.find_all(id=True)]
    assert len(ids) == len(set(ids))

    # 6.38 supersedes the permanent setup rail with role-based navigation.
    assert soup.select_one('#workspaceNavGroup') is not None
    assert soup.select_one('#managementNavGroup') is not None
    assert soup.select_one('.workflow-nav') is None

    # Academic quick actions mirror the same order and include the previously missing Exam step.
    actions = soup.select_one('.academic-hero-actions')
    action_ids = [x.get('id') for x in actions.select('button')]
    assert action_ids[:4] == ['dataNewProgram', 'dataNewCourse', 'dataNewExam', 'dataNewStudent']

    # The question editor is a focused drawer instead of a permanent narrow column.
    assert soup.find(id='bankEditorBackdrop') is not None
    assert soup.find(id='bankEditorClose') is not None
    assert 'Question bank: library is the page; editor is a focused drawer.' in CSS
    assert '#page-bank .bank-editor-card' in CSS and 'position:fixed!important' in CSS

    # Final design layer and server version are deliberately pinned.
    assert '6.25 · FINAL DESIGN SYSTEM' in CSS
    assert '6.70-production-hardening' in MAIN
