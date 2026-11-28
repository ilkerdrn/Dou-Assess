"""Demo verisini (DEMO-BP programı ve "2099-2100 Demo" dönemi) temizler.

Varsayılan: yalnızca ne silineceğini listeler (kuru çalıştırma).
Silmek için: python tools/cleanup_demo_data.py --apply   (önce veritabanı yedeği alın)

Yalnızca kodu DEMO ile başlayan programlar, bunlara bağlı alt kayıtlar ve
başka hiçbir kaydı olmayan demo akademik dönemi silinir.
"""
import argparse, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import delete, select, text
from app.db import SessionLocal, Base
from app import models as m


def collect(db, roots):
    """roots: {table_name: set(ids)} -> FK ile aşağı doğru tüm bağlı satırlar."""
    tables = {t.name: t for t in Base.metadata.sorted_tables}
    found = defaultdict(set)
    for k, v in roots.items():
        found[k] |= set(v)
    changed = True
    while changed:
        changed = False
        for t in tables.values():
            pk = [c for c in t.primary_key.columns]
            if len(pk) != 1:
                continue
            for fk in t.foreign_keys:
                parent = fk.column.table.name
                if parent == t.name or parent not in found or not found[parent]:
                    continue
                rows = db.execute(select(pk[0]).where(fk.parent.in_(found[parent]))).scalars().all()
                new = set(rows) - found[t.name]
                if new:
                    found[t.name] |= new
                    changed = True
    return found, tables


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    db = SessionLocal()
    progs = db.scalars(select(m.Program).where(m.Program.code.like("DEMO%"))).all()
    roots = {"programs": {p.id for p in progs}}
    found, tables = collect(db, roots)
    # Demo dönemi: başka hiçbir kaydı olmayan "Demo" dönemi
    periods = [p for p in db.scalars(select(m.AcademicPeriod).where(m.AcademicPeriod.term == "Demo")).all()]
    print("Silinecek programlar:", [p.code for p in progs] or "yok")
    for name, ids in sorted(found.items()):
        if ids:
            print(f"  {name}: {len(ids)} kayıt")
    print("Demo dönemleri:", [f"{p.academic_year} {p.term}" for p in periods] or "yok")
    if not a.apply:
        print("\nKuru çalıştırma — hiçbir şey silinmedi. Silmek için --apply ekleyin.")
        return
    order = [t for t in reversed(Base.metadata.sorted_tables) if found.get(t.name)]
    for t in order:
        pk = list(t.primary_key.columns)[0]
        db.execute(delete(t).where(pk.in_(found[t.name])))
    for p in periods:
        used = False
        for t in Base.metadata.sorted_tables:
            for fk in t.foreign_keys:
                if fk.column.table.name == "academic_periods" and db.execute(select(fk.parent).where(fk.parent == p.id).limit(1)).first():
                    used = True
        if not used:
            db.delete(p)
        else:
            print(f"Dönem {p.academic_year} başka kayıtlarca kullanıldığı için bırakıldı.")
    db.commit()
    print("Demo verisi silindi.")


if __name__ == "__main__":
    main()
