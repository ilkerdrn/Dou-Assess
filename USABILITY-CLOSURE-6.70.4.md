# DOU Assess 6.70.4 — Usability Closure

## Amaç
Özellik sayısını artırmadan günlük kullanımı basitleştirmek ve her rolde bilişsel yükü azaltmak.

## Kapanan alanlar
- Ana Sayfa: tek bir **Şimdi ne yapmalıyım?** aksiyonu ve ikincil işlerin progressive disclosure ile saklanması.
- Ders Workspace: Soru ekle → Sınav hazırla → Değerlendir → Sonuçları gör şeklinde dört adımlı hızlı kullanım.
- Sınavlar: belirtke tablosu ve baskı/optik ayarları varsayılan olarak Gelişmiş altında; 4 adımlı wizard dili sadeleştirildi.
- Değerlendirme: puanlama bekleyen sınavlar üstte kartlarla gösterilir ve tek tıkla çalışma alanına geçilir.
- Kalite360: Standart/Uzman görünüm. Standart görünüm yalnız Genel Bakış, PUKÖ, Takvim ve Kanıtları öne çıkarır.

## Teknik
- DB migration yok.
- API kontratı değişmedi.
- Mevcut 0042 şeması korunur.
- 6.70.1 Soru Bankası drawer specificity fix korunur.
