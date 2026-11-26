# DOU Quality / Assess — 6.37 Pre‑Integration Readiness

## Dondurulan kapsam

6.37, Entra ve OBS canlı entegrasyonundan önceki son çekirdek sürümdür. Bu noktadan sonra entegrasyon tamamlanana kadar veri modeli veya kullanıcı akışına yeni özellik eklenmemelidir.

## Pazartesi entegrasyon kapıları

### Microsoft Entra ID
- Tenant ID
- Web/SPA Client ID
- API Audience / Client ID
- Delegated scope
- Redirect URI
- Test öğretim elemanı / program başkanı / kalite hesabı
- `oid/tid` kontrollü user mapping
- Grup/görev bilgisinin kurumsal kaynağı

### OBS
İlk faz read-only:
- academic term
- faculty/school
- department
- program
- course + section/offering
- instructor
- student
- enrollment
- ÖÇ/PÇ + mappings

Stable kimlikler korunmalıdır: `student_id`, `instructor_id`, `program_id`, `course_id`, `course_offering_id`, `term_id`, `enrollment_id`.

## Pilot acceptance

1. SSO login/logout ve role scope.
2. OBS sync + idempotency + conflict log.
3. Hoca: Derslerim → sınav → soru → öğrenci → analiz.
4. Program başkanı: program analizi → PUKÖ → kanıt.
5. Kalite: framework routing → readiness → visit mode → ÖDR/KİDR.
6. OMR/ADF gerçek tarama.
7. Backup + isolated restore.
8. 20k öğrenci / 600 hoca sentetik kapasite testi.
9. Browser/mobile critical-path smoke.
10. HTTPS / proxy / security header kabulü.

## Bilinçli olarak 6.37 dışında bırakılanlar

- Gerçek Entra tenant konfigürasyonu.
- Gerçek OBS servis sözleşmesi ve connector.
- Kurumsal SMTP/Teams notification entegrasyonu.
- Kuruma özgü nihai MEDEK/MÜDEK/TURAK/ACQUIN kriter dosyalarının kalite birimi tarafından resmî doğrulaması.
