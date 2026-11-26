# DOU Assess 6.42 — Finalization Workspace

**Application version:** `6.42-finalization-workspace`  
**Schema head:** `0025_accreditation_compliance_core` (migration yok)

Bu sürüm yeni domain eklemek yerine 6.41 çekirdeğini gerçek kullanıcı akışına yaklaştırır.

- Dashboard `Action Center / Eksiklerim` kuyruğu eklendi.
- Öğrenci Karneleri bağımsız çalışma alanına çıkarıldı.
- Karnede ders bazlı Öğrenim Çıktıları, Program Çıktıları, hedef/risk durumları ve güçlü/gelişim alanları gösterilir.
- Öğrenci karnesi doğrulama kodu ve QR içeren PDF olarak indirilebilir.
- Mezuniyet snapshot dondurma akışı korunur.
- Quality-only kullanıcılar öğrenci karnesi ve program analizi görebilir; operasyonel sınav ekranları gizli kalır.
- Veritabanı şeması değişmedi; 6.41 compliance core geriye uyumludur.
