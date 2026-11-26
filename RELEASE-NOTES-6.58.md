# DOU Assess 6.58 — Academic Structure Foundation

- Added hierarchical AcademicUnit model (institution/campus/faculty/vocational school/institute/department/center).
- Programs can link to a canonical academic unit while legacy faculty/department text remains compatible.
- Added CurriculumVersion, CourseCatalogItem, CurriculumCourse, CourseOffering and TeachingAssignment models.
- Added optional offering links on enrollments and exams and catalog links on courses.
- Added modular Academic Structure API router.
- 0032 migration backfills existing flat academic data into the new hierarchy, creates a transition curriculum/catalog, creates default section A offerings, and links existing enrollment/exam rows.
- Existing assessment/accreditation APIs remain backward compatible.
