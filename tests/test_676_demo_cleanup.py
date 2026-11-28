import sys, runpy
from pathlib import Path
from sqlalchemy import select
from tests.test_674_evaluator_room import client, _setup  # noqa
from app.db import SessionLocal
from app import models as m

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cleanup_demo_data.py"


def _run(*args):
    old = sys.argv
    sys.argv = [str(TOOL), *args]
    try:
        runpy.run_path(str(TOOL), run_name="__main__")
    finally:
        sys.argv = old


def test_demo_cleanup_dry_run_then_apply(capsys):
    program, *_ = _setup()  # gerçek veri: silinmemeli
    r = client.post("/api/pilot/demo-scenario")
    assert r.status_code in (200, 201)
    _run()
    out = capsys.readouterr().out
    assert "DEMO-BP" in out and "Kuru çalıştırma" in out
    with SessionLocal() as db:
        assert db.scalar(select(m.Program).where(m.Program.code == "DEMO-BP"))
    _run("--apply")
    with SessionLocal() as db:
        assert not db.scalar(select(m.Program).where(m.Program.code == "DEMO-BP"))
        assert db.get(m.Program, program["id"]) is not None
