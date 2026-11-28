# DOU Assess — Entegrasyon Denetimi (Proliz OBS · DOU OBS Connector · DOU Core)

**Kural:** Çalışmayan entegrasyon çalışıyor olarak raporlanmaz. Bu belgede her madde **canlı doğrulama** ile **birim test (sahte Proliz)** ayrı işaretlendi.

Hedef akış: `Proliz OBS → DOU OBS Connector → DOU Core → DOU Assess`.

---

## 1. Özet durum

| Katman | Durum | Kanıt |
|---|---|---|
| Proliz REST istemcisi (`obs_proliz.py`) | 🧪 Kod var, **sahte sunucuyla testli**; canlıda sunucudan **çalışmıyor** | `test_671`, `test_672`; canlı curl'ler |
| Öğretim elemanı girişi + ders/öğrenci senkronu (`obs_proliz_sync.py`) | 🧪 Kod var, testli; **canlıda hiç çalıştırılmadı** | testler |
| DOU OBS Connector (ayrı servis) | ⛔ Yok — yalnız `ProlizConnector` sınıfı (uygulama içi) | kod |
| DOU Core (ortak akademik veri) | ⛔ Yok — Assess kendi tablolarına doğrudan yazar | kod |
| Excel ile veri girişi (yedek yol) | ✅ Çalışıyor | `test_675` |

---

## 2. HTTP 403 — kök neden (kanıtlı)

**Gözlem (2026-11-28):**

| İstek | Nereden | Sonuç |
|---|---|---|
| `GET /Obs/Genel/AkademikDonem` kimliksiz | Sunucu (10.8.1.133) | **403** `Microsoft-IIS/10.0` "Forbidden: Access is denied" |
| aynı, `douassess` kimliğiyle | Sunucu | **403** |
| aynı, kimliksiz | VPN'li kullanıcı bilgisayarı | **401** (normal: kimlik iste) |
| aynı, `douassess` kimliğiyle | VPN'li kullanıcı bilgisayarı (`curl.exe`) | **200** |
| DNS | Sunucu ve bilgisayar | ikisi de `10.8.1.118` |
| Kendi OBS (sicil) hesabıyla Basic | Sunucu | 403 |

**Sonuç [DOĞRULANDI]:** Aynı adres, aynı yol, aynı kimlik; fark yalnızca **kaynak adres**. Sunucudan gelen istek IIS/güvenlik duvarında **kimlik aşamasına gelmeden** reddediliyor. Kimlik, şifre, yol ve istemci türü (curl) elendi. **Kök neden: Proliz API'sinin kaynak IP izin listesinde 10.8.1.133 yok** (veya sunucu alt ağından 10.8.1.118:443 güvenlik duvarında engelli). Bu kod sorunu değildir.
**Çözüm sahibi:** BT (Proliz/IIS ve ağ). Talep metni sohbette verildi: "10.8.1.133 → 10.8.1.118:443 izni".
**Doğrulama testi (izin sonrası):** sunucuda kimlikli `AkademikDonem` → 200; ardından `POST /api/auth/obs-login` gerçek sicil ile.

---

## 3. Kontrol listesi (istenen doğrulamalar)

| Madde | Durum | Not |
|---|---|---|
| API bağlantısı | ❌ canlıda | 403 (yukarıda) |
| Kimlik doğrulama | 🧪 | `AkademikUserCheck`: şifre **MD5 (büyük harf onaltılık)** olarak gönderilir (`hash_obs_password`); Proliz belgesine uygun; şifre saklanmaz |
| Servis hesabı | ✅ mevcut | `douassess` kullanıcısı VPN'den çalışıyor (Swagger "Authorized") |
| Veri eşleştirme | 🧪 | sicil→öğretim elemanı, dönem adı→(yıl, dönem) ayrıştırma (`_parse_donem_ad`), ders/öğrenci/kayıt → `Course`/`Student`/`Enrollment` |
| Senkronizasyon | 🧪 | giriş anında ve "OBS'den getir" (`/api/integrations/obs/resync`); **zamanlanmış senkron yok** |
| Tekrarlanan kayıt kontrolü | 🧪 | yinelenen ders/öğrenci için güncelleme (upsert) davranışı testli; **gerçek veride sınanmadı** |
| Hata yönetimi | ✅ | `ObsLoginError` (401/403 mesajı), `ProlizError` → 502; başarısızlık `IntegrationSyncRun`'a yazılır |
| Loglama / senkron geçmişi | ✅ | `IntegrationSyncRun` + denetim kaydı (`obs_login`, `obs_login_failed`); arayüzde son senkron zamanı |
| Manuel senkronizasyon | ✅ | "OBS'den getir" (şifre yeniden istenir, saklanmaz) |
| Veri tutarlılığı | ⛔ | Proliz ile Assess arasında **karşılaştırma/uzlaştırma raporu yok** |
| İlk yönetici | 🟡 | `BOOTSTRAP_ADMIN_EMAILS` Proliz EPOSTA ile **birebir** eşleşmeli; gerçek eşleşme doğrulanmadı |
| Not geri yazma | 🟡 | `OBS_RESULTS_ENDPOINT/TOKEN` anahtarları sunucu ayar dosyasında var (değerlerin dolu/geçerli olduğu doğrulanmadı); varsayılan **salt-okunur mod**, geri yazma kapalı (`writeback_enabled:false`) |

---

## 4. Mimari boşluk: Core + Connector

**Mevcut:** Assess, Proliz'i doğrudan çağırıp kendi şemasına yazıyor. Bu, görev tanımındaki "DOU Assess OBS değildir; ortak akademik veri DOU Core'dan gelir" ilkesiyle **çelişir**: ders/öğrenci verisinin sahibi şu an Assess.

**Önerilen yapı** (kademeli, geri uyumlu):
1. **Connector arayüzü:** `SourceConnector` (protokol): `fetch_terms()`, `fetch_courses(term)`, `fetch_roster(course)`, `fetch_instructor(sicil)`. Mevcut `ProlizConnector` bunu uygular; ikinci bir kaynak (CSV/Excel, Banner, vb.) aynı arayüzü kullanır.
2. **Core şeması (`core_*` tabloları veya ayrı servis):** `core_term`, `core_course`, `core_person`, `core_enrollment` — salt-okunur görünüm olarak Assess'e açılır; Assess yalnız **referans** tutar (`course.core_id`).
3. **Senkron işi:** zamanlayıcı + `Durumu değişen akademisyen/öğrenci` uçları ile artımlı; her çalıştırmada `IntegrationSyncRun` özeti ve uzlaştırma raporu.
4. **Anahtarlama:** `core_id` + `source_system` ile eşleme; Excel içe aktarma da aynı Core'a yazar (tek doğruluk kaynağı).
- Efor: **L** (3-6 hafta); bağımlılık: BT izni, Core'un ayrı proje olup olmadığı kararı.

## 5. Doğrulama planı (canlı)
1. BT izni → sunucu `curl` 200 (5 uç). 2. Gerçek sicil ile giriş + dönem seçimi. 3. Bir hoca için ders/öğrenci sayıları Proliz ile karşılaştırma (elle). 4. Aynı hocayla ikinci senkron → **yinelenen kayıt oluşmadığını** say. 5. `IntegrationSyncRun` kaydı ve denetim kaydı gözden geçirme.
