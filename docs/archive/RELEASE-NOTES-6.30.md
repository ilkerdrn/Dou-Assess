# DOU Assess 6.30 — Quality Governance & Escalation Engine

Sürüm: `6.30-quality-governance-escalation-server-ready`

## Yeni
- Açık PUKÖ döngüleri için termin ve gecikme takibi.
- 1–7 gün gecikme: aksiyon sorumlusu takibi.
- 8–14 gün: bölüm/program başkanlığı eskalasyonu.
- 15–29 gün: fakülte/MYO yönetimi eskalasyonu.
- 30+ gün: Üniversite Kalite Birimi kurumsal eskalasyonu.
- 7 gün içinde bitecek işler ve terminsiz işler ayrı görünür.
- Yönetim ekranında termin/eskalasyon özeti ve program drill-down.
- Motor bildirim göndermez, rol/yetki değiştirmez; yalnızca açıklanabilir yönetişim önerisi üretir.

## Veri tabanı
Yeni migration yoktur. Şema head: `0021_quality_framework_routing`.
