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


def _wait_ready(base_url: str, timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            r = httpx.get(f"{base_url}/api/health", timeout=1.5)
            if r.status_code == 200:
                return
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as exc:  # pragma: no cover - diagnostic only
            last = repr(exc)
        time.sleep(0.25)
    raise RuntimeError(f"DOU Assess did not become ready: {last}")


def test_question_bank_create_end_to_end() -> None:
    """Real browser regression for the create-question path that escaped API tests."""
    with tempfile.TemporaryDirectory(prefix="dou-assess-e2e-") as td:
        tmp = Path(td)
        db_path = tmp / "e2e.db"
        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"
        env = os.environ.copy()
        env.update(
            {
                "APP_ENV": "pilot",
                "DATABASE_URL": f"sqlite+pysqlite:///{db_path}",
                "AUTH_REQUIRED": "false",
                "AUTH_PROVIDER": "pilot",
                "PILOT_AUTH_ENABLED": "true",
                "PILOT_ADMIN_EMAIL": "e2e-admin@local",
                "PILOT_DEMO_ENABLED": "false",
                "RATE_LIMIT_ENABLED": "false",
                "EVIDENCE_STORAGE_PATH": str(tmp / "evidence"),
                "SCAN_STORAGE_PATH": str(tmp / "scans"),
                "OPS_STORAGE_PATH": str(tmp / "ops"),
                "STRICT_PRODUCTION_SECURITY": "false",
            }
        )

        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            _wait_ready(base_url)
            headers = {"X-DOU-Pilot-User": "e2e-admin@local"}
            with httpx.Client(base_url=base_url, headers=headers, timeout=5.0) as client:
                p = client.post(
                    "/api/programs",
                    json={
                        "code": "E2E-IAT",
                        "name": "E2E İnternet ve Ağ Teknolojileri",
                        "faculty": "Meslek Yüksekokulu",
                        "department": "İnternet ve Ağ Teknolojileri",
                    },
                )
                assert p.status_code == 201, p.text
                program_id = p.json()["id"]
                c = client.post(
                    "/api/courses",
                    json={
                        "program_id": program_id,
                        "code": "E2E101",
                        "name": "E2E Ağ Temelleri",
                        "academic_year": "2026-2027",
                        "term": "Güz",
                        "instructor_email": "e2e-admin@local",
                        "instructor_name": "E2E Yönetici",
                        "pass_threshold_percent": 50,
                    },
                )
                assert c.status_code == 201, c.text

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    executable_path="/usr/bin/chromium",
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                console_errors: list[str] = []
                page.on(
                    "console",
                    lambda msg: console_errors.append(msg.text)
                    if msg.type == "error"
                    else None,
                )
                page.add_init_script(
                    "localStorage.setItem('douPilotUser','e2e-admin@local');"
                    "localStorage.setItem('douPilotSession','1');"
                    "localStorage.setItem('douOnboarding615:e2e-admin@local','done');"
                )
                _goto_or_skip(page, base_url)
                page.locator("#loginGate").wait_for(state="hidden")
                # workspaceNavGroup ships open by default (6.70.3 Simple Panel); no
                # toggle click needed here.
                page.locator('button[data-page="bank"]').click()
                page.locator("#page-bank").wait_for(state="visible")

                page.locator("#bankFocusCreate").click()
                _wait_js(
                    page,
                    "() => document.body.classList.contains('bank-editor-open') && "
                    "document.getElementById('bankEditorCard').classList.contains('is-open')"
                )
                assert page.locator("#bankCourse option").count() >= 1

                page.locator("#bankText").fill("E2E: TCP üç yönlü el sıkışmasının ilk paketi hangisidir?")
                page.locator("#bankChoiceA").fill("SYN")
                page.locator("#bankChoiceB").fill("ACK")
                page.locator("#bankChoiceC").fill("FIN")
                page.locator("#bankCorrect").select_option("A")

                with page.expect_response(
                    lambda r: r.url.endswith("/api/question-bank")
                    and r.request.method == "POST"
                ) as response_info:
                    page.locator("#saveBank").click()
                response = response_info.value
                assert response.status == 201, response.text()

                _wait_js(
                    page,
                    "() => document.getElementById('bankList').innerText.includes('TCP üç yönlü el sıkışmasının ilk paketi')"
                )
                assert not page.locator("body").evaluate(
                    "el => el.classList.contains('bank-editor-open')"
                )
                assert not console_errors, "Browser console errors: " + " | ".join(console_errors)
                browser.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
