from __future__ import annotations

import os
import socket
import time

from .config import settings
from .db import SessionLocal
from .services.operations import claim_next_job, execute_job, recover_stale_jobs


def main() -> None:
    worker_id = os.getenv("WORKER_ID", "").strip() or f"{socket.gethostname()}:{os.getpid()}"
    poll = max(0.5, float(settings.job_poll_seconds))
    print(f"[worker] starting id={worker_id} poll={poll}s", flush=True)
    last_recovery = 0.0
    while True:
        now = time.monotonic()
        if now - last_recovery > 60:
            with SessionLocal() as db:
                try:
                    recovered = recover_stale_jobs(db)
                    db.commit()
                    if recovered:
                        print(f"[worker] recovered_stale={recovered}", flush=True)
                except Exception as exc:
                    db.rollback(); print(f"[worker] stale recovery error: {exc}", flush=True)
            last_recovery = now
        with SessionLocal() as db:
            try:
                job = claim_next_job(db, worker_id)
            except Exception as exc:
                db.rollback(); print(f"[worker] claim error: {exc}", flush=True); time.sleep(poll); continue
            if not job:
                time.sleep(poll); continue
            print(f"[worker] job={job.id} type={job.job_type} attempt={job.attempts}/{job.max_attempts}", flush=True)
            try:
                execute_job(db, job)
                print(f"[worker] job={job.id} succeeded", flush=True)
            except Exception as exc:
                print(f"[worker] job={job.id} failed: {type(exc).__name__}: {exc}", flush=True)


if __name__ == "__main__":
    main()
