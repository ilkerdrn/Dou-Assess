# DOU Assess kapasite testi (read-only)

Bu paket üretim verisini değiştirmeyen GET tabanlı k6 smoke/load senaryosu içerir.
Gerçek üniversite pilotundan önce 50 → 100 → 200 → 300 eşzamanlı kullanıcı kademeleriyle çalıştırın.

Örnek (Entra access token ile):

```bash
BASE_URL=https://assess.dogus.edu.tr \
ACCESS_TOKEN='...' VUS=50 HOLD=2m \
k6 run ops/load/k6-read-only.js
```

Kabul hedefi: hata <%1; yaygın ekran/API p95 <1.5 sn. CPU/RAM/DB connection ve disk I/O aynı anda izlenmelidir.
500 kullanıcı testi yalnız 300 kullanıcı kademesi temiz geçtikten sonra yapılmalıdır.
