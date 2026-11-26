# DOU Assess — Pilot UAT Yol Haritası

## Kabul sırası
1. **Kimlik ve rol:** Pilot admin, öğretim elemanı, program başkanı ve kalite rolü ile ayrı ayrı giriş yapın. Görünmemesi gereken menünün görünmediğini doğrulayın.
2. **Ders çalışma alanı:** Derslerim > BLP1014 Python Programlama. Genel Bakış, Öğrenim Çıktıları, Soru Bankası, Sınavlar, Değerlendirme, Analiz ve İyileştirme sekmelerini gezin.
3. **Soru bankası:** Test, klasik ve rubrikli üç soru ekleyin; Öğrenim Çıktısı bağlantılarını kontrol edin.
4. **Sınav:** 10 test + 2 klasik soruluk karma sınav oluşturun. Toplam puanın 100 olduğunu doğrulayın.
5. **Optik:** Test bölümünü tarama/fixture ile okutun; belirsiz işaret inceleme kuyruğunu test edin.
6. **Klasik:** Soru Bazlı Seri Puanlama, Kör Değerlendirme, hızlı rubrik ve Ctrl/⌘+Enter akışını deneyin.
7. **Analiz:** Sınav > Ders > Program seviyesinde Öğrenim/Program Çıktısı başarılarını kontrol edin.
8. **Kalite:** Hedef altı bir çıktıyı PUKÖ'ye dönüştürün, kanıt ekleyin ve kapanış kontrolünü test edin.
9. **Akreditasyon:** Ziyaret görünümü, kanıt readiness ve öz değerlendirme taslağını açın.
10. **Geri bildirim:** Her test kullanıcısı en az bir kullanılabilirlik notu bıraksın.

## Kabul kriteri
- Kritik akışta 5xx hata: **0**
- Veri kaybı: **0**
- Yetkisiz ekran/veri görünümü: **0**
- Normal sayfa etkileşimleri: kullanıcı tarafından belirgin bekleme hissi oluşturmamalı
- 10 ana senaryonun en az 9'u ilk denemede tamamlanmalı
- Kritik/seviye-1 UX problemi kalmamalı

## Test grubu
- 2 öğretim elemanı
- 1 program başkanı
- 1 kalite kullanıcısı
- 1 sistem yöneticisi

İlk tur 5 kişiyle yapılır; hatalar kapatıldıktan sonra 10–20 öğretim elemanına genişletilir.
