# DOU Assess 6.58 — Academic Structure Foundation Validation

- Version: `6.58-academic-structure-foundation`
- Schema: `0032_academic_structure_foundation`
- New canonical academic hierarchy: AcademicUnit -> Program -> CurriculumVersion -> CourseCatalogItem -> CourseOffering -> TeachingAssignment.
- Existing Program.faculty/department and Course operational contracts preserved for backward compatibility.
- Upgrade backfill from 0031 creates Doğuş root, faculty/MYO/department units, transition curriculum/catalog records, default A sections, instructor assignments, and links existing enrollments/exams.
- Target academic structure tests: 3/3 PASS.
- Full regression: 206/206 PASS (validated in isolated groups: core 39; other groups 37+38+50+42).
- Acceptance: Classic Scan PASS; Legacy Classic PASS; Complete Engine PASS; Lifecycle PASS; Pilot UAT 41/41 PASS (`accreditation_ready=true`).
- Fresh 0001 -> 0032 migration: PASS.
- 0031 -> 0032 legacy backfill migration: PASS.
