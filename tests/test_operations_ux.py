from html.parser import HTMLParser
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')
JS = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
CSS = (ROOT / 'app/static/styles.css').read_text(encoding='utf-8')

class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k == 'id' and v:
                self.ids.append(v)
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def html_ids():
    p = IdCollector()
    p.feed(HTML)
    return p.ids


def test_operations_ux_contract_and_unique_ids():
    ids = html_ids()
    assert len(ids) == len(set(ids))
    for required in [
        'dashboardExamList', 'dashboardAttention', 'scanQuickStats', 'scanReviewBadge',
        'gradeProgress', 'gradeStudentSummary', 'gradeSaveNext', 'accredProgressFill',
        'accredProgressText', 'accredPeriodSelect', 'downloadAnalyticsExcel',
        'examBankGrid', 'addSelectedBankToExam', 'normalizeExamPoints', 'paperHtmlPreview', 'downloadStudentPapers',
        'scanModeStatus', 'scanSetGrading', 'scanFileCount', 'scanReviewFilter', 'scanOpenAnalytics',
        'accredKpis', 'accredMatrix', 'accredGaps', 'accredRepresentatives', 'accredActions', 'accredExcel', 'accredFreezeAll',
        'pilotOpsKpis', 'academicPeriodForm', 'academicPeriodList', 'pilotSyncHistory', 'pilotAuditLog',
        'qualityKpis', 'qualityHeatmap', 'qualityRisks', 'qualityTrend', 'qualityDrilldown', 'pilotOpsStatusBadge', 'pilotReadinessScore', 'pilotSetupChecklist', 'runPilotUat', 'pilotIssueCenter', 'pilotBackupStatus', 'pilotBenchmark',
        'dashboardRoleBadge', 'dashboardTaskGrid', 'dashOpenBank', 'dashOpenQuality', 'demoScenarioCard', 'createDemoScenario', 'feedbackForm', 'feedbackList', 'feedbackStatusFilter', 'onboardingModal', 'onboardingBody',
    ]:
        assert required in ids
    for selector in [
        '.dashboard-grid', '.operation-steps', '.grade-sticky-footer',
        '.modern-review', '.accred-main-grid', '.modern-accred-exam', '.analytics-toolbar',
        '.exam-builder-studio', '.exam-bank-pane', '.exam-canvas-pane', '.paper-studio',
        '.scan-station-hero', '.scan-review-workbench', '.scan-annotated-preview', '.scan-answer-review',
        '.accred-kpi-grid', '.accred-matrix', '.accred-gap-row', '.accred-rep-row', '.accred-action-table',
        '.pilot-kpi-grid', '.pilot-ops-grid', '.period-row', '.audit-timeline', '.pilot-uat-grid', '.pilot-checklist', '.pilot-issue-list', '.pilot-backup-status',
        '.quality-kpi-grid', '.quality-heatmap', '.quality-risk-row', '.quality-drill-grid',
        '.dashboard-task-grid', '.dashboard-task-card', '.feedback-grid', '.feedback-row', '.onboarding-overlay',
    ]:
        assert selector in CSS


def test_operations_ux_js_ids_exist_and_hidden_not_overridden():
    ids = set(html_ids())
    js_ids = set(re.findall(r"getElementById\(['\"]([^'\"]+)", JS))
    assert js_ids <= ids
    assert '.grade-workspace{display:block}' not in CSS.replace(' ', '')
    verify = (ROOT / 'docs/legacy-tools/Verify-6.18.ps1').read_text(encoding='utf-8-sig').lower()
    assert 'id="logingate"' in verify
    assert 'id="bankfilterprogram"' in verify
    assert '/api/question-bank' in verify
    assert '/scans-batch' in verify
    assert 'preview_url' in verify
    assert 'raw_preview_url' in verify
    assert '/report.xlsx' in verify
    assert '/representatives/freeze-all' in verify
    assert '/api/quality/dashboard' in verify
    assert '/api/quality/dashboard.xlsx' in verify
    assert '/api/pilot/readiness' in verify
    assert '/api/pilot/uat/run' in verify
    assert (ROOT / 'docs/legacy-tools/Pilot-Load-Test.ps1').exists()
    assert (ROOT / 'migrations/versions/0010_pilot_uat_operations.py').exists()
    assert (ROOT / 'migrations/versions/0011_final_ux_feedback.py').exists()
    assert (ROOT / 'migrations/versions/0012_security_performance_indexes.py').exists()
    assert (ROOT / 'migrations/versions/0013_multi_outcome_questions.py').exists()
    assert (ROOT / 'migrations/versions/0014_exam_workspace.py').exists()
    assert '/api/feedback' in JS and '/api/pilot/demo-scenario' in JS


def test_614_backup_restore_ops_volume_and_load_test_contracts():
    backup = (ROOT / 'docs/legacy-tools/Backup-Pilot.ps1').read_text(encoding='utf-8-sig').lower()
    restore = (ROOT / 'docs/legacy-tools/Restore-Pilot.ps1').read_text(encoding='utf-8-sig').lower()
    load = (ROOT / 'docs/legacy-tools/Pilot-Load-Test.ps1').read_text(encoding='utf-8-sig').lower()
    compose = (ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
    production = (ROOT / 'docker-compose.production.yml').read_text(encoding='utf-8')
    assert 'get-filehash' in backup and 'backup-status.json' in backup and 'database_sha256' in backup
    assert 'get-filehash' in restore and 'restore-status.json' in restore and 'sha256' in restore
    assert 'concurrency' in load and '/api/pilot/readiness' in load and '/api/pilot/performance' in load
    assert 'OPS_STORAGE_PATH: /app/data/ops' in compose and 'ops_data:/app/data/ops' in compose
    assert 'OPS_STORAGE_PATH: /app/data/ops' in production and 'ops_data:/app/data/ops' in production
    start = (ROOT / 'docs/legacy-tools/Start-Pilot.ps1').read_text(encoding='utf-8-sig').lower()
    assert 'newguid' in start and 'change_me_autogenerated' in (ROOT / '.env.pilot').read_text(encoding='utf-8').lower()


def test_6151_scan_final_visual_polish_contract():
    assert 'Akademik Ölçme ve Kalite Platformu' in HTML
    assert HTML.count('class="operation-step-actions"') >= 3
    assert 'operation-step-actions scan-upload-actions' in HTML
    assert 'Taramayı başlat' in HTML
    assert 'PDF\'leri indir' in HTML
    assert '.scan-workflow-steps .operation-step.scan-step' in CSS
    assert '.scan-file-drop.has-files' in CSS
    assert 'button:disabled' in CSS
    assert 'grid-template-areas:"stepno stepcopy" "stepactions stepactions"' in CSS
    assert "btn.disabled=!hasExam||count===0" in JS
    assert 'Tarama geçmişi için sınav seçin.' in JS


def test_6161_grouped_navigation_and_multi_outcome_ui_contract():
    root = Path(__file__).resolve().parents[1]
    html = (root / 'app' / 'static' / 'index.html').read_text(encoding='utf-8')
    js = (root / 'app' / 'static' / 'app.js').read_text(encoding='utf-8')
    css = (root / 'app' / 'static' / 'styles.css').read_text(encoding='utf-8')
    assert 'class="grouped-nav final-nav"' in html
    assert 'Ders & Sınav' in html and '>Analiz<' in html and '>Kalite<' in html and 'Yönetim Araçları' in html
    assert 'Akademik Akış' not in html
    assert 'id="managementNavGroup"' in html and 'id="workspaceNavGroup"' in html
    assert 'id="qLo" class="sr-only" multiple' in html
    assert 'id="bankLoSelect" class="sr-only" multiple' in html
    assert 'learning_outcome_codes:selectedValues' in js
    assert 'questionOutcomeCodes(q).includes(lo.code)' in js
    assert '.nav-group.open .nav-submenu' in css


def test_6162_academic_data_workspace_contract():
    ids = set(html_ids())
    for required in [
        'academicDataStats', 'courseCreateForm', 'studentCreateForm', 'programCreateForm',
        'dataCourseProgram', 'dataCourseCode', 'dataCourseName', 'dataCourseYear', 'dataCourseTerm',
        'dataStudentProgram', 'dataStudentNo', 'dataStudentName', 'dataEnrollCourse',
        'dataEnrollmentStudents', 'dataEnrollSubmit', 'academicDirectoryList',
        'academicDataSearch', 'academicProgramFilter', 'dataNewCourse', 'dataOpenObs'
    ]:
        assert required in ids
    for token in [
        "api('POST','/api/courses'", "api('POST','/api/students'", "api('POST','/api/programs'",
        '/enrollments/bulk', 'openAcademicForm', 'renderAcademicDirectory', 'loadAcademicEnrollments'
    ]:
        assert token in JS
    for selector in [
        '.academic-data-hero', '.academic-data-layout', '.academic-create-tabs',
        '.academic-directory-toolbar', '.academic-entity-card', '.enrollment-list'
    ]:
        assert selector in CSS
    assert 'Program, ders ve öğrenciyi tek akışta yönetin' in HTML
    assert 'Dersi oluştur' in HTML
    assert 'Seçili öğrencileri derse ata' in HTML


def test_6163_csp_safe_button_delegation_contract():
    # Production CSP intentionally disallows inline script/event handlers.
    # Dynamic buttons must therefore use the delegated data-action system.
    assert 'onclick=' not in HTML
    assert 'onclick=' not in JS
    assert 'data-action-call=' in JS
    assert 'DELEGATED_ACTIONS' in JS
    assert 'runDelegatedAction' in JS
    assert "closest?.('[data-action-call]')" in JS
    assert '/app.js?v=' in HTML
    assert '/styles.css?v=' in HTML
    for action in ['editCourse','openEnrollmentForCourse','removeCourse','showPage','openExam']:
        assert action in JS



def test_617_final_product_information_architecture_and_exam_workspace_contract():
    ids=set(html_ids())
    for required in [
        'commandPalette','commandSearch','outcomeCenterKpis','loEntityList','poEntityList','outcomeMatrix',
        'examCenterKpis','examSearch','examCourseFilter','examStatusFilter','examDetailStrip','examWorkspaceSummary',
        'examDraftForm','draftStartTime','draftLocation','draftWeight','draftBookletCount','draftStaffNotes','duplicateExam'
    ]:
        assert required in ids
    for label in ['Ders & Sınav','Derslerim','Sınavlar','Soru Bankası','Değerlendirme','Analiz','Kalite','Yönetim','Çıktı Yönetimi']:
        assert label in HTML
    assert 'Akademik Akış' not in HTML
    for token in ['workspace-summary','goExamNextAction','recent_activity','next_action','commandItems','openCommandPalette','renderExamWorkspaceSummary']:
        assert token in JS
    for selector in ['.final-nav','.exam-center-hero','.exam-center-layout','.exam-detail-strip','.workspace-metrics','.outcome-center-hero','.outcome-center-kpis','.command-overlay']:
        assert selector in CSS
    assert 'onsubmit=' not in HTML and 'onsubmit=' not in JS
    assert 'onclick=' not in HTML and 'onclick=' not in JS


def test_618_analysis_ui_and_academic_excel_workspace_contract():
    ids=set(html_ids())
    for required in [
        'analyticsStudentDrawer','analyticsStudentDrawerClose','analyticsStudentDrawerBody',
        'academicTemplateDownload','academicWorkbookFile','academicWorkbookValidate','academicWorkbookImport','academicWorkbookResult'
    ]:
        assert required in ids
    for token in ['SINAV ANALİZ MERKEZİ','EXCEL İLE TOPLU KURULUM','Excel şablonunu indir','Doğrula','İçe aktar']:
        assert token in HTML
    for token in ['score_distribution','renderAnalyticsStudents','academic-workbook','openAnalyticsStudent']:
        assert token in JS
    for selector in ['.analytics-sticky-tabs','.distribution-chart','.analytics-drawer','.academic-bulk-import','.question-analysis-grid']:
        assert selector in CSS


def test_619_classic_scan_grading_workspace_contract():
    ids = set(html_ids())
    assert {'gradeQuestions','gradeSaveNext','scanFile'} <= ids
    assert '/classic-scans' in JS
    assert '/classic-crop/' in (ROOT / 'app/main.py').read_text(encoding='utf-8')
    assert 'classic-grade-split' in JS
    assert '.classic-grade-split' in CSS
    assert '.classic-scan-pane' in CSS
    assert 'TARANMIŞ CEVAP' in JS
    assert 'Kaydet ve sonraki' in HTML
    assert (ROOT / 'migrations/versions/0016_classic_scan_grading.py').exists()
    paper = (ROOT / 'app/services/paper.py').read_text(encoding='utf-8')
    assert 'role={role}|page=' in paper
    assert 'def question_regions' in paper


def test_6185_sidebar_accordion_and_overflow_contract():
    assert '6.18.5 · Sidebar accordion / overflow stability fix' in CSS
    assert '.grouped-nav.final-nav{flex:1 1 auto;min-height:0' in CSS
    assert 'overflow-y:auto!important' in CSS
    assert '.identity-box{flex:0 0 auto' in CSS
    assert 'function setNavGroupOpen' in JS
    assert "document.querySelectorAll('.nav-group.open')" in JS
    assert 'setNavGroupOpen(group,true)' in JS
