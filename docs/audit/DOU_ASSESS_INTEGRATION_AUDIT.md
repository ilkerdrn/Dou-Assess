# DOU Assess – Entegrasyon Denetimi

**Kaynak:** `e98e723` (6.70.3). Yöntem: kod okuma (salt okunur). Canlı sistemlere bağlanılmadı.
**Güven notu:** Aşağıdaki "[D]" ile işaretli satırları denetçi olarak ben kaynakta tekrar doğruladım; işaretsiz olanlar kod okuması bulgusudur, çalıştırılmamıştır.

## Genel sonuç

Proliz/OBS ve DOU Core entegrasyonları **geliştirilmemiş**. Akademik veri sisteme tek yoldan girer: **elle yüklenen Excel çalışma kitabı**. Entra ID kodu vardır ama yalnız sahte JWKS ile birim testlidir.

## Entegrasyon tablosu

| Entegrasyon | Durum | Öncelik | Kanıt |
|---|---|---|---|
| Proliz REST istemcisi (kimlik doğrulama, dönem/fakülte/bölüm/ders/öğrenci/akademisyen/müfredat/kayıt/not çekme) | **NOT_IMPLEMENTED**; canlı doğrulama **BLOCKED** | Kritik | [D] `proliz`/`portalapi` kodda yalnız `app/production_acceptance_api.py:28,49-53` (kabul kapısı tanımı) ve katalog metinlerinde geçer; tek dış HTTP çağrısı `app/main.py:1434` (OBS **sonuç geri yazımı**, okuma değil). |
| Akademik veri içe aktarma | **PARTIALLY_COMPLETE** (yalnız Excel) | Yüksek | `POST /api/integrations/obs/workbook/validate\|sync` (`main.py:3847-3893`); beş sayfa zorunlu (`services/imports.py:16`); referans kontrolü `imports.py:184-202`; `external_id` eşleme `imports.py:373-420`. |
| Fakülte/bölüm hiyerarşisi, akademisyen, müfredat, OBS notları | **NOT_IMPLEMENTED** | Yüksek | Fakülte/bölüm düz metin alan; akademisyen yalnız `instructor_email`. |
| Senkronizasyon geçmişi | **PARTIALLY_COMPLETE** | Orta | `IntegrationSyncRun` (`models.py:867`), SHA-256 ile yinelenen dosya tespiti, başarısız çalışmalar kayıtlı. Çakışma (conflict) günlüğü yok. |
| Retry / hata yönetimi (OBS) | **NOT_IMPLEMENTED** | Orta | Retry/backoff yok; geri yazım tek deneme, hata 502. Otomatik çekim (zamanlanmış sync) yok. |
| OBS sonuç geri yazımı | **PARTIALLY_COMPLETE**, varsayılan kapalı, canlı test yok | Orta | `main.py:1409-1448`. `OBS_WRITEBACK_ENABLED=false` iken 403; production'da HTTPS zorunlu, ağırlık toplamı %100 kontrolü, Bearer token, SHA-256 başlığı. Yük şeması **varsayım** (yalnız `final_grade`/`status`). Çalışan alternatif: OBS-uyumlu Excel dışa aktarma (`services/exports.py:445-509`). |
| Geri yazım testleri | **PARTIALLY_COMPLETE** | Orta | `tests/test_664_integration_acceptance_guard.py` yalnız "kapalıyken 403" ve token sızmaması; başarılı push, hata yolu, HTTPS kuralı testlenmemiş. |
| Microsoft Entra ID | **PARTIALLY_COMPLETE**; gerçek tenant **NOT_VERIFIED** | Kritik (production kabulü) | JWKS, issuer/aud/tid/oid/scp, izinli client, zorunlu scope (`authz.py:89-150`), production kontrolleri (`security.py:105-175`). Test sahte `PyJWKClient` ile (`tests/test_core.py:662-689`). `.env.production.example` değerleri `CHANGE_ME`. |
| DOU Core (ortak kimlik, akademik organizasyon, merkezi yetki) | **NOT_IMPLEMENTED** | Yüksek | Kodda/yapılandırmada/dokümanda referans yok. Kimlik: kendi `users/roles` tabloları + Entra `oid`. |

## Kritik bulgu: kabul kapısı yanıltıcı olabilir [D]

`app/production_acceptance_api.py:49-53` — `proliz_obs_readonly` kapısı, son 20 `IntegrationSyncRun` içinde `status=="success"` ve `provider != "obs-results-api"` olan bir kayıt arar. Excel yüklemesi `provider="obs-workbook"` ile başarı kaydı üretir (`main.py:3885`). Dolayısıyla **gerçek Proliz bağlantısı olmadan, yalnızca Excel yükleyerek** kapı `ready` olabilir. Kapı `manual: True` olarak işaretli (insan onayı gerekir) ama sistem durumu yanıltıcı "ready" gösterir. Öneri: kapıyı sağlayıcı bazlı (`provider == "proliz"`) yap.

## `docs/PRE-INTEGRATION-READINESS-6.37.md`

Faz-1 kapsamı read-only OBS (dönem, fakülte, bölüm, program, ders, öğretim elemanı, öğrenci, kayıt, ÖÇ/PÇ) olarak tanımlı; gerçek Entra ve OBS bağlayıcısı bilinçli olarak kapsam dışı bırakılmış. 6.70.3'te de yapılmamış.

## Doğrulanamayanlar (BLOCKED / kullanıcı aksiyonu)

1. **Proliz API (`portalapi.dogus.edu.tr/swagger`) ve eski HTTP 403:** bu oturumdan test edilmedi (ağ/kimlik yok). Gerekli: Swagger/OpenAPI JSON dosyası, kimlik doğrulama yöntemi, 403 nedeninin (IP izin listesi/VPN/yetki) Bilgi İşlem'den netleştirilmesi.
2. **Entra:** Bilgi İşlem'den tenant/client/audience/scope değerleri ve test hesapları (öğretim elemanı, program başkanı, kalite) gerekli.
3. **DOU Core:** API/şema sözleşmesi yok; sözleşme olmadan geliştirilemez.
4. **Uçtan uca zincir (OBS → Core → Assess → … → kalite raporu):** `NOT_VERIFIED` — ilk iki halka yok.

## Öneri sırası

1. Read-only OBS bağlayıcı arayüzü tasarla (Excel yolunu yedek bırak).
2. Kabul kapısını sağlayıcıya göre sıkılaştır.
3. Geri yazım için test seti (başarı, hata, HTTPS, idempotency) + retry/backoff.
4. Entra için staging tenant ile uçtan uca test.
