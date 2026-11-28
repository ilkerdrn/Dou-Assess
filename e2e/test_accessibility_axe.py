"""WCAG 2.x A/AA taraması (axe-core): ana ekranlarda masaüstü ve telefon boyutunda ihlal olmamalı.

axe-core (MPL-2.0) `e2e/vendor/axe.min.js` içinde yerel kopya olarak durur; CSP satır içi betiğe izin vermediği için
`page.evaluate` ile (CDP) çalıştırılır.
"""
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


def _wait_ready(base_url: str, timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(f"{base_url}/api/health", timeout=1.5).status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError("axe test server did not become ready")


AXE = (Path(__file__).resolve().parent / "vendor" / "axe.min.js").read_text(encoding="utf-8")
PAGES = ["dashboard", "programanalytics", "outcomes", "curriculummap", "courses", "exams", "bank", "scan", "analytics",
         "courseanalytics", "studentcards", "evidencehub", "programreview", "quality360", "acceptance", "institutionalreadiness",
         "assessmentassurance", "assessmentmeasures", "surveys", "feedback", "security", "users", "import", "data", "mycourses", "grade", "print"]
RUN = "async () => { const x = await axe.run(document, {runOnly:{type:'tag', values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}}); return x.violations.map(v => v.id + ' x' + v.nodes.length); }"


def test_axe_no_wcag_aa_violations_on_main_pages() -> None:
    with tempfile.TemporaryDirectory(prefix="dou-assess-e2e-axe-") as td:
        tmp = Path(td); port = _free_port(); base_url = f"http://127.0.0.1:{port}"
        env = os.environ.copy(); env.update({
            "APP_ENV": "pilot", "DATABASE_URL": f"sqlite+pysqlite:///{tmp/'axe.db'}", "AUTH_REQUIRED": "false", "AUTH_PROVIDER": "pilot",
            "PILOT_AUTH_ENABLED": "true", "PILOT_ADMIN_EMAIL": "axe-admin@local", "PILOT_DEMO_ENABLED": "true", "RATE_LIMIT_ENABLED": "false",
            "STRICT_PRODUCTION_SECURITY": "false", "EVIDENCE_STORAGE_PATH": str(tmp/"evidence"), "SCAN_STORAGE_PATH": str(tmp/"scans"), "OPS_STORAGE_PATH": str(tmp/"ops"),
        })
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
                                cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            _wait_ready(base_url)
            httpx.post(f"{base_url}/api/pilot/demo-scenario", headers={"X-DOU-Pilot-User": "axe-admin@local"}, timeout=20.0)
            problems: list[str] = []
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_PATH") or None, args=["--no-sandbox", "--disable-dev-shm-usage"])
                for width, height in ((1440, 900), (390, 844)):
                    page = browser.new_page(viewport={"width": width, "height": height})
                    page.add_init_script("localStorage.setItem('douPilotUser','axe-admin@local');localStorage.setItem('douPilotSession','1');localStorage.setItem('douOnboarding615:axe-admin@local','done');")
                    try:
                        page.goto(base_url, wait_until="networkidle")
                    except PlaywrightError as exc:
                        if "ERR_BLOCKED_BY_ADMINISTRATOR" in str(exc):
                            pytest.skip("browser blocked localhost navigation in this environment")
                        raise
                    page.locator("#loginGate").wait_for(state="hidden")
                    page.evaluate(AXE)
                    for name in PAGES:
                        page.evaluate(f"showPage('{name}')"); time.sleep(0.5)
                        for v in page.evaluate(RUN):
                            problems.append(f"{width}px {name}: {v}")
                    page.close()
                browser.close()
            assert not problems, "axe WCAG ihlalleri:\n" + "\n".join(problems[:40])
        finally:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=5)
