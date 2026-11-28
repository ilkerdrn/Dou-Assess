# DOU Assess — Kullanıcı Akışı Denetimi

**Yöntem ve sınır:** Akışlar kod, API testleri ve demo veriyle gezilen ekranlardan çıkarıldı. **Gerçek kullanıcılarla kullanılabilirlik testi yapılmadı**; "sürtünme" maddeleri gözlem/çıkarımdır [GÖZLEM], ölçülmüş süre/tıklama sayısı değildir. Durum: ✅ uçtan uca var · 🟡 kısmen · ⛔ yok. "Test" sütunu API düzeyinde doğrulamayı belirtir.

---

## S1. Kalite koordinatörü yeni programın akreditasyon sürecini başlatır — 🟡
- **Amaç:** Program için çerçeve (MÜDEK/MEDEK/…) seç, başvuru dönemi aç, ölçütleri ve kanıt sorumlularını ata.
- **Adımlar (mevcut):** Kalite & Akreditasyon → Kalite 360 → çerçeve seç → başvuru oluştur (`POST /api/compliance/applications`) → ölçüt/kanıt isteği ve sorumlu → Kanıt Merkezi.
- **Sürtünme [GÖZLEM]:** çok sekme (Kalite 360 tek sayfada ~6.700 karakter metin); "başlangıç sihirbazı" yok; çerçeve sürüm içeriği resmî metinle doğrulanmadı (FEATURE_GAP B11).
- **Eksik:** adım adım **"Akreditasyon başlat" sihirbazı** (çerçeve → kapsam → takvim → sorumlular → ilk kanıt listesi).
- **API:** var (`compliance_api`, `quality360_api`); kapsama %59 (düşük).
- **Başarı kriteri:** koordinatör 15 dakikada program için başvuru, takvim ve sorumlu atamasını tamamlar; sistem eksik kanıt listesini otomatik üretir.

## S2. Bölüm başkanı program çıktılarının gerçekleşmesini inceler — ✅
- **Adımlar:** Program Çalışma Alanı → program seç → Karar özeti (ölçüm kapsamı %, PÇ ortalaması, riskli ders, açık PUKÖ) → "Öncelikli dersleri aç".
- **Sürtünme:** dönem karşılaştırması yok (FEATURE_GAP B8); PÇ trendi tek dönem.
- **Eksik:** dönemler arası ÖÇ/PÇ **trend grafiği**, hedef altı için tek tıkla PUKÖ aksiyonu başlatma (API var: `assessment_plan_api`, arayüz bağı kısmen).
- **Test:** analitik testleri ✅.
- **Başarı:** bölüm başkanı 3 tıkta hedef altı PÇ'nin hangi ders/soruya dayandığını görür.

## S3. Akademisyen ders öğrenme çıktıları oluşturur — ✅
- **Adımlar:** Çıktı Yönetimi → ders seç → "Yeni Öğrenim Çıktısı" (kod, açıklama, hedef %) → matriste PÇ'ye katkı (1-5; **toplu düzenleme** eklendi).
- **Sürtünme:** kurum "ÖÇ değişiklik onayı" açıksa değişiklik talebe düşer (`pending_approval`), kullanıcı bunu mesajdan anlıyor; talepler sayfanın sonunda (PR #12 ile alta alındı) bulunması sürpriz olabilir.
- **Eksik:** ÖÇ şablon kütüphanesi (program bazlı hazır ÖÇ önerisi), Bloom fiil önerisi (AI/kural).
- **Test:** ✅ (`test_674`, `test_678`).
- **Başarı:** 6 ÖÇ + eşleme 10 dakikada; hatalı katkı değeri kabul edilmez (1-5 doğrulaması ✅).

## S4. Akademisyen soru bankasından sınav hazırlar — ✅
- **Adımlar:** Sınav Hazırla → yeni sınav (sihirbaz 5 adım) → bankadan soru seç → ÖÇ kapsamı ve puan toplamı kontrolü → "Sınavı hazır durumuna al".
- **Sürtünme:** puan toplamı 100 olmadan "hazır" yapılamıyor (doğru) ama düzeltme düğmesi ("100'e ölçekle") yalnız hazırlık raporunda; filtre `select`'leri etiketsiz (erişilebilirlik).
- **Eksik:** **sınav blueprint** (ÖÇ × Bloom × zorluk hedef tablosuna göre otomatik soru önerisi) — model var (`assessment_blueprints`), arayüz sınırlı [VARSAYIM]; soru **sürüm geçmişi** (B1).
- **Test:** ✅ sınav durum makinesi, OMR kağıdı.
- **Başarı:** 10 soruluk sınav 15 dakikada; ÖÇ kapsamı eksikse sistem uyarır (✅ hazırlık kontrolü).

## S5. Yapay zekâ soruların Bloom seviyelerini analiz eder — ⛔
- **Mevcut:** Bloom düzeyi elle seçilen alan (`bloom_level`); sistemde sınıflayıcı yok.
- **Eksik:** soru metninden **Bloom önerisi** (kural tabanlı fiil sözlüğü Türkçe/İngilizce + isteğe bağlı AI), önerinin **insan onayı** ile kaydı, onay geçmişi.
- **API:** yeni (`POST /api/questions/{id}/bloom-suggestion`); veri modeli: öneri ayrı, **kesin değer ayrı** (AI önerisini kesin karardan ayırma ilkesi).
- **Başarı:** 100 sorunun %80'inde öneri uzman etiketiyle uyuşur (ölçülecek); hiçbir öneri onaysız kesinleşmez.

## S6. Sistem sınav sonuçlarından soru analizleri oluşturur — ✅
- **Adımlar:** Sınav Analizi (artık son sınav otomatik açılır) → güçlük, ayırt edicilik, Cronbach α/KR-20, ÖÇ/PÇ gerçekleşmesi, öğrenci kartı.
- **Doğrulama:** formüller gerçek yanıt verisinden hesaplanıyor (`services/analytics.py`); testli.
- **Sürtünme:** dağılım grafiği ve **distraktör analizi** (hangi yanlış şık seçildi) görselleştirmesi sınırlı [GÖZLEM]; SEM yok.
- **Başarı:** düşük ayırt edicilikli soru listesi tek ekranda; "bu soruyu bankadan çıkar / revize et" eylemi.

## S7. Akademisyen rubrikle değerlendirme yapar — ✅
- **Adımlar:** Değerlendirme Masası → sınav → öğrenci → klasik soruda **taranmış cevap solda, rubrik sağda**; kör mod; soru bazlı seri; hızlı tablo; **benzer cevap grupları**; kaydet ve sonraki.
- **Sürtünme:** metin cevap yoksa (el yazısı tarama) gruplama devreye girmez; çift puanlayıcı/uyuşmazlık yok (B3).
- **Test:** ✅ (`test_679`, rubrik testleri).
- **Başarı:** 60 kâğıt/soru için ortalama süre ölçülmeli (ölçülmedi).

## S8. Kalite uzmanı eksik kanıtları tespit eder — 🟡
- **Mevcut:** Kanıt Merkezi "sağlık" filtresi (attention), Kalite 360 boşluk sinyalleri, kabul kapıları (Hazır/Dikkat/Bekliyor). Kural tabanlı; AI değil.
- **Eksik:** ölçüt başına **beklenen kanıt listesi** ile karşılaştırıp otomatik "eksik kanıt" raporu; sahibine hatırlatma (e-posta altyapısı hazır, SMTP bekliyor).
- **Başarı:** seçilen çerçeve için eksik kanıt sayısı tek rakam + liste + sorumlu.

## S9. AI iyileştirme önerileri oluşturur — ⛔ (kural tabanlı 🟡)
- **Mevcut:** `action-recommendations` kural tabanlı öneri üretir (hedef altı + boşluk sinyalleri); **AI üretimi yok**.
- **Eksik:** hedef altı ÖÇ için gerekçeli öneri taslağı (kaynak veriye bağlı alıntı), **öneri → PUKÖ aksiyonu** dönüşümü, kabul/ret kaydı. İlke: öneri `proposed`, karar `decided` ayrı durum.
- **Güvence:** kişisel veri göndermeden (yalnız toplu istatistik).

## S10. Üniversite yöneticisi kurumsal başarı ve kalite raporlarını inceler — 🟡
- **Mevcut:** Kurumsal Hazırlık, Yönetim Kararı özeti, `quality/dashboard.xlsx`; **ayrı rektörlük rolü ve panosu yok** (kullanıcı `admin` veya `faculty_admin`).
- **Eksik:** kurum düzeyi tek pano (fakülte karşılaştırma, PÇ gerçekleşme ısı haritası, akreditasyon takvimi), **yalnız okuma** rol, dönemlik PDF özet.
- **Başarı:** yönetici 2 dakikada "hangi program riskli, neden" sorusuna cevap bulur.

---

## Özet tablo
| Senaryo | Durum | En büyük eksik |
|---|---|---|
| S1 Akreditasyon başlatma | 🟡 | Sihirbaz |
| S2 Bölüm başkanı PÇ incelemesi | ✅ | Dönem trendi |
| S3 ÖÇ oluşturma | ✅ | ÖÇ şablonları |
| S4 Sınav hazırlama | ✅ | Blueprint arayüzü, soru sürümü |
| S5 AI Bloom analizi | ⛔ | Tamamı |
| S6 Soru analizi | ✅ | Distraktör görselleştirme |
| S7 Rubrik değerlendirme | ✅ | Çift puanlayıcı |
| S8 Eksik kanıt tespiti | 🟡 | Beklenen kanıt karşılaştırması |
| S9 AI iyileştirme önerisi | ⛔ | Tamamı (kural tabanlı mevcut) |
| S10 Kurumsal rapor | 🟡 | Rektörlük rolü/panosu |
