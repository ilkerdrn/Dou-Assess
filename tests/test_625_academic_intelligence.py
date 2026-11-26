from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/static/index.html').read_text(encoding='utf-8')
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
MAIN=(ROOT/'app/main.py').read_text(encoding='utf-8')
QUALITY=(ROOT/'app/services/quality.py').read_text(encoding='utf-8')

def test_625_navigation_and_pages_contract():
    soup=BeautifulSoup(HTML,'html.parser')
    assert soup.find(id='workspaceNavGroup') is not None
    assert soup.find(id='page-mycourses') is not None
    assert soup.find(id='page-courseanalytics') is not None
    assert soup.find(id='page-programanalytics') is not None
    assert 'Derslerim' in HTML and 'Ders Sonuçları' in HTML and 'Program Analizi' in HTML

def test_625_analytics_api_contract():
    assert '/api/courses/{course_id}/analytics-overview' in MAIN
    assert '/api/programs/{program_id}/analytics-overview' in MAIN
    assert 'def course_lineage_analytics' in QUALITY
    assert 'program_id == seed.program_id' in QUALITY and 'm.Course.code == seed.code' in QUALITY

def test_625_teacher_micro_flow_contract():
    assert 'Ders bağlamını koruyun' in JS
    assert 'prepareMyCourses' in JS and 'openCourseActionPanel' in JS
    assert "showPage(isQualityOnly()?'quality360':'dashboard')" in JS
    assert 'courseanalytics' in JS and 'programanalytics' in JS
