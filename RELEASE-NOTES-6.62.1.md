# DOU Assess 6.62.1 — PostgreSQL Production Migration Hotfix

## Scope

6.62.1 is a canonical packaging/migration hotfix for the 6.62 Program Assessment Assurance release. It does not introduce new business functionality.

## Fixed

- `0032_academic_structure_foundation` no longer inserts integer `1` into PostgreSQL `BOOLEAN` columns.
- Seed inserts for `academic_units.is_active` and `course_catalog_items.is_active` now use PostgreSQL-compatible `TRUE` literals.
- A regression test prevents reintroduction of the production-only `BOOLEAN` datatype mismatch.
- Release metadata identifies the canonical package as `6.62.1` while preserving the application capability version `6.62-program-assessment-assurance` and schema head `0036_program_assessment_assurance`.
- Delivery hygiene is re-applied before sealing: no runtime database, pytest cache, Python bytecode or runtime evidence/scan/ops artifacts are included.

## Production incident reproduced

The university-server upgrade path from schema `0025_accreditation_compliance_core` reached `0032_academic_structure_foundation` and PostgreSQL rejected `is_active=1` with a datatype mismatch. The migration is transactional; after the source hotfix the upgrade can be retried against the same persistent Compose project/volumes.
