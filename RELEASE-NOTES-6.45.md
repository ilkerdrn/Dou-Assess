# DOU Assess 6.45 — MEDEK ÖDR Evidence Matrix

**Version:** `6.45-medek-odr-evidence-matrix`  
**Schema:** `0025_accreditation_compliance_core` (no new migration)

6.44 MÜDEK Version Routing baseline is preserved. This release adds a dedicated MEDEK 2026 ÖDR v1.1 preparation and evidence-routing workspace without collapsing the framework's 46 subcriteria into the more granular ÖDR narrative prompts.

## Added
- MEDEK ÖDR v1.1 preparation registry with **58 detailed prompt rows** grouped under Criteria 1–9.
- Separate **Ek I / Ek II preparation matrix** with 11 checklist rows.
- Direct ÖDR-row evidence linkage (`1.1.1`, `2.3.3`, `3.2.2`, etc.) alongside supporting framework-subcriterion evidence.
- Conservative readiness logic: failed authoritative system signals cannot be overridden by document upload; positive system data without direct ÖDR evidence remains `attention` rather than green.
- Manual maturity review for ÖDR rows where authoritative automation is unavailable.
- General vs interim evaluation scoping. Interim B/Ek areas remain conditional until previous findings/observations are linked.
- MEDEK ÖDR workspace in Quality360 with priority gaps, evidence routing, appendix status and internal preparation completion.
- Working DOCX export: `MEDEK ÖDR v1.1 Hazırlık / Kanıt Matrisi`.
- MEDEK-specific automation signals for explicit outcome-component mapping, faculty CV coverage, controlled institutional/school profile documents, part-time faculty monitoring and student/graduate statistics.

## Important interpretation
The 58-row ÖDR preparation matrix is **not** a second accreditation framework and does not replace the 46-subcriterion MEDEK v1.1 framework registry. It is a reporting/preparation layer that maps detailed ÖDR prompts back to the canonical framework subcriteria and evidence lineage.

This feature is an internal preparation/pre-check tool. It does not generate an official MEDEK score or accreditation decision, and the final official submission must still be verified against the accreditation-period source files and institutional Quality Unit approval.

## Official source metadata used by the registry
- MEDEK Öz Değerlendirme Raporu v1.1 — Document No `RP-002`, revision `02`, 23.12.2025.
- MEDEK Önlisans Program Ölçütleri v1.1 — used for the 2026 evaluation period.
