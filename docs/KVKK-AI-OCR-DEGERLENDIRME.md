# Harici yapay zekâ / OCR kullanımı için KVKK değerlendirme şablonu

Durum: **Taslak — hukuk/KVKK birimi onayı bekliyor.** Bu belge teknik ekibin bilgi toplama şablonudur; hukuki görüş yerine geçmez.
Bugünkü durum: DOU Assess tarama okumada yalnızca **yerel** OpenCV/QR/OMR işleme kullanır; görseller ve öğrenci verisi harici bir yapay zekâ veya OCR hizmetine gönderilmez.

## 1. Kapsam
- Planlanan kullanım: klasik soru puan önerisi (hoca onaylı), el yazısı okuma (OCR).
- Kullanılmadan önce bu belgedeki tüm maddeler kapatılmalıdır.

## 2. İşlenen veri
| Veri | Kişisel veri mi? | Gönderilir mi? | Not |
|---|---|---|---|
| Öğrenci adı/numarası | Evet | Hayır (maskelenir) | Gönderimden önce kaldırılmalı |
| El yazısı cevap görseli | Evet (el yazısı kimliklendirebilir) | Karar bekliyor | Yalnızca cevap alanı kırpıntısı |
| Soru metni / rubrik | Hayır | Evet | |

## 3. Hukuki dayanak ve yükümlülükler
- [ ] Hukuki sebep belirlendi (KVKK m.5/2) ve aydınlatma metni güncellendi
- [ ] Veri işleyen sözleşmesi imzalı; alt işleyenler listelendi
- [ ] Yurt dışına aktarım var mı? Varsa KVKK m.9 mekanizması (açık rıza / taahhütname / standart sözleşme) hazır
- [ ] Sağlayıcı verileri model eğitiminde **kullanmıyor** (yazılı teyit)
- [ ] Saklama süresi ve silme: sağlayıcıda kalıcı kayıt yok / en çok … gün
- [ ] VERBİS kaydı ve veri envanteri güncellendi
- [ ] Etki değerlendirmesi (DPIA benzeri) yapıldı

## 4. Teknik önlemler (DOU Assess tarafında)
- Gönderimden önce kimlik alanları kırpılır; yalnızca cevap alanı gider.
- Sonuç yalnızca **öneri**dir; puan hoca onayıyla yazılır, kim onayladığı işlem kaydına düşer.
- Her harici çağrı denetim kaydına yazılır (hangi sınav, kaç görsel, hangi sağlayıcı).
- Sağlayıcı ağ erişimi yalnızca izin verilen host listesiyle açılır; varsayılan kapalıdır.

## 5. Karar
- [ ] Onaylandı  - [ ] Şartlı onay  - [ ] Reddedildi — Tarih / onaylayan: ____________
