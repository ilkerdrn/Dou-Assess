# DOU Assess – Güvenlik Denetimi (OWASP bazlı)

**Kaynak:** `e98e723`/`a531ae7` (6.70.3). Yöntem: kod okuma + çalıştırılan dinamik kanıt (FastAPI `TestClient`, production-env simülasyonu, IDOR denemeleri). Canlı `assess.dogus.edu.tr`, gerçek Entra tenant ve gerçek nginx **test edilmedi (BLOCKED)**.
"[D]" = ben ayrıca doğruladım.

## Özet

| Şiddet | Sayı |
|---|---|
| Kritik | 1 |
| Yüksek | 2 |
| Orta | 6 |
| Düşük | 8 |

## Doğrulanmış çalışan kontroller (olumlu bulgular)

- Production'da `AUTH_REQUIRED=false` ile **uygulama başlamıyor** (`app/security.py:103,127-132` [D]).
- Production simülasyonunda: bearer'sız, pilot header'lı, sahte bearer'lı, yanlış Host header'lı istekler reddedildi.
- Entra JWT doğrulaması: RS256, aud/iss/tid/exp, scp + azp allow-list (`authz.py:112-146`). **Gerçek tenant ile denenmedi.**
- IDOR: başka dersin eğitmeni 21 uçta (ders/sınav/gradebook/results, PATCH/DELETE) 403 aldı.
- 395 route'un 363'ünde yetki kontrolü var; kalan 32 elle incelendi, gerçek boşluk yalnız S-08.
- Not güvenliği: `grading` durum kapısı, `grade_locked_at`, gerekçeli kilit açma, production'da maker-checker, dönem kilidi.
- CSP ve güvenlik başlıkları (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, COOP/CORP) yerinde.

## Bulgular

| ID | Şiddet | Bulgu | Kanıt | Senaryo |
|---|---|---|---|---|
| S-01 | **Kritik** | Pilot modda (`AUTH_REQUIRED=false`) başlıksız istek **otomatik admin** olur; `/api/auth/pilot-users` kimliksiz tüm e-postaları listeler. `docker-compose.yml` port 8080'i tüm arayüzlerde açar. | `/api/auth/pilot-users` + başlıksız `/api/users` → 200 | Pilot ortamı yanlışlıkla internete/iç ağa açık bırakılırsa herkes admin olur. **Yalnız pilot/dev modunda geçerli; production'da bloklanıyor (yukarıdaki olumlu bulgu).** |
| S-02 | Yüksek | `Backup-Server.sh:14` `.env` ve `secrets/`'i DB dump + öğrenci verisiyle **şifresiz aynı arşive** kopyalıyor. | [D] `Backup-Server.sh:14` | Yedek dosyası sızarsa DB parolası + öğrenci verisi (KVKK) birlikte açığa çıkar. |
| S-03 | Yüksek | `submit_responses` (`main.py:2921`) audit kaydı yalnız `{"responses": n}`; eski/yeni puan veya revizyon tablosu yok → yetkisiz not değişikliği **geriye dönük kanıtlanamaz**. | [D] `main.py:2921` | Görevin özellikle istediği "notların yetkisiz değiştirilmesini engelleyen kontrol" kısmen eksik — değişiklik önlenebiliyor (RBAC) ama **iz sürülemiyor**. |
| S-04 | Orta | `nginx/production.conf:30` `$proxy_add_x_forwarded_for` kullanıyor; istemci kontrollü ilk eleman alınabiliyor → rate-limit/IP tabanlı kontrol atlatılabilir. Canlı nginx'te doğrulanmadı. | `nginx/production.conf:30` | NOT_VERIFIED (canlı ortam) |
| S-05 | Orta | Audit log'da DB seviyesinde değiştirilemezlik/hash zinciri yok. | kod okuma | — |
| S-06 | Orta | Production simülasyonunda `/docs` ve `/openapi.json` **kimliksiz 200** döndü — API yüzeyi/iç mantık dışarı sızıyor. | dinamik test | — |
| S-07 | Orta | `app/static/app.js` içinde kullanıcı girdisi her yerde `esc()` ile kaçırılmıyor: `dashboardExamList` satırı `esc()` kullanıyor ama **`dashboardAttention` satırı** (`x.title`/`x.text`) kullanmıyor [D, satır doğrulandı]. CSP satır-içi script'i engelliyor ama DOM tabanlı HTML enjeksiyonu riski kalıyor. Runtime etkisi (gerçekten kötü amaçlı veri enjekte edilip render edildiğinde ne olduğu) `NOT_VERIFIED`. | [D] `app/static/app.js` (dashboardAttention bloğu) | — |
| S-08 | Orta/Düşük | `quality360_api.py:125` `mudek-ek1` ucu yetkisiz; ilgisiz bir eğitmen 200 aldı (aynı eğitmen `dashboard`/`matrix`'te 403). | `quality360_api.py:125` | Kapsam dışı kalite verisine düşük riskli okuma erişimi |
| S-09 | Orta | Öğrenci veri saklama süresi (`STUDENT_DATA_RETENTION_DAYS`) otomatik uygulanmıyor; yalnız elle çalışan kanıt purge var. Anonimleştirme takma-ad düzeyinde (12 haneli hash) — KVKK "unutulma hakkı" tam karşılanmıyor. | kod okuma | — |
| S-10 | Orta/Düşük | Açık ankette katılımcı anahtarı istemci tarafından seçiliyor; tekrar yanıt engeli teorik olarak aşılabilir. | kod okuma | — |
| S-11..S-18 | Düşük | `/api/health` production'da `build_sha`/`schema_expected` sızdırıyor (doğrulandı); rate limit process-içi (çoklu worker'da bölünüyor); `Content-Disposition` dosya adı riski (NOT_VERIFIED); blueprint `approved_by` istemciden geliyor (`main.py:2713`); `ENTRA_REQUIRE_DELEGATED_USER=false` sadece uyarı; e-posta `ILIKE` joker karakteri kapsam genişletebilir; DB bağlantısında TLS yok; `bs4` test lock'unda eksik (bkz. test raporu); **eski 6.18.4 paketinin `.env` dosyasında gerçek görünümlü bir DB parolası vardı** (6.70.3'te yok, rotasyon önerilir). | çeşitli | — |

## Test edilemeyenler (BLOCKED/NOT_VERIFIED)

- `assess.dogus.edu.tr` üzerinde gerçek nginx/XFF davranışı, gerçek Entra tenant ile uçtan uca giriş.
- Yedek/restore güvenliği (şifreleme olmadan arşivin gerçek saklanma yeri).
- Zip-bomb / aşırı büyük dosya dinamik testi (yalnız kod okumayla sınırlar doğrulandı).
- Harici dependency/CVE taraması (`Verify-Supply-Chain.sh` harici scanner gerektiriyor, çalıştırılmadı).

## Öneri sırası

1. **Kritik:** Pilot modun asla internete/iç ağa açık production benzeri bir ortamda çalışmadığından emin olun (ağ izolasyonu, deploy script kontrolü).
2. Not/puan değişikliği için eski-değer/yeni-değer revizyon tablosu ekleyin (S-03).
3. Yedekleri şifreleyin, `.env`/`secrets`'i yedek arşivinden çıkarın (S-02).
4. Production'da `/docs`/`/openapi.json`'ı kapatın (S-06).
5. nginx `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for` → güvenilir proxy zincirini doğrulayan bir yapıya geçin (S-04).
6. `app.js`'teki tüm kullanıcı girdisi render noktalarını `esc()` ile tutarlı hale getirin (S-07).
