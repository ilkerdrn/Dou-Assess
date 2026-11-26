from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..config import settings
from ..security import verify_stored_file


def scan_evidence_integrity(db: Session) -> dict:
    """Verify every persisted evidence payload without depending on HTTP context."""
    now = datetime.now(timezone.utc)
    counts = {"verified": 0, "mismatch": 0, "missing": 0, "unchecked": 0}
    failures: list[dict] = []
    exam_root = Path(settings.evidence_storage_path)
    quality_root = exam_root / "quality360"
    controlled_root = quality_root / "controlled-documents"

    def record(obj, entity_type: str, path: Path | None, *, text_payload: str | None = None):
        if path is not None:
            status, actual = verify_stored_file(path, obj.sha256)
        else:
            actual = sha256((text_payload or "").encode("utf-8")).hexdigest()
            status = "verified" if actual == (obj.sha256 or "") else "mismatch"
        obj.integrity_status = status
        obj.integrity_checked_at = now
        counts[status] = counts.get(status, 0) + 1
        if status != "verified":
            failures.append({
                "entity_type": entity_type,
                "id": obj.id,
                "status": status,
                "expected_sha256": obj.sha256,
                "actual_sha256": actual,
            })

    for obj in db.scalars(select(m.EvidenceAsset).order_by(m.EvidenceAsset.id)).all():
        record(obj, "evidence", exam_root / obj.stored_name)
    for obj in db.scalars(select(m.QualityEvidenceAsset).order_by(m.QualityEvidenceAsset.id)).all():
        record(obj, "quality_evidence", quality_root / obj.stored_name)
    for obj in db.scalars(select(m.ControlledDocumentRevision).order_by(m.ControlledDocumentRevision.id)).all():
        record(
            obj,
            "controlled_document_revision",
            controlled_root / obj.stored_name if obj.stored_name else None,
            text_payload=obj.content_text,
        )
    return {
        "status": "pass" if not failures else "failed",
        "checked": sum(counts.values()),
        "counts": counts,
        "failures": failures[:200],
        "failure_count": len(failures),
        "checked_at": now.isoformat(),
    }
