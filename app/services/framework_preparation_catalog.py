from __future__ import annotations

from typing import Any


def _item(code: str, title: str, mapped: str, automation: str, owner: str, evidence: list[str], sources: list[str]) -> dict[str, Any]:
    return {
        "code": code,
        "title": title,
        "mapped_criterion": mapped,
        "automation_key": automation,
        "owner_role": owner,
        "required_evidence": evidence,
        "source_modules": sources,
    }


# TURAK: The preparation matrix deliberately tracks the nine official criterion headings.
# The current official ODR v7 / evidence documents are retained as source metadata; no
# fictional subcriteria are invented when the public index does not expose their full text.
TURAK_ODR_V7_ITEMS = [
    _item("TURAK-ODR-1", "Öğrenciler", "1", "students", "Program Başkanı / Öğrenci İşleri", ["Öğrenci kabul, geçiş ve başarı verileri", "Danışmanlık/öğrenci destek kanıtı"], ["OBS/Proliz", "Öğrenci Kayıtları", "Kanıt Merkezi"]),
    _item("TURAK-ODR-2", "Program Öğretim Amaçları", "2", "pea", "Program Başkanı / Kalite", ["Program öğretim amaçları", "Paydaş katılımı ve gözden geçirme kanıtı"], ["PEA", "Paydaş", "Kurul & Karar"]),
    _item("TURAK-ODR-3", "Program Öğrenim Çıktıları", "3", "lo_po", "Program Başkanı / Ölçme-Değerlendirme", ["Program öğrenim çıktıları", "Çıktı ölçme ve erişim sonuçları"], ["ÖÇ/PÇ", "Ölçme & Değerlendirme", "Öğrenci Karnesi"]),
    _item("TURAK-ODR-4", "Öğretim Planı", "4", "curriculum", "Program Başkanı / Eğitim Komisyonu", ["Öğretim planı", "Ders bilgi paketleri ve AKTS/iş yükü kanıtı"], ["Müfredat & AKTS", "Ders Dosyaları"]),
    _item("TURAK-ODR-5", "Öğretim Kadrosu", "5", "faculty", "Program Başkanı / İK", ["Öğretim kadrosu listesi ve özgeçmişler", "İş yükü/gelişim kanıtı"], ["Kadroyu Yönet", "Kadro İş Yükü"]),
    _item("TURAK-ODR-6", "Yönetim Yapısı", "6", "decisions", "Program Başkanı / Birim Yönetimi", ["Organizasyon ve sorumluluklar", "Kurul/karar ve yönetim kanıtları"], ["Kurul & Karar", "Kontrollü Doküman"]),
    _item("TURAK-ODR-7", "Altyapı", "7", "infrastructure", "Program Başkanı / İdari Birim", ["Fiziki/teknik altyapı envanteri", "Erişilebilirlik, güvenlik ve kullanım kanıtı"], ["Altyapı", "Kanıt Merkezi"]),
    _item("TURAK-ODR-8", "Kurum Desteği ve Parasal Kaynaklar", "8", "decisions", "Birim Yönetimi / Mali İşler", ["Bütçe ve kaynak planı", "Kurumsal destek ve sürdürülebilirlik kanıtı"], ["Bütçe", "Kurul & Karar"]),
    _item("TURAK-ODR-9", "Sürekli İyileştirme", "9", "quality_cycle", "Program Başkanı / Kalite", ["Ölçüm sonucu", "Karar", "PUKÖ ve etkililik kanıtı"], ["PUKÖ", "Kurul & Karar", "ÖÇ/PÇ"]),
]

TURAK_ODR_V7_SOURCE = {
    "family": "TURAK",
    "document": "Özdeğerlendirme Raporu (ODR)",
    "version": "7",
    "odr_date": "2025-12-27",
    "criteria_date": "2024-12-27",
    "url": "https://turak.org/belgeler/",
    "granularity_note": "Hazırlık matrisi dokuz resmî ölçüt başlığını izler; resmî ODR/evidence dosyaları Şablon Kasası'nda dondurulmadan alt ölçüt metni türetilmez.",
}


# SABAK ODR Revizyon 5 (10.04.2026) — ODR preparation headings.
# These rows are report-preparation prompts and do not alter the underlying criteria revision.
SABAK_ODR_R5_ITEMS = [
    # 1 · Programın Eğitim Amaçları
    _item("SABAK-R5-1.1", "Program eğitim amaçlarının tanımı", "1", "pea", "Program Başkanı", ["Program eğitim amaçları"], ["PEA"]),
    _item("SABAK-R5-1.2", "Program eğitim amaçlarının erişilebilirliği", "1", "pea", "Program Başkanı", ["Kamuya açık PEA yayını/URL"], ["PEA", "Kontrollü Doküman"]),
    _item("SABAK-R5-1.3", "Program eğitim amaçlarının belirlenmesinde paydaş katılımı", "1", "stakeholders", "Program Başkanı / Kalite", ["İç/dış paydaş görüşleri", "Kurul kararı"], ["Paydaş", "Kurul & Karar"]),
    _item("SABAK-R5-1.4", "Program eğitim amaçlarının misyon ve vizyon ile uyumu", "1", "program_identity", "Program Başkanı", ["Misyon-vizyon ve PEA uyum değerlendirmesi"], ["PEA", "Kontrollü Doküman"]),
    _item("SABAK-R5-1.5", "Program eğitim amaçlarının gözden geçirilmesi ve güncellenmesi", "1", "decisions", "Program Başkanı / Kalite", ["Gözden geçirme kaydı", "Revizyon/karar izi"], ["Kurul & Karar", "PEA"]),
    _item("SABAK-R5-1.6", "Program eğitim amaçlarına ilişkin iyileştirmeler ve PUKÖ döngüsü", "1", "quality_cycle", "Program Başkanı / Kalite", ["PUKÖ kaydı", "Etkililik sonucu"], ["PUKÖ"]),
    # 2 · Program Çıktıları
    _item("SABAK-R5-2.1", "Program çıktılarının tanımı", "2", "lo_po", "Program Başkanı", ["Program çıktıları listesi"], ["ÖÇ/PÇ"]),
    _item("SABAK-R5-2.2", "Program çıktılarının erişilebilirliği", "2", "lo_po", "Program Başkanı", ["Kamuya açık program çıktıları/URL"], ["ÖÇ/PÇ", "Kontrollü Doküman"]),
    _item("SABAK-R5-2.3", "Program çıktılarının belirlenme yöntemi", "2", "stakeholders", "Program Başkanı / Kalite", ["Belirleme yöntemi", "Paydaş/kurul kayıtları"], ["Paydaş", "Kurul & Karar"]),
    _item("SABAK-R5-2.4", "Program çıktılarının eğitim amaçları ile ilişkilendirilmesi", "2", "pea", "Program Başkanı", ["PEA-PÇ ilişki matrisi"], ["PEA", "ÖÇ/PÇ"]),
    _item("SABAK-R5-2.5", "Program çıktılarının UÇEP yetkinliklerini içerme durumu", "2", "manual", "Program Başkanı / Eğitim Komisyonu", ["UÇEP-PÇ kapsama matrisi"], ["Kanıt Merkezi"]),
    _item("SABAK-R5-2.6", "Program çıktılarının TYYÇ yetkinliklerini içerme durumu", "2", "manual", "Program Başkanı / Bologna", ["TYYÇ-PÇ kapsama matrisi"], ["Kanıt Merkezi", "Müfredat & AKTS"]),
    _item("SABAK-R5-2.7", "Program çıktılarının SABAK çıktıları ile uyumu", "2", "lo_po", "Program Başkanı / Kalite", ["SABAK-PÇ kapsama matrisi"], ["ÖÇ/PÇ", "Framework Mapping"]),
    _item("SABAK-R5-2.8", "Program çıktılarının gözden geçirilmesi ve güncellenmesi", "2", "decisions", "Program Başkanı", ["Gözden geçirme ve revizyon kayıtları"], ["Kurul & Karar", "ÖÇ/PÇ"]),
    _item("SABAK-R5-2.9", "Program çıktılarına ilişkin iyileştirmeler ve PUKÖ", "2", "quality_cycle", "Program Başkanı / Kalite", ["Ölçüm sonucu", "PUKÖ ve etkililik kaydı"], ["PUKÖ", "ÖÇ/PÇ"]),
    # 3 · Eğitim Planı
    _item("SABAK-R5-3.1", "Eğitim planının tanımı ve program amaç/çıktıları ile uyumu", "3", "curriculum", "Program Başkanı / Eğitim Komisyonu", ["Eğitim planı", "Amaç/çıktı uyum matrisi"], ["Müfredat & AKTS", "ÖÇ/PÇ"]),
    _item("SABAK-R5-3.2", "Eğitim planının temel bileşenleri", "3", "curriculum", "Program Başkanı", ["Ders dağılımı ve bileşen analizi"], ["Müfredat & AKTS"]),
    _item("SABAK-R5-3.3", "Eğitim planının YÖK kararları ile uyumu", "3", "manual", "Eğitim Komisyonu", ["YÖK kararlarıyla uyum kontrolü"], ["Kontrollü Doküman", "Kanıt Merkezi"]),
    _item("SABAK-R5-3.4", "Eğitim planının UÇEP ile uyumu", "3", "manual", "Program Başkanı / Eğitim Komisyonu", ["UÇEP-ders kapsama matrisi"], ["Müfredat & AKTS", "Kanıt Merkezi"]),
    _item("SABAK-R5-3.5", "Eğitim planının eğitim amaçlarına ulaşılmasını güvence altına alması", "3", "pea", "Program Başkanı", ["PEA-eğitim planı ilişki kanıtı"], ["PEA", "Müfredat & AKTS"]),
    _item("SABAK-R5-3.6", "Eğitim planının öğrenim çıktıları ile ilişkilendirilmesi", "3", "lo_po", "Program Başkanı / Ders Sorumluları", ["Ders ÖÇ-PÇ matrisi"], ["ÖÇ/PÇ"]),
    _item("SABAK-R5-3.7", "Eğitim planının program çıktılarına ulaşılmasını güvence altına alması", "3", "lo_po", "Program Başkanı / Ölçme-Değerlendirme", ["PÇ ölçme planı", "Ders/PÇ kapsama sonuçları"], ["ÖÇ/PÇ", "Ölçme Güvence Planı"]),
    _item("SABAK-R5-3.8", "Disipline özgü uygulamaya yönelik karar verme deneyimi", "3", "program_specific", "Program Başkanı", ["Disipline özgü uygulama/proje/staj kanıtları"], ["Ölçme & Değerlendirme", "Kanıt Merkezi"]),
    _item("SABAK-R5-3.9", "Eğitim yöntemleri", "3", "curriculum", "Ders Sorumluları", ["Ders izlenceleri", "Öğretim yöntemi örnekleri"], ["Ders Dosyaları"]),
    _item("SABAK-R5-3.10", "Eğitim yönetim sistemi", "3", "manual", "Program Başkanı / Birim Yönetimi", ["Eğitim yönetim süreçleri ve sorumluluklar"], ["Kontrollü Doküman", "Kurul & Karar"]),
    _item("SABAK-R5-3.11", "Eğitim planının gözden geçirilmesi ve güncellenmesi", "3", "decisions", "Program Başkanı / Eğitim Komisyonu", ["Müfredat gözden geçirme/karar kaydı"], ["Kurul & Karar", "Müfredat & AKTS"]),
    _item("SABAK-R5-3.12", "Eğitim planına ilişkin iyileştirmeler ve PUKÖ", "3", "quality_cycle", "Program Başkanı / Kalite", ["PUKÖ kaydı ve etkililik sonucu"], ["PUKÖ"]),
    # 4 · Ölçme ve Değerlendirme
    _item("SABAK-R5-4.1", "Ölçme ve değerlendirme sisteminin tanımı", "4", "official_exam", "Ölçme-Değerlendirme Komisyonu", ["Ölçme-değerlendirme sistemi/prosedürü"], ["Ölçme & Değerlendirme", "Kontrollü Doküman"]),
    _item("SABAK-R5-4.2", "Ders izlencesi / ders bilgi paketi", "4", "curriculum", "Ders Sorumluları", ["Güncel ders bilgi paketleri"], ["Ders Dosyaları"]),
    _item("SABAK-R5-4.3", "AKTS ile ölçme-değerlendirme tutarlılığı", "4", "curriculum", "Program Başkanı / Bologna", ["AKTS/iş yükü ve değerlendirme tutarlılık analizi"], ["Müfredat & AKTS"]),
    _item("SABAK-R5-4.4", "Ölçme ve değerlendirme sistemi uygulaması", "4", "official_exam", "Ders Sorumluları", ["Sınav/rubrik/proje örnekleri", "Notlandırma sonuçları"], ["Ölçme & Değerlendirme"]),
    _item("SABAK-R5-4.5", "Program çıktılarına ulaşma düzeyinin ölçülmesi", "4", "student_outcomes", "Program Başkanı / Ölçme-Değerlendirme", ["PÇ başarı sonuçları", "Doğrudan ölçme kanıtı"], ["ÖÇ/PÇ", "Öğrenci Karnesi"]),
    _item("SABAK-R5-4.6", "SABAK çıktılarına ulaşma düzeyinin ölçülmesi", "4", "student_outcomes", "Program Başkanı / Kalite", ["SABAK çıktı eşleme ve başarı sonuçları"], ["ÖÇ/PÇ", "Framework Mapping"]),
    _item("SABAK-R5-4.7", "Program çıktıları ve mezun izleme sonuçlarının ilişkilendirilmesi", "4", "graduates", "Program Başkanı / Mezun Ofisi", ["Mezun izleme sonuçları", "PÇ ile ilişki/değerlendirme"], ["Mezun", "ÖÇ/PÇ"]),
    _item("SABAK-R5-4.8", "Eğitim amaçları ve mezun izleme sonuçlarının ilişkilendirilmesi", "4", "graduates", "Program Başkanı / Mezun Ofisi", ["Mezun izleme ve PEA değerlendirmesi"], ["Mezun", "PEA"]),
    _item("SABAK-R5-4.9", "Ölçme-değerlendirme sisteminin gözden geçirilmesi ve güncellenmesi", "4", "decisions", "Ölçme-Değerlendirme Komisyonu", ["Gözden geçirme ve karar kayıtları"], ["Kurul & Karar"]),
    _item("SABAK-R5-4.10", "Ölçme-değerlendirme iyileştirmeleri ve PUKÖ", "4", "quality_cycle", "Program Başkanı / Kalite", ["PUKÖ ve etkililik kaydı"], ["PUKÖ"]),
    # 5 · Öğrenciler ve Mezunlar
    _item("SABAK-R5-5.1", "Öğrenci kabul ve mezuniyet süreçleri", "5", "students", "Öğrenci İşleri / Program Başkanı", ["Kabul ve mezuniyet süreçleri/verileri"], ["OBS/Proliz", "Öğrenci Kayıtları"]),
    _item("SABAK-R5-5.2", "Ulusal/uluslararası değişim ve hareketlilik", "5", "manual", "Uluslararası Ofis", ["Değişim prosedürü ve katılım kayıtları"], ["Kanıt Merkezi"]),
    _item("SABAK-R5-5.3", "Öğrenci danışmanlığı", "5", "manual", "Program Başkanı / Danışmanlar", ["Danışmanlık sistemi ve faaliyet kayıtları"], ["Kanıt Merkezi"]),
    _item("SABAK-R5-5.4", "Kariyer planlama", "5", "manual", "Kariyer Merkezi / Program Başkanı", ["Kariyer faaliyeti ve katılım kanıtı"], ["Kanıt Merkezi"]),
    _item("SABAK-R5-5.5", "Öğrenci temsiliyeti", "5", "stakeholders", "Program Başkanı", ["Öğrenci temsilciliği ve katılım kayıtları"], ["Paydaş", "Kurul & Karar"]),
    _item("SABAK-R5-5.6", "Öğrencilere sağlanan olanaklar", "5", "infrastructure", "Birim Yönetimi", ["Öğrenci destek/öğrenme olanakları"], ["Altyapı", "Kanıt Merkezi"]),
    _item("SABAK-R5-5.7", "Öğrencilerin olanaklardan yararlanması", "5", "manual", "Program Başkanı / Birim Yönetimi", ["Kullanım/katılım istatistikleri"], ["Kanıt Merkezi"]),
    _item("SABAK-R5-5.8", "Öğrencilerin toplumsal katkı faaliyetleri", "5", "manual", "Program Başkanı / SKS", ["Toplumsal katkı faaliyet ve katılım kayıtları"], ["Kanıt Merkezi"]),
    _item("SABAK-R5-5.9", "Öğrencilere sağlanan finansal olanak ve destekler", "5", "manual", "Birim Yönetimi / Burs Ofisi", ["Burs/destek olanakları ve yararlanma verileri"], ["Kanıt Merkezi"]),
    _item("SABAK-R5-5.10", "Bilgilendirme ve oryantasyon", "5", "manual", "Program Başkanı / Öğrenci İşleri", ["Oryantasyon planı ve katılım kayıtları"], ["Kanıt Merkezi"]),
    _item("SABAK-R5-5.11", "Özel gereksinimli öğrenciler için düzenlemeler", "5", "infrastructure", "Engelli Öğrenci Birimi / Program Başkanı", ["Erişilebilirlik ve uyarlama kanıtları"], ["Altyapı"]),
    _item("SABAK-R5-5.12", "Öğrenci süreçlerinin gözden geçirilmesi ve güncellenmesi", "5", "decisions", "Program Başkanı / Kalite", ["Gözden geçirme/karar kaydı"], ["Kurul & Karar"]),
    _item("SABAK-R5-5.13", "Öğrenci süreçlerine ilişkin PUKÖ", "5", "quality_cycle", "Program Başkanı / Kalite", ["PUKÖ ve etkililik kaydı"], ["PUKÖ"]),
    _item("SABAK-R5-5.14", "Mezunlar", "5", "graduates", "Program Başkanı / Mezun Ofisi", ["Mezun izleme ve istihdam verileri"], ["Mezun"]),
    _item("SABAK-R5-5.15", "Mezun izleme süreçlerinin gözden geçirilmesi ve güncellenmesi", "5", "graduates", "Program Başkanı / Mezun Ofisi", ["Mezun izleme değerlendirme/karar kaydı"], ["Mezun", "Kurul & Karar"]),
    _item("SABAK-R5-5.16", "Mezun izleme süreçlerine ilişkin PUKÖ", "5", "quality_cycle", "Program Başkanı / Kalite", ["Mezun verisine dayalı PUKÖ ve etkililik kaydı"], ["Mezun", "PUKÖ"]),
    # 6 · Öğretim Elemanları
    _item("SABAK-R5-6.1", "Öğretim elemanı sayı ve niteliğinin yeterliliği", "6", "faculty", "Program Başkanı / İK", ["Kadro listesi ve nitelik analizi"], ["Kadroyu Yönet"]),
    _item("SABAK-R5-6.2", "Öğretim elemanlarının kuruluş/sektör iletişim ve iş birliği", "6", "stakeholders", "Program Başkanı", ["Sektör/kuruluş iş birliği kanıtları"], ["Paydaş", "Kanıt Merkezi"]),
    _item("SABAK-R5-6.3", "Öğretim elemanı iş yükü dağılımı", "6", "faculty", "Program Başkanı / İK", ["Dönemsel iş yükü kayıtları"], ["Kadro İş Yükü"]),
    _item("SABAK-R5-6.4", "Öğretim elemanı seçme, atama ve yükseltme", "6", "manual", "İK / Birim Yönetimi", ["Atama-yükseltme ölçüt ve süreçleri"], ["Kontrollü Doküman"]),
    _item("SABAK-R5-6.5", "Kadro gelişim planlaması", "6", "faculty", "Program Başkanı / İK", ["Kadro gelişim planı"], ["Kadroyu Yönet"]),
    _item("SABAK-R5-6.6", "Akademik performans ve ödüllendirme", "6", "manual", "Birim Yönetimi / İK", ["Performans ve ödüllendirme sistemi/kanıtları"], ["Kontrollü Doküman", "Kanıt Merkezi"]),
    _item("SABAK-R5-6.7", "Öğretim elemanlarının mesleki/akademik gelişimi", "6", "faculty", "Program Başkanı / İK", ["Gelişim faaliyetleri ve katılım kayıtları"], ["Kadroyu Yönet", "Kanıt Merkezi"]),
    _item("SABAK-R5-6.8", "Öğretim elemanı süreçlerinin gözden geçirilmesi ve güncellenmesi", "6", "decisions", "Program Başkanı / Birim Yönetimi", ["Gözden geçirme/karar kaydı"], ["Kurul & Karar"]),
    _item("SABAK-R5-6.9", "Öğretim elemanı süreçlerine ilişkin PUKÖ", "6", "quality_cycle", "Program Başkanı / Kalite", ["PUKÖ ve etkililik kaydı"], ["PUKÖ"]),
    # 7 · Altyapı
    _item("SABAK-R5-7.1", "Eğitim için fiziki koşullar", "7", "infrastructure", "Birim Yönetimi / Program Başkanı", ["Derslik/laboratuvar/uygulama alanı envanteri"], ["Altyapı"]),
    _item("SABAK-R5-7.2", "Ders ve alan dışı etkinlikler için fiziki koşullar", "7", "infrastructure", "Birim Yönetimi", ["Etkinlik/sosyal alan envanteri"], ["Altyapı"]),
    _item("SABAK-R5-7.3", "Bilişim altyapısı", "7", "infrastructure", "Bilgi İşlem / Program Başkanı", ["Bilişim altyapısı, yazılım ve lisans envanteri"], ["Altyapı"]),
    _item("SABAK-R5-7.4", "Kütüphane ve bilgi kaynakları", "7", "infrastructure", "Kütüphane / Birim Yönetimi", ["Kütüphane/veritabanı kaynak ve kullanım kanıtı"], ["Altyapı"]),
    _item("SABAK-R5-7.5", "Güvenlik", "7", "infrastructure", "İSG / Birim Yönetimi", ["İSG, güvenlik ve risk yönetimi kayıtları"], ["Altyapı"]),
    _item("SABAK-R5-7.6", "Özel gereksinimliler için altyapı", "7", "infrastructure", "Engelli Öğrenci Birimi", ["Erişilebilirlik envanteri ve iyileştirmeler"], ["Altyapı"]),
    _item("SABAK-R5-7.7", "Program arşivi", "7", "evidence", "Program Başkanı", ["Program arşiv yapısı ve saklama kanıtları"], ["Kanıt Merkezi"]),
    _item("SABAK-R5-7.8", "Altyapı bakım ve işletme süreçleri", "7", "infrastructure", "İdari Birim", ["Bakım planı ve gerçekleşme kayıtları"], ["Altyapı"]),
    _item("SABAK-R5-7.9", "Uzaktan eğitim altyapısı", "7", "infrastructure", "UZEM / Bilgi İşlem", ["Uzaktan eğitim sistem/kapasite kanıtı"], ["Altyapı"]),
    _item("SABAK-R5-7.10", "Altyapı sınırlılıklarının giderilmesi", "7", "quality_cycle", "Birim Yönetimi / Kalite", ["Tespit edilen sınırlılık ve iyileştirme kayıtları"], ["PUKÖ", "Altyapı"]),
    _item("SABAK-R5-7.11", "Altyapıyı destekleyen insan kaynakları", "7", "faculty", "Birim Yönetimi / İK", ["Teknik/idari destek personeli ve görevleri"], ["Kadroyu Yönet"]),
    _item("SABAK-R5-7.12", "Altyapının gözden geçirilmesi ve güncellenmesi", "7", "decisions", "Birim Yönetimi", ["Gözden geçirme/karar kayıtları"], ["Kurul & Karar", "Altyapı"]),
    _item("SABAK-R5-7.13", "Altyapıya ilişkin PUKÖ", "7", "quality_cycle", "Birim Yönetimi / Kalite", ["PUKÖ ve etkililik kaydı"], ["PUKÖ"]),
    # 8 · Programın Yönetim Yapısı
    _item("SABAK-R5-8.1", "Program başkanı ve program yönetimi", "8", "program_identity", "Birim Yönetimi", ["Program başkanı görevlendirmesi ve görev tanımı"], ["Kontrollü Doküman"]),
    _item("SABAK-R5-8.2", "Program ihtiyaçlarının karşılanma yöntemi", "8", "decisions", "Program Başkanı / Birim Yönetimi", ["İhtiyaç belirleme ve karşılama süreç/kararları"], ["Kurul & Karar"]),
    _item("SABAK-R5-8.3", "Program gelişim planı", "8", "quality_cycle", "Program Başkanı / Kalite", ["Program gelişim planı ve izleme sonuçları"], ["PUKÖ", "Stratejik Kalite"]),
    _item("SABAK-R5-8.4", "Birim / Öz Değerlendirme Raporu", "8", "evidence", "Program Başkanı / Kalite", ["Birim/öz değerlendirme raporu"], ["Raporlar", "Kanıt Merkezi"]),
    _item("SABAK-R5-8.5", "Programın toplumsal katkısı", "8", "manual", "Program Başkanı", ["Toplumsal katkı faaliyet/etki kanıtları"], ["Kanıt Merkezi"]),
    _item("SABAK-R5-8.6", "Program yönetiminin gözden geçirilmesi ve güncellenmesi", "8", "decisions", "Program Başkanı / Birim Yönetimi", ["Gözden geçirme/karar kaydı"], ["Kurul & Karar"]),
    _item("SABAK-R5-8.7", "Program yönetimine ilişkin PUKÖ", "8", "quality_cycle", "Program Başkanı / Kalite", ["PUKÖ ve etkililik kaydı"], ["PUKÖ"]),
]

SABAK_ODR_R5_SOURCE = {
    "family": "SABAK",
    "document": "Öz Değerlendirme Raporu",
    "version": "Revizyon 5",
    "published": "2026-04-10",
    "criteria_revision": "Revizyon 4",
    "criteria_date": "2022-06-05",
    "url": "https://www.sabak.org.tr/index.php/tr/belgeler-ve-formlar",
    "item_count": 82,
}


# EPDAD ODR guide v1.3 — 39 substandards across seven standard areas.
EPDAD_ODR_V13_ITEMS = [
    # ES1
    _item("EPDAD-1.1.1", "Programın standartlar ve yeterlikler temelinde yapılandırılmış öğretim programına sahip olması", "1", "curriculum", "Program Başkanı / Eğitim Komisyonu", ["Öğretim programı", "Standart/yeterlik kapsama matrisi"], ["Müfredat & AKTS", "ÖÇ/PÇ"]),
    _item("EPDAD-1.1.2", "Öğretim programı ögeleri arasında tutarlılık bulunması", "1", "curriculum", "Program Başkanı", ["Amaç-içerik-yöntem-değerlendirme tutarlılık kanıtı"], ["Ders Dosyaları", "Müfredat & AKTS"]),
    _item("EPDAD-1.1.3", "Öğretim programının etkili öğretmen eğitimi sağlayacak nitelikte olması", "1", "curriculum", "Program Başkanı / Eğitim Komisyonu", ["Program tasarım gerekçesi", "Mesleki yeterlik kapsama kanıtı"], ["Müfredat & AKTS", "Kanıt Merkezi"]),
    _item("EPDAD-1.2.1", "Öğretim programının planlandığı biçimde uygulanması", "1", "curriculum", "Program Başkanı / Ders Sorumluları", ["Ders uygulama/dosya kanıtları", "Program gerçekleşme kayıtları"], ["Ders Dosyaları"]),
    _item("EPDAD-1.2.2", "Öğrencilere verilen geribildirimin mesleki gelişimi desteklemesi", "1", "official_exam", "Ders Sorumluları", ["Geribildirim/rubrik örnekleri", "Öğrenci değerlendirme kanıtı"], ["Ölçme & Değerlendirme"]),
    _item("EPDAD-1.3.1", "Öğrencilerin alan eğitimi yeterliklerini kazanmış olması", "1", "student_outcomes", "Program Başkanı / Ölçme-Değerlendirme", ["Alan eğitimi yeterlik sonuçları", "Doğrudan öğrenci çalışmaları"], ["ÖÇ/PÇ", "Öğrenci Karnesi"]),
    _item("EPDAD-1.3.2", "Öğrencilerin mesleki becerileri kazanmış olması", "1", "student_outcomes", "Program Başkanı / Uygulama Koordinatörü", ["Mesleki beceri ölçümleri", "Uygulama/staj kanıtları"], ["Ölçme & Değerlendirme", "Öğrenci Karnesi"]),
    _item("EPDAD-1.3.3", "Öğrencilerin öğretmenlik mesleğine ilişkin genel tutum ve değerlere sahip olması", "1", "stakeholders", "Program Başkanı / Ölçme-Değerlendirme", ["Tutum/değer ölçüm sonuçları", "Dolaylı ölçme/anket kanıtı"], ["Anketler", "Ölçme Güvence Planı"]),
    # ES2
    _item("EPDAD-2.1.1", "Öğretim elemanlarının sayı ve nitelik bakımından yeterli olması", "2", "faculty", "Birim Yönetimi / Program Başkanı", ["Kadro/nitelik analizi", "Özgeçmişler"], ["Kadroyu Yönet"]),
    _item("EPDAD-2.1.2", "Öğretim elemanlarına mesleki yenilenme ve araştırma olanaklarının sağlanması", "2", "faculty", "Birim Yönetimi", ["Gelişim/araştırma destekleri", "Katılım kayıtları"], ["Kadroyu Yönet", "Kanıt Merkezi"]),
    _item("EPDAD-2.2.1", "Öğretim elemanlarının tanımlı görev ve sorumluluklarını yerine getirmesi", "2", "faculty", "Program Başkanı", ["Görev tanımları", "İş yükü/gerçekleşme kayıtları"], ["Kadro İş Yükü", "Kontrollü Doküman"]),
    _item("EPDAD-2.2.2", "Öğretim elemanlarının mesleki gelişimlerini sürdürmesi", "2", "faculty", "Program Başkanı / İK", ["Mesleki gelişim faaliyetleri"], ["Kadroyu Yönet", "Kanıt Merkezi"]),
    _item("EPDAD-2.3.1", "Nitelikli öğretme-öğrenme faaliyetlerinin yürütülmesi", "2", "official_exam", "Ders Sorumluları / Program Başkanı", ["Ders dosyaları ve öğretim uygulaması örnekleri"], ["Ders Dosyaları", "Ölçme & Değerlendirme"]),
    _item("EPDAD-2.3.2", "Nitelikli araştırma, proje ve yayınların gerçekleştirilmesi", "2", "manual", "Birim Yönetimi / Öğretim Elemanları", ["Araştırma/proje/yayın performansı"], ["Kanıt Merkezi"]),
    _item("EPDAD-2.3.3", "Topluma yarar sağlayan faaliyetlerin gerçekleştirilmesi", "2", "manual", "Birim Yönetimi / Program Başkanı", ["Toplumsal katkı faaliyet ve etki kanıtları"], ["Kanıt Merkezi"]),
    # ES3
    _item("EPDAD-3.1.1", "Programa kabul edilen öğrencilerin gerekli niteliklere sahip olması", "3", "students", "Öğrenci İşleri / Program Başkanı", ["Kabul koşulları", "Giriş/yerleşme verileri"], ["OBS/Proliz", "Öğrenci Kayıtları"]),
    _item("EPDAD-3.2.1", "Öğrencilerin derslere ve kişisel/mesleki gelişim faaliyetlerine etkin katılması", "3", "stakeholders", "Program Başkanı", ["Ders/etkinlik katılım kayıtları", "Öğrenci geri bildirimi"], ["Paydaş", "Kanıt Merkezi"]),
    _item("EPDAD-3.3.1", "Mezunların kariyer süreçlerinin izlenmesi", "3", "graduates", "Program Başkanı / Mezun Ofisi", ["Mezun izleme ve kariyer verileri"], ["Mezun"]),
    # ES4
    _item("EPDAD-4.1.1", "Uygulama okullarına ilişkin idari düzenleme ve belgelerin bulunması", "4", "manual", "Uygulama Koordinatörü", ["Protokol/yönerge/görevlendirme belgeleri"], ["Kontrollü Doküman", "Kanıt Merkezi"]),
    _item("EPDAD-4.2.1", "Fakülte, il millî eğitim ve uygulama paydaşları arasında yeterli iş birliği bulunması", "4", "stakeholders", "Fakülte / Uygulama Koordinatörü", ["İş birliği/protokol/toplantı kanıtları"], ["Paydaş", "Kanıt Merkezi"]),
    _item("EPDAD-4.2.2", "Uygulama okullarında uygun öğrenme ortamının sağlanması", "4", "manual", "Uygulama Koordinatörü", ["Uygulama okulu değerlendirme/ortam kanıtları"], ["Kanıt Merkezi"]),
    _item("EPDAD-4.3.1", "Öğretmenlik uygulamasına katılan öğrencilerin tanımlı yeterlikleri kazanması", "4", "student_outcomes", "Uygulama Koordinatörü / Ölçme-Değerlendirme", ["Uygulama yeterlik ölçümleri", "Rubrik/öğrenci çalışmaları"], ["Ölçme & Değerlendirme", "Öğrenci Karnesi"]),
    # ES5
    _item("EPDAD-5.1.1", "Program için gerekli tesis ve donanımın bulunması", "5", "infrastructure", "Birim Yönetimi", ["Tesis/donanım envanteri"], ["Altyapı"]),
    _item("EPDAD-5.1.2", "Yeterli öğrenme kaynaklarının bulunması", "5", "infrastructure", "Kütüphane / Birim Yönetimi", ["Öğrenme/kütüphane kaynak envanteri"], ["Altyapı"]),
    _item("EPDAD-5.1.3", "Dersliklerin kapasite ve nitelik bakımından yeterli olması", "5", "infrastructure", "Birim Yönetimi", ["Derslik kapasite/nitelik kanıtı"], ["Altyapı"]),
    _item("EPDAD-5.1.4", "Öğretim elemanı çalışma alanı, donanım ve teknik desteğinin yeterli olması", "5", "infrastructure", "Birim Yönetimi", ["Ofis/donanım/teknik destek envanteri"], ["Altyapı"]),
    _item("EPDAD-5.1.5", "Özel gereksinimli bireyler için erişilebilirliğin sağlanması", "5", "infrastructure", "Engelli Öğrenci Birimi / Birim Yönetimi", ["Erişilebilirlik envanteri/uyarlamalar"], ["Altyapı"]),
    _item("EPDAD-5.2.1", "Derslik, tesis ve donanımın etkili kullanılması", "5", "infrastructure", "Birim Yönetimi", ["Kullanım/kapasite kayıtları"], ["Altyapı"]),
    _item("EPDAD-5.2.2", "Kütüphane ve öğrenme kaynaklarının etkili kullanılması", "5", "infrastructure", "Kütüphane / Birim Yönetimi", ["Kullanım istatistikleri"], ["Altyapı"]),
    _item("EPDAD-5.3.1", "Derslik, tesis, kütüphane ve öğrenme kaynaklarının etkili yönetilmesi", "5", "decisions", "Birim Yönetimi", ["Kaynak yönetim/iyileştirme kararları"], ["Kurul & Karar", "Altyapı"]),
    # ES6
    _item("EPDAD-6.1.1", "Fakültenin öğretmen eğitimi misyon ve vizyonunun bulunması", "6", "institution_profile", "Fakülte Yönetimi", ["Misyon-vizyon ve kamuya açık yayın"], ["Kurumsal Raporlama", "Kontrollü Doküman"]),
    _item("EPDAD-6.1.2", "Yönetim yapısının misyon ve vizyonla uyumlu olması", "6", "decisions", "Fakülte Yönetimi", ["Organizasyon şeması", "Görev/yetki ve stratejik uyum"], ["Kurul & Karar", "Kontrollü Doküman"]),
    _item("EPDAD-6.2.1", "Yönetim birimlerinin etkili işlemesi", "6", "decisions", "Fakülte Yönetimi", ["Kurul/komisyon çalışma ve karar kayıtları"], ["Kurul & Karar"]),
    _item("EPDAD-6.2.2", "Yönetimin öğretmen eğitiminin gelişimini desteklemesi", "6", "quality_cycle", "Fakülte Yönetimi / Kalite", ["Gelişim kararları", "PUKÖ/stratejik hedef kanıtı"], ["PUKÖ", "Stratejik Kalite"]),
    _item("EPDAD-6.2.3", "Ulusal ve uluslararası iş birliklerinin yürütülmesi", "6", "stakeholders", "Fakülte Yönetimi / Uluslararası Ofis", ["İş birliği/protokol/faaliyet kanıtları"], ["Paydaş", "Kanıt Merkezi"]),
    _item("EPDAD-6.3.1", "Yönetimin gerekli kaynakları sağlaması ve etkili kullanması", "6", "decisions", "Fakülte Yönetimi / Mali İşler", ["Kaynak/bütçe planı ve kullanım kanıtı"], ["Bütçe", "Kurul & Karar"]),
    # ES7
    _item("EPDAD-7.1.1", "Kalite güvencesi politika ve süreçlerinin bulunması", "7", "closed_cycle", "Kalite Birimi / Fakülte Yönetimi", ["Kalite politikası", "Kalite süreçleri ve sorumluluklar"], ["Kontrollü Doküman", "PUKÖ"]),
    _item("EPDAD-7.2.1", "Fakülte bütününü geliştiren bütünleşik değerlendirme sisteminin işletilmesi", "7", "quality_cycle", "Kalite Birimi / Fakülte Yönetimi", ["Değerlendirme sistemi", "İzleme/iyileştirme sonuçları"], ["PUKÖ", "Raporlar"]),
    _item("EPDAD-7.3.1", "Mezun izleme bulgularının kalite güvencesine yansıtılması", "7", "graduates", "Program Başkanı / Kalite", ["Mezun izleme bulguları", "Karar/PUKÖ bağlantısı"], ["Mezun", "PUKÖ", "Kurul & Karar"]),
]

EPDAD_ODR_V13_SOURCE = {
    "family": "EPDAD",
    "document": "Öz Değerlendirme Raporu Hazırlama Kılavuzu",
    "version": "1.3",
    "standards_version": "1.1",
    "standards_date": "2024-12",
    "url": "https://epdad.org.tr/icerik/oz-degerlendirme-raporu",
    "standard_areas": 7,
    "substandards": 39,
}


FRAMEWORK_PREPARATION_CATALOG = {
    "TURAK": {"items": TURAK_ODR_V7_ITEMS, "source": TURAK_ODR_V7_SOURCE},
    "SABAK": {"items": SABAK_ODR_R5_ITEMS, "source": SABAK_ODR_R5_SOURCE},
    "EPDAD": {"items": EPDAD_ODR_V13_ITEMS, "source": EPDAD_ODR_V13_SOURCE},
}


def framework_preparation_catalog(family: str) -> dict[str, Any]:
    key = (family or "").strip().upper()
    if key not in FRAMEWORK_PREPARATION_CATALOG:
        raise ValueError("Hazırlık matrisi TURAK, SABAK veya EPDAD için tanımlıdır")
    cfg = FRAMEWORK_PREPARATION_CATALOG[key]
    return {"family": key, "items": [dict(x) for x in cfg["items"]], "source": dict(cfg["source"])}


def framework_preparation_valid_codes(family: str) -> set[str]:
    return {str(x["code"]) for x in framework_preparation_catalog(family)["items"]}
