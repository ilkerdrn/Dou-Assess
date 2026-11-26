# DOU Assess 6.26 — Premium Experience

Sürüm: `6.26-premium-experience-server-ready`
Schema: `0020_assessment_intelligence` (yeni migration yok)

## Hedef
Gelişmiş yetenekleri aynı anda ekrana yığmadan, yönetimde premium ürün hissi ve öğretim elemanında sıfır eğitimle kullanılabilir akış sağlamak.

## UX değişiklikleri
- Akademik Yapı artık list-first çalışır; oluşturma/düzenleme sağ drawer içinde açılır.
- Program kartlarında ders, öğrenci ve sınav kapsamı görünür; ana CTA `Programa gir` olur.
- Tehlikeli/sık kullanılmayan işlemler ana karttan geri çekilir.
- Değerlendirme ekranındaki aktif öğrenci bloğu kimlik + sınav bağlamı + soru/tarama metrikleri + puan olarak yeniden tasarlandı.
- `Soru yok` gibi ham boş ekranlar, nedeni ve sonraki aksiyonu anlatan premium empty-state bileşenlerine dönüştürüldü.
- Mobilde drawer tam ekran, öğrenci odak paneli tek kolon çalışır.
- Akademik dizin daha geniş çalışma alanı kullanır; form kalıcı olarak ekranı bölmez.

## Korunanlar
- 6.25 Academic Intelligence: Derslerim, Ders Analizi, Program Analizi.
- 6.24.x workflow ve question-bank drawer.
- 0020 assessment intelligence schema ve mevcut PostgreSQL verisi.
