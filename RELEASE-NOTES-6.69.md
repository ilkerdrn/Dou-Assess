# DOU Assess 6.69 — Program Review & Evidence Hub 2.0

Release: `6.69-program-review-evidence-hub`  
Schema: `0041_program_review_evidence_hub`  
Built: `2026-09-15T17:51:20Z`

## Scope

6.69 adds an institution-wide periodic Program Review workflow and a unified Evidence Hub without duplicating existing evidence files. Existing exam, Quality360 and controlled-document evidence remain in their original storage and are referenced by source type/id.

## Program Review

- Versioned review templates with ordered sections and guidance.
- Program + academic year + review number lifecycle.
- Contributor / reviewer maker-checker workflow.
- Contributor cannot change governed reviewer/contributor/deadline assignments.
- Contributor and reviewer cannot be the same person.
- Reviewer assignment is required before submission.
- Section states: not started, in progress, submitted, approved, changes requested.
- Evidence links to exam, Quality360 and controlled-document sources.
- Finalization only when every section is approved.
- Final snapshot freezes narrative plus evidence title/context/category/SHA-256/integrity metadata.
- Final snapshot is SHA-256 sealed and can be re-verified through the API/UI.
- Final/archived reviews are immutable; a new review version is required for later changes.

## Evidence Hub 2.0

- Unified search across exam evidence, Quality360 evidence and controlled document revisions.
- Program, source, integrity, tag and free-text filters.
- Pagination.
- Evidence tags with backend role enforcement.
- Program Review usage chain (“where is this evidence used?”).
- Duplicate SHA-256 grouping.
- Direct evidence linking from Program Review section to Evidence Hub.
- Evidence files are not copied into a new registry.

## Security and authorization

- Evidence usage results are restricted to Program Reviews visible to the current user.
- Evidence tag mutation requires quality/program-management authority.
- Program Review contributor can edit narrative but cannot reassign governance fields.
- Final snapshot stores evidence SHA metadata for later auditability.

## Validation

- 6.69 target tests: 6/6 PASS.
- Full regression: 247/247 PASS (103 + 144 grouped execution).
- Fresh migration `0001 -> 0041`: PASS.
- Realistic upgrade `0040 -> 0041`: PASS.
- JavaScript syntax: PASS.
- Python compile: PASS.
- Docker CLI was not available in the packaging runtime; Compose files were retained from the already validated 6.68 base and shell scripts are syntax-checked separately.
