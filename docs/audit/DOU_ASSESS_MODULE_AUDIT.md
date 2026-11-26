# DOU Assess – Modül İşlevsel Denetimi

**Kaynak:** `e98e723` (6.70.3). Yöntem: statik kod okuma (app/*.py, app/services/*.py, app/static) + gerçek pytest sonuçları (bkz. `DOU_ASSESS_TEST_REPORT.md`). Canlı sunucu/gerçek kullanıcı testi yapılmadı. "[D]" = ben ayrıca doğruladım.

## A. Kullanıcı ve yetki yönetimi — PARTIALLY_COMPLETE

[D] `app/authz.py:16-23` — tanımlı 6 rol: `admin`, `quality`, `instructor`, `program_head`, `department_head`, `faculty_admin`.

| Görevde istenen rol | Durum | Kanıt |
|---|---|---|
| Sistem yöneticisi | VERIFIED_COMPLETE | `admin` rolü, tüm endpoint'lere erişim |
| Rektörlük/üst yönetim | NOT_IMPLEMENTED | Ayrı rol yok; en yakını `faculty_admin` |
| Dekanlık | PARTIALLY_COMPLETE | `faculty_admin` karşılığı var ama dekanlığa özel dashboard yok |
| Bölüm başkanlığı | VERIFIED_COMPLETE | `department_head` |
| Akademisyen/öğretim elemanı | VERIFIED_COMPLETE | `instructor` |
| Ölçme-değerlendirme birimi | NOT_IMPLEMENTED | Ayrı rol yok |
| Kalite/akreditasyon birimi | VERIFIED_COMPLETE | `quality` |
| Öğrenci | NOT_IMPLEMENTED | Öğrenci kendi hesabıyla giriş yapamıyor; öğrenciler yalnızca veri olarak var |
| Misafir/denetçi | PARTIALLY_COMPLETE | Auth'suz "public snapshot" var (`compliance_api.py:633`), rol bazlı denetçi girişi yok |

Program/ders kapsamı SQL ile süzülüyor (`authz.py:217-263`). Entra JWT doğrulaması mevcut.

## B. Akademik organizasyon — PARTIALLY_COMPLETE

Modeller ve `academic_structure_api.py` (19 route [D]) mevcut. Veri girişi **tek yoldan**: Excel içe aktarma (`main.py:3896-4104`) veya elle. OBS'den otomatik çekme yok (bkz. entegrasyon raporu). Ders-program ilişkisi, müfredat, kayıt modelleri var.

## C. Soru bankası — PARTIALLY_COMPLETE

| Özellik | Durum | Kanıt |
|---|---|---|
| Oluşturma/CRUD | VERIFIED_COMPLETE | `main.py` question routes |
| Kategori/tür (çoktan seçmeli, açık uçlu vb.) | VERIFIED_COMPLETE | `models.py` Question.type |
| Çoklu ÖÇ eşleme | VERIFIED_COMPLETE | question↔outcome çoklu eşleme |
| Zorluk seviyesi | PARTIALLY_COMPLETE | Elle girilen alan; otomatik güçlük analizden ayrı |
| Bloom taksonomisi | NOT_VERIFIED | Ayrı Bloom dağılım raporu bulunamadı |
| Versiyonlama | **BROKEN/eksik** | `main.py:2623` sadece `version_no += 1`; **önceki içerik saklanmıyor**, gerçek versiyon geçmişi yok |
| Onay süreci | PARTIALLY_COMPLETE | Yaşam döngüsü draft→review→approved→institutional→retired var; review'da maker-checker **yok** (`main.py:2644`), sınav onayında **var** (`main.py:2153`) |
| Filtreleme | VERIFIED_COMPLETE | Soru havuzu filtreleri |
| Import | VERIFIED_COMPLETE | Excel import + doğrulama + yinelenen kayıt tespiti |
| Export | **NOT_IMPLEMENTED** | Yalnız şablon indirme var, havuz export'u yok |
| Soru geçmişi | NOT_IMPLEMENTED | Versiyonlama eksikliğiyle bağlantılı |

## D. Sınav yönetimi — PARTIALLY_COMPLETE (en güçlü modüllerden)

Durum makinesi, A-D kitapçık PDF üretimi, QR/OMR (OpenCV tabanlı), klasik tarama, cevap anahtarı revizyonu, not kilidi, itiraz, olay kaydı ve moderasyon **çalışıyor**. Eksik: sınav takvimi (salon/gözetmen planlaması) — mevcut takvim modeli yalnızca kalite takvimi, sınav takvimi değil.

## E. Ölçme ve değerlendirme — formüller VERIFIED_COMPLETE

[D] `app/services/analytics.py` içinde gerçek, doğrulanmış hesaplar var (demo/sahte değil):
- **Güçlük indeksi** (satır ~219-226): ortalama başarı yüzdesine göre Kolay/Orta/Zor.
- **Ayırt edicilik** (satır 229): madde-kalan toplam **Pearson korelasyonu** (`_pearson`, satır 41). Not: klasik üst-alt %27 grup yöntemi **kullanılmıyor** — alternatif ama geçerli bir yöntem.
- **Güvenirlik** (satır 52-86): **Cronbach α** ve **KR-20** hesabı, formüller tutarlı.
- **PÇ ulaşma**: ÖÇ başarı yüzdelerinin katkı-ağırlıklı ortalaması.

Eksik: ayrı Bloom düzeyi dağılım raporu, standart hata (SEM), dönemler/yıllar arası karşılaştırma raporu.

**Bu modül, grafik gösterip gerçek veriden hesap yapmama riskine karşı açıkça test edilmiş** — formüller gerçek öğrenci yanıtlarından hesaplanıyor (demo veri değil, canlı sorgu).

## F. Akademik kalite ve akreditasyon — PARTIALLY_COMPLETE (en kapsamlı modül)

[D] Route sayıları: `quality360_api.py` **60**, `compliance_api.py` **84** route. Kapsam: MÜDEK/MEDEK, ÖDR/KİDR, PEA, evaluator workspace, bulgu takibi, final rapor, kontrollü doküman, Program Review (maker-checker + final SHA-256 mühürlü snapshot), Evidence Hub (arama/etiket/duplicate SHA tespiti).

Eksik/doğrulanamayan: YÖKAK ve PUKÖ'nün uçtan uca UI akışı canlı test edilmedi; gerçek denetçi rolü yok (yalnız public/token'sız snapshot linki — bu aynı zamanda bir güvenlik bulgusu, bkz. security audit).

## G. Raporlama ve dashboard — PARTIALLY_COMPLETE

Mevcut: sonuç/gradebook/OBS/kalite/akreditasyon Excel çıktıları, sınav kâğıdı PDF, öğrenci karnesi PDF.
Eksik: fakülte/bölüm/rektörlük seviyesinde ayrı dashboard, ders/program bazlı PDF rapor.

## UX / Erişilebilirlik — PARTIALLY_COMPLETE

`lang="tr"` mevcut, 6 `@media` responsive breakpoint, ~134 aria/role/tabindex referansı (temel erişilebilirlik çabası var). **WCAG 2.2 AA otomatik taramayla doğrulanmadı.** 6.70.3 UI değişikliği 4 pytest + 2 E2E testini kırdı (bkz. test raporu) — bu bir UX regresyonu kanıtıdır.

## Özet tablo (görev formatı)

| Modül | Mevcut durum | Eksik | Öncelik | Kanıt |
|---|---|---|---|---|
| Soru bankası | CRUD/import/onay akışı çalışıyor | Versiyon geçmişi yok, export yok, review maker-checker yok | Yüksek | `main.py:2623,2644` |
| Sınav yönetimi | Durum makinesi, OMR, kitapçık PDF çalışıyor | Sınav takvimi/salon planı yok | Orta | takvim modelleri |
| Ölçme-değerlendirme | Gerçek formüllerle hesaplanıyor | Bloom dağılımı, SEM, dönemsel karşılaştırma yok | Orta | `analytics.py` |
| Kalite/akreditasyon | 144 route, çok geniş kapsam | Denetçi rolü yok, YÖKAK/PUKÖ uçtan uca doğrulanmadı | Yüksek | `quality360_api.py`, `compliance_api.py:633` |
| Kullanıcı/yetki | 6 rol çalışıyor | Öğrenci, denetçi, rektörlük, ÖDB rolleri yok | Yüksek | `authz.py:16-23` |
