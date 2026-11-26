# DOU Assess – Tamamlanma Planı (12 Faz)

Kaynak: `GAP_ANALYSIS.md`. Her faz: işler, etkilenen modüller, dosyalar, bağımlılıklar, riskler, kabul kriterleri, testler, tamamlanma koşulu.

## FAZ 1 — Kritik altyapı ve kaynak kodu güvenliği
- **İşler:** `ilkerdrn/Dou-Assess`'i kalıcı gerçek kaynak yap (bu oturumda yapıldı); CI/CD pipeline kur (lint+pytest+e2e); `bs4` dahil tüm test bağımlılıklarını lock dosyasına ekle.
- **Etkilenen:** Tüm proje.
- **Dosyalar:** `.github/workflows/*`, `requirements-dev.lock`.
- **Bağımlılıklar:** Yok.
- **Riskler:** CI olmadan her sürüm elle test edilir, 6.70.3 gibi regresyonlar tekrarlar.
- **Kabul:** CI her PR'da 263 testi otomatik koşturur.
- **Test:** `pytest tests/ e2e/`.
- **Tamamlanma:** CI yeşil + branch protection.

## FAZ 2 — Veritabanı ve akademik veri mimarisi
- **İşler:** PostgreSQL'de CI test ortamı kur; CASCADE/silme stratejisini gözden geçir (kritik tablolarda RESTRICT/soft-delete); yedekleme script'ini şifrele ve `.env`/`secrets`'i çıkar; off-site yedek hedefi ekle; KVKK saklama/silme otomasyonu.
- **Etkilenen:** `app/models.py`, `migrations/`, `Backup-Server.sh`, `Restore-Server.sh`.
- **Bağımlılıklar:** Faz 1 (CI).
- **Riskler:** Yanlış CASCADE değişikliği veri kaybına yol açabilir — önce staging'de test.
- **Kabul:** Postgres CI PASS; yedek dosyası şifreli; restore tatbikatı belgeli.
- **Test:** `alembic upgrade head` (Postgres), gerçek backup→restore denemesi.
- **Tamamlanma:** Belgelenmiş, başarılı restore tatbikatı.

## FAZ 3 — Kimlik, rol ve yetkilendirme
- **İşler:** Öğrenci, denetçi, rektörlük, ölçme-değerlendirme birimi rollerini ekle; S-01 (pilot açık erişim) için ağ izolasyonu zorunlu kıl; S-06 (production'da `/docs` açık) kapat; S-08 (`mudek-ek1` yetki boşluğu) düzelt.
- **Etkilenen:** `app/authz.py`, `app/security.py`, `app/quality360_api.py`.
- **Bağımlılıklar:** Yok.
- **Riskler:** Yeni rol eklerken mevcut kapsam mantığını kırma riski.
- **Kabul:** 9 rolün tümü tanımlı ve kapsam testli; security audit S-01/S-06/S-08 kapatıldı.
- **Test:** Rol bazlı erişim testleri (pytest), production simülasyon testleri.
- **Tamamlanma:** Güvenlik denetiminde ilgili bulgular "fixed" statüsünde.

## FAZ 4 — OBS ve DOU Core entegrasyonları
- **İşler:** Proliz OBS swagger/kimlik bilgilerini temin et (kullanıcı aksiyonu); read-only OBS connector tasarla ve geliştir (dönem/fakülte/bölüm/ders/öğrenci/akademisyen/müfredat/kayıt); kabul kapısını sağlayıcı bazlı sıkılaştır (Excel "ready" saymasın); DOU Core için API sözleşmesi iste ve entegre et.
- **Etkilenen:** `app/services/imports.py`, `app/main.py` (OBS routes), `app/production_acceptance_api.py`.
- **Bağımlılıklar:** **BLOCKED** — Bilgi İşlem'den Proliz API erişimi/kimlik bilgisi ve DOU Core sözleşmesi gerekli.
- **Riskler:** Kurum dışı bağımlılık; bu faz kullanıcı/kurum aksiyonu olmadan ilerleyemez.
- **Kabul:** Gerçek Proliz'den en az bir dönem/program/ders/öğrenci kaydı otomatik çekilip doğrulanır.
- **Test:** `test_664_integration_acceptance_guard.py` genişletilmiş hali + canlı Proliz smoke test.
- **Tamamlanma:** Kabul kapısı gerçek Proliz senkronuyla "ready".

## FAZ 5 — Soru bankası ve sınav yönetimi
- **İşler:** Soru versiyon geçmişi (eski içerik saklama) ekle; soru bankası export; review'da maker-checker; sınav takvimi + salon/gözetmen planlama modülü.
- **Etkilenen:** `app/main.py` (question/exam routes), `app/models.py`.
- **Bağımlılıklar:** Faz 2 (yeni tablolar).
- **Riskler:** Versiyonlama şeması mevcut sorularla geriye dönük uyumlu olmalı.
- **Kabul:** Her soru düzenlemesi geçmişte saklanır ve geri alınabilir; takvim çakışma kontrolü yapar.
- **Test:** Yeni pytest senaryoları (versiyon geri alma, takvim çakışması).
- **Tamamlanma:** Modül denetiminde §C/§D "VERIFIED_COMPLETE".

## FAZ 6 — Ölçme ve değerlendirme motoru
- **İşler:** Bloom düzeyi dağılım raporu; SEM (standart ölçüm hatası); dönemler/yıllar arası karşılaştırma raporu; not revizyon audit tablosu (S-03).
- **Etkilenen:** `app/services/analytics.py`, `app/models.py`.
- **Bağımlılıklar:** Yok.
- **Riskler:** Mevcut doğru çalışan formüllere (Cronbach/KR-20/Pearson) dokunmadan ekleme yapılmalı.
- **Kabul:** Bloom/SEM/dönemsel raporlar gerçek veriyle üretilir; not değişikliği eski/yeni değerle loglanır.
- **Test:** `analytics.py` için ek birim testler.
- **Tamamlanma:** Security S-03 "fixed"; yeni raporlar canlı veriyle doğrulanır.

## FAZ 7 — Program çıktıları ve akademik kalite
- **İşler:** YÖKAK/PUKÖ uçtan uca UI akışının gerçek bir program ile denenmesi; denetçi rolü (gerçek yetkili, token'lı erişim — public link değil).
- **Etkilenen:** `app/compliance_api.py`, `app/quality360_api.py`.
- **Bağımlılıklar:** Faz 3 (denetçi rolü).
- **Riskler:** Denetçi erişimi aşırı kısıtlanırsa gerçek denetim süreçlerini engeller.
- **Kabul:** Gerçek bir program için PUKÖ döngüsü baştan sona UI'da tamamlanır.
- **Test:** Senaryo bazlı manuel UAT + yeni pytest.
- **Tamamlanma:** Modül denetiminde §F "VERIFIED_COMPLETE".

## FAZ 8 — Akreditasyon ve kanıt yönetimi
- **İşler:** Evidence Hub'ın gerçek akreditasyon dosyalarıyla (MÜDEK/MEDEK) pilot kullanımı; kanıt bütünlüğü (SHA-256) sürecinin kurumsal onayı.
- **Etkilenen:** `app/services/compliance.py`, `data/evidence/`.
- **Bağımlılıklar:** Faz 7.
- **Riskler:** Gerçek akreditasyon dosyaları hassas olabilir — erişim kontrolü kritik.
- **Kabul:** En az bir gerçek program dosyası sistemde uçtan uca işlenir.
- **Test:** Manuel UAT + kanıt bütünlük testi.
- **Tamamlanma:** Kalite birimi onayı.

## FAZ 9 — Dashboard, raporlama ve UX/UI
- **İşler:** Fakülte/bölüm/rektörlük dashboard'u; ders/program PDF raporu; 6.70.3 ile kırılan 4 UI testi + 2 E2E'yi düzelt (nav etiketlerini güncelle veya testleri yeni yapıya göre yeniden yaz); WCAG 2.2 AA otomatik tarama (axe/Lighthouse) ekle.
- **Etkilenen:** `app/static/*`, `app/services/exports.py`.
- **Bağımlılıklar:** Yok.
- **Riskler:** Yok.
- **Kabul:** 263/263 test PASS; axe taramasında kritik ihlal yok.
- **Test:** `pytest tests/ e2e/` (tam yeşil), axe-core taraması.
- **Tamamlanma:** Test raporunda 0 FAIL.

## FAZ 10 — Güvenlik, performans ve erişilebilirlik
- **İşler:** S-02 (yedek şifreleme), S-04 (nginx XFF), S-05 (audit hash zinciri), S-07 (tutarlı `esc()`), S-09 (KVKK retention otomasyonu), S-10 (anket anahtarı) kapatılır; `Verify-Supply-Chain.sh` için harici CVE scanner entegre edilir; yük testi (`ops/load/k6-read-only.js`) gerçek sunucuya karşı koşulur.
- **Etkilenen:** Güvenlik denetiminde listelenen tüm dosyalar.
- **Bağımlılıklar:** Faz 1 (CI).
- **Riskler:** Yok.
- **Kabul:** Security audit'teki Kritik/Yüksek bulguların tümü "fixed".
- **Test:** Güvenlik denetiminin dinamik testleri tekrar koşulur.
- **Tamamlanma:** 0 Kritik/Yüksek açık bulgu.

## FAZ 11 — Uçtan uca testler ve kullanıcı kabulü
- **İşler:** OBS → DOU Core → DOU Assess → Ders → ÖÇ → Soru bankası → Sınav → Değerlendirme → Başarı analizi → PÇ → Kalite raporu zincirini gerçek (veya staging) OBS/Core bağlantısıyla uçtan uca test et; gerçek akademisyen/öğrenci/kalite birimi ile UAT.
- **Etkilenen:** Tüm sistem.
- **Bağımlılıklar:** Faz 4 (OBS/Core) — bu faz olmadan uçtan uca zincir tamamlanamaz.
- **Riskler:** Faz 4 tamamlanmazsa bu faz de BLOCKED kalır.
- **Kabul:** Zincirin her halkası gerçek veriyle doğrulanır, UAT imzalanır.
- **Test:** `UAT-1-9` benzeri senaryo seti + yeni OBS/Core senaryoları.
- **Tamamlanma:** İmzalı UAT raporu.

## FAZ 12 — Production hazırlığı ve FINAL-STABLE
- **İşler:** Production sunucusunun (`assess.dogus.edu.tr`) gerçek sürümünü doğrula (bu oturumda `BLOCKED` kaldı — kullanıcı sunucudan `/api/system/diagnostics` çıktısı veya `cat RELEASE.env` + `sha256sum app/static/*` paylaşmalı); `Production-GoLive.sh`/`Server-Ready-Check` tüm kapıları (Faz 1-11 kapandıktan sonra) geçsin; final go-live onayı.
- **Etkilenen:** Tüm sistem + production sunucu.
- **Bağımlılıklar:** Faz 1-11'in tamamı.
- **Riskler:** Sunucu durumu doğrulanmadan "production ready" ilan edilmemeli.
- **Kabul:** `ACCEPTANCE_CRITERIA.md`'deki tüm kriterler karşılanır; `production_acceptance_api.py` kapılarının tümü sahte-pozitif olmadan "ready".
- **Test:** Tüm test suite'leri + sunucu üzerinde canlı doğrulama.
- **Tamamlanma:** FINAL-STABLE etiketi + imzalı kabul raporu.
