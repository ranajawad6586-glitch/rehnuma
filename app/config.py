"""Application settings. Loaded from environment / .env (server-side only)."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.dburl import normalize_database_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core infra
    database_url: str = "postgresql+asyncpg://rehnuma:rehnuma@localhost:5432/rehnuma"
    redis_url: str = "redis://localhost:6379/0"

    @field_validator("database_url")
    @classmethod
    def _async_pg_scheme(cls, v: str) -> str:
        # Managed hosts give postgres:// and libpq sslmode/channel_binding params; asyncpg
        # accepts neither. See app/dburl.py.
        return normalize_database_url(v)

    # Seed the Bahria grid on startup if the plots table is empty.
    auto_seed: bool = False

    app_name: str = "RehnumaRent"
    env: str = "dev"  # "dev" | "prod" — gates dev-only conveniences (OTP echo)

    # --- Secrets (MUST be overridden in prod) ---
    # JWT signing key for session tokens.
    secret_key: str = "dev-insecure-change-me"
    # Pepper for HMAC hashing of phone/CNIC. Rotating it invalidates all stored hashes.
    hash_pepper: str = "dev-insecure-pepper-change-me"
    # Secret used to derive the Fernet key that encrypts the raw phone at rest.
    # Rotating it makes existing encrypted phones undecryptable.
    phone_encryption_secret: str = "dev-insecure-phone-key-change-me"

    # --- Session tokens ---
    token_ttl_minutes: int = 60 * 24 * 7  # 7 days

    # --- OTP ---
    otp_length: int = 6
    otp_ttl_seconds: int = 300            # code valid for 5 minutes
    otp_max_attempts: int = 5             # verify tries before the code is burned
    otp_resend_cooldown_seconds: int = 60 # min gap between sends to one number

    # --- WhatsApp Business API (OTP + notifications). Absent => console sender in dev. ---
    whatsapp_token: str | None = None
    whatsapp_phone_id: str | None = None

    # --- Rehnuma LLM router (keys server-side only, rule 6). Fixed fallback chain:
    #     Groq -> Gemini -> OpenRouter -> Anthropic Haiku (rule 5). A provider with no key
    #     is skipped. If all fail, the router returns a safe canned advisory (never raises). ---
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    openrouter_api_key: str | None = None
    anthropic_api_key: str | None = None

    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-2.0-flash"
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct"
    anthropic_model: str = "claude-haiku-4-5-20251001"

    llm_timeout_seconds: float = 8.0  # per-provider call cap before falling through

    # --- Apify listing import (server-side token only, rule 6) ---
    # APIFY_ACTOR_ID is the scraper Actor to run (e.g. a Zameen/property scraper from the Apify
    # store, "username~actor-name"). APIFY_RUN_INPUT_JSON is that actor's input as a JSON string
    # (its schema is actor-specific — start URLs, areas, max items, etc.).
    apify_token: str | None = None
    apify_actor_id: str | None = None
    apify_run_input_json: str | None = None

    # --- Object storage (PDFs + photos) ---
    # If MINIO_ACCESS_KEY is empty, the app stores files on the local filesystem (storage_dir)
    # instead of MinIO/S3 — so it works with no object-storage service configured.
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_secure: bool = False
    minio_bucket: str = "agreements"
    storage_dir: str = "/app/data"  # local-filesystem backend location

    # --- Hardening (M10) ---
    # Fixed-window rate limits: (max requests, window seconds).
    otp_request_rate_limit: int = 15      # per IP
    otp_request_rate_window: int = 3600
    otp_verify_rate_limit: int = 30       # per IP (brute-force guard across numbers)
    otp_verify_rate_window: int = 3600
    ai_rate_limit: int = 40               # per user
    ai_rate_window: int = 3600
    # Verification batch: LIVE listings older than this are expired.
    listing_expiry_days: int = 30

    @property
    def is_prod(self) -> bool:
        return self.env.lower() == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
