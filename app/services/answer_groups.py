"""Yazılı (metin olarak girilmiş) klasik cevapları benzerliğe göre gruplar.

Tamamen yerel çalışır: dış servise, yapay zekâ sağlayıcısına veri gitmez (KVKK açısından güvenli).
TF-IDF + kosinüs benzerliği; eşik üzerindeki cevaplar aynı gruba girer.
"""
from __future__ import annotations

import math
import re
from collections import Counter

_TR = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusocIGUSOC")
_STOP = {"ve", "veya", "ile", "bir", "bu", "su", "icin", "gibi", "daha", "olarak", "olan", "den", "dan", "de", "da", "ki", "mi", "ne", "en", "cok", "her", "ama", "fakat", "ise", "the", "and", "of", "to", "is"}


def tokens(text: str) -> list[str]:
    t = (text or "").translate(_TR).lower()
    out = []
    for w in re.findall(r"[a-z0-9]+", t):
        if len(w) < 3 or w in _STOP:
            continue
        out.append(w[:6] if len(w) > 6 else w)  # kaba kök: ekleri törpüler
    return out


def _vec(tf: Counter, idf: dict[str, float]) -> dict[str, float]:
    v = {w: c * idf.get(w, 1.0) for w, c in tf.items()}
    n = math.sqrt(sum(x * x for x in v.values())) or 1.0
    return {w: x / n for w, x in v.items()}


def _cos(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(w, 0.0) for w, x in a.items())


def group_answers(items: list[dict], threshold: float = 0.55) -> list[dict]:
    """items: [{"id": ..., "text": ...}] -> gruplar (büyükten küçüğe). Boş cevaplar 'bos' grubuna girer."""
    threshold = min(max(float(threshold), 0.2), 0.95)
    blanks = [x for x in items if not tokens(x["text"])]
    real = [x for x in items if tokens(x["text"])]
    docs = [Counter(tokens(x["text"])) for x in real]
    df: Counter = Counter()
    for d in docs:
        df.update(d.keys())
    n = max(1, len(docs))
    idf = {w: math.log((1 + n) / (1 + c)) + 1.0 for w, c in df.items()}
    vecs = [_vec(d, idf) for d in docs]
    order = sorted(range(len(real)), key=lambda i: -len(real[i]["text"]))
    groups: list[dict] = []
    for i in order:
        best, best_s = None, 0.0
        for g in groups:
            s = _cos(vecs[i], g["vec"])
            if s > best_s:
                best, best_s = g, s
        if best is not None and best_s >= threshold:
            best["members"].append(real[i])
        else:
            groups.append({"vec": vecs[i], "members": [real[i]]})
    result = [{"size": len(g["members"]), "sample": g["members"][0]["text"], "members": g["members"]} for g in groups]
    result.sort(key=lambda g: -g["size"])
    if blanks:
        result.append({"size": len(blanks), "sample": "(boş cevap)", "members": blanks, "blank": True})
    for k, g in enumerate(result, 1):
        g["group_no"] = k
    return result
