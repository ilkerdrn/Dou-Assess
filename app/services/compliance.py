from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models as m
from ..config import settings
from .analytics import student_exam_analytics
from .paper import _register_fonts
from .quality360 import model_dict, seed_builtin_frameworks, mudek_evidence_room_readiness


YOKAK_2026_SUBCRITERIA = [
    {"code":"A.1.1","parent":"A.1","name":"Yönetişim modeli ve idari yapı"},
    {"code":"A.1.2","parent":"A.1","name":"Liderlik"},
    {"code":"A.1.3","parent":"A.1","name":"Kurumsal dönüşüm kapasitesi"},
    {"code":"A.1.4","parent":"A.1","name":"İç kalite güvencesi mekanizmaları"},
    {"code":"A.1.5","parent":"A.1","name":"Kamuoyunu bilgilendirme ve hesap verebilirlik"},
    {"code":"A.2.1","parent":"A.2","name":"Misyon, vizyon ve politikalar"},
    {"code":"A.2.2","parent":"A.2","name":"Stratejik amaç ve hedefler"},
    {"code":"A.2.3","parent":"A.2","name":"Performans yönetimi"},
    {"code":"A.3.1","parent":"A.3","name":"Bilgi yönetim sistemi"},
    {"code":"A.3.2","parent":"A.3","name":"İnsan kaynakları yönetimi"},
    {"code":"A.3.3","parent":"A.3","name":"Finansal yönetim"},
    {"code":"A.3.4","parent":"A.3","name":"Süreç yönetimi"},
    {"code":"A.4.1","parent":"A.4","name":"İç ve dış paydaş katılımı"},
    {"code":"A.4.2","parent":"A.4","name":"Öğrenci geri bildirimleri"},
    {"code":"A.4.3","parent":"A.4","name":"Mezun ilişkileri yönetimi"},
    {"code":"A.5.1","parent":"A.5","name":"Uluslararasılaşma süreçlerinin yönetimi"},
    {"code":"A.5.2","parent":"A.5","name":"Uluslararasılaşma kaynakları"},
    {"code":"A.5.3","parent":"A.5","name":"Uluslararasılaşma performansı"},
    {"code":"B.1.1","parent":"B.1","name":"Programların tasarımı ve onayı"},
    {"code":"B.1.2","parent":"B.1","name":"Programın ders dağılım dengesi"},
    {"code":"B.1.3","parent":"B.1","name":"Ders kazanımlarının program çıktılarıyla uyumu"},
    {"code":"B.1.4","parent":"B.1","name":"Öğrenci iş yüküne dayalı ders tasarımı"},
    {"code":"B.1.5","parent":"B.1","name":"Programların izlenmesi ve güncellenmesi"},
    {"code":"B.1.6","parent":"B.1","name":"Eğitim ve öğretim süreçlerinin yönetimi"},
    {"code":"B.2.1","parent":"B.2","name":"Öğretim yöntem ve teknikleri"},
    {"code":"B.2.2","parent":"B.2","name":"Ölçme ve değerlendirme"},
    {"code":"B.2.3","parent":"B.2","name":"Öğrenci kabulü, önceki öğrenmenin tanınması ve kredilendirilmesi"},
    {"code":"B.2.4","parent":"B.2","name":"Yeterliliklerin sertifikalandırılması ve diploma"},
    {"code":"B.3.1","parent":"B.3","name":"Öğrenme ortam ve kaynakları"},
    {"code":"B.3.2","parent":"B.3","name":"Akademik destek hizmetleri"},
    {"code":"B.3.3","parent":"B.3","name":"Tesis ve altyapılar"},
    {"code":"B.3.4","parent":"B.3","name":"Dezavantajlı gruplar"},
    {"code":"B.3.5","parent":"B.3","name":"Sosyal, kültürel, sportif faaliyetler"},
    {"code":"B.4.1","parent":"B.4","name":"Atama, yükseltme ve görevlendirme kriterleri"},
    {"code":"B.4.2","parent":"B.4","name":"Öğretim yetkinlikleri ve gelişimi"},
    {"code":"B.4.3","parent":"B.4","name":"Eğitim faaliyetlerine yönelik teşvik ve ödüllendirme"},
    {"code":"C.1.1","parent":"C.1","name":"Araştırma süreçlerinin yönetimi"},
    {"code":"C.1.2","parent":"C.1","name":"İç ve dış kaynaklar"},
    {"code":"C.1.3","parent":"C.1","name":"Doktora programları ve doktora sonrası imkanlar"},
    {"code":"C.2.1","parent":"C.2","name":"Araştırma yetkinlikleri ve gelişimi"},
    {"code":"C.2.2","parent":"C.2","name":"Ulusal ve uluslararası ortak programlar ve ortak araştırma birimleri"},
    {"code":"C.3.1","parent":"C.3","name":"Araştırma performansının izlenmesi ve değerlendirilmesi"},
    {"code":"C.3.2","parent":"C.3","name":"Öğretim elemanı/araştırmacı performansının değerlendirilmesi"},
    {"code":"D.1.1","parent":"D.1","name":"Toplumsal katkı süreçlerinin yönetimi"},
    {"code":"D.1.2","parent":"D.1","name":"Kaynaklar"},
    {"code":"D.2.1","parent":"D.2","name":"Toplumsal katkı performansının izlenmesi ve değerlendirilmesi"},
]

MUDEK_31_BBO_LAYOUT = [
    "1 - Program Kanıt Belgeleri/0 - Ortak Derslerdeki Farklılıklar",
    "1 - Program Kanıt Belgeleri/1 - Öğrenciler",
    "1 - Program Kanıt Belgeleri/2 - Program Eğitim Amaçları",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları",
    "1 - Program Kanıt Belgeleri/4 - Sürekli İyileştirme",
    "1 - Program Kanıt Belgeleri/5 - Eğitim Planı",
    "1 - Program Kanıt Belgeleri/6 - Öğretim Kadrosu",
    "1 - Program Kanıt Belgeleri/7 - Altyapı",
    "1 - Program Kanıt Belgeleri/8 - Kurum Desteği ve Parasal Kaynaklar",
    "1 - Program Kanıt Belgeleri/9 - Organizasyon ve Karar Alma Süreçleri",
    "2 - Ziyaret Öncesi İstenilen Ek Bilgi ve Belgeler",
    "3 - Ziyaret Sırasında Ek Olarak Sunulan Bilgiler ve Belgeler",
    "4 - 30-Gün Yanıtı Belgeleri",
    "1 - Program Kanıt Belgeleri/1 - Öğrenciler/1.2",
    "1 - Program Kanıt Belgeleri/2 - Program Eğitim Amaçları/2.3",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.2",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/MÇ-1",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/MÇ-2",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/MÇ-3",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/MÇ-4",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/MÇ-5",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/MÇ-6",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/MÇ-7",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/MÇ-8",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/MÇ-9",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/MÇ-10",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/MÇ-11",
    "1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/Diğer Program Çıktıları",
    "1 - Program Kanıt Belgeleri/4 - Sürekli İyileştirme/4.1",
    "1 - Program Kanıt Belgeleri/4 - Sürekli İyileştirme/4.2",
    "1 - Program Kanıt Belgeleri/5 - Eğitim Planı/5.1 - EK-1 Disipline Özgü Eğitim Planı Konuları",
    "1 - Program Kanıt Belgeleri/5 - Eğitim Planı/5.5 - Ana Tasarım Deneyimi",
    "1 - Program Kanıt Belgeleri/7 - Altyapı/7.1",
    "1 - Program Kanıt Belgeleri/7 - Altyapı/7.2",
    "1 - Program Kanıt Belgeleri/7 - Altyapı/7.3",
    "1 - Program Kanıt Belgeleri/7 - Altyapı/7.4",
    "1 - Program Kanıt Belgeleri/7 - Altyapı/7.5",
]

MUDEK_31_FBO_LAYOUT = [
    "1 - Fakülte Kanıt Belgeleri/1 - Ortak Yabancı Dil Dersleri",
    "1 - Fakülte Kanıt Belgeleri/2 - Ortak Fizik Dersleri",
    "1 - Fakülte Kanıt Belgeleri/3 - Ortak Kimya Dersleri",
    "1 - Fakülte Kanıt Belgeleri/4 - Ortak Matematik Dersleri",
    "1 - Fakülte Kanıt Belgeleri/5 - Ortak Bilişim Dersleri",
    "1 - Fakülte Kanıt Belgeleri/6 - Ortak Sosyal ve Spor Alanları",
    "1 - Fakülte Kanıt Belgeleri/7 - Fakülte ve Üniversite Kapsamında Engelliler için Alınmış Olan Önlemler",
    "1 - Fakülte Kanıt Belgeleri/8 - Fakülte ve Üniversite Kapsamında Alınmış Olan Güvenlik Önlemleri",
    "1 - Fakülte Kanıt Belgeleri/9 - Üniversite Kütüphane Olanakları",
    "1 - Fakülte Kanıt Belgeleri/10 - Üniversite Bilişim Olanakları",
    "1 - Fakülte Kanıt Belgeleri/11 - Üniversite Sağlık Olanakları",
    "1 - Fakülte Kanıt Belgeleri/12 - Diğer",
    "2 - Ziyaret Öncesi İstenilen Ek Bilgi ve Belgeler",
    "3 - Ziyaret Sırasında Ek Olarak Sunulan Bilgiler ve Belgeler",
    "1 - Fakülte Kanıt Belgeleri/1 - Ortak Yabancı Dil Dersleri/Ders Bilgileri",
    "1 - Fakülte Kanıt Belgeleri/1 - Ortak Yabancı Dil Dersleri/Laboratuvarlar",
    "1 - Fakülte Kanıt Belgeleri/1 - Ortak Yabancı Dil Dersleri/Uzaktan Eğitim Süreci",
    "1 - Fakülte Kanıt Belgeleri/2 - Ortak Fizik Dersleri/Ders Bilgileri",
    "1 - Fakülte Kanıt Belgeleri/2 - Ortak Fizik Dersleri/Laboratuvarlar",
    "1 - Fakülte Kanıt Belgeleri/2 - Ortak Fizik Dersleri/Deney Listeleri ve Raporları",
    "1 - Fakülte Kanıt Belgeleri/2 - Ortak Fizik Dersleri/Uzaktan Eğitim Süreci",
    "1 - Fakülte Kanıt Belgeleri/3 - Ortak Kimya Dersleri/Ders Bilgileri",
    "1 - Fakülte Kanıt Belgeleri/3 - Ortak Kimya Dersleri/Laboratuvarlar",
    "1 - Fakülte Kanıt Belgeleri/3 - Ortak Kimya Dersleri/Deney Listeleri ve Raporları",
    "1 - Fakülte Kanıt Belgeleri/3 - Ortak Kimya Dersleri/Uzaktan Eğitim Süreci",
    "1 - Fakülte Kanıt Belgeleri/4 - Ortak Matematik Dersleri/Ders Bilgileri",
    "1 - Fakülte Kanıt Belgeleri/4 - Ortak Matematik Dersleri/Uzaktan Eğitim Süreci",
    "1 - Fakülte Kanıt Belgeleri/5 - Ortak Bilişim Dersleri/Ders Bilgileri",
    "1 - Fakülte Kanıt Belgeleri/5 - Ortak Bilişim Dersleri/Laboratuvarlar",
    "1 - Fakülte Kanıt Belgeleri/5 - Ortak Bilişim Dersleri/Uzaktan Eğitim Süreci",
    "1 - Fakülte Kanıt Belgeleri/7 - Fakülte ve Üniversite Kapsamında Engelliler için Alınmış Olan Önlemler/Fakülte",
    "1 - Fakülte Kanıt Belgeleri/7 - Fakülte ve Üniversite Kapsamında Engelliler için Alınmış Olan Önlemler/Üniversite",
    "1 - Fakülte Kanıt Belgeleri/8 - Fakülte ve Üniversite Kapsamında Alınmış Olan Güvenlik Önlemleri/Fakülte",
    "1 - Fakülte Kanıt Belgeleri/8 - Fakülte ve Üniversite Kapsamında Alınmış Olan Güvenlik Önlemleri/Üniversite",
    "1 - Fakülte Kanıt Belgeleri/9 - Üniversite Kütüphane Olanakları/Yeterlik ve Kullanım",
    "1 - Fakülte Kanıt Belgeleri/9 - Üniversite Kütüphane Olanakları/Uzaktan Erişim",
    "1 - Fakülte Kanıt Belgeleri/10 - Üniversite Bilişim Olanakları/Yeterlik ve Kullanım",
    "1 - Fakülte Kanıt Belgeleri/10 - Üniversite Bilişim Olanakları/Uzaktan Eğitim Süreci",
    "1 - Fakülte Kanıt Belgeleri/12 - Diğer/Kalite Sistemi",
    "1 - Fakülte Kanıt Belgeleri/12 - Diğer/Diğer Belgeler",
]

BUILTIN_REPORT_TEMPLATES = [
    {
        "framework_family":"MÜDEK","report_type":"ODR","version":"3.0","title":"MÜDEK Özdeğerlendirme Raporu Sürüm 3.0",
        "sections":[{"code":"A","name":"Programa İlişkin Genel Bilgiler"},{"code":"B","name":"Değerlendirme Özeti"},{"code":"EK-I","name":"Programa İlişkin Ek Bilgiler"},{"code":"EK-II","name":"Kurum Profili"}],
        "folder_layout":[],"source_url":"https://www.mudek.org.tr/tr/belge/doc.shtm","source_sha256":"official-source-registry","locked":True,"is_builtin":True,
    },
    {
        "framework_family":"MÜDEK","report_type":"ODR","version":"3.1","title":"MÜDEK Özdeğerlendirme Raporu Sürüm 3.1",
        "sections":[{"code":"A","name":"Programa İlişkin Genel Bilgiler"},{"code":"B","name":"Değerlendirme Özeti"},{"code":"EK-I","name":"Programa İlişkin Ek Bilgiler"},{"code":"EK-II","name":"Kurum Profili"}],
        "folder_layout":[],"source_url":"https://www.mudek.org.tr/tr/belge/doc.shtm","source_sha256":"official-source-registry","locked":True,"is_builtin":True,
    },
    {"framework_family":"MÜDEK","report_type":"ARA-RAPOR","version":"1.6 / Ölçüt 2.2","title":"MÜDEK Ara Rapor Hazırlama Rehberi", "sections":[],"folder_layout":[],"source_url":"https://www.mudek.org.tr/tr/belge/doc.shtm","source_sha256":"official-source-registry","locked":True,"is_builtin":True},
    {"framework_family":"MÜDEK","report_type":"BBO","version":"2.1/3.1","title":"MÜDEK Bölüm Belge Odası", "sections":[],"folder_layout":MUDEK_31_BBO_LAYOUT,"source_url":"https://www.mudek.org.tr/tr/belge/doc.shtm","source_sha256":"official-source-registry","locked":True,"is_builtin":True},
    {"framework_family":"MÜDEK","report_type":"FBO","version":"2.1/3.1","title":"MÜDEK Fakülte Belge Odası", "sections":[],"folder_layout":MUDEK_31_FBO_LAYOUT,"source_url":"https://www.mudek.org.tr/tr/belge/doc.shtm","source_sha256":"official-source-registry","locked":True,"is_builtin":True},
    {"framework_family":"MEDEK","report_type":"ODR","version":"2.0-configurable","title":"MEDEK Önlisans Program Özdeğerlendirme Raporu", "sections":[],"folder_layout":[],"source_url":"https://medek.org.tr/medek-onlisans-degerlendirme-olcutleri-20-yayimlandi","source_sha256":"official-source-registry","locked":True,"is_builtin":True},
    {"framework_family":"YÖKAK","report_type":"KIDR","version":"2026-14x46","title":"YÖKAK KİDR / Kurumsal Kalite Raporu", "sections":YOKAK_2026_SUBCRITERIA,"folder_layout":[],"source_url":"https://www.yokak.gov.tr/ukap/","source_sha256":"official-source-registry","locked":True,"is_builtin":True},
    {"framework_family":"TURAK","report_type":"ODR","version":"7-2025","title":"TURAK Özdeğerlendirme Raporu Sürüm 7", "sections":[],"folder_layout":[],"source_url":"https://turak.org/belgeler/","source_sha256":"official-source-registry","locked":True,"is_builtin":True},
    {"framework_family":"SABAK","report_type":"ODR","version":"Revizyon 5-2026","title":"SABAK Özdeğerlendirme Raporu Revizyon 5", "sections":[],"folder_layout":[],"source_url":"https://www.sabak.org.tr/index.php/tr/belgeler-ve-formlar","source_sha256":"official-source-registry","locked":True,"is_builtin":True},
    {"framework_family":"EPDAD","report_type":"ODR","version":"1.3","title":"EPDAD Öğretmen Eğitimi Öz Değerlendirme Raporu", "sections":[],"folder_layout":[],"source_url":"https://epdad.org.tr/icerik/oz-degerlendirme-raporu","source_sha256":"official-source-registry","locked":True,"is_builtin":True},
]


def stable_sha256(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def seed_report_templates(db: Session) -> list[m.AccreditationReportTemplate]:
    changed = False
    for cfg in BUILTIN_REPORT_TEMPLATES:
        obj = db.scalar(select(m.AccreditationReportTemplate).where(
            m.AccreditationReportTemplate.framework_family == cfg["framework_family"],
            m.AccreditationReportTemplate.report_type == cfg["report_type"],
            m.AccreditationReportTemplate.version == cfg["version"],
        ))
        if not obj:
            obj = m.AccreditationReportTemplate(**cfg)
            db.add(obj); changed = True
        elif obj.is_builtin:
            for k,v in cfg.items():
                if k == "source_sha256" and obj.stored_name:
                    continue
                setattr(obj,k,v)
            changed = True
    if changed: db.commit()
    return list(db.scalars(select(m.AccreditationReportTemplate).order_by(m.AccreditationReportTemplate.framework_family, m.AccreditationReportTemplate.report_type, m.AccreditationReportTemplate.version)).all())


def freeze_framework(db: Session, program_id: int, framework_profile_id: int, academic_year: str, frozen_by: str = "") -> m.QualityFrameworkSnapshot:
    fw = db.get(m.QualityFrameworkProfile, framework_profile_id)
    if not fw: raise ValueError("Kalite çerçevesi bulunamadı")
    payload = {"code":fw.code,"version":fw.version,"family":fw.framework_family,"criteria":fw.criteria,"thresholds":fw.thresholds,"source_meta":fw.source_meta}
    digest = stable_sha256(payload)
    obj = db.scalar(select(m.QualityFrameworkSnapshot).where(
        m.QualityFrameworkSnapshot.program_id==program_id,
        m.QualityFrameworkSnapshot.academic_year==academic_year,
        m.QualityFrameworkSnapshot.framework_profile_id==framework_profile_id,
    ))
    if obj:
        # Frozen snapshots are immutable. Same digest is idempotent; changed official content requires a new profile version.
        if obj.content_sha256 != digest:
            raise ValueError("Dondurulmuş çerçeve içeriği değiştirilemez; yeni resmî sürüm profili oluşturun")
        return obj
    obj = m.QualityFrameworkSnapshot(program_id=program_id, academic_year=academic_year, framework_profile_id=fw.id,
        framework_code=fw.code, framework_version=fw.version, framework_family=fw.framework_family,
        criteria=fw.criteria or [], thresholds=fw.thresholds or {}, source_meta=fw.source_meta or {}, content_sha256=digest,
        frozen_by=frozen_by or "quality")
    db.add(obj); db.flush(); return obj


def framework_criteria_tree(framework: m.QualityFrameworkProfile | m.QualityFrameworkSnapshot) -> list[dict[str,Any]]:
    rows = list(framework.criteria or [])
    family = framework.framework_family
    if family == "YÖKAK":
        by_parent = defaultdict(list)
        for s in YOKAK_2026_SUBCRITERIA: by_parent[s["parent"]].append(s)
        return [{**r,"subcriteria":by_parent.get(r.get("code"),[])} for r in rows]
    return [{**r,"subcriteria":r.get("subcriteria",[])} for r in rows]


def build_student_outcome_card(db: Session, student_id: int, academic_year: str | None = None) -> dict[str,Any]:
    student = db.get(m.Student, student_id)
    if not student:
        raise ValueError("Öğrenci bulunamadı")
    enrollments = list(db.scalars(select(m.Enrollment).where(m.Enrollment.student_id == student_id)).all())
    course_rows: list[dict[str,Any]] = []
    po_acc: dict[str,dict[str,Any]] = {}
    all_learning_outcomes: list[dict[str,Any]] = []

    for en in enrollments:
        course = en.course
        if academic_year and course.academic_year > academic_year:
            continue
        exams = list(db.scalars(select(m.Exam).where(
            m.Exam.course_id == course.id,
            m.Exam.status.in_(["grading", "approved", "archived"]),
        )).all())
        course_po = defaultdict(lambda:{"sum":0.0,"weight":0.0,"description":"","targets":[]})
        course_lo = defaultdict(lambda:{"sum":0.0,"weight":0.0,"description":"","targets":[]})
        used = 0
        for exam in exams:
            es = db.scalar(select(m.ExamStudent).where(m.ExamStudent.exam_id == exam.id, m.ExamStudent.student_id == student_id))
            if not es:
                continue
            try:
                analytics = student_exam_analytics(db, exam.id, es.id)
            except ValueError:
                continue
            weight = float(exam.assessment_weight_percent or 1.0)
            used += 1
            for lo in analytics.get("learning_outcomes", []):
                code = str(lo.get("code") or "")
                if not code:
                    continue
                att = float(lo.get("attainment_percent") or 0)
                row = course_lo[code]
                row["sum"] += att * weight
                row["weight"] += weight
                row["description"] = lo.get("description", "")
                row["targets"].append(float(lo.get("target_percent") or 0))
            for po in analytics.get("program_outcomes", []):
                code = str(po.get("code") or "")
                if not code:
                    continue
                att = float(po.get("attainment_percent") or 0)
                row = course_po[code]
                row["sum"] += att * weight
                row["weight"] += weight
                row["description"] = po.get("description", "")
                row["targets"].append(float(po.get("target_percent") or 0))
                acc = po_acc.setdefault(code,{"code":code,"description":po.get("description", ""),"sum":0.0,"weight":0.0,"targets":[]})
                acc["sum"] += att * weight
                acc["weight"] += weight
                acc["targets"].append(float(po.get("target_percent") or 0))

        lo_rows=[]
        for code,row in sorted(course_lo.items()):
            att = row["sum"] / row["weight"] if row["weight"] else 0.0
            target = sum(row["targets"]) / len(row["targets"]) if row["targets"] else 60.0
            item={
                "course_id":course.id,"course_code":course.code,"course_name":course.name,
                "academic_year":course.academic_year,"term":course.term,
                "code":code,"description":row["description"],"attainment_percent":round(att,2),
                "target_percent":round(target,2),"status":"achieved" if att >= target else "needs_improvement",
            }
            lo_rows.append(item)
            all_learning_outcomes.append(item)

        po_rows_course=[]
        for code,row in sorted(course_po.items()):
            att = row["sum"] / row["weight"] if row["weight"] else 0.0
            target = sum(row["targets"]) / len(row["targets"]) if row["targets"] else 60.0
            po_rows_course.append({
                "code":code,"description":row["description"],"attainment_percent":round(att,2),
                "target_percent":round(target,2),"status":"achieved" if att >= target else "needs_improvement",
            })
        measured_values=[x["attainment_percent"] for x in lo_rows]
        course_rows.append({
            "course_id":course.id,"course_code":course.code,"course_name":course.name,
            "academic_year":course.academic_year,"term":course.term,"exam_count":used,
            "learning_outcomes":lo_rows,"program_outcomes":po_rows_course,
            "course_attainment_percent":round(sum(measured_values)/len(measured_values),2) if measured_values else 0.0,
            "risk_count":sum(1 for x in lo_rows if x["status"] == "needs_improvement"),
        })

    po_rows=[]
    for code,x in sorted(po_acc.items()):
        att=x["sum"]/x["weight"] if x["weight"] else 0.0
        target=sum(x["targets"])/len(x["targets"]) if x["targets"] else 60.0
        po_rows.append({"code":code,"description":x["description"],"attainment_percent":round(att,2),"target_percent":round(target,2),"status":"achieved" if att>=target else "needs_improvement"})

    # Preserve current program outcomes even when no exam measurement exists yet.
    live_pos=list(db.scalars(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id==student.program_id).order_by(m.ProgramOutcome.academic_year,m.ProgramOutcome.code)).all())
    known={x["code"] for x in po_rows}
    latest_by_code={}
    for po in live_pos:
        if academic_year and po.academic_year>academic_year:
            continue
        latest_by_code[po.code]=po
    for code,po in latest_by_code.items():
        if code not in known:
            po_rows.append({"code":code,"description":po.description,"attainment_percent":0.0,"target_percent":60.0,"status":"not_measured"})

    components=[]
    for po in live_pos:
        if po.code not in {x["code"] for x in po_rows}:
            continue
        parent=next((x for x in po_rows if x["code"]==po.code),None)
        for comp in db.scalars(select(m.ProgramOutcomeComponent).where(m.ProgramOutcomeComponent.program_outcome_id==po.id).order_by(m.ProgramOutcomeComponent.code)).all():
            components.append({"program_outcome_code":po.code,"component_code":comp.code,"description":comp.description,"framework_component_code":comp.framework_component_code,
                "attainment_percent":parent["attainment_percent"] if parent else 0.0,"status":parent["status"] if parent else "not_measured","calculation":"inherited_from_program_outcome"})

    measured_po=[x for x in po_rows if x["status"]!="not_measured"]
    measured_lo=[x for x in all_learning_outcomes if x["status"]!="not_measured"]
    overall_source=measured_po or measured_lo
    overall=round(sum(x["attainment_percent"] for x in overall_source)/len(overall_source),2) if overall_source else 0.0
    risk_po=[x for x in po_rows if x["status"]=="needs_improvement"]
    risk_lo=[x for x in all_learning_outcomes if x["status"]=="needs_improvement"]
    strongest=max(overall_source,key=lambda x:float(x.get("attainment_percent") or 0),default=None)
    weakest=min(overall_source,key=lambda x:float(x.get("attainment_percent") or 0),default=None)
    verification_payload={"student_id":student.id,"student_no":student.student_no,"academic_year":academic_year,"overall":overall,"po":po_rows,"lo":all_learning_outcomes}
    verification_code=stable_sha256(verification_payload)[:16].upper()

    return {
        "student_id":student.id,"student_no":student.student_no,"full_name":student.full_name,
        "class_name":student.class_name,"program_id":student.program_id,
        "program_name":student.program.name if student.program else "","academic_year_cutoff":academic_year,
        "course_count":len(course_rows),"learning_outcomes":sorted(all_learning_outcomes,key=lambda x:(x["academic_year"],x["term"],x["course_code"],x["code"])),
        "program_outcomes":sorted(po_rows,key=lambda x:x["code"]),"program_outcome_components":components,
        "courses":sorted(course_rows,key=lambda x:(x["academic_year"],x["term"],x["course_code"])),
        "overall_attainment_percent":overall,"graduate_ready":bool(po_rows) and all(x["status"]=="achieved" for x in po_rows),
        "summary":{
            "measured_learning_outcomes":len(measured_lo),"risk_learning_outcomes":len(risk_lo),
            "measured_program_outcomes":len(measured_po),"risk_program_outcomes":len(risk_po),
            "strongest":strongest,"weakest":weakest,
        },
        "verification_code":verification_code,
        "calculation_note":"Onaylı/arşiv veya değerlendirme aşamasındaki sınavlarda soru→ÖÇ→PÇ zincirinden türetilir; dönem ağırlıkları sınav değerlendirme ağırlığına göre birleştirilir.",
    }


def build_student_outcome_card_pdf(db: Session, student_id: int, academic_year: str | None = None) -> tuple[bytes,str]:
    card=build_student_outcome_card(db,student_id,academic_year)
    _register_fonts()
    buf=BytesIO(); c=canvas.Canvas(buf,pagesize=A4)
    width,height=A4; left=42; right=width-42; page_w=right-left; y=height-42
    red=colors.HexColor('#9F1732'); red_dark=colors.HexColor('#741024'); ink=colors.HexColor('#222831')
    muted=colors.HexColor('#667085'); line=colors.HexColor('#E5E7EB'); soft=colors.HexColor('#F7F8FA')
    green=colors.HexColor('#18794E'); amber=colors.HexColor('#B56A10'); white=colors.white

    def wrap(text,max_width,font='DOU-Regular',size=7.4):
        words=str(text or '').split(); lines=[]; current=''
        for word in words:
            candidate=f'{current} {word}'.strip()
            if c.stringWidth(candidate,font,size)<=max_width or not current:
                current=candidate
            else:
                lines.append(current); current=word
        if current: lines.append(current)
        return lines or ['']

    def page_header(first=False):
        nonlocal y
        c.setFillColor(red); c.rect(0,height-10,width,10,fill=1,stroke=0)
        c.setFillColor(ink); c.setFont('DOU-Bold',12 if not first else 13.5); c.drawString(left,height-34,'DOĞUŞ ÜNİVERSİTESİ · DOU ASSESS')
        c.setFillColor(muted); c.setFont('DOU-Regular',7); c.drawRightString(right,height-33,f"Doğrulama: {card['verification_code']}")
        c.setStrokeColor(line); c.line(left,height-43,right,height-43); y=height-58

    def ensure(space=40):
        nonlocal y
        if y-space<48:
            c.showPage(); page_header(False)

    def section_title(kicker,title,desc=None):
        nonlocal y
        ensure(42)
        c.setFillColor(red); c.setFont('DOU-Bold',6.8); c.drawString(left,y,kicker.upper()); y-=12
        c.setFillColor(ink); c.setFont('DOU-Bold',10.5); c.drawString(left,y,title); y-=11
        if desc:
            c.setFillColor(muted); c.setFont('DOU-Regular',7)
            for ln in wrap(desc,page_w,'DOU-Regular',7)[:2]: c.drawString(left,y,ln); y-=9
        y-=4

    def summary_box(x,w,label,value,note='',accent=False):
        c.setFillColor(red if accent else white); c.setStrokeColor(red if accent else line)
        c.roundRect(x,y-48,w,48,7,fill=1,stroke=1)
        c.setFillColor(colors.HexColor('#F9E7EB') if accent else muted); c.setFont('DOU-Bold',6.2); c.drawString(x+9,y-12,label.upper())
        c.setFillColor(white if accent else ink); c.setFont('DOU-Bold',14.5); c.drawString(x+9,y-29,str(value))
        c.setFillColor(colors.HexColor('#F4CED6') if accent else muted); c.setFont('DOU-Regular',6.2); c.drawString(x+9,y-40,str(note)[:38])

    def outcome_row(code,desc,att,target,status,indent=0):
        nonlocal y
        ensure(43); x=left+indent; w=right-x
        tone=green if status=='achieved' else (colors.HexColor('#B7BEC8') if status=='not_measured' else amber)
        c.setFillColor(white); c.setStrokeColor(line); c.roundRect(x,y-32,w,32,6,fill=1,stroke=1)
        c.setFillColor(tone); c.roundRect(x+7,y-25,35,20,5,fill=1,stroke=0)
        c.setFillColor(white); c.setFont('DOU-Bold',7.5); c.drawCentredString(x+24.5,y-18,str(code)[:8])
        c.setFillColor(ink); c.setFont('DOU-Bold',7.3)
        dlines=wrap(desc,w-142,'DOU-Bold',7.3)[:1]; c.drawString(x+50,y-13,dlines[0] if dlines else '')
        c.setFillColor(muted); c.setFont('DOU-Regular',6.3)
        delta=float(att)-float(target); status_text='Hedef sağlandı' if status=='achieved' else ('Ölçülmedi' if status=='not_measured' else 'Gelişim gerekli')
        delta_text='ölçüm yok' if status=='not_measured' else f"{delta:+.1f} puan"
        c.drawString(x+50,y-24,f"{status_text} · hedef %{float(target):.1f} · {delta_text}")
        c.setFillColor(ink); c.setFont('DOU-Bold',10); c.drawRightString(right-10,y-18,f"%{float(att):.1f}")
        # progress line
        bx=x+50; bw=w-116; by=y-29
        c.setStrokeColor(colors.HexColor('#ECEFF2')); c.setLineWidth(3); c.line(bx,by,bx+bw,by)
        c.setStrokeColor(tone); c.line(bx,by,bx+bw*max(0,min(100,float(att)))/100,by)
        c.setStrokeColor(colors.HexColor('#3B4149')); c.setLineWidth(.8); tx=bx+bw*max(0,min(100,float(target)))/100; c.line(tx,by-3,tx,by+3)
        y-=39

    page_header(True)
    # Identity / hero area
    c.setFillColor(colors.HexColor('#FCF7F8')); c.setStrokeColor(colors.HexColor('#EADDE0')); c.roundRect(left,y-90,page_w,90,10,fill=1,stroke=1)
    initials=''.join([p[0] for p in str(card['full_name']).split()[:2]]).upper()[:2] or 'Ö'
    c.setFillColor(red); c.roundRect(left+14,y-72,54,54,12,fill=1,stroke=0)
    c.setFillColor(white); c.setFont('DOU-Bold',16); c.drawCentredString(left+41,y-50,initials)
    c.setFillColor(red); c.setFont('DOU-Bold',6.6); c.drawString(left+82,y-18,'ÖĞRENCİ BAŞARI & GELİŞİM PROFİLİ')
    c.setFillColor(ink); c.setFont('DOU-Bold',15); c.drawString(left+82,y-38,card['full_name'])
    c.setFillColor(muted); c.setFont('DOU-Regular',7.4); c.drawString(left+82,y-54,f"{card['student_no']} · {card['program_name']} · {card.get('class_name') or '-'}")
    c.drawString(left+82,y-67,f"Akademik dönem: {academic_year or 'Tüm dönemler'} · {card['course_count']} ders")
    # overall score panel
    score_x=right-110
    c.setFillColor(red_dark); c.roundRect(score_x,y-75,96,60,10,fill=1,stroke=0)
    c.setFillColor(colors.HexColor('#F5D7DE')); c.setFont('DOU-Bold',6.2); c.drawString(score_x+10,y-29,'GENEL ÇIKTI')
    c.setFillColor(white); c.setFont('DOU-Bold',19); c.drawString(score_x+10,y-51,f"%{card['overall_attainment_percent']:.1f}")
    c.setFillColor(colors.HexColor('#F4CED6')); c.setFont('DOU-Regular',6.4); c.drawString(score_x+10,y-65,'Mezuniyete hazır' if card['graduate_ready'] else 'Gelişim izleniyor')
    y-=108

    s=card['summary']; gap=7; bw=(page_w-gap*3)/4
    summary_box(left,bw,'Genel başarı',f"%{card['overall_attainment_percent']:.1f}",'çıktı erişim düzeyi',True)
    summary_box(left+(bw+gap),bw,'Ölçülen ÖÇ',s['measured_learning_outcomes'],f"{s['risk_learning_outcomes']} gelişim odağı")
    summary_box(left+2*(bw+gap),bw,'Ölçülen PÇ',s['measured_program_outcomes'],f"{s['risk_program_outcomes']} gelişim odağı")
    summary_box(left+3*(bw+gap),bw,'Ders kapsamı',card['course_count'],'sonuçlandırılmış ölçüm')
    y-=63

    # Strength / focus insight cards
    strong=s.get('strongest'); weak=s.get('weakest'); half=(page_w-gap)/2
    for idx,(title,item,tone) in enumerate([('EN GÜÇLÜ ALAN',strong,green),('GELİŞİM ODAĞI',weak,amber)]):
        x=left+idx*(half+gap)
        c.setFillColor(colors.HexColor('#F5FBF7') if idx==0 else colors.HexColor('#FFF9F1')); c.setStrokeColor(colors.HexColor('#D7EBDD') if idx==0 else colors.HexColor('#F2DFC4'))
        c.roundRect(x,y-47,half,47,7,fill=1,stroke=1)
        c.setFillColor(tone); c.setFont('DOU-Bold',6.3); c.drawString(x+10,y-13,title)
        c.setFillColor(ink); c.setFont('DOU-Bold',10); c.drawString(x+10,y-28,str((item or {}).get('code') or (item or {}).get('course_code') or '—'))
        c.setFillColor(muted); c.setFont('DOU-Regular',6.5); desc=str((item or {}).get('description') or 'Henüz yeterli ölçüm yok')
        c.drawString(x+10,y-39,(desc[:44]+'…') if len(desc)>45 else desc)
        if item: c.setFillColor(tone); c.setFont('DOU-Bold',8); c.drawRightString(x+half-10,y-27,f"%{float(item.get('attainment_percent') or 0):.1f}")
    y-=62

    section_title('PROGRAM ÇIKTILARI','PÇ başarı profili','Her program çıktısında öğrencinin doğrudan ölçülen erişim düzeyi, hedef ve hedef farkı.')
    for po in card['program_outcomes']:
        outcome_row(po['code'],po['description'],po['attainment_percent'],po['target_percent'],po['status'])

    section_title('DERS BAZLI GELİŞİM','Dersler ve öğrenim çıktıları','Her ders için bireysel başarı düzeyi ve gelişim gereken öğrenim çıktıları.')
    for course in card['courses']:
        ensure(55)
        score=float(course['course_attainment_percent'] or 0); risk=int(course['risk_count'] or 0)
        c.setFillColor(colors.HexColor('#FAFAFB')); c.setStrokeColor(line); c.roundRect(left,y-36,page_w,36,7,fill=1,stroke=1)
        c.setFillColor(red); c.setFont('DOU-Bold',6.2); c.drawString(left+10,y-11,f"{course['academic_year']} · {course['term']}")
        c.setFillColor(ink); c.setFont('DOU-Bold',8.3); c.drawString(left+10,y-24,f"{course['course_code']} · {course['course_name']}")
        c.setFillColor(muted); c.setFont('DOU-Regular',6.2); c.drawString(left+10,y-33,f"{course['exam_count']} ölçüm/sınav · {len(course['learning_outcomes'])} ÖÇ")
        c.setFillColor(amber if risk else green); c.setFont('DOU-Bold',10); c.drawRightString(right-10,y-20,f"%{score:.1f}")
        y-=44
        if course['learning_outcomes']:
            for lo in course['learning_outcomes']:
                outcome_row(lo['code'],lo['description'],lo['attainment_percent'],lo['target_percent'],lo['status'],8)
        else:
            c.setFillColor(muted); c.setFont('DOU-Regular',7); c.drawString(left+8,y,'Bu ders için bireysel ÖÇ ölçümü henüz oluşmadı.'); y-=18
        y-=3

    ensure(82)
    c.setStrokeColor(line); c.line(left,y,right,y); y-=12
    qr_payload=f"DOU-ASSESS|{card['student_no']}|{academic_year or 'ALL'}|{card['verification_code']}"
    qr=qrcode.make(qr_payload); qbuf=BytesIO(); qr.save(qbuf,format='PNG'); qbuf.seek(0)
    c.drawImage(ImageReader(qbuf),left,y-58,width=54,height=54,mask='auto')
    c.setFillColor(ink); c.setFont('DOU-Bold',7.5); c.drawString(left+66,y-15,'DOU Assess doğrulama bilgisi')
    c.setFillColor(muted); c.setFont('DOU-Regular',6.7); c.drawString(left+66,y-29,'Bu karne DOU Assess ölçme-değerlendirme kayıtlarından otomatik üretilmiştir.')
    c.drawString(left+66,y-41,f"Doğrulama kodu: {card['verification_code']}")
    c.drawString(left+66,y-53,f"Üretim zamanı: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    c.save(); payload=buf.getvalue()
    safe=re.sub(r'[^A-Za-z0-9_-]+','_',card['student_no'])
    return payload,f"DOU-Student-Outcome-Card-{safe}-{academic_year or 'all'}.pdf"

def snapshot_student_outcomes(db: Session, student_id: int, academic_year: str, snapshot_type: str="progress", freeze: bool=False) -> m.StudentOutcomeSnapshot:
    card=build_student_outcome_card(db,student_id,academic_year)
    digest=stable_sha256(card)
    latest=db.scalar(select(func.max(m.StudentOutcomeSnapshot.version_no)).where(m.StudentOutcomeSnapshot.student_id==student_id,m.StudentOutcomeSnapshot.academic_year==academic_year,m.StudentOutcomeSnapshot.snapshot_type==snapshot_type)) or 0
    obj=m.StudentOutcomeSnapshot(student_id=student_id,program_id=card["program_id"],academic_year=academic_year,snapshot_type=snapshot_type,version_no=int(latest)+1,payload=card,content_sha256=digest,frozen=freeze,frozen_at=datetime.now(timezone.utc) if freeze else None)
    db.add(obj); db.flush(); return obj


def quality_domain_dashboard(db: Session, academic_year: str, domain: str, program_id: int | None=None) -> dict[str,Any]:
    stmt=select(m.MissionActivity).where(m.MissionActivity.academic_year==academic_year,m.MissionActivity.domain==domain)
    if program_id is not None: stmt=stmt.where(m.MissionActivity.program_id==program_id)
    rows=list(db.scalars(stmt.order_by(m.MissionActivity.code)).all())
    completed=sum(1 for x in rows if x.status in {"completed","measured","closed"})
    measured=[x for x in rows if x.target_value is not None and x.actual_value is not None]
    target_attainment=round(sum(min(100.0,(float(x.actual_value)/float(x.target_value)*100.0) if float(x.target_value) else 100.0) for x in measured)/len(measured),2) if measured else 0.0
    return {"academic_year":academic_year,"domain":domain,"summary":{"activity_count":len(rows),"completed_count":completed,"evidence_linked_count":sum(1 for x in rows if x.evidence_refs),"target_attainment_percent":target_attainment,"total_budget":round(sum(float(x.budget_amount or 0) for x in rows),2),"participants":sum(int(x.participants or 0) for x in rows)},"activities":[model_dict(x) for x in rows]}


def compliance_matrix(db: Session, program_id: int, academic_year: str) -> dict[str,Any]:
    seed_builtin_frameworks(db); seed_report_templates(db)
    counts={
        "pea":db.scalar(select(func.count()).select_from(m.ProgramEducationalObjective).where(m.ProgramEducationalObjective.program_id==program_id,m.ProgramEducationalObjective.academic_year==academic_year)) or 0,
        "po_components":db.scalar(select(func.count()).select_from(m.ProgramOutcomeComponent).join(m.ProgramOutcome,m.ProgramOutcome.id==m.ProgramOutcomeComponent.program_outcome_id).where(m.ProgramOutcome.program_id==program_id)) or 0,
        "framework_snapshots":db.scalar(select(func.count()).select_from(m.QualityFrameworkSnapshot).where(m.QualityFrameworkSnapshot.program_id==program_id,m.QualityFrameworkSnapshot.academic_year==academic_year)) or 0,
        "budget":db.scalar(select(func.count()).select_from(m.QualityBudgetPlan).where(m.QualityBudgetPlan.program_id==program_id,m.QualityBudgetPlan.academic_year==academic_year)) or 0,
        "documents":db.scalar(select(func.count()).select_from(m.ControlledDocument).where((m.ControlledDocument.program_id==program_id)|(m.ControlledDocument.program_id.is_(None)))) or 0,
        "graduate_followups":db.scalar(select(func.count()).select_from(m.GraduateFollowup).join(m.GraduateRecord,m.GraduateRecord.id==m.GraduateFollowup.graduate_record_id).where(m.GraduateRecord.program_id==program_id)) or 0,
        "maintenance":db.scalar(select(func.count()).select_from(m.InfrastructureMaintenance).join(m.InfrastructureRecord,m.InfrastructureRecord.id==m.InfrastructureMaintenance.infrastructure_id).where(m.InfrastructureRecord.program_id==program_id)) or 0,
        "applications":db.scalar(select(func.count()).select_from(m.AccreditationApplication).where(m.AccreditationApplication.program_id==program_id,m.AccreditationApplication.academic_year==academic_year)) or 0,
    }
    rows=[
        ("Sürümlü kriter/ölçüt yönetimi",True,"Framework snapshot + SHA-256 freeze"),
        ("Özdeğerlendirme Raporu",True,"Kuruluş/sürüm template registry + DOCX builder"),
        ("KİDR 14 ölçüt / 46 alt ölçüt",len(YOKAK_2026_SUBCRITERIA)==46,"YÖKAK 14×46 criterion tree"),
        ("Ölçüt → alt ölçüt → kanıt",True,"criterion_code subcriterion seviyesinde desteklenir"),
        ("Program Eğitim Amaçları",True,"PEA CRUD + PEA→PÇ matrisi"),
        ("Program çıktıları",True,"Mevcut PÇ çekirdeği"),
        ("Program çıktısı bileşenleri",True,"PÇ component CRUD"),
        ("Her mezun öğrenci için çıktı başarısı",True,"Kümülatif öğrenci/mezun outcome card + freeze"),
        ("Doğrudan öğrenci çalışma kanıtı",True,"Kanıt motoru + öğrenci/sınav lineage"),
        ("Sınav/ödev/proje/rubrik kanıtı",True,"Kanıt kategorisi + rubrik/sınav çekirdeği"),
        ("Ders dosyası / ders bilgi paketi",True,"Standart course-file ZIP/DOCX endpoint"),
        ("Curriculum / AKTS kontrolü",True,"Curriculum checker + framework thresholds"),
        ("Öğretim elemanı CV",True,"YÖKSİS/ÜAK formatlı sürümlü CV snapshot"),
        ("Öğretim yükü",True,"Dönem/ders bazlı workload ledger + özet"),
        ("Mezun izleme",True,"1/3/5 yıl dahil longitudinal follow-up"),
        ("Paydaş geribildirimi",True,"Paydaş kaydı → kurul → PUKÖ zinciri"),
        ("Sanal Belge Odası",True,"MÜDEK BBO/FBO preset + ZIP export"),
        ("Kanıt rehberi/index",True,"Manifest/index + SHA-256"),
        ("PUKÖ/sürekli iyileştirme",True,"Mevcut closed-loop quality"),
        ("Kurul kararları",True,"Karar→PUKÖ→kanıt zinciri"),
        ("Altyapı/laboratuvar",True,"Bakım/İSG/erişilebilirlik/kapasite + maintenance"),
        ("Bütçe/parasal kaynak",True,"Program/yıl bütçe planı + kalemler"),
        ("Politika/yönerge/prosedür",True,"Controlled Document + revision/hash/approval"),
        ("Araştırma ve geliştirme",True,"YÖKAK mission activity + KPI/evidence"),
        ("Toplumsal katkı",True,"YÖKAK mission activity + KPI/evidence"),
        ("Uluslararasılaşma",True,"Faaliyet/partner/ülke/KPI/kanıt"),
        ("Saha ziyareti",True,"Lifecycle + evaluator workspace + ek belge talebi"),
        ("Değerlendirici erişimi",True,"Read-only workspace + frozen snapshot hash"),
        ("Başvuru/ÖDR/düzeltme takvimi",True,"Accreditation lifecycle state/tarihler"),
        ("Belge versiyon/hash/audit",True,"Controlled revisions + SHA-256 + AuditLog"),
    ]
    return {"program_id":program_id,"academic_year":academic_year,"summary":{"green":sum(1 for _,x,_ in rows if x),"total":len(rows),"runtime_data_counts":counts},"items":[{"requirement":a,"status":"green" if b else "red","implementation":c} for a,b,c in rows]}


def _safe_name(text: str) -> str:
    text=re.sub(r"[^A-Za-z0-9._ -]+","_",text or "")
    return text.strip(" ._")[:120] or "item"




def _mudek_room_target(code: str, room_type: str, layout: list[str]) -> str | None:
    c=(code or "").strip().upper()
    if room_type.upper()=="BBO":
        direct={
            "BBO.COMMON":"1 - Program Kanıt Belgeleri/0 - Ortak Derslerdeki Farklılıklar",
            "BBO.1.2":"1 - Program Kanıt Belgeleri/1 - Öğrenciler/1.2",
            "BBO.2.3":"1 - Program Kanıt Belgeleri/2 - Program Eğitim Amaçları/2.3",
            "BBO.3.2":"1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.2",
            "BBO.3.3.OTHER":"1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/Diğer Program Çıktıları",
            "BBO.4.1":"1 - Program Kanıt Belgeleri/4 - Sürekli İyileştirme/4.1",
            "BBO.4.2":"1 - Program Kanıt Belgeleri/4 - Sürekli İyileştirme/4.2",
            "BBO.5.5":"1 - Program Kanıt Belgeleri/5 - Eğitim Planı/5.5 - Ana Tasarım Deneyimi",
            "BBO.6":"1 - Program Kanıt Belgeleri/6 - Öğretim Kadrosu",
            "BBO.7.1":"1 - Program Kanıt Belgeleri/7 - Altyapı/7.1",
            "BBO.7.2":"1 - Program Kanıt Belgeleri/7 - Altyapı/7.2",
            "BBO.7.3":"1 - Program Kanıt Belgeleri/7 - Altyapı/7.3",
            "BBO.7.4":"1 - Program Kanıt Belgeleri/7 - Altyapı/7.4",
            "BBO.7.5":"1 - Program Kanıt Belgeleri/7 - Altyapı/7.5",
            "BBO.8":"1 - Program Kanıt Belgeleri/8 - Kurum Desteği ve Parasal Kaynaklar",
            "BBO.9":"1 - Program Kanıt Belgeleri/9 - Organizasyon ve Karar Alma Süreçleri",
            "BBO.REQUEST":"2 - Ziyaret Öncesi İstenilen Ek Bilgi ve Belgeler",
            "BBO.30DAY":"4 - 30-Gün Yanıtı Belgeleri",
        }
        if c.startswith("BBO.3.3.MC"):
            try: n=int(c.rsplit("MC",1)[1]); return f"1 - Program Kanıt Belgeleri/3 - Program Çıktıları/3.3/MÇ-{n}"
            except Exception: pass
        if c.startswith("EK1.") or c.startswith("EK1-"):
            return "1 - Program Kanıt Belgeleri/5 - Eğitim Planı/5.1 - EK-1 Disipline Özgü Eğitim Planı Konuları"
        if c in direct: return direct[c]
    else:
        fbo_exact={
            "FBO.LANG.INFO":"1 - Fakülte Kanıt Belgeleri/1 - Ortak Yabancı Dil Dersleri/Ders Bilgileri",
            "FBO.LANG.LAB":"1 - Fakülte Kanıt Belgeleri/1 - Ortak Yabancı Dil Dersleri/Laboratuvarlar",
            "FBO.LANG.REMOTE":"1 - Fakülte Kanıt Belgeleri/1 - Ortak Yabancı Dil Dersleri/Uzaktan Eğitim Süreci",
            "FBO.PHYS.INFO":"1 - Fakülte Kanıt Belgeleri/2 - Ortak Fizik Dersleri/Ders Bilgileri",
            "FBO.PHYS.LAB":"1 - Fakülte Kanıt Belgeleri/2 - Ortak Fizik Dersleri/Laboratuvarlar",
            "FBO.PHYS.EXP":"1 - Fakülte Kanıt Belgeleri/2 - Ortak Fizik Dersleri/Deney Listeleri ve Raporları",
            "FBO.PHYS.REMOTE":"1 - Fakülte Kanıt Belgeleri/2 - Ortak Fizik Dersleri/Uzaktan Eğitim Süreci",
            "FBO.CHEM.INFO":"1 - Fakülte Kanıt Belgeleri/3 - Ortak Kimya Dersleri/Ders Bilgileri",
            "FBO.CHEM.LAB":"1 - Fakülte Kanıt Belgeleri/3 - Ortak Kimya Dersleri/Laboratuvarlar",
            "FBO.CHEM.EXP":"1 - Fakülte Kanıt Belgeleri/3 - Ortak Kimya Dersleri/Deney Listeleri ve Raporları",
            "FBO.CHEM.REMOTE":"1 - Fakülte Kanıt Belgeleri/3 - Ortak Kimya Dersleri/Uzaktan Eğitim Süreci",
            "FBO.MATH.INFO":"1 - Fakülte Kanıt Belgeleri/4 - Ortak Matematik Dersleri/Ders Bilgileri",
            "FBO.MATH.REMOTE":"1 - Fakülte Kanıt Belgeleri/4 - Ortak Matematik Dersleri/Uzaktan Eğitim Süreci",
            "FBO.IT.INFO":"1 - Fakülte Kanıt Belgeleri/5 - Ortak Bilişim Dersleri/Ders Bilgileri",
            "FBO.IT.LAB":"1 - Fakülte Kanıt Belgeleri/5 - Ortak Bilişim Dersleri/Laboratuvarlar",
            "FBO.IT.REMOTE":"1 - Fakülte Kanıt Belgeleri/5 - Ortak Bilişim Dersleri/Uzaktan Eğitim Süreci",
            "FBO.ACCESS.FAC":"1 - Fakülte Kanıt Belgeleri/7 - Fakülte ve Üniversite Kapsamında Engelliler için Alınmış Olan Önlemler/Fakülte",
            "FBO.ACCESS.UNI":"1 - Fakülte Kanıt Belgeleri/7 - Fakülte ve Üniversite Kapsamında Engelliler için Alınmış Olan Önlemler/Üniversite",
            "FBO.SAFETY.FAC":"1 - Fakülte Kanıt Belgeleri/8 - Fakülte ve Üniversite Kapsamında Alınmış Olan Güvenlik Önlemleri/Fakülte",
            "FBO.SAFETY.UNI":"1 - Fakülte Kanıt Belgeleri/8 - Fakülte ve Üniversite Kapsamında Alınmış Olan Güvenlik Önlemleri/Üniversite",
            "FBO.LIB.INFO":"1 - Fakülte Kanıt Belgeleri/9 - Üniversite Kütüphane Olanakları/Yeterlik ve Kullanım",
            "FBO.LIB.REMOTE":"1 - Fakülte Kanıt Belgeleri/9 - Üniversite Kütüphane Olanakları/Uzaktan Erişim",
            "FBO.ITINFRA.INFO":"1 - Fakülte Kanıt Belgeleri/10 - Üniversite Bilişim Olanakları/Yeterlik ve Kullanım",
            "FBO.ITINFRA.REMOTE":"1 - Fakülte Kanıt Belgeleri/10 - Üniversite Bilişim Olanakları/Uzaktan Eğitim Süreci",
            "FBO.QUALITY":"1 - Fakülte Kanıt Belgeleri/12 - Diğer/Kalite Sistemi",
            "FBO.OTHER":"1 - Fakülte Kanıt Belgeleri/12 - Diğer/Diğer Belgeler",
            "FBO.REQUEST":"2 - Ziyaret Öncesi İstenilen Ek Bilgi ve Belgeler",
        }
        if c in fbo_exact: return fbo_exact[c]
        fbo_map={
            "FBO.LANG":"1 - Fakülte Kanıt Belgeleri/1 - Ortak Yabancı Dil Dersleri",
            "FBO.PHYS":"1 - Fakülte Kanıt Belgeleri/2 - Ortak Fizik Dersleri",
            "FBO.CHEM":"1 - Fakülte Kanıt Belgeleri/3 - Ortak Kimya Dersleri",
            "FBO.MATH":"1 - Fakülte Kanıt Belgeleri/4 - Ortak Matematik Dersleri",
            "FBO.IT":"1 - Fakülte Kanıt Belgeleri/5 - Ortak Bilişim Dersleri",
            "FBO.SOCIAL":"1 - Fakülte Kanıt Belgeleri/6 - Ortak Sosyal ve Spor Alanları",
            "FBO.SPORT":"1 - Fakülte Kanıt Belgeleri/6 - Ortak Sosyal ve Spor Alanları",
            "FBO.ACCESS":"1 - Fakülte Kanıt Belgeleri/7 - Fakülte ve Üniversite Kapsamında Engelliler için Alınmış Olan Önlemler",
            "FBO.SAFETY":"1 - Fakülte Kanıt Belgeleri/8 - Fakülte ve Üniversite Kapsamında Alınmış Olan Güvenlik Önlemleri",
            "FBO.LIB":"1 - Fakülte Kanıt Belgeleri/9 - Üniversite Kütüphane Olanakları",
            "FBO.ITINFRA":"1 - Fakülte Kanıt Belgeleri/10 - Üniversite Bilişim Olanakları",
            "FBO.HEALTH":"1 - Fakülte Kanıt Belgeleri/11 - Üniversite Sağlık Olanakları",
        }
        for prefix,target in fbo_map.items():
            if c==prefix or c.startswith(prefix+"."): return target
    return None

def build_evidence_room_zip(db: Session, program_id: int, academic_year: str, room_type: str="BBO", application_id: int | None=None, framework_id: int | None=None) -> tuple[bytes,str]:
    program=db.get(m.Program,program_id)
    if not program: raise ValueError("Program bulunamadı")
    seed_report_templates(db)
    family="MÜDEK" if room_type.upper() in {"BBO","FBO"} else "MEDEK"
    tpl=db.scalar(select(m.AccreditationReportTemplate).where(m.AccreditationReportTemplate.framework_family==family,m.AccreditationReportTemplate.report_type==room_type.upper()).order_by(m.AccreditationReportTemplate.id.desc()))
    layout=list(tpl.folder_layout or []) if tpl else []
    root_name=_safe_name(program.name if room_type.upper()=="BBO" else program.faculty or "Fakulte")
    buffer=BytesIO(); manifest=[]
    with zipfile.ZipFile(buffer,"w",zipfile.ZIP_DEFLATED) as z:
        for folder in layout: z.writestr(f"{root_name}/{folder.rstrip('/')}/.keep",b"")
        if room_type.upper()=="FBO" and (program.faculty or "").strip():
            faculty_program_ids=list(db.scalars(select(m.Program.id).where(m.Program.faculty==program.faculty)).all()) or [program_id]
            evidence=list(db.scalars(select(m.QualityEvidenceAsset).where(
                m.QualityEvidenceAsset.program_id.in_(faculty_program_ids),
                m.QualityEvidenceAsset.criterion_code.like("FBO.%"),
            ).order_by(m.QualityEvidenceAsset.id)).all())
        else:
            evidence=list(db.scalars(select(m.QualityEvidenceAsset).where(m.QualityEvidenceAsset.program_id==program_id).order_by(m.QualityEvidenceAsset.id)).all())
        program_names={x.id:x.name for x in db.scalars(select(m.Program).where(m.Program.id.in_({e.program_id for e in evidence}))).all()} if evidence else {}
        for ev in evidence:
            code=(ev.criterion_code or "GENEL").strip()
            target=_mudek_room_target(code,room_type.upper(),layout)
            if not target:
                target=next((x for x in layout if f"/{code} -" in x or x.split("/")[-1].startswith(code+" -")),None)
            if not target:
                target=next((x for x in layout if x.startswith("1 - ")),"1 - Program Kanıt Belgeleri") if layout else "Kanıtlar"
            entry={"id":ev.id,"source_program_id":ev.program_id,"source_program_name":program_names.get(ev.program_id,""),"criterion_code":code,"name":ev.original_name,"sha256":ev.sha256,"version_no":ev.version_no,"folder":target}
            manifest.append(entry)
            file_name=f"{ev.id:05d}_{_safe_name(ev.original_name)}"
            backing=Path(settings.evidence_storage_path) / "quality360" / ev.stored_name
            if backing.is_file():
                payload=backing.read_bytes()
                actual_hash=hashlib.sha256(payload).hexdigest()
                if actual_hash != ev.sha256:
                    raise ValueError(f"Kanıt bütünlük hatası: #{ev.id} SHA-256 eşleşmiyor")
                z.writestr(f"{root_name}/{target}/{file_name}",payload)
                entry["embedded"]=True
            else:
                entry["embedded"]=False
                z.writestr(f"{root_name}/{target}/{file_name}.reference.json",json.dumps(entry,ensure_ascii=False,indent=2).encode("utf-8"))
        z.writestr(f"{root_name}/KANIT-INDEKSI.json",json.dumps({"program":program.name,"academic_year":academic_year,"room_type":room_type.upper(),"template":model_dict(tpl) if tpl else None,"evidence":manifest},ensure_ascii=False,indent=2,default=str).encode("utf-8"))
        if room_type.upper() in {"BBO","FBO"}:
            readiness=mudek_evidence_room_readiness(db,program_id,academic_year,room_type.upper(),framework_id=framework_id,application_id=application_id)
            z.writestr(f"{root_name}/KANIT-HAZIRLIK-MATRISI.json",json.dumps(readiness,ensure_ascii=False,indent=2,default=str).encode("utf-8"))
        z.writestr(f"{root_name}/SHA256SUMS.txt","\n".join(f"{x['sha256']}  {x['id']:05d}_{x['name']}" for x in manifest).encode("utf-8"))
        if application_id:
            app=db.get(m.AccreditationApplication,application_id)
            if app: z.writestr(f"{root_name}/APPLICATION-SNAPSHOT.json",json.dumps(model_dict(app),ensure_ascii=False,indent=2,default=str).encode("utf-8"))
    return buffer.getvalue(),f"DOU-Assess-{room_type.upper()}-{_safe_name(program.code)}-{academic_year}.zip"


def build_course_file_docx(db: Session, course_id: int) -> tuple[bytes,str]:
    course=db.get(m.Course,course_id)
    if not course: raise ValueError("Ders bulunamadı")
    doc=Document(); doc.add_heading("DOU Assess — Standart Ders Dosyası",0)
    doc.add_paragraph(f"{course.code} · {course.name}")
    t=doc.add_table(rows=0,cols=2)
    for k,v in [("Program",course.program.name if course.program else ""),("Akademik Yıl",course.academic_year),("Dönem",course.term),("Öğretim Elemanı",course.instructor_name),("Ders Kodu",course.code)]:
        cells=t.add_row().cells; cells[0].text=k; cells[1].text=str(v or "")
    doc.add_heading("Öğrenim Çıktıları",1)
    for lo in course.learning_outcomes: doc.add_paragraph(f"{lo.code} — {lo.description} (hedef %{lo.target_percent:g})",style="List Bullet")
    doc.add_heading("ÖÇ → PÇ Katkı Matrisi",1)
    for lo in course.learning_outcomes:
        for mp in lo.mappings:
            doc.add_paragraph(f"{lo.code} → {mp.program_outcome.code}: {mp.contribution}/5",style="List Bullet")
    doc.add_heading("Ölçme-Değerlendirme",1)
    for exam in sorted(course.exams,key=lambda x:(x.exam_date or datetime.max.date(),x.id)):
        doc.add_paragraph(f"{exam.exam_type} · {exam.title} · ağırlık %{exam.assessment_weight_percent if exam.assessment_weight_percent is not None else '-'} · durum {exam.status}",style="List Bullet")
    items=list(db.scalars(select(m.CurriculumItem).where(m.CurriculumItem.program_id==course.program_id,m.CurriculumItem.academic_year==course.academic_year,m.CurriculumItem.course_code==course.code)).all())
    if items:
        doc.add_heading("Ders Bilgi Paketi / AKTS",1); x=items[0]
        doc.add_paragraph(f"AKTS: {x.ects:g} · Kategori: {x.course_category} · Sınıf: {x.class_level} · Kalite durumu: {x.quality_status}")
    doc.add_heading("Kalite ve Kanıt",1)
    cycles=list(db.scalars(select(m.QualityCycle).where(m.QualityCycle.program_id==course.program_id,m.QualityCycle.academic_year==course.academic_year)).all())
    doc.add_paragraph(f"Program PUKÖ kaydı: {len(cycles)}")
    doc.add_paragraph("Bu dosya DOU Assess içindeki sürümlü akademik kayıtlar ve ölçme kanıtlarından oluşturulmuştur.")
    out=BytesIO(); doc.save(out); return out.getvalue(),f"DOU-Assess-Ders-Dosyasi-{_safe_name(course.code)}-{course.academic_year}.docx"


def build_compliance_report_docx(db: Session, program_id: int, academic_year: str) -> tuple[bytes,str]:
    matrix=compliance_matrix(db,program_id,academic_year); program=db.get(m.Program,program_id)
    doc=Document(); doc.add_heading("DOU Assess — Akreditasyon Uyum Matrisi",0); doc.add_paragraph(f"{program.code} · {program.name} · {academic_year}")
    table=doc.add_table(rows=1,cols=3); h=table.rows[0].cells; h[0].text="Gereksinim";h[1].text="Durum";h[2].text="Sistem karşılığı"
    for x in matrix["items"]:
        c=table.add_row().cells;c[0].text=x["requirement"];c[1].text="YEŞİL" if x["status"]=="green" else "AÇIK";c[2].text=x["implementation"]
    doc.add_paragraph("Not: 'Yeşil', DOU Assess içinde ilgili gereksinimi işletmek için veri modeli/API/raporlama kabiliyetinin bulunduğunu ifade eder. Kuruma özgü resmî kaynak belgeler ve saha kabulü ayrıca sürüm snapshot'ına bağlanmalıdır.")
    out=BytesIO();doc.save(out);return out.getvalue(),f"DOU-Assess-Uyum-Matrisi-{_safe_name(program.code)}-{academic_year}.docx"


def _replace_docx_placeholders(doc: Document, values: dict[str, str]) -> None:
    """Replace simple {{KEY}} placeholders without rebuilding the official template layout."""
    def replace_in_paragraph(paragraph):
        full = "".join(run.text for run in paragraph.runs)
        if not full:
            return
        changed = full
        for key, value in values.items():
            changed = changed.replace("{{" + key + "}}", str(value or ""))
        if changed != full:
            # Preserve paragraph-level formatting as much as possible: keep the first run's formatting.
            if paragraph.runs:
                paragraph.runs[0].text = changed
                for run in paragraph.runs[1:]:
                    run.text = ""
            else:
                paragraph.text = changed
    for paragraph in doc.paragraphs:
        replace_in_paragraph(paragraph)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_in_paragraph(paragraph)


def build_template_report_docx(db: Session, template_id: int, program_id: int, academic_year: str) -> tuple[bytes, str]:
    tpl = db.get(m.AccreditationReportTemplate, template_id)
    program = db.get(m.Program, program_id)
    if not tpl:
        raise ValueError("Rapor şablonu bulunamadı")
    if not program:
        raise ValueError("Program bulunamadı")
    values = {
        "PROGRAM_CODE": program.code,
        "PROGRAM_NAME": program.name,
        "ACADEMIC_YEAR": academic_year,
        "FACULTY": program.faculty or "",
        "DEPARTMENT": program.department or "",
    }
    source_path = Path(settings.evidence_storage_path) / "quality360" / "official-templates" / (tpl.stored_name or "")
    if tpl.stored_name and source_path.is_file() and source_path.suffix.lower() == ".docx":
        payload = source_path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if tpl.source_sha256 and digest != tpl.source_sha256:
            raise ValueError("Resmî rapor şablonunun SHA-256 bütünlüğü bozulmuş")
        doc = Document(BytesIO(payload))
        _replace_docx_placeholders(doc, values)
    else:
        # When the organization publishes a non-DOCX source, retain the exact locked version metadata
        # and generate a structured working document. The official source file remains downloadable.
        doc = Document()
        doc.add_heading(tpl.title, 0)
        doc.add_paragraph(f"{program.code} · {program.name} · {academic_year}")
        doc.add_paragraph(f"Resmî profil: {tpl.framework_family} · {tpl.report_type} · sürüm {tpl.version}")
        if tpl.source_sha256:
            doc.add_paragraph(f"Kaynak SHA-256: {tpl.source_sha256}")
        for section in list(tpl.sections or []):
            code = section.get("code", "") if isinstance(section, dict) else ""
            name = section.get("name", str(section)) if isinstance(section, dict) else str(section)
            doc.add_heading(f"{code} {name}".strip(), 1)
            doc.add_paragraph("Kanıtlar, olgunluk değerlendirmesi, ilgili kurul kararı ve PUKÖ kayıtları DOU Assess üzerinden ilişkilendirilir.")
    out = BytesIO(); doc.save(out)
    return out.getvalue(), f"DOU-Assess-{_safe_name(tpl.framework_family)}-{_safe_name(tpl.report_type)}-{_safe_name(tpl.version)}-{_safe_name(program.code)}.docx"


def build_medek_institution_report_docx(db: Session, application_id: int) -> tuple[bytes, str, str]:
    app = db.get(m.AccreditationApplication, application_id)
    if not app:
        raise ValueError("Akreditasyon başvurusu bulunamadı")
    framework = db.get(m.QualityFrameworkProfile, app.framework_profile_id)
    if not framework or framework.framework_family != "MEDEK":
        raise ValueError("Kurum raporu yalnız MEDEK başvuruları için üretilebilir")
    program = db.get(m.Program, app.program_id)
    report = db.scalar(select(m.AccreditationFinalReport).where(m.AccreditationFinalReport.application_id == app.id))
    if not report:
        raise ValueError("Nihai rapor bulunamadı")
    pdr = list(db.scalars(select(m.MedekEvaluatorReportItem).where(
        m.MedekEvaluatorReportItem.application_id == app.id,
        m.MedekEvaluatorReportItem.report_phase == "final",
        m.MedekEvaluatorReportItem.status == "confirmed",
    ).order_by(m.MedekEvaluatorReportItem.criterion_code, m.MedekEvaluatorReportItem.id)).all())
    forms = list(db.scalars(select(m.MedekPdrFormAnalysis).where(
        m.MedekPdrFormAnalysis.application_id == app.id
    ).order_by(m.MedekPdrFormAnalysis.form_code, m.MedekPdrFormAnalysis.subject_ref)).all())
    decisions = list(db.scalars(select(m.AccreditationDecisionHistory).where(
        m.AccreditationDecisionHistory.application_id == app.id
    ).order_by(m.AccreditationDecisionHistory.id)).all())

    doc = Document()
    doc.add_heading("DOĞUŞ ÜNİVERSİTESİ — MEDEK KURUM RAPORU", 0)
    doc.add_paragraph(f"Program: {program.code} · {program.name}")
    doc.add_paragraph(f"Değerlendirme dönemi: {app.academic_year} · MEDEK {framework.version}")
    doc.add_paragraph(f"Başvuru türü: {app.application_type} · Yöntem: {app.evaluation_mode}")
    doc.add_heading("1. Nihai Karar Özeti", 1)
    doc.add_paragraph(f"Karar: {report.final_decision_code or 'Henüz girilmedi'}")
    if report.accreditation_start or report.accreditation_end:
        doc.add_paragraph(f"Geçerlilik: {report.accreditation_start or '-'} — {report.accreditation_end or '-'}")
    if report.accreditation_term_years is not None:
        doc.add_paragraph(f"Süre: {report.accreditation_term_years} yıl")
    if report.next_review_type:
        doc.add_paragraph(f"Sonraki değerlendirme: {report.next_review_type} · {report.next_review_due or '-'}")
    doc.add_paragraph(report.team_opinion or "Takım görüşü girilmedi.")
    doc.add_heading("2. Kurum Yanıtı Özeti", 1)
    doc.add_paragraph(report.institution_response_summary or "Kurum yanıt özeti girilmedi.")
    doc.add_heading("3. PDR Nihai Bulguları", 1)
    if not pdr:
        doc.add_paragraph("Onaylanmış nihai PDR maddesi bulunmamaktadır.")
    for x in pdr:
        doc.add_heading(f"{x.criterion_code or '-'} · {x.item_type}", 2)
        doc.add_paragraph(x.narrative or "")
        if x.assessment_value:
            doc.add_paragraph(f"Değerlendirme: {x.assessment_value}")
    doc.add_heading("4. FORM1 / FORM2 / FORM3", 1)
    table = doc.add_table(rows=1, cols=5)
    h=table.rows[0].cells
    for i,t in enumerate(["Form","Konu","Sonuç","Durum","Değerlendirici"]): h[i].text=t
    for x in forms:
        c=table.add_row().cells
        c[0].text=x.form_code; c[1].text=x.subject_ref; c[2].text=x.result; c[3].text=x.status; c[4].text=x.reviewer
    doc.add_heading("5. Karar Gerekçesi / Uygunluk Kontrolü", 1)
    basis = report.decision_basis or {}
    for k,v in basis.items():
        doc.add_paragraph(f"{k}: {v}")
    doc.add_heading("6. Karar Geçmişi", 1)
    for x in decisions:
        doc.add_paragraph(f"{x.created_at} · {x.action} · {x.decision_code} · {x.note}")
    doc.add_paragraph("Bu belge DOU Assess kayıtlarının kurum içi izlenebilir çıktısıdır; MEDEK/MEK'in resmî karar belgesinin yerine geçmez.")
    out=BytesIO(); doc.save(out); payload=out.getvalue(); digest=hashlib.sha256(payload).hexdigest()
    return payload, f"DOU-Assess-MEDEK-Kurum-Raporu-{_safe_name(program.code)}-{_safe_name(app.academic_year)}.docx", digest


def build_medek_institution_report_pdf(db: Session, application_id: int) -> tuple[bytes, str, str]:
    app = db.get(m.AccreditationApplication, application_id)
    if not app:
        raise ValueError("Akreditasyon başvurusu bulunamadı")
    framework = db.get(m.QualityFrameworkProfile, app.framework_profile_id)
    if not framework or framework.framework_family != "MEDEK":
        raise ValueError("Kurum raporu yalnız MEDEK başvuruları için üretilebilir")
    program = db.get(m.Program, app.program_id)
    report = db.scalar(select(m.AccreditationFinalReport).where(m.AccreditationFinalReport.application_id == app.id))
    if not report:
        raise ValueError("Nihai rapor bulunamadı")
    pdr = list(db.scalars(select(m.MedekEvaluatorReportItem).where(
        m.MedekEvaluatorReportItem.application_id == app.id,
        m.MedekEvaluatorReportItem.report_phase == "final",
        m.MedekEvaluatorReportItem.status == "confirmed",
    ).order_by(m.MedekEvaluatorReportItem.criterion_code, m.MedekEvaluatorReportItem.id)).all())
    out=BytesIO(); c=canvas.Canvas(out,pagesize=A4); width,height=A4
    _register_fonts(); font="DOU-Regular"
    y=height-45
    def line(text, size=9, gap=14):
        nonlocal y
        if y < 55:
            c.showPage(); y=height-45
        c.setFont(font, size)
        txt=str(text or "")
        # simple deterministic wrapping
        chunks=[]
        while len(txt)>105:
            cut=txt.rfind(" ",0,105)
            if cut<40: cut=105
            chunks.append(txt[:cut]); txt=txt[cut:].lstrip()
        chunks.append(txt)
        for chunk in chunks:
            c.drawString(42,y,chunk); y-=gap
    line("DOĞUŞ ÜNİVERSİTESİ — MEDEK KURUM RAPORU",13,18)
    line(f"Program: {program.code} · {program.name}")
    line(f"Dönem: {app.academic_year} · MEDEK {framework.version}")
    line(f"Karar: {report.final_decision_code or 'Henüz girilmedi'}")
    line(f"Geçerlilik: {report.accreditation_start or '-'} — {report.accreditation_end or '-'}")
    line(f"Sonraki değerlendirme: {report.next_review_type or '-'} · {report.next_review_due or '-'}")
    y-=6; line("Takım görüşü",11,16); line(report.team_opinion or "Takım görüşü girilmedi.")
    y-=6; line("Kurum yanıt özeti",11,16); line(report.institution_response_summary or "Kurum yanıt özeti girilmedi.")
    y-=6; line("Nihai PDR bulguları",11,16)
    for x in pdr:
        line(f"{x.criterion_code or '-'} · {x.item_type} · {x.assessment_value or '-'}")
        line(x.narrative or "",8,12)
    line("Bu belge DOU Assess kurum içi izlenebilirlik çıktısıdır; MEDEK/MEK resmî karar belgesi değildir.",8,12)
    c.save(); payload=out.getvalue(); digest=hashlib.sha256(payload).hexdigest()
    return payload, f"DOU-Assess-MEDEK-Kurum-Raporu-{_safe_name(program.code)}-{_safe_name(app.academic_year)}.pdf", digest
