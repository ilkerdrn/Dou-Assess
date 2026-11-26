# DOU Assess 6.18 — Complete Engine Feature Freeze

6.18 Complete Assessment Engine ile planlanan yazılım kapsamı kapatılmıştır.

## Bu sürümde kapanan kapsam
- Ders değerlendirme ağırlıkları ve ağırlıklı ÖÇ/PÇ
- Ders bazlı geçme eşiği ve doğru derece/sıralama
- OBS sonuç Excel'i ve HTTPS outbound adaptörü
- Soru Bankası 2.0, görsel soru ve rubrik
- Cronbach Alpha, KR-20, ayırt edicilik, point-biserial ve çeldirici analizi
- A3/A4/A5, yatay/dikey, ayrı/dahili OMR ve duplex PDF
- Maker-checker onay/revizyon akışı
- Evidence sürümleme/önizleme/saklama yaşam döngüsü
- KVKK anonimleştirme ve retention readiness kontrolleri

## Feature freeze sonrası yalnız kabul kapsamı
Bu noktadan sonra 6.18 hattında yalnız aşağıdaki işler yapılmalıdır:
1. Manuel UAT'de bulunan gerçek hata düzeltmeleri.
2. Fiziksel ADF/OMR saha testinde bulunan hata düzeltmeleri.
3. Gerçek Microsoft Entra tenant uyarlaması.
4. Kurum OBS sözleşmesine göre alan eşleme uyarlaması.
5. Hedef PostgreSQL + NGINX sunucusunda deployment/load/backup-restore kabulü.
6. Güvenlik veya performans testinde bulunan kritik bulgular.

Yeni ürün modülleri 7.x yol haritasına alınmalıdır.
