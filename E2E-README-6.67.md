# DOU Assess 6.67 Browser E2E

The first browser regression covers the production defect class that escaped API/unit tests:

`Soru Bankası -> + Yeni soru oluştur -> editor opens -> question POST -> question appears in library`

Run on a CI runner or the university test server with Chromium and Playwright installed:

```bash
python -m pytest -q e2e/test_question_bank_browser.py
```

The test creates an isolated temporary SQLite database, applies Alembic to head, starts a local Uvicorn process, seeds a pilot program/course, drives the real browser UI and asserts there are no console errors.

Some managed ChatGPT execution environments block browser navigation to localhost with `ERR_BLOCKED_BY_ADMINISTRATOR`. That platform policy is not treated as an application failure; run this test in CI/server where loopback browser access is permitted.
