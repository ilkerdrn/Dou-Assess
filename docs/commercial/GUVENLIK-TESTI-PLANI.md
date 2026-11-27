# Güvenlik testi planı

Kapsam: DOU Assess uygulaması + dağıtım. Bu plan, bağımsız bir sızma testi öncesi iç doğrulamayı ve test firmasına verilecek kapsamı tanımlar.

## 1. Otomatik (CI'da çalışan)
- Birim/yetki testleri: rol kapsamı (öğretim elemanı yalnız kendi dersi), değerlendirici token kapsamı, öğrenci bağlantısı yalnız kendi kâğıdı (`tests/`)
- Bağımlılık: `Verify-Supply-Chain.sh`, SBOM (`SBOM-*.cdx.json`)
- Üretim güvenlik ön kontrolü: `Preflight-Server.sh`

## 2. Elle doğrulanacak (iç)
| Alan | Test | Beklenen |
|---|---|---|
| Kimlik | Token'sız/yanlış token ile her `/api/*` | 401; `/api/public/*` yalnız ilgili token ile |
| Yatay yetki | Başka dersin sınav/öğrenci/tarama id'si | 403/404 |
| Değerlendirici odası | Başka programın ders/sınav/öğrenci id'si | 404; öğrenci adı maskeli |
| Öğrenci portalı | Başka öğrencinin bağlantı token'ı | 401; puanlar kilitlenmeden açılmaz |
| Girdi | Dosya yükleme (PDF/Excel/görsel) boyut, tür, zip bomb | Reddedilir, sınır `MAX_*` |
| Dışa aktarım | Kapanış paketi/OBS dosyası yetkisiz erişim | 403 |
| Gizli anahtarlar | `STUDENT_LINK_SECRET`, `AI_SCORING_API_KEY` günlüğe/yanıta sızıyor mu | Hayır |
| Yapay zekâ | Kapalıyken öneri uç noktası; açıkken istemde öğrenci kimliği | 403; kimlik yok |
| Denetim | Kritik işlemler `audit_logs`'ta (puan değişikliği, kilit, silme, itiraz kararı) | Var |

## 3. Bağımsız test (dış)
- Kapsam: web uygulaması, API, kimlik (SSO), dosya işleme (PDF/OpenCV), dağıtım yapılandırması
- Yöntem: OWASP ASVS L2 + API Security Top 10; gri kutu (rol hesapları verilir)
- Çıktı: bulgular önem sırasıyla, düzeltme + yeniden test
- Zamanlama: ikinci kurum pilotundan önce
- Bilinen riskler (yeniden test edilecek): OMR/görsel işleme girdileri, öğrenci bağlantısı imzası (HMAC, süre sınırı yalnız itiraz penceresi), değerlendirici token'ı URL parçasında taşınır
