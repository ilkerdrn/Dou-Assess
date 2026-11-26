from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
import re
import unicodedata
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models as m
from ..authz import require_program_access
from .framework_preparation_catalog import framework_preparation_catalog, framework_preparation_valid_codes


EXAM_TYPE_CATALOG = [
    {"value": "Vize", "label": "Vize", "recommended_duration_minutes": 60},
    {"value": "Final", "label": "Final", "recommended_duration_minutes": 60},
    {"value": "Bütünleme", "label": "Bütünleme", "recommended_duration_minutes": 60},
    {"value": "Mazeret", "label": "Mazeret", "recommended_duration_minutes": 60},
    {"value": "Tek Ders", "label": "Tek Ders", "recommended_duration_minutes": 60},
    {"value": "Muafiyet", "label": "Muafiyet", "recommended_duration_minutes": 60},
    {"value": "Kısa Sınav", "label": "Kısa Sınav", "recommended_duration_minutes": 20},
    {"value": "Uygulama", "label": "Uygulama", "recommended_duration_minutes": 60},
]

CLASS_LEVELS = ["1. Sınıf", "2. Sınıf", "3. Sınıf", "4. Sınıf"]
TERMS = ["Güz", "Bahar", "Yaz"]
COURSE_CATEGORIES = [
    "Genel / Zorunlu", "Seçmeli", "Programa / Alana Özgü Mesleki", "Programa Özgü Çıktı",
    "Dış Paydaş Önerili", "İşletmede Mesleki Eğitim", "Staj", "Uygulamalı Ders",
    "Güncel Mesleki Program / Yazılım",
]
STAKEHOLDER_TYPES = [
    "Öğrenci", "Mezun", "Öğretim Elemanı", "İşveren", "Sektör Temsilcisi",
    "Danışma Kurulu", "Kamu Kurumu", "STK", "Diğer",
]
STAKEHOLDER_ENGAGEMENT_TYPES = [
    "Görüş / Geri Bildirim", "Anket", "Odak Grup", "Toplantı", "Danışma Kurulu", "Çalıştay", "Mülakat", "Diğer",
]
GRADUATE_EMPLOYMENT_STATUSES = [
    "Çalışıyor - Alanında", "Çalışıyor - Alan Dışı", "İş Arıyor", "Eğitime Devam", "Girişimci", "Bilinmiyor",
]
INSTRUCTOR_TITLES = [
    "Prof. Dr.", "Doç. Dr.", "Dr. Öğr. Üyesi", "Öğr. Gör. Dr.", "Öğr. Gör.",
    "Araş. Gör. Dr.", "Araş. Gör.", "Uzm.", "Diğer",
]
EMPLOYMENT_TYPES = ["Tam Zamanlı", "Yarı Zamanlı", "Ders Saat Ücretli", "Misafir"]
INFRASTRUCTURE_TYPES = [
    "Bilgisayar Laboratuvarı", "Derslik", "Atölye", "Uygulama Laboratuvarı", "Kütüphane / Bilgi Kaynağı",
    "Ağ / Sunucu Altyapısı", "Yazılım Lisansı", "Erişilebilirlik Donanımı", "İlk Yardım / İSG", "Sosyal Alan", "Diğer",
]
QUALITY_STATUSES = [
    {"value": "not_started", "label": "Eksik / Başlanmadı", "maturity": 1},
    {"value": "planned", "label": "Planlandı", "maturity": 2},
    {"value": "implemented", "label": "Uygulanıyor", "maturity": 3},
    {"value": "measured", "label": "İzleniyor / Ölçülüyor", "maturity": 4},
    {"value": "improved", "label": "İyileştirildi / Kanıtlı", "maturity": 5},
]
QUALITY_STATUS_VALUES = {x["value"] for x in QUALITY_STATUSES}
QUALITY_CYCLE_STATUSES = ["planned", "doing", "checking", "acting", "closed"]
GOVERNANCE_BODIES = [
    "Program Kurulu", "Bölüm Kurulu", "Fakülte Kurulu", "Fakülte Yönetim Kurulu", "MYO Kurulu", "MYO Yönetim Kurulu", "Senato", "Üniversite Kalite Komisyonu", "Danışma Kurulu", "Kalite Komisyonu", "Diğer",
]


def _sc(code: str, title: str, required_evidence: list[str], automation_key: str = "manual") -> dict[str, Any]:
    return {
        "code": code,
        "title": title,
        "required_evidence": required_evidence,
        "automation_key": automation_key,
    }


MEDEK_PROGRAM_OUTCOMES_V11 = [
    {"code": "PÇ1", "title": "Temel, güncel ve uygulamalı mesleki bilgi"},
    {"code": "PÇ2", "title": "İSG, çevre bilinci ve kalite süreçleri"},
    {"code": "PÇ3", "title": "Güncel mesleki gelişme ve uygulamaları izleme/kullanma"},
    {"code": "PÇ4", "title": "Mesleki bilişim teknolojilerini etkin kullanma"},
    {"code": "PÇ5", "title": "Mesleki problemleri analitik ve eleştirel değerlendirme"},
    {"code": "PÇ6", "title": "Yazılı ve sözlü etkin iletişim"},
    {"code": "PÇ7", "title": "Ekip üyesi olarak sorumluluk alma ve problem çözme"},
    {"code": "PÇ8", "title": "Kariyer yönetimi ve yaşam boyu öğrenme farkındalığı"},
    {"code": "PÇ9", "title": "Toplumsal, bilimsel, kültürel ve etik değerler"},
    {"code": "PÇ10", "title": "Yabancı dil ile alan bilgisini izleme ve iletişim"},
]

MEDEK_V11_CRITERIA = [
    {"code": "1", "name": "Öğrenciler", "subcriteria": [
        _sc("1.1", "Programa yerleşen öğrencilerin akademik yeterliliği", ["Öğrenci kabul/YKS istatistikleri", "Yıllara göre öğrenci profili"], "students"),
        _sc("1.2", "Öğrenci kabul göstergelerinin yıllara göre izlenmesi", ["YKS puan-kontenjan-doluluk trendi", "Program değerlendirme kaydı"], "students"),
        _sc("1.3", "Öğrenci kabul süreçlerinin yazılı ve uygulanır olması", ["Kabul/yatay geçiş/uluslararası öğrenci prosedürü", "Uygulama örneği"], "manual"),
        _sc("1.4", "Önceki öğrenmelerin kredilendirilmesi", ["Muafiyet/intibak prosedürü", "Örnek kurul kararı"], "decisions"),
        _sc("1.5", "Öğrenci merkezli öğretim yaklaşımı", ["Ders izlenceleri", "Öğretim yöntemi örnekleri", "Öğrenci geri bildirimi"], "stakeholders"),
        _sc("1.6", "Kurum/kuruluş iş birliklerinin işletilmesi", ["Protokol/iş birliği belgesi", "Uygulama/etkinlik kanıtı"], "manual"),
        _sc("1.7", "Öğrenci hareketliliği ve değişim düzenlemeleri", ["Hareketlilik/değişim prosedürü", "Katılım kayıtları"], "manual"),
        _sc("1.8", "Öğrenci merkezli ölçme ve değerlendirme", ["Sınav/rubrik örnekleri", "ÖÇ bazlı ölçme sonuçları"], "official_exam"),
        _sc("1.9", "Akademik gelişim ve kariyer danışmanlığı", ["Danışmanlık görevlendirmeleri", "Kariyer/danışmanlık faaliyet kaydı"], "manual"),
        _sc("1.10", "Ders başarısı izleme ve ders planlama rehberliği", ["Öğrenci başarı izleme raporu", "Danışmanlık/uyarı kaydı"], "student_outcomes"),
        _sc("1.11", "Öğrenci geri bildirimlerinin iyileştirmede kullanılması", ["Öğrenci anket/geri bildirim sonucu", "Geri bildirimden doğan karar/PUKÖ"], "stakeholders"),
        _sc("1.12", "Şeffaf, adil ve önceden ilan edilmiş başarı değerlendirmesi", ["Ders değerlendirme yöntemi", "Sınav/rubrik ve ilan edilmiş kriterler"], "official_exam"),
        _sc("1.13", "Mezuniyet koşullarının sistematik kontrolü", ["Mezuniyet kontrol listesi", "Mezuniyet/çıktı doğrulama kaydı"], "graduation_snapshots"),
    ]},
    {"code": "2", "name": "Program Eğitim Amaçları", "subcriteria": [
        _sc("2.1", "Program eğitim amaç ve hedeflerinin tanımlanması ve yayımlanması", ["Program eğitim amaçları", "Kamuya açık yayın/URL"], "pea"),
        _sc("2.2", "Eğitim amaçları için anahtar performans göstergeleri", ["PEA-KPI listesi", "Hedef ve gerçekleşme kayıtları"], "pea"),
        _sc("2.3", "Eğitim amaçlarının misyon ve vizyonla uyumu", ["Misyon-vizyon uyum matrisi", "Kurul onayı"], "pea"),
        _sc("2.4", "Eğitim amaçlarına ulaşma için ölçme-değerlendirme sistemi", ["PEA ölçme planı", "Ölçüm araçları ve sorumluluklar"], "pea"),
        _sc("2.5", "Eğitim amaçlarına ulaşma düzeyinin sistematik izlenmesi", ["PEA izleme sonuçları", "Dönemsel değerlendirme raporu"], "pea"),
        _sc("2.6", "Program misyon ve vizyonunun tanımlanması ve yayımlanması", ["Program misyon-vizyon belgesi", "Kamuya açık yayın/URL"], "program_identity"),
        _sc("2.7", "İç ve dış paydaş katılım mekanizmaları", ["Paydaş listesi", "Toplantı/anket kayıtları", "Karar/aksiyon izi"], "stakeholders"),
    ]},
    {"code": "3", "name": "Program Çıktıları", "program_outcomes": MEDEK_PROGRAM_OUTCOMES_V11, "subcriteria": [
        _sc("3.1", "Program çıktıları ile ders öğrenme çıktılarının tanımlı ve ilişkili olması", ["Program çıktıları", "Ders ÖÇ-PÇ matrisi", "MEDEK PÇ kapsama matrisi"], "lo_po"),
        _sc("3.2", "Program çıktılarının dönemsel ölçülmesi ve belgelenmesi", ["PÇ ölçme planı", "Doğrudan ölçme sonuçları", "Öğrenci karnesi/çıktı sonuçları"], "student_outcomes"),
    ]},
    {"code": "4", "name": "Sürekli İyileştirme", "subcriteria": [
        _sc("4.1", "Ders ÖÇ ve PÇ sonuçlarının sistematik izlenmesi ve iyileştirilmesi", ["ÖÇ/PÇ analiz raporu", "PUKÖ/iyileştirme kaydı", "Etkililik sonucu"], "quality_cycle"),
        _sc("4.2", "İç ve dış paydaş geri bildirimlerinin iyileştirmede kullanılması", ["Paydaş geri bildirimi", "Kurul kararı", "PUKÖ/aksiyon"], "stakeholders"),
        _sc("4.3", "Mezun izleme verilerinin iyileştirmeye yansıtılması", ["Mezun izleme analizi", "Kurul kararı", "İyileştirme kaydı"], "graduates"),
    ]},
    {"code": "5", "name": "Öğretim Planı", "subcriteria": [
        _sc("5.1", "Mesleki ders ve programa özgü çıktı AKTS eşikleri", ["Müfredat/AKTS tablosu", "Programa özgü ders-çıktı eşlemesi"], "medek_51"),
        _sc("5.2", "Dış paydaş önerili dersler için en az 5 AKTS", ["Dış paydaş önerisi", "Müfredat/AKTS tablosu", "Kurul kararı"], "medek_52"),
        _sc("5.3", "Uygulama/staj/güncel teknoloji için en az 15 AKTS", ["Müfredat/AKTS tablosu", "Staj/uygulama/güncel teknoloji ders kanıtı"], "medek_53"),
        _sc("5.4", "Öğretim planının programa özgü ölçütleri içermesi", ["Programa özgü ölçüt-ders matrisi", "Ders ölçme kanıtları"], "program_specific"),
        _sc("5.5", "AKTS iş yüküne dayalı öğrenme çıktısı merkezli planın yayımlanması", ["Ders bilgi paketleri", "AKTS iş yükü hesapları", "Kamuya açık müfredat"], "curriculum"),
        _sc("5.6", "Öğretim planı uygulama ve sürekli iyileştirme yönetim sistemi", ["Müfredat yönetim prosedürü", "Kurul kararları", "Müfredat iyileştirme döngüsü"], "decisions"),
    ]},
    {"code": "6", "name": "Öğretim Kadrosu", "subcriteria": [
        _sc("6.1", "Öğretim kadrosunun nicelik ve nitelik yeterliliği", ["Akademik kadro envanteri", "Uzmanlık-ders eşlemesi", "İş yükü"], "faculty"),
        _sc("6.2", "Teşvik ve ödüllendirme mekanizmaları", ["Teşvik/ödül yönergesi", "Uygulama örnekleri"], "manual"),
        _sc("6.3", "Öğretim elemanı alım/yükseltme sistemi", ["Atama-yükseltme kriterleri", "Uygulama kaydı"], "manual"),
        _sc("6.4", "Niteliklere göre adil ve şeffaf ders dağılımı", ["Ders yükü dağılımı", "Uzmanlık-ders eşleşmesi", "Kurul kararı"], "faculty"),
    ]},
    {"code": "7", "name": "Altyapı", "subcriteria": [
        _sc("7.1", "Yeterli öğrenme ortamları ve kaynakları", ["Derslik/lab/atölye envanteri", "Kapasite ve kullanım kaydı"], "infrastructure"),
        _sc("7.2", "Ders dışı etkinlik altyapısı", ["Sosyal/mesleki alan envanteri", "Etkinlik kullanım kanıtı"], "infrastructure"),
        _sc("7.3", "Güvenlik, ilk yardım ve İSG önlemleri", ["İSG kayıtları", "Risk/ilk yardım planı", "Eğitim/tatbikat kanıtı"], "infrastructure"),
        _sc("7.4", "Bilgiye erişim olanakları", ["Kütüphane/veritabanı kaynakları", "Erişim/kullanım kanıtı"], "infrastructure"),
        _sc("7.5", "Özel gereksinimli öğrenciler için erişilebilirlik", ["Erişilebilirlik envanteri", "Uygunluk/iyileştirme kaydı"], "infrastructure"),
        _sc("7.6", "BİT altyapısının eğitim gereksinimlerini karşılaması", ["BİT/ağ/yazılım envanteri", "Lisans/kapasite/bakım kayıtları"], "infrastructure"),
    ]},
    {"code": "8", "name": "Yönetim ve İdari Birimlerin Yapısı", "subcriteria": [
        _sc("8.1", "Misyonla uyumlu yönetim modeli ve organizasyon", ["Organizasyon şeması", "Görev/yetki tanımları", "Stratejik uyum"], "decisions"),
        _sc("8.2", "İnsan kaynaklarının etkin kullanım prosedürleri", ["İK prosedürleri", "İş yükü/görev dağılımı"], "manual"),
        _sc("8.3", "Akademik ve idari hizmet içi eğitim süreçleri", ["Hizmet içi eğitim planı", "Katılım kayıtları"], "manual"),
        _sc("8.4", "Hesap verebilirlik ve kamuoyunu bilgilendirme", ["Kamuya açık program bilgileri", "Faaliyet/kalite raporu", "Duyuru/şeffaflık kanıtı"], "evidence"),
    ]},
    {"code": "9", "name": "Programa Özgü Ölçütler", "subcriteria": [
        _sc("9.1", "Ders ve ölçme yöntemleriyle programa özgü ölçütlerin sağlanması", ["Programa özgü ölçüt listesi", "Ölçüt-ders matrisi", "Doğrudan öğrenci çalışma/ölçme kanıtı"], "program_specific"),
    ]},
]



# ---------------------------------------------------------------------------
# MEDEK 2026 / ÖDR v1.1 preparation matrix (6.45)
# ---------------------------------------------------------------------------
# The official SER/ÖDR form is more granular than the accreditation criteria
# registry.  Keep the 46-subcriterion framework intact and track the report
# prompts separately so report preparation never changes accreditation logic.
def _odr_item(code: str, title: str, mapped: str, automation: str, owner: str,
              evidence: list[str], sources: list[str]) -> dict[str, Any]:
    return {
        "code": code, "title": title, "mapped_subcriterion": mapped,
        "automation_key": automation, "owner_role": owner,
        "required_evidence": evidence, "source_modules": sources,
    }

MEDEK_ODR_V11_ITEMS = [
    # Ölçüt 1 · Öğrenciler (14)
    _odr_item("1.1.1", "Programa öğrenci kabul sürecinin açıklanması", "1.1", "students", "Öğrenci İşleri / Program Başkanı", ["Kabul süreci/prosedürü", "YKS/yerleşme verisi"], ["OBS/Proliz", "Öğrenci Kayıtları"]),
    _odr_item("1.1.2", "Son iki yıla ait giriş sınavı ve yerleşme göstergeleri", "1.1", "students", "Öğrenci İşleri", ["Tablo 1.1 verileri", "Güncel yerleşme istatistiği"], ["OBS/Proliz", "Öğrenci Kayıtları"]),
    _odr_item("1.2", "Kontenjan, yerleşen öğrenci ve başarı göstergelerinin yıllık analizi", "1.2", "students", "Program Başkanı", ["Tablo 1.2", "Yıllık trend analizi"], ["OBS/Proliz", "Quality360"]),
    _odr_item("1.3", "Yatay geçiş, ÇAP/YAP ve kurumlar arası kredi tanıma uygulamaları", "1.3", "manual", "Öğrenci İşleri / Program Başkanı", ["Yatay geçiş/intibak mevzuatı", "Tablo 1.3", "Uygulama örneği"], ["Kontrollü Doküman", "Kurul & Karar"]),
    _odr_item("1.4", "Önceki öğrenmelerin tanınması ve kredilendirilmesi", "1.4", "decisions", "Program Başkanı", ["Muafiyet/intibak prosedürü", "Kurul kararı örneği"], ["Kurul & Karar", "Kontrollü Doküman"]),
    _odr_item("1.5", "Öğrenci merkezli öğretim uygulamalarının gösterilmesi", "1.5", "stakeholders", "Ders Sorumluları / Program Başkanı", ["Ders izlenceleri", "Aktif öğrenme örnekleri", "Öğrenci geri bildirimi"], ["Ders Dosyaları", "Paydaş"]),
    _odr_item("1.6", "Kurum ve sektör iş birliklerinin örneklerle açıklanması", "1.6", "manual", "Program Başkanı", ["Protokol/iş birliği belgesi", "Uygulama/etkinlik kanıtı"], ["Kanıt Merkezi", "Paydaş"]),
    _odr_item("1.7", "Öğrenci hareketliliğini destekleyen düzenlemeler", "1.7", "manual", "Uluslararası Ofis / Program Başkanı", ["Hareketlilik prosedürü", "Katılım kayıtları"], ["Kontrollü Doküman", "Kanıt Merkezi"]),
    _odr_item("1.8", "Yetkinlik temelli ölçme ve değerlendirme yöntemleri", "1.8", "official_exam", "Ders Sorumluları", ["Sınav/rubrik örnekleri", "ÖÇ bazlı sonuçlar"], ["Ölçme & Değerlendirme", "ÖÇ/PÇ"]),
    _odr_item("1.9", "Akademik gelişim ve kariyer danışmanlığı", "1.9", "manual", "Danışman / Program Başkanı", ["Danışman görevlendirmesi", "Kariyer/danışmanlık faaliyeti"], ["Kanıt Merkezi", "Öğrenci Karnesi"]),
    _odr_item("1.10", "Öğrenci başarısının izlenmesi ve ders planlama danışmanlığı", "1.10", "student_outcomes", "Danışman / Program Başkanı", ["Öğrenci başarı izleme raporu", "Danışmanlık/uyarı kaydı"], ["Öğrenci Karnesi", "Raporlar"]),
    _odr_item("1.11", "Öğrenci geri bildirimlerinin sürekli iyileştirmede kullanılması", "1.11", "stakeholders", "Program Başkanı / Kalite", ["Öğrenci geri bildirimi", "Kurul kararı veya PUKÖ"], ["Paydaş", "PUKÖ", "Kurul & Karar"]),
    _odr_item("1.12", "Başarı ölçmenin şeffaf, adil ve tutarlı olduğunun gösterilmesi", "1.12", "official_exam", "Ders Sorumluları", ["İlan edilmiş değerlendirme yöntemi", "Sınav/rubrik/notlandırma örneği"], ["Ders Dosyaları", "Ölçme & Değerlendirme"]),
    _odr_item("1.13", "Mezuniyet koşullarının sistematik ve güvenilir kontrolü", "1.13", "graduation_snapshots", "Öğrenci İşleri / Program Başkanı", ["Mezuniyet kontrol listesi", "Dondurulmuş mezuniyet çıktı karnesi"], ["Öğrenci Karnesi", "Mezuniyet Snapshot"]),

    # Ölçüt 2 · Program Eğitim Amaçları (11)
    _odr_item("2.1", "Program eğitim amaçlarının listelenmesi ve kamuya açık olması", "2.1", "pea", "Program Başkanı", ["PEA listesi", "Kamuya açık yayın/URL"], ["PEA", "Kontrollü Doküman"]),
    _odr_item("2.2", "PEA erişim düzeyi için KPI ve hedeflerin tanımlanması", "2.2", "pea", "Program Başkanı / Kalite", ["PEA KPI listesi", "Hedef-gerçekleşme kaydı"], ["PEA", "Stratejik Kalite"]),
    _odr_item("2.3.1", "PEA'ların MEDEK tanımıyla uyumunun değerlendirilmesi", "2.3", "pea", "Program Başkanı", ["PEA uygunluk değerlendirmesi"], ["PEA"]),
    _odr_item("2.3.2", "PEA'ların üniversite misyon/vizyonuyla uyumu", "2.3", "pea", "Program Başkanı / Kalite", ["Üniversite misyon-vizyon uyum matrisi"], ["PEA", "Kurumsal Raporlama"]),
    _odr_item("2.3.3", "PEA'ların MYO misyon/vizyonuyla uyumu", "2.3", "pea", "Program Başkanı / MYO Yönetimi", ["MYO misyon-vizyon uyum matrisi"], ["PEA", "Kurumsal Raporlama"]),
    _odr_item("2.4.1", "PEA'lara nasıl ulaşılacağının açıklanması", "2.4", "pea", "Program Başkanı", ["PEA gerçekleştirme planı"], ["PEA", "Stratejik Kalite"]),
    _odr_item("2.4.2", "PEA erişimini belirleyen ölçme-değerlendirme sisteminin açıklanması", "2.4", "pea", "Program Başkanı / Kalite", ["PEA ölçme planı", "Ölçüm araçları/sorumluluklar"], ["PEA", "Stratejik Kalite"]),
    _odr_item("2.5", "PEA'lara ulaşma düzeyinin kanıtlarla gösterilmesi", "2.5", "pea", "Program Başkanı / Kalite", ["PEA dönemsel sonuçları", "Değerlendirme/iyileştirme kaydı"], ["PEA", "PUKÖ"]),
    _odr_item("2.6", "Program misyon ve vizyonunun tanımlanması ve yayımlanması", "2.6", "program_identity", "Program Başkanı", ["Program misyon-vizyonu", "Kamuya açık yayın/URL"], ["Program Tanımı", "Kontrollü Doküman"]),
    _odr_item("2.7.1", "PEA belirleme ve uygulamada iç paydaş katılımı", "2.7", "stakeholders", "Program Başkanı", ["İç paydaş toplantı/anket kayıtları", "Karar izi"], ["Paydaş", "Kurul & Karar"]),
    _odr_item("2.7.2", "PEA belirleme ve uygulamada dış paydaş katılımı", "2.7", "stakeholders", "Program Başkanı", ["Dış paydaş toplantı/anket kayıtları", "Karar izi"], ["Paydaş", "Kurul & Karar"]),

    # Ölçüt 3 · Program Çıktıları (6)
    _odr_item("3.1.1", "Program çıktılarının belirlenme yönteminin açıklanması", "3.1", "lo_po", "Program Başkanı", ["PÇ belirleme yöntemi", "PÇ listesi"], ["ÖÇ/PÇ", "Kurul & Karar"]),
    _odr_item("3.1.2", "PÇ belirleme yönteminin uygulandığının kanıtlanması", "3.1", "lo_po", "Program Başkanı", ["Paydaş/kurul uygulama kayıtları", "PÇ revizyon izi"], ["ÖÇ/PÇ", "Paydaş", "Kurul & Karar"]),
    _odr_item("3.1.3", "Program çıktıları ile PEA ilişkisinin gösterilmesi", "3.1", "pea", "Program Başkanı", ["PEA-PÇ ilişki matrisi"], ["PEA", "ÖÇ/PÇ"]),
    _odr_item("3.1.4", "Program çıktılarının MEDEK program çıktılarını kapsadığının gösterilmesi", "3.1", "medek_outcomes", "Program Başkanı / Kalite", ["MEDEK PÇ kapsama matrisi"], ["ÖÇ/PÇ", "Framework Mapping"]),
    _odr_item("3.2.1", "Mezuniyet aşamasındaki her öğrencinin PÇ erişim düzeyinin gösterilmesi", "3.2", "graduation_snapshots", "Program Başkanı / Ders Sorumluları", ["Öğrenci bazlı PÇ karnesi", "Doğrudan ölçme sonuçları"], ["Öğrenci Karnesi", "ÖÇ/PÇ"]),
    _odr_item("3.2.2", "PÇ başarısını kanıtlayan öğrenci çalışmalarının listelenmesi ve ilişkilendirilmesi", "3.2", "student_outcomes", "Program Başkanı / Ders Sorumluları", ["Sınav/proje/ödev örnekleri", "PÇ-kanıt ilişki listesi"], ["Kanıt Merkezi", "Ölçme & Değerlendirme"]),

    # Ölçüt 4 · Sürekli İyileştirme (3)
    _odr_item("4.1", "Somut veriye dayalı sorun ve iyileştirme döngülerinin gösterilmesi", "4.1", "quality_cycle", "Program Başkanı / Kalite", ["Sorun/veri kaynağı", "Sorumlu-tarih-izleme-etkililik içeren PUKÖ"], ["PUKÖ", "ÖÇ/PÇ"]),
    _odr_item("4.2", "Ölçüt 2/3 ve diğer alanlardaki iyileştirmelerin paydaş geri bildirimiyle sistematik yürütülmesi", "4.2", "stakeholders", "Program Başkanı / Kalite", ["Paydaş girdisi", "Kurul kararı", "PUKÖ ve sonuç"], ["Paydaş", "Kurul & Karar", "PUKÖ"]),
    _odr_item("4.3", "Mezun izleme verilerinin iyileştirmede kullanılması", "4.3", "graduates", "Program Başkanı / Kalite", ["Mezun izleme verisi", "İyileştirmeye dönüşen karar/PUKÖ"], ["Mezun", "PUKÖ"]),

    # Ölçüt 5 · Eğitim Planı (6)
    _odr_item("5.1", "Eğitim planı ve ders/sınıf büyüklüğü tablolarının hazırlanması", "5.1", "curriculum", "Program Başkanı / Bologna", ["Tablo 5.1", "Tablo 5.2", "AKTS/ders planı"], ["Müfredat & AKTS", "OBS/Proliz"]),
    _odr_item("5.2", "Dış paydaş önerisini içeren en az 5 AKTS dersin gösterilmesi", "5.2", "medek_52", "Program Başkanı", ["Dış paydaş önerisi", "En az 5 AKTS ders kaydı", "Kurul kararı"], ["Müfredat & AKTS", "Paydaş"]),
    _odr_item("5.3", "İşyeri eğitimi/staj/uygulama/güncel teknoloji için en az 15 AKTS", "5.3", "medek_53", "Program Başkanı", ["En az 15 AKTS ilgili ders", "Eğitim planına eklenme süreci"], ["Müfredat & AKTS", "Kurul & Karar"]),
    _odr_item("5.4", "Programa/alana özgü çıktıları sağlayan en az 20 AKTS mesleki ders", "5.4", "medek_51", "Program Başkanı / Bologna", ["Tablo 5.3", "En az 20 AKTS program/alana özgü ders"], ["Müfredat & AKTS", "ÖÇ/PÇ"]),
    _odr_item("5.5", "Tüm ders izlencelerinin Ek I.1 formatında ve kamuya açık olması", "5.5", "curriculum", "Ders Sorumluları / Bologna", ["Tüm ders izlenceleri", "Kamuya açık ders bilgi paketi"], ["Ders Dosyaları", "Müfredat & AKTS"]),
    _odr_item("5.6", "Eğitim planının uygulanmasını ve sürekli gelişimini yöneten sistem", "5.6", "decisions", "Program Başkanı", ["Müfredat yönetim süreci", "Kurul kararları", "İyileştirme izi"], ["Kurul & Karar", "PUKÖ"]),

    # Ölçüt 6 · Öğretim Kadrosu (5)
    _odr_item("6.1.1", "Öğretim kadrosu analiz tablosunun tamamlanması", "6.1", "faculty", "Program Başkanı / MYO Yönetimi", ["Tablo 6.1", "Tam/yarı zamanlı/ek görevli kadro listesi"], ["Kadroyu Yönet", "Kadro CV"]),
    _odr_item("6.1.2", "Kadronun eğitim planına göre yeterliliğinin değerlendirilmesi ve CV'ler", "6.1", "faculty", "Program Başkanı / MYO Yönetimi", ["Kadro yeterlilik analizi", "Ek I.2 CV'ler"], ["Kadroyu Yönet", "Kadro CV"]),
    _odr_item("6.2", "Teşvik ve ödüllendirme mekanizmalarının adil ve şeffaf uygulanması", "6.2", "manual", "MYO Yönetimi / İK", ["Teşvik/ödül yönergesi", "Uygulama örnekleri"], ["Kontrollü Doküman", "Kanıt Merkezi"]),
    _odr_item("6.3", "Öğretim elemanı atama ve yükseltme kriterlerinin açıklanması", "6.3", "manual", "İK / MYO Yönetimi", ["Atama-yükseltme kriterleri", "Uygulama kaydı"], ["Kontrollü Doküman"]),
    _odr_item("6.4", "Ders yükü ve adil/şeffaf ders dağılımının gösterilmesi", "6.4", "faculty", "Program Başkanı / MYO Yönetimi", ["Tablo 6.2", "Uzmanlık-ders eşlemesi", "Ders yükü"], ["Kadroyu Yönet", "Kadro İş Yükü"]),

    # Ölçüt 7 · Altyapı (8)
    _odr_item("7.1.1", "Derslik/laboratuvar/teçhizat yeterliliğinin nicel ve nitel gösterilmesi", "7.1", "infrastructure", "Program Başkanı / İdari Birim", ["Altyapı envanteri", "Kapasite/kullanım değerlendirmesi"], ["Altyapı"]),
    _odr_item("7.1.2", "Eğitim ve laboratuvar teçhizatının Ek I.3'te sunulması", "7.1", "infrastructure", "Program Başkanı / Laboratuvar Sorumlusu", ["Ek I.3 teçhizat listesi", "Kullanım açıklaması"], ["Altyapı"]),
    _odr_item("7.2", "Ders dışı etkinlik alan ve altyapılarının açıklanması", "7.2", "infrastructure", "MYO Yönetimi", ["Sosyal/mesleki alan envanteri", "Kullanım kanıtı"], ["Altyapı"]),
    _odr_item("7.3", "Güvenlik, ilk yardım ve İSG önlemlerinin gösterilmesi", "7.3", "infrastructure", "İSG / Laboratuvar Sorumlusu", ["İSG/risk kayıtları", "İlk yardım ve eğitim/tatbikat kanıtı"], ["Altyapı", "Kanıt Merkezi"]),
    _odr_item("7.4", "Alanla ilgili bilgi ve eğitim kaynaklarına erişim olanakları", "7.4", "infrastructure", "Kütüphane / Program Başkanı", ["Kütüphane/veritabanı kaynakları", "Erişim kanıtı"], ["Altyapı"]),
    _odr_item("7.5", "Özel gereksinimli öğrenciler için erişilebilirlik düzenlemeleri", "7.5", "infrastructure", "İdari Birim / Engelsiz Üniversite", ["Erişilebilirlik envanteri", "İyileştirme kaydı"], ["Altyapı"]),
    _odr_item("7.6.1", "Öğrencilerin bilgisayar ve enformatik altyapısının yeterliliği", "7.6", "infrastructure", "Bilgi İşlem / Program Başkanı", ["Öğrenci BİT envanteri", "Kapasite/yeterlilik analizi"], ["Altyapı"]),
    _odr_item("7.6.2", "Öğretim elemanlarının bilgisayar ve enformatik altyapısının yeterliliği", "7.6", "infrastructure", "Bilgi İşlem / MYO Yönetimi", ["Personel BİT envanteri", "Kapasite/yeterlilik analizi"], ["Altyapı"]),

    # Ölçüt 8 · Yönetim ve İdari Birimler (4)
    _odr_item("8.1", "Misyon ve stratejik hedefleri destekleyen yönetim modeli/organizasyon", "8.1", "decisions", "MYO Yönetimi / Kalite", ["Organizasyon şeması", "Görev/yetki tanımları", "Stratejik uyum"], ["Kurul & Karar", "Stratejik Kalite"]),
    _odr_item("8.2", "İnsan kaynaklarının etkin/verimli kullanımını güvenceleyen süreçler", "8.2", "manual", "MYO Yönetimi / İK", ["İK politikası", "Görev/iş yükü dağılımı"], ["Kontrollü Doküman", "Kadroyu Yönet"]),
    _odr_item("8.3", "Akademik/idari personele yönelik hizmet içi eğitim süreçleri", "8.3", "manual", "İK / Kalite", ["Hizmet içi eğitim planı", "Katılım/örnek kanıtlar"], ["Kontrollü Doküman", "Kanıt Merkezi"]),
    _odr_item("8.4", "Kamuoyunu bilgilendirme politikası ve işletilen yöntemlerin kanıtları", "8.4", "evidence", "MYO Yönetimi / Kalite", ["Kamuoyu bilgilendirme politikası", "Web/rapor/duyuru kanıtı"], ["Kontrollü Doküman", "Kanıt Merkezi"]),

    # Ölçüt 9 · Programa Özgü Ölçütler (1)
    _odr_item("9.1", "Programa özgü ölçütlerin eğitim planı, ders ve ölçme yöntemleriyle sağlanması", "9.1", "program_specific", "Program Başkanı", ["Programa özgü ölçüt listesi", "Ölçüt-ders matrisi", "Doğrudan ölçme kanıtı"], ["Müfredat & AKTS", "ÖÇ/PÇ", "Ölçme & Değerlendirme"]),
]

MEDEK_ODR_V11_APPENDICES = [
    {"code":"I.1","title":"Ders İzlenceleri","automation_key":"curriculum","owner_role":"Ders Sorumluları / Bologna","required_evidence":["Tüm dersler için standart ders izlencesi","Kamuya açık ders bilgi paketi"],"source_modules":["Ders Dosyaları","Müfredat & AKTS"]},
    {"code":"I.2","title":"Öğretim Elemanı Özgeçmişleri","automation_key":"faculty_cv","owner_role":"Program Başkanı / Öğretim Elemanları","required_evidence":["Programdaki tüm öğretim elemanları için güncel onaylı CV"],"source_modules":["Kadroyu Yönet","Kadro CV"]},
    {"code":"I.3","title":"Eğitim ve Laboratuvar Teçhizatı","automation_key":"infrastructure","owner_role":"Laboratuvar Sorumlusu / Program Başkanı","required_evidence":["Başlıca eğitim/laboratuvar teçhizatı","Kullanım açıklaması"],"source_modules":["Altyapı"]},
    {"code":"I.4","title":"Diğer Program Bilgileri","automation_key":"optional","owner_role":"Program Başkanı","required_evidence":[],"source_modules":["Kanıt Merkezi"]},
    {"code":"II.1","title":"Üniversiteye İlişkin Bilgiler","automation_key":"institution_profile","owner_role":"Kalite Birimi / Genel Sekreterlik","required_evidence":["Üniversite yönetim/akreditasyon/misyon-vizyon bilgileri","İdari destek birimleri"],"source_modules":["Kurumsal Raporlama","Kontrollü Doküman"]},
    {"code":"II.2","title":"Meslek Yüksekokuluna İlişkin Bilgiler","automation_key":"school_profile","owner_role":"MYO Yönetimi","required_evidence":["MYO yönetim ve program listesi","Organizasyon şeması","Yönetici özgeçmişleri"],"source_modules":["Kurumsal Raporlama","Kontrollü Doküman"]},
    {"code":"II.3","title":"Personel Sayıları ve Akademik Destek Birimleri","automation_key":"faculty","owner_role":"MYO Yönetimi / İK","required_evidence":["Personel sayıları","Destek verilen/alınan birimler ve iş yükleri"],"source_modules":["Kadroyu Yönet","Kadro İş Yükü"]},
    {"code":"II.4","title":"Yarı Zamanlı ve Ek Görevli Öğretim Elemanlarının İzlenmesi","automation_key":"part_time_monitoring","owner_role":"MYO Yönetimi / İK","required_evidence":["Yarı zamanlı/ek görevli izleme politikası","Değerlendirme kayıtları"],"source_modules":["Kadroyu Yönet","Kontrollü Doküman"]},
    {"code":"II.5","title":"Öğrenci Kayıt ve Mezuniyet Bilgileri","automation_key":"student_graduate_stats","owner_role":"Öğrenci İşleri","required_evidence":["Son üç yıllık MYO/program öğrenci ve mezun istatistikleri"],"source_modules":["OBS/Proliz","Mezun"]},
    {"code":"II.6","title":"Kredi ve AKTS Tanımı","automation_key":"curriculum","owner_role":"Bologna / Eğitim Komisyonu","required_evidence":["Kredi/AKTS tanımı","İş yükü yaklaşımı"],"source_modules":["Müfredat & AKTS","Kontrollü Doküman"]},
    {"code":"II.7","title":"Kabul, Geçiş ve Mezuniyet Koşulları","automation_key":"graduation_policy","owner_role":"Öğrenci İşleri / MYO Yönetimi","required_evidence":["Kabul/yatay-dikey geçiş/ÇAP-YAP koşulları","Mezuniyet koşulları ve kontrol belgesi"],"source_modules":["Kontrollü Doküman","Öğrenci Karnesi"]},
]

MEDEK_ODR_V11_SOURCE = {
    "document_no": "RP-002", "title": "MEDEK Öz Değerlendirme Raporu v1.1",
    "revision_date": "2025-12-23", "revision_no": "02", "assessment_year": 2026,
    "url": "https://www.medek.org.tr/belgeler/3b671af3-be27-415b-b635-132b40768372/indir",
    "structure": ["Ana Bölüm", "Ek I · Programa İlişkin Ek Bilgiler", "Ek II · Kurum Profili"],
    "official_prompt_count": 58,
}


def medek_odr_valid_codes() -> set[str]:
    return {x["code"] for x in MEDEK_ODR_V11_ITEMS} | {x["code"] for x in MEDEK_ODR_V11_APPENDICES}

MEDEK_PROGRAM_OUTCOMES_V20 = [
    {"code": "PÇ1", "title": "Temel, güncel ve uygulamaya dönük mesleki bilgiyi etkin kullanma"},
    {"code": "PÇ2", "title": "İSG ve kalite süreçleri bilgisi"},
    {"code": "PÇ3", "title": "Mesleki bilişim teknolojilerini etkin kullanma"},
    {"code": "PÇ4", "title": "Mesleki problemleri analitik ve eleştirel değerlendirme"},
    {"code": "PÇ5", "title": "Yazılı ve sözlü etkili iletişim"},
    {"code": "PÇ6", "title": "Karmaşık sorunlarda ekip sorumluluğu alma"},
    {"code": "PÇ7", "title": "Kariyer planlama ve yaşam boyu öğrenme"},
    {"code": "PÇ8", "title": "Toplumsal, bilimsel, kültürel ve etik değerlere uygun hareket etme"},
    {"code": "PÇ9", "title": "Yabancı dil ile alan bilgisini izleme ve mesleki iletişim"},
    {"code": "PÇ10", "title": "BM Sürdürülebilir Kalkınma Amaçları farkındalığı"},
    {"code": "PÇ11", "title": "Dijitalleşme, çevre, yeşil dönüşüm ve sürdürülebilirlik farkındalığı"},
]

MEDEK_V20_CRITERIA = [
    {"code": "1", "name": "Öğrenci Kabulü, Gelişimi ve Mezuniyeti", "subcriteria": [
        _sc("1.1", "Kamuya açık ve işletilen öğrenci kabul prosedürleri", ["Kabul prosedürü", "Kamuya açık yayın", "Uygulama kaydı"], "manual"),
        _sc("1.2", "Kabul, başarı, ayrılma ve mezuniyet göstergelerinin izlenmesi", ["Doluluk ve puan trendi", "Başarı/ayrılma/mezuniyet analizi"], "students"),
        _sc("1.3", "Yeni öğrenci oryantasyon ve uyum süreci", ["Oryantasyon planı", "Katılım/uygulama kaydı"], "manual"),
        _sc("1.4", "Aktif katılımı ve farklı öğrenme gereksinimlerini destekleyen öğrenci merkezli öğretim", ["Ders izlencesi", "Öğretim yöntemi", "Öğrenci geri bildirimi"], "stakeholders"),
        _sc("1.5", "Önceki öğrenmelerin tanınması ve uygulanması", ["Muafiyet/intibak prosedürü", "Kurul/uygulama örneği"], "decisions"),
        _sc("1.6", "Çeşitlendirilmiş ölçme-değerlendirme ve geliştirici geri bildirim", ["Sınav/rubrik örnekleri", "Geri bildirim kanıtı", "ÖÇ sonuçları"], "official_exam"),
        _sc("1.7", "Şeffaf ölçme kriterleri ve işleyen itiraz mekanizması", ["İlan edilmiş değerlendirme ölçütleri", "İtiraz prosedürü", "Uygulama örneği"], "official_exam"),
        _sc("1.8", "Öğrenci görüş, talep, itiraz ve şikâyet mekanizmaları", ["Geri bildirim/şikâyet kanalı", "Değerlendirme ve sonuç kaydı"], "stakeholders"),
        _sc("1.9", "Öğrenci hareketliliği ve değişim programlarının desteklenmesi", ["Hareketlilik prosedürü", "Katılım kayıtları"], "manual"),
        _sc("1.10", "Akademik gelişim danışmanlığı", ["Danışman görevlendirmesi", "Danışmanlık faaliyet kaydı"], "manual"),
        _sc("1.11", "Kariyer ve mezuniyet sonrası rehberlik", ["Kariyer faaliyetleri", "Mezuniyet sonrası rehberlik kayıtları"], "graduates"),
        _sc("1.12", "Mezuniyet akademik koşullarının sistematik doğrulanması", ["Mezuniyet kontrol listesi", "Dondurulmuş mezuniyet çıktı karnesi"], "graduation_snapshots"),
    ]},
    {"code": "2", "name": "Program Eğitim Amaçları", "subcriteria": [
        _sc("2.1", "Program eğitim amaçlarının tanımlanması ve yayımlanması", ["Program eğitim amaçları", "Kamuya açık yayın"], "pea"),
        _sc("2.2", "Eğitim amaçlarının kurum, birim ve program misyon/vizyonuyla uyumu", ["Misyon-vizyon uyum matrisi", "Kurul onayı"], "pea"),
        _sc("2.3", "Eğitim amaçları performans göstergelerinin izlenmesi", ["PEA-KPI listesi", "Hedef/gerçekleşme analizi"], "pea"),
    ]},
    {"code": "3", "name": "Program Çıktıları", "program_outcomes": MEDEK_PROGRAM_OUTCOMES_V20, "subcriteria": [
        _sc("3.1", "Program çıktılarının MEDEK genel çıktılarını kapsaması ve yayımlanması", ["Program çıktıları", "11 genel MEDEK çıktısı kapsama matrisi", "Kamuya açık yayın"], "medek_outcomes"),
        _sc("3.2", "Program çıktılarının programa özgü MEDEK çıktılarını kapsaması ve yayımlanması", ["Programa özgü çıktı kataloğu", "Program PÇ eşleme matrisi", "Kamuya açık yayın"], "medek_program_specific"),
        _sc("3.3", "Program çıktıları ile eğitim amaçlarının uyumu", ["PEA-PÇ matrisi", "Kurul değerlendirmesi"], "pea"),
        _sc("3.4", "Program çıktıları ile ders öğrenme çıktılarının ilişkilendirilmesi", ["ÖÇ-PÇ matrisi", "Ders bilgi paketleri"], "lo_po"),
        _sc("3.5", "Program çıktılarının kazanılma düzeyinin sistematik izlenmesi", ["PÇ ölçme planı", "Doğrudan ölçme sonuçları", "Öğrenci çıktı karneleri"], "student_outcomes"),
    ]},
    {"code": "4", "name": "Öğretim Planı", "subcriteria": [
        _sc("4.1", "AKTS tabanlı ders bilgi paketlerinin yayımlanması ve uygulanması", ["Ders bilgi paketleri", "AKTS iş yükü kayıtları"], "curriculum"),
        _sc("4.2", "En az 60 AKTS mesleki ve 20 AKTS programa özgü çıktı destekli ders", ["Müfredat/AKTS tablosu", "Programa özgü çıktı-ders matrisi"], "medek_51"),
        _sc("4.3", "En az 15 AKTS uygulama/staj/işletmede eğitim/güncel yazılım bileşeni", ["Müfredat/AKTS tablosu", "Uygulama/staj/güncel teknoloji ders kanıtı"], "medek_53"),
        _sc("4.4", "Staj, işletmede mesleki eğitim veya uygulamalı dersin fiilen işletilmesi", ["Uygulama/staj planı", "Öğrenci katılımı ve değerlendirme kayıtları"], "manual"),
        _sc("4.5", "Dış paydaş önerisiyle oluşturulan/güncellenen en az 5 AKTS ders", ["Dış paydaş önerisi", "Kurul kararı", "Müfredat/AKTS tablosu"], "medek_52"),
    ]},
    {"code": "5", "name": "Sürekli İyileştirme", "subcriteria": [
        _sc("5.1", "Program eğitim amaçlarının paydaş/sektör verisiyle periyodik iyileştirilmesi", ["PEA gözden geçirme", "Paydaş verisi", "Kurul/PUKÖ kaydı"], "quality_cycle"),
        _sc("5.2", "Program çıktılarının paydaş/sektör verisiyle periyodik iyileştirilmesi", ["PÇ gözden geçirme", "Paydaş verisi", "Kurul/PUKÖ kaydı"], "quality_cycle"),
        _sc("5.3", "Öğretim planı ve ders içeriklerinin mevzuat/teknoloji/dijital gelişmelerle güncellenmesi", ["Müfredat gözden geçirme", "Kurul kararı", "İyileştirme kaydı"], "decisions"),
        _sc("5.4", "Mezun geri bildirimlerinin iyileştirmede kullanılması", ["Mezun izleme verisi", "Kurul kararı", "PUKÖ"], "graduates"),
        _sc("5.5", "İç paydaş geri bildirimlerinin iyileştirmede kullanılması", ["İç paydaş verisi", "Kurul kararı", "PUKÖ"], "stakeholders"),
        _sc("5.6", "Dış paydaş geri bildirimlerinin iyileştirmede kullanılması", ["Dış paydaş verisi", "Kurul kararı", "PUKÖ"], "stakeholders"),
    ]},
    {"code": "6", "name": "Öğretim Kadrosu", "subcriteria": [
        _sc("6.1", "Kadro sayısı ve uzmanlıkların derslerle yeterli uyumu", ["Kadro envanteri", "Uzmanlık-ders eşlemesi", "Ders yükü"], "faculty"),
        _sc("6.2", "Adil ders dağılımı ve dengeli iş yükü", ["Ders yükü dağılımı", "Kurul/planlama kaydı"], "faculty"),
        _sc("6.3", "Şeffaf teşvik ve ödüllendirme mekanizmaları", ["Teşvik/ödül yönergesi", "Uygulama örneği"], "manual"),
        _sc("6.4", "Mesleki/pedagojik gelişim ve yeni teknoloji kullanım desteği", ["Hizmet içi eğitim kayıtları", "Teknoloji/pedagoji gelişim kanıtı"], "faculty"),
    ]},
    {"code": "7", "name": "Altyapı", "subcriteria": [
        _sc("7.1", "Derslik, laboratuvar, atölye ve uygulama ortamlarının yeterliliği", ["Altyapı envanteri", "Kapasite/kullanım kaydı"], "infrastructure"),
        _sc("7.2", "Bilgi-iletişim, kütüphane ve elektronik kaynaklara erişim", ["BT/kütüphane kaynakları", "Erişim kanıtları"], "infrastructure"),
        _sc("7.3", "Beslenme, dinlenme ve çalışma ortamlarının yeterliliği", ["Sosyal/çalışma alanı envanteri", "Kapasite/kullanım kaydı"], "infrastructure"),
        _sc("7.4", "Sosyal, kültürel ve sportif etkinlik olanakları", ["Etkinlik/alan kayıtları", "Katılım kanıtları"], "infrastructure"),
        _sc("7.5", "Birime özgü İSG risk değerlendirmesi ve düzeltici tedbirler", ["İSG risk raporu", "Düzeltici faaliyet kayıtları"], "infrastructure"),
        _sc("7.6", "Özel gereksinimli öğrenciler için erişilebilirlik ve akademik destek", ["Erişilebilirlik envanteri", "Destek mekanizması ve uygulama kaydı"], "infrastructure"),
    ]},
    {"code": "8", "name": "Yönetim ve İdari Birimlerin Yapısı", "subcriteria": [
        _sc("8.1", "Organizasyon, kurul/komisyon ve görev-yetki-sorumlulukların tanımlanması", ["Organizasyon şeması", "Kurul/komisyon yönergeleri", "Görev tanımları"], "manual"),
        _sc("8.2", "Programa ilişkin güncel bilgilerin kamuoyuyla paylaşılması", ["Program web sayfası", "Güncel program bilgi paketi"], "program_identity"),
        _sc("8.3", "Öğrencilerin karar mekanizmalarında temsili", ["Öğrenci temsilcisi kayıtları", "Kurul/komisyon katılımı"], "stakeholders"),
        _sc("8.4", "İdari personelin mesleki gelişiminin desteklenmesi", ["İdari personel eğitim planı", "Katılım kayıtları"], "manual"),
    ]},
]

MEDEK_PROGRAM_SPECIFIC_OUTPUTS = {
    "v1.1": {
        "internet ve ag teknolojileri": {
            "canonical_name": "İnternet ve Ağ Teknolojileri",
            "source_section": "1.23",
            "outputs": [
                {"code": "PÖÇ1", "title": "Ağ yapıları, protokoller ve iletişim ilkelerini açıklama ve uygulama"},
                {"code": "PÖÇ2", "title": "Ağ sorunlarını giderme ve temel güvenlik uygulamalarını yürütme"},
                {"code": "PÖÇ3", "title": "Ağ cihazlarında temel programlama/yapılandırma işlemleri"},
                {"code": "PÖÇ4", "title": "Alanla ilgili temel matematiksel hesaplamaları yapma"},
            ],
            "source_url": "https://api.medek.org.tr/file/instructions/pdf/1757419892515ec3e0-ae6c-4bff-b70c-0ede6f98e6d8.pdf",
        },
    },
    "v2.0": {
        "internet ve ag teknolojileri": {
            "canonical_name": "İnternet ve Ağ Teknolojileri",
            "source_section": "1.89",
            "outputs": [
                {"code": "PÖÇ1", "title": "İnternet ve ağ teknolojilerinin temel kavramlarını açıklama"},
                {"code": "PÖÇ2", "title": "Ağ sistemlerinde kurulum ve temel yapılandırma yapma"},
                {"code": "PÖÇ3", "title": "Ağ cihazları ve sunucu sistemlerinde temel yönetim işlemleri"},
                {"code": "PÖÇ4", "title": "Ağ performansını izleme, sorun giderme ve temel güvenlik uygulama"},
                {"code": "PÖÇ5", "title": "Ağ sistemleri için raporlama ve dokümantasyon yürütme"},
            ],
            "source_url": "https://api.medek.org.tr/file/instructions/pdf/1776357358a652a341-3d0c-4def-901c-613e3da1a74a.pdf",
        },
    },
}


def _normalize_program_name(value: str) -> str:
    # Turkish dotted/dotless-I and other locale-specific letters need an
    # explicit transliteration before NFKD; otherwise "Yazılım" becomes
    # "yaz l m" and official framework profile routing can silently fail.
    translated = (value or "").translate(str.maketrans({
        "ı":"i", "İ":"I", "ş":"s", "Ş":"S", "ğ":"g", "Ğ":"G",
        "ç":"c", "Ç":"C", "ö":"o", "Ö":"O", "ü":"u", "Ü":"U",
    }))
    normalized = unicodedata.normalize("NFKD", translated)
    asciiish = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", asciiish.casefold()).strip()


def medek_program_specific_catalog(program_name: str, framework_version: str) -> dict[str, Any]:
    version = str(framework_version or "").strip()
    key = _normalize_program_name(program_name)
    profile = (MEDEK_PROGRAM_SPECIFIC_OUTPUTS.get(version) or {}).get(key)
    if not profile:
        return {
            "framework_family": "MEDEK", "framework_version": version,
            "program_name": program_name, "normalized_program_name": key,
            "match_status": "manual_required", "outputs": [], "required_count": 0,
            "warning": "Bu program adı için yerleşik resmî programa özgü çıktı kataloğu bulunamadı; resmî MEDEK kaynağı kalite birimi tarafından doğrulanmalıdır.",
        }
    return {
        "framework_family": "MEDEK", "framework_version": version,
        "program_name": program_name, "normalized_program_name": key,
        "match_status": "exact", "canonical_name": profile["canonical_name"],
        "source_section": profile["source_section"], "source_url": profile["source_url"],
        "outputs": list(profile["outputs"]), "required_count": len(profile["outputs"]), "warning": "",
    }


# ---------------------------------------------------------------------------
# MÜDEK 3.1 EK-1 discipline-specific curriculum topics (6.47)
# ---------------------------------------------------------------------------
MUDEK_DISCIPLINE_PROFILES_V31 = {
    "computer_software": {
        "canonical_name": "Bilgisayar, Yazılım ve Benzeri Adlı Mühendislik Programları",
        "aliases": ["bilgisayar", "yazilim", "yapay zeka", "yapay zekâ", "veri bilimi"],
        "common_topics": [
            {"code":"EK1-CS-01","title":"İleri matematik, olasılık-istatistik ve deneysel fizik"},
            {"code":"EK1-CS-02","title":"Algoritma analizi, yazılım geliştirme, karmaşık veri yapıları, veri saklama ve karmaşık sistem analizi/tasarımı"},
        ],
        "variants": {
            "bilgisayar": [{"code":"EK1-CS-COMP-01","title":"Laboratuvar uygulamaları ile desteklenen sayısal sistem tasarımı"}],
            "yazilim": [
                {"code":"EK1-CS-SW-01","title":"Gereksinim mühendisliği: analiz, doğrulama, sınama, yönetim ve test"},
                {"code":"EK1-CS-SW-02","title":"Yazılım mimarisi"},
                {"code":"EK1-CS-SW-03","title":"Yazılım kalite güvencesi ve karmaşık yazılım sistemlerinin doğrulanması/sınanması/yönetimi"},
            ],
            "ai": [
                {"code":"EK1-CS-AI-01","title":"Yapay zekâ kuramsal temelleri"},
                {"code":"EK1-CS-AI-02","title":"Veri bilimi, büyük veri analitiği ve veri madenciliği"},
                {"code":"EK1-CS-AI-03","title":"Doğal dil işleme, pekiştirmeli öğrenme ve derin öğrenme"},
                {"code":"EK1-CS-AI-04","title":"Bilgisayarlı görü ve öneri sistemleri"},
                {"code":"EK1-CS-AI-05","title":"Yapay zekâ yönetişimi"},
            ],
        },
    },
    "electrical_electronics": {
        "canonical_name": "Elektrik, Elektronik ve Benzeri Adlı Mühendislik Programları",
        "aliases": ["elektrik", "elektronik", "haberlesme", "telekomunikasyon", "kontrol"],
        "common_topics": [
            {"code":"EK1-EE-01","title":"İleri matematik, olasılık-istatistik, ayrık matematik, kompleks değişkenler ve deneysel fizik"},
            {"code":"EK1-EE-02","title":"Elektrik devreleri, elektromanyetik kuram ve ayrık-zaman işaretleri"},
        ],
        "variants": {
            "elektrik":[{"code":"EK1-EE-EL-01","title":"Elektrik ve elektromekanik enerji dönüşümü"}],
            "elektronik":[{"code":"EK1-EE-EC-01","title":"Sayısal elektronik"}],
            "haberlesme":[{"code":"EK1-EE-COM-01","title":"Sayısal haberleşme"}],
            "kontrol":[{"code":"EK1-EE-CTRL-01","title":"Sayısal kontrol ve kontrol sistem tasarımı"}],
        },
    },
    "industrial": {
        "canonical_name": "Endüstri ve Benzeri Adlı Mühendislik Programları",
        "aliases": ["endustri"],
        "common_topics": [
            {"code":"EK1-IE-01","title":"İleri matematik, olasılık-istatistik ve deneysel fizik"},
            {"code":"EK1-IE-02","title":"Bütünleşmiş sistemlerin tasarlanması, geliştirilmesi, uygulanması ve iyileştirilmesi"},
            {"code":"EK1-IE-03","title":"Sistem entegrasyonu için analitik, deneysel ve hesaplama yöntemleri"},
            {"code":"EK1-IE-04","title":"Yöneylem araştırması, mühendislik ekonomisi, benzetim ve üretim/operasyon yönetimi"},
        ],
        "variants": {},
    },
}

MUDEK_BBO_READINESS_FOLDERS = [
    ("BBO.0", "0 - Ortak Derslerdeki Farklılıklar", []),
    ("BBO.1", "1 - Öğrenciler", ["1","1.1","1.2","1.3","1.4","1.5","1.6"]),
    ("BBO.2", "2 - Program Eğitim Amaçları", ["2","2.1","2.2","2.3"]),
    ("BBO.3", "3 - Program Çıktıları", ["3","3.1","3.2","3.3"]),
    ("BBO.4", "4 - Sürekli İyileştirme", ["4","4.1","4.2"]),
    ("BBO.5", "5 - Eğitim Planı", ["5","5.1","5.2","5.3","5.4","5.5","EK-1"]),
    ("BBO.6", "6 - Öğretim Kadrosu", ["6","6.1","6.2","6.3"]),
    ("BBO.7", "7 - Altyapı", ["7","7.1","7.2","7.3","7.4","7.5"]),
    ("BBO.8", "8 - Kurum Desteği ve Parasal Kaynaklar", ["8","8.1","8.2","8.3","8.4"]),
    ("BBO.9", "9 - Organizasyon ve Karar Alma Süreçleri", ["9","9.1"]),
]
MUDEK_FBO_READINESS_FOLDERS = [(f"FBO.{i}", name) for i,name in enumerate([
    "", "1 - Ortak Yabancı Dil Dersleri", "2 - Ortak Fizik Dersleri", "3 - Ortak Kimya Dersleri",
    "4 - Ortak Matematik Dersleri", "5 - Ortak Bilişim Dersleri", "6 - Ortak Sosyal ve Spor Alanları",
    "7 - Engelliler için Alınmış Önlemler", "8 - Güvenlik Önlemleri", "9 - Üniversite Kütüphane Olanakları",
    "10 - Üniversite Bilişim Olanakları", "11 - Üniversite Sağlık Olanakları", "12 - Diğer"
]) if i]

def mudek_discipline_specific_catalog(program_name: str, framework_version: str) -> dict[str, Any]:
    version=str(framework_version or "").strip(); key=_normalize_program_name(program_name)
    if version not in {"3.0","3.1"}:
        return {"framework_family":"MÜDEK","framework_version":version,"program_name":program_name,"match_status":"manual_required","topics":[],"warning":"Bu sürüm için EK-1 profili manuel doğrulanmalıdır."}
    matches=[]
    for pk,profile in MUDEK_DISCIPLINE_PROFILES_V31.items():
        if any(_normalize_program_name(a) in key for a in profile["aliases"]): matches.append((pk,profile))
    if not matches:
        return {"framework_family":"MÜDEK","framework_version":version,"program_name":program_name,"match_status":"manual_required","topics":[],"warning":"Program adı için yerleşik EK-1 profili bulunamadı; resmî MÜDEK EK-1 metninden manuel doğrulama gerekir."}
    topics=[]; profiles=[]
    for pk,profile in matches:
        profiles.append(profile["canonical_name"]); topics.extend(dict(x) for x in profile.get("common_topics",[])); variants=profile.get("variants",{})
        if pk=="computer_software":
            if "bilgisayar" in key: topics += [dict(x) for x in variants.get("bilgisayar",[])]
            if "yazilim" in key: topics += [dict(x) for x in variants.get("yazilim",[])]
            if "yapay zeka" in key or "veri bilimi" in key: topics += [dict(x) for x in variants.get("ai",[])]
        if pk=="electrical_electronics":
            if "elektrik" in key: topics += [dict(x) for x in variants.get("elektrik",[])]
            if "elektronik" in key: topics += [dict(x) for x in variants.get("elektronik",[])]
            if "haberlesme" in key or "telekomunikasyon" in key: topics += [dict(x) for x in variants.get("haberlesme",[])]
            if "kontrol" in key: topics += [dict(x) for x in variants.get("kontrol",[])]
    unique={x["code"]:x for x in topics}
    return {"framework_family":"MÜDEK","framework_version":version,"program_name":program_name,"match_status":"exact","profiles":profiles,"topics":list(unique.values()),"required_count":len(unique),"warning":""}

def mudek_discipline_specific_readiness(db: Session, program_id: int, framework_id: int) -> dict[str, Any]:
    require_program_access(db,program_id,write=False,accreditation=True); program=db.get(m.Program,program_id); framework=db.get(m.QualityFrameworkProfile,framework_id)
    if not program: raise ValueError("Program bulunamadı")
    if not framework or framework.framework_family!="MÜDEK": raise ValueError("MÜDEK framework seçilmelidir")
    catalog=mudek_discipline_specific_catalog(program.name,framework.version); evidence=list(db.scalars(select(m.QualityEvidenceAsset).where(m.QualityEvidenceAsset.program_id==program_id)).all()); by_code=defaultdict(list)
    for ev in evidence: by_code[str(ev.criterion_code or "")].append(ev)
    rows=[]
    for topic in catalog.get("topics",[]):
        direct=by_code.get(topic["code"],[]); support=by_code.get("EK-1",[])+by_code.get("5.1",[]); status="ready" if direct else ("review" if support else "missing")
        rows.append({**topic,"status":status,"direct_evidence_count":len(direct),"support_evidence_count":len(support),"evidence":[{"id":x.id,"name":x.original_name} for x in direct[:6]]})
    ready=sum(x["status"]=="ready" for x in rows)
    return {**catalog,"program_id":program_id,"framework_id":framework_id,"topics":rows,"ready_count":ready,"review_count":sum(x["status"]=="review" for x in rows),"missing_count":sum(x["status"]=="missing" for x in rows),"coverage_percent":round(100*ready/len(rows),2) if rows else 0.0,"ready":catalog.get("match_status")=="exact" and bool(rows) and ready==len(rows)}

def mudek_evidence_room_readiness(db: Session, program_id: int, framework_id: int) -> dict[str, Any]:
    require_program_access(db,program_id,write=False,accreditation=True); framework=db.get(m.QualityFrameworkProfile,framework_id)
    if not framework or framework.framework_family!="MÜDEK": raise ValueError("MÜDEK framework seçilmelidir")
    evidence=list(db.scalars(select(m.QualityEvidenceAsset).where(m.QualityEvidenceAsset.program_id==program_id)).all())
    bbo=[]
    for code,name,criteria in MUDEK_BBO_READINESS_FOLDERS:
        direct=[e for e in evidence if str(e.criterion_code or "") in criteria or str(e.criterion_code or "")==code]
        bbo.append({"code":code,"name":name,"status":"ready" if direct else "missing","evidence_count":len(direct)})
    fbo=[]
    for code,name in MUDEK_FBO_READINESS_FOLDERS:
        direct=[e for e in evidence if str(e.criterion_code or "")==code]
        fbo.append({"code":code,"name":name,"status":"ready" if direct else "missing","evidence_count":len(direct)})
    return {"program_id":program_id,"framework_id":framework_id,"framework_version":framework.version,"bbo":{"rows":bbo,"ready_count":sum(x["status"]=="ready" for x in bbo),"total":len(bbo)},"fbo":{"rows":fbo,"ready_count":sum(x["status"]=="ready" for x in fbo),"total":len(fbo)}}

MUDEK_PROGRAM_OUTCOMES_V31 = [
    {"code": "1", "title": "Mühendislik Bilgisi"},
    {"code": "2", "title": "Problem Analizi"},
    {"code": "3", "title": "Mühendislik Tasarımı"},
    {"code": "4", "title": "Teknik ve Araçların Kullanımı"},
    {"code": "5", "title": "Araştırma ve İnceleme"},
    {"code": "6", "title": "Mühendislik Uygulamalarının Küresel Etkisi"},
    {"code": "7", "title": "Mühendislik Etiği"},
    {"code": "8", "title": "Bireysel ve Takım Çalışması"},
    {"code": "9", "title": "Sözlü ve Yazılı İletişim"},
    {"code": "10", "title": "Proje Yönetimi"},
    {"code": "11", "title": "Yaşam Boyu Öğrenme"},
]

MUDEK_CORE_CRITERIA = [
    {"code": "1", "name": "Öğrenciler", "subcriteria": [
        _sc("1.1", "Programa kabul edilen öğrencilerin uygun altyapıya sahip olması", ["Kabul göstergeleri ve yıllık trend", "Öğrenci profil analizi"], "students"),
        _sc("1.2", "Geçiş/ÇAP/YAP/değişim ve kredi tanıma politikaları", ["İntibak ve kredi tanıma politikası", "Uygulama örnekleri"], "decisions"),
        _sc("1.3", "Öğrenci hareketliliğini teşvik eden düzenlemeler", ["Değişim anlaşmaları", "Hareketlilik kayıtları"], "manual"),
        _sc("1.4", "Akademik danışmanlık ve kariyer yönlendirmesi", ["Danışman atamaları", "Danışmanlık/kariyer faaliyet kayıtları"], "manual"),
        _sc("1.5", "Başarının şeffaf, adil ve tutarlı ölçülmesi", ["Ders değerlendirme yöntemi", "Sınav/rubrik örnekleri", "Notlandırma kanıtı"], "official_exam"),
        _sc("1.6", "Mezuniyet koşullarının güvenilir yöntemlerle doğrulanması", ["Mezuniyet kontrolü", "Mezuniyet çıktı karnesi/snapshot"], "graduation_snapshots"),
    ]},
    {"code": "2", "name": "Program Eğitim Amaçları", "subcriteria": [
        _sc("2.1", "Program eğitim amaçlarının tanımlanmış olması", ["Program eğitim amaçları", "Resmî program belgesi"], "pea"),
        _sc("2.2", "PEA'ların MÜDEK tanımı, misyon, paydaş ve yayın koşullarını karşılaması", ["PEA-misyon uyumu", "Paydaş katılımı", "Gözden geçirme kararı", "Kamuya açık yayın"], "pea"),
        _sc("2.3", "PEA'lara erişimin ölçülmesi ve değerlendirilmesi", ["PEA ölçme planı", "Mezun/paydaş ölçüm sonuçları", "Değerlendirme kararı"], "pea"),
    ]},
    {"code": "3", "name": "Program Çıktıları", "program_outcomes": MUDEK_PROGRAM_OUTCOMES_V31, "subcriteria": [
        _sc("3.1", "Program çıktılarının 11 MÜDEK çıktısını kapsaması", ["Program çıktıları", "11 MÜDEK çıktısı kapsama matrisi", "PEA-PÇ ilişkisi"], "mudek_outcomes"),
        _sc("3.2", "Her PÇ ve bileşeni için uygun dönemsel ölçme-değerlendirme süreci", ["PÇ ölçme planı", "Bileşen bazlı doğrudan ölçme", "Dönemsel PÇ sonuçları"], "outcome_components"),
        _sc("3.3", "Mezuniyet aşamasındaki tüm öğrencilerin PÇ'leri bileşen bazında sağlaması", ["Mezuniyet PÇ karneleri", "Bileşen bazlı öğrenci sonuçları", "Dondurulmuş mezuniyet snapshotları"], "graduation_snapshots"),
    ]},
    {"code": "4", "name": "Sürekli İyileştirme", "subcriteria": [
        _sc("4.1", "Sürekli iyileştirme sürecinin varlığının kanıtlanması", ["Tanımlı PUKÖ süreci", "İyileştirme kayıtları", "Etkililik kanıtları"], "quality_cycle"),
        _sc("4.2", "İyileştirmenin sistematik ve somut verilere dayanması", ["Ölçüt 2/3 verileri", "Kurul kararı", "Kapatılmış PUKÖ ve etkililik sonucu"], "closed_cycle"),
    ]},
    {"code": "5", "name": "Eğitim Planı", "annex": {"code": "EK-1", "name": "Disipline Özgü Eğitim Planı Konuları", "is_separate_criterion": False, "note": "EK-1 ayrı bir 10. ölçüt değildir; Ölçüt 5.1 kapsamında eğitim planında doğrulanır."}, "subcriteria": [
        _sc("5.1", "Eğitim planının PEA/PÇ ortak bileşenleri ve EK-1 disiplin konularını kapsaması", ["Müfredat", "PEA/PÇ-müfredat matrisi", "EK-1 disiplin konusu kapsama matrisi"], "curriculum"),
        _sc("5.2", "Eğitim yöntemlerinin hedeflenen bilgi/beceri/farkındalığı kazandırması", ["Ders öğretim yöntemleri", "ÖÇ/PÇ ölçme kanıtları"], "lo_po"),
        _sc("5.3", "Eğitim planı uygulama ve sürekli gelişim yönetim sistemi", ["Müfredat yönetim süreci", "Kurul kararları", "Müfredat PUKÖ kayıtları"], "decisions"),
        _sc("5.4", "Matematik-temel bilim, mühendislik ve genel eğitim bileşenlerinin sağlanması", ["AKTS/kredi bileşen tablosu", "Ders kategori matrisi", "Yabancı dil koşulu"], "manual"),
        _sc("5.5", "Gerçekçi kısıtlar ve standartları içeren ana tasarım deneyimi", ["Bitirme/ana tasarım dersi", "Proje/rubrik örnekleri", "Standart-kısıt kanıtı"], "official_exam"),
    ]},
    {"code": "6", "name": "Öğretim Kadrosu", "subcriteria": [
        _sc("6.1", "Öğretim kadrosunun sayı ve alan kapsamı yeterliliği", ["Kadro envanteri", "Öğrenci/kadro ve ders yükü analizi", "Alan kapsama matrisi"], "faculty"),
        _sc("6.2", "Kadronun programı sürdürme/değerlendirme/geliştirme nitelikleri", ["Akademik CV'ler", "Uzmanlık-ders eşlemesi", "Mesleki gelişim kayıtları"], "faculty"),
        _sc("6.3", "Atama ve yükseltme kriterlerinin uygunluğu", ["Atama-yükseltme kriterleri", "Uygulama örnekleri"], "manual"),
    ]},
    {"code": "7", "name": "Altyapı", "subcriteria": [
        _sc("7.1", "Sınıf/laboratuvar/teçhizat yeterliliği", ["Altyapı envanteri", "Kapasite/kullanım kanıtı"], "infrastructure"),
        _sc("7.2", "Ders dışı sosyal ve mesleki gelişim altyapısı", ["Sosyal/mesleki alanlar", "Etkinlik kullanım kayıtları"], "infrastructure"),
        _sc("7.3", "Modern mühendislik araçları ve bilişim altyapısı", ["Yazılım/donanım/lab envanteri", "Lisans ve kullanım kayıtları"], "infrastructure"),
        _sc("7.4", "Kütüphane ve bilgi kaynaklarının yeterliliği", ["Kütüphane/veritabanı kaynakları", "Erişim kanıtı"], "infrastructure"),
        _sc("7.5", "İSG, güvenli kullanım ve erişilebilirlik", ["İSG eğitim/kayıtları", "Risk ve güvenlik prosedürleri", "Erişilebilirlik kanıtı"], "infrastructure"),
    ]},
    {"code": "8", "name": "Kurum Desteği ve Parasal Kaynaklar", "subcriteria": [
        _sc("8.1", "İdari destek, liderlik ve kaynak dağıtımının sürdürülebilirliği", ["Bütçe/kaynak planı", "Yönetim kararı", "Kaynak dağıtım politikası"], "decisions"),
        _sc("8.2", "Kadroyu çekme, tutma ve geliştirmeye yeterli kaynak", ["Kadro kaynak planı", "Mesleki gelişim bütçesi/kanıtı"], "faculty"),
        _sc("8.3", "Altyapı temin-bakım-işletme kaynaklarının yeterliliği", ["Altyapı bütçesi", "Bakım/yenileme kayıtları"], "infrastructure"),
        _sc("8.4", "Destek personeli ve kurumsal hizmetlerin yeterliliği", ["Destek personeli envanteri", "Hizmet süreçleri/görev tanımları"], "manual"),
    ]},
    {"code": "9", "name": "Organizasyon ve Karar Alma Süreçleri", "subcriteria": [
        _sc("9.1", "Organizasyon ve karar alma süreçlerinin PÇ/PEA'yı desteklemesi", ["Organizasyon şeması", "Görev/yetki tanımları", "Kurul ve karar alma kayıtları"], "decisions"),
    ]},
]


# ---------------------------------------------------------------------------
# MÜDEK versioned criteria registry (6.44)
# ---------------------------------------------------------------------------
# Sürüm 3.0 ve 3.1 aynı 9 ana ölçüt omurgasını kullanır. 3.1'de özellikle
# Ölçüt 7.5 ve EK-1 disipline özgü eğitim planı konuları güncellenmiştir.
MUDEK_CRITERIA_V30 = [
    {**criterion, "subcriteria": [dict(sc) for sc in (criterion.get("subcriteria") or [])]}
    for criterion in MUDEK_CORE_CRITERIA
]
for _criterion in MUDEK_CRITERIA_V30:
    if _criterion.get("code") == "5":
        _criterion["annex"] = {
            "code":"EK-1", "name":"Disipline Özgü Eğitim Planı Konuları", "is_separate_criterion":False,
            "note":"Sürüm 3.0'da EK-1 ayrı bir Ölçüt 10 değildir; Ölçüt 5.1 kapsamında doğrulanır.",
        }
    if _criterion.get("code") == "7":
        for _sc30 in _criterion.get("subcriteria") or []:
            if _sc30.get("code") == "7.5":
                _sc30["name"] = "Öğretim/laboratuvar güvenliği ve engelliler için altyapı düzenlemesi"
                _sc30["required_evidence"] = ["Güvenlik önlemleri", "Laboratuvar güvenlik kayıtları", "Erişilebilirlik kanıtı"]

MUDEK_PROGRAM_OUTCOMES_V22 = [
    {"code":"i", "title":"Matematik, fen ve mühendislik bilgisini uygulama"},
    {"code":"ii", "title":"Karmaşık mühendislik problemlerini tanımlama, modelleme ve çözme"},
    {"code":"iii", "title":"Karmaşık sistem/süreç/cihaz/ürün tasarlama"},
    {"code":"iv", "title":"Modern teknik ve araçları, bilişim teknolojilerini kullanma"},
    {"code":"v", "title":"Deney tasarlama, veri toplama, analiz ve yorumlama"},
    {"code":"vi", "title":"Disiplin içi/çok disiplinli takım ve bireysel çalışma"},
    {"code":"vii", "title":"Sözlü ve yazılı etkin iletişim"},
    {"code":"viii", "title":"Yaşam boyu öğrenme"},
    {"code":"ix", "title":"Etik ve mesleki sorumluluk"},
    {"code":"x", "title":"Proje/risk/değişiklik yönetimi, girişimcilik ve sürdürülebilirlik"},
    {"code":"xi", "title":"Mühendislik uygulamalarının toplumsal, çevresel, sağlık, güvenlik ve hukuki etkileri"},
]

MUDEK_CRITERIA_V22 = [
    {"code":"1", "name":"Öğrenciler", "subcriteria":[
        _sc("1.1","Öğrenci kabul göstergelerinin izlenmesi",["Kabul göstergeleri","Yıllık trend"],"students"),
        _sc("1.2","Geçiş/ÇAP/YAP/değişim ve kredi tanıma politikaları",["İntibak/kredi tanıma politikası","Uygulama kayıtları"],"decisions"),
        _sc("1.3","Öğrenci hareketliliğinin teşvik edilmesi",["Anlaşmalar","Hareketlilik kayıtları"],"manual"),
        _sc("1.4","Akademik danışmanlık ve kariyer yönlendirmesi",["Danışmanlık kayıtları","Kariyer etkinlikleri"],"manual"),
        _sc("1.5","Başarının şeffaf, adil ve tutarlı ölçülmesi",["Sınav/rubrik","Notlandırma kanıtı"],"official_exam"),
        _sc("1.6","Mezuniyet koşullarının güvenilir biçimde doğrulanması",["Mezuniyet kontrolü","Mezuniyet karnesi"],"graduation_snapshots"),
    ]},
    {"code":"2", "name":"Program Eğitim Amaçları", "subcriteria":[
        _sc("2.1","Program eğitim amaçlarının tanımlanması",["Program eğitim amaçları"],"pea"),
        _sc("2.2","PEA'ların MÜDEK tanımı, misyon, paydaş, yayın ve gözden geçirme koşulları",["PEA-misyon uyumu","Paydaş katılımı","Yayın","Gözden geçirme"],"pea"),
        _sc("2.3","PEA erişiminin ölçülmesi, değerlendirilmesi ve kanıtlanması",["PEA ölçme planı","Mezun/paydaş sonuçları"],"pea"),
    ]},
    {"code":"3", "name":"Program Çıktıları", "program_outcomes":MUDEK_PROGRAM_OUTCOMES_V22, "subcriteria":[
        _sc("3.1","Program çıktılarının MÜDEK çıktılarının tümünü kapsaması",["PÇ listesi","MÜDEK çıktı kapsama matrisi"],"mudek_outcomes"),
        _sc("3.2","PÇ sağlanma düzeyinin doğrudan öğrenci çalışmalarına dayalı dönemsel ölçülmesi",["PÇ ölçme planı","Sınav/proje/ödev kanıtları","Dönemsel PÇ sonuçları"],"outcome_components"),
        _sc("3.3","Mezuniyet aşamasındaki öğrencilerin PÇ'leri sağladığının kanıtlanması",["Mezuniyet PÇ karneleri","Mezuniyet snapshotları"],"graduation_snapshots"),
    ]},
    {"code":"4", "name":"Sürekli İyileştirme", "subcriteria":[
        _sc("4.1","Ölçme-değerlendirme sonuçlarının sürekli iyileştirmede kullanılması",["PUKÖ kayıtları","İyileştirme kararları"],"quality_cycle"),
        _sc("4.2","İyileştirmenin sistematik ve somut verilere dayanması",["Ölçüt 2/3 verileri","Kapatılmış PUKÖ"],"closed_cycle"),
    ]},
    {"code":"5", "name":"Eğitim Planı", "subcriteria":[
        _sc("5.1","Eğitim planının PEA/PÇ, ortak bileşenler ve Ölçüt 10 disipline özgü bileşenlerini içermesi",["Müfredat","PEA/PÇ-müfredat matrisi","Disipline özgü ölçüt kapsama"],"curriculum"),
        _sc("5.2","Eğitim yöntemlerinin hedeflenen bilgi, beceri ve davranışları kazandırması",["Öğretim yöntemleri","ÖÇ/PÇ ölçme kanıtları"],"lo_po"),
        _sc("5.3","Eğitim planı uygulama ve sürekli gelişim yönetim sisteminin bulunması",["Müfredat yönetim süreci","Kurul kararları"],"decisions"),
        _sc("5.4","Matematik-temel bilim, mühendislik ve genel eğitim bileşenlerinin sağlanması",["Kredi/AKTS bileşen tablosu","Ders kategori matrisi"],"manual"),
        _sc("5.5","Gerçekçi kısıtlar ve standartları içeren ana tasarım deneyimi",["Bitirme/ana tasarım dersi","Proje/rubrik kanıtı"],"official_exam"),
    ]},
    {"code":"6", "name":"Öğretim Kadrosu", "subcriteria":[
        _sc("6.1","Öğretim kadrosunun sayı ve alan kapsamı yeterliliği",["Kadro envanteri","Ders yükü/alan kapsama"],"faculty"),
        _sc("6.2","Kadronun programı sürdürme, değerlendirme ve geliştirme nitelikleri",["CV'ler","Uzmanlık-ders eşlemesi"],"faculty"),
        _sc("6.3","Atama ve yükseltme kriterlerinin uygunluğu",["Atama-yükseltme kriterleri"],"manual"),
    ]},
    {"code":"7", "name":"Altyapı", "subcriteria":[
        _sc("7.1","Sınıf/laboratuvar/teçhizat yeterliliği",["Altyapı envanteri","Kapasite/kullanım"],"infrastructure"),
        _sc("7.2","Ders dışı sosyal ve mesleki gelişim altyapısı",["Sosyal/mesleki alanlar","Etkinlik kayıtları"],"infrastructure"),
        _sc("7.3","Modern mühendislik araçları ve bilişim altyapısı",["Yazılım/donanım/lab envanteri","Kullanım kayıtları"],"infrastructure"),
        _sc("7.4","Kütüphane olanaklarının yeterliliği",["Kütüphane/veritabanı kaynakları"],"infrastructure"),
        _sc("7.5","Öğretim/laboratuvar güvenliği ve engelliler için altyapı düzenlemesi",["Güvenlik önlemleri","Erişilebilirlik kanıtı"],"infrastructure"),
    ]},
    {"code":"8", "name":"Kurum Desteği ve Parasal Kaynaklar", "subcriteria":[
        _sc("8.1","İdari destek, liderlik ve kaynak dağıtımının sürdürülebilirliği",["Bütçe/kaynak planı","Yönetim kararı"],"decisions"),
        _sc("8.2","Kadroyu çekme, tutma ve geliştirmeye yeterli kaynak",["Kadro kaynak planı","Gelişim bütçesi"],"faculty"),
        _sc("8.3","Altyapı temin-bakım-işletme kaynaklarının yeterliliği",["Altyapı bütçesi","Bakım kayıtları"],"infrastructure"),
        _sc("8.4","Destek personeli ve kurumsal hizmetlerin yeterliliği",["Destek personeli envanteri","Görev tanımları"],"manual"),
    ]},
    {"code":"9", "name":"Organizasyon ve Karar Alma Süreçleri"},
    {"code":"10", "name":"Disipline Özgü Ölçütler", "subcriteria":[
        _sc("10.1","Programın ilgili disipline özgü ölçütleri sağlaması",["Disipline özgü ölçüt listesi","Ders/ölçüt kapsama matrisi"],"program_specific"),
        _sc("10.2","Program adı birden fazla ölçüt kümesine giriyorsa tüm ilgili kümelerin sağlanması",["Program adı-disiplin eşlemesi","Çoklu ölçüt kapsama matrisi"],"program_specific"),
    ]},
]

YOKAK_14_CRITERIA = [
    {"code": "A.1", "name": "Liderlik ve Kalite", "area": "Liderlik, Yönetişim ve Kalite"},
    {"code": "A.2", "name": "Misyon ve Stratejik Amaçlar", "area": "Liderlik, Yönetişim ve Kalite"},
    {"code": "A.3", "name": "Yönetim Sistemleri", "area": "Liderlik, Yönetişim ve Kalite"},
    {"code": "A.4", "name": "Paydaş Katılımı", "area": "Liderlik, Yönetişim ve Kalite"},
    {"code": "A.5", "name": "Uluslararasılaşma", "area": "Liderlik, Yönetişim ve Kalite"},
    {"code": "B.1", "name": "Program Tasarımı, Değerlendirmesi ve Güncellenmesi", "area": "Eğitim ve Öğretim"},
    {"code": "B.2", "name": "Programların Yürütülmesi", "area": "Eğitim ve Öğretim"},
    {"code": "B.3", "name": "Öğrenme Kaynakları ve Akademik Destek Hizmetleri", "area": "Eğitim ve Öğretim"},
    {"code": "B.4", "name": "Öğretim Kadrosu", "area": "Eğitim ve Öğretim"},
    {"code": "C.1", "name": "Araştırma Süreçlerinin Yönetimi ve Araştırma Kaynakları", "area": "Araştırma ve Geliştirme"},
    {"code": "C.2", "name": "Araştırma Yetkinliği, İş Birlikleri ve Destekler", "area": "Araştırma ve Geliştirme"},
    {"code": "C.3", "name": "Araştırma Performansı", "area": "Araştırma ve Geliştirme"},
    {"code": "D.1", "name": "Toplumsal Katkı Süreçlerinin Yönetimi ve Toplumsal Katkı Kaynakları", "area": "Toplumsal Katkı"},
    {"code": "D.2", "name": "Toplumsal Katkı Performansı", "area": "Toplumsal Katkı"},
]


TURAK_CORE_CRITERIA = [
    {"code":"1","name":"Öğrenciler"},
    {"code":"2","name":"Program Öğretim Amaçları"},
    {"code":"3","name":"Program Öğrenim Çıktıları"},
    {"code":"4","name":"Öğretim Planı"},
    {"code":"5","name":"Öğretim Kadrosu"},
    {"code":"6","name":"Yönetim Yapısı"},
    {"code":"7","name":"Altyapı"},
    {"code":"8","name":"Kurum Desteği ve Parasal Kaynaklar"},
    {"code":"9","name":"Sürekli İyileştirme"},
]

SABAK_CORE_CRITERIA = [
    {"code":"1","name":"Eğitim Programı"}, {"code":"2","name":"Program Çıktıları"},
    {"code":"3","name":"Öğrenciler"}, {"code":"4","name":"Öğretim Elemanları"},
    {"code":"5","name":"Altyapı"}, {"code":"6","name":"Yönetim Yapısı"},
    {"code":"7","name":"Kurum Desteği ve Maddi Kaynaklar"}, {"code":"8","name":"Sürekli Yenileme ve Gelişim"},
    {"code":"9","name":"Disipline Özgü Ölçütler"},
]

EPDAD_CORE_CRITERIA = [
    {"code":"1","name":"Öğretimin Planlanması, Uygulanması ve Değerlendirilmesi"},
    {"code":"2","name":"Öğretim Elemanları"}, {"code":"3","name":"Öğrenciler"},
    {"code":"4","name":"Fakülte-Okul İş Birliği"}, {"code":"5","name":"Tesisler, Öğrenme Ortamları ve Kaynakları"},
    {"code":"6","name":"Yönetim"}, {"code":"7","name":"Kalite Güvencesi"},
]

ESG_CORE_CRITERIA = [
    {"code":"1.1","name":"Kalite Güvencesi Politikası"}, {"code":"1.2","name":"Programların Tasarımı ve Onayı"},
    {"code":"1.3","name":"Öğrenci Merkezli Öğrenme, Öğretme ve Değerlendirme"}, {"code":"1.4","name":"Öğrenci Kabulü, İlerlemesi ve Belgelendirme"},
    {"code":"1.5","name":"Öğretim Kadrosu"}, {"code":"1.6","name":"Öğrenme Kaynakları ve Öğrenci Desteği"},
    {"code":"1.7","name":"Bilgi Yönetimi"}, {"code":"1.8","name":"Kamuya Açık Bilgi"},
    {"code":"1.9","name":"Programların Sürekli İzlenmesi ve Periyodik Gözden Geçirilmesi"}, {"code":"1.10","name":"Dış Kalite Güvencesi"},
]

ACQUIN_CORE_CRITERIA = [
    {"code":"SYS.1","name":"Strateji ve Kalite Kültürü"}, {"code":"SYS.2","name":"Yönetişim ve Sorumluluklar"},
    {"code":"SYS.3","name":"Program Tasarımı ve Onayı"}, {"code":"SYS.4","name":"Ölçme, İzleme ve Değerlendirme"},
    {"code":"SYS.5","name":"Paydaş Katılımı"}, {"code":"SYS.6","name":"Kaynaklar ve Akademik Kadro"},
    {"code":"SYS.7","name":"Sürekli İyileştirme ve Kanıt"},
]

BUILTIN_FRAMEWORKS = [
    {
        "code":"MUDEK-2.2", "name":"MÜDEK Mühendislik Lisans Programı Ölçütleri", "version":"2.2",
        "framework_family":"MÜDEK", "effective_from_year":2020, "transition_from_year":2026, "status":"legacy",
        "criteria":MUDEK_CRITERIA_V22, "thresholds":{"required_mudek_outcomes":11},
        "source_meta":{"scope":"Mühendislik lisans programları", "mode":"official-version", "published":"2020-01-25", "source":"MÜDEK Lisans Programları Değerlendirme Ölçütleri Sürüm 2.2", "url":"https://www.mudek.org.tr/doc/tr/MUDEK-Degerlendirme_Olcutleri_(2.2-25.01.2020).pdf", "official_criteria_count":10, "discipline_specific":"Ölçüt 10", "routing_note":"2026-2027 ara değerlendirmelerinde zorunlu sürüm."},
    },
    {
        "code":"MUDEK-3.0", "name":"MÜDEK Mühendislik Lisans Programı Ölçütleri", "version":"3.0",
        "framework_family":"MÜDEK", "effective_from_year":2026, "transition_from_year":2027, "status":"transition",
        "criteria":MUDEK_CRITERIA_V30, "thresholds":{"official_subcriteria_count":32,"required_mudek_outcomes":11},
        "source_meta":{"scope":"Mühendislik lisans programları", "mode":"official-version", "published":"2023-11-08", "source":"MÜDEK Lisans Programları Değerlendirme Ölçütleri Sürüm 3.0", "url":"https://www.mudek.org.tr/doc/tr/MUDEK-Degerlendirme_Olcutleri_(3.0-08.11.2023).pdf", "official_criteria_count":9, "official_subcriteria_count":32, "annex":"EK-1 Disipline Özgü Eğitim Planı Konuları", "routing_note":"2026-2027 genel değerlendirmesinde kurum tercihine bağlı olarak kullanılabilir."},
    },
    {
        "code":"MUDEK-CORE", "name":"MÜDEK Mühendislik Lisans Programı Ölçütleri", "version":"3.1",
        "framework_family":"MÜDEK", "effective_from_year":2026, "transition_from_year":2027, "status":"active",
        "criteria":MUDEK_CORE_CRITERIA, "thresholds":{"official_subcriteria_count":32,"required_mudek_outcomes":11},
        "source_meta":{"scope":"Mühendislik lisans programları", "mode":"official-version", "published":"2025-12-05", "source":"MÜDEK Lisans Programları Değerlendirme Ölçütleri Sürüm 3.1", "url":"https://www.mudek.org.tr/doc/tr/MUDEK-Degerlendirme_Olcutleri_(3.1-05.12.2025).pdf", "official_criteria_count":9, "official_subcriteria_count":32, "annex":"EK-1 Disipline Özgü Eğitim Planı Konuları", "transition_note":"2026-2027 genel değerlendirmelerinde 3.0 veya 3.1 seçilebilir; 2027-2028'den itibaren genel değerlendirmelerde 3.1."},
    },
    {
        "code":"TURAK-CORE", "name":"TURAK Turizm Programı Kalite Profili", "version":"2024-12-27",
        "framework_family":"TURAK", "effective_from_year":2025, "transition_from_year":None, "status":"active",
        "criteria":TURAK_CORE_CRITERIA, "thresholds":{},
        "source_meta":{"scope":"Turizm ve ilgili programlar", "mode":"official-version", "criteria_date":"2024-12-27", "official_criteria_count":9, "odr_version":"7", "odr_date":"2025-12-27", "url":"https://turak.org/belgeler/"},
    },
    {
        "code":"SABAK-2026", "name":"SABAK Sağlık Bilimleri Programı Kalite Profili", "version":"R4 / ODR-R5",
        "framework_family":"SABAK", "effective_from_year":2026, "transition_from_year":None, "status":"active",
        "criteria":SABAK_CORE_CRITERIA, "thresholds":{"minimum_ects":240},
        "source_meta":{"scope":"Sağlık bilimleri lisans programları", "mode":"official-version", "odr_revision":"5", "odr_date":"2026-04-10", "criteria_revision":"4", "url":"https://www.sabak.org.tr/index.php/tr/belgeler-ve-formlar"},
    },
    {
        "code":"EPDAD-1.1", "name":"EPDAD Öğretmen Eğitimi Programı Kalite Profili", "version":"1.1",
        "framework_family":"EPDAD", "effective_from_year":2024, "transition_from_year":None, "status":"active",
        "criteria":EPDAD_CORE_CRITERIA, "thresholds":{"standard_areas":7,"substandards":39,"indicators":158},
        "source_meta":{"scope":"Öğretmen eğitimi lisans programları", "mode":"official-version", "odr_guide_version":"1.3", "url":"https://www.epdad.org.tr/icerik/program-degerlendirme-standartlari"},
    },
    {
        "code":"ESG-2015", "name":"European Standards and Guidelines — İç Kalite Güvencesi", "version":"2015",
        "framework_family":"ESG", "effective_from_year":2015, "transition_from_year":None, "status":"active",
        "criteria":ESG_CORE_CRITERIA, "thresholds":{}, "source_meta":{"scope":"Kurum geneli", "mode":"institutional"},
    },
    {
        "code":"ACQUIN-SYSTEM", "name":"ACQUIN Kurumsal / Sistem Akreditasyonu Profili", "version":"configurable",
        "framework_family":"ACQUIN", "effective_from_year":2026, "transition_from_year":None, "status":"active",
        "criteria":ACQUIN_CORE_CRITERIA, "thresholds":{},
        "source_meta":{"scope":"Kurum geneli", "mode":"configurable", "note":"Başvuru tipine göre resmî ACQUIN kriter seti sürümlenmelidir."},
    },
    {
        "code": "MEDEK-2026", "name": "MEDEK Önlisans Program Ölçütleri", "version": "v1.1",
        "framework_family": "MEDEK", "effective_from_year": 2026, "transition_from_year": None, "status": "active",
        "criteria": MEDEK_V11_CRITERIA,
        "thresholds": {"professional_ects": 60, "program_specific_ects": 20, "external_stakeholder_ects": 5, "applied_current_tech_ects": 15, "official_subcriteria_count": 46, "required_medek_outcomes": 10},
        "source_meta": {
            "document_no": "KL-004", "revision": "REV.2025V1.1", "used_for": "2026 akreditasyon başvuruları",
            "source": "MEDEK Önlisans Program Ölçütleri v1.1",
            "url": "https://api.medek.org.tr/file/instructions/pdf/1757419892515ec3e0-ae6c-4bff-b70c-0ede6f98e6d8.pdf", "official_criteria_count": 9, "official_subcriteria_count": 46,
        },
    },
    {
        "code": "MEDEK-2028", "name": "MEDEK Önlisans Program Ölçütleri", "version": "v2.0",
        "framework_family": "MEDEK", "effective_from_year": 2028, "transition_from_year": 2028, "status": "transition",
        "criteria": MEDEK_V20_CRITERIA,
        "thresholds": {"professional_ects": 60, "program_specific_ects": 20, "external_stakeholder_ects": 5, "applied_current_tech_ects": 15, "official_subcriteria_count": 45, "required_medek_outcomes": 11},
        "source_meta": {
            "document_no": "KL-007", "published": "2026-04-16",
            "used_for": "2028 değerlendirme döneminden itibaren ilk/genel yeniden değerlendirmeler",
            "transition_note": "Ara değerlendirmelerde önceki genel değerlendirmede kullanılan ölçütler esas alınır.",
            "source": "MEDEK Önlisans Program Ölçütleri v2.0",
            "url": "https://medek.org.tr/medek-onlisans-degerlendirme-olcutleri-20-yayimlandi",
        },
    },
    {
        "code": "YOKAK-2026", "name": "YÖKAK Kurumsal Kalite Profili", "version": "DPK-3.3 / KİDR-3.2.1",
        "framework_family": "YÖKAK", "effective_from_year": 2026, "transition_from_year": None, "status": "active",
        "criteria": YOKAK_14_CRITERIA,
        "thresholds": {"criteria_count": 14, "subcriteria_count": 46},
        "source_meta": {
            "evaluation_guide": "Değerlendirme Programları Kılavuzu Sürüm 3.3 (2026)",
            "kidr_guide": "Kurum İç Değerlendirme Raporu Hazırlama Kılavuzu Sürüm 3.2.1",
            "url": "https://www.yokak.gov.tr/ulusal-degerlendirme-programlari-",
        },
    },
]


def academic_year_catalog(anchor_year: int | None = None) -> list[str]:
    anchor_year = anchor_year or datetime.now().year
    return [f"{y}-{y+1}" for y in range(anchor_year - 3, anchor_year + 4)]


def catalogs() -> dict[str, Any]:
    return {
        "exam_types": EXAM_TYPE_CATALOG,
        "class_levels": CLASS_LEVELS,
        "terms": TERMS,
        "academic_years": academic_year_catalog(),
        "course_categories": COURSE_CATEGORIES,
        "stakeholder_types": STAKEHOLDER_TYPES,
        "stakeholder_engagement_types": STAKEHOLDER_ENGAGEMENT_TYPES,
        "graduate_employment_statuses": GRADUATE_EMPLOYMENT_STATUSES,
        "instructor_titles": INSTRUCTOR_TITLES,
        "employment_types": EMPLOYMENT_TYPES,
        "infrastructure_types": INFRASTRUCTURE_TYPES,
        "quality_statuses": QUALITY_STATUSES,
        "quality_cycle_statuses": QUALITY_CYCLE_STATUSES,
        "governance_bodies": GOVERNANCE_BODIES,
    }


def seed_builtin_frameworks(db: Session) -> list[m.QualityFrameworkProfile]:
    changed = False
    for cfg in BUILTIN_FRAMEWORKS:
        obj = db.scalar(select(m.QualityFrameworkProfile).where(
            m.QualityFrameworkProfile.code == cfg["code"], m.QualityFrameworkProfile.version == cfg["version"]
        ))
        if not obj:
            obj = m.QualityFrameworkProfile(**cfg, is_builtin=True)
            db.add(obj)
            changed = True
        elif obj.is_builtin:
            for key, value in cfg.items():
                setattr(obj, key, value)
            changed = True
    # Keep historical builtin framework rows for audit/snapshots, but archive
    # stale versions so normal selectors expose one current/transition profile.
    desired = {(cfg["code"], cfg["version"]) for cfg in BUILTIN_FRAMEWORKS}
    desired_codes = {cfg["code"] for cfg in BUILTIN_FRAMEWORKS}
    stale = db.scalars(select(m.QualityFrameworkProfile).where(m.QualityFrameworkProfile.is_builtin.is_(True))).all()
    for obj in stale:
        if obj.code in desired_codes and (obj.code, obj.version) not in desired and obj.status != "archived":
            obj.status = "archived"
            changed = True
    if changed:
        db.commit()
    return db.scalars(
        select(m.QualityFrameworkProfile)
        .where(m.QualityFrameworkProfile.status != "archived")
        .order_by(m.QualityFrameworkProfile.framework_family, m.QualityFrameworkProfile.effective_from_year, m.QualityFrameworkProfile.id)
    ).all()


def model_dict(obj: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in obj.__table__.columns:
        value = getattr(obj, col.name)
        if isinstance(value, (date, datetime)):
            out[col.name] = value.isoformat()
        else:
            out[col.name] = value
    return out


def recommend_program_frameworks(db: Session, program_id: int) -> dict[str, Any]:
    program = require_program_access(db, program_id, write=False, accreditation=True)
    frameworks = seed_builtin_frameworks(db)
    text = " ".join([program.code or "", program.name or "", program.faculty or "", program.department or ""]).casefold()
    recs: list[dict[str, Any]] = []
    def add(family: str, confidence: float, rationale: str, primary: bool = False):
        candidates = [x for x in frameworks if x.framework_family == family and x.status in {"active","transition"}]
        candidates.sort(key=lambda x: (x.status == "active", x.effective_from_year or 0, x.id or 0), reverse=True)
        fw = candidates[0] if candidates else None
        if fw and not any(r["framework_id"] == fw.id for r in recs):
            recs.append({"framework_id":fw.id,"code":fw.code,"family":fw.framework_family,"name":fw.name,"confidence":confidence,"rationale":rationale,"is_primary":primary})
    tourism = any(k in text for k in ["turizm","otelcilik","gastronomi","seyahat","tourism","hospitality"] )
    engineering = any(k in text for k in ["mühendis","muhendis","engineering"] )
    associate = any(k in text for k in ["meslek yüksekokulu","meslek yuksekokulu","myo","önlisans","onlisans"] )
    if tourism: add("TURAK", .95, "Program/birim adı turizm alanı ile eşleşiyor.", True)
    elif engineering: add("MÜDEK", .95, "Program/birim adı mühendislik alanı ile eşleşiyor.", True)
    elif associate: add("MEDEK", .90, "Program Meslek Yüksekokulu/önlisans kapsamı ile eşleşiyor.", True)
    else: add("YÖKAK", .55, "Alan akreditasyonu otomatik kesinleşmedi; kurumsal kalite profili varsayılan bağlam olarak önerildi.", True)
    # Institutional overlays are not substitutes for programme accreditation.
    add("YÖKAK", 1.0, "Üniversite genel iç kalite güvencesi katmanı.")
    add("ESG", 1.0, "Avrupa yükseköğretim iç kalite güvencesi üst katmanı.")
    add("ACQUIN", .75, "Kurumsal/sistem akreditasyonu için etkinleştirilebilir üst katman.")
    manual = db.scalars(select(m.QualityFrameworkAssignment).where(m.QualityFrameworkAssignment.program_id==program_id, m.QualityFrameworkAssignment.active.is_(True)).order_by(m.QualityFrameworkAssignment.is_primary.desc(),m.QualityFrameworkAssignment.id)).all()
    return {"program":model_dict(program),"recommendations":recs,"assignments":[{**model_dict(x),"framework":model_dict(db.get(m.QualityFrameworkProfile,x.framework_profile_id))} for x in manual]}



def _academic_year_start(academic_year: str) -> int:
    match = re.match(r"^\s*(\d{4})\s*[-/]", academic_year or "")
    if not match:
        raise ValueError("Akademik yıl YYYY-YYYY biçiminde olmalıdır")
    return int(match.group(1))


def medek_version_route(
    db: Session,
    academic_year: str,
    application_type: str = "general",
    preferred_version: str | None = None,
    previous_general_version: str | None = None,
) -> dict[str, Any]:
    """Route MEDEK criteria by evaluation period and application lifecycle.

    MEDEK v2.0 starts with the 2028 evaluation period for first/general
    re-evaluations. Interim/monitoring work inherits the previous general
    evaluation criteria version and therefore requires historical context.
    """
    start = _academic_year_start(academic_year)
    kind = (application_type or "general").strip().casefold()
    if kind not in {"general", "interim", "renewal", "monitoring"}:
        raise ValueError("Desteklenmeyen MEDEK değerlendirme türü")
    normalized_kind = "general" if kind in {"general", "renewal"} else kind
    frameworks = [x for x in seed_builtin_frameworks(db) if x.framework_family == "MEDEK"]
    by_version = {str(x.version): x for x in frameworks}
    selection_required = False
    warning = ""

    if normalized_kind == "general":
        allowed_versions = ["v2.0"] if start >= 2028 else ["v1.1"]
        rationale = (
            "2028 değerlendirme döneminden itibaren ilk/genel yeniden değerlendirmelerde MEDEK v2.0 kullanılır."
            if start >= 2028 else
            "2028 değerlendirme dönemi öncesindeki ilk/genel değerlendirmelerde MEDEK v1.1 profili kullanılır."
        )
    else:
        if previous_general_version in by_version:
            allowed_versions = [str(previous_general_version)]
            rationale = "Ara/izleme değerlendirmesi, programın önceki genel değerlendirmesinde kullanılan MEDEK ölçüt sürümünü devralır."
        else:
            allowed_versions = []
            selection_required = True
            warning = "Önceki genel MEDEK değerlendirmesinde kullanılan sürüm bilinmiyor; tarihsel başvuru kaydı doğrulanmadan ara/izleme başlatılamaz."
            rationale = "MEDEK ara değerlendirmelerinde önceki genel değerlendirmedeki ölçüt sürümü korunur."

    allowed = [by_version[v] for v in allowed_versions if v in by_version]
    selected = None
    if preferred_version in allowed_versions:
        selected = by_version.get(str(preferred_version))
    elif len(allowed) == 1:
        selected = allowed[0]

    return {
        "framework_family": "MEDEK", "academic_year": academic_year,
        "application_type": kind, "normalized_application_type": normalized_kind,
        "allowed_versions": allowed_versions,
        "allowed_frameworks": [model_dict(x) for x in allowed],
        "selected_framework": model_dict(selected) if selected else None,
        "selection_required": selection_required,
        "previous_general_version": previous_general_version,
        "rationale": rationale, "warning": warning,
        "official_source": "https://medek.org.tr/medek-onlisans-degerlendirme-olcutleri-20-yayimlandi",
    }


def previous_general_framework_version(
    db: Session, program_id: int, framework_family: str, academic_year: str,
) -> str | None:
    previous = db.scalars(
        select(m.AccreditationApplication)
        .join(m.QualityFrameworkProfile, m.AccreditationApplication.framework_profile_id == m.QualityFrameworkProfile.id)
        .where(
            m.AccreditationApplication.program_id == program_id,
            m.AccreditationApplication.academic_year < academic_year,
            m.AccreditationApplication.application_type.in_(["general", "renewal"]),
            m.QualityFrameworkProfile.framework_family == framework_family,
        )
        .order_by(m.AccreditationApplication.academic_year.desc(), m.AccreditationApplication.id.desc())
    ).first()
    if not previous:
        return None
    framework = db.get(m.QualityFrameworkProfile, previous.framework_profile_id)
    return str(framework.version) if framework else None


def validate_medek_framework_selection(
    db: Session,
    framework: m.QualityFrameworkProfile,
    academic_year: str,
    application_type: str,
    *,
    program_id: int | None = None,
) -> dict[str, Any]:
    if framework.framework_family != "MEDEK":
        return {"valid": True, "family": framework.framework_family}
    previous_version = previous_general_framework_version(db, program_id, "MEDEK", academic_year) if program_id is not None else None
    route = medek_version_route(db, academic_year, application_type, framework.version, previous_version)
    if framework.version not in route["allowed_versions"]:
        if route["selection_required"] and not route["allowed_versions"]:
            raise ValueError(route["warning"] or "Önceki genel MEDEK sürümü doğrulanmalıdır.")
        allowed = ", ".join(route["allowed_versions"]) or "önceki genel değerlendirme sürümü"
        raise ValueError(f"Bu MEDEK değerlendirme dönemi/türü için Sürüm {framework.version} kullanılamaz. İzin verilen: {allowed}.")
    return {**route, "valid": True}


def medek_program_specific_profile(
    db: Session,
    program_id: int,
    framework_id: int,
    academic_year: str | None = None,
) -> dict[str, Any]:
    require_program_access(db, program_id, write=False, accreditation=True)
    program = db.get(m.Program, program_id)
    if not program:
        raise ValueError("Program bulunamadı")
    framework = db.get(m.QualityFrameworkProfile, framework_id)
    if not framework or framework.framework_family != "MEDEK":
        raise ValueError("Programa özgü çıktı profili için MEDEK framework seçilmelidir")
    catalog = medek_program_specific_catalog(program.name, framework.version)
    stmt = select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == program_id)
    if academic_year:
        stmt = stmt.where(m.ProgramOutcome.academic_year == academic_year)
    pos = list(db.scalars(stmt.order_by(m.ProgramOutcome.code)).all())
    po_ids = [x.id for x in pos]
    components: list[m.ProgramOutcomeComponent] = []
    if po_ids:
        components = list(db.scalars(select(m.ProgramOutcomeComponent).where(
            m.ProgramOutcomeComponent.program_outcome_id.in_(po_ids),
            m.ProgramOutcomeComponent.framework_family == "MEDEK",
            m.ProgramOutcomeComponent.framework_version == framework.version,
        )).all())
    mapped_by_code: dict[str, list[m.ProgramOutcomeComponent]] = defaultdict(list)
    for component in components:
        if component.framework_component_code:
            mapped_by_code[component.framework_component_code].append(component)
    po_by_id = {x.id: x for x in pos}
    rows = []
    for output in catalog.get("outputs", []):
        mapped_components = mapped_by_code.get(output["code"], [])
        rows.append({
            **output,
            "mapped": bool(mapped_components),
            "mappings": [
                {
                    "component_id": c.id,
                    "program_outcome_id": c.program_outcome_id,
                    "program_outcome_code": po_by_id.get(c.program_outcome_id).code if po_by_id.get(c.program_outcome_id) else "",
                    "program_outcome_description": po_by_id.get(c.program_outcome_id).description if po_by_id.get(c.program_outcome_id) else "",
                    "component_code": c.code,
                }
                for c in mapped_components
            ],
        })
    required = len(rows)
    mapped = sum(1 for row in rows if row["mapped"])
    coverage = round(mapped / required * 100, 2) if required else 0.0
    return {
        **catalog,
        "program_id": program_id, "framework_id": framework.id,
        "academic_year": academic_year,
        "outputs": rows,
        "mapped_count": mapped,
        "unmapped_count": max(0, required - mapped),
        "coverage_percent": coverage,
        "ready": catalog.get("match_status") == "exact" and required > 0 and mapped == required,
    }


def mudek_version_route(
    db: Session,
    academic_year: str,
    application_type: str = "general",
    preferred_version: str | None = None,
    previous_general_version: str | None = None,
) -> dict[str, Any]:
    """Return the official MÜDEK licence-program criteria versions allowed for a cycle.

    2026-2027 official application rules:
      * general/re-general: 3.0 or 3.1 (institution choice)
      * interim: 2.2
    From 2027-2028 general evaluations use 3.1. Later interim evaluations should
    inherit the criteria version of the previous general evaluation when known.
    """
    start = _academic_year_start(academic_year)
    kind = (application_type or "general").strip().casefold()
    if kind not in {"general", "interim", "renewal", "monitoring"}:
        raise ValueError("Desteklenmeyen MÜDEK değerlendirme türü")
    normalized_kind = "general" if kind in {"general", "renewal"} else kind

    frameworks = [x for x in seed_builtin_frameworks(db) if x.framework_family == "MÜDEK"]
    by_version = {str(x.version): x for x in frameworks}
    allowed_versions: list[str]
    selection_required = False
    rationale = ""
    warning = ""

    if start < 2026:
        allowed_versions = ["2.2"]
        rationale = "2026-2027 geçiş dönemi öncesindeki lisans değerlendirmeleri için tarihsel 2.2 profili."
    elif start == 2026:
        if normalized_kind == "interim":
            allowed_versions = ["2.2"]
            rationale = "2026-2027 MÜDEK ara değerlendirmelerinde Sürüm 2.2 kullanılır."
        elif normalized_kind == "general":
            allowed_versions = ["3.0", "3.1"]
            selection_required = preferred_version not in allowed_versions
            rationale = "2026-2027 genel değerlendirmelerinde kurum Sürüm 3.0 veya 3.1'i seçebilir."
        else:  # monitoring
            allowed_versions = [v for v in [previous_general_version, "3.1", "3.0", "2.2"] if v and v in by_version]
            allowed_versions = list(dict.fromkeys(allowed_versions))
            rationale = "İzleme faaliyetinde başvurunun bağlı olduğu resmî değerlendirme sürümü korunmalıdır."
    else:
        if normalized_kind == "general":
            allowed_versions = ["3.1"]
            rationale = "2027-2028 ve sonrasındaki genel değerlendirmelerde Sürüm 3.1 zorunludur."
        elif normalized_kind == "interim":
            if previous_general_version in by_version:
                allowed_versions = [str(previous_general_version)]
                rationale = "Ara değerlendirme, önceki genel değerlendirmede kullanılan ölçüt sürümünü izler."
            else:
                allowed_versions = ["3.1", "3.0", "2.2"]
                selection_required = True
                warning = "Önceki genel değerlendirme sürümü bilinmiyor; başvuru oluşturulmadan önce resmî önceki sürüm doğrulanmalıdır."
                rationale = "Ara değerlendirmede önceki genel değerlendirme ölçüt sürümü korunur."
        else:
            allowed_versions = [v for v in [previous_general_version, "3.1"] if v and v in by_version]
            allowed_versions = list(dict.fromkeys(allowed_versions))
            rationale = "İzleme faaliyetinde bağlı değerlendirme sürümü korunmalıdır."

    allowed = [by_version[v] for v in allowed_versions if v in by_version]
    selected = None
    if preferred_version in allowed_versions:
        selected = by_version.get(str(preferred_version))
    elif len(allowed) == 1:
        selected = allowed[0]
    elif "3.1" in allowed_versions and not selection_required:
        selected = by_version.get("3.1")

    return {
        "framework_family":"MÜDEK",
        "academic_year":academic_year,
        "application_type":kind,
        "normalized_application_type":normalized_kind,
        "allowed_versions":allowed_versions,
        "allowed_frameworks":[model_dict(x) for x in allowed],
        "selected_framework":model_dict(selected) if selected else None,
        "selection_required":selection_required,
        "previous_general_version":previous_general_version,
        "rationale":rationale,
        "warning":warning,
        "official_source":"https://www.mudek.org.tr/tr/akredit/basvuru2026.shtm",
    }


def validate_mudek_framework_selection(
    db: Session,
    framework: m.QualityFrameworkProfile,
    academic_year: str,
    application_type: str,
    *,
    program_id: int | None = None,
) -> dict[str, Any]:
    if framework.framework_family != "MÜDEK":
        return {"valid":True,"family":framework.framework_family}
    previous_version = previous_general_framework_version(db, program_id, "MÜDEK", academic_year) if program_id is not None else None
    route = mudek_version_route(db, academic_year, application_type, framework.version, previous_version)
    if framework.version not in route["allowed_versions"]:
        allowed = ", ".join(route["allowed_versions"]) or "önceki genel değerlendirme sürümü"
        raise ValueError(f"Bu MÜDEK değerlendirme dönemi/türü için Sürüm {framework.version} kullanılamaz. İzin verilen: {allowed}.")
    return {**route,"valid":True}

def university_quality_dashboard(db: Session, academic_year: str) -> dict[str, Any]:
    programs = db.scalars(select(m.Program).order_by(m.Program.faculty,m.Program.department,m.Program.name)).all()
    rows=[]
    framework_counts=defaultdict(int)
    for p in programs:
        try:
            routing=recommend_program_frameworks(db,p.id)
        except Exception:
            routing={"recommendations":[]}
        primary=next((x for x in routing["recommendations"] if x.get("is_primary")), None)
        if primary: framework_counts[primary["family"]]+=1
        courses=_count(db,m.Course,m.Course.program_id==p.id,m.Course.academic_year==academic_year)
        cycles=_count(db,m.QualityCycle,m.QualityCycle.program_id==p.id,m.QualityCycle.academic_year==academic_year)
        open_cycles=_count(db,m.QualityCycle,m.QualityCycle.program_id==p.id,m.QualityCycle.academic_year==academic_year,m.QualityCycle.status!="closed")
        evidence=_count(db,m.QualityEvidenceAsset,m.QualityEvidenceAsset.program_id==p.id)
        exams=_count(db,m.Exam,m.Exam.course_id.in_(select(m.Course.id).where(m.Course.program_id==p.id,m.Course.academic_year==academic_year)),m.Exam.status.in_(["approved","archived"]))
        # Executive quality health is intentionally explainable: measurement activity, evidence and closed-loop quality work.
        measurement_score = min(100, exams * 20) if courses else 0
        evidence_score = min(100, evidence * 20)
        cycle_score = 100 if cycles and open_cycles == 0 else (65 if cycles else 25)
        coverage_score = min(100, courses * 15)
        health_score = round(measurement_score * .35 + evidence_score * .25 + cycle_score * .25 + coverage_score * .15)
        risk_level = "critical" if health_score < 45 else ("watch" if health_score < 70 or open_cycles >= 3 else "healthy")
        rows.append({"id":p.id,"code":p.code,"name":p.name,"faculty":p.faculty,"department":p.department,"primary_framework":primary,"course_count":courses,"official_exam_count":exams,"quality_cycle_count":cycles,"open_cycle_count":open_cycles,"evidence_count":evidence,"quality_health":health_score,"risk_level":risk_level})
    faculties=defaultdict(lambda:{"programs":0,"courses":0,"official_exams":0,"open_cycles":0,"evidence":0,"health_total":0,"critical_programs":0})
    for r in rows:
        k=r["faculty"] or "Tanımsız Akademik Birim"; f=faculties[k]; f["programs"]+=1; f["courses"]+=r["course_count"]; f["official_exams"]+=r["official_exam_count"]; f["open_cycles"]+=r["open_cycle_count"]; f["evidence"]+=r["evidence_count"]; f["health_total"]+=r["quality_health"]; f["critical_programs"]+=1 if r["risk_level"]=="critical" else 0
    faculty_rows=[]
    for k,v in faculties.items():
        health=round(v["health_total"] / max(v["programs"],1))
        faculty_rows.append({"name":k,**{x:y for x,y in v.items() if x!="health_total"},"quality_health":health,"risk_level":"critical" if health<45 else ("watch" if health<70 or v["critical_programs"] else "healthy")})
    faculty_rows.sort(key=lambda x:(x["quality_health"],-x["open_cycles"],x["name"]))
    program_rows=sorted(rows,key=lambda x:(x["quality_health"],-x["open_cycle_count"],x["name"]))
    university_health=round(sum(x["quality_health"] for x in rows)/max(len(rows),1))
    critical_count=sum(1 for x in rows if x["risk_level"]=="critical")
    watch_count=sum(1 for x in rows if x["risk_level"]=="watch")
    executive_insights=[]
    if critical_count: executive_insights.append({"severity":"critical","title":f"{critical_count} program kritik kalite eşiğinin altında","action":"Kritik programları açıp ölçüm, kanıt ve PUKÖ açıklarını kapatın."})
    if sum(x["open_cycle_count"] for x in rows): executive_insights.append({"severity":"watch","title":f"{sum(x['open_cycle_count'] for x in rows)} açık PUKÖ döngüsü takip bekliyor","action":"Geciken iyileştirme aksiyonlarını sorumlu ve termin bazında izleyin."})
    if not executive_insights: executive_insights.append({"severity":"healthy","title":"Kurum kalite akışı kontrol altında","action":"Dönem trendlerini ve akreditasyon kanıt kapsamını izlemeye devam edin."})
    return {"academic_year":academic_year,"summary":{"program_count":len(rows),"faculty_count":len(faculties),"course_count":sum(x["course_count"] for x in rows),"official_exam_count":sum(x["official_exam_count"] for x in rows),"open_cycle_count":sum(x["open_cycle_count"] for x in rows),"evidence_count":sum(x["evidence_count"] for x in rows),"university_quality_health":university_health,"critical_program_count":critical_count,"watch_program_count":watch_count},"framework_distribution":dict(framework_counts),"faculties":faculty_rows,"programs":program_rows,"executive_insights":executive_insights}



def quality_escalation_queue(db: Session, academic_year: str) -> dict[str, Any]:
    """Build a deterministic governance queue from overdue/open PUKO cycles.

    This does not send messages or change permissions. It only recommends the
    next governance level so a human quality owner can act.
    """
    today = date.today()
    cycles = db.scalars(select(m.QualityCycle).where(
        m.QualityCycle.academic_year == academic_year,
        m.QualityCycle.status != "closed",
    ).order_by(m.QualityCycle.due_date.asc().nullslast(), m.QualityCycle.id.asc())).all()
    items: list[dict[str, Any]] = []
    counts = defaultdict(int)
    for cycle in cycles:
        program = db.get(m.Program, cycle.program_id)
        if not program:
            continue
        due = cycle.due_date
        days_overdue = (today - due).days if due else None
        days_remaining = (due - today).days if due else None
        if due is None:
            level = 0; state = "unscheduled"
            next_role = cycle.owner or "Program Kalite Sorumlusu"
            label = "Termin bekliyor"
        elif days_overdue is not None and days_overdue > 0:
            if days_overdue >= 30:
                level = 4; next_role = "Üniversite Kalite Birimi"; label = "Kurumsal eskalasyon"
            elif days_overdue >= 15:
                level = 3; next_role = "Fakülte / MYO Yönetimi"; label = "Akademik birim eskalasyonu"
            elif days_overdue >= 8:
                level = 2; next_role = "Bölüm / Program Başkanlığı"; label = "Yönetim eskalasyonu"
            else:
                level = 1; next_role = cycle.owner or "Program Kalite Sorumlusu"; label = "Sorumlu takibi"
            state = "overdue"
        elif days_remaining is not None and days_remaining <= 7:
            level = 0; state = "due_soon"; next_role = cycle.owner or "Program Kalite Sorumlusu"; label = "Termin yaklaşıyor"
        else:
            continue
        counts[state] += 1
        if state == "overdue": counts[f"level_{level}"] += 1
        items.append({
            "cycle_id": cycle.id, "program_id": program.id, "program_code": program.code,
            "program_name": program.name, "faculty": program.faculty, "department": program.department,
            "criterion_code": cycle.criterion_code, "title": cycle.title, "status": cycle.status,
            "owner": cycle.owner, "due_date": due.isoformat() if due else None,
            "days_overdue": days_overdue if days_overdue and days_overdue > 0 else 0,
            "days_remaining": days_remaining if days_remaining is not None and days_remaining >= 0 else None,
            "escalation_level": level, "escalation_state": state, "next_role": next_role,
            "label": label,
            "recommended_action": (
                "Termin ve sorumluyu tanımlayın." if state == "unscheduled" else
                "Sorumluya hatırlatma yapın ve kanıt hazırlığını kontrol edin." if state == "due_soon" else
                "Gecikme nedenini kaydedin, yeni termin ve kurtarma planını onaylayın." if level <= 1 else
                "Program/Bölüm yönetiminde aksiyon planını yeniden onaylayın." if level == 2 else
                "Akademik birim yönetiminde kaynak/engel kararını alın." if level == 3 else
                "Üniversite Kalite Biriminde kurumsal müdahale ve izleme kararı alın."
            ),
        })
    priority = {"overdue": 0, "due_soon": 1, "unscheduled": 2}
    items.sort(key=lambda x: (priority.get(x["escalation_state"], 9), -x["escalation_level"], -(x["days_overdue"] or 0), x["program_name"]))
    return {
        "academic_year": academic_year,
        "summary": {
            "open_cycle_count": len(cycles),
            "overdue_count": counts["overdue"],
            "due_soon_count": counts["due_soon"],
            "unscheduled_count": counts["unscheduled"],
            "institutional_escalation_count": counts["level_4"],
        },
        "items": items,
        "policy": [
            {"level": 1, "after_days": 1, "role": "Aksiyon sorumlusu"},
            {"level": 2, "after_days": 8, "role": "Bölüm / Program Başkanlığı"},
            {"level": 3, "after_days": 15, "role": "Fakülte / MYO Yönetimi"},
            {"level": 4, "after_days": 30, "role": "Üniversite Kalite Birimi"},
        ],
    }


def quality_action_recommendations(db: Session, program_id: int, academic_year: str, framework_id: int | None = None) -> dict[str, Any]:
    """Turn measurable quality gaps into explainable PUKO action proposals."""
    dashboard = program_dashboard(db, program_id, academic_year, framework_id)
    evidence_readiness = accreditation_evidence_readiness(db, program_id, academic_year, framework_id)
    framework = dashboard.get("framework") or {}
    family = str(framework.get("framework_family") or "KALİTE")
    precise_gaps_by_criterion: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for gap in evidence_readiness.get("priority_gaps") or []:
        if gap.get("subcriterion_code"):
            precise_gaps_by_criterion[str(gap.get("criterion_code") or "")].append(gap)
    proposals: list[dict[str, Any]] = []

    owner_by_hint = [
        (("öğrenci", "mezun"), "Program Başkanı / Öğrenci İşleri"),
        (("çıktı", "ölçme", "değerlendirme"), "Program Başkanı / Ders Sorumluları"),
        (("müfredat", "eğitim planı", "program tasarımı"), "Program Kurulu"),
        (("kadro", "öğretim"), "Bölüm Başkanlığı"),
        (("altyapı", "kaynak"), "Akademik Birim Yönetimi"),
        (("paydaş", "sektör"), "Program Başkanı / Danışma Kurulu"),
        (("iyileştirme", "kalite", "pukö"), "Program Kalite Sorumlusu"),
    ]

    for row in dashboard.get("criteria") or []:
        score = float(row.get("score") or 0)
        missing = [x.get("label") for x in (row.get("signals") or []) if not x.get("ok")]
        code = str(row.get("code") or "")
        precise = precise_gaps_by_criterion.get(code, [])[:3]
        if score >= 65 and not missing and not precise:
            continue
        name = str(row.get("name") or row.get("code") or "Kalite ölçütü")
        hay = name.casefold()
        owner = "Program Kalite Sorumlusu"
        for hints, candidate in owner_by_hint:
            if any(h in hay for h in hints):
                owner = candidate; break
        severity = "critical" if score < 40 else ("high" if score < 65 else "watch")
        days = 30 if severity == "critical" else (45 if severity == "high" else 60)
        due = date.today() + timedelta(days=days)
        if precise:
            gaps = [f"{x.get('subcriterion_code')} · {x.get('subcriterion_title')}" for x in precise]
        else:
            gaps = missing or ["Manuel kalite değerlendirmesi ve kanıt doğrulaması gerekli"]
        expected = []
        for item in precise:
            expected.extend(item.get("missing_evidence") or [])
        for gap in gaps[:4]:
            g = str(gap)
            if "sınav" in g.casefold() or "ölç" in g.casefold(): expected.append("Sınav/ölçme analiz raporu")
            elif "paydaş" in g.casefold(): expected.append("Paydaş toplantı/anket sonucu ve karar kaydı")
            elif "kadro" in g.casefold(): expected.append("Akademik kadro envanteri")
            elif "altyapı" in g.casefold(): expected.append("Altyapı envanteri ve uygunluk kanıtı")
            elif "müfredat" in g.casefold() or "akts" in g.casefold(): expected.append("Müfredat/AKTS doğrulama çıktısı")
            elif "pukö" in g.casefold() or "iyileştirme" in g.casefold(): expected.append("Kapatılmış PUKÖ ve etkililik kanıtı")
            else: expected.append(f"{g} kanıtı")
        expected = list(dict.fromkeys(expected))
        proposal_id = f"{program_id}:{framework.get('id') or framework_id or 0}:{academic_year}:{row.get('code')}"
        proposals.append({
            "proposal_id": proposal_id, "program_id": program_id, "academic_year": academic_year,
            "framework_id": framework.get("id"), "framework_family": family,
            "criterion_code": str(row.get("code") or ""), "criterion_name": name,
            "score": score, "severity": severity, "owner_role": owner, "suggested_due_date": due.isoformat(),
            "title": f"{name} kalite açığını kapat",
            "why": f"{family} {row.get('code')} ölçütü %{round(score)} hazır bulunuşluk düzeyinde.",
            "gap_signals": gaps, "expected_evidence": expected,
            "priority_subcriteria": precise,
            "plan_text": "Eksik sinyalleri doğrula, sorumluları ata ve gerekli akademik/idarî girdileri tamamla.",
            "do_text": "Önerilen iyileştirmeleri uygula ve oluşan belgeleri kanıt alanına bağla.",
            "check_text": "Aynı ölçütü yeniden ölç; hedef en az %65 ve tüm kritik sinyallerin tamamlanmasıdır.",
            "act_text": "Sonucu kurul/kalite kararına bağla; etkiliyse standardize et, değilse yeni PUKÖ aç.",
        })
    # 6.47: surface exact MÜDEK evidence-room / EK-1 gaps as actionable work,
    # not merely as passive dashboard warnings.
    if family == "MÜDEK" and framework.get("id"):
        fw_id = int(framework["id"])
        supplemental: list[dict[str, Any]] = []
        try:
            ek1 = mudek_ek1_profile(db, program_id, academic_year, fw_id)
            for item in [x for x in (ek1.get("topics") or []) if x.get("status") in {"gap", "review"}][:3]:
                is_gap = item.get("status") == "gap"
                supplemental.append({
                    "proposal_id":f"{program_id}:{fw_id}:{academic_year}:{item.get('code')}",
                    "program_id":program_id,"academic_year":academic_year,"framework_id":fw_id,"framework_family":family,
                    "criterion_code":item.get("code"),"criterion_name":"Ölçüt 5.1 · EK-1",
                    "score":0 if is_gap else 50,"severity":"critical" if is_gap else "high",
                    "owner_role":"Program Başkanı / Müfredat Komisyonu","suggested_due_date":(date.today()+timedelta(days=30 if is_gap else 45)).isoformat(),
                    "title":f"{item.get('code')} EK-1 kapsam açığını kapat",
                    "why":"MÜDEK Ölçüt 5.1 kapsamında disipline özgü eğitim planı konusu tam doğrulanmadı.",
                    "gap_signals":[f"Ders eşleşmesi: {item.get('matched_course_count',0)}",f"Doğrudan kanıt: {item.get('evidence_count',0)}",("Manuel doğrulama tamam" if item.get('manual_review_completed') else "Manuel kalite doğrulaması eksik")],
                    "expected_evidence":[f"{item.get('code')} doğrudan kanıtı","İlgili ders(ler) ve içerik eşleşmesi","Kalite birimi manuel doğrulaması"],
                    "priority_subcriteria":[],
                    "plan_text":"EK-1 konusunun müfredattaki karşılığını, doğrudan kanıtını ve kalite doğrulamasını tamamla.",
                    "do_text":"İlgili dersleri doğrula; kanıtı EK-1 koduyla yükle ve olgunluk incelemesini kaydet.",
                    "check_text":"EK-1 hazırlık matrisinde ilgili kodun Hazır durumuna geçtiğini doğrula.",
                    "act_text":"Müfredat/kanıt açığı kalıcıysa program kurulunda iyileştirme kararı al ve standardize et.",
                })
        except Exception:
            pass
        for room, owner in (("BBO","Bölüm Başkanlığı / Program Kalite Sorumlusu"),("FBO","Dekanlık / Fakülte Kalite Sorumlusu")):
            try:
                readiness = mudek_evidence_room_readiness(db, program_id, academic_year, room, fw_id)
            except Exception:
                continue
            room_gaps=[x for x in (readiness.get("items") or []) if not x.get("optional") and x.get("status") in {"gap","review"}][:4]
            for item in room_gaps:
                is_gap=item.get("status")=="gap"
                expected=list(item.get("required_evidence") or []) or [f"{item.get('code')} kanıtı"]
                supplemental.append({
                    "proposal_id":f"{program_id}:{fw_id}:{academic_year}:{item.get('code')}",
                    "program_id":program_id,"academic_year":academic_year,"framework_id":fw_id,"framework_family":family,
                    "criterion_code":item.get("code"),"criterion_name":f"MÜDEK {room}",
                    "score":0 if is_gap else 50,"severity":"critical" if is_gap else "high",
                    "owner_role":item.get("owner") or owner,"suggested_due_date":(date.today()+timedelta(days=30 if is_gap else 45)).isoformat(),
                    "title":f"{item.get('code')} kanıt açığını kapat",
                    "why":f"MÜDEK {room} hazırlık matrisinde {item.get('title')} {'eksik' if is_gap else 'kontrol bekliyor'}.",
                    "gap_signals":[f"Doğrudan kanıt: {item.get('exact_evidence_count',0)}",f"Destek kanıtı: {item.get('support_evidence_count',0)}",("Sistem sinyali var" if item.get('auto_signal') else "Sistem sinyali yok")],
                    "expected_evidence":expected,"priority_subcriteria":[],
                    "plan_text":f"{room} gereksinimini doğrula, sorumluyu ata ve doğrudan kanıtı {item.get('code')} koduyla hazırla.",
                    "do_text":"Beklenen belge/öğrenci çalışması/kurumsal kanıtı üret ve kanıt merkezine yükle.",
                    "check_text":f"{room} hazırlık matrisinde ilgili kodun Hazır durumuna geçtiğini doğrula.",
                    "act_text":"Eksik tekrar oluşuyorsa belge üretim sorumluluğunu ve periyodik kalite takvimini standardize et.",
                })
        existing_ids={x.get("proposal_id") for x in proposals}
        proposals.extend(x for x in supplemental if x.get("proposal_id") not in existing_ids)

    proposals.sort(key=lambda x: ({"critical":0,"high":1,"watch":2}.get(x["severity"],3), x["score"], x["criterion_code"]))
    return {"program_id":program_id,"academic_year":academic_year,"framework":framework,"count":len(proposals),"proposals":proposals}

def curriculum_check(db: Session, program_id: int, academic_year: str, *, thresholds: dict[str, Any] | None = None) -> dict[str, Any]:
    require_program_access(db, program_id, write=False, accreditation=True)
    rows = db.scalars(select(m.CurriculumItem).where(
        m.CurriculumItem.program_id == program_id, m.CurriculumItem.academic_year == academic_year
    ).order_by(m.CurriculumItem.term, m.CurriculumItem.class_level, m.CurriculumItem.course_code)).all()
    thresholds = {"professional_ects": 60, "program_specific_ects": 20, "external_stakeholder_ects": 5, "applied_current_tech_ects": 15, **(thresholds or {})}
    total = round(sum(float(x.ects or 0) for x in rows), 2)
    professional = round(sum(float(x.ects or 0) for x in rows if x.is_professional), 2)
    program_specific = round(sum(float(x.ects or 0) for x in rows if x.is_program_specific), 2)
    stakeholder = round(sum(float(x.ects or 0) for x in rows if x.is_external_stakeholder_supported), 2)
    applied = round(sum(float(x.ects or 0) for x in rows if x.is_applied_or_current_tech), 2)
    checks = [
        {"code": "5.1a", "label": "Programa/alana özgü mesleki dersler", "actual": professional, "required": thresholds["professional_ects"], "unit": "AKTS", "passed": professional >= float(thresholds["professional_ects"])},
        {"code": "5.1b", "label": "Programa özgü çıktıları sağlayan dersler", "actual": program_specific, "required": thresholds["program_specific_ects"], "unit": "AKTS", "passed": program_specific >= float(thresholds["program_specific_ects"])},
        {"code": "5.2", "label": "Dış paydaş önerilerini dikkate alan dersler", "actual": stakeholder, "required": thresholds["external_stakeholder_ects"], "unit": "AKTS", "passed": stakeholder >= float(thresholds["external_stakeholder_ects"])},
        {"code": "5.3", "label": "İşletmede eğitim / staj / uygulama / güncel mesleki teknoloji", "actual": applied, "required": thresholds["applied_current_tech_ects"], "unit": "AKTS", "passed": applied >= float(thresholds["applied_current_tech_ects"])},
    ]
    return {
        "program_id": program_id, "academic_year": academic_year, "course_count": len(rows), "total_ects": total,
        "professional_ects": professional, "program_specific_ects": program_specific,
        "external_stakeholder_ects": stakeholder, "applied_current_tech_ects": applied,
        "checks": checks, "passed": sum(1 for x in checks if x["passed"]), "total_checks": len(checks),
        "readiness_percent": round(sum(1 for x in checks if x["passed"]) / len(checks) * 100, 2) if checks else 0,
        "rows": [model_dict(x) for x in rows],
    }


def _count(db: Session, model, *criteria) -> int:
    stmt = select(func.count()).select_from(model)
    if criteria:
        stmt = stmt.where(*criteria)
    return int(db.scalar(stmt) or 0)


def _manual_assessments(db: Session, program_id: int, framework_id: int, academic_year: str) -> dict[str, m.QualityCriterionAssessment]:
    rows = db.scalars(select(m.QualityCriterionAssessment).where(
        m.QualityCriterionAssessment.program_id == program_id,
        m.QualityCriterionAssessment.framework_profile_id == framework_id,
        m.QualityCriterionAssessment.academic_year == academic_year,
    )).all()
    return {x.criterion_code: x for x in rows}


def _criterion_signals(db: Session, program: m.Program, academic_year: str, curriculum: dict[str, Any], framework: m.QualityFrameworkProfile) -> dict[str, list[tuple[str, bool]]]:
    program_id = program.id
    student_count = _count(db, m.Student, m.Student.program_id == program_id)
    po_count = _count(db, m.ProgramOutcome, m.ProgramOutcome.program_id == program_id, m.ProgramOutcome.academic_year == academic_year)
    course_ids = [x for x in db.scalars(select(m.Course.id).where(m.Course.program_id == program_id, m.Course.academic_year == academic_year)).all()]
    lo_count = _count(db, m.LearningOutcome, m.LearningOutcome.course_id.in_(course_ids)) if course_ids else 0
    map_count = 0
    if course_ids:
        lo_ids = db.scalars(select(m.LearningOutcome.id).where(m.LearningOutcome.course_id.in_(course_ids))).all()
        if lo_ids:
            map_count = _count(db, m.OutcomeMapping, m.OutcomeMapping.learning_outcome_id.in_(list(lo_ids)))
    stakeholder_count = _count(db, m.StakeholderRecord, m.StakeholderRecord.program_id == program_id)
    graduate_count = _count(db, m.GraduateRecord, m.GraduateRecord.program_id == program_id)
    faculty_count = _count(db, m.FacultyRecord, m.FacultyRecord.program_id == program_id)
    infra_count = _count(db, m.InfrastructureRecord, m.InfrastructureRecord.program_id == program_id)
    cycle_count = _count(db, m.QualityCycle, m.QualityCycle.program_id == program_id, m.QualityCycle.academic_year == academic_year)
    closed_cycle_count = _count(db, m.QualityCycle, m.QualityCycle.program_id == program_id, m.QualityCycle.academic_year == academic_year, m.QualityCycle.status == "closed")
    decision_count = _count(db, m.GovernanceDecision, m.GovernanceDecision.program_id == program_id)
    evidence_count = _count(db, m.QualityEvidenceAsset, m.QualityEvidenceAsset.program_id == program_id)
    official_exam_count = _count(db, m.Exam, m.Exam.course_id.in_(course_ids), m.Exam.status.in_(["approved", "archived"])) if course_ids else 0
    improvement_count = _count(db, m.ImprovementAction, m.ImprovementAction.exam_id.in_(select(m.Exam.id).where(m.Exam.course_id.in_(course_ids)))) if course_ids else 0

    if framework.framework_family == "YÖKAK":
        return {
            "A.1": [("Kalite döngüsü kaydı", cycle_count > 0), ("Kurul/karar kaydı", decision_count > 0), ("Kanıt varlığı", evidence_count > 0)],
            "A.2": [("Kurul/karar zinciri", decision_count > 0), ("Program tanımı", bool(program.name and program.code))],
            "A.3": [("Yönetim kararları", decision_count > 0), ("Kalite kanıtları", evidence_count > 0)],
            "A.4": [("Paydaş kaydı", stakeholder_count > 0), ("Paydaş geri bildiriminin karara dönüşmesi", _count(db, m.StakeholderRecord, m.StakeholderRecord.program_id == program_id, m.StakeholderRecord.resulting_action != "") > 0)],
            "A.5": [("Uluslararasılaşma kanıtı / manuel değerlendirme", False)],
            "B.1": [("Müfredat kaydı", curriculum["course_count"] > 0), ("Program çıktıları", po_count > 0), ("ÖÇ-PÇ eşlemesi", map_count > 0)],
            "B.2": [("Ders/ÖÇ verisi", lo_count > 0), ("Resmî ölçme sonucu", official_exam_count > 0)],
            "B.3": [("Altyapı / öğrenme kaynağı kaydı", infra_count > 0), ("Öğrenci kaydı", student_count > 0)],
            "B.4": [("Öğretim kadrosu envanteri", faculty_count > 0)],
            "C.1": [("Araştırma kaynağı / manuel değerlendirme", False)],
            "C.2": [("Araştırma yetkinliği / manuel değerlendirme", False)],
            "C.3": [("Araştırma performansı / manuel değerlendirme", False)],
            "D.1": [("Toplumsal paydaş kaydı", stakeholder_count > 0)],
            "D.2": [("İzlenen/kapalı PUKÖ", closed_cycle_count > 0)],
        }

    if framework.framework_family == "MÜDEK":
        return {
            "1":[("Öğrenci kayıtları",student_count>0),("Resmî ölçme sonucu",official_exam_count>0)],
            "2":[("Paydaş kaydı",stakeholder_count>0),("Kurul/karar kaydı",decision_count>0)],
            "3":[("Program çıktıları",po_count>0),("Ders öğrenme çıktıları",lo_count>0),("ÖÇ-PÇ eşlemesi",map_count>0),("Resmî sınav ölçümü",official_exam_count>0)],
            "4":[("PUKÖ döngüsü",cycle_count>0),("Kapalı PUKÖ",closed_cycle_count>0),("İyileştirme aksiyonu",improvement_count>0)],
            "5":[("Müfredat envanteri",curriculum["course_count"]>0)],
            "6":[("Öğretim kadrosu",faculty_count>0)],
            "7":[("Altyapı",infra_count>0)],
            "8":[("Kalite kanıtı",evidence_count>0)],
            "9":[("Kurul/karar zinciri",decision_count>0)],
        }
    if framework.framework_family == "TURAK":
        return {
            "1":[("Program tanımı",bool(program.name and program.code)),("Kurul/karar",decision_count>0)],
            "2":[("Öğrenci kayıtları",student_count>0),("Mezun izleme",graduate_count>0)],
            "3":[("Program çıktıları",po_count>0),("ÖÇ-PÇ eşlemesi",map_count>0),("Resmî sınav",official_exam_count>0)],
            "4":[("Müfredat",curriculum["course_count"]>0),("Uygulamalı/güncel ders",curriculum["applied_current_tech_ects"]>0)],
            "5":[("Öğretim kadrosu",faculty_count>0)],
            "6":[("Altyapı",infra_count>0)],
            "7":[("Paydaş/sektör kaydı",stakeholder_count>0),("Paydaşın aksiyona dönüşmesi",_count(db,m.StakeholderRecord,m.StakeholderRecord.program_id==program_id,m.StakeholderRecord.resulting_action!="")>0)],
            "8":[("PUKÖ",cycle_count>0),("Kapalı PUKÖ",closed_cycle_count>0),("Kanıt",evidence_count>0)],
        }
    if framework.framework_family == "ESG":
        return {
            "1.1":[("Kalite döngüsü",cycle_count>0),("Kurul/karar",decision_count>0)],
            "1.2":[("Müfredat",curriculum["course_count"]>0),("Program çıktıları",po_count>0),("Paydaş",stakeholder_count>0)],
            "1.3":[("ÖÇ ölçümü",lo_count>0),("Resmî sınav",official_exam_count>0)],
            "1.4":[("Öğrenci kaydı",student_count>0),("Mezun izleme",graduate_count>0)],
            "1.5":[("Öğretim kadrosu",faculty_count>0)],
            "1.6":[("Altyapı/kaynak",infra_count>0)],
            "1.7":[("Kanıt/veri izi",evidence_count>0)],
            "1.8":[("Kurumsal karar/kanıt",decision_count>0 and evidence_count>0)],
            "1.9":[("PUKÖ",cycle_count>0),("Kapatılmış PUKÖ",closed_cycle_count>0),("İyileştirme",improvement_count>0)],
            "1.10":[("Akreditasyon kanıtı",evidence_count>0)],
        }
    if framework.framework_family == "ACQUIN":
        return {
            "SYS.1":[("Kalite döngüsü",cycle_count>0),("Kanıt",evidence_count>0)],
            "SYS.2":[("Yönetişim kararı",decision_count>0)],
            "SYS.3":[("Müfredat",curriculum["course_count"]>0),("Program çıktıları",po_count>0)],
            "SYS.4":[("Resmî ölçme",official_exam_count>0),("ÖÇ-PÇ eşlemesi",map_count>0)],
            "SYS.5":[("Paydaş",stakeholder_count>0),("Mezun",graduate_count>0)],
            "SYS.6":[("Kadro",faculty_count>0),("Altyapı",infra_count>0)],
            "SYS.7":[("PUKÖ",cycle_count>0),("Kapalı PUKÖ",closed_cycle_count>0),("İyileştirme",improvement_count>0)],
        }

    # MEDEK v1.1 and v2.0 share most evidence domains. v2.0 swaps the order of plan/improvement.
    plan_signals = [("Müfredat envanteri", curriculum["course_count"] > 0), ("AKTS eşikleri", curriculum["readiness_percent"] >= 100)]
    improvement_signals = [("PUKÖ döngüsü", cycle_count > 0), ("Kapatılmış/ACT aşamasına ulaşmış döngü", closed_cycle_count > 0), ("İyileştirme aksiyonu", improvement_count > 0)]
    base = {
        "1": [("Öğrenci kayıtları", student_count > 0), ("Mezun izleme", graduate_count > 0), ("Öğrenci/mezun paydaş geri bildirimi", stakeholder_count > 0)],
        "2": [("İç/dış paydaş kaydı", stakeholder_count > 0), ("Kurul/karar zinciri", decision_count > 0)],
        "3": [("Program çıktıları", po_count > 0), ("Ders öğrenme çıktıları", lo_count > 0), ("ÖÇ-PÇ katkı eşlemesi", map_count > 0), ("Resmî sınav ölçümü", official_exam_count > 0)],
        "4": improvement_signals,
        "5": plan_signals,
        "6": [("Öğretim kadrosu envanteri", faculty_count > 0)],
        "7": [("Altyapı/laboratuvar envanteri", infra_count > 0)],
        "8": [("Kurul/karar zinciri", decision_count > 0), ("Kalite kanıtı", evidence_count > 0)],
        "9": [("Programa özgü çıktı", po_count > 0), ("Programa özgü ders AKTS", curriculum["program_specific_ects"] > 0)],
    }
    if framework.code == "MEDEK-2028":
        # v2.0 moves Öğretim Planı to criterion 4 and Sürekli İyileştirme to criterion 5.
        base["4"], base["5"] = plan_signals, improvement_signals
        base.pop("9", None)
    return base


def program_dashboard(db: Session, program_id: int, academic_year: str, framework_id: int | None = None) -> dict[str, Any]:
    program = require_program_access(db, program_id, write=False, accreditation=True)
    frameworks = seed_builtin_frameworks(db)
    if framework_id:
        framework = db.get(m.QualityFrameworkProfile, framework_id)
        if not framework:
            raise ValueError("Kalite çerçevesi bulunamadı")
    else:
        start_year = int(str(academic_year).split("-", 1)[0]) if str(academic_year).split("-", 1)[0].isdigit() else datetime.now().year
        if start_year >= 2028:
            framework = next((x for x in frameworks if x.code == "MEDEK-2028"), frameworks[0])
        else:
            framework = next((x for x in frameworks if x.code == "MEDEK-2026"), frameworks[0])
    curriculum = curriculum_check(db, program_id, academic_year, thresholds=framework.thresholds or {})
    signals = _criterion_signals(db, program, academic_year, curriculum, framework)
    manual = _manual_assessments(db, program_id, framework.id, academic_year)
    criteria_rows = []
    for criterion in framework.criteria or []:
        code = str(criterion.get("code") or "")
        criterion_signals = signals.get(code, [])
        auto = round(sum(1 for _, ok in criterion_signals if ok) / len(criterion_signals) * 100, 2) if criterion_signals else 0.0
        assessment = manual.get(code)
        manual_score = float(assessment.maturity_level * 20) if assessment else None
        if assessment and criterion_signals:
            score = round((auto + manual_score) / 2, 2)
        elif assessment:
            score = manual_score
        else:
            score = auto
        if score >= 85: readiness = "strong"
        elif score >= 65: readiness = "ready"
        elif score >= 40: readiness = "developing"
        else: readiness = "gap"
        criteria_rows.append({
            **criterion, "score": score, "readiness": readiness, "auto_score": auto,
            "manual_maturity": assessment.maturity_level if assessment else None,
            "manual_status": assessment.quality_status if assessment else None,
            "manual_note": assessment.note if assessment else "",
            "signals": [{"label": label, "ok": ok} for label, ok in criterion_signals],
        })
    readiness_percent = round(sum(float(x["score"]) for x in criteria_rows) / len(criteria_rows), 2) if criteria_rows else 0.0

    counts = {
        "curriculum": _count(db, m.CurriculumItem, m.CurriculumItem.program_id == program_id, m.CurriculumItem.academic_year == academic_year),
        "stakeholders": _count(db, m.StakeholderRecord, m.StakeholderRecord.program_id == program_id),
        "graduates": _count(db, m.GraduateRecord, m.GraduateRecord.program_id == program_id),
        "faculty": _count(db, m.FacultyRecord, m.FacultyRecord.program_id == program_id),
        "infrastructure": _count(db, m.InfrastructureRecord, m.InfrastructureRecord.program_id == program_id),
        "quality_cycles": _count(db, m.QualityCycle, m.QualityCycle.program_id == program_id, m.QualityCycle.academic_year == academic_year),
        "governance_decisions": _count(db, m.GovernanceDecision, m.GovernanceDecision.program_id == program_id),
        "quality_evidence": _count(db, m.QualityEvidenceAsset, m.QualityEvidenceAsset.program_id == program_id),
    }
    return {
        "program": {"id": program.id, "code": program.code, "name": program.name, "faculty": program.faculty, "department": program.department},
        "academic_year": academic_year,
        "framework": model_dict(framework),
        "readiness_percent": readiness_percent,
        "criteria": criteria_rows,
        "curriculum": curriculum,
        "counts": counts,
        "readiness_label": "Hazır" if readiness_percent >= 70 else ("Geliştiriliyor" if readiness_percent >= 40 else "Kritik Açıklar Var"),
    }




def _subcriterion_automation_context(
    db: Session,
    program: m.Program,
    academic_year: str,
    curriculum: dict[str, Any],
    framework: dict[str, Any],
) -> dict[str, bool | None]:
    """Build conservative, explainable automation signals for framework subcriteria.

    `None` means the requirement needs human review because DOU Assess does not own a
    sufficiently authoritative source for an automatic pass/fail decision.  This is
    intentionally stricter than treating an absent integration as a failed criterion.
    """
    program_id = program.id
    course_ids = list(db.scalars(select(m.Course.id).where(
        m.Course.program_id == program_id,
        m.Course.academic_year == academic_year,
    )).all())
    lo_ids: list[int] = []
    if course_ids:
        lo_ids = list(db.scalars(select(m.LearningOutcome.id).where(m.LearningOutcome.course_id.in_(course_ids))).all())
    po_ids = list(db.scalars(select(m.ProgramOutcome.id).where(
        m.ProgramOutcome.program_id == program_id,
        m.ProgramOutcome.academic_year == academic_year,
    )).all())

    student_count = _count(db, m.Student, m.Student.program_id == program_id)
    stakeholder_count = _count(db, m.StakeholderRecord, m.StakeholderRecord.program_id == program_id)
    graduate_count = _count(db, m.GraduateRecord, m.GraduateRecord.program_id == program_id)
    faculty_count = _count(db, m.FacultyRecord, m.FacultyRecord.program_id == program_id)
    infrastructure_count = _count(db, m.InfrastructureRecord, m.InfrastructureRecord.program_id == program_id)
    decision_count = _count(db, m.GovernanceDecision, m.GovernanceDecision.program_id == program_id)
    evidence_count = _count(db, m.QualityEvidenceAsset, m.QualityEvidenceAsset.program_id == program_id)
    pea_count = _count(db, m.ProgramEducationalObjective,
        m.ProgramEducationalObjective.program_id == program_id,
        m.ProgramEducationalObjective.academic_year == academic_year,
    )
    po_count = len(po_ids)
    lo_count = len(lo_ids)
    mapping_count = _count(db, m.OutcomeMapping, m.OutcomeMapping.learning_outcome_id.in_(lo_ids)) if lo_ids else 0
    official_exam_count = _count(
        db, m.Exam,
        m.Exam.course_id.in_(course_ids),
        m.Exam.status.in_(["approved", "archived"]),
    ) if course_ids else 0
    quality_cycle_count = _count(db, m.QualityCycle,
        m.QualityCycle.program_id == program_id,
        m.QualityCycle.academic_year == academic_year,
    )
    closed_cycle_count = _count(db, m.QualityCycle,
        m.QualityCycle.program_id == program_id,
        m.QualityCycle.academic_year == academic_year,
        m.QualityCycle.status.in_(["closed", "completed", "act", "acting"]),
    )
    outcome_snapshot_count = _count(db, m.StudentOutcomeSnapshot,
        m.StudentOutcomeSnapshot.program_id == program_id,
        m.StudentOutcomeSnapshot.academic_year == academic_year,
    )
    graduation_snapshot_count = _count(db, m.StudentOutcomeSnapshot,
        m.StudentOutcomeSnapshot.program_id == program_id,
        m.StudentOutcomeSnapshot.academic_year == academic_year,
        m.StudentOutcomeSnapshot.snapshot_type == "graduation",
        m.StudentOutcomeSnapshot.frozen.is_(True),
    )
    component_count = _count(db, m.ProgramOutcomeComponent, m.ProgramOutcomeComponent.program_outcome_id.in_(po_ids)) if po_ids else 0
    po_with_components = 0
    if po_ids:
        po_with_components = int(db.scalar(select(func.count(func.distinct(m.ProgramOutcomeComponent.program_outcome_id))).where(
            m.ProgramOutcomeComponent.program_outcome_id.in_(po_ids)
        )) or 0)
    mudek_component_codes = 0
    medek_component_codes = 0
    medek_program_specific_codes = 0
    if po_ids:
        mudek_component_codes = int(db.scalar(select(func.count(func.distinct(m.ProgramOutcomeComponent.framework_component_code))).where(
            m.ProgramOutcomeComponent.program_outcome_id.in_(po_ids),
            m.ProgramOutcomeComponent.framework_family == "MÜDEK",
            m.ProgramOutcomeComponent.framework_component_code != "",
        )) or 0)
        medek_component_codes = int(db.scalar(select(func.count(func.distinct(m.ProgramOutcomeComponent.framework_component_code))).where(
            m.ProgramOutcomeComponent.program_outcome_id.in_(po_ids),
            m.ProgramOutcomeComponent.framework_family == "MEDEK",
            m.ProgramOutcomeComponent.framework_version == str(framework.get("version") or ""),
            m.ProgramOutcomeComponent.framework_component_code.like("PÇ%"),
        )) or 0)
        medek_program_specific_codes = int(db.scalar(select(func.count(func.distinct(m.ProgramOutcomeComponent.framework_component_code))).where(
            m.ProgramOutcomeComponent.program_outcome_id.in_(po_ids),
            m.ProgramOutcomeComponent.framework_family == "MEDEK",
            m.ProgramOutcomeComponent.framework_version == str(framework.get("version") or ""),
            m.ProgramOutcomeComponent.framework_component_code.like("PÖÇ%"),
        )) or 0)

    faculty_ids = list(db.scalars(select(m.FacultyRecord.id).where(m.FacultyRecord.program_id == program_id)).all())
    approved_cv_faculty = 0
    if faculty_ids:
        approved_cv_faculty = int(db.scalar(select(func.count(func.distinct(m.FacultyCVRevision.faculty_record_id))).where(
            m.FacultyCVRevision.faculty_record_id.in_(faculty_ids),
            m.FacultyCVRevision.approved.is_(True),
        )) or 0)
    part_time_count = int(db.scalar(select(func.count(m.FacultyRecord.id)).where(
        m.FacultyRecord.program_id == program_id,
        m.FacultyRecord.employment_type != "Tam Zamanlı",
    )) or 0)

    controlled_docs = list(db.scalars(select(m.ControlledDocument).where(
        (m.ControlledDocument.program_id == program_id) | (m.ControlledDocument.program_id.is_(None)),
        m.ControlledDocument.status == "active",
    )).all())
    controlled_doc_ids = [x.id for x in controlled_docs]
    approved_revision_doc_ids: set[int] = set()
    if controlled_doc_ids:
        approved_revision_doc_ids = set(db.scalars(select(m.ControlledDocumentRevision.document_id).where(
            m.ControlledDocumentRevision.document_id.in_(controlled_doc_ids),
            m.ControlledDocumentRevision.status.in_(["approved", "active", "published"]),
        )).all())
    approved_docs = [x for x in controlled_docs if x.id in approved_revision_doc_ids]
    approved_doc_text = " ".join(
        f"{x.document_type} {x.document_code} {x.title}".casefold() for x in approved_docs
    )
    institution_profile_signal: bool | None = True if any(k in approved_doc_text for k in ["kurum profil", "üniversite profil", "universite profil", "institution profile"]) else None
    school_profile_signal: bool | None = True if any(k in approved_doc_text for k in ["myo", "meslek yüksekokulu", "meslek yuksekokulu", "school profile", "birim profil"]) else None
    graduation_policy_signal: bool | None = True if any(k in approved_doc_text for k in ["mezuniyet", "yatay geçiş", "yatay gecis", "dikey geçiş", "dikey gecis", "kabul koş", "kabul kos"]) else None
    part_time_monitoring_signal: bool | None
    if part_time_count == 0:
        part_time_monitoring_signal = True
    elif any(k in approved_doc_text for k in ["yarı zamanlı", "yari zamanli", "ek görev", "ek gorev", "ders saat ücret", "ders saat ucret"]):
        part_time_monitoring_signal = True
    else:
        part_time_monitoring_signal = None

    check_map = {str(x.get("code")): bool(x.get("passed")) for x in curriculum.get("checks") or []}
    program_identity = bool(program.code and program.name and (program.department or program.faculty))

    # For exact MÜDEK outcome coverage, do not infer compliance just because a program
    # happens to have 11 locally named outcomes.  Require explicit framework component
    # mapping; if none exists, leave it for manual/framework mapping review.
    mudek_outcomes: bool | None
    if mudek_component_codes:
        mudek_outcomes = mudek_component_codes >= int((framework.get("thresholds") or {}).get("required_mudek_outcomes", 11))
    else:
        mudek_outcomes = None
    medek_outcomes: bool | None
    if medek_component_codes:
        medek_outcomes = medek_component_codes >= int((framework.get("thresholds") or {}).get("required_medek_outcomes", 10))
    else:
        medek_outcomes = None
    medek_specific_catalog = medek_program_specific_catalog(program.name, str(framework.get("version") or "")) if framework.get("framework_family") == "MEDEK" else {"match_status":"manual_required","required_count":0}
    medek_program_specific: bool | None
    if medek_specific_catalog.get("match_status") != "exact":
        medek_program_specific = None
    else:
        required_specific = int(medek_specific_catalog.get("required_count") or 0)
        medek_program_specific = required_specific > 0 and medek_program_specific_codes >= required_specific

    return {
        "students": student_count > 0,
        "manual": None,
        "decisions": decision_count > 0,
        "stakeholders": stakeholder_count > 0,
        "official_exam": official_exam_count > 0,
        "student_outcomes": outcome_snapshot_count > 0 or (student_count > 0 and po_count > 0 and official_exam_count > 0),
        "graduation_snapshots": graduation_snapshot_count > 0,
        "pea": pea_count > 0,
        "program_identity": program_identity,
        "lo_po": lo_count > 0 and po_count > 0 and mapping_count > 0,
        "quality_cycle": quality_cycle_count > 0,
        "graduates": graduate_count > 0,
        "medek_51": bool(check_map.get("5.1a")) and bool(check_map.get("5.1b")),
        "medek_52": bool(check_map.get("5.2")),
        "medek_53": bool(check_map.get("5.3")),
        "program_specific": float(curriculum.get("program_specific_ects") or 0) > 0,
        "curriculum": int(curriculum.get("course_count") or 0) > 0,
        "faculty": faculty_count > 0,
        "infrastructure": infrastructure_count > 0,
        "evidence": evidence_count > 0,
        "mudek_outcomes": mudek_outcomes,
        "medek_outcomes": medek_outcomes,
        "medek_program_specific": medek_program_specific,
        "outcome_components": po_count > 0 and component_count > 0 and po_with_components == po_count,
        "closed_cycle": closed_cycle_count > 0,
        "faculty_cv": faculty_count > 0 and approved_cv_faculty >= faculty_count,
        "institution_profile": institution_profile_signal,
        "school_profile": school_profile_signal,
        "part_time_monitoring": part_time_monitoring_signal,
        "student_graduate_stats": student_count > 0 and (graduate_count > 0 or graduation_snapshot_count > 0),
        "graduation_policy": graduation_policy_signal,
        "optional": True,
    }


def accreditation_evidence_readiness(db: Session, program_id: int, academic_year: str, framework_id: int | None = None) -> dict[str, Any]:
    """Criterion + official subcriterion evidence readiness for accreditation/site visits.

    The engine deliberately distinguishes three things:
    1) automatic institutional signals owned by DOU Assess,
    2) evidence attached to the *exact* subcriterion code,
    3) requirements that still need an authorised human review.

    This remains an internal preparation aid; it never represents an accreditation body's
    official score or decision.
    """
    dashboard = program_dashboard(db, program_id, academic_year, framework_id)
    program = require_program_access(db, program_id, write=False, accreditation=True)
    evidence_rows = list(db.scalars(select(m.QualityEvidenceAsset).where(
        m.QualityEvidenceAsset.program_id == program_id
    ).order_by(m.QualityEvidenceAsset.created_at.desc())).all())
    cycles = list(db.scalars(select(m.QualityCycle).where(
        m.QualityCycle.program_id == program_id,
        m.QualityCycle.academic_year == academic_year,
    )).all())
    decisions = list(db.scalars(select(m.GovernanceDecision).where(
        m.GovernanceDecision.program_id == program_id
    )).all())

    framework = dashboard.get("framework") or {}
    manual_assessments = _manual_assessments(db, program_id, int(framework.get("id") or framework_id or 0), academic_year) if (framework.get("id") or framework_id) else {}
    automation = _subcriterion_automation_context(
        db, program, academic_year, dashboard.get("curriculum") or {}, framework
    )
    framework_criteria = {str(x.get("code") or ""): x for x in (framework.get("criteria") or [])}
    general = [x for x in evidence_rows if not (x.criterion_code or "")]

    matrix: list[dict[str, Any]] = []
    subcriteria_all: list[dict[str, Any]] = []
    for criterion in dashboard.get("criteria", []):
        code = str(criterion.get("code") or "")
        definition = framework_criteria.get(code) or criterion
        # Parent readiness may display all evidence below that branch, while exact
        # subcriterion readiness only accepts an exact code match.
        direct = [x for x in evidence_rows if (x.criterion_code or "") == code]
        branch_evidence = [x for x in evidence_rows if (x.criterion_code or "") == code or (x.criterion_code or "").startswith(code + ".")]
        related_cycles = [x for x in cycles if (x.criterion_code or "") == code or (x.criterion_code or "").startswith(code + ".")]
        related_decisions = [x for x in decisions if (x.related_criterion or "") == code or (x.related_criterion or "").startswith(code + ".")]
        missing_signals = [x.get("label") for x in criterion.get("signals", []) if not x.get("ok")]
        open_cycles = [x for x in related_cycles if x.status not in {"closed", "completed", "act", "acting"}]
        closed_cycles = [x for x in related_cycles if x.status in {"closed", "completed", "act", "acting"}]
        signal_rate = round(sum(1 for x in criterion.get("signals", []) if x.get("ok")) / max(1, len(criterion.get("signals", []))) * 100, 2)
        evidence_score = min(100, len(branch_evidence) * 35 + (15 if general else 0))
        closure_score = 100 if closed_cycles else (50 if related_cycles else 0)
        visit_score = round((float(criterion.get("score") or 0) * 0.45) + (evidence_score * 0.35) + (closure_score * 0.20), 2)

        sub_rows: list[dict[str, Any]] = []
        for sub in definition.get("subcriteria") or []:
            sub_code = str(sub.get("code") or "")
            sub_direct = [x for x in evidence_rows if (x.criterion_code or "") == sub_code]
            parent_only = [x for x in direct if (x.criterion_code or "") == code]
            key = str(sub.get("automation_key") or "manual")
            auto_ok = automation.get(key)
            sub_assessment = manual_assessments.get(sub_code)
            manual_review_completed = bool(
                sub_assessment
                and int(sub_assessment.maturity_level or 0) >= 3
                and sub_assessment.quality_status in {"implemented", "measured", "improved"}
            )
            manual_required = auto_ok is None and not manual_review_completed
            required_evidence = list(sub.get("required_evidence") or [])
            effective_ok = manual_review_completed if auto_ok is None else auto_ok
            if sub_direct and effective_ok is True:
                sub_status = "ready"
            elif sub_direct or effective_ok is True:
                sub_status = "attention"
            else:
                sub_status = "gap"
            missing_evidence = [] if sub_direct else required_evidence
            sub_row = {
                "criterion_code": code,
                "subcriterion_code": sub_code,
                "title": sub.get("title") or sub_code,
                "automation_key": key,
                "auto_ok": auto_ok,
                "manual_review_required": manual_required,
                "manual_review_completed": manual_review_completed,
                "manual_maturity": sub_assessment.maturity_level if sub_assessment else None,
                "manual_status": sub_assessment.quality_status if sub_assessment else None,
                "manual_note": sub_assessment.note if sub_assessment else "",
                "required_evidence": required_evidence,
                "evidence_count": len(sub_direct),
                "parent_evidence_count": len(parent_only),
                "missing_evidence": missing_evidence,
                "status": sub_status,
                "evidence": [
                    {"id": x.id, "name": x.original_name, "category": x.category, "description": x.description,
                     "created_at": x.created_at.isoformat() if x.created_at else None}
                    for x in sub_direct[:8]
                ],
            }
            sub_rows.append(sub_row)
            subcriteria_all.append(sub_row)

        if sub_rows:
            ready_sub = sum(1 for x in sub_rows if x["status"] == "ready")
            attention_sub = sum(1 for x in sub_rows if x["status"] == "attention")
            gap_sub = sum(1 for x in sub_rows if x["status"] == "gap")
            # Official frameworks with subcriteria are primarily judged here by exact
            # requirement coverage; the top-level signal score remains visible as context.
            sub_score = round((ready_sub + attention_sub * 0.5) / len(sub_rows) * 100, 2)
            visit_score = round((visit_score * 0.35) + (sub_score * 0.65), 2)
            status = "ready" if gap_sub == 0 and attention_sub == 0 else ("attention" if ready_sub or attention_sub else "gap")
        else:
            ready_sub = attention_sub = gap_sub = 0
            status = "ready" if visit_score >= 75 and branch_evidence else ("attention" if visit_score >= 45 else "gap")

        matrix.append({
            "criterion_code": code,
            "criterion_name": criterion.get("name") or code,
            "criterion_score": criterion.get("score", 0),
            "signal_rate": signal_rate,
            "evidence_count": len(branch_evidence),
            "direct_parent_evidence_count": len(direct),
            "general_evidence_count": len(general),
            "open_cycle_count": len(open_cycles),
            "closed_cycle_count": len(closed_cycles),
            "decision_count": len(related_decisions),
            "missing_signals": missing_signals,
            "visit_score": visit_score,
            "status": status,
            "subcriteria_total": len(sub_rows),
            "subcriteria_ready": ready_sub,
            "subcriteria_attention": attention_sub,
            "subcriteria_gaps": gap_sub,
            "subcriteria": sub_rows,
            "evidence": [
                {"id": x.id, "name": x.original_name, "category": x.category, "description": x.description,
                 "criterion_code": x.criterion_code,
                 "created_at": x.created_at.isoformat() if x.created_at else None}
                for x in branch_evidence[:12]
            ],
        })

    ready = sum(1 for x in matrix if x["status"] == "ready")
    attention = sum(1 for x in matrix if x["status"] == "attention")
    gaps = sum(1 for x in matrix if x["status"] == "gap")
    total = len(matrix)
    visit_readiness = round(sum(x["visit_score"] for x in matrix) / total, 2) if total else 0.0
    missing_evidence = [x for x in matrix if x["evidence_count"] == 0]
    sub_ready = sum(1 for x in subcriteria_all if x["status"] == "ready")
    sub_attention = sum(1 for x in subcriteria_all if x["status"] == "attention")
    sub_gaps = sum(1 for x in subcriteria_all if x["status"] == "gap")
    sub_manual = sum(1 for x in subcriteria_all if x["manual_review_required"])

    priority_subcriteria = sorted(
        [x for x in subcriteria_all if x["status"] != "ready"],
        key=lambda r: (0 if r["status"] == "gap" else 1, 0 if r["evidence_count"] == 0 else 1, r["subcriterion_code"]),
    )[:12]
    if priority_subcriteria:
        priority_gaps = [{
            "criterion_code": x["criterion_code"],
            "subcriterion_code": x["subcriterion_code"],
            "criterion_name": next((r["criterion_name"] for r in matrix if r["criterion_code"] == x["criterion_code"]), x["criterion_code"]),
            "subcriterion_title": x["title"],
            "status": x["status"],
            "auto_ok": x["auto_ok"],
            "manual_review_required": x["manual_review_required"],
            "needs_evidence": x["evidence_count"] == 0,
            "missing_evidence": x["missing_evidence"],
        } for x in priority_subcriteria]
    else:
        priority_gaps = [{
            "criterion_code": x["criterion_code"],
            "criterion_name": x["criterion_name"],
            "missing_signals": x["missing_signals"],
            "needs_evidence": x["evidence_count"] == 0,
            "visit_score": x["visit_score"],
        } for x in sorted(matrix, key=lambda r: r["visit_score"])[:8]]

    return {
        "program": dashboard["program"],
        "academic_year": academic_year,
        "framework": dashboard["framework"],
        "visit_readiness_percent": visit_readiness,
        "visit_readiness_label": "Ziyarete Hazır" if visit_readiness >= 75 and gaps == 0 and sub_gaps == 0 else ("Kontrol Gerekli" if visit_readiness >= 45 else "Kritik Hazırlık Açığı"),
        "summary": {
            "criteria_total": total,
            "ready": ready,
            "attention": attention,
            "gaps": gaps,
            "missing_evidence": len(missing_evidence),
            "evidence_total": len(evidence_rows),
            "subcriteria_total": len(subcriteria_all),
            "subcriteria_ready": sub_ready,
            "subcriteria_attention": sub_attention,
            "subcriteria_gaps": sub_gaps,
            "subcriteria_manual_review": sub_manual,
        },
        "matrix": matrix,
        "priority_gaps": priority_gaps,
        "automation": automation,
        "disclaimer": "Bu gösterge resmî akreditasyon kararı veya puanı değildir; kurum içi hazırlık, alt ölçüt izleme ve kanıt tamamlama aracıdır.",
    }



def _medek_odr_item_status(
    *, auto_ok: bool | None, exact_evidence_count: int, supporting_evidence_count: int,
    manual_review_completed: bool, optional: bool = False,
) -> str:
    """Internal readiness state, deliberately stricter than a visual checklist.

    A document cannot override an authoritative failed system signal.  Conversely, a
    positive system signal without an ÖDR-row evidence link remains `attention`, so
    the preparation centre never manufactures a false green state.
    """
    if optional and auto_ok is True and exact_evidence_count == 0:
        return "ready"
    if auto_ok is False:
        return "gap"
    if auto_ok is True:
        return "ready" if exact_evidence_count > 0 else "attention"
    if manual_review_completed and exact_evidence_count > 0:
        return "ready"
    if exact_evidence_count > 0 or supporting_evidence_count > 0 or manual_review_completed:
        return "attention"
    return "gap"


def framework_preparation_readiness(
    db: Session,
    program_id: int,
    academic_year: str,
    framework_id: int | None = None,
) -> dict[str, Any]:
    """TURAK/SABAK/EPDAD report-preparation readiness without inventing official scores.

    The registry is intentionally separate from the canonical accreditation criteria.
    It routes exact preparation rows to evidence, authoritative system signals and
    authorised manual review while preserving the source framework/version.
    """
    dashboard = program_dashboard(db, program_id, academic_year, framework_id)
    framework = dashboard.get("framework") or {}
    family = str(framework.get("framework_family") or "").upper()
    catalog = framework_preparation_catalog(family)
    program = require_program_access(db, program_id, write=False, accreditation=True)
    framework_pk = int(framework.get("id") or framework_id or 0)
    if not framework_pk:
        raise ValueError("Program için seçili akreditasyon çerçevesi bulunamadı")

    manual = _manual_assessments(db, program_id, framework_pk, academic_year)
    evidence_rows = list(db.scalars(select(m.QualityEvidenceAsset).where(
        m.QualityEvidenceAsset.program_id == program_id
    ).order_by(m.QualityEvidenceAsset.created_at.desc())).all())
    automation = _subcriterion_automation_context(
        db, program, academic_year, dashboard.get("curriculum") or {}, framework
    )

    rows: list[dict[str, Any]] = []
    for item in catalog["items"]:
        code = str(item["code"])
        mapped = str(item.get("mapped_criterion") or "")
        exact = [x for x in evidence_rows if (x.criterion_code or "").strip().upper() == code.upper()]
        supporting = [x for x in evidence_rows if mapped and (x.criterion_code or "").strip().upper() == mapped.upper()]
        assessment = manual.get(code)
        manual_ok = bool(
            assessment
            and int(assessment.maturity_level or 0) >= 4
            and assessment.quality_status in {"implemented", "measured", "improved", "closed"}
        )
        auto_key = str(item.get("automation_key") or "manual")
        auto_ok = automation.get(auto_key) if auto_key != "manual" else None
        status = _medek_odr_item_status(
            auto_ok=auto_ok if isinstance(auto_ok, bool) else None,
            exact_evidence_count=len(exact),
            supporting_evidence_count=len(supporting),
            manual_review_completed=manual_ok,
            optional=False,
        )
        rows.append({
            **item,
            "auto_ok": auto_ok if isinstance(auto_ok, bool) else None,
            "manual_review_required": auto_key == "manual" or auto_ok is None,
            "manual_review_completed": manual_ok,
            "manual_maturity": assessment.maturity_level if assessment else None,
            "manual_status": assessment.quality_status if assessment else None,
            "manual_note": assessment.note if assessment else "",
            "exact_evidence_count": len(exact),
            "supporting_evidence_count": len(supporting),
            "status": status,
            "evidence": [
                {"id": x.id, "name": x.original_name, "category": x.category, "criterion_code": x.criterion_code}
                for x in exact[:8]
            ],
        })

    ready = sum(1 for x in rows if x["status"] == "ready")
    attention = sum(1 for x in rows if x["status"] == "attention")
    gaps = sum(1 for x in rows if x["status"] == "gap")
    total = len(rows)
    readiness = round((ready + attention * 0.5) / total * 100, 2) if total else 0.0
    by_criterion = []
    criterion_defs = {str(x.get("code") or ""): x for x in framework.get("criteria") or []}
    for criterion_code in sorted({str(x.get("mapped_criterion") or "") for x in rows if x.get("mapped_criterion")}):
        subset = [x for x in rows if str(x.get("mapped_criterion") or "") == criterion_code]
        c_ready = sum(1 for x in subset if x["status"] == "ready")
        c_attention = sum(1 for x in subset if x["status"] == "attention")
        c_gap = sum(1 for x in subset if x["status"] == "gap")
        c_score = round((c_ready + c_attention * 0.5) / len(subset) * 100, 2) if subset else 0.0
        by_criterion.append({
            "criterion_code": criterion_code,
            "criterion_name": (criterion_defs.get(criterion_code) or {}).get("name") or criterion_code,
            "total": len(subset), "ready": c_ready, "attention": c_attention, "gaps": c_gap,
            "readiness_percent": c_score,
        })

    priority = sorted(
        [x for x in rows if x["status"] != "ready"],
        key=lambda x: (0 if x["status"] == "gap" else 1, 0 if x["exact_evidence_count"] == 0 else 1, x["code"]),
    )[:15]
    return {
        "program": dashboard["program"],
        "academic_year": academic_year,
        "framework": framework,
        "family": family,
        "source": catalog["source"],
        "readiness_percent": readiness,
        "readiness_label": "Hazır" if gaps == 0 and attention == 0 else ("Kontrol Gerekli" if ready or attention else "Kritik Hazırlık Açığı"),
        "summary": {
            "total": total, "ready": ready, "attention": attention, "gaps": gaps,
            "exact_evidence_links": sum(x["exact_evidence_count"] for x in rows),
            "manual_review_required": sum(1 for x in rows if x["manual_review_required"]),
        },
        "by_criterion": by_criterion,
        "items": rows,
        "priority_gaps": priority,
        "disclaimer": "Bu matris kurum içi hazırlık ve kanıt yönlendirme aracıdır; ilgili akreditasyon kuruluşunun resmî puanı, uygunluk kararı veya değerlendirme sonucu değildir.",
    }


# ---------------------------------------------------------------------------
# 6.47 MÜDEK EK-1 + BBO/FBO evidence-room precision
# ---------------------------------------------------------------------------

MUDEK_BBO_REQUIREMENTS_V31 = [
    {"code":"BBO.COMMON","title":"Ortak Derslerdeki Farklılıklar","criterion":"GENEL","owner":"Bölüm Başkanlığı","required_evidence":["Ortak olmayan derslere ilişkin ders dosyaları / açıklama"]},
    {"code":"BBO.1.2","title":"Ölçüt 1.2 · Yatay/dikey geçiş, ÇAP/Yandal ve değişim intibak örnekleri","criterion":"1.2","owner":"Program Başkanlığı","required_evidence":["İntibak örnekleri","Varsa kurul/toplantı tutanakları"]},
    {"code":"BBO.2.3","title":"Ölçüt 2.3 · PEA ölçme ve değerlendirme kanıtları","criterion":"2.3","owner":"Program Başkanlığı","required_evidence":["Anketler","Değerlendirme sonuçları","Toplantı tutanakları"]},
    {"code":"BBO.3.2","title":"Ölçüt 3.2 · PÇ sağlanma düzeyi ölçme-değerlendirme sistemi","criterion":"3.2","owner":"Program Ölçme-Değerlendirme Komisyonu","required_evidence":["Ölçme sistemi açıklaması","Öğrenci çalışmaları/notları","Anket/değerlendirme sonuçları","Toplantı tutanakları"]},
]
for _mc in range(1, 12):
    MUDEK_BBO_REQUIREMENTS_V31.append({
        "code":f"BBO.3.3.MC{_mc}","title":f"Ölçüt 3.3 · MÇ-{_mc} kanıtları","criterion":"3.3",
        "owner":"Program Ölçme-Değerlendirme Komisyonu",
        "required_evidence":[f"MÇ-{_mc} bileşen bazlı değerlendirme sonuçları","Ders dosyaları / çözümlü sınav / ödev / proje örnekleri"],
    })
MUDEK_BBO_REQUIREMENTS_V31 += [
    {"code":"BBO.3.3.OTHER","title":"Ölçüt 3.3 · Programın varsa diğer çıktıları","criterion":"3.3","owner":"Program Başkanlığı","optional":True,"required_evidence":["Programa özgü diğer çıktı kanıtları"]},
    {"code":"BBO.4.1","title":"Ölçüt 4.1 · Sürekli iyileştirme sürecinin varlığı ve işletilmesi","criterion":"4.1","owner":"Kalite / Program Komisyonu","required_evidence":["Ölçme sonuçları","Değerlendirme raporları","Toplantı tutanakları"]},
    {"code":"BBO.4.2","title":"Ölçüt 4.2 · Somut verilere dayalı iyileştirme kanıtları","criterion":"4.2","owner":"Kalite / Program Komisyonu","required_evidence":["PUKÖ kayıtları","İyileştirme kararları","Önce/sonra ölçüm sonuçları"]},
    {"code":"BBO.5.5","title":"Ölçüt 5.5 · Ana tasarım deneyimi","criterion":"5.5","owner":"Program Başkanlığı","required_evidence":["Son bir yıla ait tüm bitirme/ana tasarım proje raporları","Proje adları listesi","Standart/kısıt/koşul kanıtları"]},
    {"code":"BBO.6","title":"Ölçüt 6 · Öğretim kadrosu ek belgeleri","criterion":"6","owner":"Bölüm Başkanlığı","optional":True,"required_evidence":["Gerektiğinde ek kadro kanıtları"]},
    {"code":"BBO.7.1","title":"Ölçüt 7.1 · Sınıf, laboratuvar ve teçhizat","criterion":"7.1","owner":"Bölüm Başkanlığı","required_evidence":["Sınıf/laboratuvar/teçhizat fotoğraf veya videoları"]},
    {"code":"BBO.7.2","title":"Ölçüt 7.2 · Ders dışı/sosyal/mesleki altyapı","criterion":"7.2","owner":"Bölüm Başkanlığı","required_evidence":["Program altyapısı fotoğraf veya videoları"]},
    {"code":"BBO.7.3","title":"Ölçüt 7.3 · Bilgisayar ve enformatik altyapısı","criterion":"7.3","owner":"Bölüm Başkanlığı","optional":True,"required_evidence":["Program bilişim altyapısı fotoğraf veya videoları"]},
    {"code":"BBO.7.4","title":"Ölçüt 7.4 · Programa özgü kütüphane olanakları","criterion":"7.4","owner":"Bölüm Başkanlığı","optional":True,"required_evidence":["Program kütüphane olanakları fotoğraf veya videoları"]},
    {"code":"BBO.7.5","title":"Ölçüt 7.5 · İSG, kullanım eğitimi ve erişilebilirlik","criterion":"7.5","owner":"Bölüm Başkanlığı","required_evidence":["Laboratuvar kullanım eğitim kayıtları","İSG önlemleri","Engelli erişimi düzenlemeleri"]},
    {"code":"BBO.8","title":"Ölçüt 8 · Kurum desteği ve parasal kaynaklar ek belgeleri","criterion":"8","owner":"Dekanlık / Program","optional":True,"required_evidence":["Gerektiğinde ek kaynak kanıtları"]},
    {"code":"BBO.9","title":"Ölçüt 9 · Organizasyon ve karar alma ek belgeleri","criterion":"9","owner":"Dekanlık / Bölüm","optional":True,"required_evidence":["Gerektiğinde organizasyon/karar alma kanıtları"]},
    {"code":"BBO.REQUEST","title":"Program değerlendiricisinin talep ettiği ek bilgi ve belgeler","criterion":"REQUEST","owner":"Bölüm Başkanlığı","optional":True,"required_evidence":["Değerlendirici taleplerine yanıt belgeleri"]},
    {"code":"BBO.30DAY","title":"30-gün yanıtı belgeleri","criterion":"30DAY","owner":"Bölüm Başkanlığı","optional":True,"required_evidence":["Form 4/5 sonrası 30-gün yanıtı ve kanıtları"]},
]

MUDEK_FBO_REQUIREMENTS_V21 = [
    {"code":"FBO.LANG.INFO","title":"Ortak Yabancı Dil · Ders bilgileri","owner":"Dekanlık / Yabancı Diller","required_evidence":["İzlenceler","Çözümlü sınav örnekleri","Notlandırma ve ölçme-değerlendirme bilgileri"]},
    {"code":"FBO.LANG.LAB","title":"Ortak Yabancı Dil · Laboratuvarlar","owner":"Dekanlık / Yabancı Diller","required_evidence":["Laboratuvar bilgisi ve görselleri"]},
    {"code":"FBO.LANG.REMOTE","title":"Ortak Yabancı Dil · Uzaktan eğitim süreci","owner":"Dekanlık / Yabancı Diller","optional":True,"required_evidence":["Uzaktan eğitim ve sınav uygulamaları"]},
    {"code":"FBO.PHYS.INFO","title":"Ortak Fizik · Ders bilgileri","owner":"Dekanlık / Fizik","required_evidence":["İzlenceler","Çözümlü sınav örnekleri","Notlandırma ve ölçme-değerlendirme bilgileri"]},
    {"code":"FBO.PHYS.LAB","title":"Ortak Fizik · Laboratuvarlar","owner":"Dekanlık / Fizik","required_evidence":["Laboratuvar bilgisi ve görselleri"]},
    {"code":"FBO.PHYS.EXP","title":"Ortak Fizik · Deney listeleri ve raporları","owner":"Dekanlık / Fizik","required_evidence":["Deney listesi/föyleri","Güncel notlandırılmış laboratuvar raporları"]},
    {"code":"FBO.PHYS.REMOTE","title":"Ortak Fizik · Uzaktan eğitim süreci","owner":"Dekanlık / Fizik","optional":True,"required_evidence":["Uzaktan laboratuvar/eğitim çözümleri"]},
    {"code":"FBO.CHEM.INFO","title":"Ortak Kimya · Ders bilgileri","owner":"Dekanlık / Kimya","required_evidence":["İzlenceler","Çözümlü sınav örnekleri","Notlandırma ve ölçme-değerlendirme bilgileri"]},
    {"code":"FBO.CHEM.LAB","title":"Ortak Kimya · Laboratuvarlar","owner":"Dekanlık / Kimya","required_evidence":["Laboratuvar bilgisi ve görselleri"]},
    {"code":"FBO.CHEM.EXP","title":"Ortak Kimya · Deney listeleri ve raporları","owner":"Dekanlık / Kimya","required_evidence":["Deney listesi/föyleri","Güncel notlandırılmış laboratuvar raporları"]},
    {"code":"FBO.CHEM.REMOTE","title":"Ortak Kimya · Uzaktan eğitim süreci","owner":"Dekanlık / Kimya","optional":True,"required_evidence":["Uzaktan laboratuvar/eğitim çözümleri"]},
    {"code":"FBO.MATH.INFO","title":"Ortak Matematik · Ders bilgileri","owner":"Dekanlık / Matematik","required_evidence":["İzlenceler","Çözümlü sınav örnekleri","Notlandırma ve ölçme-değerlendirme bilgileri"]},
    {"code":"FBO.MATH.REMOTE","title":"Ortak Matematik · Uzaktan eğitim süreci","owner":"Dekanlık / Matematik","optional":True,"required_evidence":["Uzaktan eğitim ve sınav uygulamaları"]},
    {"code":"FBO.IT.INFO","title":"Ortak Bilişim · Ders bilgileri","owner":"Dekanlık / Bilişim","required_evidence":["İzlenceler","Çözümlü sınav örnekleri","Notlandırma ve ölçme-değerlendirme bilgileri"]},
    {"code":"FBO.IT.LAB","title":"Ortak Bilişim · Laboratuvarlar","owner":"Dekanlık / Bilişim","required_evidence":["Bilişim laboratuvarı bilgisi ve görselleri"]},
    {"code":"FBO.IT.REMOTE","title":"Ortak Bilişim · Uzaktan eğitim süreci","owner":"Dekanlık / Bilişim","optional":True,"required_evidence":["Uzaktan bilişim eğitimi/sınav çözümleri"]},
    {"code":"FBO.SOCIAL","title":"Ortak sosyal alanlar","owner":"Dekanlık","required_evidence":["Sosyal alanlar/kulüpler/çalışma alanları/ulaşım/yurt bilgileri ve görseller"]},
    {"code":"FBO.SPORT","title":"Ortak spor alanları","owner":"Dekanlık","required_evidence":["Spor olanakları bilgisi ve görseller"]},
    {"code":"FBO.ACCESS.FAC","title":"Erişilebilirlik · Fakülte içi önlemler","owner":"Dekanlık","required_evidence":["Erişilebilirlik önlemleri ve görseller"]},
    {"code":"FBO.ACCESS.UNI","title":"Erişilebilirlik · Üniversite içi önlemler","owner":"Rektörlük / İdari Birimler","required_evidence":["Üniversite erişilebilirlik önlemleri ve görseller"]},
    {"code":"FBO.SAFETY.FAC","title":"Güvenlik · Fakülte içi önlemler","owner":"Dekanlık","required_evidence":["Derslik/laboratuvar/ortak alan güvenlik önlemleri ve görseller"]},
    {"code":"FBO.SAFETY.UNI","title":"Güvenlik · Üniversite içi önlemler","owner":"Rektörlük / İdari Birimler","required_evidence":["Üniversite güvenlik önlemleri ve görseller"]},
    {"code":"FBO.LIB.INFO","title":"Üniversite kütüphane yeterlik ve kullanım bilgileri","owner":"Kütüphane","required_evidence":["Koleksiyonlar/periyodik yayınlar/online erişim/çalışma olanakları/açılış saatleri ve görseller"]},
    {"code":"FBO.LIB.REMOTE","title":"Kütüphane · Uzaktan erişim süreci","owner":"Kütüphane","optional":True,"required_evidence":["Uzaktan erişim olanakları ve kullanım istatistikleri"]},
    {"code":"FBO.ITINFRA.INFO","title":"Üniversite bilişim yeterlik ve kullanım bilgileri","owner":"Bilgi İşlem","required_evidence":["Yazılım/internet/eğitim bilişim olanakları ve görseller"]},
    {"code":"FBO.ITINFRA.REMOTE","title":"Bilişim · Uzaktan eğitim süreci","owner":"Bilgi İşlem","optional":True,"required_evidence":["Uzaktan eğitim bilişim olanakları ve kullanım istatistikleri"]},
    {"code":"FBO.HEALTH","title":"Üniversite sağlık olanakları","owner":"SKS / Sağlık Birimi","required_evidence":["Sağlık olanakları bilgisi ve görseller"]},
    {"code":"FBO.QUALITY","title":"Dekanlığın koordine ettiği kalite sistemi","owner":"Dekanlık / Kalite","required_evidence":["Fakülte toplantı kararları","Akreditasyon/kalite komitesi çalışmaları"]},
    {"code":"FBO.OTHER","title":"Fakülte/kurum ile ilgili diğer yararlı belgeler","owner":"Dekanlık","optional":True,"required_evidence":["Diğer destekleyici belgeler"]},
    {"code":"FBO.REQUEST","title":"Takım Başkanı tarafından istenen ek bilgi ve belgeler","owner":"Dekanlık","optional":True,"required_evidence":["Takım Başkanı taleplerine yanıt belgeleri"]},
]

MUDEK_EK1_PROFILES_V31 = [
    {
        "code":"CS-SW-AI","title":"Bilgisayar, Yazılım ve Benzeri Mühendislik Programları",
        "keywords":["bilgisayar","yazılım","yapay zeka","yapay zekâ","software","computer","artificial intelligence"],
        "topics":[
            {"code":"EK1-CS-01","title":"İleri matematik, olasılık-istatistik ve deneysel fizik","keywords":["ayrık matematik","doğrusal cebir","diferansiyel","türevsel denkle","olasılık","istatistik","fizik"]},
            {"code":"EK1-CS-02","title":"Algoritma analizi, yazılım süreçleri, karmaşık veri yapıları, veri saklama ve karmaşık sistem analizi/tasarımı","keywords":["algoritma","veri yapıları","veri yapısı","veritaban","veri taban","bellek","yazılım geliştirme","bilgisayar mimarisi","donanım","sistem tasarımı"]},
            {"code":"EK1-CS-COMP-01","title":"Bilgisayar adlı programlar için laboratuvar destekli sayısal sistem tasarımı","keywords":["sayısal sistem","dijital sistem","sayısal tasarım","dijital tasarım","lojik tasarım"],"program_keywords":["bilgisayar","computer"]},
            {"code":"EK1-CS-SW-01","title":"Yazılım adlı programlar için gereksinim mühendisliği","keywords":["gereksinim mühendis","gereksinim analizi","gereksinim yönetimi","requirements"],"program_keywords":["yazılım","software"]},
            {"code":"EK1-CS-SW-02","title":"Yazılım adlı programlar için yazılım mimarisi","keywords":["yazılım mimar","software architecture"],"program_keywords":["yazılım","software"]},
            {"code":"EK1-CS-SW-03","title":"Yazılım adlı programlar için kalite güvencesi, doğrulama, sınama ve yönetim","keywords":["yazılım kalite","kalite güvencesi","yazılım test","doğrulama","sınama","software quality","software testing"],"program_keywords":["yazılım","software"]},
            {"code":"EK1-CS-AI-01","title":"Yapay zekâ adlı programlar için yapay zekâ kuramsal temelleri","keywords":["yapay zeka","yapay zekâ","makine öğrenmesi","machine learning","artificial intelligence"],"program_keywords":["yapay zeka","yapay zekâ","artificial intelligence","veri bilimi"]},
            {"code":"EK1-CS-AI-02","title":"Yapay zekâ adlı programlar için veri bilimi, büyük veri analitiği ve veri madenciliği","keywords":["veri bilimi","büyük veri","veri madenciliği","data science","big data","data mining"],"program_keywords":["yapay zeka","yapay zekâ","artificial intelligence","veri bilimi"]},
            {"code":"EK1-CS-AI-03","title":"Yapay zekâ adlı programlar için doğal dil işleme, pekiştirmeli öğrenme ve derin öğrenme","keywords":["doğal dil","pekiştirmeli","derin öğrenme","nlp","reinforcement","deep learning"],"program_keywords":["yapay zeka","yapay zekâ","artificial intelligence","veri bilimi"]},
            {"code":"EK1-CS-AI-04","title":"Yapay zekâ adlı programlar için bilgisayarlı görü ve öneri sistemleri","keywords":["bilgisayarlı görü","bilgisayar görüsü","öneri sistem","computer vision","recommender"],"program_keywords":["yapay zeka","yapay zekâ","artificial intelligence","veri bilimi"]},
            {"code":"EK1-CS-AI-05","title":"Yapay zekâ adlı programlar için yapay zekâ yönetişimi","keywords":["yapay zeka etiği","yapay zekâ etiği","yapay zeka yönetişim","ai governance","responsible ai"],"program_keywords":["yapay zeka","yapay zekâ","artificial intelligence","veri bilimi"]},
        ],
    },
    {
        "code":"EEE","title":"Elektrik, Elektronik ve Benzeri Mühendislik Programları",
        "keywords":["elektrik","elektronik","haberleşme","telekomünikasyon","kontrol","electrical","electronics","telecommunication","control"],
        "topics":[
            {"code":"EK1-EE-01","title":"İleri matematik, olasılık-istatistik, ayrık matematik, kompleks değişkenler; mekanik ve elektrik fiziği","keywords":["doğrusal cebir","diferansiyel","olasılık","istatistik","ayrık matematik","kompleks","mekanik","elektrik fiziği"]},
            {"code":"EK1-EE-02","title":"Elektrik devreleri, elektromanyetik kuram ve ayrık-zaman işaretleri","keywords":["elektrik devre","devre analizi","elektromanyetik","ayrık zaman","işaretler ve sistemler","sinyaller ve sistemler"]},
            {"code":"EK1-EE-EL-01","title":"Elektrik adlı programlar için elektrik ve elektromekanik enerji dönüşümü","keywords":["enerji dönüşüm","elektromekanik"],"program_keywords":["elektrik","electrical"]},
            {"code":"EK1-EE-EC-01","title":"Elektronik adlı programlar için sayısal elektronik","keywords":["sayısal elektronik","dijital elektronik"],"program_keywords":["elektronik","electronics"]},
            {"code":"EK1-EE-COM-01","title":"Haberleşme/telekomünikasyon programları için sayısal haberleşme","keywords":["sayısal haberleşme","dijital haberleşme","digital communication"],"program_keywords":["haberleşme","telekomünikasyon","communication","telecommunication"]},
            {"code":"EK1-EE-CTRL-01","title":"Kontrol adlı programlar için sayısal kontrol ve kontrol sistem tasarımı","keywords":["sayısal kontrol","dijital kontrol","kontrol sistem tasar"],"program_keywords":["kontrol","control"]},
        ],
    },
    {
        "code":"IE","title":"Endüstri ve Benzeri Mühendislik Programları",
        "keywords":["endüstri","endustri","industrial"],
        "topics":[
            {"code":"EK1-IE-01","title":"İleri matematik, olasılık-istatistik ve deneysel fizik","keywords":["doğrusal cebir","diferansiyel","olasılık","istatistik","fizik"]},
            {"code":"EK1-IE-02","title":"Bütünleşmiş sistemlerin tasarlanması, geliştirilmesi, uygulanması ve iyileştirilmesi","keywords":["sistem tasar","bütünleşik sistem","entegre sistem","sistem geliştirme","sistem iyileştirme"]},
            {"code":"EK1-IE-03","title":"Sistem entegrasyonu için analitik, deneysel ve hesaplama yöntemleri","keywords":["sistem entegr","analitik yöntem","deneysel yöntem","hesaplama yöntem","optimizasyon"]},
            {"code":"EK1-IE-04","title":"Yöneylem araştırması, mühendislik ekonomisi, benzetim ve üretim/operasyon yönetimi","keywords":["yöneylem","mühendislik ekonomisi","benzetim","simülasyon","üretim yönetimi","operasyon yönetimi"]},
        ],
    },
]


def mudek_ek1_valid_codes() -> set[str]:
    """Internal evidence/review codes for MÜDEK EK-1 topics.

    These codes are not additional MÜDEK criteria. They are child tracking codes
    anchored to Criterion 5.1 so evidence and manual review can be version-scoped
    without inventing a fictional Criterion 10.
    """
    return {str(topic["code"]) for profile in MUDEK_EK1_PROFILES_V31 for topic in profile.get("topics", [])}


def _mudek_norm(text: str | None) -> str:
    table = str.maketrans("ÇĞİÖŞÜÂÎÛçğıöşüâîû", "CGIOSUAIUcgiösuaiu")
    return (text or "").translate(table).casefold()


def mudek_ek1_profile(db: Session, program_id: int, academic_year: str, framework_id: int | None = None) -> dict[str, Any]:
    program = db.get(m.Program, program_id)
    if not program:
        raise ValueError("Program bulunamadı")
    framework = db.get(m.QualityFrameworkProfile, framework_id) if framework_id else None
    if framework and framework.framework_family != "MÜDEK":
        raise ValueError("EK-1 profili yalnız MÜDEK framework'ü için kullanılabilir")
    if framework and framework.version not in {"3.0", "3.1"}:
        return {"program":model_dict(program),"academic_year":academic_year,"framework":model_dict(framework),"matched":False,"manual_review_required":True,"reason":"EK-1 eğitim planı konu motoru MÜDEK 3.0/3.1 için tanımlıdır.","topics":[],"summary":{"total":0,"review":0,"gap":0}}
    haystack = _mudek_norm(" ".join([program.name, program.department, program.faculty]))
    profile = next((x for x in MUDEK_EK1_PROFILES_V31 if any(_mudek_norm(k) in haystack for k in x["keywords"])), None)
    if not profile:
        return {"program":model_dict(program),"academic_year":academic_year,"framework":model_dict(framework) if framework else None,"matched":False,"manual_review_required":True,"reason":"Program adı mevcut otomatik EK-1 katalog profilleriyle güvenli biçimde eşleşmedi; disiplin profili kalite yöneticisi tarafından doğrulanmalıdır.","topics":[],"summary":{"total":0,"review":0,"gap":0}}
    curriculum = list(db.scalars(select(m.CurriculumItem).where(m.CurriculumItem.program_id==program_id,m.CurriculumItem.academic_year==academic_year).order_by(m.CurriculumItem.course_code)).all())
    assessment_query = select(m.QualityCriterionAssessment).where(
        m.QualityCriterionAssessment.program_id == program_id,
        m.QualityCriterionAssessment.academic_year == academic_year,
    )
    if framework:
        assessment_query = assessment_query.where(m.QualityCriterionAssessment.framework_profile_id == framework.id)
    assessments = {x.criterion_code:x for x in db.scalars(assessment_query).all()}
    evidence = list(db.scalars(select(m.QualityEvidenceAsset).where(m.QualityEvidenceAsset.program_id==program_id)).all())
    rows=[]
    for topic in profile["topics"]:
        pks=[_mudek_norm(x) for x in topic.get("program_keywords",[])]
        applicable = not pks or any(k in haystack for k in pks)
        if not applicable:
            continue
        matches=[]
        for item in curriculum:
            course_text=_mudek_norm(" ".join([item.course_code,item.course_name,item.course_category,item.notes or ""]))
            if any(_mudek_norm(k) in course_text for k in topic.get("keywords",[])):
                matches.append({"course_code":item.course_code,"course_name":item.course_name,"ects":item.ects,"term":item.term})
        direct=[x for x in evidence if (x.criterion_code or "").strip().upper()==topic["code"].upper()]
        assessment=assessments.get(topic["code"])
        manual_ok=bool(assessment and assessment.maturity_level>=4 and assessment.quality_status in {"implemented","measured","improved","closed"})
        if direct and matches and manual_ok:
            status="ready"
        elif direct or matches or assessment:
            status="review"
        else:
            status="gap"
        rows.append({**topic,"matched_courses":matches,"matched_course_count":len(matches),"evidence_count":len(direct),"manual_review_completed":manual_ok,"manual_maturity":assessment.maturity_level if assessment else None,"manual_note":assessment.note if assessment else "","status":status,"criterion_anchor":"5.1","is_program_outcome":False})
    return {"program":model_dict(program),"academic_year":academic_year,"framework":model_dict(framework) if framework else None,"matched":True,"profile_code":profile["code"],"profile_title":profile["title"],"manual_review_required":True,"note":"EK-1 konuları Program Çıktısı değildir; Ölçüt 5.1 kapsamında eğitim planında kapsanması gereken disipline özgü konulardır.","topics":rows,"summary":{"total":len(rows),"ready":sum(1 for x in rows if x["status"]=="ready"),"review":sum(1 for x in rows if x["status"]=="review"),"gap":sum(1 for x in rows if x["status"]=="gap")}}


def _mudek_room_auto_signal(db: Session, program_id: int, academic_year: str, code: str) -> bool:
    course_ids=list(db.scalars(select(m.Course.id).where(m.Course.program_id==program_id,m.Course.academic_year==academic_year)).all())
    code=code.upper()
    if code.startswith("BBO.3.3.MC"):
        try: n=int(code.rsplit("MC",1)[1])
        except Exception: n=0
        if n:
            mapped=list(db.scalars(
                select(m.ProgramOutcomeComponent)
                .join(m.ProgramOutcome, m.ProgramOutcome.id == m.ProgramOutcomeComponent.program_outcome_id)
                .where(
                    m.ProgramOutcome.program_id == program_id,
                    m.ProgramOutcomeComponent.framework_family == "MÜDEK",
                    m.ProgramOutcomeComponent.framework_version.in_(["3.0", "3.1"]),
                )
            ).all())
            return any(
                (x.framework_component_code or x.code or "").upper().startswith(f"MÇ-{n}")
                or (x.framework_component_code or x.code or "").upper().startswith(f"MC-{n}")
                for x in mapped
            )
    if code=="BBO.3.2":
        return bool(course_ids and _count(db,m.Exam,m.Exam.course_id.in_(course_ids),m.Exam.status.in_(["approved","archived"]))>0)
    if code in {"BBO.4.1","BBO.4.2"}:
        return _count(db,m.QualityCycle,m.QualityCycle.program_id==program_id,m.QualityCycle.academic_year==academic_year)>0
    if code=="BBO.5.5":
        items=list(db.scalars(select(m.CurriculumItem).where(m.CurriculumItem.program_id==program_id,m.CurriculumItem.academic_year==academic_year)).all())
        return any(any(k in _mudek_norm((x.course_name or "")+" "+(x.notes or "")) for k in ["bitirme","tasarim","proje","capstone"]) for x in items)
    if code.startswith("BBO.7."):
        return _count(db,m.InfrastructureRecord,m.InfrastructureRecord.program_id==program_id)>0
    if code=="BBO.2.3":
        return _count(db,m.StakeholderRecord,m.StakeholderRecord.program_id==program_id)>0 and _count(db,m.GovernanceDecision,m.GovernanceDecision.program_id==program_id)>0
    if code=="BBO.1.2":
        return _count(db,m.Student,m.Student.program_id==program_id)>0
    if code=="FBO.QUALITY":
        return _count(db,m.GovernanceDecision,m.GovernanceDecision.program_id==program_id)>0
    if code.startswith("FBO.ACCESS") or code.startswith("FBO.SAFETY") or code.startswith("FBO.ITINFRA"):
        return _count(db,m.InfrastructureRecord,m.InfrastructureRecord.program_id==program_id)>0
    return False


def mudek_evidence_room_readiness(db: Session, program_id: int, academic_year: str, room_type: str="BBO", framework_id: int | None=None, application_id: int | None=None) -> dict[str, Any]:
    program=db.get(m.Program,program_id)
    if not program: raise ValueError("Program bulunamadı")
    room=room_type.upper()
    if room not in {"BBO","FBO"}: raise ValueError("room_type BBO veya FBO olmalıdır")
    framework=db.get(m.QualityFrameworkProfile,framework_id) if framework_id else None
    if framework and framework.framework_family!="MÜDEK": raise ValueError("BBO/FBO hazırlığı yalnız MÜDEK framework'ü ile kullanılabilir")
    application=db.get(m.AccreditationApplication,application_id) if application_id else None
    if application and (application.program_id!=program_id): raise ValueError("Başvuru bu programa ait değil")
    requirements=MUDEK_BBO_REQUIREMENTS_V31 if room=="BBO" else MUDEK_FBO_REQUIREMENTS_V21
    evidence_scope={"type":"program","program_ids":[program_id],"label":program.name}
    if room=="FBO" and (program.faculty or "").strip():
        faculty_program_ids=list(db.scalars(select(m.Program.id).where(m.Program.faculty==program.faculty)).all())
        faculty_program_ids=faculty_program_ids or [program_id]
        evidence=list(db.scalars(
            select(m.QualityEvidenceAsset).where(
                m.QualityEvidenceAsset.program_id.in_(faculty_program_ids),
                m.QualityEvidenceAsset.criterion_code.like("FBO.%"),
            ).order_by(m.QualityEvidenceAsset.created_at.desc())
        ).all())
        evidence_scope={"type":"faculty","faculty":program.faculty,"program_ids":faculty_program_ids,"label":program.faculty}
    else:
        evidence=list(db.scalars(select(m.QualityEvidenceAsset).where(m.QualityEvidenceAsset.program_id==program_id).order_by(m.QualityEvidenceAsset.created_at.desc())).all())
    assessment_query = select(m.QualityCriterionAssessment).where(
        m.QualityCriterionAssessment.program_id == program_id,
        m.QualityCriterionAssessment.academic_year == academic_year,
    )
    if framework:
        assessment_query = assessment_query.where(m.QualityCriterionAssessment.framework_profile_id == framework.id)
    assessments={x.criterion_code:x for x in db.scalars(assessment_query).all()}
    rows=[]
    for req in requirements:
        code=req["code"]
        exact=[x for x in evidence if (x.criterion_code or "").strip().upper()==code.upper()]
        # Criterion-level evidence is context only; it must not make a room requirement green.
        parent_code=req.get("criterion") or ""
        parent=[x for x in evidence if parent_code and (x.criterion_code or "").strip().upper()==parent_code.upper()]
        assessment=assessments.get(code)
        manual_ok=bool(assessment and assessment.maturity_level>=4 and assessment.quality_status in {"implemented","measured","improved","closed"})
        auto_ok=_mudek_room_auto_signal(db,program_id,academic_year,code)
        optional=bool(req.get("optional"))
        if exact and (manual_ok or not req.get("manual_required",False)):
            status="ready"
        elif exact or parent or auto_ok or assessment:
            status="review"
        else:
            status="optional" if optional else "gap"
        rows.append({**req,"room_type":room,"exact_evidence_count":len(exact),"support_evidence_count":len(parent),"auto_signal":auto_ok,"manual_review_completed":manual_ok,"manual_maturity":assessment.maturity_level if assessment else None,"manual_note":assessment.note if assessment else "","status":status,"evidence":[{"id":x.id,"program_id":x.program_id,"name":x.original_name,"category":x.category,"sha256":x.sha256} for x in exact[:10]]})
    mandatory=[x for x in rows if not x.get("optional")]
    ready=sum(1 for x in mandatory if x["status"]=="ready")
    review=sum(1 for x in mandatory if x["status"]=="review")
    gap=sum(1 for x in mandatory if x["status"]=="gap")
    score=round((ready+review*0.5)/len(mandatory)*100,2) if mandatory else 0.0
    return {"program":model_dict(program),"academic_year":academic_year,"room_type":room,"framework":model_dict(framework) if framework else None,"application":model_dict(application) if application else None,"evidence_scope":evidence_scope,"source":{"title":"MÜDEK Sanal Belge Odaları Hazırlama Yönergesi","version":"2.1","published":"2026-03-04","criteria_version":framework.version if framework else None},"readiness_percent":score,"readiness_label":"Hazır" if gap==0 and review==0 else ("Kontrol Gerekli" if ready or review else "Kritik Eksik"),"summary":{"mandatory_total":len(mandatory),"ready":ready,"review":review,"gap":gap,"optional":sum(1 for x in rows if x.get("optional"))},"items":rows}

def medek_odr_readiness(
    db: Session,
    program_id: int,
    academic_year: str,
    framework_id: int | None = None,
    application_type: str = "general",
) -> dict[str, Any]:
    """MEDEK v1.1 ÖDR preparation/evidence matrix.

    This is an institutional pre-check and evidence routing surface.  It does not
    reproduce an accreditation decision, nor does it convert MEDEK's narrative ÖDR
    prompts into an official numeric score.
    """
    application_type = (application_type or "general").strip().casefold()
    if application_type not in {"general", "interim"}:
        raise ValueError("application_type general veya interim olmalıdır")

    dashboard = program_dashboard(db, program_id, academic_year, framework_id)
    framework = dashboard.get("framework") or {}
    if str(framework.get("framework_family") or "").upper() != "MEDEK" or str(framework.get("version") or "") != "v1.1":
        raise ValueError("MEDEK ÖDR v1.1 hazırlık merkezi yalnız MEDEK v1.1 çerçevesiyle kullanılabilir")

    program = require_program_access(db, program_id, write=False, accreditation=True)
    framework_pk = int(framework.get("id") or framework_id or 0)
    manual = _manual_assessments(db, program_id, framework_pk, academic_year) if framework_pk else {}
    evidence_rows = list(db.scalars(select(m.QualityEvidenceAsset).where(
        m.QualityEvidenceAsset.program_id == program_id
    ).order_by(m.QualityEvidenceAsset.created_at.desc())).all())
    automation = _subcriterion_automation_context(db, program, academic_year, dashboard.get("curriculum") or {}, framework)

    def evidence_payload(rows: list[m.QualityEvidenceAsset], limit: int = 6) -> list[dict[str, Any]]:
        return [{
            "id": x.id, "name": x.original_name, "category": x.category,
            "description": x.description, "criterion_code": x.criterion_code,
            "created_at": x.created_at.isoformat() if x.created_at else None,
        } for x in rows[:limit]]

    item_rows: list[dict[str, Any]] = []
    for item in MEDEK_ODR_V11_ITEMS:
        code = str(item["code"])
        mapped = str(item.get("mapped_subcriterion") or "")
        exact = [x for x in evidence_rows if (x.criterion_code or "") == code]
        supporting = [x for x in evidence_rows if mapped and mapped != code and (x.criterion_code or "") == mapped]
        assessment = manual.get(code)
        manual_review_completed = bool(
            assessment and int(assessment.maturity_level or 0) >= 3
            and assessment.quality_status in {"implemented", "measured", "improved"}
        )
        key = str(item.get("automation_key") or "manual")
        auto_ok = automation.get(key)
        status = _medek_odr_item_status(
            auto_ok=auto_ok, exact_evidence_count=len(exact), supporting_evidence_count=len(supporting),
            manual_review_completed=manual_review_completed,
        )
        item_rows.append({
            **item,
            "section": "B",
            "scope": "mandatory" if application_type == "general" else "conditional",
            "auto_ok": auto_ok,
            "manual_review_required": auto_ok is None and not manual_review_completed,
            "manual_review_completed": manual_review_completed,
            "manual_maturity": assessment.maturity_level if assessment else None,
            "manual_status": assessment.quality_status if assessment else None,
            "manual_note": assessment.note if assessment else "",
            "exact_evidence_count": len(exact),
            "supporting_evidence_count": len(supporting),
            "exact_evidence": evidence_payload(exact),
            "supporting_evidence": evidence_payload(supporting),
            "status": status,
            "next_action": (
                "Sistem koşulunu düzelt" if auto_ok is False else
                "ÖDR maddesine doğrudan kanıt ilişkilendir" if auto_ok is True and not exact else
                "Yetkili olgunluk incelemesini tamamla" if auto_ok is None and not manual_review_completed else
                "Kanıtı bu ÖDR maddesine yeniden ilişkilendir" if not exact and supporting else
                "Hazır"
            ),
        })

    appendix_rows: list[dict[str, Any]] = []
    for item in MEDEK_ODR_V11_APPENDICES:
        code = str(item["code"])
        exact = [x for x in evidence_rows if (x.criterion_code or "") == code]
        assessment = manual.get(code)
        manual_review_completed = bool(
            assessment and int(assessment.maturity_level or 0) >= 3
            and assessment.quality_status in {"implemented", "measured", "improved"}
        )
        key = str(item.get("automation_key") or "manual")
        auto_ok = automation.get(key)
        is_optional = key == "optional"
        status = _medek_odr_item_status(
            auto_ok=auto_ok, exact_evidence_count=len(exact), supporting_evidence_count=0,
            manual_review_completed=manual_review_completed, optional=is_optional,
        )
        appendix_rows.append({
            **item,
            "scope": "optional" if is_optional else ("mandatory" if application_type == "general" else "conditional"),
            "auto_ok": auto_ok,
            "manual_review_required": auto_ok is None and not manual_review_completed,
            "manual_review_completed": manual_review_completed,
            "manual_maturity": assessment.maturity_level if assessment else None,
            "manual_status": assessment.quality_status if assessment else None,
            "manual_note": assessment.note if assessment else "",
            "exact_evidence_count": len(exact),
            "exact_evidence": evidence_payload(exact),
            "status": status,
            "next_action": (
                "İsteğe bağlı" if is_optional else
                "Sistem kaydını tamamla" if auto_ok is False else
                "Ek maddesine doğrudan kanıt ilişkilendir" if auto_ok is True and not exact else
                "Yetkili incelemeyi tamamla" if auto_ok is None and not manual_review_completed else
                "Hazır"
            ),
        })

    general_section = [
        {"code": "A.1", "title": "Program kimliği ve temel bilgiler", "scope": "mandatory",
         "status": "ready" if automation.get("program_identity") is True else "gap",
         "next_action": "Hazır" if automation.get("program_identity") is True else "Program kodu/adı/birim bilgilerini tamamla"},
        {"code": "A.2", "title": "Programın kısa tarihçesi ve önemli değişiklikler", "scope": "mandatory",
         "status": "attention", "next_action": "Yetkili program tarihçesi anlatımını doğrula"},
        {"code": "A.3", "title": "Önceki değerlendirme bulguları ve yapılan iyileştirmeler", "scope": "mandatory" if application_type == "interim" else "conditional",
         "status": "attention", "next_action": "Varsa önceki değerlendirme bulgularını ve kapatma kanıtlarını ilişkilendir"},
    ]

    groups: list[dict[str, Any]] = []
    framework_names = {str(x.get("code")): str(x.get("name") or x.get("code")) for x in framework.get("criteria") or []}
    for criterion_code in [str(i) for i in range(1, 10)]:
        rows = [x for x in item_rows if str(x.get("code", "")).split(".", 1)[0] == criterion_code]
        groups.append({
            "criterion_code": criterion_code,
            "criterion_name": framework_names.get(criterion_code, criterion_code),
            "total": len(rows),
            "ready": sum(1 for x in rows if x["status"] == "ready"),
            "attention": sum(1 for x in rows if x["status"] == "attention"),
            "gaps": sum(1 for x in rows if x["status"] == "gap"),
            "items": rows,
        })

    scored = [x for x in item_rows if x["scope"] == "mandatory"] + [x for x in appendix_rows if x["scope"] == "mandatory"]
    ready_weight = sum(1.0 if x["status"] == "ready" else 0.5 if x["status"] == "attention" else 0.0 for x in scored)
    completion = round(ready_weight / len(scored) * 100, 2) if scored else 0.0
    priority = [x for x in item_rows + appendix_rows if x["status"] != "ready"]
    priority.sort(key=lambda x: (0 if x["status"] == "gap" else 1, x["code"]))

    return {
        "program": dashboard["program"],
        "academic_year": academic_year,
        "framework": framework,
        "application_type": application_type,
        "source": dict(MEDEK_ODR_V11_SOURCE),
        "general_section": general_section,
        "summary": {
            "official_prompt_count": len(MEDEK_ODR_V11_ITEMS),
            "prompt_ready": sum(1 for x in item_rows if x["status"] == "ready"),
            "prompt_attention": sum(1 for x in item_rows if x["status"] == "attention"),
            "prompt_gaps": sum(1 for x in item_rows if x["status"] == "gap"),
            "appendix_total": len(appendix_rows),
            "appendix_ready": sum(1 for x in appendix_rows if x["status"] == "ready"),
            "mandatory_prompt_count": sum(1 for x in item_rows if x["scope"] == "mandatory"),
            "conditional_prompt_count": sum(1 for x in item_rows if x["scope"] == "conditional"),
            "internal_completion_percent": completion,
        },
        "groups": groups,
        "items": item_rows,
        "appendices": appendix_rows,
        "priority_gaps": priority[:15],
        "scope_note": (
            "Genel değerlendirmede ÖDR ana bölümündeki tüm başlıklar izlenir."
            if application_type == "general" else
            "Ara değerlendirmede genel program bilgileri tam tutulur; diğer ÖDR alanlarının kapsamı önceki yetersizlik/gözlemlere göre belirlenir. Önceki bulgu kapsamı sisteme aktarılmadan koşullu maddeler zorunlu kabul edilmez."
        ),
        "disclaimer": "Bu çıktı MEDEK'in resmî puanı/kararı değildir. DOU Assess içinde ÖDR hazırlığı, kanıt yönlendirme ve kurum içi ön kontrol amacıyla üretilir.",
    }


def build_medek_odr_docx(
    db: Session, program_id: int, academic_year: str, framework_id: int | None = None,
    application_type: str = "general",
) -> tuple[bytes, str]:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    report = medek_odr_readiness(db, program_id, academic_year, framework_id, application_type)
    program = report["program"]
    doc = Document()
    doc.styles["Normal"].font.name = "Aptos"
    doc.styles["Normal"].font.size = Pt(9.5)
    title = doc.add_paragraph(); title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("DOĞUŞ ÜNİVERSİTESİ\nMEDEK ÖDR v1.1 HAZIRLIK / KANIT MATRİSİ")
    r.bold = True; r.font.size = Pt(17)
    sub = doc.add_paragraph(); sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.add_run(f"{program['code']} · {program['name']}\n{academic_year} · {report['application_type'].upper()}")
    doc.add_paragraph(report["disclaimer"])
    doc.add_paragraph(report["scope_note"])

    doc.add_heading("1. Kurum İçi Ön Kontrol Özeti", level=1)
    s = report["summary"]
    t = doc.add_table(rows=1, cols=5); t.style = "Table Grid"
    for i, h in enumerate(["ÖDR satırı", "Hazır", "Kontrol", "Eksik", "İç tamamlanma"]): t.rows[0].cells[i].text = h
    c = t.add_row().cells
    for i, v in enumerate([s["official_prompt_count"], s["prompt_ready"], s["prompt_attention"], s["prompt_gaps"], f"%{s['internal_completion_percent']}"]): c[i].text = str(v)

    doc.add_heading("2. Bölüm A · Genel Program Bilgileri", level=1)
    for x in report["general_section"]:
        doc.add_paragraph(f"{x['code']} · {x['title']} — {x['status'].upper()} · {x['next_action']}", style="List Bullet")

    doc.add_heading("3. Bölüm B · Ölçüt Bazlı ÖDR Hazırlığı", level=1)
    for group in report["groups"]:
        doc.add_heading(f"Ölçüt {group['criterion_code']} · {group['criterion_name']}", level=2)
        table = doc.add_table(rows=1, cols=5); table.style = "Table Grid"
        for i, h in enumerate(["Kod", "İstenen açıklama", "Durum", "Kanıt", "Sorumlu"]): table.rows[0].cells[i].text = h
        for x in group["items"]:
            cells = table.add_row().cells
            cells[0].text = x["code"]
            cells[1].text = x["title"]
            cells[2].text = x["status"].upper()
            cells[3].text = f"Doğrudan: {x['exact_evidence_count']} / Destek: {x['supporting_evidence_count']}"
            cells[4].text = x["owner_role"]

    doc.add_heading("4. Ek I ve Ek II Hazırlık Kontrolü", level=1)
    t = doc.add_table(rows=1, cols=5); t.style = "Table Grid"
    for i, h in enumerate(["Kod", "Başlık", "Durum", "Kanıt", "Sorumlu"]): t.rows[0].cells[i].text = h
    for x in report["appendices"]:
        cells = t.add_row().cells
        cells[0].text = x["code"]; cells[1].text = x["title"]; cells[2].text = x["status"].upper()
        cells[3].text = str(x["exact_evidence_count"]); cells[4].text = x["owner_role"]

    doc.add_heading("5. Öncelikli Açıklar", level=1)
    if report["priority_gaps"]:
        for x in report["priority_gaps"]:
            doc.add_paragraph(f"{x['code']} · {x['title']} — {x['status'].upper()}: {x['next_action']}", style="List Bullet")
    else:
        doc.add_paragraph("Öncelikli açık bulunmadı; insan onayı ve resmî şablon son kontrolü yine zorunludur.")

    doc.add_heading("6. Kaynak ve İzlenebilirlik", level=1)
    src = report["source"]
    doc.add_paragraph(f"Kaynak: {src['title']} · Doküman No: {src['document_no']} · Revizyon: {src['revision_no']} · {src['revision_date']}")
    doc.add_paragraph("Bu taslak, resmî MEDEK ÖDR dosyasının yerine geçmez; DOU Assess kayıtlarının resmî hazırlık sürecine izlenebilir biçimde aktarılmasını kolaylaştırır.")

    out = BytesIO(); doc.save(out)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(program["code"]))[:60]
    return out.getvalue(), f"DOU-Assess-MEDEK-ODR-v1.1-{safe}-{academic_year}.docx"


def build_self_evaluation_report(db: Session, program_id: int, academic_year: str, framework_id: int | None = None) -> dict[str, Any]:
    """Build an evidence-traceable self-evaluation draft from verified Quality360 records."""
    dashboard = program_dashboard(db, program_id, academic_year, framework_id)
    readiness = accreditation_evidence_readiness(db, program_id, academic_year, framework_id)
    criteria = []
    matrix = {str(x.get("criterion_code")): x for x in readiness.get("matrix", [])}
    for c in dashboard.get("criteria", []):
        code = str(c.get("code") or "")
        r = matrix.get(code, {})
        positives = [x.get("label") for x in c.get("signals", []) if x.get("ok")]
        gaps = list(r.get("missing_signals") or [])
        evidence = list(r.get("evidence") or [])
        narrative = []
        if positives:
            narrative.append("Güçlü yönler: " + "; ".join(positives[:5]) + ".")
        if gaps:
            narrative.append("Geliştirme alanları: " + "; ".join(gaps[:5]) + ".")
        if evidence:
            narrative.append(f"Bu ölçüt için {len(evidence)} doğrudan kanıt ilişkilendirilmiştir.")
        if not narrative:
            narrative.append("Bu ölçüt için yeterli doğrulanmış kayıt henüz oluşmamıştır.")
        criteria.append({
            "code": code,
            "name": c.get("name") or code,
            "readiness_score": c.get("score", 0),
            "visit_score": r.get("visit_score", 0),
            "status": r.get("status", "gap"),
            "narrative": " ".join(narrative),
            "positive_signals": positives,
            "missing_signals": gaps,
            "evidence_refs": [{"id": e.get("id"), "name": e.get("name"), "category": e.get("category")} for e in evidence],
            "open_cycle_count": r.get("open_cycle_count", 0),
            "closed_cycle_count": r.get("closed_cycle_count", 0),
            "decision_count": r.get("decision_count", 0),
        })
    strong = sorted(criteria, key=lambda x: x["visit_score"], reverse=True)[:3]
    priority = sorted(criteria, key=lambda x: x["visit_score"])[:5]
    return {
        "program": dashboard["program"],
        "academic_year": academic_year,
        "framework": dashboard["framework"],
        "readiness_percent": dashboard.get("readiness_percent", 0),
        "visit_readiness_percent": readiness.get("visit_readiness_percent", 0),
        "executive_summary": {
            "strengths": [{"code": x["code"], "name": x["name"], "score": x["visit_score"]} for x in strong],
            "priorities": [{"code": x["code"], "name": x["name"], "score": x["visit_score"], "missing_signals": x["missing_signals"]} for x in priority],
            "counts": dashboard.get("counts", {}),
        },
        "criteria": criteria,
        "traceability": {
            "source": "DOU Assess Quality360",
            "rule": "Her anlatım yalnız sistemde doğrulanmış sinyal, kanıt, PUKÖ ve kurul kayıtlarından türetilir.",
            "human_approval_required": True,
        },
        "disclaimer": "Bu içerik otomatik oluşturulan öz değerlendirme çalışma taslağıdır; nihai rapor yetkili kurul tarafından doğrulanmalı ve onaylanmalıdır.",
    }


def build_self_evaluation_docx(db: Session, program_id: int, academic_year: str, framework_id: int | None = None) -> tuple[bytes, str]:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    report = build_self_evaluation_report(db, program_id, academic_year, framework_id)
    program = report["program"]
    fw = report["framework"]
    doc = Document()
    doc.styles["Normal"].font.name = "Aptos"
    doc.styles["Normal"].font.size = Pt(10.5)
    title = doc.add_paragraph(); title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("DOĞUŞ ÜNİVERSİTESİ\nÖZ DEĞERLENDİRME RAPORU · İZLENEBİLİR TASLAK")
    run.bold = True; run.font.size = Pt(18)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"{program['code']} · {program['name']}\n{academic_year}\n{fw['name']} · {fw['version']}")
    doc.add_paragraph(report["disclaimer"])

    doc.add_heading("1. Yönetici Özeti", level=1)
    doc.add_paragraph(f"Program hazırlık göstergesi %{report['readiness_percent']} · ziyaret hazırlığı %{report['visit_readiness_percent']}.")
    doc.add_heading("Güçlü alanlar", level=2)
    for x in report["executive_summary"]["strengths"]:
        doc.add_paragraph(f"{x['code']} · {x['name']} — %{x['score']}", style="List Bullet")
    doc.add_heading("Öncelikli geliştirme alanları", level=2)
    for x in report["executive_summary"]["priorities"]:
        missing = "; ".join(x.get("missing_signals") or []) or "Kanıt ve ölçüm derinliği artırılmalı"
        doc.add_paragraph(f"{x['code']} · {x['name']} — %{x['score']}: {missing}", style="List Bullet")

    doc.add_heading("2. Ölçüt Bazlı Öz Değerlendirme", level=1)
    for c in report["criteria"]:
        doc.add_heading(f"{c['code']} · {c['name']}", level=2)
        doc.add_paragraph(c["narrative"])
        doc.add_paragraph(f"Hazırlık: %{c['readiness_score']} · Ziyaret hazırlığı: %{c['visit_score']} · Açık PUKÖ: {c['open_cycle_count']} · Kapalı PUKÖ: {c['closed_cycle_count']} · Kurul kararı: {c['decision_count']}")
        if c["evidence_refs"]:
            doc.add_paragraph("İzlenebilir kanıtlar:")
            for e in c["evidence_refs"]:
                doc.add_paragraph(f"E#{e['id']} · {e['name']} · {e.get('category') or 'quality'}", style="List Bullet")
        else:
            doc.add_paragraph("Doğrudan ilişkilendirilmiş kanıt bulunmuyor.")

    doc.add_heading("3. İzlenebilirlik ve Onay", level=1)
    doc.add_paragraph(report["traceability"]["rule"])
    doc.add_paragraph("Nihai yayımdan önce program kurulu / kalite sorumlusu tarafından doğrulama ve insan onayı zorunludur.")
    out = BytesIO(); doc.save(out)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in program["code"])[:60]
    return out.getvalue(), f"DOU-Assess-Oz-Degerlendirme-{safe}-{academic_year}.docx"


def build_institutional_self_evaluation_report(db: Session, academic_year: str, faculty: str | None = None) -> dict[str, Any]:
    """Aggregate programme self-evaluations into faculty/unit or university KIDR-style draft."""
    stmt = select(m.Program).order_by(m.Program.faculty, m.Program.department, m.Program.name)
    programs = db.scalars(stmt).all()
    if faculty:
        programs = [p for p in programs if (p.faculty or "Tanımsız Akademik Birim") == faculty]
    programme_rows=[]
    framework_counts=defaultdict(int)
    all_strengths=[]
    all_priorities=[]
    total_evidence=0; total_open=0; total_closed=0
    for p in programs:
        routing=recommend_program_frameworks(db,p.id)
        manual_primary=next((a for a in routing.get("assignments",[]) if a.get("is_primary") and a.get("active")),None)
        recommended=next((r for r in routing.get("recommendations",[]) if r.get("is_primary")),None)
        fw_id=(manual_primary or {}).get("framework_profile_id") or (recommended or {}).get("framework_id")
        try:
            rep=build_self_evaluation_report(db,p.id,academic_year,fw_id)
        except Exception:
            continue
        fw=rep.get("framework") or {}
        framework_counts[fw.get("framework_family") or fw.get("code") or "Tanımsız"] += 1
        crit=rep.get("criteria",[])
        evidence=sum(len(c.get("evidence_refs") or []) for c in crit)
        opened=sum(int(c.get("open_cycle_count") or 0) for c in crit)
        closed=sum(int(c.get("closed_cycle_count") or 0) for c in crit)
        total_evidence+=evidence; total_open+=opened; total_closed+=closed
        row={"program_id":p.id,"code":p.code,"name":p.name,"faculty":p.faculty,"department":p.department,"framework":fw,"readiness_percent":rep.get("readiness_percent",0),"visit_readiness_percent":rep.get("visit_readiness_percent",0),"evidence_count":evidence,"open_cycle_count":opened,"closed_cycle_count":closed}
        programme_rows.append(row)
        for x in rep.get("executive_summary",{}).get("strengths",[]): all_strengths.append({**x,"program_code":p.code,"program_name":p.name})
        for x in rep.get("executive_summary",{}).get("priorities",[]): all_priorities.append({**x,"program_code":p.code,"program_name":p.name})
    n=len(programme_rows)
    avg=round(sum(float(x["visit_readiness_percent"]) for x in programme_rows)/n,2) if n else 0.0
    faculties=sorted({(x.get("faculty") or "Tanımsız Akademik Birim") for x in programme_rows})
    scope_name=faculty or "Doğuş Üniversitesi"
    return {
        "scope":"faculty" if faculty else "university","scope_name":scope_name,"academic_year":academic_year,
        "summary":{"program_count":n,"faculty_count":len(faculties),"visit_readiness_percent":avg,"evidence_count":total_evidence,"open_cycle_count":total_open,"closed_cycle_count":total_closed},
        "framework_distribution":dict(framework_counts),"programs":sorted(programme_rows,key=lambda x:(x["visit_readiness_percent"],x["name"])),
        "strengths":sorted(all_strengths,key=lambda x:x.get("score",0),reverse=True)[:10],
        "priorities":sorted(all_priorities,key=lambda x:x.get("score",0))[:15],
        "narrative":{
            "quality_assurance":f"{scope_name} kapsamında {n} programın kalite ve akreditasyon verileri izlenebilir biçimde birleştirilmiştir.",
            "evidence":f"Toplam {total_evidence} kriter bağlantılı kanıt kaydı değerlendirmeye dahil edilmiştir.",
            "improvement":f"{total_open} açık ve {total_closed} kapalı PUKÖ döngüsü kurumsal iyileştirme izine dahil edilmiştir.",
            "readiness":f"Programların ortalama kurum içi ziyaret hazırlığı %{avg} seviyesindedir. Bu gösterge resmî akreditasyon puanı değildir."
        },
        "traceability":{"source":"DOU Assess Quality360","programme_level_trace":True,"human_approval_required":True},
        "disclaimer":"Bu belge program öz değerlendirmelerinden otomatik derlenen kurum içi çalışma taslağıdır; nihai Birim Öz Değerlendirme / KİDR metni yetkili kurullar tarafından doğrulanmalı ve onaylanmalıdır."
    }


def build_institutional_self_evaluation_docx(db: Session, academic_year: str, faculty: str | None = None) -> tuple[bytes,str]:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt
    report=build_institutional_self_evaluation_report(db,academic_year,faculty)
    doc=Document(); doc.styles["Normal"].font.name="Aptos"; doc.styles["Normal"].font.size=Pt(10.5)
    t=doc.add_paragraph(); t.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=t.add_run("DOĞUŞ ÜNİVERSİTESİ\n" + ("BİRİM ÖZ DEĞERLENDİRME RAPORU" if faculty else "KURUM İÇ DEĞERLENDİRME RAPORU") + " · İZLENEBİLİR TASLAK"); r.bold=True; r.font.size=Pt(18)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run(f"{report['scope_name']}\n{academic_year}")
    doc.add_paragraph(report["disclaimer"])
    doc.add_heading("1. Yönetici Özeti",level=1)
    s=report["summary"]; doc.add_paragraph(f"Program sayısı: {s['program_count']} · Ortalama ziyaret hazırlığı: %{s['visit_readiness_percent']} · Kanıt: {s['evidence_count']} · Açık PUKÖ: {s['open_cycle_count']} · Kapalı PUKÖ: {s['closed_cycle_count']}")
    for k,v in report["narrative"].items(): doc.add_paragraph(v)
    doc.add_heading("2. Program / Birim Görünümü",level=1)
    table=doc.add_table(rows=1,cols=6); table.style="Table Grid"
    for i,h in enumerate(["Program","Birim","Çerçeve","Hazırlık","Kanıt","Açık PUKÖ"]): table.rows[0].cells[i].text=h
    for x in report["programs"]:
        row=table.add_row().cells; vals=[f"{x['code']} · {x['name']}",x.get('faculty') or '-',(x.get('framework') or {}).get('code') or '-',f"%{x['visit_readiness_percent']}",str(x['evidence_count']),str(x['open_cycle_count'])]
        for i,v in enumerate(vals): row[i].text=str(v)
    doc.add_heading("3. Kurumsal Güçlü Alanlar",level=1)
    for x in report["strengths"]: doc.add_paragraph(f"{x['program_code']} · {x['code']} · {x['name']} — %{x['score']}",style="List Bullet")
    doc.add_heading("4. Öncelikli Geliştirme Alanları",level=1)
    for x in report["priorities"]:
        miss='; '.join(x.get('missing_signals') or []) or 'Kanıt/ölçüm derinliği artırılmalı'
        doc.add_paragraph(f"{x['program_code']} · {x['code']} · {x['name']} — %{x['score']}: {miss}",style="List Bullet")
    doc.add_heading("5. İzlenebilirlik ve Onay",level=1); doc.add_paragraph("Her kurumsal bulgu program düzeyindeki kriter, kanıt, PUKÖ ve kurul kayıtlarına geri izlenebilir. Nihai yayımdan önce insan onayı zorunludur.")
    out=BytesIO(); doc.save(out)
    safe=(faculty or 'Universite').replace(' ','_')[:70]
    return out.getvalue(),f"DOU-Assess-{'Birim-ODR' if faculty else 'KIDR'}-{safe}-{academic_year}.docx"

def build_odr_docx(db: Session, program_id: int, academic_year: str, framework_id: int | None = None) -> tuple[bytes, str]:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    dashboard = program_dashboard(db, program_id, academic_year, framework_id)
    program = dashboard["program"]
    doc = Document()
    styles = doc.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(10.5)
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("DOĞUŞ ÜNİVERSİTESİ\nÖZ DEĞERLENDİRME RAPORU (ÖDR) TASLAĞI")
    run.bold = True; run.font.size = Pt(18)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"{program['code']} · {program['name']}\n{academic_year}\n{dashboard['framework']['name']} {dashboard['framework']['version']}")
    doc.add_paragraph("Bu belge DOU Assess Quality & Accreditation 360 verilerinden otomatik oluşturulan çalışma taslağıdır. Nihai ÖDR, program kurulu ve kalite sorumluları tarafından kanıtlarla doğrulanarak yayımlanmalıdır.")

    doc.add_heading("1. Hazırlık Özeti", level=1)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for i, text in enumerate(["Hazırlık Skoru", "Durum", "Çerçeve"]): table.rows[0].cells[i].text = text
    row = table.add_row().cells
    row[0].text = f"%{dashboard['readiness_percent']}"
    row[1].text = dashboard["readiness_label"]
    row[2].text = f"{dashboard['framework']['code']} · {dashboard['framework']['version']}"

    doc.add_heading("2. Ölçüt Bazlı Hazırlık", level=1)
    t = doc.add_table(rows=1, cols=4); t.style = "Table Grid"
    for i, text in enumerate(["Ölçüt", "Başlık", "Skor", "Durum"]): t.rows[0].cells[i].text = text
    for c in dashboard["criteria"]:
        cells = t.add_row().cells
        cells[0].text = str(c.get("code", "")); cells[1].text = str(c.get("name", "")); cells[2].text = f"%{c['score']}"; cells[3].text = c["readiness"]

    doc.add_heading("3. Müfredat ve AKTS Denetimi", level=1)
    cur = dashboard["curriculum"]
    doc.add_paragraph(f"Toplam tanımlı AKTS: {cur['total_ects']} · Tanımlı ders sayısı: {cur['course_count']}")
    t = doc.add_table(rows=1, cols=4); t.style = "Table Grid"
    for i, text in enumerate(["Kontrol", "Gerçekleşen", "Eşik", "Sonuç"]): t.rows[0].cells[i].text = text
    for check in cur["checks"]:
        cells = t.add_row().cells
        cells[0].text = f"{check['code']} · {check['label']}"; cells[1].text = str(check["actual"]); cells[2].text = str(check["required"]); cells[3].text = "Uygun" if check["passed"] else "Açık"

    doc.add_heading("4. Ölçüt Açıklamaları ve Kanıt Sinyalleri", level=1)
    for c in dashboard["criteria"]:
        doc.add_heading(f"Ölçüt {c.get('code')} · {c.get('name')}", level=2)
        doc.add_paragraph(f"Hazırlık skoru: %{c['score']}. Manuel olgunluk: {c.get('manual_maturity') or 'girilmeli'}. {c.get('manual_note') or ''}")
        if c.get("signals"):
            for s in c["signals"]:
                doc.add_paragraph(("✓ " if s["ok"] else "○ ") + s["label"], style="List Bullet")

    doc.add_heading("5. Kayıt Envanteri", level=1)
    for key, label in [
        ("stakeholders", "Paydaş kayıtları"), ("graduates", "Mezun izleme"), ("faculty", "Öğretim kadrosu"),
        ("infrastructure", "Altyapı/laboratuvar"), ("quality_cycles", "PUKÖ döngüleri"),
        ("governance_decisions", "Kurul/karar kayıtları"), ("quality_evidence", "Kalite kanıtları"),
    ]:
        doc.add_paragraph(f"{label}: {dashboard['counts'][key]}", style="List Bullet")

    doc.add_heading("6. Sonraki Adımlar", level=1)
    gaps = [c for c in dashboard["criteria"] if c["score"] < 70]
    if gaps:
        for c in gaps:
            doc.add_paragraph(f"Ölçüt {c.get('code')} {c.get('name')}: eksik kanıtları tamamla, PUKÖ kaydı oluştur ve olgunluk değerlendirmesini güncelle.", style="List Bullet")
    else:
        doc.add_paragraph("Ölçütlerin tamamı hazırlık eşiğinin üzerinde. Kanıt bütünlüğü ve kurul onayı son kez doğrulanmalıdır.")

    out = BytesIO(); doc.save(out)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in program["code"])[:60]
    return out.getvalue(), f"DOU-Assess-ODR-{safe}-{academic_year}.docx"


def _date_value(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime): return value.date()
    if isinstance(value, date): return value
    return date.fromisoformat(str(value)[:10])


def _bool_value(value: Any, default: bool = False) -> bool:
    if value in (None, ""): return default
    return str(value).strip().casefold() in {"1", "true", "evet", "yes", "e", "x", "var"}


def _program_from_row(db: Session, row: dict[str, Any]) -> m.Program | None:
    code = str(row.get("program_code") or "").strip()
    return db.scalar(select(m.Program).where(m.Program.code == code)) if code else None


QUALITY_EXCEL_KINDS = {"curriculum", "stakeholders", "graduates", "faculty", "infrastructure", "quality_cycles", "governance"}


def validate_excel_rows(kind: str, rows: list[dict[str, Any]], db: Session) -> list[str]:
    errors: list[str] = []
    for row in rows:
        rn = row.get("__row__")
        try:
            program = _program_from_row(db, row)
            if not program:
                errors.append(f"Satır {rn}: program bulunamadı ({row.get('program_code')})"); continue
            require_program_access(db, program.id, write=True, accreditation=True)
            if kind == "curriculum":
                if str(row.get("term") or "") not in TERMS: errors.append(f"Satır {rn}: dönem geçersiz")
                if str(row.get("class_level") or "") not in CLASS_LEVELS: errors.append(f"Satır {rn}: sınıf geçersiz")
                if float(row.get("ects") or 0) < 0: errors.append(f"Satır {rn}: AKTS negatif olamaz")
            elif kind == "stakeholders":
                if str(row.get("stakeholder_type") or "") not in STAKEHOLDER_TYPES: errors.append(f"Satır {rn}: paydaş türü geçersiz")
            elif kind == "graduates":
                if str(row.get("employment_status") or "Bilinmiyor") not in GRADUATE_EMPLOYMENT_STATUSES: errors.append(f"Satır {rn}: istihdam durumu geçersiz")
                if not str(row.get("graduate_key") or "").strip(): errors.append(f"Satır {rn}: graduate_key zorunlu")
            elif kind == "faculty":
                if str(row.get("title") or "") not in INSTRUCTOR_TITLES: errors.append(f"Satır {rn}: unvan geçersiz")
                if "@" not in str(row.get("email") or ""): errors.append(f"Satır {rn}: e-posta geçersiz")
            elif kind == "infrastructure":
                if str(row.get("infrastructure_type") or "") not in INFRASTRUCTURE_TYPES: errors.append(f"Satır {rn}: altyapı türü geçersiz")
            elif kind == "quality_cycles":
                if str(row.get("status") or "planned") not in QUALITY_CYCLE_STATUSES: errors.append(f"Satır {rn}: PUKÖ durumu geçersiz")
            elif kind == "governance":
                if str(row.get("body_type") or "") not in GOVERNANCE_BODIES: errors.append(f"Satır {rn}: kurul türü geçersiz")
                if not str(row.get("decision_no") or "").strip(): errors.append(f"Satır {rn}: decision_no zorunlu")
        except Exception as exc:
            errors.append(f"Satır {rn}: {exc}")
    return errors


def import_excel_rows(kind: str, rows: list[dict[str, Any]], db: Session) -> tuple[int, int]:
    created = updated = 0
    now = datetime.now(timezone.utc)
    for row in rows:
        program = _program_from_row(db, row)
        assert program is not None
        if kind == "curriculum":
            year = str(row["academic_year"]).strip(); code = str(row["course_code"]).strip()
            obj = db.scalar(select(m.CurriculumItem).where(m.CurriculumItem.program_id == program.id, m.CurriculumItem.academic_year == year, m.CurriculumItem.course_code == code))
            data = dict(program_id=program.id, academic_year=year, term=str(row["term"]).strip(), class_level=str(row["class_level"]).strip(), course_code=code, course_name=str(row["course_name"]).strip(), ects=float(row.get("ects") or 0), course_category=str(row.get("course_category") or "Genel / Zorunlu").strip(), is_professional=_bool_value(row.get("is_professional")), is_program_specific=_bool_value(row.get("is_program_specific")), is_external_stakeholder_supported=_bool_value(row.get("is_external_stakeholder_supported")), is_applied_or_current_tech=_bool_value(row.get("is_applied_or_current_tech")), quality_status=str(row.get("quality_status") or "implemented").strip(), notes=str(row.get("notes") or "").strip())
            if obj:
                for k,v in data.items(): setattr(obj,k,v)
                updated += 1
            else: db.add(m.CurriculumItem(**data)); created += 1
        elif kind == "stakeholders":
            db.add(m.StakeholderRecord(program_id=program.id, stakeholder_type=str(row["stakeholder_type"]).strip(), name=str(row["name"]).strip(), organization=str(row.get("organization") or "").strip(), engagement_type=str(row.get("engagement_type") or "Görüş / Geri Bildirim").strip(), engagement_date=_date_value(row.get("engagement_date")), feedback=str(row.get("feedback") or "").strip(), resulting_action=str(row.get("resulting_action") or "").strip(), quality_status=str(row.get("quality_status") or "implemented").strip(), evidence_ref=str(row.get("evidence_ref") or "").strip())); created += 1
        elif kind == "graduates":
            key = str(row["graduate_key"]).strip()
            obj = db.scalar(select(m.GraduateRecord).where(m.GraduateRecord.program_id == program.id, m.GraduateRecord.graduate_key == key))
            rel = None if row.get("related_field") in (None, "") else _bool_value(row.get("related_field"))
            data = dict(program_id=program.id, graduate_key=key, full_name=str(row.get("full_name") or "").strip(), graduation_year=int(row["graduation_year"]) if row.get("graduation_year") not in (None, "") else None, employment_status=str(row.get("employment_status") or "Bilinmiyor").strip(), employer=str(row.get("employer") or "").strip(), sector=str(row.get("sector") or "").strip(), job_title=str(row.get("job_title") or "").strip(), related_field=rel, survey_date=_date_value(row.get("survey_date")), notes=str(row.get("notes") or "").strip())
            if obj:
                for k,v in data.items(): setattr(obj,k,v)
                updated += 1
            else: db.add(m.GraduateRecord(**data)); created += 1
        elif kind == "faculty":
            email = str(row["email"]).strip().lower()
            obj = db.scalar(select(m.FacultyRecord).where(m.FacultyRecord.program_id == program.id, m.FacultyRecord.email == email))
            data = dict(program_id=program.id, title=str(row["title"]).strip(), full_name=str(row["full_name"]).strip(), email=email, employment_type=str(row.get("employment_type") or "Tam Zamanlı").strip(), expertise=str(row.get("expertise") or "").strip(), highest_degree=str(row.get("highest_degree") or "").strip(), industry_experience_years=float(row.get("industry_experience_years") or 0), weekly_course_hours=float(row.get("weekly_course_hours") or 0), quality_status=str(row.get("quality_status") or "implemented").strip())
            if obj:
                for k,v in data.items(): setattr(obj,k,v)
                updated += 1
            else: db.add(m.FacultyRecord(**data)); created += 1
        elif kind == "infrastructure":
            db.add(m.InfrastructureRecord(program_id=program.id, infrastructure_type=str(row["infrastructure_type"]).strip(), name=str(row["name"]).strip(), location=str(row.get("location") or "").strip(), capacity=int(row["capacity"]) if row.get("capacity") not in (None, "") else None, quality_status=str(row.get("quality_status") or "implemented").strip(), accessibility_status=str(row.get("accessibility_status") or "implemented").strip(), isg_status=str(row.get("isg_status") or "implemented").strip(), last_review_date=_date_value(row.get("last_review_date")), notes=str(row.get("notes") or "").strip())); created += 1
        elif kind == "quality_cycles":
            status = str(row.get("status") or "planned").strip()
            db.add(m.QualityCycle(program_id=program.id, academic_year=str(row["academic_year"]).strip(), criterion_code=str(row["criterion_code"]).strip(), title=str(row["title"]).strip(), plan_text=str(row.get("plan_text") or "").strip(), do_text=str(row.get("do_text") or "").strip(), check_text=str(row.get("check_text") or "").strip(), act_text=str(row.get("act_text") or "").strip(), owner=str(row.get("owner") or "").strip(), due_date=_date_value(row.get("due_date")), status=status, evidence_refs=[x.strip() for x in str(row.get("evidence_refs") or "").split(";") if x.strip()], closed_at=now if status == "closed" else None)); created += 1
        elif kind == "governance":
            meeting_no = str(row["meeting_no"]).strip(); decision_no = str(row["decision_no"]).strip()
            obj = db.scalar(select(m.GovernanceDecision).where(m.GovernanceDecision.program_id == program.id, m.GovernanceDecision.meeting_no == meeting_no, m.GovernanceDecision.decision_no == decision_no))
            data = dict(program_id=program.id, body_type=str(row["body_type"]).strip(), meeting_date=_date_value(row.get("meeting_date")), meeting_no=meeting_no, decision_no=decision_no, subject=str(row["subject"]).strip(), decision_text=str(row["decision_text"]).strip(), related_criterion=str(row.get("related_criterion") or "").strip(), source_stakeholder_id=int(row["source_stakeholder_id"]) if row.get("source_stakeholder_id") not in (None, "") else None, status=str(row.get("status") or "implemented").strip(), evidence_ref=str(row.get("evidence_ref") or "").strip())
            if obj:
                for k,v in data.items(): setattr(obj,k,v)
                updated += 1
            else: db.add(m.GovernanceDecision(**data)); created += 1
    return created, updated

# ---------------------------------------------------------------------------
# 6.63 Institutional Accreditation Readiness
# ---------------------------------------------------------------------------

def institutional_accreditation_readiness(db: Session, academic_year: str) -> dict[str, Any]:
    """Cross-program, cross-framework institutional readiness cockpit.

    Readiness is an internal preparation signal only. Evidence reuse is reported only
    through explicitly approved crosswalk rows; no criterion equivalence is inferred.
    """
    programs = list(db.scalars(select(m.Program).order_by(m.Program.faculty, m.Program.department, m.Program.name)).all())
    crosswalks = list(db.scalars(select(m.AccreditationCrosswalk).where(
        m.AccreditationCrosswalk.review_status == "approved"
    ).order_by(m.AccreditationCrosswalk.id)).all())
    framework_summary: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "program_count": 0, "readiness_total": 0.0, "ready": 0, "attention": 0, "gaps": 0,
        "evidence_total": 0, "critical_gap_count": 0,
    })
    program_rows: list[dict[str, Any]] = []
    gap_queue: list[dict[str, Any]] = []
    reusable_evidence: list[dict[str, Any]] = []

    for program in programs:
        try:
            routing = recommend_program_frameworks(db, program.id)
        except Exception:
            continue
        assigned = [x for x in routing.get("assignments", []) if x.get("active")]
        selected = next((x for x in assigned if x.get("is_primary")), None)
        framework = (selected or {}).get("framework") if selected else None
        if not framework:
            primary = next((x for x in routing.get("recommendations", []) if x.get("is_primary")), None)
            if not primary:
                continue
            framework = model_dict(db.get(m.QualityFrameworkProfile, int(primary["framework_id"])))
        if not framework:
            continue
        family = str(framework.get("framework_family") or "").upper()
        framework_id = int(framework.get("id") or 0)
        if not framework_id:
            continue

        try:
            if family in {"TURAK", "SABAK", "EPDAD"}:
                readiness = framework_preparation_readiness(db, program.id, academic_year, framework_id)
                score = float(readiness.get("readiness_percent") or 0)
                summary = readiness.get("summary") or {}
                ready = int(summary.get("ready") or 0)
                attention = int(summary.get("attention") or 0)
                gaps = int(summary.get("gaps") or 0)
                evidence_total = int(summary.get("exact_evidence_links") or 0)
                priorities = readiness.get("priority_gaps") or []
            else:
                readiness = accreditation_evidence_readiness(db, program.id, academic_year, framework_id)
                score = float(readiness.get("visit_readiness_percent") or 0)
                summary = readiness.get("summary") or {}
                ready = int(summary.get("subcriteria_ready") or summary.get("ready") or 0)
                attention = int(summary.get("subcriteria_attention") or summary.get("attention") or 0)
                gaps = int(summary.get("subcriteria_gaps") or summary.get("gaps") or 0)
                evidence_total = int(summary.get("evidence_total") or 0)
                priorities = readiness.get("priority_gaps") or []
        except Exception:
            score = 0.0; ready = attention = evidence_total = 0; gaps = 1; priorities = []

        cycles = list(db.scalars(select(m.QualityCycle).where(
            m.QualityCycle.program_id == program.id,
            m.QualityCycle.academic_year == academic_year,
            m.QualityCycle.status != "closed",
        )).all())
        cycle_by_code = {str(x.criterion_code or ""): x for x in cycles if x.criterion_code}
        status = "ready" if score >= 80 and gaps == 0 else ("attention" if score >= 55 else "risk")
        fsum = framework_summary[family]
        fsum["program_count"] += 1; fsum["readiness_total"] += score
        fsum["ready"] += ready; fsum["attention"] += attention; fsum["gaps"] += gaps
        fsum["evidence_total"] += evidence_total; fsum["critical_gap_count"] += gaps

        row = {
            "program_id": program.id, "program_code": program.code, "program_name": program.name,
            "faculty": program.faculty, "department": program.department,
            "framework_id": framework_id, "framework_family": family,
            "framework_version": framework.get("version") or "", "framework_code": framework.get("code") or "",
            "readiness_percent": round(score, 2), "status": status,
            "ready_count": ready, "attention_count": attention, "gap_count": gaps,
            "evidence_total": evidence_total, "open_quality_cycles": len(cycles),
        }
        program_rows.append(row)

        for gap in priorities[:12]:
            code = str(gap.get("subcriterion_code") or gap.get("code") or gap.get("criterion_code") or gap.get("mapped_criterion") or "")
            cycle = cycle_by_code.get(code) or next((c for k, c in cycle_by_code.items() if code.startswith(k + ".") or k.startswith(code + ".")), None)
            gap_queue.append({
                "program_id": program.id, "program_name": program.name, "faculty": program.faculty,
                "framework_family": family, "framework_version": framework.get("version") or "",
                "criterion_code": code,
                "title": gap.get("subcriterion_title") or gap.get("title") or gap.get("criterion_name") or code,
                "status": gap.get("status") or "gap", "needs_evidence": bool(gap.get("needs_evidence", True)),
                "owner": cycle.owner if cycle else "Program / Kalite Sorumlusu",
                "due_date": cycle.due_date.isoformat() if cycle and cycle.due_date else None,
                "quality_cycle_id": cycle.id if cycle else None,
            })

        evidence_rows = list(db.scalars(select(m.QualityEvidenceAsset).where(m.QualityEvidenceAsset.program_id == program.id)).all())
        for evidence in evidence_rows:
            code = str(evidence.criterion_code or "")
            if not code:
                continue
            applicable = [x for x in crosswalks if
                x.source_framework_family.upper() == family and
                (not x.source_framework_version or x.source_framework_version == str(framework.get("version") or "")) and
                x.source_criterion_code == code]
            if applicable:
                reusable_evidence.append({
                    "evidence_id": evidence.id, "program_id": program.id, "program_name": program.name,
                    "name": evidence.original_name, "sha256": evidence.sha256,
                    "source": {"family": family, "version": framework.get("version") or "", "criterion_code": code},
                    "targets": [{"crosswalk_id": x.id, "family": x.target_framework_family, "version": x.target_framework_version,
                                 "criterion_code": x.target_criterion_code, "relationship": x.relationship}
                                for x in applicable],
                })

    frameworks = []
    for family, values in sorted(framework_summary.items()):
        count = values["program_count"]
        frameworks.append({
            "family": family, **{k:v for k,v in values.items() if k != "readiness_total"},
            "readiness_percent": round(values["readiness_total"] / max(count, 1), 2),
        })
    gap_queue.sort(key=lambda x: (0 if x["status"] == "gap" else 1, x["due_date"] is None, x["due_date"] or "9999-12-31", x["program_name"]))
    program_rows.sort(key=lambda x: (x["readiness_percent"], -x["gap_count"], x["program_name"]))
    overall = round(sum(x["readiness_percent"] for x in program_rows) / max(len(program_rows), 1), 2)
    return {
        "academic_year": academic_year,
        "summary": {
            "program_count": len(program_rows), "framework_count": len(frameworks),
            "institutional_readiness_percent": overall,
            "critical_gap_count": sum(x["gap_count"] for x in program_rows),
            "open_quality_cycle_count": sum(x["open_quality_cycles"] for x in program_rows),
            "evidence_total": sum(x["evidence_total"] for x in program_rows),
            "approved_crosswalk_count": len(crosswalks),
            "reusable_evidence_count": len(reusable_evidence),
        },
        "frameworks": frameworks,
        "programs": program_rows,
        "priority_gaps": gap_queue[:50],
        "reusable_evidence": reusable_evidence[:50],
        "disclaimer": "Hazırlık yüzdeleri kurum içi yönetim göstergesidir; hiçbir akreditasyon kuruluşunun resmî puanı veya kararı değildir. Çapraz kanıt kullanımı yalnız kalite birimi tarafından onaylanmış eşlemeler üzerinden gösterilir.",
    }
