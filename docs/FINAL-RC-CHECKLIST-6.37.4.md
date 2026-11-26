# DOU Assess 6.37.4 Final RC — Pazartesi Öncesi Kontrol

## Freeze
- API kontratı: `6.37-final-preintegration-server-ready`
- Schema head: `0023_strategic_quality`
- OBS/Entra gerçek kurum bilgileri gelene kadar veri modeli değiştirilmez.

## Kapatılan son açıklar
- Production pilot auth kill-switch
- Production demo seed kill-switch
- Preflight production güvenlik kapısı
- Paket içi runtime/test DB temizliği
- Read-only k6 kapasite testi taslağı
- UI terminoloji regresyon kontrolü

## Pazartesi entegrasyon kapısı
1. Entra Tenant/API/SPA bilgileri
2. Gerçek test kullanıcıları ve rol/kapsam eşlemesi
3. OBS read-only endpoint ve stable ID sözleşmesi
4. OBS → ders/şube/hoca/öğrenci enrollment dry-run
5. Menü/workflow'un role göre sadeleştirilmesi
6. 20k öğrenci / 600 akademisyen kapasite testi

## Yasak destructive işlemler
- `docker compose down -v`
- `docker volume prune`
- `docker system prune --volumes`
