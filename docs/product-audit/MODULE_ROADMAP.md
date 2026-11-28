# DOU Assess — Modül Yol Haritası

Her modül için: mevcut durum (doğrulanmış) · eksik · öncelik · bağımlılık · maliyet (tahmin: S ≤ 3 gün, M 1-2 hf, L 3-6 hf, XL > 6 hf). Ayrıntılı bulgular: `FEATURE_GAP_ANALYSIS.md`.

## 1. Mevcut modüller

| Modül | Durum | Eksik | Öncelik | Bağımlılık | Maliyet |
|---|---|---|---|---|---|
| Akademik yapı & Excel Veri Merkezi | ✅ | OBS/Core ile otomatik besleme; ağaç görünüm | P1 | Core/Connector | L |
| Öğrenme çıktıları & ÖÇ-PÇ matrisi | ✅ | ÖÇ şablonları, ısı haritası görünüm, dönem trendi | P2 | – | M |
| Soru bankası | ✅ | **Sürümleme**, dışa aktarma, Bloom önerisi | **P1** | migration | M |
| Sınav hazırlama / kağıt / OMR | ✅/🧪 | Saha doğrulaması, blueprint arayüzü | P1 | gerçek form seti | M |
| Puanlama (rubrik, kör, gruplar) | ✅ | Çift puanlayıcı + kalibrasyon | P2 | – | M |
| Sınav analizi | ✅ | Distraktör, SEM, dönem karşılaştırma | P2 | – | M |
| Program çalışma alanı / Program Değerlendirmesi / Kanıt Merkezi | ✅ | Beklenen-kanıt karşılaştırması | P2 | çerçeve içeriği (B11) | M |
| Kalite 360 / PUKÖ / akreditasyon | 🟡 | Başlatma sihirbazı, **resmî ölçüt doğrulaması**, test kapsamı %59 | **P1** | resmî belgeler | M |
| Değerlendirici Odası | ✅ | Çoklu değerlendirici yorum akışı genişletme | P3 | – | S |
| Anket / dolaylı ölçme | ✅ | Zamanlanmış dağıtım | P3 | e-posta | S |
| Bildirim + e-posta | ✅/🟡 | SMTP kurulumu | P1 | BT | S |
| Güvenlik / kimlik (OBS, Entra) | 🟡/❌ | Canlı OBS, çerez oturumu, kilitleme | **P0** | BT izni | S–M |
| Operasyon (yedek, zamanlayıcı) | ✅/🟡 | Geri yükleme tatbikatı, izleme/uyarı | P1 | – | M |

## 2. Birleştirilmesi önerilen modüller (menü sadeleşmesi)

| Şimdi ayrı | Birleşik yeni ad | Gerekçe |
|---|---|---|
| Ölçme Planı & Rubrik + Ödev/Proje ölçümü + Anket & Dolaylı Ölçüm | **Ölçme Araçları** (3 sekme) | Hepsi "doğrudan/dolaylı ölçme aracı"; yönetici menüsünde 3 yerine 1 |
| Program Çalışma Alanı + Öğrenci Karneleri + Ders Sonuçları | **Program Sonuçları** | Aynı soruya cevap: "program hedefe ulaşıyor mu?" |
| Kalite 360 + Program Değerlendirmesi + Kanıt Merkezi + Kurumsal Hazırlık + Ölçme Güvence | **Kalite & Akreditasyon** (sekmeli) | Aynı süreç zinciri (ölçüt → kanıt → değerlendirme → iyileştirme); 5 ayrı menü → 1 |
| Kullanıcılar + Güvenlik + Kabul + Pilot İşletim | **Yönetim** | Yalnız yöneticiye görünen |

## 3. Eklenmesi önerilen yeni modüller

| Modül | Amaç | Önceliği | Bağımlılık | Maliyet |
|---|---|---|---|---|
| **DOU Core + Connector** | Ortak akademik veri (dönem, ders, kişi, kayıt) ve kaynak bağdaştırıcıları | P1 | BT izni, mimari karar | L |
| **Rol Panoları** (rektörlük, ölçme uzmanı, dekan) | Role özel karar desteği | P2 | yeni roller (`authz.py`) | M |
| **Rapor Merkezi** | Tek katalog, zamanlanmış rapor | P2 | – | M |
| **Soru Kalitesi Merkezi** | Kötü maddeleri (düşük ayırt edicilik, çok kolay/zor) kuyruğa alır; revize/emekliye ayır | P2 | analiz verisi ✅ | M |
| **AI Asistan Merkezi** | Bloom/ÖÇ önerisi, soru taslağı, iyileştirme önerisi, cevap gruplama; **öneri ≠ karar** | P3 | KVKK onayı, sağlayıcı kararı | L |
| **Çok kiracılık + i18n** | Yeni üniversite/ülke | P2 (uluslararası P1) | ADR, metin sözlüğü | XL |
| **Erişilebilirlik & Tasarım Sistemi** | `DESIGN_SYSTEM.md` | P1–P2 | – | XL (kademeli) |

## 4. Yapay zekâ kullanım ilkesi (tüm modüller)
1. **Önerir, karar vermez:** AI çıktısı `proposed` durumunda saklanır; yetkili kullanıcı **kabul/düzenle/reddet** eder; kesin karar ayrı alan ve ayrı denetim kaydıdır.
2. **Veri minimizasyonu:** öğrenci kimliği gönderilmez; yalnız cevap metni/toplu istatistik.
3. **Açık/kapalı anahtar:** kurum ayarı + KVKK onayı olmadan kapalı.
4. **Açıklanabilirlik:** her öneri kaynağını (hangi veri/ölçüt) gösterir.
5. **Yerel öncelik:** mümkün olan her yerde kural/istatistik tabanlı yerel yöntem (cevap gruplama örneği).

## 5. Fazlar (özet; ayrıntı `FINAL_RECOMMENDATIONS.md`)
- **FAZ 1** (0-8 hf): P0 + P1 güvenlik/entegrasyon/erişilebilirlik temeli.
- **FAZ 2** (2-5 ay): akademik modüller + UX (sürümleme, panolar, tasarım sistemi 1-3. adım, rapor merkezi).
- **FAZ 3** (5-12 ay): AI asistan, çok kiracılık/i18n, uluslararası standartlar.
