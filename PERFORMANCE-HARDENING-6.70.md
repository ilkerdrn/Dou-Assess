# DOU Assess 6.70 — Performance & Production Hardening

## Scope

6.70 does not add a new accreditation framework or redesign the product. It hardens the existing 6.69 product for larger university data volumes and more deterministic production deployments.

## Academic-scope query hardening

The old read path could load every program/course and repeatedly call Python authorization helpers. 6.70 adds SQL-native visible-program and visible-course selectors. Program, course, student and exam lists are constrained at the database boundary before rows are materialized.

The instructor semantics are unchanged: an instructor can read only explicitly assigned/owned courses and the programs that contain those courses. Program/department/faculty managers keep their existing scoped access; admin and quality retain institution-level read scope.

## Pagination and payload reduction

- `/api/programs`, `/api/courses`, `/api/students`, `/api/exams` now expose bounded `limit`/`offset` query contracts.
- `/api/question-bank` performs `q`, review-status, course/program/outcome filters in SQL and returns bounded pages.
- `/api/directory/summary` provides authorized aggregate program/course/student/exam counts plus per-program counts without downloading student rows.
- The frontend global bootstrap no longer downloads the student directory.
- Academic Data → Students uses 100-row server pages with search and program filters.
- Student Outcome Card uses server-side student search rather than a full-university dropdown.
- Course enrollment candidate selection queries only the selected program and optional student search.

## Frontend modularization

`runtime-core.js` now owns shared browser state, API/auth headers, downloads, toast messaging and HTML escaping. `app.js` consumes that runtime instead of carrying those primitives itself. This is the first safe extraction step; domain UI decomposition can continue without a framework rewrite.

## Database indexes

Migration `0042_performance_production_hardening` adds composite indexes for the highest-growth access paths, including course scope, student lookup, exam status, question-bank review, evidence integrity, audit/security events, scan review, operations queue/notifications, Program Review and Evidence Hub usage.

The migration changes no business data and adds no new domain columns.

## Dependency determinism and SBOM

- `requirements.txt` remains the human-maintained compatibility policy.
- `requirements.lock` is the exact production image dependency set.
- Docker installs from `requirements.lock` and runs `pip check` during image build.
- `SBOM-6.70.cdx.json` is a CycloneDX 1.5 inventory generated from the production lock.
- `Verify-Supply-Chain.sh` checks the lock/runtime and SBOM. If `pip-audit` or Trivy are unavailable, it reports that explicitly instead of claiming a vulnerability scan passed.

The current execution container has no Docker daemon and no external package DNS, so the isolated Docker dependency install could not be executed here. The university/CI Docker build is therefore a mandatory release acceptance step.

## Browser acceptance

Two Playwright flows are present:

1. Question Bank → create question → save → verify list.
2. Academic Data → server-side student search → Program Review → Evidence Hub navigation.

The current controlled Chromium environment blocks localhost with `ERR_BLOCKED_BY_ADMINISTRATOR`; these tests therefore skip only for that exact policy error. On CI/university test infrastructure they execute normally.

## Validation

- Target + recent-domain regression: 18/18 PASS.
- Full regression: 253/253 PASS (103 + 150 grouped execution).
- Fresh migration `0001 -> 0042`: PASS.
- Upgrade migration `0041 -> 0042`: PASS.
- Python compile: PASS.
- JavaScript syntax: PASS.
- Shell syntax: PASS.
- Compose YAML structure: PASS (`db`, `migrate`, `api`, `worker`, `scheduler`, `nginx`).
- Browser E2E in this environment: 2 SKIPPED due only to localhost administrator policy.
