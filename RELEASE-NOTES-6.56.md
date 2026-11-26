# DOU Assess 6.56 — Premium Student Success Profile

Bu sürüm öğrenci karnesinin ekran ve PDF deneyimini yeniden tasarlar. Akademik/kalite hesaplama mantığı, schema head (`0031_medek_final_decision`) ve production deploy katmanı değişmemiştir.

## Öğrenci Karnesi
- Öğrenci kimliği, program/sınıf ve dönem bilgisini öne alan premium profil başlığı.
- Genel çıktı başarısı için büyük görsel skor halkası ve mezuniyet hazırlığı özeti.
- Ölçülen ÖÇ/PÇ, risk ve ders kapsamını daha okunur KPI kartlarıyla sunma.
- PÇ satırlarında erişim, hedef, hedef farkı ve durumun birlikte gösterimi.
- Güçlü alan, gelişim odağı ve ölçüm kapsamı için ayrı akademik içgörü kartları.
- Ders kartlarında sınav/ölçüm sayısı, ÖÇ kapsamı, ders başarı düzeyi ve risk durumu.
- Responsive mobil/tablet düzeni.

## PDF Karnesi
- Kurumsal öğrenci profil başlığı ve doğrulanabilir kimlik alanı.
- Premium özet KPI kartları.
- Güçlü alan / gelişim odağı bölümü.
- PÇ ve ders/ÖÇ satırlarında hedef farkı ve görsel ilerleme çizgileri.
- QR + doğrulama kodu korunmuştur.

## Güvence
- Backend outcome hesapları değişmedi.
- Öğrenci snapshot/freeze semantiği değişmedi.
- 200/200 regression PASS.
- Classic / Legacy Classic / Complete Assessment Engine / Lifecycle PASS.
- Pilot UAT 41/41 PASS; accreditation_ready=true.
