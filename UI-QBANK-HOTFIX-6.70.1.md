# DOU Assess 6.70 UI / Question Bank Hotfix 6701

Bu hotfix veritabanı şemasını veya 6.70 backend release kontratını değiştirmez.

## Düzeltilenler

1. **Soru Bankası → Yeni soru oluştur**
   - Kök neden JavaScript değildi: editor `is-open` sınıfını almasına rağmen eski `#page-bank .bank-editor-card` selectorü daha yüksek CSS specificity ile `translateX(104%) !important` değerini koruyordu.
   - Yeni `#page-bank .bank-editor-card.is-open` selectorü paneli gerçekten görünür alana getirir.

2. **Login ekranı**
   - Sabit genişlikli login canvas sola yapışık kalıyordu.
   - Login artık viewport içinde ortalanır ve masaüstünde 1440px'e kadar alanı dengeli kullanır.

3. **Sidebar / Program Review aktif öğe**
   - Eski submenu guide pseudo-elementi ve yeni aktif çizgi aynı anda çiziliyordu.
   - Eski guide/pseudo active çizgileri kapatıldı; tek aktif gösterge bırakıldı.

4. **Cache bust**
   - styles/runtime/app asset URL'lerine `h=6701` eklendi.

## Doğrulama

- Full regression: 257/257 PASS
- Chromium visual contract: login centered at 1600x900; question editor visible at x=940 width=660 after open transition.
- Database migration: yok.
- Expected schema: `0042_performance_production_hardening`.
