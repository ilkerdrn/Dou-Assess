# DOU Assess 6.70.3 — Simple Panel

Amaç: Özellikleri silmeden rol bazlı progressive disclosure ile paneli sadeleştirmek.

## Öğretim elemanı
- Ana Sayfa
- Derslerim
- Soru Bankası
- Sınavlar
- Değerlendirme
- Sınav Sonuçları
- Ders Sonuçları

Kalite, akreditasyon, kullanıcı, sistem, entegrasyon ve akademik yönetim araçları görünmez.

## Kalite rolü
Kalite çalışma alanı varsayılan açık; günlük sınav hazırlama menüleri gizlidir.

## Yönetim
Gelişmiş yönetim araçları erişilebilir ancak varsayılan kapalıdır.

## Ana sayfa
Öğretim elemanı için 4 adımlı akış:
1. Derslerim
2. Soru Bankası
3. Sınavlar
4. Değerlendirme

Sistem sağlık kartı öğretim elemanı görünümünde gizlenir; yönetim ayrıntıları kullanıcıya gösterilmez.

## Teknik
- Backend / DB değişikliği yok.
- Schema: 0042_performance_production_hardening.
- 6.70.1 Question Bank drawer fix korunur.
- 6.70.2 modal/UX closure korunur.
- Focused regression: 17/17 PASS.
