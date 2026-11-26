# DOU Assess 6.27 — University Quality OS

## Amaç
DOU Assess'i MYO odaklı bir ölçme uygulamasından üniversite geneli kalite işletim sistemine taşır.

## Yeni kalite hiyerarşisi
Üniversite → Fakülte/MYO → Bölüm → Program → Ders → Sınav.

## Akıllı çerçeve eşleştirme
- MEDEK: önlisans/MYO programları için öneri.
- MÜDEK: mühendislik programları için öneri.
- TURAK: turizm/otelcilik/ilgili programlar için öneri.
- YÖKAK, ESG ve ACQUIN: kurum geneli kalite üst katmanları.
- Kalite yöneticisi otomatik öneriyi manuel olarak doğrulayabilir/değiştirebilir.
- Otomatik eşleştirme bir karar desteğidir; resmî kapsam ve sürüm kurum kalite birimince onaylanır.

## Yönetim deneyimi
- Üniversite kalite nabzı: akademik birim, program, resmî sınav, açık PUKÖ ve kanıt KPI'ları.
- Program bazlı akıllı kalite profil kartı.
- Alan akreditasyonu ile kurumsal kalite çerçeveleri birbirinden ayrıldı.

## Veri tabanı
Yeni migration: `0021_quality_framework_routing`.
Mevcut sınav, öğrenci, soru, kanıt ve kalite verileri korunur.
