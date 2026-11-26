# DOU Assess 6.61 — Survey & Indirect Assessment Engine

- Adds a program-level Survey & Indirect Assessment Engine for student, graduate, employer, external stakeholder, faculty, course-evaluation and program-evaluation surveys.
- Adds versioned survey templates, typed questions, campaign lifecycle and public campaign tokens.
- Survey questions can map directly to Program Outcomes (PÇ), Program Educational Objectives (PEA) or quality/accreditation criterion codes.
- Anonymous campaigns do not persist respondent keys or respondent metadata. Identified campaigns store only a SHA-256 respondent-key hash for duplicate prevention.
- Adds public survey read/submit endpoints behind opaque campaign tokens; campaigns must be open and inside their date window.
- Adds campaign analytics with normalized Likert/NPS scores and target attainment.
- Adds program-level indirect assessment analytics by academic year.
- Adds transparent Direct + Indirect Program Outcome evidence mix. Default UI view is 70% direct / 30% indirect; a combined result is emitted only when both channels have evidence.
- Direct evidence combines approved/archived exam outcome analytics with Generic Assessment Measure results (project, assignment, lab, internship, etc.).
- Adds the `Anket & Dolaylı Ölçüm` management workspace to the academic structure navigation.
- Existing exam, OMR, classic grading, Quality360, MEDEK/MÜDEK and student-card workflows remain compatible.
