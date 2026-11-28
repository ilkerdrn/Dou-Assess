from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import false as sa_false, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models as m
from .authz import current_user, has_role, require_program_access, require_roles, visible_program_ids
from .db import get_db

router = APIRouter()
UTC = timezone.utc
SOURCE_TYPES = {"exam", "quality", "controlled"}
SECTION_STATES = {"not_started", "in_progress", "submitted", "approved", "changes_requested"}
REVIEW_MANAGER_ROLES = {"admin", "quality", "program_head", "department_head", "faculty_admin"}


def now() -> datetime:
    return datetime.now(UTC)


def actor_email() -> str:
    return str(current_user().get("email") or "system").strip().lower()


def audit(db: Session, action: str, entity_type: str, entity_id: int | None, payload: dict | None = None):
    ctx = current_user()
    db.add(m.AuditLog(actor_user_id=ctx.get("id"), actor_email=ctx.get("email") or "system", actor_roles=list(ctx.get("role_names") or []), action=action, entity_type=entity_type, entity_id=entity_id, payload=payload or {}))


def commit(db: Session):
    try: db.commit()
    except Exception:
        db.rollback(); raise


def tag_key(label: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", label.strip().casefold().replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")).strip("-")
    if not value: raise HTTPException(400, "Etiket boş olamaz")
    return value[:64]


def template_out(x: m.ProgramReviewTemplate) -> dict:
    return {"id":x.id,"code":x.code,"version":x.version,"title":x.title,"description":x.description,"sections":x.sections or [],"active":x.active,"created_by":x.created_by,"created_at":x.created_at}


def review_out(x: m.ProgramReview) -> dict:
    return {"id":x.id,"program_id":x.program_id,"template_id":x.template_id,"academic_year":x.academic_year,"review_no":x.review_no,"title":x.title,"owner":x.owner,"due_date":x.due_date,"status":x.status,"final_sha256":x.final_sha256,"finalized_by":x.finalized_by,"finalized_at":x.finalized_at,"created_at":x.created_at,"updated_at":x.updated_at}


def section_out(x: m.ProgramReviewSection, evidence: list[dict] | None = None) -> dict:
    return {"id":x.id,"review_id":x.review_id,"section_key":x.section_key,"title":x.title,"order_no":x.order_no,"guidance":x.guidance,"narrative":x.narrative,"contributor_email":x.contributor_email,"reviewer_email":x.reviewer_email,"due_date":x.due_date,"status":x.status,"reviewer_note":x.reviewer_note,"submitted_at":x.submitted_at,"approved_at":x.approved_at,"updated_at":x.updated_at,"evidence":evidence or []}


class TemplateCreate(BaseModel):
    code: str = Field(min_length=2, max_length=96)
    version: str = Field(default="1.0", min_length=1, max_length=32)
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(default="", max_length=8000)
    sections: list[dict[str, Any]] = Field(min_length=1, max_length=40)


class ReviewCreate(BaseModel):
    template_id: int
    academic_year: str = Field(min_length=4, max_length=32)
    title: str = Field(default="", max_length=255)
    owner: str = Field(default="", max_length=255)
    due_date: date | None = None


class SectionUpdate(BaseModel):
    narrative: str | None = Field(default=None, max_length=50000)
    contributor_email: str | None = Field(default=None, max_length=255)
    reviewer_email: str | None = Field(default=None, max_length=255)
    due_date: date | None = None


class SectionReview(BaseModel):
    decision: str
    note: str = Field(default="", max_length=8000)


class EvidenceLinkCreate(BaseModel):
    source_type: str
    source_id: int
    note: str = Field(default="", max_length=4000)


class TagCreate(BaseModel):
    label: str = Field(min_length=1, max_length=96)


def normalize_sections(raw: list[dict[str, Any]]) -> list[dict]:
    rows=[]; seen=set()
    for i,item in enumerate(raw,1):
        key=str(item.get("key") or item.get("section_key") or "").strip()[:96]
        title=str(item.get("title") or "").strip()[:255]
        if not key or not title: raise HTTPException(400, f"Şablon bölüm {i}: key ve title zorunlu")
        if key in seen: raise HTTPException(400, f"Tekrarlı bölüm anahtarı: {key}")
        seen.add(key)
        rows.append({"key":key,"title":title,"guidance":str(item.get("guidance") or "")[:8000],"order_no":int(item.get("order_no") or i)})
    return sorted(rows,key=lambda x:(x["order_no"],x["key"]))


@router.get("/api/program-review/templates")
def list_templates(active_only: bool = True, db: Session = Depends(get_db)):
    stmt=select(m.ProgramReviewTemplate).order_by(m.ProgramReviewTemplate.code,m.ProgramReviewTemplate.version.desc())
    if active_only: stmt=stmt.where(m.ProgramReviewTemplate.active.is_(True))
    return [template_out(x) for x in db.scalars(stmt).all()]


@router.post("/api/program-review/templates", status_code=201)
def create_template(data: TemplateCreate, db: Session = Depends(get_db)):
    require_roles("admin","quality")
    obj=m.ProgramReviewTemplate(code=data.code.strip().upper(),version=data.version.strip(),title=data.title.strip(),description=data.description.strip(),sections=normalize_sections(data.sections),created_by=actor_email())
    db.add(obj)
    try:
        db.flush(); audit(db,"create","program_review_template",obj.id,{"code":obj.code,"version":obj.version}); commit(db)
    except IntegrityError:
        db.rollback(); raise HTTPException(409,"Bu program review şablon sürümü zaten var")
    db.refresh(obj); return template_out(obj)


@router.get("/api/programs/{program_id}/program-reviews")
def list_reviews(program_id: int, academic_year: str | None = None, db: Session = Depends(get_db)):
    require_program_access(db,program_id,write=False,accreditation=True)
    stmt=select(m.ProgramReview).where(m.ProgramReview.program_id==program_id).order_by(m.ProgramReview.id.desc())
    if academic_year: stmt=stmt.where(m.ProgramReview.academic_year==academic_year)
    return [review_out(x) for x in db.scalars(stmt).all()]


@router.post("/api/programs/{program_id}/program-reviews", status_code=201)
def create_review(program_id: int, data: ReviewCreate, db: Session = Depends(get_db)):
    program=require_program_access(db,program_id,write=True,accreditation=True)
    template=db.get(m.ProgramReviewTemplate,data.template_id)
    if not template or not template.active: raise HTTPException(404,"Aktif program review şablonu bulunamadı")
    current_no=(db.scalar(select(func.max(m.ProgramReview.review_no)).where(m.ProgramReview.program_id==program_id,m.ProgramReview.academic_year==data.academic_year)) or 0)+1
    owner=(data.owner.strip() or actor_email())[:255]
    obj=m.ProgramReview(program_id=program_id,template_id=template.id,academic_year=data.academic_year.strip(),review_no=current_no,title=(data.title.strip() or f"{program.name} · {data.academic_year} Program Değerlendirmesi")[:255],owner=owner,due_date=data.due_date,status="draft",created_at=now(),updated_at=now())
    db.add(obj);db.flush()
    for item in normalize_sections(template.sections or []):
        db.add(m.ProgramReviewSection(review_id=obj.id,section_key=item["key"],title=item["title"],order_no=item["order_no"],guidance=item["guidance"],contributor_email=owner,due_date=data.due_date,status="not_started",updated_at=now()))
    audit(db,"create","program_review",obj.id,{"program_id":program_id,"template_id":template.id,"academic_year":obj.academic_year,"review_no":current_no});commit(db);db.refresh(obj)
    return review_out(obj)


def get_review(db: Session, review_id: int, *, write: bool=False) -> m.ProgramReview:
    obj=db.get(m.ProgramReview,review_id)
    if not obj: raise HTTPException(404,"Program değerlendirmesi bulunamadı")
    require_program_access(db,obj.program_id,write=write,accreditation=True)
    return obj


def get_section(db: Session, section_id: int) -> tuple[m.ProgramReviewSection,m.ProgramReview]:
    section=db.get(m.ProgramReviewSection,section_id)
    if not section: raise HTTPException(404,"Program review bölümü bulunamadı")
    review=get_review(db,section.review_id,write=False)
    return section,review


def section_evidence(db: Session, section_id: int) -> list[dict]:
    rows=db.scalars(select(m.ProgramReviewEvidenceLink).where(m.ProgramReviewEvidenceLink.section_id==section_id).order_by(m.ProgramReviewEvidenceLink.id)).all()
    return [{"id":x.id,"source_type":x.source_type,"source_id":x.source_id,"note":x.note,"added_by":x.added_by,"created_at":x.created_at} for x in rows]


@router.get("/api/program-reviews/{review_id}")
def review_dashboard(review_id: int, db: Session = Depends(get_db)):
    obj=get_review(db,review_id)
    sections=list(db.scalars(select(m.ProgramReviewSection).where(m.ProgramReviewSection.review_id==obj.id).order_by(m.ProgramReviewSection.order_no,m.ProgramReviewSection.id)).all())
    counts={k:0 for k in SECTION_STATES}
    payload=[]
    for s in sections:
        counts[s.status]=counts.get(s.status,0)+1; payload.append(section_out(s,section_evidence(db,s.id)))
    approved=counts.get("approved",0);total=len(sections)
    return {"review":review_out(obj),"sections":payload,"progress":{"total":total,"approved":approved,"percent":round(100*approved/total,1) if total else 0,"by_status":counts}}


def review_manager() -> bool:
    return bool(set(current_user().get("role_names") or []).intersection(REVIEW_MANAGER_ROLES))


def can_edit_section(section: m.ProgramReviewSection, review: m.ProgramReview) -> bool:
    email=actor_email()
    return bool(review_manager() or email in {section.contributor_email.lower(),review.owner.lower()})


def can_review_section(section: m.ProgramReviewSection) -> bool:
    email=actor_email()
    return bool(review_manager() or (section.reviewer_email and email==section.reviewer_email.lower()))


@router.patch("/api/program-review-sections/{section_id}")
def update_section(section_id: int, data: SectionUpdate, db: Session = Depends(get_db)):
    section,review=get_section(db,section_id)
    if review.status in {"final","archived"}: raise HTTPException(409,"Final/arsivlenmiş program review değiştirilemez")
    if not can_edit_section(section,review): raise HTTPException(403,"Bu bölümü düzenleme yetkiniz yok")
    changes=data.model_dump(exclude_unset=True)
    governed={"contributor_email","reviewer_email","due_date"}
    if governed.intersection(changes) and not review_manager():
        raise HTTPException(403,"Katkı veren, inceleyen ve termin atamalarını yalnız program/kalite yöneticisi değiştirebilir")
    normalized=dict(changes)
    for key,value in normalized.items():
        if key in {"contributor_email","reviewer_email"} and value is not None: value=value.strip().lower()
        setattr(section,key,value)
    if section.contributor_email and section.reviewer_email and section.contributor_email.casefold()==section.reviewer_email.casefold():
        raise HTTPException(409,"Katkı veren ile inceleyen aynı kişi olamaz")
    if "narrative" in changes and section.status in {"not_started","changes_requested"}: section.status="in_progress"
    section.updated_at=now();review.status="in_progress" if review.status=="draft" else review.status;review.updated_at=now()
    audit(db,"update","program_review_section",section.id,{"fields":sorted(changes)});commit(db);db.refresh(section);return section_out(section,section_evidence(db,section.id))


@router.post("/api/program-review-sections/{section_id}/submit")
def submit_section(section_id: int, db: Session = Depends(get_db)):
    section,review=get_section(db,section_id)
    if review.status in {"final","archived"}: raise HTTPException(409,"Final/arsivlenmiş program review değiştirilemez")
    if not can_edit_section(section,review): raise HTTPException(403,"Bu bölümü gönderme yetkiniz yok")
    if not section.narrative.strip(): raise HTTPException(409,"Bölüm anlatımı boşken incelemeye gönderilemez")
    if not section.reviewer_email.strip(): raise HTTPException(409,"Bölüm reviewer atanmadan incelemeye gönderilemez")
    if section.contributor_email and section.contributor_email.casefold()==section.reviewer_email.casefold(): raise HTTPException(409,"Katkı veren ile inceleyen aynı kişi olamaz")
    section.status="submitted";section.submitted_at=now();section.updated_at=now();review.status="review";review.updated_at=now();audit(db,"submit","program_review_section",section.id,{});commit(db);return section_out(section,section_evidence(db,section.id))


@router.post("/api/program-review-sections/{section_id}/review")
def review_section(section_id: int, data: SectionReview, db: Session = Depends(get_db)):
    section,review=get_section(db,section_id)
    if review.status in {"final","archived"}: raise HTTPException(409,"Final/arsivlenmiş program review değiştirilemez")
    if not can_review_section(section): raise HTTPException(403,"Bu bölümü inceleme yetkiniz yok")
    if section.status!="submitted": raise HTTPException(409,"Yalnız incelemeye gönderilmiş bölüm karara bağlanabilir")
    decision=data.decision.strip().lower()
    if decision not in {"approve","changes_requested"}: raise HTTPException(400,"decision approve veya changes_requested olmalı")
    if decision=="approve":
        if section.contributor_email and actor_email()==section.contributor_email.lower(): raise HTTPException(409,"Katkı veren kişi kendi bölümünü onaylayamaz")
        section.status="approved";section.approved_at=now()
    else:
        section.status="changes_requested";section.approved_at=None
    section.reviewer_note=data.note.strip();section.updated_at=now();audit(db,"review","program_review_section",section.id,{"decision":decision});commit(db);return section_out(section,section_evidence(db,section.id))


def evidence_source(db: Session, source_type: str, source_id: int) -> dict:
    if source_type not in SOURCE_TYPES: raise HTTPException(400,"Geçersiz kanıt kaynağı")
    if source_type=="exam":
        x=db.get(m.EvidenceAsset,source_id)
        if not x: raise HTTPException(404,"Sınav kanıtı bulunamadı")
        exam=db.get(m.Exam,x.exam_id);course=db.get(m.Course,exam.course_id) if exam else None
        if not course: raise HTTPException(409,"Kanıtın ders/program bağı çözümlenemedi")
        require_program_access(db,course.program_id,write=False,accreditation=True)
        return {"source_type":"exam","source_id":x.id,"program_id":course.program_id,"title":x.original_name,"description":x.description,"category":x.category,"sha256":x.sha256,"integrity_status":x.integrity_status,"created_at":x.created_at,"download_url":f"/api/evidence/{x.id}/download","context":f"Sınav #{x.exam_id}"}
    if source_type=="quality":
        x=db.get(m.QualityEvidenceAsset,source_id)
        if not x: raise HTTPException(404,"Kalite kanıtı bulunamadı")
        require_program_access(db,x.program_id,write=False,accreditation=True)
        return {"source_type":"quality","source_id":x.id,"program_id":x.program_id,"title":x.original_name,"description":x.description,"category":x.category,"sha256":x.sha256,"integrity_status":x.integrity_status,"created_at":x.created_at,"download_url":f"/api/quality360/evidence/{x.id}/download","context":x.criterion_code or x.entity_type}
    rev=db.get(m.ControlledDocumentRevision,source_id)
    if not rev: raise HTTPException(404,"Kontrollü doküman revizyonu bulunamadı")
    doc=db.get(m.ControlledDocument,rev.document_id)
    if not doc: raise HTTPException(409,"Kontrollü doküman bulunamadı")
    if doc.program_id is not None: require_program_access(db,doc.program_id,write=False,accreditation=True)
    else: require_roles("admin","quality","faculty_admin","department_head","program_head")
    return {"source_type":"controlled","source_id":rev.id,"program_id":doc.program_id,"title":f"{doc.document_code} · {doc.title} · R{rev.revision_no}","description":rev.change_summary,"category":doc.document_type,"sha256":rev.sha256,"integrity_status":rev.integrity_status,"created_at":rev.created_at,"download_url":f"/api/compliance/document-revisions/{rev.id}/download" if rev.stored_name else "","context":rev.status}


@router.post("/api/program-review-sections/{section_id}/evidence", status_code=201)
def link_evidence(section_id: int, data: EvidenceLinkCreate, db: Session = Depends(get_db)):
    section,review=get_section(db,section_id)
    if review.status in {"final","archived"}: raise HTTPException(409,"Final/arsivlenmiş program review değiştirilemez")
    if not can_edit_section(section,review): raise HTTPException(403,"Bu bölüme kanıt ekleme yetkiniz yok")
    source=evidence_source(db,data.source_type,data.source_id)
    if source["program_id"] not in {None,review.program_id}: raise HTTPException(409,"Başka programa ait kanıt bu review bölümüne bağlanamaz")
    obj=m.ProgramReviewEvidenceLink(section_id=section.id,source_type=data.source_type,source_id=data.source_id,note=data.note.strip(),added_by=actor_email(),created_at=now())
    db.add(obj)
    try: db.flush();audit(db,"link_evidence","program_review_section",section.id,{"source_type":obj.source_type,"source_id":obj.source_id});commit(db)
    except IntegrityError: db.rollback(); raise HTTPException(409,"Bu kanıt bölüme zaten bağlı")
    db.refresh(obj);return {"id":obj.id,"source":source,"note":obj.note,"added_by":obj.added_by,"created_at":obj.created_at}


@router.delete("/api/program-review-evidence-links/{link_id}")
def unlink_evidence(link_id: int, db: Session = Depends(get_db)):
    obj=db.get(m.ProgramReviewEvidenceLink,link_id)
    if not obj: raise HTTPException(404,"Kanıt bağlantısı bulunamadı")
    section,review=get_section(db,obj.section_id)
    if review.status in {"final","archived"}: raise HTTPException(409,"Final/arsivlenmiş program review değiştirilemez")
    if not can_edit_section(section,review): raise HTTPException(403,"Bu bağlantıyı kaldırma yetkiniz yok")
    audit(db,"unlink_evidence","program_review_section",section.id,{"source_type":obj.source_type,"source_id":obj.source_id});db.delete(obj);commit(db);return {"ok":True}


@router.post("/api/program-reviews/{review_id}/finalize")
def finalize_review(review_id: int, db: Session = Depends(get_db)):
    obj=get_review(db,review_id,write=True)
    require_roles("admin","quality","program_head")
    if obj.status in {"final","archived"}: raise HTTPException(409,"Program review zaten final/arsivlenmiş")
    sections=list(db.scalars(select(m.ProgramReviewSection).where(m.ProgramReviewSection.review_id==obj.id).order_by(m.ProgramReviewSection.order_no,m.ProgramReviewSection.id)).all())
    if not sections or any(s.status!="approved" for s in sections): raise HTTPException(409,"Final için tüm bölümler inceleyen tarafından onaylanmış olmalı")
    frozen_sections=[]
    for section in sections:
        evidence=[]
        for link in db.scalars(select(m.ProgramReviewEvidenceLink).where(m.ProgramReviewEvidenceLink.section_id==section.id).order_by(m.ProgramReviewEvidenceLink.id)).all():
            source=evidence_source(db,link.source_type,link.source_id)
            evidence.append({
                "link_id":link.id,"source_type":link.source_type,"source_id":link.source_id,"note":link.note,
                "added_by":link.added_by,"linked_at":link.created_at,"title":source.get("title"),
                "category":source.get("category"),"context":source.get("context"),"sha256":source.get("sha256"),
                "integrity_status":source.get("integrity_status"),"program_id":source.get("program_id"),
            })
        frozen_sections.append(section_out(section,evidence))
    snap={"review":review_out(obj),"sections":frozen_sections,"frozen_at":now().isoformat(),"manifest_version":"6.69"}
    snap=json.loads(json.dumps(snap,ensure_ascii=False,default=str))
    raw=json.dumps(snap,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    obj.final_snapshot=snap;obj.final_sha256=hashlib.sha256(raw).hexdigest();obj.finalized_by=actor_email();obj.finalized_at=now();obj.status="final";obj.updated_at=now();audit(db,"finalize","program_review",obj.id,{"sha256":obj.final_sha256,"sections":len(sections),"evidence":sum(len(x["evidence"]) for x in frozen_sections)});commit(db);return review_out(obj)


@router.get("/api/program-reviews/{review_id}/final-snapshot")
def final_review_snapshot(review_id: int, db: Session = Depends(get_db)):
    obj=get_review(db,review_id)
    if obj.status!="final" or not obj.final_snapshot or not obj.final_sha256:
        raise HTTPException(409,"Program review henüz final snapshot ile mühürlenmedi")
    raw=json.dumps(obj.final_snapshot,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    actual=hashlib.sha256(raw).hexdigest()
    return {"review_id":obj.id,"sha256":obj.final_sha256,"actual_sha256":actual,"integrity_status":"verified" if actual==obj.final_sha256 else "mismatch","snapshot":obj.final_snapshot}


def _tag_map(db: Session, items: list[tuple[str,int]]) -> dict[tuple[str,int],list[dict]]:
    if not items:return {}
    result={}
    grouped={t:set() for t in SOURCE_TYPES}
    for t,i in items: grouped.setdefault(t,set()).add(i)
    for t,ids in grouped.items():
        if not ids: continue
        rows=db.scalars(select(m.EvidenceTag).where(m.EvidenceTag.source_type==t,m.EvidenceTag.source_id.in_(ids)).order_by(m.EvidenceTag.tag_label)).all()
        for x in rows: result.setdefault((x.source_type,x.source_id),[]).append({"id":x.id,"key":x.tag_key,"label":x.tag_label})
    return result


def _usage_counts(db: Session, items: list[tuple[str,int]]) -> dict[tuple[str,int],int]:
    result={}
    for t in SOURCE_TYPES:
        ids=[i for st,i in items if st==t]
        if not ids:continue
        for source_id,count in db.execute(select(m.ProgramReviewEvidenceLink.source_id,func.count(m.ProgramReviewEvidenceLink.id)).where(m.ProgramReviewEvidenceLink.source_type==t,m.ProgramReviewEvidenceLink.source_id.in_(ids)).group_by(m.ProgramReviewEvidenceLink.source_id)).all(): result[(t,int(source_id))]=int(count)
    return result


def _evidence_hub_rows(db: Session, *, program_id:int|None,q:str|None,source_type:str|None,integrity_status:str|None,tag:str|None,fetch:int) -> tuple[list[dict],int]:
    allowed=visible_program_ids(db)
    if program_id is not None:
        require_program_access(db,program_id,write=False,accreditation=True);allowed={program_id}
    qpat=f"%{q.strip()}%" if q and q.strip() else None
    tag_filter:dict[str,set[int]]={t:set() for t in SOURCE_TYPES}
    if tag:
        key=tag_key(tag)
        for t,sid in db.execute(select(m.EvidenceTag.source_type,m.EvidenceTag.source_id).where(m.EvidenceTag.tag_key==key)).all(): tag_filter.setdefault(t,set()).add(int(sid))
    rows=[];total=0
    types=[source_type] if source_type else ["exam","quality","controlled"]
    if any(t not in SOURCE_TYPES for t in types): raise HTTPException(400,"Geçersiz source_type")
    if "exam" in types and allowed:
        stmt=select(m.EvidenceAsset,m.Course.program_id).join(m.Exam,m.Exam.id==m.EvidenceAsset.exam_id).join(m.Course,m.Course.id==m.Exam.course_id).where(m.Course.program_id.in_(allowed))
        if integrity_status: stmt=stmt.where(m.EvidenceAsset.integrity_status==integrity_status)
        if qpat: stmt=stmt.where(or_(m.EvidenceAsset.original_name.ilike(qpat),m.EvidenceAsset.description.ilike(qpat),m.EvidenceAsset.category.ilike(qpat)))
        if tag: stmt=stmt.where(m.EvidenceAsset.id.in_(tag_filter["exam"] or {-1}))
        total+=int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        for x,pid in db.execute(stmt.order_by(m.EvidenceAsset.created_at.desc()).limit(fetch)).all(): rows.append({"source_type":"exam","source_id":x.id,"program_id":pid,"title":x.original_name,"description":x.description,"category":x.category,"sha256":x.sha256,"integrity_status":x.integrity_status,"created_at":x.created_at,"download_url":f"/api/evidence/{x.id}/download","context":f"Sınav #{x.exam_id}"})
    if "quality" in types and allowed:
        stmt=select(m.QualityEvidenceAsset).where(m.QualityEvidenceAsset.program_id.in_(allowed))
        if integrity_status: stmt=stmt.where(m.QualityEvidenceAsset.integrity_status==integrity_status)
        if qpat: stmt=stmt.where(or_(m.QualityEvidenceAsset.original_name.ilike(qpat),m.QualityEvidenceAsset.description.ilike(qpat),m.QualityEvidenceAsset.category.ilike(qpat),m.QualityEvidenceAsset.criterion_code.ilike(qpat)))
        if tag: stmt=stmt.where(m.QualityEvidenceAsset.id.in_(tag_filter["quality"] or {-1}))
        total+=int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        for x in db.scalars(stmt.order_by(m.QualityEvidenceAsset.created_at.desc()).limit(fetch)).all(): rows.append({"source_type":"quality","source_id":x.id,"program_id":x.program_id,"title":x.original_name,"description":x.description,"category":x.category,"sha256":x.sha256,"integrity_status":x.integrity_status,"created_at":x.created_at,"download_url":f"/api/quality360/evidence/{x.id}/download","context":x.criterion_code or x.entity_type})
    if "controlled" in types:
        roles=set(current_user().get("role_names") or [])
        stmt=select(m.ControlledDocumentRevision,m.ControlledDocument).join(m.ControlledDocument,m.ControlledDocument.id==m.ControlledDocumentRevision.document_id)
        if "admin" not in roles and "quality" not in roles:
            if not allowed:return rows,total
            stmt=stmt.where(m.ControlledDocument.program_id.in_(allowed))
        elif program_id is not None: stmt=stmt.where(or_(m.ControlledDocument.program_id==program_id,m.ControlledDocument.program_id.is_(None)))
        if integrity_status: stmt=stmt.where(m.ControlledDocumentRevision.integrity_status==integrity_status)
        if qpat: stmt=stmt.where(or_(m.ControlledDocument.title.ilike(qpat),m.ControlledDocument.document_code.ilike(qpat),m.ControlledDocumentRevision.original_name.ilike(qpat),m.ControlledDocumentRevision.change_summary.ilike(qpat)))
        if tag: stmt=stmt.where(m.ControlledDocumentRevision.id.in_(tag_filter["controlled"] or {-1}))
        total+=int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        for rev,doc in db.execute(stmt.order_by(m.ControlledDocumentRevision.created_at.desc()).limit(fetch)).all(): rows.append({"source_type":"controlled","source_id":rev.id,"program_id":doc.program_id,"title":f"{doc.document_code} · {doc.title} · R{rev.revision_no}","description":rev.change_summary,"category":doc.document_type,"sha256":rev.sha256,"integrity_status":rev.integrity_status,"created_at":rev.created_at,"download_url":f"/api/compliance/document-revisions/{rev.id}/download" if rev.stored_name else "","context":rev.status})
    return rows,total


@router.get("/api/evidence-hub/summary")
def evidence_hub_summary(program_id:int|None=None,db:Session=Depends(get_db)):
    rows,total=_evidence_hub_rows(db,program_id=program_id,q=None,source_type=None,integrity_status=None,tag=None,fetch=5000)
    status_counts={k:0 for k in ("verified","unchecked","mismatch","missing")}
    source_counts={k:0 for k in SOURCE_TYPES}
    for x in rows:
        status=str(x.get("integrity_status") or "unchecked")
        status_counts[status]=status_counts.get(status,0)+1
        source_counts[x.get("source_type")]=source_counts.get(x.get("source_type"),0)+1
    keys=[(x["source_type"],x["source_id"]) for x in rows]
    usage=_usage_counts(db,keys)
    used=sum(1 for key in keys if usage.get(key,0)>0)
    sha={}
    for x in rows:
        value=str(x.get("sha256") or "")
        if value: sha[value]=sha.get(value,0)+1
    duplicate_groups=sum(1 for count in sha.values() if count>1)
    attention=status_counts.get("unchecked",0)+status_counts.get("mismatch",0)+status_counts.get("missing",0)
    return {"total":total,"verified":status_counts.get("verified",0),"attention":attention,"unchecked":status_counts.get("unchecked",0),"mismatch":status_counts.get("mismatch",0),"missing":status_counts.get("missing",0),"used_in_review":used,"duplicate_groups":duplicate_groups,"source_counts":source_counts}


@router.get("/api/evidence-hub")
def evidence_hub(q:str|None=None,program_id:int|None=None,source_type:str|None=None,integrity_status:str|None=None,tag:str|None=None,limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0,le=5000),db:Session=Depends(get_db)):
    rows,total=_evidence_hub_rows(db,program_id=program_id,q=q,source_type=source_type,integrity_status=integrity_status,tag=tag,fetch=offset+limit)
    rows.sort(key=lambda x:(x.get("created_at") or datetime.min.replace(tzinfo=UTC)),reverse=True)
    page=rows[offset:offset+limit];keys=[(x["source_type"],x["source_id"]) for x in page];tags=_tag_map(db,keys);uses=_usage_counts(db,keys)
    for x in page:x["tags"]=tags.get((x["source_type"],x["source_id"]),[]);x["review_usage_count"]=uses.get((x["source_type"],x["source_id"]),0)
    return {"items":page,"total":total,"limit":limit,"offset":offset}


@router.get("/api/evidence-hub/item/{source_type}/{source_id}")
def evidence_hub_detail(source_type:str,source_id:int,db:Session=Depends(get_db)):
    source=evidence_source(db,source_type,source_id)
    tags=_tag_map(db,[(source_type,source_id)]).get((source_type,source_id),[])
    allowed=visible_program_ids(db)
    link_stmt=select(m.ProgramReviewEvidenceLink,m.ProgramReviewSection,m.ProgramReview).join(m.ProgramReviewSection,m.ProgramReviewSection.id==m.ProgramReviewEvidenceLink.section_id).join(m.ProgramReview,m.ProgramReview.id==m.ProgramReviewSection.review_id).where(m.ProgramReviewEvidenceLink.source_type==source_type,m.ProgramReviewEvidenceLink.source_id==source_id)
    if allowed: link_stmt=link_stmt.where(m.ProgramReview.program_id.in_(allowed))
    else: link_stmt=link_stmt.where(sa_false())
    links=db.execute(link_stmt.order_by(m.ProgramReview.id.desc())).all()
    usage=[{"link_id":l.id,"review_id":r.id,"review_title":r.title,"section_id":s.id,"section_title":s.title,"status":s.status} for l,s,r in links]
    return {"evidence":source,"tags":tags,"program_review_usage":usage}


@router.post("/api/evidence-hub/item/{source_type}/{source_id}/tags",status_code=201)
def add_evidence_tag(source_type:str,source_id:int,data:TagCreate,db:Session=Depends(get_db)):
    evidence_source(db,source_type,source_id)
    if not review_manager(): raise HTTPException(403,"Kanıt etiketlerini yalnız kalite/program yönetimi değiştirebilir")
    label=data.label.strip();key=tag_key(label)
    obj=m.EvidenceTag(source_type=source_type,source_id=source_id,tag_key=key,tag_label=label,created_by=actor_email(),created_at=now());db.add(obj)
    try:db.flush();audit(db,"tag","evidence",source_id,{"source_type":source_type,"tag":key});commit(db)
    except IntegrityError:db.rollback();raise HTTPException(409,"Bu etiket kanıtta zaten var")
    db.refresh(obj);return {"id":obj.id,"key":obj.tag_key,"label":obj.tag_label}


@router.delete("/api/evidence-hub/tags/{tag_id}")
def delete_evidence_tag(tag_id:int,db:Session=Depends(get_db)):
    obj=db.get(m.EvidenceTag,tag_id)
    if not obj:raise HTTPException(404,"Etiket bulunamadı")
    evidence_source(db,obj.source_type,obj.source_id)
    if not review_manager(): raise HTTPException(403,"Kanıt etiketlerini yalnız kalite/program yönetimi değiştirebilir")
    audit(db,"untag","evidence",obj.source_id,{"source_type":obj.source_type,"tag":obj.tag_key});db.delete(obj);commit(db);return {"ok":True}


@router.get("/api/evidence-hub/duplicates/sha256")
def duplicate_evidence(program_id:int|None=None,db:Session=Depends(get_db)):
    rows,_=_evidence_hub_rows(db,program_id=program_id,q=None,source_type=None,integrity_status=None,tag=None,fetch=5000)
    groups={}
    for x in rows:
        sha=str(x.get("sha256") or "");
        if sha:groups.setdefault(sha,[]).append({"source_type":x["source_type"],"source_id":x["source_id"],"title":x["title"],"program_id":x["program_id"]})
    items=[{"sha256":sha,"count":len(v),"items":v} for sha,v in groups.items() if len(v)>1]
    items.sort(key=lambda x:(-x["count"],x["sha256"]))
    return {"items":items,"duplicate_groups":len(items)}
