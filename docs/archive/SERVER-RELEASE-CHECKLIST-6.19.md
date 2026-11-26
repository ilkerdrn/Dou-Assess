# DOU Assess 6.19 — Final Sunucu Yayın Kontrol Listesi

## Paket

- [ ] Final ZIP SHA256 doğrulandı.
- [ ] `SOURCE-MANIFEST-SHA256.txt` tüm dosyalarda PASS.
- [ ] Alembic head `0018_classic_assessment_standard`.
- [ ] Paket DB'sinde akademik/test verisi yok.
- [ ] `data/evidence`, `data/scans`, `data/ops` yalnız `.gitkeep` içeriyor.
- [ ] Production parolası ZIP içinde yok.

## Sunucu

- [ ] Docker Engine + Compose v2 hazır.
- [ ] Disk/RAM ve saat/NTP kontrol edildi.
- [ ] DNS kaydı hazır.
- [ ] TLS reverse proxy hazır.
- [ ] Güvenilir proxy CIDR'ları belli.

## Kimlik

- [ ] Entra Tenant ID.
- [ ] Client ID/Audience.
- [ ] Redirect URI.
- [ ] Gerekli scope'lar.
- [ ] Öğretim Görevlisi hesabı test edildi.
- [ ] Program Başkanı hesabı test edildi.
- [ ] Kalite Müdürü hesabı test edildi.
- [ ] Rol kapsamı dışındaki kaynağa erişim reddedildi.

## Uygulama

- [ ] `Production-Preflight.ps1` PASS.
- [ ] `Server-Ready-Check-6.19.ps1` PASS.
- [ ] Deploy tamamlandı.
- [ ] `/api/health` 200.
- [ ] `/api/ready` ready.
- [ ] Schema 0018.

## Pilot kabul

- [ ] Excel Akademik Veri doğrulandı/içe aktarıldı.
- [ ] 72 soruluk yeni soru havuzu doğrulandı.
- [ ] Klasik soruda beklenen cevap/rubrik/ÖÇ kontrolü çalıştı.
- [ ] Öğrenci atama + katılım çalıştı.
- [ ] PDF/ADF OMR okundu.
- [ ] Klasik cevap crop görüntülendi.
- [ ] Rubrik puanlandı.
- [ ] Devamsız öğrenci analizden çıkarıldı.
- [ ] Puan kilidi çalıştı.
- [ ] İtiraz/rubrik yeniden değerlendirme audit izi oluşturdu.
- [ ] Kalite/PDCA sonucu kaydedildi.
- [ ] Kanıt paketi üretildi.

## Operasyon

- [ ] Backup alındı.
- [ ] Ayrı ortama restore tatbikatı yapıldı.
- [ ] Log/monitoring yöntemi belirlendi.
- [ ] Evidence/scans/ops volume yedek planı belirlendi.
- [ ] KVKK saklama/anonimleştirme süreleri kurum tarafından onaylandı.
