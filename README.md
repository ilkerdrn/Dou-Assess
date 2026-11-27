> Canonical build metadata is stored in `RELEASE.env`. `/api/health` and `/api/system/diagnostics` expose the active non-secret build/runtime state.

# DOU Assess — 6.70 PERFORMANCE & PRODUCTION HARDENING

**Sürüm:** `6.70-production-hardening`  
**Veritabanı şeması:** `0043_response_grade_revisions` (bkz. "Not/puan değişikliği audit izi" eklentisi, 0042'den sonra)

**Production baseline:** 6.53 akademik/ölçme/kalite/akreditasyon fonksiyonları donduruldu. 6.54 yeni business feature eklemez; sunucuya güvenli kurulum, yükseltme, backup/restore ve go-live doğrulamasını standardize eder.

**Bugün sunucuya kurulum için ana doküman:** `PRODUCTION-DEPLOYMENT-6.54.md`


## 6.70 Performance & Production Hardening

- Akademik yetki kapsamı program/ders listelerinin tamamını Python'a çekmek yerine SQL scope sorgularıyla uygulanır.
- Program, ders, öğrenci, sınav ve soru bankası listelerinde server-side filtre/pagination standardı vardır.
- Global frontend bootstrap artık tüm öğrencileri yüklemez; öğrenci dizini ve öğrenci karnesi isteğe bağlı arama/sayfalama kullanır.
- `runtime-core.js` ortak state/API/auth/download/toast/escaping katmanını `app.js` içinden ayırır.
- `0042_performance_production_hardening` sık kullanılan authorization, evidence, scan, operations ve Program Review sorgularına composite index ekler.
- Production image tam sürüm kilitli `requirements.lock` üzerinden kurulur ve build sırasında `pip check` zorunludur.
- CycloneDX `SBOM-6.70.cdx.json` ve `Verify-Supply-Chain.sh` supply-chain doğrulama yüzeyi sağlar; harici vulnerability scanner yoksa durum açıkça raporlanır.
- Browser kabul kapsamı Soru Bankası yanında Akademik Veri, Program Review ve Evidence Hub navigasyonunu da kapsar.
- Schema head: `0042_performance_production_hardening`.

**6.70 dokümanları:** `RELEASE-NOTES-6.70.md`, `FINAL-VALIDATION-MATRIX-6.70.md`, `PERFORMANCE-HARDENING-6.70.md`.

## 6.69 Program Review & Evidence Hub 2.0

- Sürümlü Program Review şablonları ve program/yıl bazlı review cycle.
- Bölüm bazlı contributor → reviewer maker-checker workflow; aynı kişi kendi bölümünü onaylayamaz.
- Kanıt bağlantıları fiziksel dosyayı kopyalamadan exam / Quality360 / controlled document kaynaklarına referans verir.
- Final snapshot yalnız tüm bölümler onaylı olduğunda oluşur ve kanıt SHA-256 manifesti ile mühürlenir.
- Final snapshot bütünlüğü sonradan yeniden doğrulanabilir.
- Evidence Hub 2.0: global arama, program/kaynak/bütünlük/etiket filtresi, pagination, etiketleme, duplicate SHA ve Program Review kullanım zinciri.
- UI çalışma alanları: Program Review + Kanıt Merkezi.
- Schema head: `0041_program_review_evidence_hub`.

**6.69 dokümanları:** `RELEASE-NOTES-6.69.md`, `FINAL-VALIDATION-MATRIX-6.69.md`, `PROGRAM-REVIEW-EVIDENCE-HUB-6.69.md`.

## 6.68 Operations & Automation

**6.68 operasyon dokümanları:** `RELEASE-NOTES-6.68.md`, `FINAL-VALIDATION-MATRIX-6.68.md`, `OPERATIONS-AUTOMATION-6.68.md`.

- PostgreSQL-backed kalıcı operasyon kuyruğu, ayrı worker ve scheduler servisleri eklendi; Redis/Celery bağımlılığı eklenmedi.
- Ağır kanıt bütünlüğü ve backup işleri HTTP request yaşam döngüsünden ayrıldı; worker restart sonrasında kuyruk kalıcıdır.
- PUKÖ, kalite takvimi, akreditasyon belge talepleri/bulguları ve ölçme güvence planı terminleri idempotent bildirimlere dönüştürülür.
- Üst bardaki Bildirim Merkezi okunmamış sayaç, okundu durumu ve ilgili modüle yönlendirme sağlar.
- Otomatik/manual backup işi checksum ve archive doğrulaması geçmeden başarılı sayılmaz; production restore otomatik yapılmaz ve kontrollü DR tatbikatı olarak kalır.
- Operasyon API'leri job/notification pagination ve merkezi durum özeti sunar.
- Schema head: `0040_operations_automation`.

## 6.67 Evidence Integrity & Security

**6.67 operasyon dokümanları:** `RELEASE-NOTES-6.67.md`, `FINAL-VALIDATION-MATRIX-6.67.md`, `SECURITY-OPERATIONS-6.67.md`, `E2E-README-6.67.md`.


- Sınav, Quality360 ve kontrollü doküman kanıtlarında indirme/önizleme/paketleme sırasında SHA-256 bütünlük doğrulaması uygulanır; eksik dosya 404, hash uyuşmazlığı 409 ve audit izi üretir.
- Quality360, kontrollü doküman ve resmî şablon yüklemeleri içerik tabanlı PDF/görsel/Office/ZIP güvenlik kapısından geçer; uzantı sahteciliği, şifreli container, path traversal ve şüpheli sıkıştırma reddedilir.
- Kontrollü doküman revizyonu artık doğrudan onaylı yaratılamaz: Taslak → İnceleme → Kontrol → Onay akışı ve hazırlayan ≠ kontrol/onaylayan kuralı sunucu tarafında zorunludur.
- External Evaluator Workspace, yalnız hash'i saklanan tek-seferlik davet tokenı, expiry/active enforcement, revoke ve ayrı public read-only snapshot erişimiyle güvenli hale getirildi.
- Toplu bütünlük taraması `/api/security/evidence-integrity/scan` üzerinden sınav, Quality360 ve kontrollü doküman depolarını doğrular.
- Browser E2E regresyonu Soru Bankası → Yeni soru → Kaydet akışını gerçek Chromium/Playwright ile kapsar; bazı kontrollü çalışma ortamlarında localhost browser politikası nedeniyle CI/server üzerinde çalıştırılması gerekir.
- Schema head: `0039_evidence_integrity_security`.

## 6.66 Production Acceptance Gate

- Kurum bağımlı production kabulü sekiz doğrulanabilir kapıyla yönetilir.
- Entra, Proliz/OBS read-only, DNS/TLS, fiziksel OMR, backup/restore/DR, resmî şablon onayı, gerçek program pilotu ve RBAC izolasyonu sistem sinyali + yetkili imza ile kapanır.
- Schema head at release: `0038_institution_acceptance_gate`.

## 6.65 Framework Lifecycle Precision

- TURAK/SABAK/EPDAD 2026 resmî süreç takvimleri kurumsal hazırlık merkezine bağlandı.

## 6.64 Integration Acceptance Guard

- OBS varsayılan read-only; write-back yalnız açık kurumsal onay bayrağıyla etkinleşir.

## 6.63 Institutional Accreditation Readiness

- Kuruluş/program hazırlık portföyü, ortak gap kuyruğu, onaylı cross-framework kanıt reuse ve hash'li yönetim snapshot'ları eklendi.

## 6.62 Program Assessment Assurance

- Program + akademik yıl + sürüm bazlı **Yıllık Ölçme Güvence Planı** oluşturulur.
- Her PÇ için doğrudan ve dolaylı ölçme yöntemi, sorumlu, dönem/sıklık, hedef, termin ve beklenen kanıt açıkça tanımlanır.
- Mevcut sınav, proje/ödev/lab/staj ölçümleri ve PÇ eşleşmiş anketlerden plan kalemleri otomatik oluşturulabilir.
- Güvence dashboard'u yalnız planda seçilmiş kaynaklardan gelen kanıtı hesaba katar; ilgisiz bir ölçüm plan hedefini yanlışlıkla kapatamaz.
- PÇ bazında plan kapsamı, kanıt tamlığı, birleşik başarı ve hedef durumu izlenir.
- Final yıl sonu review, dashboard'u snapshot olarak dondurur; kapanmış plan değiştirilemez ve yeni değişiklik yeni plan sürümü gerektirir.
- Hedef altında kalan ve iki kanal kanıtı tamamlanmış PÇ için mevcut Quality360 PUKÖ motoruna kontrollü geçiş vardır.


DOU Assess 6.47, 6.46 MEDEK Version Routing baselineını korur ve MÜDEK tarafını EK-1 disipline özgü eğitim planı konuları, ayrıntılı BBO/FBO kanıt hazırlığı, fakülte-paylaşımlı FBO kanıtları ve Action Center eksik-kanıt aksiyonlarıyla derinleştirir. 6.45 MEDEK ÖDR matrisi ve 6.46 sürüm/programa özgü çıktı motoru aynen korunur.

> **Yeşil ne demek?** Bu sürümde “yeşil”, gereksinimin DOU Assess içinde yönetilebildiği, sürümlenebildiği, kanıtlanabildiği ve test edildiği anlamına gelir. Bir akreditasyon kuruluşunun resmî onayını veya Doğuş Üniversitesi canlı ortam kabulünü otomatik olarak ifade etmez. Kuruluşların yayımladığı fiziksel şablonlar Resmî Şablon Kasası'na yüklenip SHA-256 ile dondurulabilir.

## 6.47 MÜDEK EK-1 + BBO/FBO Kanıt Hazırlığı

- MÜDEK 3.1 EK-1 disipline özgü konuları Ölçüt 5.1 altında izlenir.
- BBO/FBO hazırlık matrisi doğrudan kanıtı, destek kanıtını ve otomatik sistem sinyalini ayırır.
- BBO program bazlıdır; FBO kanıtları yalnız aynı fakülte içindeki programlarda ortak kullanılır.
- BBO 3.3 altında MÇ-1…MÇ-11 ayrı kanıt izlenir; FBO ortak ders/lab/deney, erişilebilirlik, güvenlik, kütüphane, bilişim ve sağlık alanlarını ayrıntılı izler.
- Bilgisayar/Yazılım/AI, Elektrik/Elektronik/Haberleşme/Kontrol ve Endüstri ailelerinde yerleşik EK-1 profilleri vardır; diğer programlar manuel doğrulamada kalır.
- Zorunlu EK-1/BBO/FBO açıkları Action Center içinde sorumlu, termin ve beklenen kanıtla PUKÖ önerisine dönüşür.

- İlk/genel yeniden değerlendirmede 2028 öncesi v1.1, 2028+ v2.0 backend guard ile uygulanır.
- Ara/izleme değerlendirmesi önceki genel MEDEK sürümünü devralır; tarihsel sürüm yoksa başvuru engellenir.
- MEDEK v2.0, 8 genel ölçüt / 45 alt ölçüt / 11 genel program çıktısı olarak sürümlenmiştir.
- İnternet ve Ağ Teknolojileri programa özgü çıktı kataloğu v1.1 (4) ve v2.0 (5) ayrı tutulur.
- Programa özgü çıktılar mevcut Program Çıktılarına açık framework mapping ile bağlanır; katalog bulunmayan program otomatik uygun sayılmaz.

## 6.45 MEDEK ÖDR Evidence Matrix

- MEDEK 2026 / v1.1 canonical framework remains **9 criteria / 46 subcriteria**.
- The official ÖDR preparation surface is modeled separately as **58 detailed prompt rows**, so reporting granularity does not corrupt the framework registry.
- Each ÖDR row can carry exact evidence, supporting framework-subcriterion evidence, responsible role, source module and manual maturity review.
- Ek I / Ek II are tracked in an **11-row preparation matrix** (course syllabi, faculty CVs, equipment, institutional/MYO profile, staffing, student-graduate data, credit/ECTS and admission/transition/graduation conditions).
- Conservative readiness: a failed authoritative system signal remains a gap even when a file is attached; system data without exact ÖDR evidence remains `attention`.
- General and interim evaluation scopes are separated; interim conditional areas are not falsely treated as mandatory before previous findings are imported.
- New Quality360 **MEDEK ÖDR** workspace provides priority gaps, evidence navigation, manual review and working DOCX export.
- Existing Role Workspace, Action Center, Student Outcome Card, MÜDEK routing and 6.41 compliance core remain intact.

## 6.41 ile kapanan akreditasyon/kalite alanları

- Kuruluş + sürüm bazlı kriter/ölçüt profili ve değişmez framework snapshot'ı.
- YÖKAK KİDR için **14 ölçüt / 46 alt ölçüt** kriter ağacı; alt ölçüt seviyesinde kanıt kodlama.
- MÜDEK 3.1 profili, MÜDEK BBO/FBO klasör presetleri ve gerçek kanıt dosyalarını içeren ZIP export.
- MEDEK, TURAK, SABAK ve EPDAD için sürümlü profil/rapor şablon kaydı.
- Resmî DOCX/XLSX/PDF/ZIP şablon dosyasını yükleme, SHA-256 ile kilitleme ve kaynak dosyayı bütünlük doğrulamalı saklama.
- Program Eğitim Amaçları (PEA), PEA → Program Çıktısı katkı matrisi.
- Program Çıktısı bileşenleri ve MÜDEK sürüm/bileşen kodu bağlama.
- Her öğrenci/mezun için kümülatif ÖÇ → PÇ → PÇ bileşeni **Çıktı Karnesi** ve mezuniyet snapshot'ı.
- Standart **Ders Dosyası / Ders Bilgi Paketi** DOCX üretimi.
- Curriculum / AKTS denetimi ve framework eşikleri.
- YÖKSİS/ÜAK biçimli sürümlü öğretim elemanı CV snapshot kayıtları.
- Dönem/ders bazlı öğretim yükü ledger ve toplam iş yükü.
- Mezunlar için 1 / 3 / 5 yıllık takip ve kapsama dashboard'u.
- Paydaş → karar → PUKÖ → kanıt zinciri; mevcut closed-loop kalite motoru korunur.
- Altyapı/laboratuvar için kapasite, erişilebilirlik, İSG ve periyodik bakım kaydı.
- Program/yıl bazlı bütçe planı, harcama kalemleri, kaynak ve varyans takibi.
- Politika/yönerge/prosedür/form için kontrollü doküman + revizyon + onay + SHA-256 + audit.
- YÖKAK misyon alanlarında Araştırma-Geliştirme, Toplumsal Katkı ve Uluslararasılaşma faaliyet/KPI/bütçe/partner/kanıt kayıtları.
- Akreditasyon başvuru yaşam döngüsü: hazırlık → gönderim → ön inceleme → düzeltme → ziyaret hazırlığı → saha ziyareti → 30 gün yanıt → karar → kapanış.
- Salt-okuma değerlendirici workspace, dondurulmuş snapshot hash'i ve ek belge talep/yanıt akışı.
- 30 maddelik Uyum Merkezi ve DOCX uyum matrisi.

## Korunan güçlü çekirdek

- Soru Bankası, karma sınav, A/B/C/D, PDF/baskı akışı.
- OMR/ADF tarama, belirsiz işaret inceleme, klasik/rubrik puanlama.
- Soru → ÖÇ → PÇ analitiği, öğrenci/soru/ders/program drill-down.
- MIN/AVG/MAX temsilî kanıt, evidence readiness, ziyaret görünümü.
- PUKÖ, kalite takvimi, kurul kararları, stratejik hedef/KPI.
- Audit log, güvenlik, rate-limit, production Docker/PostgreSQL/NGINX altyapısı.
- OBS Excel köprüsü ve Microsoft Entra PKCE entegrasyon altyapısı.

## Kurum ortamında ayrıca kabul edilmesi gerekenler

Bunlar **ürün özelliği eksiği değil, canlı saha kabul kapılarıdır**:

1. Doğuş Üniversitesi gerçek Microsoft Entra tenant/client/scope/rol eşlemesi.
2. Proliz/OBS tarafından sağlanacak gerçek API/web-service sözleşmesi ve veri mutabakatı.
3. Üniversite production VM üzerinde Docker/PostgreSQL/NGINX, DNS/TLS ve reverse-proxy kabulü.
4. Fiziksel yazıcı + ADF/OMR saha testi.
5. Hedef sunucuda yük, backup/restore ve felaket kurtarma tatbikatı.
6. Kullanılacak akreditasyon dönemine ait kuruluş resmî kaynak dosyalarının Şablon Kasası'na yüklenip dondurulması ve kalite birimince doğrulanması.

## Production kurulum / yükseltme

Detaylı ve güncel adımlar için `PRODUCTION-DEPLOYMENT-6.54.md` kullanın.

İlk kurulum:
```bash
cp .env.production.example .env
mkdir -p secrets
openssl rand -base64 48 | tr -d '\n' > secrets/postgres_password.txt
chmod 600 secrets/postgres_password.txt
# .env içindeki gerçek Entra/hostname bilgilerini doldurun
bash Preflight-Server.sh
bash Production-GoLive.sh install
```

Yükseltme:
```bash
# Mevcut production .env ve secrets/ yeni release klasörüne güvenli biçimde taşındıktan sonra:
bash Production-GoLive.sh upgrade
```

Doğrulama:
```bash
bash Production-GoLive.sh verify
```

> **Kesinlikle `docker compose down -v` veya `docker volume prune` kullanmayın.**


## 6.61 Survey & Indirect Assessment

- Öğrenci, mezun, işveren, dış paydaş ve program/ders değerlendirme anketleri.
- Anket sorusu → PÇ / PEA / kalite ölçütü bağlantısı.
- Anonim veya hash tabanlı kimlikli kampanya yanıtları.
- Program düzeyinde Direct + Indirect kanıt karması (varsayılan %70 / %30).

## 6.66 Production Acceptance Gate

- Entra, Proliz/OBS read-only, DNS/TLS, fiziksel OMR, backup/restore/DR, resmî şablon onayı, gerçek program pilotu ve RBAC izolasyonu tek canlı kabul merkezinde izlenir.
- Sistem sinyali ile kurum imzası birbirinden ayrılır; teknik readiness tek başına PASS üretmez.
- PASS/waived kayıtları kanıt/ticket/rapor referansı, doğrulayan kullanıcı ve zaman damgasıyla saklanır ve audit log'a yazılır.
- Release-ready yalnız tüm zorunlu kurum kabul kapıları yetkili kullanıcı tarafından kapatıldığında true olur.

## 6.65 Framework Lifecycle Precision

- TURAK 2026, SABAK 2026 ve EPDAD 2026 resmî süreç takvimleri kaynak kontrollü lifecycle catalog olarak eklendi.
- Kurumsal Hazırlık ekranı yaklaşan/aktif teslim, ön inceleme, değerlendirme, ziyaret ve karar pencerelerini tek zaman çizelgesinde gösterir.
- Takvim girdileri resmî kuruluş kaynak URL'si, doküman/ölçüt profili ve süreç aşamasıyla saklanır.
- Sistem kuruluş puanı veya kararı üretmez; programa özel resmî yazının genel takvimden üstün olduğu açıkça belirtilir.

## 6.64 Integration Acceptance Guard

- OBS entegrasyonu varsayılan olarak **read-only** çalışır; akademik veri içeri alınabilir ve sonuçlar OBS-uyumlu Excel olarak dışa aktarılabilir.
- Doğrudan OBS API write-back yalnız `OBS_WRITEBACK_ENABLED=true` ile, kurum onayı sonrası açılır; production ortamında HTTPS endpoint zorunludur.
- `/api/auth/config` yalnız güvenli entegrasyon durum bayraklarını yayınlar; token veya endpoint değeri açığa çıkarılmaz.
- Kurumsal Pilot readiness ekranı OBS veri yönünü zorunlu güvenlik kontrolü olarak izler.
- UI write-back butonunu yalnız kurumsal olarak etkinleştirilmiş durumda gösterir.
