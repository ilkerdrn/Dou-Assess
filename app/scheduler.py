from __future__ import annotations

import time

from .config import settings
from .db import SessionLocal
from .services.operations import scheduler_tick


def main() -> None:
    interval = max(15, int(settings.scheduler_interval_seconds))
    print(f"[scheduler] starting interval={interval}s", flush=True)
    while True:
        started = time.monotonic()
        with SessionLocal() as db:
            try:
                result = scheduler_tick(db)
                print(f"[scheduler] tick={result}", flush=True)
            except Exception as exc:
                db.rollback(); print(f"[scheduler] error: {type(exc).__name__}: {exc}", flush=True)
        elapsed = time.monotonic() - started
        time.sleep(max(1.0, interval - elapsed))


if __name__ == "__main__":
    main()
