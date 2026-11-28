from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal, Optional

from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models as m
from .authz import current_user, require_course_access, require_course_management
from .db import get_db

router = APIRouter(prefix="/api", tags=["Assessment Measures"])

MEASURE_TYPES = {"exam","assignment","project","presentation","laboratory","internship","portfolio","capstone","practical","peer_assessment"}


def _commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _audit(db: Session, action: str, entity_type: str, entity_id: int | None, payload: dict) -> None:
    try:
        actor = current_user()
    except Exception:
        actor = {"id": None, "email": "system", "role_names": []}
    db.add(m.AuditLog(
        actor_user_id=actor.get("id"), actor_email=actor.get("email") or "system",
        actor_roles=list(actor.get("role_names") or []), action=action,
        entity_type=entity_type, entity_id=entity_id, payload=payload,
    ))


class RubricLevelIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=128)
    description: str = ""
    score_percent: float = Field(ge=0, le=100)
    order_no: int = Field(default=1, ge=1)


class RubricCriterionIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    learning_outcome_id: Optional[int] = None
    order_no: int = Field(default=1, ge=1)
    max_points: float = Field(gt=0)
    weight_percent: float = Field(default=0, ge=0, le=100)
    levels: list[RubricLevelIn] = Field(default_factory=list)


class RubricTemplateCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    version_no: int = Field(default=1, ge=1)
    max_points: float = Field(default=100, gt=0)
    criteria: list[RubricCriterionIn] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_points(self):
        total = sum(float(x.max_points) for x in self.criteria)
        if abs(total - float(self.max_points)) > 0.01:
            raise ValueError(f"Rubrik kriter puan toplamı {self.max_points:g} olmalıdır; mevcut toplam {total:g}")
        codes = [x.code.strip().lower() for x in self.criteria]
        if len(codes) != len(set(codes)):
            raise ValueError("Rubrik kriter kodları benzersiz olmalıdır")
        return self


class MeasureCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    measure_type: Literal["exam","assignment","project","presentation","laboratory","internship","portfolio","capstone","practical","peer_assessment"]
    directness: Literal["direct","indirect"] = "direct"
    course_offering_id: Optional[int] = None
    rubric_template_id: Optional[int] = None
    weight_percent: float = Field(default=0, ge=0, le=100)
    max_points: float = Field(default=100, gt=0)
    target_percent: float = Field(default=60, ge=0, le=100)
    instructions: str = ""
    due_date: Optional[date] = None


class MeasureUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    rubric_template_id: Optional[int] = None
    weight_percent: Optional[float] = Field(default=None, ge=0, le=100)
    max_points: Optional[float] = Field(default=None, gt=0)
    target_percent: Optional[float] = Field(default=None, ge=0, le=100)
    instructions: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[Literal["draft","active","closed","archived"]] = None


class OutcomeLinkIn(BaseModel):
    learning_outcome_id: int
    weight_percent: float = Field(default=100, ge=0, le=100)


class OutcomeLinksReplace(BaseModel):
    items: list[OutcomeLinkIn] = Field(default_factory=list)


class MeasureResultIn(BaseModel):
    student_id: int
    raw_score: Optional[float] = Field(default=None, ge=0)
    rubric_scores: dict[str, float] = Field(default_factory=dict)
    feedback: str = ""
    status: Literal["draft","final"] = "final"


def _rubric_detail(db: Session, template: m.RubricTemplate) -> dict:
    criteria = db.scalars(select(m.RubricCriterion).where(m.RubricCriterion.rubric_template_id == template.id).order_by(m.RubricCriterion.order_no, m.RubricCriterion.id)).all()
    rows = []
    for c in criteria:
        levels = db.scalars(select(m.RubricLevel).where(m.RubricLevel.rubric_criterion_id == c.id).order_by(m.RubricLevel.order_no, m.RubricLevel.id)).all()
        lo = db.get(m.LearningOutcome, c.learning_outcome_id) if c.learning_outcome_id else None
        rows.append({
            "id": c.id, "code": c.code, "title": c.title, "description": c.description,
            "learning_outcome_id": c.learning_outcome_id, "learning_outcome_code": lo.code if lo else None,
            "order_no": c.order_no, "max_points": c.max_points, "weight_percent": c.weight_percent,
            "levels": [{"id": x.id, "code": x.code, "title": x.title, "description": x.description, "score_percent": x.score_percent, "order_no": x.order_no} for x in levels],
        })
    return {"id": template.id, "course_id": template.course_id, "title": template.title, "description": template.description, "version_no": template.version_no, "status": template.status, "max_points": template.max_points, "criteria": rows}


def _measure_out(db: Session, x: m.AssessmentMeasure) -> dict:
    rubric = db.get(m.RubricTemplate, x.rubric_template_id) if x.rubric_template_id else None
    links = db.scalars(select(m.AssessmentMeasureOutcome).where(m.AssessmentMeasureOutcome.assessment_measure_id == x.id)).all()
    return {
        "id": x.id, "course_id": x.course_id, "course_offering_id": x.course_offering_id,
        "rubric_template_id": x.rubric_template_id, "rubric_title": rubric.title if rubric else None,
        "code": x.code, "title": x.title, "measure_type": x.measure_type, "directness": x.directness,
        "weight_percent": x.weight_percent, "max_points": x.max_points, "target_percent": x.target_percent,
        "instructions": x.instructions, "due_date": x.due_date.isoformat() if x.due_date else None,
        "status": x.status,
        "outcomes": [{"learning_outcome_id": z.learning_outcome_id, "weight_percent": z.weight_percent, "code": (db.get(m.LearningOutcome, z.learning_outcome_id).code if db.get(m.LearningOutcome, z.learning_outcome_id) else "")} for z in links],
    }


@router.get("/courses/{course_id}/rubrics")
def list_rubrics(course_id: int, db: Session = Depends(get_db)):
    require_course_access(db, course_id, write=False)
    rows = db.scalars(select(m.RubricTemplate).where(m.RubricTemplate.course_id == course_id).order_by(m.RubricTemplate.id.desc())).all()
    return [_rubric_detail(db, x) for x in rows]


@router.post("/courses/{course_id}/rubrics", status_code=201)
def create_rubric(course_id: int, data: RubricTemplateCreate, db: Session = Depends(get_db)):
    require_course_management(db, course_id)
    if not db.get(m.Course, course_id):
        raise HTTPException(404, "Ders bulunamadı")
    lo_ids = {x.id for x in db.scalars(select(m.LearningOutcome).where(m.LearningOutcome.course_id == course_id)).all()}
    for c in data.criteria:
        if c.learning_outcome_id and c.learning_outcome_id not in lo_ids:
            raise HTTPException(400, f"Rubrik kriteri başka bir derse ait Öğrenim Çıktısına bağlanamaz: {c.code}")
    actor = current_user().get("email") or "system"
    obj = m.RubricTemplate(course_id=course_id, title=data.title, description=data.description, version_no=data.version_no, status="draft", max_points=data.max_points, created_by=actor)
    db.add(obj); db.flush()
    for c in data.criteria:
        criterion = m.RubricCriterion(rubric_template_id=obj.id, learning_outcome_id=c.learning_outcome_id, code=c.code, title=c.title, description=c.description, order_no=c.order_no, max_points=c.max_points, weight_percent=c.weight_percent)
        db.add(criterion); db.flush()
        for level in c.levels:
            db.add(m.RubricLevel(rubric_criterion_id=criterion.id, **level.model_dump()))
    _audit(db, "create", "rubric_template", obj.id, {"course_id": course_id, "title": data.title, "version_no": data.version_no})
    _commit(db)
    return _rubric_detail(db, obj)


@router.post("/rubrics/{rubric_id}/activate")
def activate_rubric(rubric_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.RubricTemplate, rubric_id)
    if not obj: raise HTTPException(404, "Rubrik bulunamadı")
    require_course_management(db, obj.course_id)
    obj.status = "active"
    _audit(db, "activate", "rubric_template", obj.id, {})
    _commit(db)
    return _rubric_detail(db, obj)


@router.get("/courses/{course_id}/assessment-measures")
def list_measures(course_id: int, db: Session = Depends(get_db)):
    require_course_access(db, course_id, write=False)
    rows = db.scalars(select(m.AssessmentMeasure).where(m.AssessmentMeasure.course_id == course_id).order_by(m.AssessmentMeasure.id.desc())).all()
    return [_measure_out(db, x) for x in rows]


@router.post("/courses/{course_id}/assessment-measures", status_code=201)
def create_measure(course_id: int, data: MeasureCreate, db: Session = Depends(get_db)):
    require_course_management(db, course_id)
    course = db.get(m.Course, course_id)
    if not course: raise HTTPException(404, "Ders bulunamadı")
    if data.course_offering_id:
        offering = db.get(m.CourseOffering, data.course_offering_id)
        if not offering or offering.course_id != course_id:
            raise HTTPException(400, "Ders açımı bu derse ait değil")
    if data.rubric_template_id:
        rubric = db.get(m.RubricTemplate, data.rubric_template_id)
        if not rubric or rubric.course_id != course_id:
            raise HTTPException(400, "Rubrik bu derse ait değil")
        if rubric.status != "active":
            raise HTTPException(400, "Yalnız aktif rubrik ölçme aracına bağlanabilir")
        if abs(float(rubric.max_points) - float(data.max_points)) > 0.01:
            raise HTTPException(400, "Ölçme aracı maksimum puanı aktif rubrik puanı ile aynı olmalıdır")
    actor = current_user().get("email") or "system"
    obj = m.AssessmentMeasure(course_id=course_id, status="draft", created_by=actor, **data.model_dump())
    db.add(obj); db.flush(); _audit(db, "create", "assessment_measure", obj.id, data.model_dump(mode="json")); _commit(db)
    return _measure_out(db, obj)


@router.patch("/assessment-measures/{measure_id}")
def update_measure(measure_id: int, data: MeasureUpdate, db: Session = Depends(get_db)):
    obj = db.get(m.AssessmentMeasure, measure_id)
    if not obj: raise HTTPException(404, "Ölçme aracı bulunamadı")
    require_course_management(db, obj.course_id)
    changes = data.model_dump(exclude_unset=True)
    if "rubric_template_id" in changes and changes["rubric_template_id"]:
        rubric = db.get(m.RubricTemplate, changes["rubric_template_id"])
        if not rubric or rubric.course_id != obj.course_id or rubric.status != "active":
            raise HTTPException(400, "Geçerli ve aktif bir ders rubriği seçilmelidir")
        proposed_max = changes.get("max_points", obj.max_points)
        if abs(float(rubric.max_points) - float(proposed_max)) > 0.01:
            raise HTTPException(400, "Ölçme aracı maksimum puanı rubrik puanı ile aynı olmalıdır")
    for key, value in changes.items(): setattr(obj, key, value)
    _audit(db, "update", "assessment_measure", obj.id, {k:(v.isoformat() if hasattr(v,"isoformat") else v) for k,v in changes.items()}); _commit(db)
    return _measure_out(db, obj)


@router.put("/assessment-measures/{measure_id}/outcomes")
def replace_measure_outcomes(measure_id: int, data: OutcomeLinksReplace, db: Session = Depends(get_db)):
    obj = db.get(m.AssessmentMeasure, measure_id)
    if not obj: raise HTTPException(404, "Ölçme aracı bulunamadı")
    require_course_management(db, obj.course_id)
    allowed = {x.id for x in db.scalars(select(m.LearningOutcome).where(m.LearningOutcome.course_id == obj.course_id)).all()}
    if any(x.learning_outcome_id not in allowed for x in data.items):
        raise HTTPException(400, "Yalnız bu derse ait Öğrenim Çıktıları bağlanabilir")
    ids = [x.learning_outcome_id for x in data.items]
    if len(ids) != len(set(ids)):
        raise HTTPException(400, "Aynı Öğrenim Çıktısı birden fazla kez bağlanamaz")
    old = db.scalars(select(m.AssessmentMeasureOutcome).where(m.AssessmentMeasureOutcome.assessment_measure_id == measure_id)).all()
    for x in old: db.delete(x)
    for x in data.items: db.add(m.AssessmentMeasureOutcome(assessment_measure_id=measure_id, **x.model_dump()))
    _audit(db, "replace_outcomes", "assessment_measure", obj.id, {"items": [x.model_dump() for x in data.items]}); _commit(db)
    return _measure_out(db, obj)


@router.put("/assessment-measures/{measure_id}/results")
def upsert_measure_result(measure_id: int, data: MeasureResultIn, db: Session = Depends(get_db)):
    obj = db.get(m.AssessmentMeasure, measure_id)
    if not obj: raise HTTPException(404, "Ölçme aracı bulunamadı")
    require_course_management(db, obj.course_id)
    student = db.get(m.Student, data.student_id)
    if not student: raise HTTPException(404, "Öğrenci bulunamadı")
    enrolled = db.scalar(select(func.count()).select_from(m.Enrollment).where(m.Enrollment.course_id == obj.course_id, m.Enrollment.student_id == data.student_id)) or 0
    if not enrolled: raise HTTPException(400, "Öğrenci bu derse kayıtlı değil")

    raw_score = data.raw_score
    rubric_scores = {str(k): float(v) for k,v in data.rubric_scores.items()}
    if obj.rubric_template_id:
        criteria = db.scalars(select(m.RubricCriterion).where(m.RubricCriterion.rubric_template_id == obj.rubric_template_id)).all()
        by_id = {str(x.id): x for x in criteria}
        unknown = set(rubric_scores) - set(by_id)
        if unknown: raise HTTPException(400, f"Rubrikte olmayan kriter puanı: {', '.join(sorted(unknown))}")
        for cid, score in rubric_scores.items():
            if score < 0 or score > float(by_id[cid].max_points):
                raise HTTPException(400, f"Rubrik kriter puanı sınır dışında: {by_id[cid].code}")
        raw_score = round(sum(rubric_scores.values()), 4)
    if raw_score is None:
        raise HTTPException(400, "Puan veya rubrik puanları gereklidir")
    if raw_score < 0 or raw_score > float(obj.max_points) + 1e-9:
        raise HTTPException(400, "Puan ölçme aracı maksimum puanını aşamaz")
    actor = current_user().get("email") or "system"
    result = db.scalar(select(m.AssessmentMeasureResult).where(m.AssessmentMeasureResult.assessment_measure_id == measure_id, m.AssessmentMeasureResult.student_id == data.student_id))
    if not result:
        result = m.AssessmentMeasureResult(assessment_measure_id=measure_id, student_id=data.student_id)
        db.add(result)
    result.raw_score = raw_score; result.rubric_scores = rubric_scores; result.feedback = data.feedback; result.status = data.status; result.graded_by = actor; result.graded_at = datetime.now(timezone.utc)
    _audit(db, "grade", "assessment_measure_result", result.id, {"measure_id": measure_id, "student_id": data.student_id, "score": raw_score, "status": data.status})
    _commit(db)
    return {"id": result.id, "assessment_measure_id": measure_id, "student_id": result.student_id, "raw_score": result.raw_score, "percent": round(result.raw_score / obj.max_points * 100, 1), "rubric_scores": result.rubric_scores, "feedback": result.feedback, "status": result.status, "graded_by": result.graded_by}


@router.get("/assessment-measures/{measure_id}/summary")
def measure_summary(measure_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.AssessmentMeasure, measure_id)
    if not obj: raise HTTPException(404, "Ölçme aracı bulunamadı")
    require_course_access(db, obj.course_id, write=False)
    rows = db.scalars(select(m.AssessmentMeasureResult).where(m.AssessmentMeasureResult.assessment_measure_id == measure_id, m.AssessmentMeasureResult.status == "final")).all()
    percents = [float(x.raw_score) / float(obj.max_points) * 100 for x in rows] if obj.max_points else []
    avg = round(sum(percents)/len(percents), 1) if percents else 0.0
    achieved = sum(1 for x in percents if x >= obj.target_percent)
    links = db.scalars(select(m.AssessmentMeasureOutcome).where(m.AssessmentMeasureOutcome.assessment_measure_id == measure_id)).all()
    return {
        "measure": _measure_out(db, obj),
        "result_count": len(rows),
        "average_percent": avg,
        "target_percent": obj.target_percent,
        "target_achievement_percent": round(achieved / len(rows) * 100, 1) if rows else 0.0,
        "min_percent": round(min(percents),1) if percents else None,
        "max_percent": round(max(percents),1) if percents else None,
        "outcome_count": len(links),
        "ready_for_outcome_analysis": bool(rows and links),
    }


# ---------------------------------------------------------------- Excel template + import (assignments / projects / labs ...)
def _measure_columns(db: Session, obj: m.AssessmentMeasure) -> list[tuple[str, float, str | None]]:
    """(column key, max, rubric criterion id) - one column per rubric criterion, else a single total-score column."""
    if obj.rubric_template_id:
        crit = db.scalars(select(m.RubricCriterion).where(m.RubricCriterion.rubric_template_id == obj.rubric_template_id).order_by(m.RubricCriterion.order_no)).all()
        if crit:
            return [(c.code, float(c.max_points), str(c.id)) for c in crit]
    return [("puan", float(obj.max_points), None)]


@router.get("/assessment-measures/{measure_id}/results-template.xlsx")
def measure_results_template(measure_id: int, db: Session = Depends(get_db)):
    from openpyxl import Workbook
    obj = db.get(m.AssessmentMeasure, measure_id)
    if not obj: raise HTTPException(404, "Ölçme aracı bulunamadı")
    require_course_access(db, obj.course_id, write=True)
    cols = _measure_columns(db, obj)
    wb = Workbook(); ws = wb.active; ws.title = "Puanlar"
    ws.append(["Öğrenci No", "Ad Soyad (bilgi)"] + [f"{'Puan' if k == 'puan' else k} (0-{mx:g})" for k, mx, _ in cols] + ["Geri Bildirim"])
    for st in db.scalars(select(m.Student).join(m.Enrollment, m.Enrollment.student_id == m.Student.id).where(m.Enrollment.course_id == obj.course_id).order_by(m.Student.student_no)).all():
        ws.append([st.student_no, st.full_name] + [None] * len(cols) + [""])
    info = wb.create_sheet("Yonerge")
    info.append(["Her satır bir öğrencidir. Boş bırakılan satırlar atlanır. Puanlar 0 ile parantezdeki üst sınır arasında olmalıdır."])
    buf = BytesIO(); wb.save(buf); buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="puan-sablonu-{obj.code}.xlsx"'})


@router.post("/assessment-measures/{measure_id}/results-import")
async def import_measure_results(measure_id: int, validate_only: bool = False, file: UploadFile = File(...), db: Session = Depends(get_db)):
    from openpyxl import load_workbook
    from .security import read_upload_limited
    obj = db.get(m.AssessmentMeasure, measure_id)
    if not obj: raise HTTPException(404, "Ölçme aracı bulunamadı")
    require_course_management(db, obj.course_id)
    data = await read_upload_limited(file)
    try:
        ws = load_workbook(BytesIO(data), read_only=True, data_only=True)["Puanlar"]
    except Exception:
        raise HTTPException(422, "Geçerli bir şablon yüklenmedi ('Puanlar' sayfası bulunamadı)")
    rows = list(ws.iter_rows(values_only=True))
    if not rows: raise HTTPException(422, "Dosya boş")
    header = [str(h or "").strip() for h in rows[0]]
    cols = _measure_columns(db, obj)
    idx = {}
    for key, mx, cid in cols:
        pos = next((i for i, h in enumerate(header) if h.split(" ")[0].lower() in (key.lower(), "puan" if key == "puan" else key.lower())), None)
        if pos is None: raise HTTPException(422, f"Şablonda '{key}' sütunu yok")
        idx[key] = pos
    fold = lambda t: "".join(ch for ch in t.lower().translate(str.maketrans("ığüşöç", "igusoc")) if ch.isalnum())
    no_pos = next((i for i, h in enumerate(header) if fold(h).startswith("ogrencino")), 0)
    fb_pos = next((i for i, h in enumerate(header) if fold(h).startswith("geribildirim")), None)
    enrolled = {st.student_no: st for st in db.scalars(select(m.Student).join(m.Enrollment, m.Enrollment.student_id == m.Student.id).where(m.Enrollment.course_id == obj.course_id)).all()}
    errors, ready = [], []
    for n, row in enumerate(rows[1:], start=2):
        sno = str(row[no_pos] or "").strip()
        vals = {k: row[i] for k, i in idx.items()}
        if not sno or all(v in (None, "") for v in vals.values()): continue
        st = enrolled.get(sno)
        if not st: errors.append({"row": n, "student_no": sno, "message": "Öğrenci bu derse kayıtlı değil"}); continue
        parsed, bad = {}, False
        for key, mx, cid in cols:
            v = vals[key]
            try: f = float(str(v).replace(",", ".")) if v not in (None, "") else None
            except ValueError: f = None
            if f is None: errors.append({"row": n, "student_no": sno, "message": f"'{key}' sayı olmalı"}); bad = True; break
            if f < 0 or f > mx + 1e-9: errors.append({"row": n, "student_no": sno, "message": f"'{key}' 0-{mx:g} arasında olmalı"}); bad = True; break
            parsed[key] = f
        if not bad: ready.append((st, parsed, str(row[fb_pos] or "") if fb_pos is not None else ""))
    if errors: raise HTTPException(422, {"message": "Dosya doğrulanamadı; hiçbir puan kaydedilmedi", "errors": errors[:100], "error_count": len(errors)})
    if validate_only: return {"valid": True, "rows": len(ready)}
    actor = current_user().get("email") or "system"; now = datetime.now(timezone.utc)
    for st, parsed, fb in ready:
        res = db.scalar(select(m.AssessmentMeasureResult).where(m.AssessmentMeasureResult.assessment_measure_id == measure_id, m.AssessmentMeasureResult.student_id == st.id))
        if not res:
            res = m.AssessmentMeasureResult(assessment_measure_id=measure_id, student_id=st.id); db.add(res)
        if cols[0][2] is None:
            res.raw_score = parsed["puan"]; res.rubric_scores = {}
        else:
            res.rubric_scores = {cid: parsed[key] for key, _, cid in cols}; res.raw_score = round(sum(parsed.values()), 4)
        res.feedback = fb; res.status = "final"; res.graded_by = actor; res.graded_at = now
    _audit(db, "grade_import", "assessment_measure", measure_id, {"rows": len(ready)}); _commit(db)
    return {"valid": True, "imported": len(ready)}
