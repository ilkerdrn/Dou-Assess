# Microsoft Entra Kurulum Notu — DOU Assess 6.18

Bu dosya Bilgi İşlem ile yapılacak gerçek Entra pilotunda gereken alanları özetler.

## Önerilen yapı
İki Entra App Registration kullanılması en temiz ayrımdır:

1. **DOU Assess API**
   - API scope expose eder, örneğin `Assess.Access`.
   - API application/client ID, access token audience olarak kullanılır.

2. **DOU Assess Web (SPA)**
   - Redirect URI: örneğin `https://assess.dogus.edu.tr/`
   - API üzerindeki delegated scope'a izin alır.
   - Authorization Code + PKCE kullanır; client secret tarayıcıya konmaz.

## Environment eşlemesi

```text
ENTRA_TENANT_ID=<Doğuş tenant GUID>
ENTRA_CLIENT_ID=<DOU Assess Web / SPA client GUID>
ENTRA_AUDIENCE=<DOU Assess API client GUID>
ENTRA_ALLOWED_CLIENT_IDS=<DOU Assess Web / SPA client GUID>
ENTRA_REQUIRED_SCOPES=Assess.Access
ENTRA_LOGIN_SCOPES=api://<API client GUID>/Assess.Access
ENTRA_REDIRECT_URI=https://assess.dogus.edu.tr/
```

## Kullanıcı eşleştirme
Production'da `ENTRA_AUTO_LINK_BY_EMAIL=false` kalmalıdır. Kullanıcının Entra `oid` + `tid` bilgisi DOU Assess kullanıcısına kontrollü biçimde bağlanmalıdır. Böylece aynı e-posta adına güvenilerek otomatik yetki verilmez.

## Token kontrolleri
Backend şu kontrolleri yapar:
- Microsoft tenant issuer
- `tid`
- `aud`
- `oid`
- v2 access token
- delegated `scp`
- çağıran `azp/appid`
- gerekli API scope

## Production öncesi kabul
- SPA redirect URI Entra portalında birebir kayıtlı olmalı.
- Scope için admin/user consent politikası netleşmeli.
- Test öğretim elemanı, program başkanı ve kalite hesabıyla ayrı ayrı login denenmeli.
- Login sonrası rol kapsamları DOU Assess içinden doğrulanmalı.


## 6.18 güvenlik notu

Production'da Uvicorn forwarded header'ları otomatik güvenmez. Dış TLS proxy ve iç NGINX tarafından gelen `X-Forwarded-*` bilgileri yalnız `TRUSTED_PROXY_CIDRS` içindeki peer üzerinden kabul edilir. `ENTRA_REDIRECT_URI` mutlaka HTTPS olmalıdır.
