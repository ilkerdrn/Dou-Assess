# DOU Assess – Eksik Analizi ve Önceliklendirme

**Kaynak:** 6.70.3 (`a531ae7`). Diğer 5 denetim raporunun sentezi.

## Ana tablo

| Modül | Mevcut durum | Eksik | Öncelik | Kanıt | Statü |
|---|---|---|---|---|---|
| Soru bankası | CRUD, çoklu ÖÇ eşleme, Excel import, yaşam döngüsü çalışıyor | Versiyon geçmişi yok (`main.py:2623`), export yok, review'da maker-checker yok | Yüksek | `MODULE_AUDIT.md` §C | PARTIALLY_COMPLETE |
| Sınav yönetimi | Durum makinesi, A-D kitapçık PDF, OMR/klasik tarama, not kilidi, itiraz çalışıyor | Sınav takvimi/salon/gözetmen planı yok | Orta | `MODULE_AUDIT.md` §D | PARTIALLY_COMPLETE |
| Ölçme-değerlendirme | Güçlük, ayırt edicilik (Pearson), Cronbach α, KR-20, PÇ ulaşma gerçek veriyle hesaplanıyor | Bloom dağılımı raporu, SEM, dönemsel karşılaştırma yok | Orta | `MODULE_AUDIT.md` §E, `analytics.py` | PARTIALLY_COMPLETE (hesaplar VERIFIED_COMPLETE) |
| OBS entegrasyonu | Yalnız Excel ile elle veri girişi; sonuç geri yazım adaptörü var ama varsayılan kapalı | Proliz REST bağlantısı yok; otomatik çekme yok; kabul kapısı Excel ile de "ready" olabiliyor (yanıltıcı) | **Kritik** | `INTEGRATION_AUDIT.md` | NOT_IMPLEMENTED (Proliz) / PARTIALLY_COMPLETE (Excel yolu) |
| Kalite ve akreditasyon | 144 route (quality360+compliance), MÜDEK/MEDEK/ÖDR/KİDR, Program Review, Evidence Hub | Denetçi rolü yok (yalnız public snapshot link — S-08 ile ilişkili), YÖKAK/PUKÖ uçtan uca doğrulanmadı | Yüksek | `MODULE_AUDIT.md` §F | PARTIALLY_COMPLETE |
| Kullanıcı/yetki | 6 rol (admin/quality/instructor/program_head/department_head/faculty_admin) çalışıyor, kapsam SQL ile süzülüyor | Öğrenci girişi, denetçi rolü, rektörlük, ölçme-değerlendirme birimi rolleri yok | Yüksek | `MODULE_AUDIT.md` §A | PARTIALLY_COMPLETE |
| Veritabanı | 111 tablo, 42 migration tek head, SQLite'ta temiz kurulum PASS | PostgreSQL'de hiç test yok; CASCADE 121 FK ile sessiz veri kaybı riski; yedek şifresiz | Yüksek | `DATABASE_AUDIT.md` | PARTIALLY_COMPLETE |
| Güvenlik | RBAC, IDOR koruması, Entra JWT, not kilidi/maker-checker, CSP sağlam | Not revizyon audit'i yok, yedek şifresiz, production'da docs açık, XFF güvenilmez | Yüksek (S-01 Kritik ama yalnız pilot modda) | `SECURITY_AUDIT.md` | PARTIALLY_COMPLETE |
| Test/CI | 259/263 pytest PASS (gerçek çalıştırıldı) | CI/CD yok; 4 UI test + 2 E2E kırık (6.70.3 regresyonu); Postgres/backup/perf test yok | Yüksek | `TEST_REPORT.md` | PARTIALLY_COMPLETE |
| Raporlama/Dashboard | Excel/PDF çıktıları (sonuç, gradebook, OBS, kalite, akreditasyon, sınav kâğıdı, karne) | Fakülte/bölüm/rektörlük dashboard'u, ders/program PDF raporu yok | Orta | `MODULE_AUDIT.md` §G | PARTIALLY_COMPLETE |
| Production sunucusu | `/opt/dou-assess/`, `assess.dogus.edu.tr` var; deploy script'leri (Install/Upgrade/Backup/Restore/Verify-Server.sh) kapsamlı | Sunucunun fiilen hangi sürümü çalıştırdığı, bu ortamdan doğrulanamıyor | Kritik | `PROJECT_STATUS.md` | **BLOCKED** |
| DOU Core entegrasyonu | — | Kodda hiç referans yok | Yüksek (mimari risk) | `INTEGRATION_AUDIT.md` | NOT_IMPLEMENTED |

## Statü dağılımı (görev formatı)

- **VERIFIED_COMPLETE:** Ölçme-değerlendirme formülleri (güçlük/ayırt edicilik/güvenirlik), Alembic tek-head migration zinciri (SQLite), temel RBAC/IDOR koruması.
- **PARTIALLY_COMPLETE:** Soru bankası, sınav yönetimi, kalite/akreditasyon, kullanıcı/yetki, raporlama, veritabanı bütünlüğü, güvenlik, test altyapısı, OBS sonuç geri yazımı.
- **BROKEN:** 6.70.3 sonrası 4 UI-kontrat testi + 2 E2E testi (nav değişikliği); yedekleme script'i (şifresiz secret kopyalama).
- **NOT_IMPLEMENTED:** Proliz OBS otomatik entegrasyonu, DOU Core entegrasyonu, öğrenci/denetçi/rektörlük/ÖDB rolleri, soru versiyon geçmişi, soru bankası export, sınav takvimi/salon planı, not revizyon audit tablosu, Bloom dağılım raporu.
- **DEMO_ONLY:** Tespit edilmedi — denetlenen özelliklerin tamamı gerçek veriyle/gerçek koddan çalışıyor (demo veri ile üretim mantığı ayrımı net).
- **BLOCKED:** Production sunucu durumu, Proliz API erişimi, gerçek Entra tenant testi, PostgreSQL canlı davranışı, backup/restore tatbikatı, canlı nginx/XFF.
- **NOT_VERIFIED:** Performans/yük, WCAG 2.2 AA otomatik tarama, dependency/CVE taraması, çok işçili (multi-worker) rate-limit davranışı.

## En kritik 10 bulgu (öncelik sırasıyla)

1. **Proliz OBS entegrasyonu hiç yok**; akademik veri yalnız elle Excel ile giriyor — kurumsal ölçekte sürdürülemez.
2. **DOU Core entegrasyonu hiç yok** — kimlik/akademik ana veri sahipliği belirsiz.
3. Production acceptance kapısı (`proliz_obs_readonly`) Excel yüklemesiyle de "ready" dönebiliyor — **yanıltıcı go-live sinyali**.
4. Not/puan değişikliklerinde eski-yeni değer audit kaydı yok — adli iz sürülemez (S-03).
5. Yedekleme script'i `.env`+`secrets`'i şifresiz kopyalıyor — KVKK ve kimlik bilgisi riski.
6. 6.70.3 UI değişikliği tam regresyon koşulmadan yayınlandı — 4 test + 2 E2E kırık.
7. Öğrenci kendi hesabıyla sisteme giremiyor; denetçi/rektörlük/ÖDB rolleri yok.
8. CI/CD hiç yok — testler yalnızca elle koşuluyor, insan hatasına açık.
9. PostgreSQL üzerinde hiçbir migration/test koşulmamış — production davranışı tamamen doğrulanmamış.
10. Production sunucusunun (`assess.dogus.edu.tr`) fiilen hangi kod sürümünü çalıştırdığı bu denetimden belirlenemedi.
