# DOU Assess — Tasarım Sistemi (Öneri v1)

**Durum:** Öneri. Mevcut uygulama bu sisteme **henüz uymuyor** (bkz. `UI_UX_AUDIT.md` §1.3: 1.194 renk, 48 yazı boyutu, 33 köşe yarıçapı, 2.767 `!important`). Bu belge bir **hedef** ve **kademeli göç planıdır**; mevcut marka kimliği (kırmızı `#b3132b`, Inter) korunur.
Tüm sayısal kontrast değerleri hesaplanmıştır (WCAG 2.x göreli parlaklık formülü), tahmin değildir.

Yaklaşım: modern kurumsal SaaS · akademik · sade · güven veren · yüksek okunabilirlik.

---

## 1. Renk (tokenlar)

### Marka ve anlam renkleri
| Token | Değer | Beyaz üzerinde | Kullanım |
|---|---|---|---|
| `--brand-600` | `#b3132b` | **6,90:1** ✓ | Birincil düğme, bağlantı, aktif öğe |
| `--brand-700` | `#8f0e21` | 9,32:1 ✓ | Basılı/hover |
| `--brand-50` | `#fdf1f3` | – | Seçili satır, rozet zemini |
| `--ink-900` | `#20242a` | 15,59:1 ✓ | Başlık, gövde |
| `--ink-700` | `#475467` | 7,1:1 (`#f4f6f8` üstünde) ✓ | İkincil gövde |
| `--ink-600` | `#5b6676` | **5,82:1** ✓ (5,37 `#f4f6f8`, 5,18 `#eef2f7`) | **Yardımcı metin (mevcut `--muted` yerine)** |
| `--success-700` | `#0f7a4a` | **5,38:1** ✓ | Başarı metni/rozeti (mevcut `#138a55` = 4,38:1 ✗) |
| `--warning-700` | `#b45309` | 5,02:1 ✓ | Uyarı metni |
| `--danger-700` | `#9a3412` | 7,31:1 ✓ | Hata metni (kırmızı marka ile karışmasın diye turuncu-kırmızı) |
| `--info-700` | `#1d4ed8` | 6,7:1 ✓ | Bilgi |

**Kural:** metin ≥ 4,5:1, büyük metin (≥ 18,66 px kalın / 24 px) ≥ 3:1, kontrol kenarlığı/odak halkası ≥ 3:1 (WCAG 2.2 SC 1.4.11).
**Yasak tonlar (mevcut, geçersiz):** `#98a2b3` (beyazda 2,57:1), `#8d96a0`, `#7b848e`, `#697584` (zeminde 4,29:1) metin için kullanılamaz; yalnızca süs/devre dışı bırakılmış öğede.

### Nötr ölçek
`--gray-0 #ffffff` · `--gray-50 #f7f8fa` · `--gray-100 #f4f6f8` (sayfa zemini) · `--gray-200 #e3e7ec` (kenarlık) · `--gray-300 #cdd3da` · `--gray-900 #20242a`.

### Veri görselleştirme paleti (renk körü güvenli)
Sıralı (başarı yüzdesi): tek ton ailesi `brand-50 → brand-600`. Ayrışan: hedef altı `danger-700` / hedefte `success-700`, orta `warning-700`; **renge ek olarak simge/etiket** (✓ ⚠ ✕) ve desen. Kategorik: en çok 6 renk; ayrıca doğrudan etiketleme (lejant yerine).

---

## 2. Tipografi
- **Aile:** Inter (mevcut) + `"Segoe UI", Arial, sans-serif` yedek. Rakamlarda `font-variant-numeric: tabular-nums` (tablo/KPI).
- **Ölçek (rem, 16 px taban):** `12 · 14 · 16 · 18 · 20 · 24 · 30` px (7 basamak; **mevcut 48'in yerine**).

| Rol | Boyut / ağırlık / satır |
|---|---|
| Sayfa başlığı (H1) | 24 / 700 / 32 |
| Bölüm başlığı (H2) | 20 / 600 / 28 |
| Kart başlığı (H3) | 16 / 600 / 24 |
| Gövde | 14 / 400 / 22 |
| Yardımcı / etiket | 12 / 600 / 16, `ink-600` |
| KPI sayısı | 30 / 700 / 36, tabular |
- Minimum metin 12 px; dokunma yüzeylerinde 14+.

## 3. Boşluk, ızgara, köşe, gölge
- **Boşluk (4 px taban):** `4 · 8 · 12 · 16 · 24 · 32 · 48`. Kart iç boşluğu 16 (mobil) / 24 (masaüstü).
- **Izgara:** 12 sütun, kapsayıcı maks. 1440 px, yan boşluk 16 (mobil) / 24 (tablet) / 32 (masaüstü). Kırılımlar: `sm 640 · md 768 · lg 1024 · xl 1440`.
- **Köşe yarıçapı:** `--r-sm 6` (girdi) · `--r-md 10` (düğme/kart) · `--r-lg 16` (modal/çekmece) · `--r-pill 999`. (**mevcut 33 değer → 4**)
- **Gölge:** `--sh-1` kart `0 1px 2px rgba(16,24,40,.06)` · `--sh-2` yükselmiş `0 8px 24px rgba(16,24,40,.10)` · `--sh-3` modal `0 24px 60px rgba(16,24,40,.18)`.
- **Hareket:** 120-200 ms; `prefers-reduced-motion` ile kapat.

## 4. Bileşenler (her biri: durumlar + davranış)

| Bileşen | Varyantlar | Zorunlu durumlar / kurallar |
|---|---|---|
| **Düğme** | birincil, ikincil (çerçeveli), üçüncül (metin), tehlike; boyut S/M/L (min. 40 px yükseklik, dokunmada 44) | hover, `:focus-visible` (2 px halka `brand-600`, 3:1), disabled, yükleniyor (dönen simge + `aria-busy`) |
| **Girdi / select / textarea** | normal, hata, başarılı | **görünür etiket zorunlu** (placeholder etiket değildir); yardım metni; hata `aria-describedby` + `role="alert"`; zorunlu `*` etiket yanında |
| **Tablo** | yoğun / rahat; sıralanabilir; sayfalı | `<th scope>`, sabit başlık, mobilde yatay kaydırma kutusu **odaklanabilir** (`tabindex=0`, `role=region`, `aria-label`), boş/yükleniyor satırı |
| **Kart / KPI kartı** | genel, KPI (değer + fark ▲▼ + sparkline), uyarı | KPI'da **birim ve dönem** görünür; renk tek başına anlam taşımaz |
| **Rozet / durum** | nötr, başarı, uyarı, hata, bilgi | metin + simge; durum adları Türkçe sözlükten (`Taslak, Hazır, Puanlanıyor, Onaylı…`) |
| **Modal / Çekmece (drawer)** | merkez modal, sağ çekmece (genişlik `min(520px,92vw)`) | odak tuzağı, `Esc` kapatır, kapanınca tetikleyiciye dön, arka plan `inert`; **yatay kaydırma çubuğu olmaz** |
| **Toast** | başarı, hata, bilgi | `role="status"/"alert"`, 5 sn (hata kalıcı), kapatma düğmesi, tek seferde en fazla 3 |
| **Sekmeler** | yatay, mobilde kaydırılabilir | `role="tablist"` içinde **yalnız** `role="tab"`; ok tuşlarıyla gezinme |
| **Boş durum** | ilk kullanım, filtre sonucu yok, yetki yok | tek cümle neden + tek ana eylem |
| **Yükleniyor** | iskelet (skeleton), ilerleme çubuğu, dönen simge | >300 ms'de göster; içerik yüklenince yer değiştirmesin |
| **Hata durumu** | alan, sayfa, sistem | ne oldu + ne yapılır + (varsa) istek kodu; teknik ayrıntı gizli |
| **Grafik** | çubuk, çizgi (trend), ısı haritası (ÖÇ-PÇ), radar (ÖÇ profili) | eksen etiketi, değer etiketi, **tablo alternatifi**, `aria-label` özeti, kontrast ≥ 3:1 |
| **İkon** | tek set (çizgi stili, 20 px) | yalnız-simge düğmeye `aria-label`; **harf/emoji simge kullanılmaz** (şu an alt gezinmede emoji — geçici) |

## 5. Düzen kalıpları
1. **Sayfa iskeleti:** sol gezinme (248 px, daraltılabilir) + üst çubuk (breadcrumb, arama `Ctrl K`, bildirim, kullanıcı) + içerik.
2. **Rol panosu:** 3 şerit (Bugün / Göstergeler / Riskler). Bkz. `UI_UX_AUDIT.md` §2.
3. **Liste–detay:** sol liste + sağ detay (masaüstü), mobilde ayrı ekran.
4. **Sihirbaz:** adım çubuğu + sabit alt eylem çubuğu (Geri / Kaydet / İleri).
5. **Sayfa başlığı:** başlık + tek cümle açıklama + en çok 2 eylem.

## 6. Duyarlı davranış
`≥1440` tam düzen · `1024-1439` yan panel daralır · `768-1023` gezinme simge çubuğu, tablolar kaydırma kutusu · `<768` hamburger menü + alt gezinme (en çok 5 öğe), tablo → kart listesi, çekmece tam ekran · `<=360` tek sütun, 16 px yan boşluk. **Kabul kriteri:** sayfa düzeyinde yatay kaydırma **0**, hedef boyutu ≥ 24 px (tercihen 44).

## 7. Erişilebilirlik kabul listesi (WCAG 2.2 AA)
Kontrast (1.4.3, 1.4.11) · yeniden akış 320 px (1.4.10) · odak görünür ve örtülmez (2.4.7, 2.4.11) · hedef boyutu (2.5.8) · klavye (2.1.1) · etiket/ad (4.1.2, 3.3.2) · hata önerisi (3.3.3) · durum mesajları (4.1.3) · ekran okuyucuda tablo başlıkları.
**CI kapısı:** `axe-core` her PR'da ana ekranlarda çalışsın; `critical` = 0, `serious` düşüş eğilimi.

## 8. Göç planı (mevcut CSS'i bozmadan)
1. **Token katmanı:** `tokens.css` (yukarıdaki değişkenler) → mevcut `:root` değişkenleri bu tokenlara eşlenir (görsel değişiklik yok).
2. **Kontrast düzeltmesi:** yasak tonları token'a çevir (en çok etki: 333 düğüm). *Kabul: axe `color-contrast` ≤ 20.*
3. **Bileşen sınıfları:** `.btn`, `.field`, `.table`, `.card`, `.badge`, `.drawer` — yeni ekranlar yalnız bunları kullanır; eski ekranlar sayfa sayfa taşınır, her taşımada `!important` silinir (hedef: < 500).
4. **Simge seti ve grafik bileşenleri.**
5. **Görsel regresyon:** Playwright ekran görüntüsü karşılaştırması (ana 10 ekran × 3 boyut).
Efor: **XL** (6-10 hafta, kademeli); ilk iki adım **M** ve düşük risklidir.
