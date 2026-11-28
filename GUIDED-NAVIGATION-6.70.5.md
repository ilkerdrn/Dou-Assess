# DOU Assess 6.70.5 — Guided Navigation

Bu sürüm kullanım kolaylığı kapanışıdır. Veritabanı şeması değişmez (`0042_performance_production_hardening`).

## Kapanan alanlar
- Ctrl+K Komut Merkezi gerçek ders, program, sınav ve öğrenci araması yapar.
- Öğrenci araması server-side `/api/students?q=` üzerinden çalışır.
- Komut sonucundan ders çalışma alanı, sınav detayı ve öğrenci karnesi doğrudan açılır.
- Bildirim Merkezi `source_entity_type/source_entity_id/program_id` bağlamını taşır.
- PUKÖ bildirimi Kalite360 > PUKÖ'ye; kalite takvimi ilgili takvim sekmesine; akreditasyon talepleri ziyaret/hazırlık alanına; ölçme güvence bildirimi ilgili program planına gider.
- Soru Bankası, Sınavlar, Değerlendirme ve Derslerim boş durumlarında kullanıcıya net sonraki adım CTA'sı gösterilir.
- Asset cache anahtarı `6705-guided-navigation` ile kırılır.

## Doğrulama
- Full regression: 274/274 PASS
- JS syntax: PASS
- DB migration: yok
