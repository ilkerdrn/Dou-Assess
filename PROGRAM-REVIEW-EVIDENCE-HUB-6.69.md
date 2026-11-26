# Program Review & Evidence Hub 2.0 — 6.69

## Program Review lifecycle

1. Quality/admin creates or selects a versioned review template.
2. A review cycle is created for a program and academic year.
3. Each section receives a contributor, reviewer and optional deadline.
4. Contributor prepares the narrative and links existing institutional evidence.
5. Section is submitted to the reviewer.
6. Reviewer approves or requests changes.
7. All sections must be approved before finalization.
8. Finalization creates a JSON snapshot and SHA-256 seal.
9. Final reviews are immutable; subsequent work starts a new review number.

## Final evidence manifest

The final snapshot includes, for each linked evidence item:

- source type and source id
- link note and actor
- evidence title/category/context
- program id where applicable
- SHA-256
- integrity status

This preserves an auditable manifest even if the live source record later changes.

## Evidence Hub 2.0

Evidence Hub reads live records from three source systems:

- Exam evidence (`EvidenceAsset`)
- Quality360 evidence (`QualityEvidenceAsset`)
- Controlled document revisions (`ControlledDocumentRevision`)

It does not copy the physical file. Tags and Program Review links are metadata relationships only.

### Main capabilities

- global evidence search
- program/source/integrity/tag filtering
- pagination
- evidence tagging
- duplicate content detection by SHA-256
- Program Review usage chain
- direct linking to a selected review section

## Governance rules

- contributor and reviewer must be different people
- reviewer must be assigned before submit
- governed assignment fields require quality/program-management authority
- tag writes require quality/program-management authority
- evidence visibility and usage visibility are scoped by server-side authorization
- final review content cannot be changed
