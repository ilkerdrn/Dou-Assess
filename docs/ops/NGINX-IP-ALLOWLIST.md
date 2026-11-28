# Sunucuyu kimlik doğrulama gelene kadar daraltma (geçici koruma)

**Neden:** Pilot modunda (`AUTH_REQUIRED=false`) başlıksız bir istek admin bağlamı alır (bkz. `docs/product-audit/SECURITY_AUDIT.md` S1).
OBS girişi açılana kadar erişimi kurumsal ağ aralığına kısıtlayın.

HTTPS'i sağlayan **ana makinedeki nginx** (örn. `/etc/nginx/sites-enabled/assess.dogus.edu.tr`) `server` bloğunda,
`location /` içine şunu ekleyin (aralıkları BT'den alın; aşağıdakiler örnektir):

```nginx
location / {
    allow 10.8.0.0/16;      # kurum iç ağı / VPN havuzu — BT'den doğrulayın
    allow 127.0.0.1;
    deny  all;
    proxy_pass http://127.0.0.1:8080;   # mevcut satırlar aynen kalsın
    # ... mevcut proxy_set_header satırları ...
}
```

Doğrulama (izinsiz bir ağdan): `curl -I https://assess.dogus.edu.tr/` → `403`.
Uygulama sonrası: `sudo nginx -t && sudo systemctl reload nginx`. Geri almak için `allow/deny` satırlarını silip yeniden yükleyin.

Kalıcı çözüm: OBS girişi (`AUTH_REQUIRED=true`, `AUTH_PROVIDER=obs`), bkz. `.env.pilot` OBS bölümü.
