# ADR: Çok kiracılı (multi-tenant) mimari

Durum: **Öneri — karar bekliyor.** Tarih: 2026-11.

## Bağlam
DOU Assess bugün tek kurum (Doğuş) için çalışır. İkinci bir üniversiteye satmak için veri ayrımı, kurum bazlı ayar (terim, eşik, saklama, depolama) ve bağlayıcı (OBS) gerekir.

## Seçenekler
| | A. Kiracı başına veritabanı + uygulama örneği | B. Tek veritabanı, satır düzeyinde `tenant_id` |
|---|---|---|
| Veri ayrımı | Güçlü (fiziksel) | Yazılım katmanına bağlı; tek hata = veri sızıntısı |
| Kod değişikliği | Çok az: ortam değişkenleri + kurum ayarları | Yüksek: ~100 tabloda alan, her sorguda filtre, tüm benzersizlik kısıtları (örn. `students.student_no` global unique) değişir |
| KVKK / yedek / silme | Kurum başına yedek, tek komutla silme | Karmaşık |
| İşletim maliyeti | Kurum sayısıyla artar (az sayıda kurumda kabul edilebilir) | Düşük |
| Kurum bazlı depolama/şifre | Doğal | Özel çalışma |

## Karar önerisi
**A** ile başlanır (≤ ~10 kurum). Gerekçe: kod tabanı küresel benzersizlik kısıtlarına (öğrenci no, program kodu) ve küresel sorgulara dayanır; satır düzeyi ayrım güvenlik riski ve büyük refaktör getirir.

## Bugün hazır olanlar
- Kurum ayarları (`institution_settings`): ÖÇ terimi, ÖÇ değişiklik onayı, soru kendi kendine onay, yapay zekâ önerisi.
- Sürümlü başarı eşikleri (kurum/program/yıl).
- Bağlayıcı arayüzü (`app/services/connectors.py`): yeni OBS = tek sınıf.
- Saklama süresi ve depolama yolu ortam değişkeni (`SCAN_RETENTION_DAYS`, `SCAN_STORAGE_PATH`, `EVIDENCE_STORAGE_PATH`).

## Açık işler
- Kurum başına dağıtım şablonu (compose/Helm), kurum başına gizli anahtarlar, yedek zamanlaması.
- Kurum logosu/başlık metni (kâğıt şablonu şu an Doğuş'a özel: `app/services/paper.py` başlık ve logo) — şablon ayarlanabilir hâle getirilmeli.
- Kimlik: kurumun Entra/Google tenant'ı (`ENTRA_*`) kurum başına.
