# DOU Assess 6.40.1 — Runtime UI / Evaluation / Mapping Hotfix

- Soru Havuzu `+ Yeni soru oluştur` artık API yanıtını beklemeden editörü anında açar.
- Buton için bağımsız same-origin runtime hotfix scripti eklendi; ana app listener zincirinden bağımsızdır.
- 6.40 değerlendirme renk CSS'inde yanlışlıkla literal `\\n` olarak paketlenen satır sonları düzeltildi.
- Değerlendirme: öğrenci seçimi sarı vurgu, doğru cevap yeşil, yanlış seçilen cevap kırmızı olarak görünür.
- Öğrenim Çıktısı ↔ Program Çıktısı katkı ölçeği 1–5 olarak DB seviyesinde zorunlu hale getirildi.
- Eski 0 katkı kayıtları migration sırasında 1'e normalize edilir; sınav snapshot katkıları da normalize edilir.
- Schema revision: `0024_mapping_contribution_1_5`.
