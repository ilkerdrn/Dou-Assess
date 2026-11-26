from __future__ import annotations

"""Client for the Proliz/DogusAPI OBS integration (Üniversite Öğrenci Bilgi
Sistemi REST API Dokümanı v3.1, confirmed against the live server).

Auth: every call authenticates to Proliz with the DOU Assess service account
(OBS_PROLIZ_USERNAME/PASSWORD, HTTP Basic). The *UserCheck endpoints also take
a teacher's/student's own username+password as query parameters — those are
the credentials being validated, not used for the Basic Auth header itself.

Password hashing for *UserCheck: per the official doc, Pass must be
UTF-8 -> MD5 -> uppercase hex, never the plaintext password. Use
`hash_obs_password()`.

Known real response field names (from the v3.1 PDF, 2026-11-26):
- AkademikDonem (bulk, no params): ID, AD, YIL, TIP, BAS_TARIH, BIT_TARIH,
  AD_EN, TIP_EN, DURUM
- Fakulte (bulk, no params): KOD, AD, SURE, TIP, AD_EN, TIP_EN
- Program (FakulteKod optional -> bulk if empty): ID, KOD, AD, FAK_KOD,
  KISA_AD, PROG_TIP, PROG_TUR, NORMAL_SURE, AZAMI_SURE, DURUM, AD_EN,
  PROG_TIP_EN, PROG_TUR_EN
- Akademisyen (Tck optional -> bulk if empty): TCK, SICIL_NO, AD, SOYAD,
  FAKULTE_KOD, FAKULTE_AD, BOLUM_ID, BOLUM_AD, PROG_ID, PROG_AD, EPOSTA, GSM,
  UNVAN_KOD, UNVAN_AD, DEGISIKLIK_TAR, PERSONEL_TIP (+ _EN variants)
- AkademisyenVerdigiDers (Tck, DonemId): DERS_ID, DERS_KOD, DERS_AD, SUBE_KOD,
  TEO_SAAT, UYG_SAAT, AKTS, KREDI, SINIF, FAKULTE_KOD, FAKULTE_AD, BOLUM_ID,
  BOLUM_AD, PROG_ID, PROG_AD (+ _EN variants)
- AkademisyenVerdigiDersiAlanOgrenci (Tck, DonemId, DersId optional): ID,
  OGR_NO, DERS_ID, DERS_KOD, SUBE_KOD, DERS_AD, KREDI, AKTS, ALMA_TIP,
  OGR_KAYIT_TARIH, DAN_ONAY_TARIH, GECME_DURUM (+ _EN variants)
- AktifOgrenci / AyrilanOgrenci (all filters optional -> bulk if empty):
  OGR_NO, OGR_NO_ONCK, TCK, AD, SOYAD, FAK_KOD, BOL_ID, PROG_ID, SINIF,
  KAY_NEDEN, KAY_TAR, OGRENIM_DURUM, OGRENIM_TIP, MUFREDAT_ID (+ many more)
- Mufredat (bulk, no params): MUFREDAT_ID, MUFREDAT_AD, YIL, DURUM, FAKULTE,
  BOLUM, PROGRAM_AD, FAK_KOD, BOLUM_ID, PROG_ID
- MufredatDersler (MufredatId): MUF_DERS_ID, DERS_KOD, DERS_AD, AKTS,
  FAKULTE_AD, FAKULTE_KOD, BOLUM_AD, BOLUM_ID, PROG_AD, PROG_ID, DONEM_TIP,
  SINIF
- AkademikUserCheck / OgrenciUserCheck: {"SonucDurum": "true"|"false",
  "SonucAciklama": "..."}. userName is the Sicil No (teacher) or Öğrenci No
  (student) — NOT the Tck/email. No identity fields are returned; resolve
  identity separately via Akademisyen (by SICIL_NO) or Ogrenci/Kimlik.
- Ogrenci/Kimlik (OgrenciNo optional -> bulk if empty): KIMLIK_TCNO,
  KIMLIK_AD, KIMLIK_SOYAD, CINSIYET, DOGUM_TAR, ...
- Ogrenci/Iletisim (OgrenciNo optional -> bulk if empty): OGR_NO, EPOSTA1,
  EPOSTA2, GSM1, GSM2, ...
- Ogrenci/AlinanDersler (OgrenciNo, DonemId): OGR_NO, DERS_ID, DERS_KOD,
  DERS_AD, ALMA_TIP, GECME_DURUM
- Ogrenci/SinavNot (OgrenciNo, DonemId, DersId optional): SINAV_AD,
  SINAV_TIP, SINAV_GIRME_TIP, NOT_DEGER
- Ogrenci/OgrenciDersProgrami (OgrenciNo, DonemId): DERS_ID, GUN, DERS_KOD,
  DERS_AD, BAS_SAAT, BIT_SAAT, DERSLIK, OE_TCK
"""

import base64
import hashlib
import json
from urllib import error as urlerror, parse as urlparse, request as urlrequest

from ..config import settings


class ProlizError(RuntimeError):
    pass


def hash_obs_password(password: str) -> str:
    """UTF-8 -> MD5 -> uppercase hex, exactly as the Proliz doc specifies for
    AkademikUserCheck / OgrenciUserCheck 'Pass'. Never send a plaintext
    password to those endpoints."""
    return hashlib.md5(password.encode("utf-8")).hexdigest().upper()


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


def fetch_akademisyen(tck: str | None = None) -> object:
    """Empty tck returns the full academic staff roster (SICIL_NO + TCK +
    EPOSTA among the fields) — used to resolve a Sicil No login to a Tck."""
    return _get("/Obs/Genel/Akademisyen", {"Tck": tck} if tck else None)


def fetch_akademisyen_verdigi_ders(tck: str, donem_id: str | None = None) -> object:
    return _get("/Obs/Genel/AkademisyenVerdigiDers", {"Tck": tck, "DonemId": donem_id})


def fetch_akademisyen_verdigi_dersi_alan_ogrenci(tck: str, donem_id: str | None = None, ders_id: str | None = None) -> object:
    return _get("/Obs/Genel/AkademisyenVerdigiDersiAlanOgrenci", {"Tck": tck, "DonemId": donem_id, "DersId": ders_id})


def check_akademik_user(user_name: str, password_hash: str) -> dict:
    """userName = Sicil No. password_hash must already be hash_obs_password()
    output, not a plaintext password. Returns {"SonucDurum": "true"/"false",
    "SonucAciklama": "..."}."""
    return _get("/Obs/Genel/AkademikUserCheck", {"userName": user_name, "Pass": password_hash})


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


def fetch_kimlik(ogrenci_no: str | None = None) -> object:
    return _get("/Obs/Ogrenci/Kimlik", {"OgrenciNo": ogrenci_no} if ogrenci_no else None)


def fetch_iletisim(ogrenci_no: str | None = None) -> object:
    return _get("/Obs/Ogrenci/Iletisim", {"OgrenciNo": ogrenci_no} if ogrenci_no else None)


def fetch_alinan_dersler(ogrenci_no: str, donem_id: str | None = None) -> object:
    return _get("/Obs/Ogrenci/AlinanDersler", {"OgrenciNo": ogrenci_no, "DonemId": donem_id})


def fetch_sinav_not(ogrenci_no: str, donem_id: str | None = None, ders_id: str | None = None) -> object:
    return _get("/Obs/Ogrenci/SinavNot", {"OgrenciNo": ogrenci_no, "DonemId": donem_id, "DersId": ders_id})


def fetch_ogrenci_ders_programi(ogrenci_no: str, donem_id: str | None = None) -> object:
    return _get("/Obs/Ogrenci/OgrenciDersProgrami", {"OgrenciNo": ogrenci_no, "DonemId": donem_id})


def check_ogrenci_user(user_name: str, password_hash: str) -> dict:
    """userName = Öğrenci No. password_hash must already be
    hash_obs_password() output. Returns {"SonucDurum": "true"/"false",
    "SonucAciklama": "..."}."""
    return _get("/Obs/Ogrenci/OgrenciUserCheck", {"userName": user_name, "Pass": password_hash})


def fetch_durumu_degisen_ogrenci(baslangic: str, bitis: str | None = None) -> object:
    return _get("/Obs/Ogrenci/DurumuDegisenOgrenci", {"degisilikBaslangicTarihi": baslangic, "degisilikBitisTarihi": bitis})


PROBE_ENDPOINTS = {
    "akademik_donem": fetch_akademik_donem,
    "fakulte": fetch_fakulte,
    "program": fetch_program,
    "mufredat": fetch_mufredat,
    "akademisyen_all": fetch_akademisyen,
}


def probe(name: str) -> object:
    """Call one read-only, no-argument endpoint and return its raw response."""
    fn = PROBE_ENDPOINTS.get(name)
    if not fn:
        raise ProlizError(f"Bilinmeyen probe adı: {name}. Geçerli: {', '.join(PROBE_ENDPOINTS)}")
    return fn()
