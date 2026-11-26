# DOU Assess 6.19 — Final Server Validation

Tarih: 2026-09-07

## Release kimliği

- Release adı: `DOU Assess 6.19 FINAL SERVER READY`
- Uygulama compatibility version: `6.18-6.19-final-server-ready`
- Alembic head: `0018_classic_assessment_standard`
- Production DB: PostgreSQL 17
- Production servisleri: db / migrate / api / nginx

## Otomatik doğrulama

- Pytest: **51/51 PASS**
- Classic Scan Grading acceptance: **PASS**
  - 2 sayfa
  - 1 accepted OMR
  - 1 klasik support page
  - answer crop: **1181×345 px**
  - rubrik puanı: **8/10**
- Legacy `dou-official-v2` Classic Scan: **PASS**
  - legacy association: true
  - answer crop: **1181×345 px**
- Complete Engine acceptance: **PASS**
- Lifecycle acceptance: **PASS**
- Local Pilot UAT 1–9: **41/41 PASS**
- UAT accreditation ready: **true**
- Fresh migration `0001 → ... → 0018`: **PASS**
- 72 soruluk soru havuzu importer doğrulaması: **72 satır / 0 hata**
  - 60 test
  - 12 klasik
  - 12 klasik soruda expected_answer + rubrik kriteri→ÖÇ standardı
- Python compile: **PASS**
- Frontend JavaScript `node --check`: **PASS**
- Pilot/production Compose YAML parse: **PASS**
- `/api/health`: **200**
- `/api/ready`: **200 / ready / 0018_classic_assessment_standard**

## Temiz release veritabanı

Fresh migration ile yeniden oluşturulan paket DB'sinde:

- programs: 0
- courses: 0
- students: 0
- enrollments: 0
- exams: 0
- questions: 0
- responses: 0
- scan_sessions/items: 0
- evidence_assets: 0
- improvement_actions: 0
- exam_incidents: 0
- grade_appeals: 0

Migration tarafından oluşturulan yalnız **1 teknik bootstrap admin + 1 admin rol ataması** korunur.

Runtime dizinleri release öncesi temizlenmiştir:

- `data/evidence`: yalnız `.gitkeep`
- `data/scans`: yalnız `.gitkeep`
- `data/ops`: yalnız `.gitkeep`

Production parola/secret dosyası pakete eklenmez.

## 6.19 akademik bütünlük kontrolleri

- Üç akademik persona: Öğretim Görevlisi / Program Başkanı / Kalite Müdürü.
- Teknik admin akademik rol atama seçeneklerinden ayrı tutulur.
- Katılım: attended / absent / excused / invalidated.
- Analiz yalnız aktif `attended` öğrencileri paydaya alır.
- Klasik soru: beklenen cevap + Bloom + ÖÇ + analitik rubrik zorunlu.
- Rubrik kriterleri ÖÇ'lere bağlanır.
- Puan kilidi sonrası normal puan değişikliği engellenir.
- Açık optik review / kritik olay / itiraz kilit-onay akışını bloke eder.
- İtiraz kabulünde klasik puan kriterlerden yeniden hesaplanır; revizyon izi saklanır.
- PDCA kapanışı gerçekleşen değer + doğrulama yöntemi + etkililik + kapanış notu ister.
- Kalite kanıt paketine olay/itiraz/iyileştirme kayıtları dahil edilir.

## Kullanılabilirlik

- Ekran bazlı `? Kılavuz`.
- Rol bazlı onboarding/görev akışı.
- Üst bardan `Excel Yükle`.
- Excel Veri Merkezi: şablon → doğrula → içe aktar.
- Sınav, optik, klasik, analiz ve kalite akışlarında role göre sadeleştirilmiş yönlendirme.

## Production hardening

- PostgreSQL 17.
- API'den önce Alembic migration.
- 2 API worker.
- read-only API filesystem.
- `no-new-privileges`.
- `cap_drop: ALL`.
- NGINX rate/connection/upload limitleri.
- scan upload timeout 300 sn.
- `MAX_PDF_PAGES=120`.
- `MAX_IMAGE_MEGAPIXELS=40`.
- kalıcı evidence/scans/ops volumes.
- büyük PDF için streaming rasterization.

## Bu ortamda çalıştırılamayan saha kabulü

Bu test ortamında Docker CLI/daemon ve PowerShell runtime bulunmadığından gerçek production container stack burada ayağa kaldırılmadı. Aşağıdaki kabul maddeleri hedef sunucuda tamamlanmalıdır:

- Docker/PostgreSQL/NGINX runtime.
- Microsoft Entra gerçek tenant/app registration.
- Gerçek OBS endpoint/alan sözleşmesi.
- TLS/DNS.
- Fiziksel ADF tarayıcı/baskı kalibrasyonu.
- Production backup → ayrı ortam restore tatbikatı.
- Hedef sunucu eşzamanlı yük testi.

Bunlar için `SERVER-DEPLOYMENT-6.19.md` ve `SERVER-RELEASE-CHECKLIST-6.19.md` kullanılmalıdır.
