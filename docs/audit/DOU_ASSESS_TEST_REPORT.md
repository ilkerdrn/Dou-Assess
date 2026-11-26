# DOU Assess – Test Raporu

**Denetlenen kaynak:** `ilkerdrn/Dou-Assess` @ `e6d20d0` (başlangıç: kullanıcının yüklediği `DOU-Assess-6.70.3-SIMPLE-PANEL-FULL.zip`, commit `e98e723`)
**Tarih:** 2026-11-26
**Ortam:** Claude Code bulut konteyneri, Linux, Python 3.13.18, SQLite (test varsayılanı), Chromium 1243 (Playwright 1.57.0). **Production sunucusu ve PostgreSQL bu ortamda YOK.**

> Bu rapordaki her sonuç aşağıdaki komutlarla bu oturumda gerçekten çalıştırılmıştır. Çalıştırılmayanlar açıkça `NOT_VERIFIED` işaretlidir.

## 0. Güncelleme — denetim sonrası düzeltmeler uygulandı

İlk denetimde (commit `e98e723`) 259/263 pytest + 0/2 E2E PASS idi (aşağıdaki §1-2 o anı belgeler). Denetim sonrasında aynı oturumda **gerçek kök nedenler bulunup düzeltildi** (commit `e6d20d0`):

- **Kritik, üretim etkili CSS hatası:** `.login-gate{display:grid!important}` (6.70.1 hotfix) ile jenerik `.hidden{display:none!important}` kuralı aynı özgüllükte çakışıyordu; dosyada daha sonra gelen kural kazandığı için **giriş ekranı başarılı login sonrasında asla kapanmıyor, tüm uygulamayı z-index:1000 ile kaplıyordu**. `.login-gate.hidden{display:none!important}` (daha yüksek özgüllük) eklenerek düzeltildi — `app/static/styles.css`.
- **CSP ihlali (23+3 nokta):** `app/static/app.js` ve `app/static/index.html` içinde dinamik yüzde/skor çubukları `style="width:${x}%"` gibi satır-içi stil öznitelikleriyle render ediliyordu; production CSP'si (`style-src 'self'`, `unsafe-inline` yok) bunları **sessizce engelliyordu** — yani ilerleme çubukları, başarı yüzdeleri, sağlık skorları gerçekte hiç görünmüyordu. `data-style` + `MutationObserver` tabanlı CSSOM hydration mekanizmasıyla düzeltildi (CSSOM `.style.x=` yazımları CSP style-src'den etkilenmiyor, doğrulandı).
- **`/favicon.ico` 404:** `<link rel="icon">` eksikti; mevcut logo favicon olarak bağlandı.
- 4 eski pytest sözleşme testi ve 2 E2E testi, 6.70.3'ün kasıtlı menü/metin değişikliklerine göre güncellendi (bkz. §2).

**Düzeltme sonrası sonuç: 263/263 pytest PASS, 2/2 E2E PASS.** Komutlar ve kanıtlar aynen aşağıda; §2'deki kök-neden analizi hâlâ geçerli ve önemli (ileride benzer hatalar için).

## 1. Çalıştırılan testler (ilk tarama, commit `e98e723`)

| # | Test | Komut | Sonuç |
|---|---|---|---|
| T1 | Backend unit/integration/API (SQLite) | `.venv/bin/python -m pytest tests/ -q` | **259 PASS / 4 FAIL** (263 test, ~42 sn). İki ayrı çalıştırmada aynı sonuç (tekrarlanabilir). **Düzeltme sonrası: 263/263 PASS.** |
| T2 | Tarayıcı E2E (Playwright/Chromium) | `.venv/bin/python -m pytest e2e/ -q` | **0 PASS / 2 FAIL.** **Düzeltme sonrası: 2/2 PASS.** |
| T3 | Bağımlılık kurulumu (belgelenen yol) | `pip install -r requirements.txt -r requirements-dev.lock` | **BAŞARISIZ DEĞİL ama eksik:** `bs4` hiçbir lock dosyasında yok → 3 test dosyası `ModuleNotFoundError` ile toplanamadı. `pip install beautifulsoup4` sonrası T1 çalıştı. **Henüz düzeltilmedi** — `requirements-dev.lock`'a eklenmeli. |
| T4 | Kaynak bütünlük manifesti | `sha256sum -c SOURCE-MANIFEST.sha256` | **4 uyuşmazlık:** `app/static/app.js`, `index.html`, `styles.css` (+ benim eklediğim `.gitignore`); 3 `data/*/.gitkeep` dosyası pakette yok. Düzeltmeler bu dosyaları ayrıca değiştirdiği için manifest artık daha da eski; **manifest yeniden üretilmeli.** |

## 2. Başarısız testler ve kök neden

| Test | Hata | Kök neden (kanıt) |
|---|---|---|
| `test_625_navigation_and_pages_contract` | `'Derslerim' in HTML` yanlış | 6.70.3 "Simple Panel" arayüzü eski etiketleri değiştirdi; test güncellenmedi |
| `test_642_action_center_and_student_workspace_contract` | `'ACTION CENTER · EKSİKLERİM'` yok | Aynı |
| `test_operations_ux::test_6161_grouped_navigation…` | `'Çalışma Alanım'` yok | Aynı (index.html'de grup adı artık "Ders & Sınav") |
| `test_operations_ux::test_617_final_product_information_architecture…` | `'Çalışma Alanım'` yok | Aynı |
| `e2e/test_question_bank_browser.py` | `button[data-page="bank"]` **görünür değil**, 30 sn timeout | **Gerçek kök neden (ilk hipotezim yanlıştı — düzeltiyorum):** `workspaceNavGroup` admin için de varsayılan açık; sorun nav grubu değil, **giriş ekranının hiç kapanmaması** (bkz. §0). `data-page="data"` düğmesi de 6.70.3'te kaldırılmış, yerine `programs`/`courses`/`students` ayrı düğmeleri geldi (test eski seçiciyi kullanıyordu). |
| `e2e/test_critical_navigation_browser.py` | `button[data-page="data"]` bulunamadı/görünmez | Aynı — giriş ekranı CSS hatası + kaldırılmış `data-page="data"` düğmesi |

**Sonuç (güncellenmiş):** 6.70.3, **tam regresyon çalıştırılmadan** yayınlanmış. `SIMPLE-PANEL-6.70.3.md` yalnızca "Focused regression: 17/17 PASS" bildiriyor; `CHANGELOG.md` 6.70 için "253/253 PASS" diyordu. 4 pytest regresyonu gerçekten yalnızca **isim değişikliği** kaynaklıydı (test güncellenmemiş, uygulama doğru). 2 E2E kırığı ise görünürde "6.70.3 regresyonu" gibi duruyordu ama kök neden araştırıldığında **6.70.1'den kalma, önceden fark edilmemiş kritik bir CSS hatası** (login ekranı asla kapanmıyor) ve **CSP ile satır-içi stillerin sessizce engellenmesi** (23+3 nokta — tüm dinamik ilerleme çubukları/skor göstergeleri gerçekte render olmuyordu) olduğu ortaya çıktı. Üçü de bu oturumda düzeltildi (bkz. §0).

## 3. Ortama bağlı / taşınabilirlik sorunları

- `e2e/*.py` içinde `executable_path='/usr/bin/chromium'` sabit kodlanmış (`test_critical_navigation_browser.py:67`, `test_question_bank_browser.py:135`). Bu oturumda `/usr/bin/chromium → /opt/pw-browsers/chromium` symlink'i (repo dışı) ile çalıştırıldı. Başka makinede/CI'da bu yol yoksa testler başlamaz.
- Üretim imajı `python:3.12-slim` (`Dockerfile:1`); testler burada **3.13** ile koşuldu → 3.12 üzerinde `NOT_VERIFIED`.
- CI/CD yok: `.github/` dizini yok, başka pipeline dosyası bulunmadı. Testler yalnızca elle çalıştırılıyor.

## 4. Çalıştırılmayan / doğrulanamayan testler

| Test türü | Durum | Neden |
|---|---|---|
| PostgreSQL üzerinde migration/entegrasyon | `NOT_VERIFIED` | Bu ortamda PostgreSQL yok (SQLite ile koşuldu). `tests/test_6621_postgres_migration_hotfix.py` yalnızca statik içerik kontrolü yapıyor, canlı Postgres'e bağlanmıyor. |
| Yedekleme/geri yükleme (`Backup-Server.sh`, `Restore-Server.sh`) | `NOT_VERIFIED` | Docker/PostgreSQL yok |
| Performans/yük (`ops/load/k6-read-only.js`) | `NOT_VERIFIED` | k6 + çalışan sunucu yok |
| `tests/acceptance/validate_*.py` (5 betik) | `NOT_VERIFIED` | Çalışan sunucu gerektiriyor; çalıştırılmadı |
| Production canlı sunucu (`assess.dogus.edu.tr`) | `BLOCKED` | Yalnızca üniversite iç ağından erişilebilir (kullanıcı beyanı); bu oturumdan TCP seviyesinde 502 |
| Proliz OBS API (Swagger/403 durumu) | `BLOCKED` | Dış ağ/kimlik bilgisi yok; denenmedi |
| Gerçek Entra ID uçtan uca giriş | `NOT_VERIFIED` | Tenant/istemci bilgisi yok |
| Güvenlik tarayıcıları (SAST/DAST/dependency CVE) | `NOT_VERIFIED` | `Verify-Supply-Chain.sh` harici scanner gerektiriyor; çalıştırılmadı (güvenlik raporuna bkz.) |
| Erişilebilirlik (WCAG 2.2 AA) otomatik tarama | `NOT_VERIFIED` | axe/Lighthouse çalıştırılmadı |
| Uçtan uca iş zinciri (OBS → Core → Assess → … → kalite raporu) | `NOT_VERIFIED` | OBS ve DOU Core entegrasyonu yok/erişilemiyor (entegrasyon raporuna bkz.) |

## 5. Sunucudaki sürüm ile kaynağın aynılığı

`NOT_VERIFIED`. Production sunucusuna erişilemedi; production modunda `/api/health` ve `/api/ready` sürümü bilerek gizliyor (`app/main.py` `health()`/`ready()`), yalnızca admin yetkili `/api/system/diagnostics` gösteriyor. Ek olarak:
- `RELEASE.env` hâlâ `APP_VERSION=6.70-production-hardening` (6.70.3'e yükseltilmemiş) → 6.70.3 çalışsa bile sürüm olarak "6.70" raporlar.
- `SOURCE-MANIFEST.sha256` 6.70.3 UI dosyalarıyla uyuşmuyor → manifest sunucu karşılaştırması için güvenilir değil (6.70'e ait, 6.70.3 sonrası güncellenmemiş).
Doğrulama için kullanıcıdan sunucuda `curl -s localhost:8080/api/system/diagnostics` (admin) veya `docker exec … cat /app/RELEASE.env` + `sha256sum /app/app/static/*` çıktısı gerekir.

## 6. Düzeltilmesi gerekenler (test açısından)

1. `bs4` (ve varsa diğer test bağımlılıkları) `requirements-dev.lock`'a eklenmeli. — Yüksek
2. 4 UI sözleşme testi ve 2 E2E, 6.70.3 arayüzüne göre güncellenmeli veya admin için nav gruplarının davranışı yeniden değerlendirilmeli. — Yüksek
3. E2E'de Chromium yolu ortam değişkeni/Playwright varsayılanı ile çözülmeli. — Orta
4. CI pipeline (pytest + e2e + migration + lock doğrulama) kurulmalı. — Yüksek
5. `RELEASE.env`, manifest ve SBOM her sürümde otomatik üretilmeli; 6.70.3 için yeniden üretilmeli. — Orta
