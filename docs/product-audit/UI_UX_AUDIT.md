# DOU Assess — UI/UX Denetimi

**Yöntem:** Uygulama demo verisiyle ayağa kaldırıldı; 27 ekran × 6 ekran boyutu (1920, 1440, 1024, 768, 390, 360 px) Playwright ile gezildi; **axe-core 4.10** ile WCAG 2.0/2.1/2.2 A-AA kuralları (1440 ve 390 px) çalıştırıldı; CSS ölçüldü. Ekran görüntüleri: yerel çalışma klasöründe (rapora gömülü değil).
Etiketler: **[DOĞRULANDI]** ölçüldü · **[GÖZLEM]** ekranda görüldü, ölçülmedi · **[VARSAYIM]**.

---

## 1. Ölçülmüş sonuçlar

### 1.1 Duyarlı tasarım (responsive)
- [DOĞRULANDI] 27 ekranın hiçbirinde **sayfa düzeyinde yatay taşma yok**, 6 boyutun hiçbirinde (1920 → 360). Geniş tablolar kendi kaydırma kutusunda.
- [DOĞRULANDI] JS hatası (`pageerror`): 48 ekran yüklemesinde (24 sayfa × masaüstü/telefon) **0**.
- [DOĞRULANDI] 768 px ve altında dokunma hedefi < 24×24 px olan öğe: yalnızca Soru Bankası ve İçe Aktarma sayfalarında 1'er adet (WCAG 2.2 SC 2.5.8).
- [GÖZLEM] Telefon alt gezinme çubuğunda harf simgeleri vardı (D, ?, S, P); PR #12'de emojiyle değiştirildi (ayrı simge sistemi hâlâ yok).

### 1.2 Erişilebilirlik (axe, WCAG 2.2 AA hedefi)
| Kural | Etki | Düğüm (1440 px / 390 px) | Not |
|---|---|---|---|
| `color-contrast` | serious | **333 / 260** | 27 ekranın çoğunda. En sık çiftler: `#697584` / `#f7f4f5` = 4,29:1; `#98a2b3` / `#f5f6f8` = **2,38:1**; `#8d96a0` / `#f7f8fa` = 2,82:1; `#98a2b3` / `#fff` = 2,57:1. Gövde/alan metni ≥ 4,5:1 olmalı |
| `select-name` | critical | 5 / 5 | `#examCourseFilter`, `#examTypeFilter`, `#examStatusFilter`, `#feedbackStatusFilter` (görünür etiketi/aria-label'ı yok), `#bankLoSelect` (sr-only çoklu seçim) |
| `aria-required-children` | critical | 1 / 1 | `quality360` sekmeleri: `role="tablist"` içinde `role="tab"` olmayan çocuklar |
| `scrollable-region-focusable` | serious | – / 2 | Kurumsal Hazırlık ve İçe Aktarma: klavyeyle odaklanamayan kaydırma kutusu |

Kod düzeyi: `:focus-visible` kuralı yalnızca 5 yerde; `prefers-reduced-motion` var (4); atlama bağlantısı (skip link) var; `aria-live` 7 yerde; `img` etiketlerinin hepsinde `alt` var.
**Eksik/doğrulanmadı [VARSAYIM]:** ekran okuyucuyla (NVDA/VoiceOver) manuel gezinme, klavye-yalnız tam akış testi, tablo başlık ilişkileri (`scope`), form hata bildirimlerinin `aria-describedby` ile bağlanması, odak yönetimi (drawer/modal açılış-kapanış), 200% yakınlaştırma.

### 1.3 Tasarım sistemi sağlığı (CSS ölçümü)
| Ölçüt | Değer | Yorum |
|---|---|---|
| Ayrı onaltılık renk | **1.194** | Palet yok; her ekran kendi tonunu kullanıyor |
| Tanımlı CSS değişkeni | 137 | Var ama tutarlı kullanılmıyor |
| Farklı `font-size` (px) | **48** | Tipografi ölçeği yok |
| Farklı `border-radius` | **33** | |
| `!important` | **2.767** | Katmanlı "hotfix" üzerine hotfix; bakım/regresyon riski |
| Medya sorgusu | 153 | Parçalı |
| Koyu tema | yok | |
| Grafik kütüphanesi | yok | Görselleştirme HTML/CSS çubuklarıyla elle |
| Tek stil dosyası | 2.198 satır + `evaluator.css`, `login-gate-fix.css` | |

Marka tokenları (`--red:#b3132b`, `--ink:#20242a`, `--muted:#6b7280`, `--ok:#138a55`) iyi bir başlangıç ama **iki token kontrast kuralını geçmiyor**: `--muted` (#6b7280) `--bg` (#f4f6f8) üzerinde **4,46:1**, `--ok` (#138a55) beyaz üzerinde **4,38:1**.

---

## 2. Ekran ekran değerlendirme (gözlem + ölçüm)

Her ekran için: **Sorun → Yeni yaklaşım → Mobil**.

| Ekran | Mevcut sorun [GÖZLEM] | Önerilen yaklaşım | Mobil |
|---|---|---|---|
| **Giriş** | Pilot modda kullanıcı **seçim listesi** (kimlik doğrulaması yok); OBS modunda kullanıcı adı/şifre alanı | Tek odaklı kart: kurumsal oturum (OBS) birincil, pilot seçimi yalnız geliştirme bayrağıyla; "Şifrem OBS şifremdir, kaydedilmez" güven notu | Tam ekran, tek sütun |
| **Ana sayfa (dashboard)** | Rol sadeleştirmesi var, ama yönetici için üstte "Pilotun işletim akışı" metni; "Şimdi ne yapmalıyım" kutusu akreditasyon kriteri öneriyordu (PR #12'de kurulum görevine çevrildi) | **Rol başına 3 şerit:** (1) Bugün yapılacaklar, (2) Durum göstergeleri (4 KPI + 1 trend), (3) Riskler/öneriler. Hoca: derslerim + bekleyen puanlama; Kalite: kanıt eksikleri + PUKÖ; Yönetici: kurulum durumu | KPI'lar yatay kaydırmalı kart şeridi |
| **Akademik yapı** | Tek sayfada program/ders/öğrenci listesi + sağ çekmece formu; çekmece yatay çubuğu vardı (düzeltildi PR #10) | Sol: ağaç (kurum → fakülte → program → ders); sağ: detay. Toplu içe aktarma tek sihirbaz | Ağaç → tam ekran liste |
| **Öğrenme çıktıları** | Kapalı bölümler başlıktan önce geliyordu (PR #12'de düzeltildi); 6 KPI + iki form + iki katalog + matris aynı sayfada | Sekmeler: Özet · Katalog · Matris · Talepler · Eşikler | Sekme çubuğu kaydırılabilir |
| **ÖÇ-PÇ matrisi** | Hücrede `<select>`; 4×4 üstünde okunur ama 15×12'de zor; toplu düzenleme yoktu (eklendi) | Isı haritası hücreleri (renk = katkı), tıkla-düzenle, sütun/satır toplamı, boş hücre uyarısı | Yalnızca okunur özet + "tam ekran aç" |
| **Soru bankası** | Güçlü ama yoğun; düzenleyici çekmece; sürüm geçmişi yok | Liste + yan önizleme; filtre çipleri (ÖÇ, Bloom, zorluk, durum); sürüm karşılaştırma | Filtre alt sayfası |
| **Sınav yönetimi** | 5 adımlı sihirbaz iyi; filtre `select`'leri etiketsiz (axe) | Adım çubuğu + sabit alt eylem çubuğu; hazırlık kontrol listesi sağda | Adımlar dikey akordeon |
| **Rubrik** | Ölçme aracı sayfasında gömülü; "Rubrik taslağı" metin alanı (`K1 | etiket | puan`) | Görsel rubrik tablosu (kriter × düzey), sürükle-bırak sıra, şablon kütüphanesi | Kriter başına kart |
| **Başarı analizi** | Boş açılıyordu (PR #12'de son sınav otomatik); grafikler elle çubuk | Madde analizi tablosu + distraktör grafiği + ÖÇ radar; "neden riskli?" açıklama paneli | Tek grafik/ekran |
| **Akreditasyon / Kalite360** | Çok sekme, sekme rolü hatası (axe); çok bilgi yoğunluğu | Ölçüt ağacı + ilerleme halkası + "eksik kanıt" kuyruğu; PUKÖ panosu (Kanban) | Ağaç → liste |
| **Kanıt yönetimi** | Kanıt Merkezi iyi; sürümleme/sahiplik görünürlüğü sınırlı [VARSAYIM] | Kanıt kartı: sahibi, son güncelleme, ölçütler, durum rozeti | Kart listesi |
| **AI analiz merkezi** | **Yok** (AI öneri alanı tek tek ekranlarda dağınık veya kapalı) | Tek "Öneriler" kutusu: kaynak + güven + "kabul et / reddet / düzenle" + insan onayı kaydı | Alt sayfa |
| **Raporlama** | Rapor uçları çok (Excel/Word/PDF) ama tek "Rapor Merkezi" yok | Rapor kataloğu: amaç → dönem/program → format; zamanlanmış rapor | Katalog listesi |
| **Sistem yönetimi** | Kullanıcılar, güvenlik, kabul, pilot işletim ayrı sayfalar | Tek "Yönetim" bölümü, sol alt gezinme, durum sağlığı kartı | Liste |

---

## 3. Gezinme

- [DOĞRULANDI] Yönetici görünümünde 27 sayfa/menü; hoca görünümü sadeleştirilmiş (rol bazlı CSS/JS). Kalabalık sorunu esas olarak **yönetici** rolünde.
- [GÖZLEM] Global arama var (`Ctrl K`); breadcrumb var ("DOU ASSESS / İZLEME / GENEL BAKIŞ"); hızlı işlem düğmeleri ana sayfada.
- Öneri: menüyü **5 gruba** indir — *İş (Ders & Sınav)*, *Sonuçlar*, *Çıktılar*, *Kalite & Akreditasyon*, *Yönetim*; "Ölçme Planı & Rubrik", "Anket & Dolaylı Ölçüm", "Entegrasyonlar" isimlerini iş diline çevir ("Ödev/Proje Ölçümü", "Anketler", "Veri Aktarımı").

## 4. Boş / yüklenen / hata durumları
- [GÖZLEM] Boş durum kartları var (ör. "Bir sınav seçin"); yükleme göstergesi çoğunlukla düz metin ("İşleniyor…"); **iskelet (skeleton) yükleme yok**. Hata mesajları Türkçe ve anlaşılır; teknik kod gösterilmiyor.

## 5. Bu denetimde düzeltilenler (kanıt: PR'lar)
#10 çekmece yatay kaydırma · #11 kalan İngilizce etiketler · #12 yönetici kurulum görevi, otomatik analiz, bölüm sırası, mobil simgeler, toplu matris.
**Henüz düzeltilmeyenler:** renk kontrastı (333 düğüm), 5 etiketsiz `select`, sekme rol hatası, odaklanamayan kaydırma kutuları, tasarım sistemi dağınıklığı → `DESIGN_SYSTEM.md` ve `FEATURE_GAP_ANALYSIS.md` (P1-P2).
