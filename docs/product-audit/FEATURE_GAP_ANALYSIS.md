# DOU Assess — Özellik Boşluk Analizi

Öncelik: **P0** güvenlik/veri kaybı/çalışmama · **P1** kritik akış eksikliği · **P2** UX/rapor/modül eksikliği · **P3** iyileştirme.
Efor: **S** ≤ 3 gün · **M** 1-2 hafta · **L** 3-6 hafta · **XL** > 6 hafta (tek geliştirici, **tahmin**; ölçülmedi).
Durum etiketleri `PRODUCT_AUDIT.md` ile aynıdır. "Kanıt" sütunu doğrulanmış bulguya bağlanır.

---

## A. Güvenlik ve işletme

| # | Boşluk | Mevcut durum (kanıt) | Etki | Çözüm | İlgili dosya | Bağımlılık | Efor | Öncelik | Test yöntemi |
|---|---|---|---|---|---|---|---|---|---|
| A1 | **Canlı sunucu kimliksiz pilot modunda** | `auth_provider=pilot`: başlıksız istek **admin** bağlamı döndürür (denendi: `GET /api/auth/me` → `pilot-admin@local`, rol `admin`). Sunucu bu modda (`AUTH_REQUIRED=false`) | `assess.dogus.edu.tr`'ye erişebilen herkes tüm veriyi okuyup yazabilir (VPN/iç ağ ile sınırlı) | Kısa vadede nginx'te kurumsal IP izin listesi veya Basic Auth; kalıcı: OBS girişi (A2'ye bağlı) | `docker-compose.yml`, `nginx/default.conf`, `.env.internal` | A2 (OBS) | S (nginx) / M (OBS) | **P0** | Başlıksız `curl` → 401 beklenir |
| A2 | OBS/Proliz canlı bağlantısı yok | Sunucudan IIS `403` (kimlikli/kimliksiz); VPN'li bilgisayardan `200` | OBS girişi açılamıyor → A1 kapanamıyor | BT: sunucu IP'sini Proliz izin listesine ekle | – | BT | S (BT) | **P0** (A1 yüzünden) | Sunucudan `AkademikDonem` → 200 |
| A3 | Hız sınırlayıcı süreç belleğinde, pilotta kapalı | `security._RATE_BUCKETS`; `RATE_LIMIT_ENABLED` yalnız production'da açık | Kaba kuvvet/yük koruması yok; çok süreçte paylaşılmaz | Pilotta aç; Redis/nginx `limit_req` | `security.py`, nginx | – | S–M | P1 | 600+ istek → 429 |
| A4 | Oturum jetonu tarayıcı depolamasında | [DOĞRULANDI] `runtime-core.js:28`: `Bearer` jeton `sessionStorage` (`douEntraAccessToken`) içinde; pilot modda kimlik `localStorage`'daki e-postadan `X-DOU-Pilot-User` başlığıyla gider | XSS olursa jeton okunabilir (sekme kapanınca silinir; CSP katı) | OBS/Entra modunda `HttpOnly` çerez + CSRF jetonu veya kısa ömürlü jeton | `runtime-core.js`, `main.py` | – | M | P2 | CSP/XSS testi |
| A5 | Yedek **geri yükleme** tatbikatı | Yedek alınıyor (`pre-update-*.sql.gz`); geri yükleme sınanmadı | Veri kaybı riski | Aylık otomatik geri yükleme testi | `ops/`, `Restore-Server.sh` | – | M | P1 | Boş DB'ye geri yükle, sayım karşılaştır |
| A6 | Çok kiracılık yok | Yalnızca `users.tenant_id`; ADR plan düzeyinde | İkinci üniversite için ayrı kurulum gerekir | Satır düzeyi `tenant_id` + RLS veya şema-başı kiracı | `models.py`, `authz.py` | Karar (ADR) | XL | P2 (uluslararası için P1) | Kiracılar arası sızıntı testi |

## B. Ürün işlevleri

| # | Boşluk | Mevcut durum | Etki | Çözüm | Bağımlılık | Efor | Öncelik |
|---|---|---|---|---|---|---|---|
| B1 | Soru **versiyonlama** | Yalnız `version_no += 1` (`main.py:2850`), içerik saklanmıyor | Sınavda kullanılan sorunun geçmiş hali kanıtlanamaz | `question_versions` tablosu + karşılaştırma ekranı | Migration | M | P1 |
| B2 | Soru havuzu **dışa aktarma** | Yalnız şablon | Veri taşınabilirliği yok | Excel/CSV + QTI (isteğe bağlı) | – | S | P2 |
| B3 | Rubrik: çift puanlayıcı/kalibrasyon | Kör puanlama var | Puanlayıcı güvenilirliği ölçülemiyor | İkinci puanlayıcı + uyuşmazlık kuyruğu + Cohen κ | – | M | P2 |
| B4 | Bloom/ÖÇ **otomatik öneri** | `bloom_level` elle girilir | Soru etiketleme yükü | Yerel kural + isteğe bağlı AI önerisi (insan onaylı) | KVKK onayı | M | P2 |
| B5 | AI soru üretimi | Yok | – | Taslak soru üretimi, **taslak olarak** işaretle, yazar onayı | B4, KVKK | L | P3 |
| B6 | Doğal dille veri sorgulama | Yok | – | Salt-okunur, yetki süzgeçli sorgu katmanı | AI sağlayıcı kararı | L | P3 |
| B7 | Anomali tespiti (başarı sıçraması, kopya şüphesi) | Yok | Sınav güvenliği | İstatistiksel kural tabanlı uyarılar (z-skor, cevap deseni benzerliği) | – | M | P2 |
| B8 | Dönemler arası trend / karşılaştırma raporu | Dönem filtresi var, karşılaştırma raporu yok | Yönetici karar desteği | Dönem×ÖÇ trend grafiği + Excel | – | M | P2 |
| B9 | Rektörlük / ölçme uzmanı rolleri ve panoları | 6 rol; bu ikisi yok | İstenen kullanıcı gruplarına özel pano yok | 2 yeni rol + rol panoları | `authz.py` | M | P2 |
| B10 | Öğrenci hesabı | Yok (imzalı bağlantı) | Kendi ÖÇ gelişimini sürekli göremez (portalda sınav bazlı eklendi) | OBS öğrenci girişi (Proliz `OgrenciUserCheck`) | A2 | M | P2 |
| B11 | Akreditasyon çerçevesi **içerik doğrulaması** | Çerçeveler veri olarak yapılandırılmış; kodda "MÜDEK 3.1" etiketi; kaynakta MÜDEK **3.0 (8 Kasım 2023)** bulundu | Güncel olmayan ölçütle rapor | Resmî metinlerle (mudek.org.tr, yokak.gov.tr) satır satır karşılaştır, sürüm etiketini düzelt | Resmî belge erişimi | M | **P1** |
| B12 | Raporlama merkezi | Çok rapor ucu, tek katalog yok | Kullanıcı rapor bulamıyor | Rapor kataloğu + zamanlanmış rapor | – | M | P2 |
| B13 | OMR **saha doğrulaması** | Yalnız fixture; `services/omr.py` %0 kapsama | Gerçek formda hata riski | 50 gerçek form ile doğruluk ölçümü, kapsama artırma | Gerçek form seti | M | P1 |
| B14 | Madde havuzu "kalibrasyon" (IRT) | Klasik test kuramı var; IRT yok | İleri psikometri | Isteğe bağlı Rasch (uzun vade) | Veri hacmi | XL | P3 |

## C. Entegrasyon (ayrıntı: `INTEGRATION_AUDIT.md`)

| # | Boşluk | Çözüm | Efor | Öncelik |
|---|---|---|---|---|
| C1 | **DOU Core / DOU OBS Connector** katmanı yok; Proliz doğrudan çağrılıyor | Connector arayüzü (`SourceConnector` protokolü) arkasına al; Core'a yazan tek yol | L | P1 |
| C2 | Zamanlanmış senkronizasyon yok (yalnız giriş ve elle) | Zamanlayıcı işi + değişen kayıt (`Durumu değişen`) uçları | M | P1 |
| C3 | LTI 1.3 / SSO (Entra) / QTI içe-dışa aktarma | Standart protokoller | L–XL | P3 |

## D. UI/UX ve erişilebilirlik (ayrıntı: `UI_UX_AUDIT.md`)

| # | Boşluk | Kanıt | Çözüm | Efor | Öncelik |
|---|---|---|---|---|---|
| D1 | Renk kontrastı | axe: 333 düğüm | Token tabanlı düzeltme (bkz. `DESIGN_SYSTEM.md`) | M | **P1** |
| D2 | Etiketsiz `select` (5), sekme rolü hatası, odaklanamayan kaydırma kutusu | axe (critical) | Etiket/ARIA düzeltmeleri | S | **P1** |
| D3 | Tasarım sistemi dağınık | 1.194 renk, 48 yazı boyutu, 2.767 `!important` | Token + bileşen katmanı, kademeli göç | XL | P2 |
| D4 | Tüm metinler Türkçe sabit kodlu | i18n yok | Metin sözlüğü + dil seçici | L | P1 (uluslararası için) |
| D5 | Yükleme iskeleti, grafik sistemi | Düz metin/elle çubuk | Bileşen kütüphanesi | M | P2 |
| D6 | Koyu tema | Yok | Token'lar ile | M | P3 |
| D7 | Erişilebilirlik beyanı (VPAT/EN 301 549) | Yok | Manuel test + beyan | M | P2 |

## E. Kalite ve mühendislik

| # | Boşluk | Kanıt | Çözüm | Efor | Öncelik |
|---|---|---|---|---|---|
| E1 | `main.py` 5.051 satır | Tek dosyada iş mantığı | Router/servis ayrımı | L | P2 |
| E2 | Frontend monolit (`app.js` 3.393 uzun satır), derleme yok | Bakım/test zor | Modül sınırları, bileşen yapısı, JS birim testi | XL | P2 |
| E3 | Kökte 150+ sürüm notu `.md` | Depo gürültüsü | `docs/archive/`'e taşı | S | P3 |
| E4 | CI'da erişilebilirlik ve görsel regresyon yok | – | axe CI adımı | S | P2 |
| E5 | Yük testi yok | – | k6/Locust senaryosu (500 öğrenci) | M | P1 |

---

## Bağımlılık özeti
`A2 (BT izni)` → `A1 (kimlik doğrulama)` → `B10 (öğrenci girişi)`, `C2`.
`D4 (i18n)` + `A6 (çok kiracılık)` + `D7 (erişilebilirlik beyanı)` → uluslararası pazar.
`B11 (resmî ölçüt doğrulaması)` → akreditasyon raporlarının güvenilirliği.
