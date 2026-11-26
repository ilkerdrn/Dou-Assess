# Premium Klasik Değerlendirme · 6.37.5

Bu revizyon yalnız klasik değerlendirme iş akışını hızlandırır; veritabanı şemasını ve Entra/OBS entegrasyon sözleşmesini değiştirmez.

## Modlar
- Öğrenci bazlı: bir öğrencinin tüm sınav cevapları aynı çalışma alanında değerlendirilir.
- Soru bazlı seri: seçilen klasik soru tüm öğrencilerde ardışık puanlanır.
- Kör değerlendirme: arayüzde ad/numara yerine Aday 001, Aday 002 biçiminde kod gösterilir.

## Hızlı rubrik
Her rubrik ölçütünde 0%, 25%, 50%, 75%, 100% puan presetleri bulunur. Toplam sistem tarafından otomatik hesaplanır ve soru üst sınırı mevcut backend doğrulamasıyla korunur.

## Klavye
- 1–5: aktif rubrik ölçütünde hızlı puan
- Tab: sonraki ölçüt
- Ctrl/Cmd + Enter: kaydet ve sonraki öğrenci
- Alt + Sol/Sağ: önceki/sonraki öğrenci

## Güvenlik notu
Kör değerlendirme, değerlendirici arayüzünde kimliği maskeler. Yetkili kullanıcıların sistem yöneticisi seviyesindeki veri erişim yetkilerini ortadan kaldıran kriptografik anonimleştirme değildir.
