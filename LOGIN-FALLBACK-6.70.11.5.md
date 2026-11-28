# DOU Assess 6.70.11.5 — Login Fallback

Pilot giriş düğmesi artık ana `app.js` veya `runtime-core.js` başlangıç zincirinden bağımsız bir dış script tarafından da yönetilir.

- Doğrudan `/api/auth/me` + `X-DOU-Pilot-User` doğrulaması
- 10 saniye timeout ve kullanıcıya görünür hata
- Başarılı auth sonrası login gate kesin kapatılır ve panel görünür
- Legacy login handler'ları capture phase ile devre dışı bırakılır
- Veritabanı / migration değişikliği yok
