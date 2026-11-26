# DOU Assess 6.19 — Final Release Notes

## Ana geliştirmeler

- Üç akademik persona: Öğretim Görevlisi, Program Başkanı, Kalite Müdürü.
- Bağlama duyarlı ekran kılavuzu ve rol bazlı onboarding.
- Merkezi Excel şablon/doğrulama/içe aktarma deneyimi.
- Katılım statüsü ve ölçüm paydasından doğru hariç tutma.
- Sınav olay/istisna kayıtları.
- Puan kilidi ve kilit sonrası normal puan değişikliği engeli.
- Öğrenci/soru bazlı itiraz ve kontrollü rubrik yeniden değerlendirme.
- Klasik soruda beklenen cevap + Bloom + ÖÇ + analitik rubrik standardı.
- Rubrik kriteri → ÖÇ eşleşmesi ve kriter bazlı kalite ölçümü.
- PDCA etkililik doğrulaması ve kapanış zinciri.
- Kalite kontrol kuyruğu ve klasik moderasyon sinyalleri.
- Akreditasyon kanıt paketine olay/itiraz/iyileştirme kayıtları.
- 72 soruluk pilot soru havuzundaki 12 klasik soru yeni 6.19 standardına yükseltildi.

## Şema

```text
0018_classic_assessment_standard
```

Yeni migration'lar:

- `0017_quality_ops`
- `0018_classic_assessment_standard`

## Geriye uyumluluk

- Yeni QR'lı soru sayfaları desteklenir.
- Eski `dou-official-v2` sınav kağıtları legacy fallback ile okunmaya devam eder.
- 6.18 operasyon scriptlerinin dosya adları geriye uyumluluk için tutulur; içerikleri 0018 head ile güncellenmiştir. Yeni kurulumda 6.19 isimli scriptleri kullanın.
