# DOU Assess 6.55 — Premium Academic UX

Bu release yalnız arayüz/deneyim katmanını modernize eder. Backend, şema, akreditasyon ve ölçme-değerlendirme davranışları 6.54.1 ile aynıdır.

## Tasarım hedefleri
- Üniversite kurumsal sistemi hissi: sade, güvenilir, açık tema.
- Günlük öğretim elemanı akışında daha az görsel yük.
- 7–10 px mikro metinlerin kritik yüzeylerde kaldırılması ve okunabilirliğin artırılması.
- Rol bazlı menü hiyerarşisinin daha net algılanması.
- Action Center'ın dashboard'un gerçek çalışma kuyruğu olarak öne çıkarılması.
- Quality360 / MEDEK / MÜDEK ekranlarında kanıt ve durumun görsel süsten önce gelmesi.
- Form, tablo ve butonların minimum rahat tıklama/okuma ölçülerine taşınması.
- Mobilde iki kolonlu yoğun kontrollerin sadeleşmesi.

## Görsel sistem
- Kurumsal bordo: `#9d1730`
- Ana metin: `#17202b`
- Açık zemin: `#f5f6f8`
- Kart yüzeyi: `#ffffff`
- Kartlar: düşük gölge + belirgin sınır
- Sol menü: açık kurumsal navigasyon
- Başlıklar: daha güçlü tipografik hiyerarşi

## Değişmeyenler
- API contract'ları
- DB schema (`0031_medek_final_decision`)
- MEDEK/MÜDEK/Quality360 hesapları
- Rol/yetki davranışları
- Öğrenci karnesi hesapları
- Sınav, OMR ve klasik değerlendirme motorları
