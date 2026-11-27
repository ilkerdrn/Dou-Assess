"""Versioned institution/program success thresholds (LO default target, PO target)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models as m
from .authz import current_user, require_program_access, require_roles
from .db import get_db

router = APIRouter()


class ThresholdCreate(BaseModel):
    program_id: int | None = None
    academic_year: str = Field(default="", max_length=32)
    kind: Literal["lo", "po"]
    target_percent: float = Field(ge=0, le=100)
    note: str = Field(default="", max_length=1000)


def _out(x: m.OutcomeThreshold) -> dict:
    return {"id": x.id, "program_id": x.program_id, "academic_year": x.academic_year, "kind": x.kind, "target_percent": x.target_percent,
            "version_no": x.version_no, "is_active": x.is_active, "note": x.note, "created_by": x.created_by,
            "created_at": x.created_at.isoformat() if x.created_at else None}


@router.get("/api/outcome-thresholds")
def list_thresholds(program_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(m.OutcomeThreshold).order_by(m.OutcomeThreshold.kind, m.OutcomeThreshold.id.desc())
    if program_id:
        stmt = stmt.where((m.OutcomeThreshold.program_id == program_id) | (m.OutcomeThreshold.program_id.is_(None)))
    return [_out(x) for x in db.scalars(stmt).all()]


@router.post("/api/outcome-thresholds", status_code=201)
def create_threshold(body: ThresholdCreate, db: Session = Depends(get_db)):
    """Creates a new version; the previous active version of the same scope stops applying (history is kept)."""
    if body.program_id:
        require_program_access(db, body.program_id, write=True)
    else:
        require_roles("admin", "quality")
    scope = [m.OutcomeThreshold.kind == body.kind, m.OutcomeThreshold.academic_year == body.academic_year,
             m.OutcomeThreshold.program_id == body.program_id if body.program_id else m.OutcomeThreshold.program_id.is_(None)]
    last = db.scalar(select(func.max(m.OutcomeThreshold.version_no)).where(*scope)) or 0
    for old in db.scalars(select(m.OutcomeThreshold).where(*scope, m.OutcomeThreshold.is_active.is_(True))).all():
        old.is_active = False
    row = m.OutcomeThreshold(program_id=body.program_id, academic_year=body.academic_year, kind=body.kind, target_percent=body.target_percent,
                             version_no=last + 1, note=body.note.strip(), created_by=current_user().get("email") or "system")
    db.add(row); db.flush()
    db.add(m.AuditLog(actor_user_id=current_user().get("id"), actor_email=row.created_by, actor_roles=list(current_user().get("role_names") or []),
                      action="outcome_threshold_create", entity_type="outcome_threshold", entity_id=row.id, payload=_out(row)))
    db.commit()
    return _out(row)
