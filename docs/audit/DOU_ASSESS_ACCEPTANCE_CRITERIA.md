# DOU Assess – FINAL-STABLE Kabul Kriterleri

Bu kriterler karşılanmadan proje "PRODUCTION READY" ilan edilemez.

## Kaynak kod ve süreç
- [ ] `ilkerdrn/Dou-Assess` tek, güncel, çalışan kaynak kod deposudur (main branch korumalı).
- [ ] CI/CD pipeline her PR'da `pytest tests/ e2e/`'yi otomatik koşturur ve PASS zorunludur.
- [ ] Tüm bağımlılıklar (`requirements.lock`, `requirements-dev.lock`) tam ve eksiksizdir (bkz. `bs4` eksikliği düzeltilmiştir).

## Test
- [ ] 263 backend testin tamamı PASS (şu an 259/263).
- [ ] 2 E2E testin tamamı PASS (şu an 0/2).
- [ ] PostgreSQL üzerinde migration (0001→0042) ve test suite en az bir kez CI'da PASS.
- [ ] Gerçek backup→restore tatbikatı belgeli ve başarılı.
- [ ] Yük testi (`ops/load/k6-read-only.js`) gerçek/staging sunucuya karşı koşulmuş ve kabul edilebilir yanıt süreleri belgeli.

## Güvenlik
- [ ] Security audit'teki 1 Kritik + 2 Yüksek bulgu (S-01, S-02, S-03) kapatılmıştır.
- [ ] Production'da `/docs`, `/openapi.json` kimliksiz erişime kapalıdır (S-06).
- [ ] Not/puan değişiklikleri eski-yeni değerle audit edilir (S-03).
- [ ] Yedekler şifrelidir, `.env`/`secrets` yedek arşivinde açık değildir (S-02).
- [ ] Gerçek Entra tenant ile en az bir uçtan uca kimlik doğrulama testi yapılmıştır.

## Entegrasyon
- [ ] Proliz OBS'den en az read-only bir entegrasyon (dönem/program/ders/öğrenci) canlı doğrulanmıştır — **kurum aksiyonu gerektirir**.
- [ ] Production acceptance kapısı (`proliz_obs_readonly`) sağlayıcı bazlı kontrol eder; Excel yüklemesiyle "ready" olamaz.
- [ ] DOU Core ile ortak kimlik/akademik organizasyon sözleşmesi netleşmiş ve (varsa) entegre edilmiştir.

## Modüller
- [ ] Soru bankası: versiyon geçmişi ve export mevcuttur.
- [ ] Sınav yönetimi: takvim/salon/gözetmen planlaması mevcuttur.
- [ ] Ölçme-değerlendirme: Bloom dağılımı ve dönemsel karşılaştırma raporları mevcuttur.
- [ ] Kullanıcı/yetki: öğrenci, denetçi, rektörlük rolleri tanımlı ve test edilmiştir.
- [ ] Kalite/akreditasyon: en az bir gerçek program için PUKÖ döngüsü uçtan uca tamamlanmıştır.

## Production doğrulama
- [ ] `assess.dogus.edu.tr` sunucusunun çalıştırdığı sürüm, kaynak koddaki sürümle (manifest/SHA-256 veya `/api/system/diagnostics`) eşleştiği belgelenmiştir.
- [ ] `Production-GoLive.sh` / `Server-Ready-Check` script'lerindeki tüm kapılar gerçek (sahte-pozitif olmayan) verilerle "ready" durumundadır.

## Nihai onay
- [ ] Kalite birimi, Bilgi İşlem ve en az bir pilot akademik birim tarafından imzalı UAT raporu mevcuttur.
- [ ] Bu denetim serisindeki (`DOU_ASSESS_*`) 9 rapor güncellenmiş ve tüm "Kritik"/"Yüksek" öncelikli bulgular "fixed"/"VERIFIED_COMPLETE" statüsündedir.

**Bu kriterlerin hiçbiri bu denetim oturumunda "tamamlandı" olarak işaretlenmemiştir — tümü gelecekteki geliştirme fazlarının çıkış koşuludur.**
