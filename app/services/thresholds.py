from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m


def active_threshold(db: Session, program_id: int | None, academic_year: str | None, kind: str) -> float | None:
    """Most specific active target: program+year > program > institution+year > institution."""
    rows = db.scalars(select(m.OutcomeThreshold).where(m.OutcomeThreshold.kind == kind, m.OutcomeThreshold.is_active.is_(True))).all()
    best, best_rank = None, -1
    for r in rows:
        if r.program_id not in (None, program_id):
            continue
        if r.academic_year not in ("", academic_year or ""):
            continue
        rank = (2 if r.program_id is not None else 0) + (1 if r.academic_year else 0)
        if rank > best_rank:
            best, best_rank = r, rank
    return float(best.target_percent) if best else None
