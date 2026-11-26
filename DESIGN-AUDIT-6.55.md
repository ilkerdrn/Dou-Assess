# DOU Assess — Kurumsal UX / UI Tasarım Denetimi (6.55)

## Yönetici özeti
DOU Assess'in ana problemi özellik eksikliği değil, uzun geliştirme sürecinde biriken çok sayıda modülün aynı anda görünür hale gelmesiyle oluşan görsel ve bilişsel yoğunluktu. Sistem işlevsel olarak güçlü; ancak önceki arayüzde küçük yazı boyutları, yoğun rozet/kart kullanımı, koyu teknik yan menü, tekrar eden dashboard kuyrukları ve yönetim paneli estetiği akademik-kurumsal güven algısını zayıflatıyordu.

6.55 yalnız UX/UI katmanını düzenler; iş kuralları ve veri modeli değiştirilmez.

## Tespit edilen temel sorunlar
1. **Mikro tipografi:** CSS içinde 7–10 px aralığında çok sayıda metin tanımı bulunuyordu. Akademisyenlerin uzun süreli kullanımında okunabilirlik ve taranabilirlik zayıftı.
2. **Teknik panel hissi:** Koyu yan menü ve sıkışık modül hiyerarşisi üniversite bilgi sistemi yerine geliştirici/admin paneli hissi oluşturuyordu.
3. **Aynı önem seviyesinde çok fazla kart:** Kritik görev, bilgi ve ikincil sistem durumu aynı görsel ağırlıkta gösteriliyordu.
4. **Dashboard tekrarı:** Action Center ile “Dikkat Gerektiren” kuyruğu benzer mesajları iki kez sunuyordu.
5. **Kalite ekranlarında görsel gürültü:** MEDEK/MÜDEK/Quality360 kanıt ve durum bilgisinden önce kart/badge yoğunluğu algılanıyordu.
6. **Form yoğunluğu:** Kontroller kısa ve sıkışık; label, input ve buton hedefleri kurumsal masaüstü kullanımında gereğinden küçüktü.
7. **Tablo okunabilirliği:** Akademik veri ve kalite matrislerinde başlık/gövde ayrımı ve satır taraması zayıftı.
8. **Kimlik ekranı:** Giriş ekranı işlevsel ancak ürün kimliği ile kurumsal üniversite güvenini daha dengeli vermeliydi.
9. **Responsive öncelik:** Mobilde bazı ikincil header aksiyonları ana işi daraltıyordu.

## 6.55 tasarım kararı
### Görsel dil
- Açık kurumsal tema
- Doğuş bordosu ana aksan
- Beyaz kartlar + açık gri kampüs/portal zemini
- Minimum gölge, net sınırlar
- Daha büyük tipografi ve rahat satır yüksekliği
- Teknik dekorasyondan çok içerik hiyerarşisi

### Bilgi mimarisi
Sol menü dört ana çalışma katmanını korur:
- Çalışma Alanım
- Analiz
- Kalite
- Yönetim

Grup açıklamalarının sürekli görünmesi kaldırılarak günlük navigasyon sadeleştirildi. Aktif modül bordo sol vurgu ve yumuşak arka planla belirginleştirildi.

### Dashboard
- Action Center ana görev kuyruğu olarak öne çıkarıldı.
- Tekrarlayan “Dikkat Gerektiren” kartı görsel olarak kaldırıldı.
- Hızlı aksiyonlar korunurken daha belirgin birincil/ikincil aksiyon ayrımı getirildi.
- KPI kartlarının sayısal hiyerarşisi büyütüldü.

### Quality360 / Akreditasyon
- Durum ve kanıt içeriği görsel süsten önce gelecek şekilde sade kart sistemi.
- Alt ölçüt satırlarında daha yüksek okunabilirlik.
- MEDEK ÖDR ve kanıt listelerinde satır/panel ayrımı güçlendirildi.
- İnsan onayı gerektiren kalite süreçlerinin dikkat dili korunurken renk kullanımı sakinleştirildi.

### Form ve veri tabloları
- Input/select hedef yüksekliği 42 px tabanına taşındı.
- Label ve içerik yazıları büyütüldü.
- Tablolarda sticky header, daha belirgin satır çizgileri ve hover taraması eklendi.
- Büyük akademik matrisler için mevcut yatay kaydırma davranışı korunur.

### Öğrenci karnesi
- PÇ/ÖÇ çıktıları bilgi kartı olarak daha sakin ve okunabilir hale getirildi.
- PDF / freeze aksiyonları işlevsel olarak değişmeden görsel hiyerarşiye oturtuldu.

### Giriş ekranı
- “SaaS landing page” hissi azaltıldı.
- Doğuş kurumsal bordosu korunurken sağ tarafta sade giriş alanı kullanıldı.
- Güvenlik ve yetkilendirme bilgileri ikincil kanıt metni olarak konumlandı.

## Erişilebilirlik
- Klavye focus-visible halkaları
- Daha büyük buton ve input hedefleri
- Daha yüksek metin kontrastı
- `prefers-reduced-motion` desteği
- Mobilde ikincil header aksiyonlarının azaltılması

## Teknik sınır
Bu çalışma **UI-only** release'tir.
- APP_VERSION: `6.54-final-production-release`
- Schema: `0031_medek_final_decision`
- API contract değişikliği yok
- Migration değişikliği yok
- Backend business logic değişikliği yok
