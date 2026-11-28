# DOU Assess — Nihai Değerlendirme ve Öneriler

Bu belge `PRODUCT_AUDIT`, `UI_UX_AUDIT`, `COMPETITOR_ANALYSIS`, `FEATURE_GAP_ANALYSIS`, `SECURITY_AUDIT`, `INTEGRATION_AUDIT`, `USER_JOURNEY_AUDIT`, `DESIGN_SYSTEM`, `MODULE_ROADMAP` sonuçlarını özetler. Doğrulanmış bulgular o raporlarda kanıtlarıyla yer alır; burada yalnızca sonuç ve plan var.
Sınırlar: rakip ürünler **kullanılarak test edilmedi** (yalnız kaynak taraması); gerçek kullanıcı testi, sızma testi, yük testi ve gerçek OMR sahası yapılmadı.

---

## 1. Sorulara kesin cevaplar

**1. DOU Assess bugün hangi seviyede?**
Çalışan, testli (386 test, %79,9 backend kapsama) bir **kurum içi pilot ürünü**. Akademik çekirdek zincir tam; üretim/uluslararası ürün seviyesine **güvenlik (kimlik doğrulama), entegrasyon, erişilebilirlik, çok dillilik/çok kiracılık ve AI** katmanlarının eksikliği engel.

**2. Gerçekten çalışan modüller?**
Akademik yapı + Excel veri merkezi, ÖÇ/PÇ + matris (toplu düzenleme dâhil), soru bankası, sınav + kağıt + OMR (fixture ile), klasik puanlama (rubrik, kör, gruplar), itiraz portalı, sınav analizi (güçlük, ayırt edicilik, KR-20/Cronbach), program çalışma alanı, program değerlendirmesi, kanıt merkezi, değerlendirici odası, anket, bildirimler (+hedef altı uyarısı). 27 ekran 6 boyutta hatasız açıldı, yatay taşma yok.

**3. Eksik modüller?**
Soru sürümleme ve dışa aktarma, çift puanlayıcı/kalibrasyon, AI (Bloom, soru üretimi, öneri, doğal dil sorgu, anomali), dönem karşılaştırma raporu, rektörlük/ölçme uzmanı panoları, öğrenci hesabı, rapor merkezi, DOU Core/Connector, çok kiracılık, çok dillilik, koyu tema, erişilebilirlik beyanı.

**4. Rakiplerde olup bizde olmayanlar?** (kaynaklı bulgulara göre)
Soru sürümleme ve tam denetim izi (Questionmark), AI soru üretimi (Questionmark Author Aide), çift kör/moderasyonlu puanlama (Inspera), değerlendirici kalibrasyonu (Watermark), hazır akreditasyon şablonları ve LMS/SIS/SSO entegrasyonları (AEFIS/HelioCampus), QTI/LTI standartları (TAO), risk öngörü panoları (D2L Performance+), çok dillilik. Bizde olup incelenen kaynaklarda öne çıkmayanlar: optik okuma, öğrenci itiraz akışı, dış değerlendirici odası, YÖKAK/MÜDEK/MEDEK'e özgü yapı.

**5. UI/UX'in en büyük sorunları?**
(1) **Kontrast:** 333 düğüm WCAG AA ihlali (en kötü 2,38:1). (2) **Tasarım sistemi yok:** 1.194 renk, 48 yazı boyutu, 2.767 `!important`. (3) **Yönetici menüsü kalabalık** (27 sayfa) ve bölümler arası kopukluk. (4) Rol panoları ve rapor merkezi eksik. (5) Etiketsiz alanlar ve sekme rolü hatası.

**6. Hangi ekranlar yeniden tasarlanmalı?**
Ana panolar (rol başına), Kalite & Akreditasyon (tek sekmeli çalışma alanı), ÖÇ-PÇ matrisi (ısı haritası), Başarı analizi (madde analizi görselleştirmesi), Rubrik (görsel tablo), Rapor merkezi (yeni). Ayrıntı: `UI_UX_AUDIT` §2.

**7. Hangi modüller birleştirilmeli?**
Ölçme Araçları (3→1), Program Sonuçları (3→1), Kalite & Akreditasyon (5→1), Yönetim (4→1). `MODULE_ROADMAP` §2.

**8. Hangi yeni modüller eklenmeli?**
DOU Core + Connector, Rol Panoları, Rapor Merkezi, Soru Kalitesi Merkezi, AI Asistan Merkezi, çok kiracılık + i18n, tasarım sistemi.

**9. Yapay zekâ nerelerde kullanılmalı?**
Önce **yerel/kural tabanlı** (cevap gruplama ✅, Bloom fiil sözlüğü, anomali z-skoru), sonra AI: Bloom ve ÖÇ eşleme **önerisi**, soru taslağı, hedef altı için gerekçeli iyileştirme önerisi, eksik kanıt tespiti. İlke: **öneri ≠ karar**, insan onayı kayıtlı, kişisel veri gönderilmez, kurum ayarıyla kapalı varsayılan.

**10. Proliz entegrasyonunda ne eksik?**
Canlıda **sunucu adresinin Proliz izin listesinde olmaması** (IIS 403; VPN'li bilgisayardan 200 → kanıtlı). Sonrasında: gerçek sicille giriş doğrulaması, zamanlanmış senkron, uzlaştırma raporu, **DOU Core/Connector** katmanı.

**11. Güvenlik ve ölçeklenebilirlik sorunları?**
**P0:** canlı sunucu kimliksiz pilot modunda (başlıksız istek = admin). **P1:** hız sınırlama pilotta kapalı ve süreç belleğinde, giriş kilitleme yok, öğrenci bağlantıları süresiz, yedek geri yükleme sınanmadı, yük testi yok. **P2:** denetim kaydı DB düzeyinde değiştirilemez değil, tek kiracı, jeton depolaması, `main.py` ve `app.js` monolit. Olumlu: 449 uçtan 430'u kimliksiz reddediyor, ham SQL yok, katı CSP, öğrenci verisi maskeleme, HMAC jeton.

**12. Uluslararası rekabet için gerekenler?**
i18n (en az İngilizce), çok kiracılık, erişilebilirlik beyanı (WCAG 2.2 AA / VPAT), standart entegrasyonlar (SSO, LTI, QTI), çerçeve kataloğunun **yapılandırılabilir** genişlemesi (yalnız Türk kuruluşları değil ABET/AACSB/ESG), kurulum ve veri yerleşimi seçenekleri, bağımsız güvenlik testi, SLA/izleme, hukuki paket (KVKK/GDPR).

---

## 2. Üç aşamalı yol haritası

### FAZ 1 — Temel ürünün sağlamlaştırılması (0-8 hafta)
Amaç: güvenli, doğrulanmış, entegre pilot.
| # | İş | Öncelik | Efor | Kabul kriteri |
|---|---|---|---|---|
| 1 | **Canlıyı kimlik arkasına al:** nginx IP izin listesi (hemen) → OBS girişi (BT izni sonrası) | P0 | S + M | Başlıksız `/api/auth/me` → 401 |
| 2 | BT izni: sunucu → Proliz; 5 uç `200`; gerçek hocayla giriş ve senkron | P0 | S | `IntegrationSyncRun` başarılı, yinelenen kayıt yok |
| 3 | Rate limit + giriş kilitleme; öğrenci bağlantısına süre | P1 | M | 429 testi; süresi dolan bağlantı 401 |
| 4 | Yedek **geri yükleme** otomasyonu ve izleme/uyarı | P1 | M | Aylık otomatik geri yükleme raporu |
| 5 | **Erişilebilirlik acil paket:** kontrast tokenları, etiketsiz select, sekme rolü | P1 | M | axe `critical`=0, `color-contrast` ≤ 20 |
| 6 | Resmî ölçüt doğrulaması (MÜDEK 3.0/3.1 farkı, YÖKAK, MEDEK) | P1 | M | Her çerçeve satırı resmî metne referanslı |
| 7 | Soru **sürümleme** (`question_versions`) | P1 | M | Sınavda kullanılan sürüm sabit; karşılaştırma ekranı |
| 8 | OMR saha doğrulaması (50 gerçek form) ve kapsama artırma | P1 | M | ≥ %99 okuma doğruluğu raporu |
| 9 | Yük testi (500 öğrenci × 5 sınav) | P1 | M | p95 < 2 sn ana sayfalar |
| 10 | SMTP kurulumu (e-posta uyarıları) | P1 | S | Hedef altı uyarı e-postası alınır |

### FAZ 2 — Akademik modüller ve kullanıcı deneyiminin tamamlanması (2-5 ay)
| # | İş | Öncelik | Efor |
|---|---|---|---|
| 1 | Menü birleştirme (4 grup) + rol panoları (hoca, bölüm, kalite, yönetici, rektörlük) + yeni roller | P2 | L |
| 2 | Tasarım sistemi adım 1-3 (token → kontrast → bileşen sınıfları), `!important` < 500 | P2 | L |
| 3 | DOU Core + Connector (Proliz arayüzü, zamanlanmış senkron, uzlaştırma raporu) | P1 | L |
| 4 | Akreditasyon başlatma sihirbazı + "beklenen kanıt" karşılaştırması | P2 | M |
| 5 | Çift puanlayıcı + kalibrasyon + uyuşmazlık kuyruğu | P2 | M |
| 6 | Dönem karşılaştırma/trend raporları, Rapor Merkezi | P2 | M |
| 7 | Soru Kalitesi Merkezi, distraktör ve SEM analizi | P2 | M |
| 8 | Öğrenci girişi (OBS öğrenci) ve kendi ÖÇ gelişimi | P2 | M |
| 9 | `main.py` ve `app.js` modülerleştirme + JS birim testi + CI'da axe | P2 | L |

### FAZ 3 — AI destekli ileri analiz ve uluslararası seviye (5-12 ay)
| # | İş | Öncelik | Efor |
|---|---|---|---|
| 1 | **AI Asistan Merkezi:** Bloom/ÖÇ önerisi, soru taslağı, iyileştirme önerisi (öneri ≠ karar, KVKK anahtarı) | P3 | L |
| 2 | Anomali tespiti (başarı sıçraması, cevap deseni benzerliği) | P2–P3 | M |
| 3 | Doğal dille salt-okunur sorgu (yetki süzgeçli) | P3 | L |
| 4 | Çok kiracılık (RLS/şema-başı) + i18n (en/tr) | P2→P1 (uluslararası) | XL |
| 5 | LTI 1.3 / SSO / QTI; ABET-AACSB-ESG çerçeve katalogları | P3 | L–XL |
| 6 | Erişilebilirlik beyanı (VPAT), bağımsız sızma testi, SLA ve izleme | P2 | M |
| 7 | Koyu tema, gelişmiş kişiselleştirme, IRT (isteğe bağlı) | P3 | M–XL |

---

## 3. Bu hafta yapılabilecek ilk 5 iş (en yüksek etki / en düşük risk)
1. **nginx'te kurumsal IP izin listesi** (P0, S) — kimliksiz erişimi hemen daraltır.
2. **BT'ye Proliz izin talebi** (hazır metin var) — OBS girişini açar.
3. **Kontrast tokenları + 5 etiket düzeltmesi** (P1, M) — axe ihlallerinin çoğunu kapatır, görsel risk düşük.
4. **PR #12'yi birleştirip sunucuya al** — toplu matris, cevap grupları, hedef altı uyarı.
5. **Yük testi senaryosu yazmak** (P1, M) — ölçeklenebilirlik varsayımını ölçüme çevirir.

## 4. Kaynaklar
Rakip özellikleri için kaynaklar `COMPETITOR_ANALYSIS.md` içinde ürün ürün bağlantılıdır. Türkiye akreditasyonu için: [EMO — MÜDEK 3.0 ölçütleri bülteni (ikincil kaynak)](https://www.emo.org.tr/ekler/7850a31fe1a4fb6_ek.pdf?dergi=1344) · [YÖKAK 2024 Durum Raporu](https://www.yokak.gov.tr/documents/StatusReports/2024%20Y%C4%B1l%C4%B1%20Y%C3%BCksek%C3%B6%C4%9Fretim%20De%C4%9Ferlendirme%20ve%20Kalite%20G%C3%BCvencesi%20Durum%20Raporu.pdf) · [YÖKAK Uluslararası Kurumsal Akreditasyon Kılavuzu v1.0a](https://www.yokak.gov.tr/documents/international-doc/EN_INTERNATIONAL_INSTITUTIONAL_ACCREDITATION_PROGRAM_GUIDE_v.1.0a.pdf). **Uyarı:** güncel bağlayıcı ölçütler için mudek.org.tr ve yokak.gov.tr resmî metinleri esas alınmalıdır; bu denetimde resmî ölçüt metni satır satır karşılaştırılmadı.
