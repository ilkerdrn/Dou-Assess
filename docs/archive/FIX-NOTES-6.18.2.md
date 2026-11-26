# DOU Assess 6.18.2 · Final Kontrol / Öğrenci Senkronu

Bu ara sürüm aşağıdaki pilot geri bildirimlerini kapatır:

- Kontrol & Çıktı ekranında sol kontrol kolonu genişletildi ve responsive davranış iyileştirildi.
- Kurumsal Onay metinleri ayrı bloklara alındı; birleşik/taşan metin görünümü giderildi.
- Kazanım dağılımı kartları dar kolonlarda taşmayacak şekilde düzenlendi.
- 100 puanı aşan sınavlarda Kontrol & Çıktı ekranından doğrudan **Puanları 100'e ölçekle** işlemi eklendi.
- Readiness API artık sınava atanmış öğrenci ve ders kayıtlı öğrenci sayılarını döndürür.
- Kontrol & Çıktı ekranına **Öğrenci Ataması** kartı eklendi.
- Ders kayıtları sonradan eklendiyse **Ders kayıtlarını sınava aktar** tek tık işlemi eklendi.
- Toplu kişiselleştirilmiş kağıt butonu öğrenci ataması yoksa pasifleşir ve kullanıcıya nedenini açıklar.
- Yeni sınav oluştururken seçili derste öğrenci yoksa görünür uyarı ve **Öğrenci ata** kısayolu gösterilir.
- Öğrenci senkron endpointinde transaction içi sayaç için `flush` düzeltildi; 0/30 -> 30/30 anlık doğru gösterilir.
- Test için 30 öğrenci ve 6 teknik derse 180 ders kaydı içeren Excel paket içine eklendi.

Schema değişikliği yoktur; mevcut 0015 migration yapısı korunur.
