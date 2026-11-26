# DOU Assess 6.19 — Kullanım Kılavuzu

## 1. Sisteme ilk giriş

DOU Assess normal akademik kullanımda üç hesap tipi sunar:

### Öğretim Görevlisi
Kendi dersleri kapsamında soru bankası, sınav hazırlama, öğrenci atama/katılım, kağıt üretme, optik tarama, klasik puanlama ve analiz süreçlerini yürütür.

### Program Başkanı
Program kapsamındaki akademik veri, ÖÇ/PÇ, sınav operasyonu/moderasyon, kalite göstergeleri, iyileştirme ve kanıt süreçlerini yönetir.

### Kalite Müdürü
Kurum/program kalite sonuçlarını, ÖÇ/PÇ açıklarını, akreditasyon, PDCA aksiyonları ve kanıt zincirini izler/yönetir.

Teknik `admin` akademik hesap tipi değildir; yalnız kurulum, kullanıcı/yetki ve sistem işletimi içindir.

## 2. Ekran içi yönlendirme

Her ekranda üst bölümde:

- `? Kılavuz`: bulunduğunuz ekrana özel işlem sırasını gösterir.
- `Excel Yükle`: bulunduğunuz modüle uygun Excel Veri Merkezi'ni açar.
- `Ara / Git (Ctrl+K)`: modüller arasında hızlı geçiş sağlar.

Dashboard rolünüze göre sıradaki işleri öne çıkarır.

## 3. Excel ile veri yükleme

Excel Merkezi'nde temel yöntem aynıdır:

1. Veri türünü seçin.
2. `Şablonu indir` ile güncel dosyayı alın.
3. Excel'i doldurun.
4. Önce `Doğrula` çalıştırın.
5. Hata yoksa `İçe aktar` yapın.

Toplu işlemler kullanıcının yetki/kapsamına göre sunucu tarafında tekrar kontrol edilir.

Desteklenen başlıca akışlar:

- Akademik Veri: Programlar, Dersler, Öğrenciler, Ders Kayıtları, ÖÇ/PÇ.
- Soru Havuzu: test ve klasik sorular.
- Sınav Öğrencileri & Katılım: `attended | absent | excused | invalidated`.
- Klasik Rubrik Puanlama.
- Kalite / PDCA Aksiyonları.
- Kullanıcı & Akademik Rol: `instructor | program_head | quality`.

## 4. Soru havuzu

### Test sorusu
En az iki seçenek, doğru cevap, puan, Bloom düzeyi ve en az bir ÖÇ eşleşmesi bulunmalıdır.

### Klasik soru
Klasik soruda şu alanlar zorunludur:

- Beklenen cevap / değerlendirme anahtarı.
- Bloom düzeyi.
- En az bir ÖÇ.
- Analitik rubrik.
- Her rubrik ölçütünün en az bir ÖÇ eşleşmesi.
- Rubrik toplamı = soru puanı.

Excel rubrik örneği:

```text
Ağ kontrolleri | 3 | ÖÇ=ÖÇ4; Servis kontrolleri | 3 | ÖÇ=ÖÇ6; Log kullanımı | 2 | ÖÇ=ÖÇ6; Çözüm sırası | 2 | ÖÇ=ÖÇ4
```

## 5. Sınav hazırlama

1. Ders ve sınav türünü seçin.
2. Tarih, süre ve salon/konum girin.
3. Soru havuzundan soruları ekleyin veya yeni soru oluşturun.
4. Soru puanları toplamını 100'e tamamlayın.
5. Öğrencileri sınava aktarın/atananları kontrol edin.
6. Hazırlık kontrolünü çalıştırın.
7. Sınavı `ready` durumuna alın.
8. Öğrenciye özel A/B kitapçık PDF'lerini üretin.

Production ortamında salon/konum zorunludur.

## 6. Tarama / optik

- PDF veya fiziksel ADF taraması sisteme yüklenir.
- QR öğrenci/sınav/kitapçık kimliğini belirler.
- Test işaretleri otomatik okunur.
- Belirsiz, çift veya güveni düşük işaretler manuel incelemeye düşer.
- Klasik soru sayfaları öğrenci ve soruya otomatik bağlanır.
- Eski `dou-official-v2` kağıtları legacy association ile desteklenir.

Manuel inceleme tamamlanmadan sınavın puanlarını kilitlemeyin.

## 7. Klasik puanlama

Puanlama ekranında taranmış cevap solda, soru/beklenen cevap/rubrik sağda görülür.

Toplam puanı elle yazmak yerine rubrik kriterlerini puanlayın. Sistem toplamı otomatik hesaplar ve ÖÇ/kriter analizini bu puanlardan üretir.

Örnek:

```text
Ağ kontrolü        3 / 3
Servis kontrolü    2 / 3
Log analizi        1 / 2
Çözüm sırası       2 / 2
-----------------------
Toplam              8 / 10
```

## 8. Katılım ve istisnalar

Öğrenci durumu:

- `attended`: ölçüm/analiz paydasına dahil.
- `absent`: devamsız, paydadan çıkarılır.
- `excused`: mazeretli, paydadan çıkarılır.
- `invalidated`: sınav/kağıt geçersiz, paydadan çıkarılır.

Kayıp/mükerrer kağıt, teknik problem, akademik bütünlük veya tarama sorunu `Sınav Olayı` olarak kaydedilir.

## 9. Puan kilidi ve itiraz

Puan kilidi için:

- aktif öğrencilerin puanlaması tamamlanmış olmalı,
- açık optik inceleme olmamalı,
- açık kritik olay olmamalı,
- açık itiraz olmamalı.

Kilit sonrası normal puan değişikliği reddedilir.

İtiraz kabul edilirse klasik soruda toplam puan elle değiştirilmez; rubrik kriterleri yeniden değerlendirilir, yeni toplam kriterlerden hesaplanır. Eski/yeni puan ve revizyon izi korunur.

## 10. Analiz ve kalite

Sistem test sorularında güçlük, ayırt edicilik, point-biserial, boş cevap ve çeldirici analizi; sınav genelinde KR-20/Cronbach Alpha ve ÖÇ/PÇ başarılarını üretir.

Klasik sorularda ayrıca rubrik kriter başarıları ölçülebilir. Küçük örneklemlerde istatistiksel sonuçlar güven uyarısı ile yorumlanmalıdır.

## 11. PDCA / sürekli iyileştirme

Kalite aksiyonunda yalnız “aksiyon açıldı” kaydı yeterli değildir. Aşağıdaki zincir tamamlanır:

```text
Baseline → Hedef → Aksiyon/Sorumlu → Sonraki Ölçüm → Gerçekleşen → Doğrulama Yöntemi → Etkililik → Kapanış
```

`done` durumuna geçiş için gerçekleşen sonuç, doğrulama yöntemi, etkililik durumu ve kapanış notu doldurulur.

## 12. Kanıt ve akreditasyon

Sınav sonuçları, analiz, iyileştirme, olay ve itiraz kayıtları kalite/akreditasyon kanıt zincirine dahil edilir. Kanıt dosyaları SHA-256 ile izlenir ve saklama/purge politikası uygulanabilir.

## 13. Dönem sonu önerilen sıra

```text
Tarama tamamla
→ manuel incelemeleri kapat
→ klasik rubrikleri puanla
→ katılım/olayları doğrula
→ itirazları kapat
→ puanları kilitle
→ analiz/ÖÇ-PÇ sonuçlarını kontrol et
→ kalite aksiyonlarını aç/kapat
→ kanıt paketini üret
→ yönetici onayı
→ OBS çıktısı/gönderimi
```
