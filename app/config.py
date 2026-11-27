from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import quote_plus


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    return tuple(x.strip() for x in raw.split(",") if x.strip())


def _secret(name: str, default: str = "") -> str:
    raw = os.getenv(name)
    file_name = os.getenv(f"{name}_FILE", "").strip()
    if raw not in (None, ""):
        return raw
    if raw == "" and not file_name:
        return ""
    if not file_name:
        return default
    try:
        return Path(file_name).read_text(encoding="utf-8").rstrip("\r\n")
    except OSError as exc:
        raise RuntimeError(f"{name}_FILE okunamadı: {file_name}: {exc}") from exc


def _max_request_mb() -> int:
    raw = os.getenv("MAX_REQUEST_MB")
    if raw not in (None, ""):
        return int(raw)
    batch = int(os.getenv("MAX_BATCH_UPLOAD_MB", "60"))
    single = int(os.getenv("MAX_UPLOAD_MB", "20"))
    return max(batch, single) + 4


def _env_is_production() -> bool:
    return (os.getenv("APP_ENV", "pilot").strip().lower() or "pilot") == "production"


def _database_url() -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    host = os.getenv("DB_HOST")
    if not host:
        return "sqlite+pysqlite:///./dou_assess.db"
    port = os.getenv("DB_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "dou_assess")
    user = quote_plus(os.getenv("POSTGRES_USER", "dou_assess"))
    password = quote_plus(_secret("POSTGRES_PASSWORD", ""))
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "pilot").strip().lower() or "pilot"
    database_url: str = _database_url()
    evidence_storage_path: str = os.getenv("EVIDENCE_STORAGE_PATH", "./data/evidence")
    scan_storage_path: str = os.getenv("SCAN_STORAGE_PATH", "./data/scans")
    ops_storage_path: str = os.getenv("OPS_STORAGE_PATH", "./data/ops")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    max_batch_upload_mb: int = int(os.getenv("MAX_BATCH_UPLOAD_MB", "60"))
    max_batch_files: int = int(os.getenv("MAX_BATCH_FILES", "20"))
    max_request_mb: int = _max_request_mb()
    max_pdf_pages: int = int(os.getenv("MAX_PDF_PAGES", "120"))
    max_image_megapixels: int = int(os.getenv("MAX_IMAGE_MEGAPIXELS", "40"))
    max_xlsx_uncompressed_mb: int = int(os.getenv("MAX_XLSX_UNCOMPRESSED_MB", "80"))
    max_xlsx_members: int = int(os.getenv("MAX_XLSX_MEMBERS", "5000"))
    evidence_retention_days: int = int(os.getenv("EVIDENCE_RETENTION_DAYS", "1825"))
    student_data_retention_days: int = int(os.getenv("STUDENT_DATA_RETENTION_DAYS", "2555"))
    privacy_contact: str = os.getenv("PRIVACY_CONTACT", "").strip()
    obs_writeback_enabled: bool = _bool("OBS_WRITEBACK_ENABLED", False)
    obs_results_endpoint: str = os.getenv("OBS_RESULTS_ENDPOINT", "").strip()
    obs_results_token: str = _secret("OBS_RESULTS_TOKEN", "")
    student_link_secret: str = _secret("STUDENT_LINK_SECRET", "")
    student_appeal_days: int = int(os.getenv("STUDENT_APPEAL_DAYS", "7"))
    obs_results_timeout_seconds: int = int(os.getenv("OBS_RESULTS_TIMEOUT_SECONDS", "15"))

    # Proliz OBS read-only academic data pull (DogusAPI, HTTP Basic Auth).
    obs_proliz_enabled: bool = _bool("OBS_PROLIZ_ENABLED", False)
    obs_proliz_base_url: str = os.getenv("OBS_PROLIZ_BASE_URL", "https://portalapi.dogus.edu.tr").strip().rstrip("/")
    obs_proliz_username: str = _secret("OBS_PROLIZ_USERNAME", "")
    obs_proliz_password: str = _secret("OBS_PROLIZ_PASSWORD", "")
    obs_proliz_timeout_seconds: int = int(os.getenv("OBS_PROLIZ_TIMEOUT_SECONDS", "20"))

    # AUTH_PROVIDER=obs: teacher/student login with their own Proliz OBS
    # username/password instead of Microsoft Entra. DOU Assess verifies the
    # credentials against Proliz, then mints its own short-lived session JWT.
    obs_jwt_secret: str = _secret("OBS_JWT_SECRET", "")
    obs_jwt_expires_minutes: int = int(os.getenv("OBS_JWT_EXPIRES_MINUTES", "480"))

    rate_limit_enabled: bool = _bool("RATE_LIMIT_ENABLED", _env_is_production())
    api_rate_limit_per_minute: int = int(os.getenv("API_RATE_LIMIT_PER_MINUTE", "600"))
    upload_rate_limit_per_minute: int = int(os.getenv("UPLOAD_RATE_LIMIT_PER_MINUTE", "30"))
    rate_limit_bucket_ttl_seconds: int = int(os.getenv("RATE_LIMIT_BUCKET_TTL_SECONDS", "180"))

    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    db_pool_timeout_seconds: int = int(os.getenv("DB_POOL_TIMEOUT_SECONDS", "30"))
    db_pool_recycle_seconds: int = int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800"))
    db_statement_timeout_ms: int = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000"))
    auth_last_seen_write_seconds: int = int(os.getenv("AUTH_LAST_SEEN_WRITE_SECONDS", "300"))
    jwks_cache_lifespan_seconds: int = int(os.getenv("JWKS_CACHE_LIFESPAN_SECONDS", "600"))
    jwks_http_timeout_seconds: int = int(os.getenv("JWKS_HTTP_TIMEOUT_SECONDS", "5"))

    auth_required: bool = _bool("AUTH_REQUIRED", False)
    auth_provider: str = os.getenv("AUTH_PROVIDER", "pilot").strip().lower() or "pilot"
    pilot_admin_email: str = os.getenv("PILOT_ADMIN_EMAIL", "pilot-admin@local").strip().lower()
    # Pilot access is convenient for local/UAT work but must be explicitly disabled
    # in production. Defaults preserve current pilot/test behaviour.
    pilot_auth_enabled: bool = _bool("PILOT_AUTH_ENABLED", not _env_is_production())
    pilot_demo_enabled: bool = _bool("PILOT_DEMO_ENABLED", not _env_is_production())

    entra_tenant_id: str = os.getenv("ENTRA_TENANT_ID", "").strip()
    entra_client_id: str = os.getenv("ENTRA_CLIENT_ID", "").strip()
    entra_audience: str = os.getenv("ENTRA_AUDIENCE", os.getenv("ENTRA_CLIENT_ID", "")).strip()
    entra_auto_link_by_email: bool = _bool("ENTRA_AUTO_LINK_BY_EMAIL", False)
    entra_allowed_client_ids: tuple[str, ...] = _csv("ENTRA_ALLOWED_CLIENT_IDS")
    entra_required_scopes: tuple[str, ...] = _csv("ENTRA_REQUIRED_SCOPES")
    entra_login_scopes: tuple[str, ...] = _csv("ENTRA_LOGIN_SCOPES")
    entra_redirect_uri: str = os.getenv("ENTRA_REDIRECT_URI", "").strip()
    entra_require_delegated_user: bool = _bool("ENTRA_REQUIRE_DELEGATED_USER", True)

    public_hostname: str = os.getenv("PUBLIC_HOSTNAME", "").strip().lower()
    allowed_hosts: tuple[str, ...] = _csv("ALLOWED_HOSTS")
    require_https: bool = _bool("REQUIRE_HTTPS", False)
    security_headers: bool = _bool("SECURITY_HEADERS", True)
    strict_production_security: bool = _bool("STRICT_PRODUCTION_SECURITY", True)
    trust_proxy_headers: bool = _bool("TRUST_PROXY_HEADERS", True)
    trusted_proxy_cidrs: tuple[str, ...] = _csv("TRUSTED_PROXY_CIDRS")

    # 6.68 operations & automation
    job_poll_seconds: float = float(os.getenv("JOB_POLL_SECONDS", "2"))
    job_stale_minutes: int = int(os.getenv("JOB_STALE_MINUTES", "30"))
    scheduler_interval_seconds: int = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "60"))
    notification_lookahead_days: int = int(os.getenv("NOTIFICATION_LOOKAHEAD_DAYS", "7"))
    backup_automation_enabled: bool = _bool("BACKUP_AUTOMATION_ENABLED", False)
    backup_interval_hours: int = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
    backup_retention_days: int = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
    evidence_integrity_interval_hours: int = int(os.getenv("EVIDENCE_INTEGRITY_INTERVAL_HOURS", "24"))


settings = Settings()
