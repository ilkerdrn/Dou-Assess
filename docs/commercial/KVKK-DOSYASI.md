# KVKK dosyası (taslak)

Hukuk/KVKK biriminin tamamlayıp onaylaması gerekir; bu belge teknik envanteri hazırlar.

## 1. Veri envanteri
| Veri | Kategori | Amaç | Saklama | Erişim |
|---|---|---|---|---|
| Öğrenci no, ad-soyad, sınıf | Kimlik | Ders kaydı, sınav kâğıdı, karne | Öğrencilik süresi + `STUDENT_DATA_RETENTION_DAYS` | Dersin öğretim elemanı, program/kalite rolleri |
| Sınav cevap kâğıdı (tarama) | El yazısı/kimliklendirilebilir | Puanlama, itiraz, akreditasyon kanıtı | `SCAN_RETENTION_DAYS` (kurum arşiv yönergesiyle teyit) | Aynı |
| Puanlar, ÖÇ/PÇ başarıları | Akademik | Not, analiz, akreditasyon | Dönem kapanış paketiyle arşiv | Aynı |
| Kullanıcı e-postası, rol | Kimlik | Yetkilendirme | Hesap süresi | Yönetici |
| İşlem/denetim kaydı | İşlem güvenliği | İzlenebilirlik | Kurum politikası | Yönetici, kalite |

## 2. Üçüncü taraf paylaşımı
- Değerlendirici (MEDEK/MÜDEK vb.): salt-okunur, süreli, **öğrenci adları maskeli**, erişim denetim kaydında
- Yapay zekâ/OCR: **varsayılan kapalı**; açılmadan önce `docs/KVKK-AI-OCR-DEGERLENDIRME.md` kapatılmalı
- Bulut/yedek: depolama konumu ve yurt dışı aktarımı kuruma göre doldurulacak: ________

## 3. İlgili kişi hakları (uygulamadaki karşılığı)
- Erişim: öğrenci portalı (kendi kâğıdı/puanları); itiraz: portal üzerinden
- Silme/anonimleştirme: `students.anonymized_at`, tarama görseli kayıtlı silme (`POST /api/exams/{id}/purge-scans`)
- Düzeltme: puan değişiklikleri revizyon kaydıyla (`response_grade_revisions`)

## 4. Teknik/idari tedbirler
Rol bazlı erişim, denetim kaydı, HTTPS zorunlu (üretim), gizli anahtarlar ortam/dosya, yedek şifreleme, bütünlük özetleri (SHA-256), kapanış paketi.

## 5. Onay
- [ ] Veri sorumlusu envanteri  - [ ] VERBİS  - [ ] Aydınlatma metni  - [ ] Veri işleyen sözleşmesi  - [ ] Risk/etki değerlendirmesi
