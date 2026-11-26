from __future__ import annotations

"""Read-only client for the Proliz/DogusAPI OBS integration.

Real contract (confirmed from the live portalapi.dogus.edu.tr swagger.json,
2026-11-26): HTTP Basic Auth, GET endpoints under /Obs/Genel and /Obs/Ogrenci.
Response bodies are undocumented in the swagger (no schema, just "200 OK"),
so this module intentionally returns raw parsed JSON rather than guessing
field names. Map the raw payload into DOU Assess models (app/models.py
Program/Student external_source="proliz"/external_id, matching the existing
app/services/imports.py pattern) only once a real sample response has been
inspected via the /api/integrations/obs/proliz/probe endpoint.
"""

import base64
import json
from urllib import error as urlerror, parse as urlparse, request as urlrequest

from ..config import settings


class ProlizError(RuntimeError):
    pass


def _auth_header() -> str:
    if not settings.obs_proliz_username or not settings.obs_proliz_password:
        raise ProlizError("OBS_PROLIZ_USERNAME / OBS_PROLIZ_PASSWORD yapılandırılmamış")
    raw = f"{settings.obs_proliz_username}:{settings.obs_proliz_password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _get(path: str, params: dict[str, str] | None = None) -> object:
    if not settings.obs_proliz_base_url:
        raise ProlizError("OBS_PROLIZ_BASE_URL yapılandırılmamış")
    query = ("?" + urlparse.urlencode({k: v for k, v in (params or {}).items() if v is not None})) if params else ""
    url = f"{settings.obs_proliz_base_url}{path}{query}"
    req = urlrequest.Request(url, headers={"Authorization": _auth_header(), "Accept": "application/json"}, method="GET")
    try:
        with urlrequest.urlopen(req, timeout=max(1, settings.obs_proliz_timeout_seconds)) as resp:
            body = resp.read()
    except urlerror.HTTPError as exc:
        raise ProlizError(f"Proliz OBS HTTP {exc.code}: {path}") from exc
    except (urlerror.URLError, TimeoutError, OSError) as exc:
        raise ProlizError(f"Proliz OBS bağlantı hatası: {path}: {exc}") from exc
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProlizError(f"Proliz OBS geçersiz JSON yanıtı: {path}: {exc}") from exc


# --- /Obs/Genel ---

def fetch_akademik_donem() -> object:
    return _get("/Obs/Genel/AkademikDonem")


def fetch_fakulte() -> object:
    return _get("/Obs/Genel/Fakulte")


def fetch_program(fakulte_kod: str | None = None) -> object:
    return _get("/Obs/Genel/Program", {"FakulteKod": fakulte_kod} if fakulte_kod else None)


def fetch_acilan_dersler(donem_id: str | None = None, ders_id: str | None = None) -> object:
    return _get("/Obs/Genel/AcilanDersler", {"DonemId": donem_id, "DersId": ders_id})


def fetch_mufredat() -> object:
    return _get("/Obs/Genel/Mufredat")


def fetch_mufredat_dersler(mufredat_id: str) -> object:
    return _get("/Obs/Genel/MufredatDersler", {"MufredatId": mufredat_id})


def fetch_akademisyen(tck: str) -> object:
    return _get("/Obs/Genel/Akademisyen", {"Tck": tck})


def fetch_akademisyen_verdigi_ders(tck: str, donem_id: str | None = None) -> object:
    return _get("/Obs/Genel/AkademisyenVerdigiDers", {"Tck": tck, "DonemId": donem_id})


def fetch_akademisyen_verdigi_dersi_alan_ogrenci(tck: str, donem_id: str | None = None, ders_id: str | None = None) -> object:
    return _get("/Obs/Genel/AkademisyenVerdigiDersiAlanOgrenci", {"Tck": tck, "DonemId": donem_id, "DersId": ders_id})


def check_akademik_user(user_name: str, password: str) -> object:
    """Validates a teacher's own OBS username/password against Proliz. The call
    itself still authenticates to Proliz with the DOU Assess service account
    (OBS_PROLIZ_USERNAME/PASSWORD); userName/Pass here are the teacher's own
    credentials being checked, passed as Proliz's contract requires.
    NOTE: response shape is unconfirmed (undocumented in swagger) — do not
    build login/session logic on this until a real sample response has been
    inspected (see /api/auth/obs-login design note)."""
    return _get("/Obs/Genel/AkademikUserCheck", {"userName": user_name, "Pass": password})


def fetch_durumu_degisen_akademisyen(degisiklik_baslangic_tarihi: str) -> object:
    return _get("/Obs/Genel/DurumuDegisenAkademisyen", {"degisilikBaslangicTarihi": degisiklik_baslangic_tarihi})


# --- /Obs/Ogrenci ---

def fetch_aktif_ogrenci(
    ogrenci_no: str | None = None, tc_kimlik_no: str | None = None, kayit_neden: str | None = None,
    ogrenim_durum: str | None = None, fak_kod: str | None = None, bolum_id: str | None = None, prog_id: str | None = None,
) -> object:
    return _get("/Obs/Ogrenci/AktifOgrenci", {
        "OgrenciNo": ogrenci_no, "TckimlikNo": tc_kimlik_no, "KayitNeden": kayit_neden,
        "OgrenimDurum": ogrenim_durum, "FakKod": fak_kod, "BolumId": bolum_id, "ProgId": prog_id,
    })


def fetch_alinan_dersler(ogrenci_no: str, donem_id: str | None = None) -> object:
    return _get("/Obs/Ogrenci/AlinanDersler", {"OgrenciNo": ogrenci_no, "DonemId": donem_id})


def fetch_durumu_degisen_ogrenci(baslangic: str, bitis: str | None = None) -> object:
    return _get("/Obs/Ogrenci/DurumuDegisenOgrenci", {"degisilikBaslangicTarihi": baslangic, "degisilikBitisTarihi": bitis})


PROBE_ENDPOINTS = {
    "akademik_donem": fetch_akademik_donem,
    "fakulte": fetch_fakulte,
    "program": fetch_program,
    "mufredat": fetch_mufredat,
}


def probe(name: str) -> object:
    """Call one read-only endpoint and return its raw response, to inspect the
    real field names before writing the Program/Student mapping logic."""
    fn = PROBE_ENDPOINTS.get(name)
    if not fn:
        raise ProlizError(f"Bilinmeyen probe adı: {name}. Geçerli: {', '.join(PROBE_ENDPOINTS)}")
    return fn()
