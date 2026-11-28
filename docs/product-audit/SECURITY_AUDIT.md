# DOU Assess — Güvenlik Denetimi

**Yöntem:** (1) tüm API rotaları kimliksiz çağrıldı (`AUTH_REQUIRED=true`, OBS sağlayıcı); (2) kod incelemesi (`security.py`, `authz.py`, `student_portal_api.py`, `runtime-core.js`, `config.py`); (3) canlı pilot modunun kimliksiz davranışı denendi. Sızma testi **yapılmadı**; bu belge bir sızma testi raporu değildir.
Etiketler: **[DOĞRULANDI]** · **[KOD OKUMA]** (kodda görüldü, çalıştırılmadı) · **[VARSAYIM]**.

---

## 1. Doğrulanmış güçlü yanlar

| Konu | Bulgu | Kanıt |
|---|---|---|
| **Kimlik doğrulama zorunluluğu (OBS/Entra modu)** | 449 yol-yöntemden **430'u kimliksiz 401/403** döndü; kalan 19'u beklenen genel uçlar: `/api/health`, `/api/ready`, `/api/auth/config`, `/api/auth/obs-login`, jetonlu `/api/public/surveys/*` ve `/api/public/evaluator-workspaces/*`. **Sunucu hatası (5xx) 0.** | rota taraması [DOĞRULANDI] |
| **Yetkilendirme (RBAC + kapsam)** | 6 rol; program/ders kapsamı SQL süzgeciyle; `require_roles`, `require_course_management`, `require_exam_access` | `authz.py`, testler |
| **Öğrenci verisi gizliliği** | Değerlendirici odasında öğrenci adları maskeli (`A*** Y***`), başka program verisi 404, kapatılan çalışma alanı 410; öğrenci portalı yalnız kendi verisi | `test_674` [DOĞRULANDI] |
| **Öğrenci bağlantı jetonu** | HMAC-SHA256, `hmac.compare_digest`; başka öğrencinin jetonu 401; AUTH_REQUIRED/production'da yedek anahtar **yok** | `student_portal_api.py`, test [DOĞRULANDI] |
| **Girdi doğrulama / SQL enjeksiyonu** | Pydantic şemaları, SQLAlchemy ORM; ham SQL yalnızca sabit `SELECT 1` ve `alembic_version` sorguları | grep [DOĞRULANDI] |
| **Güvenlik başlıkları** | `Content-Security-Policy` (`script-src 'self'; style-src 'self'; frame-ancestors 'none'`), `X-Frame-Options: DENY`, `Strict-Transport-Security` (HTTPS'te) | `security.py` [KOD OKUMA] |
| **XSS yüzeyi** | 377 `innerHTML` kullanımı; 1.029 `esc()` çağrısı (kaçırma yardımcısı) ve katı CSP (satır içi betik/stil yok) | [KOD OKUMA] |
| **Yükleme sınırı** | `MAX_UPLOAD_MB=20`, `read_upload_limited`; yükleme hız sınırı ayrı | `config.py` [KOD OKUMA] |
| **Denetim izi** | `AuditLog` (kim/ne/ne zaman/yük); puan değişiklikleri `ResponseGradeRevision` ile öncesi/sonrası | modeller, testler |
| **Hata yönetimi** | Beklenmeyen hata kullanıcıya `INTERNAL_ERROR` + istek kodu döner (yığın izi sızmaz) | rota taraması sırasında 5xx 0; `main.py` işleyici |
| **Bağımlılık güvenliği** | `requirements.lock`, SBOM, `Verify-Supply-Chain.sh` | depo dosyaları [KOD OKUMA] |

## 2. Bulgular (öncelikli)

### S1 — P0: Canlı sunucu kimlik doğrulamasız çalışıyor [DOĞRULANDI]
- **Ne:** `AUTH_REQUIRED=false`, `AUTH_PROVIDER=pilot`. Başlıksız `GET /api/auth/me` → `pilot-admin@local`, rol **admin**. Başlık (`X-DOU-Pilot-User`) ile herhangi bir kullanıcı taklit edilebilir; kimlik, tarayıcıda `localStorage`'daki e-posta.
- **Etki:** `assess.dogus.edu.tr`'ye ağ erişimi olan **herkes** tüm akademik veriyi okuyup değiştirebilir. Erişim şu an iç ağ/VPN ile sınırlı (kullanıcı bildirimi; dışarıdan erişim sınanmadı [VARSAYIM]).
- **Çözüm:** Hemen: nginx'te kurumsal IP aralığı izin listesi veya geçici Basic Auth. Kalıcı: OBS girişi (`INTEGRATION_AUDIT` A2 engelini kaldırınca). Üretim konuşlandırmasında `docker-compose.production.yml` zaten AUTH_REQUIRED'ı zorunlu tutar (`security.validate_security_config`).

### S2 — P1: Hız sınırlama pilotta kapalı, süreç belleğinde [DOĞRULANDI]
`RATE_LIMIT_ENABLED` varsayılanı yalnız production'da açık; sayaçlar süreç içi sözlük (`_RATE_BUCKETS`). Giriş ucuna kaba kuvvet denemesine karşı **hesap kilitleme yok** [KOD OKUMA: obs-login hata sayacı bulunamadı → VARSAYIM]. Çözüm: nginx `limit_req` + uygulama içi giriş başarısızlık sayacı.

### S3 — P1: OBS şifresi uygulamadan geçiyor [KOD OKUMA]
Giriş formu OBS şifresini API'ye gönderir (kod, MD5 özetini Proliz'e iletir ve **şifreyi saklamaz** — doğru). Risk: Proliz'in MD5 gerektirmesi zayıf bir protokoldür (Proliz tasarımı). Önlem: **yalnız HTTPS** (`REQUIRE_HTTPS`; sunucuda pilot düzeninde `false` → host nginx HTTPS sağlıyor, doğrulanmalı); günlüklerde şifre/özet yer almadığını test et.

### S4 — P1: Öğrenci bağlantıları süresiz [KOD OKUMA]
`make_token(exam_id, student_id)` HMAC'i **son kullanma tarihi içermez**; itiraz penceresi ayrı denetleniyor ama bağlantı sızarsa sonuçlar süresiz görüntülenebilir. Çözüm: jetona son kullanma + iptal listesi (veya sınav bazlı rotasyon).

### S5 — P2: Denetim kaydı uygulama düzeyinde değiştirilemez [VARSAYIM]
`AuditLog` için veritabanı tetikleyicisi/salt-ekleme izni bulunamadı; yönetici DB erişimi olan biri kayıt silebilir. Çözüm: ayrı salt-ekleme rolü veya hash zinciri (mühürlü kayıtlarda SHA-256 zaten var).

### S6 — P2: Tenant izolasyonu yok [DOĞRULANDI]
Veri tablolarında `tenant_id` yok → bir kurulum = bir kurum. İkinci üniversite için ayrı dağıtım gerekir (bkz. `docs/commercial/ADR-multi-tenant.md`).

### S7 — P2: Oturum jetonu depolaması [DOĞRULANDI]
Bearer jeton `sessionStorage` (`runtime-core.js`); XSS durumunda okunabilir. Katı CSP bunu zorlaştırır. Çözüm: `HttpOnly; SameSite=Strict` çerez + CSRF jetonu.

### S8 — P2: CSRF
Bearer/özel başlıkla kimlik taşındığı için klasik çerez-CSRF yüzeyi yok [KOD OKUMA]. Çerez tabanlı oturuma geçilirse CSRF jetonu zorunlu olur (S7 ile birlikte tasarla).

### S9 — P2: Dosya güvenliği [KOD OKUMA]
Tarama/kanıt dosyaları kalıcı birimde; tür/boyut sınırı var. Doğrulanmayanlar: virüs taraması, içerik türü sızdırma testi, kanıt dosyası erişimlerinin her istekte yetki süzgeci (testlerde kapsanan kısım dışında) [VARSAYIM].

### S10 — P2: AI veri güvenliği [KOD OKUMA + `docs/KVKK-AI-OCR-DEGERLENDIRME.md`]
AI puan önerisi varsayılan **kapalı**; açılması için KVKK onayı + kurum ayarı + yapılandırma gerekir; istek içeriği günlüklenmez, yalnız uzunluk/ana makine adı denetim kaydına yazılır. Yerel cevap gruplama dış servise veri göndermez. Not: sağlayıcıya cevap metni **gönderiliyorsa** öğrenci kimliği içermemesi sağlanmalı (şu an yalnız cevap metni gidiyor — kod okuma).

## 3. Doğrulanmamış / yapılmayan kontroller
Gerçek sızma testi, bağımlılık zafiyet taraması (CVE), TLS yapılandırma testi, nginx başlıkları, yedeklerin şifrelenmesi, günlük saklama süresi/erişimi, sır yönetimi (`.env.internal` dosya izinleri), konteyner kullanıcı ayrıcalıkları (`douassess` kullanıcı var; sandbox sınanmadı) → `GUVENLIK-TESTI-PLANI.md` (docs/commercial) ile birlikte bağımsız test önerilir.
