# İkinci üniversite pilot kontrol listesi

Amaç: ürünün Doğuş'a özel olmadığını, ikinci bir kurumda aynı akışla çalıştığını göstermek.

## 1. Hazırlık (pilottan önce)
- [ ] Kurum seçimi, sorumlu kişi ve pilot kapsamı (1 program, 3–5 ders, 1 dönem) yazılı
- [ ] Veri sorumlusu/işleyen sözleşmesi ve KVKK dosyası (docs/commercial/KVKK-DOSYASI.md) imzalı
- [ ] Dağıtım: kuruma özel örnek (bkz. ADR-multi-tenant.md), HTTPS, yedek, kimlik (SSO) kuruldu
- [ ] OBS bağlayıcısı: kurumun OBS'si için `AcademicConnector` yazıldı veya Excel içe aktarma yolu seçildi
- [ ] Kurum ayarları: ÖÇ terimi, başarı eşikleri, saklama süresi, onay akışı anahtarları girildi
- [ ] Kâğıt şablonu: kurum adı/logosu uyarlandı (şu an Doğuş'a özel)

## 2. Kabul senaryosu (Doğuş demo senaryosunun aynısı)
- [ ] Hoca kurumsal hesapla girer, yalnızca kendi derslerini görür
- [ ] OBS verisi (ders, ÖÇ, öğrenci) gelir; son senkron zamanı görünür
- [ ] ÖÇ ekleme/düzenleme/pasife alma ve (açıksa) onay akışı
- [ ] Soru havuzu, sınav, kapsam kontrolü, özgün kâğıt PDF, basım ve "yazdırdım" kilidi
- [ ] Gerçek yazıcı + kurumun tarayıcısıyla 20/50/100 soruluk kâğıtların tarama ve okuma testi; örnekleme ile hata oranı ölçümü
- [ ] Puanlama, kilit, öğrenci itiraz akışı, OBS aktarım dosyası
- [ ] Analiz, karne, PÇ belgesi, dönem kapanış paketi

## 3. Çıkış ölçütleri
- [ ] Okuma hata oranı ≤ hedef (SCAN_TARGET_ERROR_PERCENT) — ölçülmüş
- [ ] P0/P1 hatası yok; kullanıcı memnuniyeti geri bildirimi toplandı
- [ ] Kurum kalite birimi akreditasyon çıktısını (PÇ belgesi, kapanış paketi) kabul etti
- [ ] Devam kararı ve ticari koşullar (docs/commercial/TICARI-PAKET-SABLONU.md) görüşüldü
