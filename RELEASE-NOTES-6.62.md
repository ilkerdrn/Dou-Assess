# DOU Assess 6.62 — Program Assessment Assurance

- Adds a versioned annual **Program Assessment Assurance Plan** for every program and academic year.
- Connects each Program Outcome (PÇ) to explicit direct and indirect assessment methods, owner, term/frequency, target, due date and expected evidence.
- Adds `Mevcut kanıttan plan oluştur` auto-build using the existing approved exam engine, Generic Assessment Measures and PÇ-mapped survey templates.
- Assurance analytics only count evidence from sources explicitly selected in the plan; unrelated evidence cannot satisfy a planned method.
- Adds normalized direct/indirect weighting and PÇ-level states: `not_planned`, `plan_gap`, `awaiting_evidence`, `achieved`, `below_target`.
- Adds plan coverage, evidence completeness, target attainment, below-target and plan-gap summary KPIs.
- Adds editable plan items before closure and strict source provenance checks (program/year/channel/source-type consistency).
- Adds immutable year-end review snapshots. A final review freezes the plan; later changes require a new plan version. Reviewed plans may only be archived.
- Adds controlled PUKÖ creation for fully evidenced PÇ results that remain below target, using the existing QualityCycle engine.
- Adds the premium `Ölçme Güvence Planı` workspace to the academic/quality navigation.
- Preserves 6.61 Survey & Indirect Assessment, 6.60 Generic Assessment/Rubric, exam/OMR/classic grading, Quality360, MEDEK/MÜDEK and accreditation lifecycle behavior.
