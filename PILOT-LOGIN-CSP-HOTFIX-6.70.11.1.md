# DOU Assess 6.70.11.1 — Pilot Login + CSP Hotfix

- Pilot giriş artık `location.reload()` bağımlılığı olmadan seçili kullanıcıyı doğrular, `/api/auth/me` çağrısını yapar ve uygulama kabuğunu doğrudan açar.
- Giriş hatası login kartı içinde görünür ve generic "kimlik doğrulama gerekli" mesajına indirgenmez.
- Çıkış pilot kullanıcı + pilot session bilgisini birlikte temizler.
- Statik HTML'deki 3 CSP inline-style ihlali CSS sınıflarına/default kurallara taşındı.
- 6.70.11 asset marker korunur; ayrıca `67111-login-csp-hotfix` cache marker eklenir.
- DB migration yoktur; schema `0042_performance_production_hardening` kalır.
- Full regression: 312/312 PASS.
