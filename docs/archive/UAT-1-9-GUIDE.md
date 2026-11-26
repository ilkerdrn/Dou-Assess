# DOU Assess · Local Pilot UAT 1–9

Bu kabul paketi kurum dışı/local pilotta aşağıdaki zinciri tek seferde doğrular:

1. Ana uygulama, pilot oturum ve rol/yetki sınırları
2. Ders, 30 öğrenci, 4 ÖÇ + 4 PÇ ve eşleştirmeler
3. Soru Bankası 2.0: konu, ünite, zorluk, Bloom, görsel ve rubrik
4. Vize %40, A/B/C/D kitapçık ve PDF
5. Gerçek OMR: otomatik kabul + çift işaret/manual review çözümü
6. Final %60, A3 yatay, ayrı optik, duplex ve klasik rubrik
7. Cronbach Alpha, KR-20, ayırt edicilik, point-biserial, çeldiriciler, ağırlıklı not/ÖÇ/PÇ
8. İyileştirme aksiyonu, MIN/AVG/MAX, MEDEK profili, kanıtlar ve kanıt ZIP'i
9. Ağırlıklı not defteri ve OBS Excel çıktısı

**Adım 10 (gerçek Entra, gerçek OBS API, production sunucu/domain/SSL) bilinçli olarak bu UAT'nin dışındadır.**

## Çalıştırma

Pilot ayaktayken proje klasöründe:

```powershell
powershell -ExecutionPolicy Bypass -File .\Run-UAT-1-9.ps1
```

Script gerekirse pilotu başlatır, API container içinde izole bir UAT veritabanı oluşturur ve gerçek servis kodunu kullanarak senaryoyu çalıştırır. Mevcut pilot veritabanını kirletmez.

Çıktılar `UAT-1-9-Outputs` klasörüne gelir:

- Vize PDF
- kabul edilmiş OMR örneği
- belirsiz/double-mark OMR örneği
- A3 yatay Final PDF
- gelişmiş sınav analiz Excel'i
- MEDEK yönetici raporu
- MEDEK kanıt ZIP'i
- ağırlıklı ders not defteri
- OBS sonuç Excel'i
- JSON ve Markdown kabul raporu
