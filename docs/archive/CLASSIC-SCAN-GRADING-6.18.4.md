# DOU Assess 6.18.4 — Taranmış Klasik Cevap Puanlama

## Amaç

6.18.4 ile klasik/açık uçlu soruların taranmış cevapları doğrudan **Puanlama** ekranında rubrikle yan yana gösterilir. Öğretim elemanı ayrı PDF açmadan öğrencinin cevabını görür, rubrik puanlarını girer ve **Kaydet ve sonraki** ile bir sonraki öğrenciye geçer.

## Yeni akış

1. Öğrenciye özel sınav kağıdı üretilir.
2. OMR/kapak sayfası ve klasik soru sayfaları ADF ile taranır.
3. Yeni üretilen soru sayfalarındaki sayfa QR'ı; sınav, kitapçık, öğrenci ve mantıksal sayfa bilgisini taşır.
4. Tarama sistemi klasik soru sayfasını doğru öğrenciye otomatik bağlar.
5. Puanlama ekranı klasik soruda taranmış cevap alanını gösterir.
6. Rubrik kriterleri ayrı ayrı puanlanır; toplam puan canlı hesaplanır.
7. Puan kaydedilir ve toplam sınav notuna dahil edilir.

## Puanlama ekranı

Klasik sorularda üç görüntü modu vardır:

- **Cevap alanı:** yalnız öğrencinin yazdığı cevap bölgesi.
- **Soru + cevap:** soru metni ve cevap alanı birlikte.
- **Tam sayfa:** taranan fiziksel sayfanın tamamı.

Rubrikli sorularda her kriterin üst sınırı backend tarafından doğrulanır. Rubrik toplamı soru puanını aşamaz. Rubriksiz klasik soruda doğrudan puan girilebilir.

## ADF / sayfa sırası

Yeni kağıtlarda her soru sayfasında bağımsız QR bulunduğu için ADF sayfalarının sırasının karışması klasik sayfanın öğrenciyle eşleşmesini bozmaz.

## Eski `dou-official-v2` kağıtları

6.18.4 geriye dönük uyumludur. Eski kağıtlarda yalnız OMR/kapak QR taşıdığı için takip eden soru sayfaları önceki güvenli öğrenci QR kimliğine göre sıralı olarak bağlanır. Bu kayıtlar arayüzde **legacy association** olarak işaretlenir. Eski sayfa düzeni için ayrı crop geometrisi kullanılır.

> Eski paketlerde sayfa sırası fiziksel olarak korunmalıdır. Yeni sayfa-QR'lı paketlerde bu kısıt yoktur.

## Büyük tarama PDF'leri

PDF tarama motoru artık 90–120 sayfalık ADF dosyalarını tek seferde RAM'e açmak yerine **sayfa sayfa** rasterize eder. Üretim varsayılanı `MAX_PDF_PAGES=120` ve `MAX_IMAGE_MEGAPIXELS=40` olarak sınırlandırılmıştır.

## Depolama

Klasik soru sayfalarının JPEG önizlemeleri `SCAN_STORAGE_PATH` altında saklanır. Production compose bu alanı `scan_data` kalıcı Docker volume'una bağlar. Backup/restore akışı `data/scans` içeriğini de kapsar.

## Veritabanı

Alembic head:

`0016_classic_scan_grading`

Yeni alanlar:

- `scan_sessions.support_count`
- `scan_items.page_kind`
- `scan_items.logical_page_no`
- `scan_items.question_numbers`

## API

- `GET /api/exams/{exam_id}/students/{student_id}/classic-scans`
- `GET /api/scan-items/{item_id}/classic-crop/{question_id}?mode=answer`
- `GET /api/scan-items/{item_id}/classic-crop/{question_id}?mode=question`
- `GET /api/scan-items/{item_id}/preview`

Bu endpointler mevcut sınav erişim/yetki kontrolünü kullanır.
