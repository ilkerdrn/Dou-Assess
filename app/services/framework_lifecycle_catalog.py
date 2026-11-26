from __future__ import annotations

from datetime import date, datetime
from typing import Any


CATALOG: dict[int, dict[str, dict[str, Any]]] = {
    2026: {
        "TURAK": {
            "title": "TURAK 2026 Akreditasyon Süreci",
            "source_title": "TURAK 2026 Çalışma Takvimi / Başvuru",
            "source_url": "https://turak.org/2026-calisma-takvimi/",
            "document_profile": "ÖDR Sürüm 7 · 27.12.2025",
            "criteria_profile": "Değerlendirme Ölçütleri · 27.12.2024",
            "events": [
                {"code":"odr_submit","label":"ÖDR elektronik teslim","actor":"Kurum","date":"2026-07-01","stage":"submitted"},
                {"code":"format_feedback","label":"ÖDR format uygunluk geri bildirimi","actor":"TURAK","start":"2026-08-01","end":"2026-08-15","stage":"pre_review"},
                {"code":"odr_correction","label":"Düzeltilmiş ÖDR ve eklerin teslimi","actor":"Kurum","date":"2026-09-01","stage":"correction"},
                {"code":"team_notice","label":"Değerlendirme takımlarının kuruma bildirilmesi","actor":"TURAK","date":"2026-09-01","stage":"visit_ready"},
                {"code":"odr_to_team","label":"ÖDR'nin değerlendirme takımına iletilmesi","actor":"TURAK","date":"2026-09-15","stage":"visit_ready"},
                {"code":"team_objection","label":"Değerlendirme takımına itiraz son tarihi","actor":"Kurum","date":"2026-09-30","stage":"visit_ready"},
                {"code":"objection_resolution","label":"Takım itirazlarının giderilmesi","actor":"TURAK","date":"2026-10-15","stage":"visit_ready"},
                {"code":"site_visit","label":"Saha ziyaretleri","actor":"Değerlendirme Takımları","start":"2026-09-20","end":"2026-11-15","stage":"site_visit"},
                {"code":"exit_report_objection","label":"Çıkış bildirimi itiraz son tarihi","actor":"Kurum","date":"2026-11-22","stage":"response_30_day"},
                {"code":"final_report","label":"Nihai raporun TURAK'a sunulması","actor":"Değerlendirme Takımları","date":"2026-11-30","stage":"decision"},
                {"code":"consistency_report","label":"Tutarlılık komisyonu raporu","actor":"Tutarlılık Komisyonu","date":"2026-12-10","stage":"decision"},
                {"code":"decision","label":"Nihai akreditasyon kararları","actor":"TURAK","date":"2026-12-20","stage":"decision"},
                {"code":"decision_notice","label":"Karar ve raporun kuruma gönderilmesi","actor":"TURAK","date":"2026-12-31","stage":"closed"},
            ],
        },
        "SABAK": {
            "title": "SABAK 2026 Akreditasyon Süreci",
            "source_title": "SABAK 2026 Dönemi Akreditasyon Süreci Tarihleri",
            "source_url": "https://www.sabak.org.tr/index.php/tr/9-blog/75-sabak-degerlendirici-egitimi",
            "document_profile": "ÖDR Revizyon 5 · 10.04.2026",
            "criteria_profile": "Değerlendirme Ölçütleri Revizyon 4 · 05.06.2022",
            "events": [
                {"code":"intent","label":"Niyet mektubu / yazılı başvuru","actor":"Kurum","start":"2026-02-01","end":"2026-02-15","stage":"preparation"},
                {"code":"application_review","label":"Başvuruların değerlendirilmesi","actor":"SABAK","start":"2026-02-16","end":"2026-03-13","stage":"preparation"},
                {"code":"acceptance_letter","label":"Kabul mektubunun SABAK'a gönderilmesi","actor":"Kurum","start":"2026-03-16","end":"2026-03-23","stage":"preparation"},
                {"code":"institution_training","label":"Kurum eğitimi","actor":"SABAK / Kurum","date":"2026-03-26","stage":"preparation"},
                {"code":"odr_prepare","label":"ÖDR hazırlama ve elektronik teslim dönemi","actor":"Kurum","start":"2026-04-01","end":"2026-07-31","stage":"submitted"},
                {"code":"odr_pre_review","label":"ÖDR ön inceleme ve takım oluşturma","actor":"SAK","start":"2026-08-03","end":"2026-09-18","stage":"pre_review"},
                {"code":"team_review","label":"ÖDR'nin değerlendirme takımı incelemesi","actor":"Değerlendirme Takımı","start":"2026-09-18","end":"2026-10-16","stage":"visit_ready"},
                {"code":"site_visit","label":"Kurum ziyareti","actor":"Değerlendirme Takımı","start":"2026-10-18","end":"2026-12-16","stage":"site_visit"},
                {"code":"report_decision","label":"Değerlendirme raporu ve SAK kararı","actor":"SABAK / SAK","start":"2026-12-18","end":"2027-02-26","stage":"decision"},
                {"code":"system_entry","label":"Akreditasyon bilgilerinin sisteme girilmesi","actor":"SABAK","start":"2027-03-01","end":"2027-03-12","stage":"decision"},
                {"code":"university_approval","label":"Üniversite onay süreci","actor":"Kurum","start":"2027-03-15","end":"2027-03-31","stage":"closed"},
            ],
        },
        "EPDAD": {
            "title": "EPDAD 2026 Akreditasyon Süreci",
            "source_title": "EPDAD 2026 Akreditasyon Başvurusu",
            "source_url": "https://www.epdad.org.tr/icerik/akreditasyon-basvurusu-",
            "document_profile": "Öz Değerlendirme Raporu · güncel resmi doküman",
            "criteria_profile": "Lisans Programları Değerlendirme Standartları Sürüm 1.1",
            "events": [
                {"code":"contract_approval","label":"Sözleşme teklifinin kurumsal onayı","actor":"Kurum","date":"2026-04-17","stage":"preparation"},
                {"code":"odr_submit","label":"ÖDR / ara değerlendirme raporunun ABYS'de onaylanması","actor":"Kurum","date":"2026-07-03","stage":"submitted"},
                {"code":"pre_review_notice","label":"Ön inceleme yetersizliklerinin kuruma bildirilmesi","actor":"EPDAD","date":"2026-08-28","stage":"pre_review"},
                {"code":"corrected_report","label":"Düzeltilmiş raporun ABYS'de onaylanması","actor":"Kurum","date":"2026-09-25","stage":"correction"},
                {"code":"development_report","label":"Gelişim İzleme Raporu teslimi (uygun programlar)","actor":"Kurum","date":"2026-12-25","stage":"decision","conditional":True},
            ],
        },
    }
}


def _parse(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def lifecycle_profiles(cycle_year: int, as_of: date | None = None) -> dict[str, Any]:
    today = as_of or date.today()
    families = CATALOG.get(cycle_year, {})
    rows: list[dict[str, Any]] = []
    upcoming: list[dict[str, Any]] = []
    for family, cfg in families.items():
        events=[]
        for raw in cfg["events"]:
            item=dict(raw)
            start=_parse(item.get("start") or item.get("date"))
            end=_parse(item.get("end") or item.get("date"))
            if end and end < today:
                status="completed-window"
            elif start and start <= today <= (end or start):
                status="active"
            else:
                status="upcoming"
            item["status"]=status
            if start:
                item["days_until"]=(start-today).days if start>=today else 0 if status=="active" else None
            events.append(item)
            if status in {"active","upcoming"}:
                upcoming.append({"framework_family":family, **item, "source_url":cfg["source_url"]})
        rows.append({"framework_family":family, **{k:v for k,v in cfg.items() if k!="events"}, "events":events})
    upcoming.sort(key=lambda x: (_parse(x.get("start") or x.get("date")) or date.max, x["framework_family"]))
    return {
        "cycle_year": cycle_year,
        "as_of": today.isoformat(),
        "frameworks": rows,
        "upcoming": upcoming[:20],
        "disclaimer": "Takvim resmi kuruluş sayfalarından kaynak kontrollü olarak modellenmiştir. Kuruluşun yeni duyurusu veya programa özel yazısı her zaman önceliklidir.",
    }
