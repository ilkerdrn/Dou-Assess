# DOU Assess 6.67 — Evidence Integrity & Security

Version: `6.67-evidence-integrity-security`  
Schema: `0039_evidence_integrity_security`

## Scope

6.67 is a security/integrity closure release. It does not redesign the UI and does not expand Entra or OBS integration. It hardens the evidence lifecycle, controlled-document approvals and external evaluator access while adding a browser-regression baseline for the Question Bank create flow.

## Evidence integrity

- Exam evidence, Quality360 evidence and controlled-document revisions now carry `integrity_status` and `integrity_checked_at`.
- Uploads start as `verified` after SHA-256 is calculated.
- Download/preview/package paths re-read the physical file and compare its SHA-256 with the database record.
- Missing physical evidence returns 404; a hash mismatch returns 409 and records an audit/security trail instead of silently serving altered content.
- `POST /api/security/evidence-integrity/scan` performs a batch verification across the managed evidence stores.
- The System & Security UI exposes this scan and summarizes verified/mismatch/missing results.

## Upload Security Gateway

- Quality360 evidence, controlled-document binary revisions and official templates use content-aware validation instead of trusting filename or browser MIME alone.
- PDF/JPEG/PNG payloads are validated by format signature/parser.
- DOCX/XLSX containers are checked for required package structure.
- ZIP/Office containers reject encrypted members, traversal/absolute paths, excessive member counts, suspicious compression ratios and configured uncompressed-size limits.
- Text-like uploads reject binary NUL payloads.

An external antivirus engine is not bundled into the application container in this release; infrastructure-level malware scanning can be added separately without weakening the content-validation gate above.

## Controlled Document maker-checker

Controlled revisions can no longer be created directly as approved.

`draft -> submitted -> reviewed -> approved`

- `prepared_by`, submit/review timestamps and authenticated reviewer/approver identity are recorded by the server.
- The preparer cannot review or approve their own revision.
- Approval supersedes the previous approved revision through the existing controlled-document version model.
- Binary revision downloads also enforce SHA-256 integrity.

## External Evaluator security

- Evaluator workspaces receive a cryptographically random one-time invitation token.
- Only the SHA-256 token hash is persisted.
- Tokens are time-bounded (14 days by default), workspace access can be revoked, and expired/inactive workspaces return 410.
- Bad tokens return 401 using constant-time hash comparison.
- Public access updates `last_access_at` and writes an audit event.
- A dedicated `/evaluator.html` read-only portal consumes the token from the URL fragment, removes it from the address bar after loading, and displays the frozen application/framework snapshot, document requests, findings and evaluator-visible visit notes.
- The internal UI now surfaces the one-time invitation link instead of discarding the create response.

## Question Bank browser regression

`e2e/test_question_bank_browser.py` covers:

`Soru Bankası -> + Yeni soru oluştur -> editor opens -> POST /api/question-bank -> question appears in library`

The test starts an isolated database and Uvicorn process and uses real Chromium/Playwright. The managed ChatGPT execution environment blocks browser navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`, so browser execution itself must be run on CI or the university test server. The E2E source is included and ready to run.

## Migration safety

Migration `0039_evidence_integrity_security` is conditional/idempotent because historical migration `0025` creates some tables from live SQLAlchemy metadata. This preserves both:

- fresh `0001 -> 0039` installs, and
- real `6.66.1 / 0038 -> 6.67 / 0039` upgrades.

No existing evidence file is renamed or deleted by the migration.
