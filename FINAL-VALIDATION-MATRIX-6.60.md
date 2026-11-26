# DOU Assess 6.60 — Generic Assessment Measure + Rubric Engine Validation

- Version: `6.60-generic-assessment-rubric`
- Schema: `0034_generic_assessment_rubric`
- New entities: AssessmentMeasure, RubricTemplate, RubricCriterion, RubricLevel, AssessmentMeasureOutcome, AssessmentMeasureResult.
- Measure types: exam, assignment, project, presentation, laboratory, internship, portfolio, capstone, practical, peer assessment.
- Reusable versioned rubric templates support criteria, performance levels and optional Learning Outcome links.
- Measure results validate rubric criterion score bounds server-side and derive total score from rubric criteria when a rubric is attached.
- Measure -> Learning Outcome links keep alternative assessment inside the existing outcome-analysis chain.
- Instructor/management UI: `Ölçme Planı & Rubrik`.
- Target 6.60 tests: 3/3 PASS.
- Full regression: 212/212 PASS via isolated/grouped execution (suite has known process teardown wait in monolithic execution).
- Fresh migration `0001 -> 0034_generic_assessment_rubric`: PASS.
- Upgrade `0033_curriculum_outcome_map -> 0034_generic_assessment_rubric`: PASS.
- Acceptance: Classic Scan PASS; Legacy Classic PASS; Complete Engine PASS; Lifecycle PASS; Pilot UAT 41/41 PASS (`accreditation_ready=true`).
