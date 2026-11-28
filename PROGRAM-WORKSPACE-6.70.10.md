# DOU Assess 6.70.10 — Program Head Workspace

## Amaç
Program Başkanı, bölüm/fakülte yöneticisi ve kalite rollerinin programı ayrı menülerde dolaşmadan tek ekrandan yönetebilmesi.

## Yeni Program Workspace
- Program bazlı 4 karar göstergesi: ölçüm kapsamı, Program Çıktısı ortalaması, riskli ders, açık PUKÖ.
- Dinamik “Şimdi ne yapmalıyım?” önerisi.
- Hızlı işlemler: Çıktılar, Ders Performansı, Program Review, Kanıtlar, PUKÖ & Kalite, Akreditasyon.
- Son Program Review durumu aynı ekranda.
- Seçilen program bağlamı diğer çalışma alanlarına taşınır; tekrar program seçmek gerekmez.
- Ayrıntılı analiz isteğe bağlı details alanında kalır.

## Teknik sınırlar
- Backend API değişikliği yok.
- DB migration yok.
- Schema: 0042_performance_production_hardening.
- Mevcut Program Review / Evidence Hub / Quality / Accreditation endpointleri yeniden kullanılır.

## Doğrulama
- Hedef kontrat: 17/17 PASS.
- Full regression: 302/302 PASS.
