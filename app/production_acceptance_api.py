from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from . import models as m
from .authz import current_user, require_roles
from .config import settings
from .db import get_db

router = APIRouter(tags=["Production Acceptance"])


class AcceptanceUpdate(BaseModel):
    status: str = Field(pattern="^(pending|passed|failed|waived)$")
    evidence_ref: str = Field(default="", max_length=1024)
    note: str = Field(default="", max_length=4000)


GATES = [
    {"key":"entra_identity","title":"Microsoft Entra canlı kimlik kabulü","domain":"identity","required":True,"manual":True},
    {"key":"proliz_obs_readonly","title":"Proliz / OBS read-only senkron kabulü","domain":"integration","required":True,"manual":True},
    {"key":"tls_dns_proxy","title":"Production DNS / TLS / reverse proxy kabulü","domain":"infrastructure","required":True,"manual":True},
    {"key":"physical_omr","title":"Fiziksel ADF / OMR saha kabulü","domain":"assessment","required":False,"manual":True},
    {"key":"backup_restore_dr","title":"Backup / restore / DR tatbikatı","domain":"infrastructure","required":True,"manual":True},
    {"key":"official_templates","title":"Resmî akreditasyon şablonları kalite birimi onayı","domain":"accreditation","required":True,"manual":True},
    {"key":"real_program_pilot","title":"Gerçek program uçtan uca pilot kabulü","domain":"academic","required":True,"manual":True},
    {"key":"rbac_isolation","title":"Rol ve akademik kapsam izolasyonu kabulü","domain":"security","required":True,"manual":True},
]


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _system_state(db: Session, gate_key: str) -> tuple[str, str]:
    if gate_key == "entra_identity":
        ready = bool(settings.auth_required and settings.auth_provider == "entra" and settings.entra_tenant_id and settings.entra_client_id and settings.entra_audience and settings.entra_allowed_client_ids and settings.entra_required_scopes and settings.entra_login_scopes and settings.entra_redirect_uri)
        return ("ready" if ready else "attention", "Entra production ayarları eksiksiz." if ready else "Tenant/client/audience/scope/redirect veya production auth ayarlarından biri eksik.")
    if gate_key == "proliz_obs_readonly":
        runs = list(db.scalars(select(m.IntegrationSyncRun).order_by(m.IntegrationSyncRun.id.desc()).limit(20)).all())
        success = any((r.status == "success" and str(r.provider or "").lower() not in {"obs-results-api"}) for r in runs)
        safe = not settings.obs_writeback_enabled
        return ("ready" if success and safe else "attention", ("Başarılı read-only senkron kaydı var; write-back kapalı." if success and safe else "Başarılı gerçek OBS/Proliz read-only senkron kaydı ve kapalı write-back birlikte doğrulanmalı."))
    if gate_key == "backup_restore_dr":
        root=Path(settings.ops_storage_path)
        backup=_read_json(root/"backup-status.json"); restore=_read_json(root/"restore-status.json")
        ok=bool(backup.get("created_at") and restore.get("created_at"))
        return ("ready" if ok else "attention", "Backup ve restore doğrulama kayıtları mevcut." if ok else "Backup ve/veya restore doğrulama kaydı eksik.")
    if gate_key == "rbac_isolation":
        roles=db.scalar(select(func.count()).select_from(m.UserRoleAssignment)) or 0
        return ("ready" if roles else "attention", f"{roles} rol ataması mevcut; gerçek hesaplarla izolasyon UAT'si ayrıca imzalanmalı.")
    if gate_key == "real_program_pilot":
        programs=db.scalar(select(func.count()).select_from(m.Program)) or 0
        exams=db.scalar(select(func.count()).select_from(m.Exam).where(m.Exam.status.in_(["approved","archived"]))) or 0
        return ("ready" if programs and exams else "attention", f"{programs} program, {exams} resmî sınav sistemde; gerçek dönem kullanıcı kabulü ayrıca gerekli.")
    if gate_key == "official_templates":
        count=db.scalar(select(func.count()).select_from(m.AccreditationReportTemplate).where(m.AccreditationReportTemplate.locked.is_(True))) or 0
        return ("ready" if count else "attention", f"{count} kilitli resmî/kurumsal şablon kaydı var; hedef dönem kalite birimi imzası ayrıca gerekli.")
    if gate_key == "tls_dns_proxy":
        return ("ready" if settings.app_env == "production" else "attention", "Uygulama production modunda; dış HTTPS/DNS kabulü manuel imza ister." if settings.app_env == "production" else "APP_ENV production değil.")
    if gate_key == "physical_omr":
        scans=db.scalar(select(func.count()).select_from(m.ScanSession)) or 0
        return ("ready" if scans else "attention", f"{scans} tarama batch kaydı var; fiziksel cihaz benchmark imzası ayrıca gerekli.")
    return "attention", "Sistem sinyali bulunamadı."


@router.get("/api/production-acceptance")
def production_acceptance(environment: str = "production", db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    records={x.gate_key:x for x in db.scalars(select(m.InstitutionAcceptanceRecord).where(m.InstitutionAcceptanceRecord.environment==environment)).all()}
    rows=[]
    for gate in GATES:
        rec=records.get(gate["key"])
        system_status, system_detail=_system_state(db,gate["key"])
        manual_status=rec.status if rec else "pending"
        effective="passed" if manual_status in {"passed","waived"} else ("failed" if manual_status=="failed" else "pending")
        rows.append({**gate,"system_status":system_status,"system_detail":system_detail,"manual_status":manual_status,"effective_status":effective,
                     "evidence_ref":rec.evidence_ref if rec else "","note":rec.note if rec else "","verified_by":rec.verified_by if rec else "","verified_at":rec.verified_at if rec else None})
    required=[x for x in rows if x["required"]]
    passed=sum(1 for x in required if x["effective_status"]=="passed")
    return {"environment":environment,"score":round(100*passed/len(required)) if required else 100,"required_passed":passed,"required_total":len(required),"release_ready":passed==len(required),"gates":rows,
            "disclaimer":"Sistem sinyali teknik hazırlığı gösterir; kurum kabulü yalnız yetkili kişi tarafından kanıt/ref ile passed/waived olarak imzalandığında kapanır."}


@router.patch("/api/production-acceptance/{gate_key}")
def update_production_acceptance(gate_key: str, body: AcceptanceUpdate, environment: str = "production", db: Session = Depends(get_db)):
    require_roles("admin", "quality")
    if gate_key not in {x["key"] for x in GATES}:
        raise HTTPException(404,"Kabul kapısı bulunamadı")
    rec=db.scalar(select(m.InstitutionAcceptanceRecord).where(m.InstitutionAcceptanceRecord.environment==environment,m.InstitutionAcceptanceRecord.gate_key==gate_key))
    if not rec:
        rec=m.InstitutionAcceptanceRecord(environment=environment,gate_key=gate_key)
        db.add(rec); db.flush()
    rec.status=body.status; rec.evidence_ref=body.evidence_ref.strip(); rec.note=body.note.strip(); rec.updated_at=datetime.now(timezone.utc)
    if body.status in {"passed","waived"}:
        ctx=current_user(); rec.verified_by=str(ctx.get("email") or "system"); rec.verified_at=datetime.now(timezone.utc)
    else:
        rec.verified_by=""; rec.verified_at=None
    db.add(m.AuditLog(actor_email=(current_user().get("email") or "system"), actor_roles=list(current_user().get("role_names") or []), action="production_acceptance_update", entity_type="institution_acceptance_record", entity_id=rec.id, payload={"gate_key":gate_key,"status":body.status,"evidence_ref":body.evidence_ref}))
    db.commit(); db.refresh(rec)
    return {"id":rec.id,"gate_key":rec.gate_key,"status":rec.status,"evidence_ref":rec.evidence_ref,"note":rec.note,"verified_by":rec.verified_by,"verified_at":rec.verified_at}
