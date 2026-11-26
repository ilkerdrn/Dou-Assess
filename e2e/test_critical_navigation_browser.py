from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Error as PlaywrightError, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _goto_or_skip(page, base_url: str) -> None:
    try:
        page.goto(base_url, wait_until="networkidle")
    except PlaywrightError as exc:
        if "ERR_BLOCKED_BY_ADMINISTRATOR" in str(exc):
            pytest.skip("Chromium localhost navigation is blocked by the execution environment policy")
        raise


def _wait_js(page, fn: str, timeout: float = 10.0) -> None:
    """Poll a page.evaluate() predicate from Python instead of page.wait_for_function(),
    whose string-eval polling is blocked by this app's strict CSP (script-src 'self',
    no unsafe-eval). page.evaluate() runs via CDP Runtime.callFunctionOn and is unaffected."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if page.evaluate(fn):
            return
        time.sleep(0.1)
    raise TimeoutError(f"condition not met within {timeout}s: {fn}")


def _wait_ready(base_url: str, timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(f"{base_url}/api/health", timeout=1.5).status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError("DOU Assess browser smoke server did not become ready")


def test_academic_program_review_and_evidence_hub_navigation() -> None:
    with tempfile.TemporaryDirectory(prefix="dou-assess-e2e-nav-") as td:
        tmp = Path(td); port = _free_port(); base_url = f"http://127.0.0.1:{port}"
        env = os.environ.copy(); env.update({
            "APP_ENV":"pilot", "DATABASE_URL":f"sqlite+pysqlite:///{tmp/'e2e.db'}",
            "AUTH_REQUIRED":"false", "AUTH_PROVIDER":"pilot", "PILOT_AUTH_ENABLED":"true",
            "PILOT_ADMIN_EMAIL":"e2e-admin@local", "PILOT_DEMO_ENABLED":"false",
            "RATE_LIMIT_ENABLED":"false", "STRICT_PRODUCTION_SECURITY":"false",
            "EVIDENCE_STORAGE_PATH":str(tmp/'evidence'), "SCAN_STORAGE_PATH":str(tmp/'scans'), "OPS_STORAGE_PATH":str(tmp/'ops'),
        })
        subprocess.run([sys.executable,"-m","alembic","upgrade","head"],cwd=ROOT,env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        proc = subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app","--host","127.0.0.1","--port",str(port),"--log-level","warning"],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        try:
            _wait_ready(base_url)
            headers={"X-DOU-Pilot-User":"e2e-admin@local"}
            with httpx.Client(base_url=base_url,headers=headers,timeout=5.0) as c:
                pr=c.post('/api/programs',json={'code':'E2E-NAV','name':'E2E Navigation','faculty':'MYO','department':'Bilgisayar'}); assert pr.status_code==201,pr.text
                pid=pr.json()['id']
                st=c.post('/api/students',json={'program_id':pid,'student_no':'E2E7001','full_name':'E2E Navigation Student','class_name':'1. Sınıf'}); assert st.status_code==201,st.text
                tpl=c.post('/api/program-review/templates',json={'code':'E2E-PR','version':'1.0','title':'E2E Program Review','sections':[{'key':'profile','title':'Program Profili','guidance':'Test'}]}); assert tpl.status_code==201,tpl.text
                rv=c.post(f'/api/programs/{pid}/program-reviews',json={'template_id':tpl.json()['id'],'academic_year':'2026-2027','title':'E2E Review','owner':'e2e-admin@local'}); assert rv.status_code==201,rv.text
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
                page=browser.new_page(viewport={'width':1440,'height':1000}); errors=[]
                page.on('console',lambda msg: errors.append(msg.text) if msg.type=='error' else None)
                page.add_init_script(
                    "localStorage.setItem('douPilotUser','e2e-admin@local');"
                    "localStorage.setItem('douPilotSession','1');"
                    "localStorage.setItem('douOnboarding615:e2e-admin@local','done');"
                )
                _goto_or_skip(page, base_url)
                page.locator('#loginGate').wait_for(state='hidden')
                # Admin pilot login starts with every nav group collapsed; expand the
                # group before clicking a submenu item it contains (6.70.3 Simple Panel).
                page.locator('#managementNavGroup .nav-group-toggle').click()
                # The "Öğrenciler" nav alias both switches the data view to students and
                # opens the student-create drawer (openAcademicForm); close the drawer
                # before interacting with the directory list/search behind it.
                page.locator('button[data-page="students"]').click(); page.locator('#page-data').wait_for(state='visible')
                page.locator('#academicDrawerClose').click()
                page.locator('#academicDataSearch').fill('E2E Navigation Student')
                _wait_js(page, "() => document.getElementById('academicDirectoryList').innerText.includes('E2E Navigation Student')")
                page.locator('#qualityNavGroup .nav-group-toggle').click()
                page.locator('button[data-page="programreview"]').click(); page.locator('#page-programreview').wait_for(state='visible')
                _wait_js(page, "() => document.getElementById('programReviewList').innerText.includes('E2E Review')")
                page.locator('button[data-page="evidencehub"]').click(); page.locator('#page-evidencehub').wait_for(state='visible')
                assert page.locator('#evidenceHubList').count()==1
                assert not errors, 'Browser console errors: ' + ' | '.join(errors)
                browser.close()
        finally:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=5)
