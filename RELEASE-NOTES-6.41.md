# DOU Assess 6.41 — Accreditation Compliance Core

**Release date:** 2026-09-10  
**Application version:** `6.41-accreditation-compliance-core`  
**Schema head:** `0025_accreditation_compliance_core`

6.41 builds on the validated 6.40.1 assessment engine and closes the previous product-level accreditation/compliance gaps with an operable data model, API, UI, exports, versioning, hashing and audit trail.

## New compliance capabilities

- Versioned accreditation framework registry and immutable framework snapshots with SHA-256.
- YÖKAK KİDR criterion tree with 14 criteria and 46 subcriteria; evidence can be attached at subcriterion level.
- Versioned report/template registry for MÜDEK, MEDEK, TURAK, SABAK, EPDAD and YÖKAK.
- Official template vault: DOCX/XLSX/PDF/ZIP uploads are stored with SHA-256 integrity metadata and can be frozen by framework/version.
- Program Educational Objectives (PEA) and PEA → Program Outcome mapping.
- Program Outcome components and component codes.
- Cumulative student/graduate Outcome Card covering ÖÇ → PÇ → PÇ component attainment, plus frozen graduation snapshots.
- Standard Course File / Course Information Package DOCX output.
- Curriculum/ECTS checks with framework threshold support.
- Versioned faculty CV snapshots for YÖKSİS/ÜAK-style archival use.
- Faculty workload ledger by academic year, term and course.
- Graduate longitudinal follow-up including 1/3/5-year checkpoints.
- MÜDEK BBO/FBO virtual evidence room presets and ZIP export containing actual evidence files plus manifest/index and hashes.
- Controlled document management for policy/directive/procedure/form revisions, approvals and SHA-256.
- Program/year budget planning, budget lines, funding sources and variance tracking.
- Infrastructure/laboratory maintenance records tied to capacity, accessibility and OHS evidence.
- YÖKAK mission-domain activities for research & development, social contribution and internationalization with KPI, budget, partner, participant and evidence fields.
- Accreditation lifecycle covering preparation, submission, preliminary review, correction, visit preparation, site visit, response, decision and closure.
- Read-only evaluator workspace with frozen snapshot hash and additional-document request/response workflow.
- 30-item Accreditation Compliance Matrix and DOCX export.

## Compatibility

- Existing assessment, question bank, OMR/ADF, classic grading, rubrics, ÖÇ/PÇ analytics, evidence readiness, PUKÖ, governance, Quality360, audit, Docker/PostgreSQL/NGINX and OBS/Entra integration scaffolding are preserved.
- Database upgrade path: `0024_mapping_contribution_1_5 -> 0025_accreditation_compliance_core`.
- Fresh migration path: `0001_initial -> 0025_accreditation_compliance_core`.

## Validation result

- Full pytest regression: **140/140 PASS**.
- 6.41-specific compliance suite: **6/6 PASS**.
- Pilot UAT 1–9: **41/41 PASS**, `accreditation_ready=true`.
- Classic scan grading, legacy classic scan, complete engine and lifecycle acceptance: **PASS**.
- Python compile, JavaScript syntax and Bash syntax: **PASS**.
- Uvicorn runtime smoke: health, readiness, catalog and Quality360 framework endpoints: **PASS**.

## Important boundary

A green item means the capability exists inside DOU Assess and has an implementation/test path. It does **not** mean an accreditation body has formally approved the institution or that a live institutional integration has been accepted. Real Entra, Proliz/OBS, production infrastructure, physical ADF/OMR, backup/restore and official-current template content remain site/institution acceptance gates.
