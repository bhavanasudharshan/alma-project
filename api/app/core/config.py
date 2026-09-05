"""Application configuration (S3: single config surface, pydantic-settings only).

Every setting the app reads lives here. No module outside this file may touch
``os.environ`` -- see CLAUDE.md. New settings must also be added to the repo-root
``.env.example`` with a comment.

Adapter selection is driven entirely by these values (M4/E2): an unset provider key
means "that adapter is not selected", so the zero-config default is console email and
local-disk storage on SQLite, with no Docker ($1).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, EmailStr, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py -> core -> app -> api -> <repo root>
REPO_ROOT = Path(__file__).resolve().parents[3]

# Placeholder credentials that are safe for a local reviewer run but must never
# reach a deployed environment; startup logs a warning if they survive (S4).
DEV_JWT_SECRET = "dev-only-change-me"  # noqa: S105
DEV_ATTORNEY_PASSWORD = "changeme"  # noqa: S105


class Attorney(BaseModel):
    """One member of the attorney roster.

    Held in configuration rather than a table on purpose: this build has one role and
    no user management, so a table would be schema without a decision behind it. The
    upgrade path is in DESIGN.md -- an ``attorneys`` table is the prerequisite for RBAC
    and per-attorney routing, and this shape maps onto it one-for-one.
    """

    email: EmailStr
    # SecretStr so the value cannot leak through a settings dump, a log line or a
    # traceback: repr() and model_dump() render it as "**********" (S4).
    password: SecretStr
    name: str


class Settings(BaseSettings):
    """Settings loaded from the repo-root ``.env`` file and the process environment."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- application ---------------------------------------------------------
    app_name: str = "Alma Lead Intake API"
    environment: str = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- web / CORS (S5: browser cross-origin locked to an allow-list) --------
    cors_origins: list[str] = ["http://localhost:3000"]
    # Used to build the "open this lead" link in the attorney notification email.
    internal_ui_url: str = "http://localhost:3000/leads"
    # EXT1: where the prospect checks their own status with the tracking code.
    status_portal_url: str = "http://localhost:3000/status"

    # --- persistence ($1: zero-infra local run defaults to SQLite) -----------
    database_url: str = "sqlite:///./data/alma.db"

    # --- auth (S1/S4) --------------------------------------------------------
    jwt_secret_key: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    # 8 hours; no refresh tokens in this build (documented in DESIGN.md).
    access_token_expire_minutes: int = 480
    # The single seeded attorney. The password is bcrypt-hashed at startup and the
    # plaintext is never persisted anywhere.
    attorney_email: str = "attorney@example.com"
    attorney_password: str = DEV_ATTORNEY_PASSWORD
    # Optional multi-attorney roster. When unset, the single account above is used, so
    # the zero-config reviewer run still has exactly one login ($1).
    attorneys: list[Attorney] = []

    # --- uploads (S2: untrusted uploads are bounded) -------------------------
    upload_dir: str = "uploads"
    max_resume_mb: int = 5
    # SEC2(b): legacy .doc is OLE and macro-prone, so P1 accepts pdf/docx only.
    allowed_resume_content_types: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    allowed_resume_extensions: list[str] = [".pdf", ".docx"]

    # --- rate limiting (SEC1) ------------------------------------------------
    rate_limit_enabled: bool = True
    # slowapi syntax: "<count>/<period>".
    rate_limit_leads: str = "5/10minutes"
    rate_limit_login: str = "10/5minutes"
    # EXT1: the status portal is public and cheap, so a looser but real budget.
    rate_limit_status: str = "20/minute"
    # In-memory today; point at redis://... to share limits across replicas.
    rate_limit_storage_url: str = "memory://"

    # --- observability (M5) --------------------------------------------------
    log_json: bool = False
    request_id_header: str = "X-Request-ID"

    # --- email (P0 console; Resend selected in P1 when the key is set) -------
    # Unset RESEND_API_KEY => ConsoleEmailService.
    resend_api_key: str | None = None
    email_from: str = "noreply@example.com"
    attorney_notify_email: str = "attorney@example.com"

    # --- object storage (P0 local disk; S3/MinIO selected in P1) -------------
    # Unset S3_ENDPOINT_URL => LocalDiskStorage.
    s3_endpoint_url: str | None = None
    s3_bucket: str = "alma-resumes"
    s3_region: str = "us-east-1"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None

    @property
    def max_resume_bytes(self) -> int:
        """Upload size cap in bytes."""
        return self.max_resume_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        """Absolute upload root, anchored to the repo so cwd does not matter."""
        configured = Path(self.upload_dir)
        return configured if configured.is_absolute() else REPO_ROOT / configured

    @property
    def roster(self) -> list[Attorney]:
        """Every attorney who can sign in, however they were configured (M4)."""
        if self.attorneys:
            return self.attorneys
        return [
            Attorney(
                email=self.attorney_email,
                password=self.attorney_password,
                name="Attorney",
            )
        ]

    @property
    def uses_s3(self) -> bool:
        """Whether object storage is configured (M4: selection is config, not code)."""
        return bool(self.s3_endpoint_url or self.s3_access_key_id)

    @property
    def uses_resend(self) -> bool:
        """Whether a real email provider is configured."""
        return bool(self.resend_api_key)

    def insecure_defaults(self) -> list[str]:
        """Names of placeholder credentials still in use outside local development."""
        if self.environment == "local":
            return []
        insecure = []
        if self.jwt_secret_key == DEV_JWT_SECRET:
            insecure.append("JWT_SECRET_KEY")
        if self.attorney_password == DEV_ATTORNEY_PASSWORD:
            insecure.append("ATTORNEY_PASSWORD")
        return insecure


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
