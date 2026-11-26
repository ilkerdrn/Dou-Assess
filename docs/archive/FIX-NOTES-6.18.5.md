# DOU Assess 6.18.5 — Sidebar / Responsive UI Fix

## Düzeltilen sorun
- Sidebar alt menüleri açıldığında özellikle kısa ekranlarda kullanıcı kartı ve alt menülerin aynı alana taşması engellendi.
- Navigasyon alanı ayrı bir scroll bölgesine alındı (`flex: 1`, `min-height: 0`, `overflow-y: auto`).
- Kimlik ve API durum alanları sidebar altında sabit flex bölgeleri olarak ayrıldı.
- Menü grupları gerçek accordion davranışına alındı; yeni bir grup açıldığında diğer açık grup kapanır.
- Mobil drawer `100dvh` ile sabitlendi ve nav içeriği kendi içinde kayar.
- Kısa masaüstü ekranları için kompakt dikey navigasyon eklendi.
- CSS/JS cache etiketi `6.18.5-sidebar-fix` olarak yenilendi.

## Korunan özellikler
- Klasik tarama / rubrik puanlama
- Öğrenci sınav eşleştirme
- Soru havuzu Excel import
- OMR / legacy v2 uyumluluğu
- Production compose / backup / restore / migration zinciri
