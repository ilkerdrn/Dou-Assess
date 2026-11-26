# DOU Assess 6.67 — Final Validation Matrix

- Version: `6.67-evidence-integrity-security`
- Schema: `0039_evidence_integrity_security`
- 6.67 + compliance targeted regression: **12/12 PASS**.
- Full source regression: **235/235 PASS**.
- Fresh migration `0001 -> 0039`: **PASS**.
- Realistic upgrade path built with original 6.66.1 source `0038`, then upgraded by 6.67 to `0039`: **PASS**.
- New evidence-integrity, maker-checker and evaluator-token columns present after both migration paths: **PASS**.
- `app.js` / `evaluator.js` JavaScript syntax: **PASS**.
- Python application/migration compile: **PASS**.
- Question Bank Playwright E2E test source: **IMPLEMENTED**.
- Browser execution in this managed build environment: **BLOCKED BY RUNNER POLICY** (`ERR_BLOCKED_BY_ADMINISTRATOR` for localhost); not reported as a product PASS. Run `python -m pytest -q e2e/test_question_bank_browser.py` on CI/university test server.

## Security behaviors validated

- fake PDF content rejected even with `.pdf` extension;
- tampered Quality360 evidence returns 409 and records `mismatch`;
- tampered exam evidence blocks direct download and evidence-package generation;
- controlled document cannot be directly created as approved;
- preparer cannot review their own controlled-document revision;
- authenticated second actor can review/approve;
- malformed DOCX is rejected;
- evaluator raw token is shown only in create response and token hash is not returned;
- wrong evaluator token -> 401;
- valid evaluator token -> read-only snapshot;
- revoked workspace -> 410;
- evaluator portal and integrity-scan UI contracts exist.

## Deliberately external acceptance

This source validation does not auto-pass physical ADF/OMR field benchmarking, off-site backup/restore/DR rehearsal, target-period official-template sign-off or real-program institutional UAT. Entra and OBS were explicitly outside the 6.67 scope requested for this work.
