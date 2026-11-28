"""OBS-ready grade export and the program-outcome (PÇ) calculation formula document."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .authz import current_user, require_course_access, require_program_access
from .db import get_db
from .services.analytics import course_gradebook
from .services.thresholds import active_threshold

router = APIRouter()
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/api/courses/{course_id}/obs-grades.xlsx")
def obs_grades_xlsx(course_id: int, db: Session = Depends(get_db)):
    """Final grades laid out for OBS bulk entry: one row per student, one column per weighted assessment, final grade last.
    The exact OBS import layout differs per institution - confirm it against the OBS bulk-entry template before first use."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    course = require_course_access(db, course_id, write=False)
    gb = course_gradebook(db, course_id)
    if not gb["exams"]:
        raise HTTPException(409, "Onaylı ve ağırlığı tanımlı sınav yok; OBS aktarım dosyası üretilemedi")
    wb = Workbook(); ws = wb.active; ws.title = "OBS_Toplu_Not"
    exams = gb["exams"]
    ws.append(["Öğrenci No", "Ad Soyad"] + [f"{e['title']} ({e['exam_type']}) %{e['weight_percent']:g}" for e in exams] + ["Başarı Notu (100)", "Durum"])
    for c in ws[1]: c.font = Font(bold=True)
    for st in gb["students"]:
        by_exam = {p["exam_id"]: p["score_percent"] for p in st["exams"]}
        ws.append([st["student_no"], st["full_name"]] + [by_exam.get(e["id"]) for e in exams] + [st["final_grade"], "Geçti" if st["status"] == "passed" else "Kaldı"])
    meta = wb.create_sheet("Bilgi")
    for row in [["Ders", f"{course.code} {course.name}"], ["Dönem", f"{course.academic_year} {course.term}"], ["Ağırlık toplamı", gb["assessment_weight_total"]],
                ["Ağırlıklar geçerli mi", "Evet" if gb["weights_valid"] else "HAYIR - toplam 100 değil; OBS'ye yüklemeden önce düzeltin"],
                ["Geçme notu (%)", gb["pass_threshold_percent"]], ["Üretim", datetime.now(timezone.utc).isoformat()],
                ["Uyarı", "OBS toplu not şablonunun sütun düzeni kuruma göre değişir; bu dosyayı şablona kopyalayarak kullanın."]]:
        meta.append(row)
    from .services.excel_tr import localize_workbook
    localize_workbook(wb)
    buf = BytesIO(); wb.save(buf); buf.seek(0)
    db.add(m.AuditLog(actor_user_id=current_user().get("id"), actor_email=current_user().get("email") or "system", actor_roles=list(current_user().get("role_names") or []),
                      action="obs_grades_export", entity_type="course", entity_id=course_id, payload={"students": len(gb["students"]), "weights_valid": gb["weights_valid"]}))
    db.commit()
    return StreamingResponse(buf, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="obs-notlar-{course.code.replace(" ", "_")}.xlsx"'})


@router.get("/api/programs/{program_id}/po-formula.md")
def po_formula_document(program_id: int, academic_year: str | None = None, db: Session = Depends(get_db)):
    """Auditor-facing description of how program-outcome attainment is computed, stamped with the live matrix and thresholds."""
    require_program_access(db, program_id, write=False)
    p = db.get(m.Program, program_id)
    if not p: raise HTTPException(404, "Program bulunamadı")
    pos = db.scalars(select(m.ProgramOutcome).where(m.ProgramOutcome.program_id == program_id, *( [m.ProgramOutcome.academic_year == academic_year] if academic_year else [])).order_by(m.ProgramOutcome.academic_year, m.ProgramOutcome.code)).all()
    lines = [f"# Program Çıktısı (PÇ) Hesaplama Belgesi — {p.code} {p.name}", "", f"Üretim: {datetime.now(timezone.utc).date().isoformat()}", "",
             "## 1. Yöntem", "",
             "1. **Soru → ÖÇ:** Her soru bir veya birden fazla ders öğrenme çıktısı (ÖÇ) ile eşlenir. Sınav oluşturulurken ÖÇ/PÇ eşleşmeleri sınava *anlık görüntü (snapshot)* olarak dondurulur; sonradan yapılan değişiklikler eski sınavları etkilemez.",
             "2. **ÖÇ başarısı (sınav):** `ÖÇ% = Σ(öğrencilerin o ÖÇ sorularından aldığı puan) / Σ(o ÖÇ sorularının toplam puanı × katılan öğrenci sayısı) × 100`. Devamsız öğrenciler dışarıda bırakılır.",
             "3. **PÇ başarısı (sınav):** `PÇ% = Σ(ÖÇ% × katkı) / Σ(katkı)`; katkı, ÖÇ–PÇ matrisindeki 1–5 değeridir. Katkısı 0 olan ÖÇ hesaba girmez.",
             "4. **Hedef:** ÖÇ hedefi ÖÇ tanımındaki yüzdedir. PÇ hedefi, geçerli bir PÇ başarı eşiği (sürümlü, aşağıda) tanımlıysa o eşik; yoksa katkı ağırlıklı ÖÇ hedeflerinin ortalamasıdır. Başarı ≥ hedef ise *ulaşıldı*, değilse *iyileştirme gerekli*.",
             "5. **Ders düzeyi:** Dersteki onaylı sınavların ÖÇ/PÇ yüzdeleri, sınavın ders notuna etki ağırlığıyla ağırlıklandırılır.",
             "6. **Öğrenci karnesi:** Öğrencinin kendi puanlarından aynı formüllerle hesaplanır; dönemler boyunca ders ağırlıklarıyla birleştirilir.",
             "7. **Dolaylı ölçme:** Anket ve benzeri dolaylı ölçmeler doğrudan (sınav/ödev/proje) sonuçlardan ayrı raporlanır ve bu formülün parçası değildir.",
             "8. **Ölçülmeyen PÇ:** Hiçbir ÖÇ aracılığıyla ölçülmeyen PÇ'ler için başarı hesaplanmaz ve uyarı verilir.", "",
             "## 2. Başarı eşikleri (geçerli sürümler)", ""]
    for kind, label in (("lo", "ÖÇ varsayılan hedefi"), ("po", "PÇ başarı eşiği")):
        v = active_threshold(db, program_id, academic_year, kind)
        lines.append(f"- {label}: {'%' + format(v, 'g') if v is not None else 'tanımlı değil'}")
    lines += ["", "## 3. Programın PÇ listesi ve katkı matrisi", ""]
    for po in pos:
        lines.append(f"### {po.code} ({po.academic_year}) — {po.description}")
        rows = db.execute(select(m.Course.code, m.LearningOutcome.code, m.OutcomeMapping.contribution).join(m.LearningOutcome, m.LearningOutcome.id == m.OutcomeMapping.learning_outcome_id)
                          .join(m.Course, m.Course.id == m.LearningOutcome.course_id).where(m.OutcomeMapping.program_outcome_id == po.id, m.OutcomeMapping.contribution > 0).order_by(m.Course.code, m.LearningOutcome.code)).all()
        lines += [f"- {c} / {lo}: katkı {k}/5" for c, lo, k in rows] or ["- Bu PÇ'ye katkı veren ÖÇ yok (ölçülmüyor)."]
        lines.append("")
    return Response("\n".join(lines), media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f'inline; filename="po-formula-{p.code}.md"'})
