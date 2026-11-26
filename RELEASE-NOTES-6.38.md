# DOU Assess 6.38 — Role-Based Workspace UX

## Amaç
6.37.5 fonksiyonel çekirdeğini bozmadan günlük kullanıcı deneyimini role göre sadeleştirmek.

## Değişiklikler
- Sol menüdeki kalıcı **Akademik Akış** kaldırıldı.
- Öğretim elemanı navigasyonu: Ana Sayfa, Derslerim, Sınavlarım, Soru Bankası, Değerlendirme, Analiz.
- Kalite ve yönetim modülleri yalnız yetkili rollerde görünür.
- Program/Ders/Öğrenci ana veri ekranları **Yönetim** grubuna taşındı.
- Ders seçildikten sonra bağlamsal çalışma sekmeleri eklendi: Genel Bakış, Öğrenim Çıktıları, Soru Bankası, Sınavlar, Değerlendirme, Analiz, İyileştirme.
- Öğretim elemanı giriş sonrası aksiyon odaklı Ana Sayfa'ya yönlendirilir.
- Login akışı Program→Ders→Sınav→Öğrenci yerine Ders→Ölçme→Değerlendirme→İyileştirme olarak güncellendi.
- Kart, navigasyon, tipografi ve responsive çalışma alanı yeniden dengelendi.
- Eski workflow DOM bağımlılıkları JavaScript'ten kaldırıldı.
- Asset cache anahtarları 6.38'e güncellendi.

## Teknik kontrat
- API sürümü bilinçli olarak değişmedi: `6.37-final-preintegration-server-ready`
- Schema değişmedi: `0023_strategic_quality`
- OBS ve Entra entegrasyonu için veri modeli dondurulmuştur.
