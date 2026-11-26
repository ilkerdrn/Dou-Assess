# DOU Assess 6.18.3 — Sınav Öğrenci Atama

Bu düzeltme sınav ile öğrenci arasındaki eşleştirmeyi görünür ve yönetilebilir hale getirir.

## Yeni akış

- Sınav sihirbazının 4. adımı **Öğrenciler & Çıktı** olarak güncellendi.
- **Öğrencileri seç / yönet** paneli eklendi.
- Ders kayıtlı öğrenciler checkbox ile tek tek sınava atanabilir.
- Tümünü seç / seçimi temizle / arama işlevleri eklendi.
- Seçilen liste sınav bazında kalıcı olarak kaydedilir.
- Ders kaydı ile sınav ataması birbirinden ayrıldı: bir öğrenci derse kayıtlı olup belirli bir sınava dahil edilmeyebilir.
- Puanlama başladıktan sonra öğrenci atama listesi kilitlenir.
- Mevcut **Tümünü ata** hızlı aksiyonu korunmuştur.
- Öğrenciye özel PDF, optik ve puanlama listesi yalnız sınava atanmış öğrencileri kullanır.

## API

- `GET /api/exams/{exam_id}/student-assignment`
- `PUT /api/exams/{exam_id}/students`

`PUT` gövdesi:

```json
{"student_ids":[1,2,3]}
```

Bu istek sınav öğrenci listesini verilen öğrenci listesiyle eşitler. Öğrencilerin ilgili derse kayıtlı olması gerekir.

## Doğrulama

- Otomatik test: **44/44 PASS**
- Complete Engine acceptance: **PASS**
- Lifecycle acceptance: **PASS**
