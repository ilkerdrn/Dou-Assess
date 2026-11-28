# DOU Assess 6.70.11.4 — Login Runtime Hardening

Amaç: Pilot kullanıcı girişini büyük `app.js` başlangıç zincirinden ayırmak.

- `runtime-core.js` giriş butonunu capture aşamasında sahiplenir.
- Seçilen kullanıcı `/api/auth/me` çağrısında `X-DOU-Pilot-User` ile açıkça doğrulanır.
- Doğrulama başarılı olduğunda panel anında açılır.
- Dashboard/veri yükleme hataları doğrulanmış kullanıcıyı yeniden login ekranına atamaz.
- Gizli sekmede kullanıcı listesi için bağımsız bootstrap vardır.
- Hızlı Başlangıç otomatik açılmaz; manuel olarak korunur.
- Veritabanı migration yoktur.
