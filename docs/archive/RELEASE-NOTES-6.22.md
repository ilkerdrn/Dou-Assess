# DOU Assess 6.22 · Final Workflow

6.22, 6.20 Quality360 veri modeli ve `0019_quality360` şemasını koruyan final kullanıcı-akışı sürümüdür.

## Final kullanıcı akışı
- Öğretim elemanı için mikro sıra: **Program → Ders → Sınav → Öğrenci**.
- Ön koşul hazır değilse sonraki adım kilitli ve açıklamalıdır.
- Yönetim yetkisi olmayan öğretim elemanı ana veri oluşturmaya zorlanmaz; yalnız yetkili program/ders kapsamından ilerler.
- Sınıf alanı serbest metin yerine 1–4. sınıf kataloğudur.

## Kurumsal soru bankası
- Sorular artık tek bir yıllık `course_id` kaydına mahkûm değildir.
- Aynı program + aynı ders kodundaki geçmiş dönem soruları yeni akademik yılda yetkili öğretim elemanına görünür.
- Geçmiş soru yeni sınava doğrudan snapshot olarak eklenebilir.
- Kaynak akademik yıl/dönem, yazar, sürüm, kullanım sayısı ve son kullanım bilgisi korunur.
- Geçmiş dönem sorusu yeni öğretim elemanı tarafından yanlışlıkla düzenlenmez/arşivlenmez; güncel dönem soruları normal yönetilir.

## Korunan çekirdek
- PostgreSQL ve persistent Docker volume kimlikleri korunur.
- Şema head: `0019_quality360`.
- Sınav, optik, klasik puanlama, analiz, kanıt, Quality360 ve Excel akışları korunur.
