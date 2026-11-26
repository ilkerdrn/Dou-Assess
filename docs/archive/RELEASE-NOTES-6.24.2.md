# DOU Assess 6.24.2 — Workflow Order Fix

## Kritik bilgi mimarisi düzeltmesi
- Ana menünün ilk akışı artık kesin olarak **Program → Ders → Sınav → Öğrenci**.
- Genel Bakış ilk giriş olmaktan çıkarıldı; akademik akıştan sonra ikincil izleme ekranı olarak konumlandı.
- Program, Ders ve Öğrenci ayrı menü girişleri olarak Akademik Veri çalışma alanının ilgili görünümünü açar.
- İlk oturum açılışı Program adımıyla başlar.
- Akademik Veri varsayılan görünümü Programlar; ana CTA `+ Program`; hızlı işlem sekmeleri Program ile başlar.
- Dashboard yeni sınav aksiyonu eksik önkoşul varsa doğrudan Program veya Ders adımına yönlendirir.

Backend ve veritabanı şeması değişmez: `0020_assessment_intelligence`.
