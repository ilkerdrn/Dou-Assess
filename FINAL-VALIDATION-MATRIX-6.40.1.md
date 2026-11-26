# DOU Assess 6.40.1 — Final Validation Matrix

Validation date: 2026-09-10
Application version: `6.40.1-question-bank-runtime-evaluation-mapping-hotfix`
Schema head: `0024_mapping_contribution_1_5`

## Green / passed

- ZIP/package source manifest integrity: PASS.
- Python compile (`app`, `migrations`, `tests`): PASS.
- JavaScript syntax (`app/static/**/*.js`): PASS.
- Bash syntax (`*.sh`): PASS.
- Pytest regression suite: 134/134 PASS.
- Clean Alembic migration chain: `0001_initial -> 0024_mapping_contribution_1_5`: PASS.
- Legacy contribution normalization: 0 -> 1 in `outcome_mappings` and `exam_outcome_mappings`: PASS.
- DB contribution guard: values 0 and 6 rejected; allowed scale is 1..5: PASS.
- Question Bank `+ Yeni soru oluştur`: independent runtime binding and immediate editor open: PASS.
- MCQ client validation / minimum option handling: PASS.
- Evaluation color semantics: student selection yellow, correct answer green, wrong selected answer red: PASS.
- ÖÇ -> PÇ contribution scale 1..5 across schema/UI/migration: PASS.
- Classic scan grading acceptance: PASS.
- Legacy classic scan acceptance: PASS.
- Complete assessment engine acceptance: PASS.
- Lifecycle acceptance: PASS.
- Pilot UAT 1-9: 41/41 PASS; accreditation_ready=true.
- Runtime Uvicorn smoke using packaged `Verify-Server.sh`: `/api/health`, `/api/ready`, catalogs and Quality360 frameworks PASS.
- Delivery hygiene: `data/evidence`, `data/scans`, `data/ops` contain only `.gitkeep`; no delivery SQLite DB.
- Stale server verifier success label corrected from 6.37.4 to 6.40.1.

## Institution / production acceptance still required

These are environment-bound, not local package failures:

- Real Microsoft Entra ID tenant/client/scope/role mapping acceptance.
- Real OBS/Proliz integration contract, sample payload and reconciliation acceptance.
- Production Docker/PostgreSQL/NGINX run on the university server.
- Production TLS/DNS and reverse-proxy acceptance.
- Physical printer / ADF / OMR field acceptance.
- Target-server load, backup/restore and disaster-recovery rehearsal.

## Final local package verdict

**PASS — SERVER-READY candidate.**

Local/source/package validation is green. Production/institution integration items remain site acceptance gates.
