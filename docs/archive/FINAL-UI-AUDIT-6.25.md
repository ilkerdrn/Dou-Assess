# DOU Assess 6.25 — Academic Intelligence Final Audit

## UX kararları
- Öğretim elemanı varsayılan olarak `Derslerim` ekranına girer.
- Ana akademik CRUD normal öğretim elemanından gizlenir.
- Ders seçildikten sonra yalnız Sınavlar / Soru Bankası / Öğrenciler / Ders Analizi sunulur.
- Ders öğrenci listesi salt-okunur mikro ekrandır.
- Analiz hiyerarşisi: Sınav → Ders → Program.

## Teknik kapsam
- Yeni migration yok; `0020_assessment_intelligence` korunur.
- Course analytics aynı program + ders kodunu dönemler arasında izler.
- Program analytics mevcut resmî kalite snapshot motorunu kullanır.
- Soru, OMR, klasik, lifecycle, akreditasyon ve Quality360 motorları korunur.
