"""Turkish column headers and values for every Excel template/export.

Templates are generated with Turkish headers and Turkish enum values. Importers accept BOTH the Turkish
headers/values and the old English ones, so existing files and integrations keep working.
Everything internal (importers, validators, API) keeps using the English keys.
"""
from __future__ import annotations

import re
from typing import Any

# internal key -> Turkish header shown in Excel
HEADER_TR: dict[str, str] = {
    # ortak
    "program_code": "Program Kodu", "program_name": "Program Adı", "faculty": "Fakülte", "department": "Bölüm",
    "external_id": "Harici Kimlik", "course_code": "Ders Kodu", "course_name": "Ders Adı", "academic_year": "Akademik Yıl",
    "term": "Dönem", "instructor_name": "Öğretim Elemanı Adı", "instructor_email": "Öğretim Elemanı E-posta",
    "student_no": "Öğrenci No", "full_name": "Ad Soyad", "class_name": "Sınıf", "email": "E-posta", "display_name": "Görünen Ad",
    "role": "Rol", "is_active": "Aktif mi", "notes": "Notlar", "name": "Ad", "title": "Unvan / Başlık", "owner": "Sorumlu",
    "due_date": "Son Tarih", "status": "Durum", "location": "Konum", "capacity": "Kapasite", "feedback": "Geri Bildirim",
    "evidence_ref": "Kanıt Referansı", "evidence_refs": "Kanıt Referansları", "subject": "Konu", "organization": "Kurum",
    # sınav / katılım / puanlama / kalite aksiyonu
    "exam_id": "Sınav No", "attendance_status": "Katılım Durumu", "attendance_note": "Katılım Notu",
    "question_order": "Soru Sırası", "answer_text": "Öğrenci Cevabı", "rubric_scores": "Rubrik Puanları",
    "outcome_code": "ÖÇ Kodu", "action_text": "Aksiyon", "baseline_percent": "Başlangıç %", "target_percent": "Hedef Yüzdesi",
    "actual_percent": "Gerçekleşen %", "verification_method": "Doğrulama Yöntemi", "effectiveness_status": "Etkinlik Durumu",
    "closure_note": "Kapanış Notu",
    # müfredat
    "class_level": "Sınıf Düzeyi", "ects": "AKTS", "course_category": "Ders Kategorisi", "is_professional": "Mesleki mi",
    "is_program_specific": "Programa Özgü mü", "is_external_stakeholder_supported": "Dış Paydaş Destekli mi",
    "is_applied_or_current_tech": "Uygulamalı / Güncel Teknoloji mi", "quality_status": "Kalite Durumu",
    # paydaş / mezun / kadro / altyapı
    "stakeholder_type": "Paydaş Türü", "engagement_type": "Katılım Türü", "engagement_date": "Katılım Tarihi",
    "resulting_action": "Sonuçlanan Aksiyon", "graduate_key": "Mezun Kodu", "graduation_year": "Mezuniyet Yılı",
    "employment_status": "İstihdam Durumu", "employer": "İşveren", "sector": "Sektör", "job_title": "Görev Unvanı",
    "related_field": "Alanla İlgili mi", "survey_date": "Anket Tarihi", "employment_type": "Çalışma Türü", "expertise": "Uzmanlık",
    "highest_degree": "En Yüksek Derece", "industry_experience_years": "Sektör Deneyimi (Yıl)", "weekly_course_hours": "Haftalık Ders Saati",
    "infrastructure_type": "Altyapı Türü", "accessibility_status": "Erişilebilirlik Durumu", "isg_status": "İSG Durumu",
    "last_review_date": "Son Kontrol Tarihi",
    # PUKÖ / kurul
    "criterion_code": "Ölçüt Kodu", "plan_text": "Planla", "do_text": "Uygula", "check_text": "Kontrol Et", "act_text": "Önlem Al",
    "body_type": "Kurul Türü", "meeting_date": "Toplantı Tarihi", "meeting_no": "Toplantı No", "decision_no": "Karar No",
    "decision_text": "Karar Metni", "related_criterion": "İlgili Ölçüt", "source_stakeholder_id": "Kaynak Paydaş No",
    # akademik veri çalışma kitabı
    "learning_outcome_code": "Öğrenme Çıktısı Kodu", "learning_outcome_description": "Öğrenme Çıktısı Açıklaması",
    "target": "Hedef %", "program_outcome_code": "Program Çıktısı Kodu", "program_outcome_description": "Program Çıktısı Açıklaması",
    "contribution": "Katkı Düzeyi (1-5)", "exam_title": "Sınav Adı", "exam_type": "Sınav Türü", "exam_date": "Sınav Tarihi",
    "start_time": "Başlangıç Saati", "duration_minutes": "Süre (dk)", "assessment_weight_percent": "Ders Notuna Etkisi %",
    "booklet_count": "Kitapçık Sayısı", "instructions": "Sınav Talimatı", "staff_notes": "Gözetmen Notları", "order_no": "Soru No",
    "question_type": "Soru Türü", "question_text": "Soru Metni", "points": "Puan", "learning_outcome_codes": "Öğrenme Çıktısı Kodları",
    "choice_A": "A Şıkkı", "choice_B": "B Şıkkı", "choice_C": "C Şıkkı", "choice_D": "D Şıkkı", "choice_E": "E Şıkkı",
    "correct_answer": "Doğru Cevap", "expected_answer": "Beklenen Cevap", "rubric": "Rubrik",
    # soru havuzu
    "default_points": "Varsayılan Puan", "answer_lines": "Cevap Satırı", "tags": "Etiketler", "topic": "Konu Başlığı", "unit": "Ünite",
    "difficulty": "Zorluk", "bloom_level": "Bloom Düzeyi", "author": "Yazar", "reviewer": "İnceleyen",
    "add_to_bank": "Soru Havuzuna Ekle", "sync_students": "Öğrencileri Sınava Ekle",
}

# internal value (English token) -> Turkish value, per field. A field may also list kind-specific maps via ENUM_KIND.
_ATT = {"attended": "Katıldı", "absent": "Gelmedi", "excused": "Mazeretli", "invalidated": "Geçersiz"}
_QUALITY = {"not_started": "Başlanmadı", "planned": "Planlandı", "implemented": "Uygulanıyor", "measured": "Ölçülüyor", "improved": "İyileştirildi"}
_QUALITY_ALIAS = {"Eksik / Başlanmadı": "not_started", "İzleniyor / Ölçülüyor": "measured", "İyileştirildi / Kanıtlı": "improved"}
_IMPROVEMENT = {"open": "Açık", "in_progress": "Devam Ediyor", "done": "Tamamlandı", "cancelled": "İptal"}
_PUKO = {"planned": "Planlandı", "doing": "Uygulanıyor", "checking": "Kontrol Ediliyor", "acting": "Önlem Alınıyor", "closed": "Kapandı"}
_EFFECT = {"pending": "Bekliyor", "effective": "Etkili", "partially_effective": "Kısmen Etkili", "ineffective": "Etkisiz"}
_ROLE = {"instructor": "Öğretim Elemanı", "program_head": "Program Başkanı", "quality": "Kalite"}
_QTYPE = {"mcq": "Çoktan Seçmeli", "classic": "Klasik", "truefalse": "Doğru/Yanlış"}
_DIFF = {"easy": "Kolay", "medium": "Orta", "hard": "Zor"}
_BLOOM = {"remember": "Hatırlama", "understand": "Anlama", "apply": "Uygulama", "analyze": "Analiz", "evaluate": "Değerlendirme", "create": "Yaratma"}

ENUM_BY_FIELD: dict[str, dict[str, str]] = {
    "attendance_status": _ATT, "quality_status": _QUALITY, "accessibility_status": _QUALITY, "isg_status": _QUALITY,
    "effectiveness_status": _EFFECT, "status": {"draft": "Taslak"}, "role": _ROLE, "question_type": _QTYPE, "difficulty": _DIFF, "bloom_level": _BLOOM,
}
ENUM_BY_KIND_FIELD: dict[tuple[str, str], dict[str, str]] = {
    ("improvements", "status"): _IMPROVEMENT, ("quality_cycles", "status"): _PUKO,
    ("stakeholders", "quality_status"): _QUALITY, ("governance", "status"): _QUALITY,
}


def _fold(text: Any) -> str:
    s = str(text if text is not None else "").replace("İ", "i").replace("I", "ı").lower()
    s = s.translate(str.maketrans("ığüşöçâîû", "igusocaiu"))
    return re.sub(r"[^a-z0-9]+", "", s)


_HEADER_LOOKUP: dict[str, str] = {}
for _key, _tr in HEADER_TR.items():
    _HEADER_LOOKUP.setdefault(_fold(_key), _key)
    _HEADER_LOOKUP.setdefault(_fold(_tr), _key)
# a few harmless extra spellings people type
_HEADER_LOOKUP.update({_fold(k): v for k, v in {"Hedef": "target", "Ogrenci No": "student_no", "Sinav No": "exam_id", "Ad Soyad (bilgi)": "full_name"}.items()})


# the same internal key reads differently in different templates
KIND_HEADER_TR: dict[tuple[str, str], str] = {
    ("faculty", "title"): "Unvan", ("quality_cycles", "title"): "Başlık", ("stakeholders", "name"): "Paydaş Adı",
    ("infrastructure", "name"): "Altyapı Adı",
}
for (_k, _f), _label in KIND_HEADER_TR.items():
    _HEADER_LOOKUP.setdefault(_fold(_label), _f)
_HEADER_LOOKUP.update({_fold("Unvan"): "title", _fold("Başlık"): "title"})


def header_tr(key: str, kind: str | None = None) -> str:
    return KIND_HEADER_TR.get((kind or "", key)) or HEADER_TR.get(key, key)


def canonical_header(text: Any) -> str:
    """Turkish or English header -> internal English key. Unknown headers are returned stripped, unchanged."""
    raw = str(text if text is not None else "").strip()
    return _HEADER_LOOKUP.get(_fold(raw), raw)


def normalize_headers(headers: list[Any]) -> list[str]:
    return [canonical_header(h) for h in headers]


def _enum(field: str, kind: str | None) -> dict[str, str] | None:
    return ENUM_BY_KIND_FIELD.get((kind or "", field)) or ENUM_BY_FIELD.get(field)


def value_tr(field: str, value: Any, kind: str | None = None) -> Any:
    table = _enum(field, kind)
    if table and isinstance(value, str) and value in table:
        return table[value]
    return value


def canonical_value(field: str, value: Any, kind: str | None = None) -> Any:
    """Turkish (or English) enum text -> internal English token; anything else is returned unchanged."""
    table = _enum(field, kind)
    if not table or not isinstance(value, str):
        return value
    f = _fold(value)
    for en, tr in table.items():
        if f in (_fold(en), _fold(tr)):
            return en
    if field in ("quality_status", "accessibility_status", "isg_status"):
        for tr_label, en in _QUALITY_ALIAS.items():
            if f == _fold(tr_label):
                return en
    return value


_KEY_RX = re.compile(r"\b(" + "|".join(sorted((re.escape(k) for k in HEADER_TR), key=len, reverse=True)) + r")\b")


_WORDS = {"mcq": "çoktan seçmeli", "classic": "klasik", "easy": "kolay", "medium": "orta", "hard": "zor",
          "attended": "Katıldı", "absent": "Gelmedi", "excused": "Mazeretli", "invalidated": "Geçersiz",
          "open": "Açık", "in_progress": "Devam Ediyor", "done": "Tamamlandı", "instructor": "Öğretim Elemanı",
          "program_head": "Program Başkanı", "quality": "Kalite"}
_WORD_RX = re.compile(r"\b(" + "|".join(sorted(map(re.escape, _WORDS), key=len, reverse=True)) + r")\b")


def localize(text: str) -> str:
    """Replace English column keys / enum tokens inside an error message with Turkish names."""
    text = _localize_keys(text)
    return _WORD_RX.sub(lambda m: _WORDS[m.group(1)], text)


def _localize_keys(text: str) -> str:
    return _KEY_RX.sub(lambda m: f"'{header_tr(m.group(1))}'" if not text[max(0, m.start() - 1):m.start()] == "'" else header_tr(m.group(1)), text)


# ---------------------------------------------------------------- exports: English code values -> Turkish
EXPORT_TOKENS = {
    "draft": "Taslak", "ready": "Hazır", "grading": "Puanlama", "approved": "Onaylı", "archived": "Arşiv",
    "achieved": "Hedefe ulaşıldı", "needs_improvement": "İyileştirme gerekli",
    "easy": "Kolay", "medium": "Orta", "hard": "Zor", "low": "Düşük", "caution": "Dikkatli yorumlayın", "usable": "Güvenilir",
    "small_sample": "Küçük örneklem", "negative_discrimination": "Negatif ayırt edicilik", "low_discrimination": "Düşük ayırt edicilik",
    "high_blank_rate": "Yüksek boş bırakma", "too_easy": "Çok kolay", "too_hard": "Çok zor",
    "open": "Açık", "closed": "Kapandı", "pending": "Bekliyor", "passed": "Geçti", "failed": "Kaldı", "in_progress": "Devam ediyor",
    "done": "Tamamlandı", "attended": "Katıldı", "absent": "Gelmedi", "excused": "Mazeretli", "invalidated": "Geçersiz",
    "mcq": "Çoktan seçmeli", "classic": "Klasik", "planned": "Planlandı", "implemented": "Uygulanıyor", "measured": "Ölçülüyor",
    "improved": "İyileştirildi", "not_started": "Başlanmadı", "high": "Yüksek", "no_exam": "Sınav yok", "complete": "Tamam",
    "remember": "Hatırlama", "understand": "Anlama", "apply": "Uygulama", "analyze": "Analiz", "evaluate": "Değerlendirme", "create": "Yaratma",
}
_TOKEN_CELL = re.compile(r"^[a-z_]+(?:[ ,;|/]+[a-z_]+)*$")


def export_tr(text: str) -> str:
    """'needs_improvement' / 'small_sample, high_blank_rate' -> Turkish. Normal Turkish text is left alone."""
    if not isinstance(text, str) or len(text) > 120 or not _TOKEN_CELL.match(text):
        return text
    return re.sub(r"[a-z_]+", lambda m: EXPORT_TOKENS.get(m.group(0), m.group(0)), text)


def localize_workbook(wb) -> None:
    """Translate English code values in every text cell of a workbook (exports only)."""
    for ws in wb:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    new = export_tr(cell.value)
                    if new != cell.value:
                        cell.value = new
