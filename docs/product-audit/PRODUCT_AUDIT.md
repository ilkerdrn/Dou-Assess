# DOU Assess — Ürün Denetimi

**Tarih:** 2026-11-28 · **Kod durumu:** `main` + açık PR #12 (386 test) · **Yöntem:** kod ölçümü, gerçek test çalıştırma, canlı tarayıcı gezintisi, yetkisiz erişim taraması.
**Kural:** Bu denetim sırasında kod, veritabanı ve çalışan sunucu değiştirilmedi. Yalnızca `docs/product-audit/` altına yeni dosyalar yazıldı.

Etiketler: **[DOĞRULANDI]** = çalıştırılıp görüldü/ölçüldü · **[KAYNAKLI]** = dış kaynak (bağlantılı) · **[VARSAYIM]** = doğrulanmadı, denetlenmeli.

Bu klasördeki öncesi: `docs/audit/DOU_ASSESS_*.md` (6.70.3 sürümüne dayalı statik inceleme). Bu denetim onları güncel sürümde gerçek ölçümlerle yeniler; çelişen yerlerde bu rapor geçerlidir.

---

## 1. Mimari sınır (görev tanımı) ile mevcut durum

| İstenen | Mevcut durum | Sonuç |
|---|---|---|
| DOU Assess bağımsız ölçme-kalite platformu | Öğrenci kaydı/OBS işlevi yok; ders/öğrenci verisi dışarıdan (Excel/Proliz) gelir | [DOĞRULANDI] uyumlu |
| Akış: Proliz → **DOU OBS Connector** → **DOU Core** → DOU Assess | Kodda "DOU Core" **yok**; Proliz çağrıları uygulama içinde (`obs_proliz.py`, `obs_proliz_sync.py`). Küçük bir `ProlizConnector`/`get_connector` soyutlaması var (`obs_proliz_sync.py:82,111`) ama ayrı bir DOU OBS Connector servisi değil | [DOĞRULANDI] **hedef mimari uygulanmamış**; ara adaptör düzeyinde (bkz. INTEGRATION_AUDIT) |
| DOU OS / DOU BEP ile karışmama | Repoda bu projelere ait kod yok | [DOĞRULANDI] uyumlu |

---

## 2. Sistem envanteri (ölçülmüş)

| Ölçüt | Değer | Kaynak |
|---|---|---|
| Backend | FastAPI + SQLAlchemy 2 + Alembic, Python 3.12 | `requirements.txt` |
| Frontend | Vanilla JS (build yok, framework yok), tek `index.html` + `app.js` (3.393 satır; satırlar çok uzun) + `styles.css` (2.198 satır) | satır sayımı |
| Veritabanı | PostgreSQL 17 (sunucu), SQLite (test); **115 tablo**, **48 migration** | `models.py`, `migrations/` |
| API | **449 yol-yöntem** (92 GET, 67 POST, 17 PATCH, 11 DELETE, 3 PUT — yalnız `main.py` doğrudan rotaları; 16 ayrı router dosyası ek) | rota taraması |
| Python dosyası | 53 (`app/`), 24 servis modülü | sayım |
| Test | **386 test geçiyor** (pytest) + 2 tarayıcı (Playwright) testi; satır kapsama **%79,9** (backend, 16.965 ifade) | gerçek çalıştırma |
| Dağıtım | Docker Compose (db, migrate, api, worker, scheduler, nginx); pilot ve production düzeni | `docker-compose*.yml` |
| Depo hijyeni | Kökte **150'den fazla** sürüm notu/doğrulama `.md` dosyası (`RELEASE-NOTES-*`, `FINAL-VALIDATION-MATRIX-*`, `PACKAGE-CLEANUP-*`…) | `ls` |

Kapsama en düşük dosyalar: `services/omr.py` %0 (kullanılmayan/eski olabilir), `quality360_api.py` %58,9, `services/scan.py` %64,3, `services/operations.py` %66,3, `security.py` %66,8. Frontend (JS) için otomatik kapsama yok; yalnızca 2 tarayıcı testi.

---

## 3. Roller ve yetkiler

6 rol tanımlı (`authz.py`): `admin`, `quality`, `instructor`, `program_head`, `department_head`, `faculty_admin`. Program/ders kapsamı SQL ile süzülür. Arayüz rol bazlı sadeleştirir (`applyRoleUI`: hoca, kalite, yönetim için farklı menü).

Eksikler [DOĞRULANDI]: ayrı **rektörlük/üst yönetim** rolü yok; ayrı **ölçme-değerlendirme uzmanı** rolü yok; **öğrenci hesabı** yok (öğrenci yalnızca imzalı bağlantıyla kendi sınavını görür); **denetçi/değerlendirici** için jetonlu "Değerlendirici Odası" var (salt okunur, maskeli öğrenci verisi).

---

## 4. Modül durumu (gerçek doğrulamaya göre)

Sınıflar: ✅ Çalışıyor ve doğrulandı · 🟡 Kısmen · 🧪 Yalnızca test/fixture ile doğrulandı · ⛔ Eksik · ❌ Canlıda çalışmıyor.

| # | Modül | Durum | Kanıt |
|---|---|---|---|
| 1 | Akademik yapı (program/ders/öğrenci/kayıt/dönem) | ✅ | testler; 27 ekran tarayıcıda hatasız açıldı; Excel Veri Merkezi gidiş-dönüş testli |
| 2 | Excel içe/dışa aktarma (Türkçe şablon, doğrulama, hata raporu) | ✅ | `test_675…`, `imports`/`question_bank_import` testleri |
| 3 | ÖÇ / PÇ yönetimi, 1-5 katkı matrisi, **toplu düzenleme** | ✅ | `test_678…`; tarayıcıda uygulama denendi |
| 4 | ÖÇ değişiklik onay akışı, başarı eşikleri (sürümlü) | ✅ | testler (`test_674`) |
| 5 | Soru bankası (CRUD, Excel içe aktarma, yinelenen tespiti, yaşam döngüsü) | ✅ | testler; e2e |
| 5b | Soru bankası **dışa aktarma** | ⛔ | yalnızca şablon indirme var |
| 5c | Soru **versiyon geçmişi** (içerik saklama) | ⛔ | [DOĞRULANDI] `main.py:2850` yalnızca `version_no += 1`; modelde soru sürümü tablosu yok (`CurriculumVersion` yalnız müfredat için) |
| 6 | Sınav oluşturma, kitapçık (A-D), QR kağıt, PDF | ✅ | testler (`test_63` OMR üretimi okunabilir) |
| 7 | Optik okuma (OMR) + klasik tarama + inceleme | 🧪 | laboratuvar fixture'ı ile doğrulandı; **gerçek form/tarayıcı saha testi yapılmadı** |
| 8 | Klasik puanlama: rubrik, taranmış cevap yanında, kör puanlama, soru bazlı seri, hızlı tablo, **benzer cevap grupları** | ✅ | testler; arayüz yapısı doğrulandı |
| 9 | Not kilidi, itiraz portalı (öğrenci imzalı bağlantı), puan revizyon geçmişi | ✅ | `test_674` |
| 10 | Sınav analizi (güçlük, ayırt edicilik, KR-20/Cronbach, ÖÇ/PÇ gerçekleşme) | ✅ | `services/analytics.py` gerçek veriden hesaplar; testli |
| 11 | Program analitiği, Program Çalışma Alanı, Öğrenci karneleri | ✅ | testler; tarayıcı |
| 12 | Program Değerlendirmesi + Kanıt Merkezi | ✅ | `test_69…` |
| 13 | Kalite 360 / PUKÖ / MÜDEK-MEDEK-YÖKAK çerçeveleri, öz değerlendirme taslağı (Word) | 🟡 | `quality360_api.py` kapsama %59; taslak üretimi var |
| 14 | Değerlendirici Odası (dış değerlendirici, salt okunur, maskeli) | ✅ | testler |
| 15 | Anket / dolaylı ölçme | ✅ | `test_661` |
| 16 | Bildirimler + hedef altı ÖÇ uyarısı | ✅ | `test_677`; e-posta 🟡 (kod var, **canlıda SMTP yapılandırılmadı**) |
| 17 | Arşiv/saklama, denetim kaydı, yedekleme betikleri | ✅/🟡 | testler; yedek **geri yükleme** tatbikatı doğrulanmadı [VARSAYIM] |
| 18 | **OBS/Proliz girişi ve senkronizasyon** | ❌ | kod+test var, **canlıda sunucudan 403** (bkz. INTEGRATION_AUDIT) |
| 19 | Yapay zekâ: puan önerisi | 🟡 | kod var, **varsayılan kapalı** (KVKK onayı + yapılandırma gerekir) |
| 19b | Yapay zekâ: soru üretimi, Bloom sınıflama, ÖÇ eşleme önerisi, doğal dil sorgu, anomali tespiti | ⛔ | kodda yok |
| 20 | Çok kiracılık | ⛔ | yalnızca `users.tenant_id` kolonu; veri tablolarında yok; ADR belgesi plan düzeyinde |
| 21 | Çok dillilik (İngilizce vb.) | ⛔ | tüm metinler Türkçe sabit kodlu; i18n altyapısı yok |
| 22 | Koyu tema | ⛔ | `prefers-color-scheme` yok |

**Demo ve gerçek veri:** `/api/pilot/demo-scenario` demo üretir; `tools/cleanup_demo_data.py` demo verisini siler (sunucuda uygulandı). Production ortamında demo uç noktası kapalıdır (`APP_ENV=production`).

---

## 5. Test altyapısı

- 386 pytest (birim + API entegrasyon), 2 Playwright; CI: `backend-tests` ve `e2e-tests` her PR'da çalışıyor ve yeşil.
- Kapsanmayanlar [DOĞRULANDI]: JS birim testi yok; erişilebilirlik testi CI'da yok; görsel regresyon yok; yük/performans testi yok; gerçek OMR sahası yok.
- Güçlü yan: kapsama %79,9; ayrıca sözleşme testleri (HTML id'leri, CSP uyumu).

---

## 6. Performans ve ölçeklenebilirlik

- [DOĞRULANDI] Hız sınırlayıcı **süreç belleğinde** (`security._RATE_BUCKETS`); birden fazla API süreci/konteyneri çalıştırılırsa paylaşılmaz. Pilot düzeninde varsayılan olarak **kapalı** (`RATE_LIMIT_ENABLED` yalnızca production'da açık).
- [DOĞRULANDI] `main.py` 5.051 satır, 3.693 ifade; tek dosyada çok sayıda iş mantığı (bakım riski).
- [VARSAYIM] Yük testi yapılmadı; büyük sınıf (500+ öğrenci) için analiz sayfalama/zamanlama doğrulanmadı. Zamanlayıcı her süpürmede onaylı 200 sınav için analiz hesaplar (`_emit_below_target_alerts`); veri büyüdükçe önbellek/artımlı hesap gerekebilir.

---

## 7. Sonuç (özet)

Çekirdek akademik akış (ders → ÖÇ/PÇ → soru → sınav → okuma → puanlama → analiz → kalite kanıtı) **gerçekten çalışıyor ve testli**. Üç büyük risk: (1) canlı sunucu **kimlik doğrulamasız** pilot modunda, (2) OBS/Proliz canlı bağlantısı çalışmıyor, (3) hedef platform mimarisi (Core/Connector, çok kiracılık, çok dillilik, AI) henüz yok. Ayrıntı: `FINAL_RECOMMENDATIONS.md`.
