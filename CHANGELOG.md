## 6.71 (unreleased) — Demo/pilot P0 closure (migration 0044)
- Learning outcomes: instructors manage their own course's outcomes; each carries a source label (OBS / added in Assess / OBS-modified); linked outcomes are deactivated instead of deleted and skipped by new exam snapshots; create/update/deactivate audit-logged with before/after.
- New "Basım" screen: per-exam print summary (pages, sheets, booklet split), bulk and per-student PDFs, attendance/signature list PDF, "Yazdırdım" confirmation that freezes the questions (changes need a copied version).
- Answer sheet: bubbles follow each question's real choice count (2–5); marking instruction added to the exam rules (TR/EN).
- Menu follows the working order (1 Derslerim, 2 Soru Bankası, 3 Sınav Hazırla, 4 Basım, 5 Optik Okuma, 6 Değerlendirme) with numbered badges; header buttons are text-only.
- OBS: "OBS'den getir" re-sync (password not stored, ownership-checked) and last-sync status on Derslerim.
- Mobile: 44px touch targets, checkbox/label alignment; no horizontal scroll at 360/390/414/768/1024 (verified in Chromium).
- P1: persistent exam state bar (Taslak → Hazır → Basıldı → Puanlama → Onaylı, with what is locked); OBS vs Assess outcome diff report (`GET /api/courses/{id}/outcome-diff`, original OBS text recovered from the audit trail); grading completeness (`GET /api/exams/{id}/grading-progress`) separating "girilmedi" from a real 0.
- Fast grading grid for rubric-based classic questions (student x criterion, all-or-nothing validation, blind-mode aware, unchanged rows skipped, revisions logged). Institution wording for "learning outcome" via `OUTCOME_TERM` (Öğrenim | Öğrenme | Kazanım).
- P1: versioned success thresholds (migration 0045: LO default target + PO threshold per institution/program/year, history kept, applied to new outcomes and analytics); random sampling of auto-accepted OMR pages with error-rate vs `SCAN_TARGET_ERROR_PERCENT`; hash-sealed semester closure package per exam; scan retention overview and recorded purge (`SCAN_RETENTION_DAYS`, default 1460, admin only).
- P1: OBS bulk-entry grade export (`GET /api/courses/{id}/obs-grades.xlsx`, layout must be confirmed against the OBS template), PÇ calculation formula document (`GET /api/programs/{id}/po-formula.md`), Excel template + validated all-or-nothing import for assignment/project/lab scores, `docs/KVKK-AI-OCR-DEGERLENDIRME.md` assessment template.
- P1: exams with more than 40 test questions automatically use a separate answer page (embedded bubbles overlapped at 100 questions); the score grid now lists every question (was capped at 40); per-student extra time (migration 0046) printed on the student's paper and attendance sheet, locked after print.
- P2: institution settings (migration 0047: ÖÇ term, ÖÇ change approval, question self-approval switch, AI scoring switch); ÖÇ change approval queue (maker-checker, reviewer roles); question maker-checker + shared institutional pool (same program, copy as draft with outcome mapping by code); connector interface + canonical sync (`app/services/connectors.py`, Proliz adapter, tested with a fake second institution); flag-gated AI scoring *suggestion* (off by default, no student identity sent, never writes grades); docs/commercial/* (ADR multi-tenant, second-university pilot checklist, commercial pack template, security test plan, KVKK dossier).
- Demo scenario uses the real current term instead of 2099-2100 when that period is free.

# 6.70 — Performance & Production Hardening

- Replaced Python/N+1 academic scope filtering with SQL-scoped program/course selectors.
- Added server-side pagination/search for students and question bank; frontend no longer globally bootstraps all students.
- Added aggregate directory summary counts and student-card search to avoid large dropdown payloads.
- Extracted shared browser state/API/auth/download/toast/escape primitives into `runtime-core.js`.
- Added composite performance indexes in migration `0042_performance_production_hardening`.
- Added exact production dependency lock, CycloneDX SBOM and supply-chain verification script.
- Added critical browser navigation E2E alongside the existing Question Bank create E2E.
- Full regression: 253/253 PASS; fresh and 0041→0042 migrations PASS.

# 6.69 — Program Review & Evidence Hub 2.0

- Added versioned Program Review templates and program/year review cycles.
- Added contributor/reviewer maker-checker section workflow and final immutable snapshot.
- Final snapshot now freezes linked evidence SHA-256 metadata.
- Added final snapshot integrity verification.
- Added Evidence Hub 2.0 search, tags, usage chain, pagination and duplicate SHA detection.
- Added Program Review and Kanıt Merkezi UI workspaces.
- Hardened governed assignment and evidence-tag authorization.
- Full regression 247/247 PASS; fresh and 0040→0041 migrations PASS.

# Changelog

## Unreleased — Evaluator evidence room & exam readiness
- Evaluator portal "Kanıt Odası": read-only program/course/learning-outcome/program-outcome matrix, exams (questions, answer key, blank paper PDF, attainment), students with masked names, per-student answers, scanned pages and outcome cards; token-only auth, audit-logged, program-scoped.
- Exam readiness: uncovered learning outcomes, duplicate questions, rubric/points mismatch, non-positive duration, uniform MCQ key.
- Question key exceptions (`POST /api/exams/{id}/questions/{qid}/key-exception`): annul an MCQ (full credit) or accept an extra correct choice; persisted as answer-key revisions so later OMR/manual entries and regrades follow it; grade changes are audit-logged.
- Evaluator room: course file (Word) download per course.
- Student portal (`/student.html`): per-student HMAC links (no new tables; `STUDENT_LINK_SECRET`, `STUDENT_APPEAL_DAYS`), visible only after grade lock, own paper/scan/rubric scores, time-boxed appeals feeding the existing GradeAppeal workflow. Exam toolbar gets grade-lock and links-CSV buttons.
- Classic-question annulment (full marks on every rubric criterion, honoured by later manual entries). Student appeals notify the course instructor (in-app notification). Exam workspace gets an appeals panel: accept (points/rubric) / reject, plus bulk reject with a shared note.
- Institution replies to evaluator comments (`POST /api/compliance/visit-notes/{id}/reply`, "Yanıtla" in the visit center); replies show in the evaluator's "Yorumlarım".
- Evaluator room: comments/questions land in institution visit notes (max 100 per workspace). Scan panel: phone camera capture.
- `GET /api/exams/{id}/scan-coverage`: students without a scanned paper, pending reviews and papers with missing pages; shown in the scan panel.

## 6.68 — Operations & Automation
- Added PostgreSQL-backed durable operational jobs with separate worker and scheduler containers.
- Added in-app deadline notification engine and user-facing notification center.
- Moved integrity scans and backup creation to asynchronous worker jobs.
- Added verified operational backups with checksum/archive verification and retention pruning.
- Added operations summary, paginated job/notification APIs and scheduler controls.
- Added migration `0040_operations_automation`.

# 6.67 — Evidence Integrity & Security

- Read-time SHA-256 evidence integrity enforcement and batch integrity scan.
- Content-aware upload security gateway for quality evidence, controlled documents and official templates.
- Controlled-document maker-checker workflow with authenticated actors.
- Expiring/revocable external evaluator token portal with hash-only token persistence.
- Migration `0039_evidence_integrity_security`.
- Playwright regression baseline for Question Bank create flow.


## 6.62 — Program Assessment Assurance
- Added versioned annual Program Assessment Assurance plans by program and academic year.
- Added PÇ-level direct/indirect method planning with owner, target, cadence, due date and evidence requirements.
- Added evidence-source-specific assurance analytics, plan coverage, evidence completeness and target attainment.
- Added immutable final year-end review snapshots and post-review plan freeze.
- Added controlled below-target PÇ → QualityCycle/PUKÖ creation.
- Schema advanced to `0036_program_assessment_assurance`.
- Full regression: 217/217 PASS; Pilot UAT: 41/41 PASS.

## 6.61 — Survey & Indirect Assessment
- Added versioned survey templates/campaigns, anonymous and identified response handling, and PÇ/PEA/criterion mappings.
- Added direct + indirect PÇ evidence mix and academic-year indirect assessment analytics.
- Schema advanced to `0035_survey_indirect_assessment`.
- Full regression: 215/215 PASS; Pilot UAT: 41/41 PASS.

## 6.48 — MÜDEK Evaluator & Site Visit Control
- Added previous-general application linkage for interim/monitoring evaluations.
- Added accreditation findings and site-visit notes.
- Added document-request SLA answer/close timestamps.
- Added official 30-day response workflow after site visit.
- Added Visit Control Center UI and enhanced evaluator snapshot.
- Schema advanced to `0026_accreditation_visit_control`.

## 6.46 — MEDEK Version Routing + Programa Özgü Çıktılar

- MEDEK v1.1/v2.0 değerlendirme dönemi routing ve backend guard.
- v2.0: 8 ölçüt, 45 alt ölçüt, 11 genel PÇ.
- İnternet ve Ağ Teknolojileri için sürümlü programa özgü çıktı kataloğu ve PÇ mapping görünümü.
- Ara/izleme değerlendirmesinde önceki genel sürüm zorunlu tarihsel bağlam.

## 6.45 — MEDEK ÖDR Evidence Matrix
- Added separate MEDEK 2026 ÖDR v1.1 preparation layer with 58 detailed prompts mapped to the canonical 46-subcriterion framework.
- Added 11-row Ek I / Ek II preparation matrix, exact evidence lineage, manual review and conservative readiness states.
- Added general/interim scope handling and MEDEK ÖDR working DOCX export.
- Added dedicated Quality360 MEDEK ÖDR workspace with priority gaps and evidence routing.
- Full regression: 158/158 PASS; Pilot UAT: 41/41 PASS.

## 6.44 — MÜDEK Version Routing
- MÜDEK 2.2/3.0/3.1 sürüm registry ve dönem/tür bazlı routing.
- Başvuru oluşturma backend guard ve UI sürüm seçici.
- 2026-2027 geçiş, 2027-2028 3.1 zorunluluk kuralları.

# 6.42-finalization-workspace — 2026-09-14
- Action Center / Eksiklerim role-based task queue.
- Dedicated Student Cards workspace with ÖÇ/PÇ/course detail.
- Student report-card PDF with verification code and QR.
- No schema migration; remains on 0025 accreditation compliance core.


## 6.41 — Accreditation Compliance Core
- 30-item accreditation/compliance product matrix closed to green with models, APIs, UI, exports and tests.
- Added PEA, PÇ components, cumulative student/graduate Outcome Card and graduation snapshots.
- Added YÖKAK 14×46 criterion tree and subcriterion evidence linkage.
- Added official template vault, immutable framework snapshots, controlled documents and document hashing.
- Added budget/resource, faculty CV/workload, graduate 1/3/5-year tracking, infrastructure maintenance and YÖKAK mission-domain modules.
- Added accreditation lifecycle, read-only evaluator workspace, additional-document requests and MÜDEK BBO/FBO evidence-room export.
- Schema advanced from `0024_mapping_contribution_1_5` to `0025_accreditation_compliance_core`.
- Full local regression: 140/140 PASS; 6.41-specific suite: 6/6 PASS; Pilot UAT: 41/41 PASS.


## 6.37 — Final Pre‑Integration Stabilization

- 6.36 fonksiyonları korunarak sürüm donduruldu.
- Kök dizindeki eski version-specific upgrade/verify scriptleri kaldırıldı.
- Tek `Upgrade-Server.sh`, `Verify-Server.sh` ve `Preflight-Server.sh` akışı getirildi.
- Testlerden kalan evidence/scan/ops dosyaları dağıtım paketinden temizlendi.
- README tek güncel sürüm/schema kaynağı olacak şekilde yeniden yazıldı.
- Paket hijyeni ve pre-integration kontratı için 6.37 regresyon testleri eklendi.
- Entra ID ve OBS dış bağımlılıkları açıkça entegrasyon kapısı olarak ayrıldı.

## 6.25–6.36 — Ürünleşme Özeti

- Academic Intelligence ve premium role-based UX.
- University Quality OS ve accreditation framework routing.
- Executive Quality Command Center.
- Quality Action / Governance / Escalation / Calendar motorları.
- Closed-loop evidence & PUKÖ operations.
- Evidence readiness ve accreditation visit mode.
- Self-evaluation, institutional quality reporting ve strategic quality management.

## 6.37.4 Final RC
- Production pilot/demo kill-switch'leri eklendi.
- Production preflight güvenlik kapısı sertleştirildi.
- Read-only k6 kapasite testi taslağı eklendi.
- Final paket runtime/test SQLite kalıntılarından arındırıldı.
- API ve schema freeze korundu; OBS/Entra entegrasyonuna hazır taban.

## 6.37.5 · Premium Classic Grading (UI/Workflow)
- Klasik değerlendirmede Öğrenci Bazlı ve Soru Bazlı Seri Puanlama modları eklendi.
- Kör Değerlendirme görünümü eklendi; puanlama sırasında öğrenci kimliği aday kodu ile maskelenir.
- Rubrik ölçütlerine 0/25/50/75/100 hızlı puan presetleri eklendi.
- Klavye akışı eklendi: 1-5 hızlı rubrik, Ctrl/Cmd+Enter Kaydet & Sonraki, Alt+ok öğrenci geçişi.
- Beklenen cevap/değerlendirme anahtarı klasik puanlama ekranında açılır panel olarak gösterilir.
- Backend API ve şema değiştirilmedi; entegrasyon tabanı 6.37 / 0023 olarak korunur.

## 6.39 — Premium Usability & Pilot UAT
- Sidebar geri bildirim ve kullanıcı kimlik alanı yeniden düzenlendi.
- Dashboard task-first hiyerarşisi güçlendirildi.
- Pilot UAT yol haritası ve test veri rehberi eklendi.

## 6.43 — Quality Framework Precision
- MEDEK v1.1 expanded to 46 official subcriteria and 10 reference outcomes.
- MÜDEK v3.1 expanded to 32 normalized subcriteria and 11 reference outcomes.
- Removed incorrect MÜDEK criterion 10; EK-1 is attached to criterion 5.1.
- Added exact subcriterion evidence readiness, manual-review workflow and Action Center precision.
- Full regression 148/148 PASS; all assessment/lifecycle acceptance suites PASS; Pilot UAT 41/41 PASS.

## 6.51 — MEDEK Evaluator / PDR / +7 Day Response
- Added MEDEK evaluator PDR phase tracking and Quality360 PDR Center.
- Added MEDEK-specific +7 day institution response lifecycle.
- Added carry-forward of confirmed final improvement areas for MEDEK interim evaluations.
- Added schema revision 0029_medek_evaluator_pdr.
