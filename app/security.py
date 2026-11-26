from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
import hashlib
import ipaddress
import re
import threading
import time
import uuid
import zipfile

from fastapi import HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from sqlalchemy.orm import Session

from .config import Settings, settings
from . import models as m

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,96}$")
_UPLOAD_PATH_RE = re.compile(r"^/api/(?:import/|integrations/obs/workbook/|exams/\d+/(?:scans(?:-batch)?|evidence))")
_RATE_LOCK = threading.Lock()
_RATE_BUCKETS: dict[tuple[str, str], deque[float]] = {}
_RATE_LAST_SWEEP = 0.0


def request_id_for(request: Request) -> str:
    supplied = (request.headers.get("X-Request-ID") or "").strip()
    if supplied and _REQUEST_ID_RE.fullmatch(supplied):
        return supplied
    return uuid.uuid4().hex


def _peer_ip(request: Request) -> str:
    return (request.client.host if request.client else "").strip()


def _ip_in_configured_cidrs(ip_text: str, cidrs: tuple[str, ...]) -> bool:
    if not ip_text:
        return False
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return False
    for raw in cidrs:
        try:
            network = ipaddress.ip_network(raw, strict=False)
        except ValueError:
            continue
        if ip in network:
            return True
    return False


def proxy_headers_trusted(request: Request) -> bool:
    if not settings.trust_proxy_headers:
        return False
    if settings.trusted_proxy_cidrs:
        return _ip_in_configured_cidrs(_peer_ip(request), settings.trusted_proxy_cidrs)
    # Pilot/local keeps backwards-compatible proxy support. Production must declare CIDRs.
    return settings.app_env != "production"


def request_is_https(request: Request) -> bool:
    if proxy_headers_trusted(request):
        forwarded = (request.headers.get("X-Forwarded-Proto") or "").split(",", 1)[0].strip().lower()
        if forwarded:
            return forwarded == "https"
    return request.url.scheme == "https"


def _host_only(raw: str) -> str:
    raw = (raw or "").strip().lower()
    if raw.startswith("[") and "]" in raw:  # IPv6 literal
        return raw.split("]", 1)[0] + "]"
    return raw.split(":", 1)[0]


def allowed_host(request: Request) -> bool:
    path = request.url.path
    host = _host_only(request.headers.get("host") or request.url.hostname or "")
    if path in {"/api/health", "/api/ready"} and host in {"127.0.0.1", "localhost", "api", "testserver"}:
        return True
    configured = {x.casefold() for x in settings.allowed_hosts}
    if settings.public_hostname:
        configured.add(settings.public_hostname.casefold())
    if not configured:
        return settings.app_env != "production"
    return host.casefold() in configured


def production_security_issues(cfg: Settings = settings) -> list[str]:
    if cfg.app_env != "production":
        return []
    issues: list[str] = []
    if cfg.database_url.startswith("sqlite"):
        issues.append("Production ortamında SQLite kullanılamaz")
    if not cfg.auth_required:
        issues.append("Production ortamında AUTH_REQUIRED=true olmalıdır")
    if cfg.auth_provider != "entra":
        issues.append("Production ortamında AUTH_PROVIDER=entra olmalıdır")
    if not cfg.entra_tenant_id:
        issues.append("ENTRA_TENANT_ID zorunludur")
    if not cfg.entra_client_id:
        issues.append("ENTRA_CLIENT_ID zorunludur")
    if not cfg.entra_audience:
        issues.append("ENTRA_AUDIENCE zorunludur")
    if not cfg.entra_allowed_client_ids:
        issues.append("ENTRA_ALLOWED_CLIENT_IDS ile çağrı yapabilecek istemciler sınırlandırılmalıdır")
    if not cfg.entra_required_scopes:
        issues.append("ENTRA_REQUIRED_SCOPES production ortamında zorunludur")
    if not cfg.entra_login_scopes:
        issues.append("ENTRA_LOGIN_SCOPES tarayıcı kurumsal giriş akışı için zorunludur")
    if not cfg.entra_redirect_uri:
        issues.append("ENTRA_REDIRECT_URI tarayıcı kurumsal giriş akışı için zorunludur")
    elif not cfg.entra_redirect_uri.lower().startswith("https://"):
        issues.append("ENTRA_REDIRECT_URI production ortamında HTTPS olmalıdır")
    if cfg.entra_auto_link_by_email:
        issues.append("Production ortamında ENTRA_AUTO_LINK_BY_EMAIL=false olmalıdır")
    if not cfg.public_hostname:
        issues.append("PUBLIC_HOSTNAME zorunludur")
    if not cfg.require_https:
        issues.append("Production ortamında REQUIRE_HTTPS=true olmalıdır")
    if not cfg.security_headers:
        issues.append("Production ortamında SECURITY_HEADERS=true olmalıdır")
    if not cfg.strict_production_security:
        issues.append("Production ortamında STRICT_PRODUCTION_SECURITY=true olmalıdır")
    if not cfg.trust_proxy_headers:
        issues.append("Production reverse proxy mimarisinde TRUST_PROXY_HEADERS=true olmalıdır")
    elif not cfg.trusted_proxy_cidrs:
        issues.append("TRUST_PROXY_HEADERS açıkken TRUSTED_PROXY_CIDRS production ortamında zorunludur")
    else:
        invalid_cidrs = []
        for raw in cfg.trusted_proxy_cidrs:
            try:
                ipaddress.ip_network(raw, strict=False)
            except ValueError:
                invalid_cidrs.append(raw)
        if invalid_cidrs:
            issues.append("TRUSTED_PROXY_CIDRS içinde geçersiz ağ tanımı var: " + ", ".join(invalid_cidrs[:3]))
    if not cfg.rate_limit_enabled:
        issues.append("Production ortamında RATE_LIMIT_ENABLED=true olmalıdır")
    if cfg.api_rate_limit_per_minute < 60 or cfg.api_rate_limit_per_minute > 6000:
        issues.append("API_RATE_LIMIT_PER_MINUTE 60-6000 aralığında olmalıdır")
    if cfg.upload_rate_limit_per_minute < 1 or cfg.upload_rate_limit_per_minute > 300:
        issues.append("UPLOAD_RATE_LIMIT_PER_MINUTE 1-300 aralığında olmalıdır")
    if cfg.max_upload_mb <= 0 or cfg.max_upload_mb > 100:
        issues.append("MAX_UPLOAD_MB 1-100 aralığında olmalıdır")
    if cfg.max_batch_upload_mb < cfg.max_upload_mb or cfg.max_batch_upload_mb > 500:
        issues.append("MAX_BATCH_UPLOAD_MB tek dosya limitinden küçük olamaz ve 500 MB'ı aşamaz")
    if cfg.max_batch_files < 1 or cfg.max_batch_files > 100:
        issues.append("MAX_BATCH_FILES 1-100 aralığında olmalıdır")
    if cfg.max_request_mb < cfg.max_batch_upload_mb:
        issues.append("MAX_REQUEST_MB, MAX_BATCH_UPLOAD_MB değerinden küçük olamaz")
    if cfg.max_pdf_pages < 1 or cfg.max_pdf_pages > 1000:
        issues.append("MAX_PDF_PAGES 1-1000 aralığında olmalıdır")
    if cfg.max_image_megapixels < 1 or cfg.max_image_megapixels > 200:
        issues.append("MAX_IMAGE_MEGAPIXELS 1-200 aralığında olmalıdır")
    if cfg.db_pool_size < 2 or cfg.db_pool_size > 50:
        issues.append("DB_POOL_SIZE 2-50 aralığında olmalıdır")
    if cfg.db_max_overflow < 0 or cfg.db_max_overflow > 100:
        issues.append("DB_MAX_OVERFLOW 0-100 aralığında olmalıdır")
    if cfg.db_statement_timeout_ms < 1000 or cfg.db_statement_timeout_ms > 300000:
        issues.append("DB_STATEMENT_TIMEOUT_MS 1000-300000 aralığında olmalıdır")
    return issues


def production_security_warnings(cfg: Settings = settings) -> list[str]:
    warnings: list[str] = []
    if cfg.app_env == "production" and not cfg.entra_require_delegated_user:
        warnings.append("ENTRA_REQUIRE_DELEGATED_USER=false; uygulama-only tokenlar ayrıca değerlendirilmelidir")
    if cfg.app_env == "production" and cfg.max_request_mb > 128:
        warnings.append("MAX_REQUEST_MB 128 MB üzerinde; reverse proxy/body limitini ayrıca gözden geçirin")
    if cfg.app_env == "production" and cfg.db_pool_size + cfg.db_max_overflow > 40:
        warnings.append("Tek worker için DB bağlantı havuzu 40'ın üzerinde; PostgreSQL max_connections ile doğrulayın")
    return warnings


def enforce_production_security(cfg: Settings = settings) -> None:
    # Production güvenlik kuralları runtime'da bayrakla devre dışı bırakılamaz.
    if cfg.app_env == "production":
        issues = production_security_issues(cfg)
        if issues:
            raise RuntimeError("Production security preflight başarısız: " + " | ".join(issues))


def security_headers(response, request: Request, request_id: str) -> None:
    response.headers["X-Request-ID"] = request_id
    if not settings.security_headers:
        return
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    csp = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; "
        "connect-src 'self' https://login.microsoftonline.com; object-src 'none'; base-uri 'self'; "
        "frame-ancestors 'none'; form-action 'self'"
    )
    if settings.app_env == "production":
        csp += "; upgrade-insecure-requests"
    response.headers["Content-Security-Policy"] = csp
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    elif request.url.path in {"/", "/index.html", "/app.js", "/styles.css"}:
        # UI hotfixes must never run against a stale JS/CSS shell from a previous build.
        response.headers["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
    if request_is_https(request):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"


def client_ip(request: Request) -> str:
    if proxy_headers_trusted(request):
        forwarded = (request.headers.get("X-Forwarded-For") or "").split(",", 1)[0].strip()
        if forwarded:
            try:
                return str(ipaddress.ip_address(forwarded))[:64]
            except ValueError:
                pass
    return _peer_ip(request)[:64]


def _rate_category(request: Request) -> str:
    if request.method.upper() in {"POST", "PUT", "PATCH"} and _UPLOAD_PATH_RE.match(request.url.path):
        return "upload"
    return "api"


def rate_limit_check(request: Request) -> tuple[bool, int, int, str]:
    """Return (allowed, retry_after_seconds, limit, category).

    This is intentionally a lightweight process-local safety net. Production NGINX
    remains the cross-request first line of defense; this guard protects direct API
    access and pilot deployments where NGINX rules may be bypassed accidentally.
    """
    if not settings.rate_limit_enabled or not request.url.path.startswith("/api/"):
        return True, 0, 0, "disabled"
    if request.url.path in {"/api/health", "/api/ready", "/api/auth/config"}:
        return True, 0, 0, "public"
    category = _rate_category(request)
    limit = settings.upload_rate_limit_per_minute if category == "upload" else settings.api_rate_limit_per_minute
    if limit <= 0:
        return True, 0, limit, category
    now = time.monotonic()
    window_start = now - 60.0
    key = (client_ip(request) or "unknown", category)
    global _RATE_LAST_SWEEP
    with _RATE_LOCK:
        bucket = _RATE_BUCKETS.setdefault(key, deque())
        while bucket and bucket[0] <= window_start:
            bucket.popleft()
        if len(bucket) >= limit:
            retry = max(1, int(61 - (now - bucket[0])))
            return False, retry, limit, category
        bucket.append(now)
        if now - _RATE_LAST_SWEEP >= settings.rate_limit_bucket_ttl_seconds:
            stale_before = now - max(60, settings.rate_limit_bucket_ttl_seconds)
            for stale_key in list(_RATE_BUCKETS):
                q = _RATE_BUCKETS[stale_key]
                while q and q[0] < stale_before:
                    q.popleft()
                if not q:
                    _RATE_BUCKETS.pop(stale_key, None)
            _RATE_LAST_SWEEP = now
    return True, 0, limit, category


def reset_rate_limiter_for_tests() -> None:
    global _RATE_LAST_SWEEP
    with _RATE_LOCK:
        _RATE_BUCKETS.clear()
        _RATE_LAST_SWEEP = 0.0


def add_security_event(
    db: Session,
    event_type: str,
    *,
    severity: str = "info",
    request_id: str = "",
    request: Request | None = None,
    actor_email: str = "",
    detail: dict[str, Any] | None = None,
) -> None:
    row = m.SecurityEvent(
        event_type=event_type[:64], severity=severity[:16], request_id=request_id[:96],
        actor_email=(actor_email or "")[:255], remote_addr=client_ip(request) if request else "",
        method=(request.method if request else "")[:16], path=(request.url.path if request else "")[:512],
        detail=detail or {}, created_at=datetime.now(timezone.utc),
    )
    db.add(row)


async def read_upload_limited(file: UploadFile, *, limit_mb: int | None = None) -> bytes:
    limit = int(limit_mb or settings.max_upload_mb) * 1024 * 1024
    total = 0
    chunks: list[bytes] = []
    while True:
        chunk = await file.read(min(1024 * 1024, limit + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(413, f"Dosya en fazla {int(limit_mb or settings.max_upload_mb)} MB olabilir")
        chunks.append(chunk)
    return b"".join(chunks)


def validate_xlsx_container(data: bytes) -> None:
    if not data.startswith(b"PK"):
        raise HTTPException(400, "Excel dosyası geçerli XLSX/ZIP yapısında değil")
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            infos = zf.infolist()
            if len(infos) > settings.max_xlsx_members:
                raise HTTPException(413, f"Excel arşivinde en fazla {settings.max_xlsx_members} parça olabilir")
            total_uncompressed = 0
            total_compressed = 0
            for info in infos:
                name = info.filename.replace("\\", "/")
                if info.flag_bits & 0x1:
                    raise HTTPException(400, "Şifreli Excel arşivleri kabul edilmez")
                if name.startswith("/") or "../" in f"/{name}":
                    raise HTTPException(400, "Excel arşivinde güvenli olmayan dosya yolu bulundu")
                total_uncompressed += int(info.file_size)
                total_compressed += int(info.compress_size)
            limit = settings.max_xlsx_uncompressed_mb * 1024 * 1024
            if total_uncompressed > limit:
                raise HTTPException(413, f"Excel açıldığında en fazla {settings.max_xlsx_uncompressed_mb} MB olabilir")
            if total_uncompressed > 5 * 1024 * 1024 and total_uncompressed / max(total_compressed, 1) > 200:
                raise HTTPException(400, "Excel arşivi olağandışı sıkıştırma oranı nedeniyle reddedildi")
            names = {x.filename for x in infos}
            if "[Content_Types].xml" not in names or not any(x.startswith("xl/") for x in names):
                raise HTTPException(400, "Dosya geçerli bir XLSX çalışma kitabı değil")
    except HTTPException:
        raise
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "Excel dosyası bozuk veya geçersiz") from exc


def validate_pdf_payload(data: bytes, *, purpose: str = "PDF") -> int:
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, f"{purpose} içeriği geçerli PDF değil")
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise HTTPException(400, f"Şifreli {purpose} dosyaları kabul edilmez")
        pages = len(reader.pages)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"{purpose} dosyası bozuk veya okunamıyor") from exc
    if pages < 1:
        raise HTTPException(400, f"{purpose} içinde okunabilir sayfa yok")
    if pages > settings.max_pdf_pages:
        raise HTTPException(413, f"{purpose} en fazla {settings.max_pdf_pages} sayfa olabilir")
    return pages


def validate_image_payload(data: bytes, *, purpose: str = "Görsel") -> tuple[int, int]:
    try:
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, f"{purpose} dosyası bozuk veya okunamıyor") from exc
    pixels = int(width) * int(height)
    max_pixels = settings.max_image_megapixels * 1_000_000
    if width < 1 or height < 1:
        raise HTTPException(400, f"{purpose} boyutları geçersiz")
    if pixels > max_pixels:
        raise HTTPException(413, f"{purpose} en fazla {settings.max_image_megapixels} megapiksel olabilir")
    return int(width), int(height)




_DOCUMENT_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _validate_office_zip_container(data: bytes, *, purpose: str, required_prefix: str) -> None:
    if not data.startswith(b"PK"):
        raise HTTPException(400, f"{purpose} geçerli Office Open XML/ZIP yapısında değil")
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            infos = zf.infolist()
            if len(infos) > settings.max_xlsx_members:
                raise HTTPException(413, f"{purpose} arşivinde çok fazla parça var")
            total_uncompressed = 0
            total_compressed = 0
            names: set[str] = set()
            for info in infos:
                name = info.filename.replace("\\", "/")
                names.add(name)
                if info.flag_bits & 0x1:
                    raise HTTPException(400, f"Şifreli {purpose} dosyaları kabul edilmez")
                if name.startswith("/") or "../" in f"/{name}":
                    raise HTTPException(400, f"{purpose} arşivinde güvenli olmayan dosya yolu bulundu")
                total_uncompressed += int(info.file_size)
                total_compressed += int(info.compress_size)
            limit = settings.max_xlsx_uncompressed_mb * 1024 * 1024
            if total_uncompressed > limit:
                raise HTTPException(413, f"{purpose} açıldığında en fazla {settings.max_xlsx_uncompressed_mb} MB olabilir")
            if total_uncompressed > 5 * 1024 * 1024 and total_uncompressed / max(total_compressed, 1) > 200:
                raise HTTPException(400, f"{purpose} olağandışı sıkıştırma oranı nedeniyle reddedildi")
            if "[Content_Types].xml" not in names or not any(x.startswith(required_prefix) for x in names):
                raise HTTPException(400, f"Dosya geçerli bir {purpose} belgesi değil")
    except HTTPException:
        raise
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, f"{purpose} dosyası bozuk veya geçersiz") from exc



def validate_generic_zip(data: bytes, *, purpose: str = "ZIP") -> None:
    if not data.startswith(b"PK"):
        raise HTTPException(400, f"{purpose} geçerli ZIP yapısında değil")
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            infos=zf.infolist()
            if len(infos)>settings.max_xlsx_members:
                raise HTTPException(413,f"{purpose} arşivinde çok fazla parça var")
            total_uncompressed=0;total_compressed=0
            for info in infos:
                name=info.filename.replace("\\","/")
                if info.flag_bits & 0x1:
                    raise HTTPException(400,f"Şifreli {purpose} arşivleri kabul edilmez")
                if name.startswith("/") or "../" in f"/{name}":
                    raise HTTPException(400,f"{purpose} arşivinde güvenli olmayan dosya yolu bulundu")
                total_uncompressed+=int(info.file_size);total_compressed+=int(info.compress_size)
            limit=settings.max_xlsx_uncompressed_mb*1024*1024
            if total_uncompressed>limit:
                raise HTTPException(413,f"{purpose} açıldığında en fazla {settings.max_xlsx_uncompressed_mb} MB olabilir")
            if total_uncompressed>5*1024*1024 and total_uncompressed/max(total_compressed,1)>200:
                raise HTTPException(400,f"{purpose} olağandışı sıkıştırma oranı nedeniyle reddedildi")
    except HTTPException:
        raise
    except zipfile.BadZipFile as exc:
        raise HTTPException(400,f"{purpose} arşivi bozuk veya geçersiz") from exc


def validate_document_upload(
    filename: str,
    data: bytes,
    *,
    purpose: str = "Belge",
    allowed_extensions: set[str] | None = None,
) -> str:
    """Validate a user-supplied evidence/document and return the canonical MIME type.

    Validation is content based for PDF/images/Office Open XML containers. Text-like
    files are rejected when they contain NUL bytes so arbitrary binary payloads cannot
    be smuggled behind a .txt/.csv extension.
    """
    if not data:
        raise HTTPException(400, f"Boş {purpose.lower()} dosyası yüklenemez")
    ext = Path(filename or "").suffix.lower()
    allowed = allowed_extensions or set(_DOCUMENT_MIME_BY_EXT)
    if ext not in allowed or ext not in _DOCUMENT_MIME_BY_EXT:
        allowed_text = ", ".join(sorted(allowed))
        raise HTTPException(400, f"{purpose} için izin verilen uzantılar: {allowed_text}")
    if ext == ".pdf":
        validate_pdf_payload(data, purpose=purpose)
    elif ext in {".jpg", ".jpeg"}:
        if not data.startswith(b"\xff\xd8\xff"):
            raise HTTPException(400, f"{purpose} içeriği geçerli JPEG değil")
        validate_image_payload(data, purpose=purpose)
    elif ext == ".png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(400, f"{purpose} içeriği geçerli PNG değil")
        validate_image_payload(data, purpose=purpose)
    elif ext == ".xlsx":
        validate_xlsx_container(data)
    elif ext == ".docx":
        _validate_office_zip_container(data, purpose="DOCX", required_prefix="word/")
    else:
        if b"\x00" in data:
            raise HTTPException(400, f"{purpose} metin uzantısına rağmen ikili veri içeriyor")
    return _DOCUMENT_MIME_BY_EXT[ext]


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_stored_file(path: Path, expected_sha256: str) -> tuple[str, str]:
    """Return (status, actual_sha256): verified, mismatch or missing."""
    if not path.is_file():
        return "missing", ""
    actual = sha256_path(path)
    return ("verified" if actual == (expected_sha256 or "") else "mismatch"), actual

def security_error(status_code: int, code: str, message: str, request_id: str, *, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": [], "request_id": request_id}},
        headers=headers or {},
    )
