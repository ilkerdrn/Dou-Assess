# DOU Assess 6.70.8 — Friction / Click-Count Closure

## Amaç
En sık kullanılan dört akışta gereksiz seçim ve tıklamayı azaltmak.

## Değişiklikler
- Soru Bankası: temel alanlar önde, gelişmiş metadata kapalı; `Kaydet + yeni soru` ile aynı derste seri giriş.
- Sınav: `Oluştur ve sorulara geç` ile yeni sınavdan doğrudan soru adımına geçiş.
- Değerlendirme: yalnız bir aktif `grading` sınavı varsa otomatik seçilir ve ilk öğrenci açılır.
- Kalite / PUKÖ: Başlık + Plan ile döngü başlatılabilir; Uygula/Kontrol/Önlem ilerledikçe doldurulur.
- Kalite kanıtı: `Yükle + PUKÖ başlat` ile kanıttan doğrudan iyileştirme akışına geçilir.
- Mobil düzen: yeni seri soru ve sınav aksiyonları tek sütuna düşer.

## Teknik kapsam
- Veritabanı migration yok.
- API contract değişikliği yok.
- Schema: `0042_performance_production_hardening`.
- Static cache key: `6708-friction-closure`.

## Doğrulama
- Hedef UX regression: 29/29 PASS.
- Full regression: 292/292 PASS.
- Python compile: PASS.
- JavaScript syntax: PASS.
