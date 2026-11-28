from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .excel_tr import canonical_header, canonical_value, header_tr, localize, value_tr


TEMPLATES: dict[str, dict[str, Any]] = {
    "exam_students": {
        "sheet": "Sinav_Ogrencileri",
        "title": "Sınav Öğrencileri & Katılım",
        "columns": ["exam_id", "student_no", "attendance_status", "attendance_note"],
        "sample": [1, "BT260001", "attended", ""],
        "file": "Sinav-Ogrencileri-Katilim-Sablonu",
        "help": "Katılım Durumu: Katıldı | Gelmedi | Mazeretli | Geçersiz. Her satır bir öğrencidir; Sınav No sistemdeki sınav numarasıdır.",
    },
    "classic_grades": {
        "sheet": "Klasik_Puanlama",
        "title": "Klasik Rubrik Puanlama",
        "columns": ["exam_id", "student_no", "question_order", "answer_text", "rubric_scores"],
        "sample": [1, "BT260001", 1, "Öğrenci cevabı", "olcut1=3;olcut2=2"],
        "file": "Klasik-Puanlama-Sablonu",
        "help": "Rubrik Puanları: rubrik ölçüt kodu=puan;... biçiminde yazılır. Toplam puanı sistem hesaplar.",
    },
    "improvements": {
        "sheet": "Kalite_Aksiyonlari",
        "title": "Kalite / PUKÖ Aksiyonları",
        "columns": ["exam_id", "outcome_code", "action_text", "owner", "due_date", "status", "baseline_percent", "target_percent", "actual_percent", "verification_method", "effectiveness_status", "closure_note"],
        "sample": [1, "Ö1", "Log analizi uygulaması artırılacak", "Program Başkanı", "2026-12-30", "open", 55, 70, "", "Sonraki sınav ÖÇ ölçümü", "pending", ""],
        "file": "Kalite-Aksiyonlari-Sablonu",
        "help": "Durum: Açık | Devam Ediyor | Tamamlandı. Tamamlandı için Gerçekleşen %, Doğrulama Yöntemi ve Etkinlik Durumu (Etkili | Kısmen Etkili | Etkisiz) zorunludur.",
    },
    "users_roles": {
        "sheet": "Kullanicilar_Roller",
        "title": "Kullanıcı & Akademik Rol",
        "columns": ["email", "display_name", "role", "program_code", "course_code", "academic_year", "term", "is_active"],
        "sample": ["hoca@dogus.edu.tr", "Öğr. Gör. Örnek", "instructor", "", "BGT 108", "2026-2027", "Güz", "Evet"],
        "file": "Kullanici-Rol-Sablonu",
        "help": "Rol: Öğretim Elemanı | Program Başkanı | Kalite. Sistem yöneticisi Excel üzerinden atanmaz.",
    },
    "curriculum": {
        "sheet": "Mufredat", "title": "Müfredat & AKTS Denetimi",
        "columns": ["program_code","academic_year","term","class_level","course_code","course_name","ects","course_category","is_professional","is_program_specific","is_external_stakeholder_supported","is_applied_or_current_tech","quality_status","notes"],
        "sample": ["IAT","2026-2027","Güz","1. Sınıf","IAT 1012","Yazılım Geliştirme Yöntemleri",6,"Programa / Alana Özgü Mesleki","Evet","Evet","Hayır","Evet","implemented",""],
        "file": "Mufredat-AKTS-Sablonu",
        "help": "Dönem: Güz/Bahar/Yaz; Sınıf Düzeyi: 1.–4. Sınıf. Evet/Hayır alanları MEDEK AKTS denetiminde kullanılır.",
    },
    "stakeholders": {
        "sheet": "Paydaslar", "title": "Paydaş Kayıtları",
        "columns": ["program_code","stakeholder_type","name","organization","engagement_type","engagement_date","feedback","resulting_action","quality_status","evidence_ref"],
        "sample": ["IAT","Sektör Temsilcisi","Örnek Paydaş","Örnek Teknoloji","Danışma Kurulu","2026-09-01","Bulut dersi önerildi","Müfredata değerlendirme maddesi açıldı","implemented","KANIT-001"],
        "file": "Paydas-Kayitlari-Sablonu",
        "help": "Paydaş Türü ve Katılım Türü Kalite 360 kataloglarından seçilmelidir. Kalite Durumu: Başlanmadı | Planlandı | Uygulanıyor | Ölçülüyor | İyileştirildi.",
    },
    "graduates": {
        "sheet": "Mezunlar", "title": "Mezun İzleme",
        "columns": ["program_code","graduate_key","full_name","graduation_year","employment_status","employer","sector","job_title","related_field","survey_date","notes"],
        "sample": ["IAT","MZ-2026-001","Örnek Mezun",2026,"Çalışıyor - Alanında","Örnek AŞ","BT","Ağ Uzmanı","Evet","2026-09-01",""],
        "file": "Mezun-Izleme-Sablonu",
        "help": "Mezun Kodu program içinde benzersizdir. İstihdam Durumu katalogdan seçilir.",
    },
    "faculty": {
        "sheet": "Ogretim_Kadrosu", "title": "Öğretim Kadrosu",
        "columns": ["program_code","title","full_name","email","employment_type","expertise","highest_degree","industry_experience_years","weekly_course_hours","quality_status"],
        "sample": ["IAT","Öğr. Gör.","Örnek Öğretim Elemanı","ornek@dogus.edu.tr","Tam Zamanlı","Ağ ve sistem yönetimi","Yüksek Lisans",5,15,"implemented"],
        "file": "Ogretim-Kadrosu-Sablonu",
        "help": "Unvan ve Çalışma Türü Kalite 360 kataloglarından seçilir.",
    },
    "infrastructure": {
        "sheet": "Altyapi", "title": "Laboratuvar & Altyapı",
        "columns": ["program_code","infrastructure_type","name","location","capacity","quality_status","accessibility_status","isg_status","last_review_date","notes"],
        "sample": ["IAT","Bilgisayar Laboratuvarı","Ağ Laboratuvarı","B Blok",24,"implemented","measured","measured","2026-09-01",""],
        "file": "Altyapi-Sablonu",
        "help": "Kalite, Erişilebilirlik ve İSG durumları: Başlanmadı | Planlandı | Uygulanıyor | Ölçülüyor | İyileştirildi.",
    },
    "quality_cycles": {
        "sheet": "PUKO", "title": "PUKÖ Döngüleri",
        "columns": ["program_code","academic_year","criterion_code","title","plan_text","do_text","check_text","act_text","owner","due_date","status","evidence_refs"],
        "sample": ["IAT","2026-2027","4","Sektör geri bildirim döngüsü","Planlandı","Uygulandı","Ölçüldü","Revize edildi","Program Başkanı","2026-12-31","acting","KANIT-001;KANIT-002"],
        "file": "PUKO-Dongu-Sablonu",
        "help": "Durum: Planlandı | Uygulanıyor | Kontrol Ediliyor | Önlem Alınıyor | Kapandı. Kanıt Referansları noktalı virgülle ayrılabilir.",
    },
    "governance": {
        "sheet": "Kurul_Karar", "title": "Kurul & Karar Zinciri",
        "columns": ["program_code","body_type","meeting_date","meeting_no","decision_no","subject","decision_text","related_criterion","source_stakeholder_id","status","evidence_ref"],
        "sample": ["IAT","Program Kurulu","2026-09-01","2026-01","01","Müfredat güncellemesi","Paydaş önerisi görüşülerek kabul edildi","5","","implemented","KANIT-003"],
        "file": "Kurul-Karar-Sablonu",
        "help": "Kurul Türü katalogdan seçilir; Toplantı No + Karar No program içinde benzersizdir. Durum: Başlanmadı | Planlandı | Uygulanıyor | Ölçülüyor | İyileştirildi.",
    },
}


def template_bytes(kind: str) -> bytes:
    cfg = TEMPLATES[kind]
    wb = Workbook()
    ws = wb.active
    ws.title = cfg["sheet"]
    ws.append([header_tr(c, kind) for c in cfg["columns"]])
    ws.append([value_tr(c, v, kind) for c, v in zip(cfg["columns"], cfg["sample"])])
    header = ws[1]
    fill = PatternFill("solid", fgColor="8F0E21")
    for cell in header:
        cell.fill = fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"
    for idx, col in enumerate(cfg["columns"], 1):
        values = [header_tr(str(col), kind), str(value_tr(str(col), cfg["sample"][idx-1], kind) if idx-1 < len(cfg["sample"]) else "")]
        width = min(42, max(12, max(len(v) for v in values) + 3))
        ws.column_dimensions[get_column_letter(idx)].width = width
    info = wb.create_sheet("KILAVUZ")  # "kılavuz" (guide) sheet
    info["A1"] = cfg["title"]
    info["A1"].font = Font(size=16, bold=True, color="8F0E21")
    info["A3"] = cfg["help"]
    info["A3"].alignment = Alignment(wrap_text=True)
    info.column_dimensions["A"].width = 110
    out = BytesIO(); wb.save(out); return out.getvalue()


def parse_workbook(kind: str, data: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    cfg = TEMPLATES[kind]
    errors: list[str] = []
    try:
        wb = load_workbook(BytesIO(data), data_only=True)
    except Exception as exc:
        return [], [f"Excel açılamadı: {exc}"]
    if cfg["sheet"] not in wb.sheetnames:
        return [], [f"{cfg['sheet']} sayfası bulunamadı"]
    ws = wb[cfg["sheet"]]
    headers = [canonical_header(c.value) for c in ws[1]]  # accepts Turkish and the older English headers
    missing = [c for c in cfg["columns"] if c not in headers]
    if missing:
        return [], ["Eksik sütunlar: " + ", ".join(header_tr(c, kind) for c in missing)]
    index = {h: i for i, h in enumerate(headers)}
    rows: list[dict[str, Any]] = []
    for rno, values in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        if not any(v not in (None, "") for v in values):
            continue
        row = {col: canonical_value(col, values[index[col]] if index[col] < len(values) else None, kind) for col in cfg["columns"]}
        row["__row__"] = rno
        rows.append(row)
    if not rows:
        errors.append("Excel içinde veri satırı bulunamadı")
    return rows, [localize(e) for e in errors]


def yes_no(value: Any, default: bool = True) -> bool:
    text = str(value if value is not None else "").strip().casefold()
    if not text:
        return default
    return text in {"1", "true", "evet", "yes", "aktif", "active"}


def rubric_scores(value: Any) -> dict[str, float]:
    result: dict[str, float] = {}
    for part in str(value or "").split(";"):
        if not part.strip():
            continue
        if "=" not in part:
            raise ValueError(f"Rubrik puanı hatalı: {part.strip()}")
        key, raw = part.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("Rubrik ölçüt id boş olamaz")
        result[key] = float(str(raw).replace(",", ".").strip())
    return result
