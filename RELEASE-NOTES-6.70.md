# DOU Assess 6.70 — Release Notes

**Release:** `6.70-production-hardening`  
**Schema:** `0042_performance_production_hardening`

6.70 is a production hardening release. It keeps the 6.69 Program Review, Evidence Hub, Quality360, assessment, accreditation and operations behavior while reducing unnecessary data loading and making production builds more deterministic.

## Highlights

- Database-scoped academic authorization queries replace Python row-by-row visibility filtering on major read paths.
- Server-side pagination/search for students and Question Bank.
- Authorized directory aggregate endpoint prevents loading all students just to calculate counts.
- Student directory and Student Outcome Card become demand-loaded/search-driven.
- Shared frontend runtime extracted to `runtime-core.js` without redesigning the UI.
- Composite query indexes added with schema revision 0042.
- Exact production dependency lock and CycloneDX SBOM added.
- Docker build now installs the lock and requires `pip check`.
- Browser regression coverage expanded beyond Question Bank to academic data, Program Review and Evidence Hub navigation.

## Compatibility

No existing business table is rewritten. Migration 0042 adds indexes only. Existing PostgreSQL data, evidence/scans/ops volumes, Entra configuration and OBS configuration are not migrated by this release.

## Acceptance caveat

The local execution environment has no Docker daemon/external package DNS and its Chromium policy blocks localhost. Therefore Docker dependency resolution and browser execution must be completed on the university/CI environment. Source regression and migration gates are complete.
