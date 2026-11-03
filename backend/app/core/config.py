import base64
import binascii
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    db_name: str = "test"
    db_user: str = "postgres"
    db_password: str = "strongpassword"
    db_host: str = "localhost"
    db_port: str = "5432"
    database_url_override: str | None = None

    session_ttl_seconds: int = 1800
    session_cookie_name: str = "ucm_session"
    session_cookie_secure: bool = False
    session_idle_seconds: int = 900
    data_encryption_key: str | None = None
    office_trust_enabled: bool = False

    cors_allow_origins: str = "http://localhost:3000,http://localhost:3100"
    fcm_server_key: str | None = None

    @model_validator(mode="after")
    def validate_deployment_security(self):
        if self.app_env == "development":
            return self
        if not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true outside development.")
        if not self.data_encryption_key:
            raise ValueError("DATA_ENCRYPTION_KEY is required outside development.")
        try:
            key = base64.b64decode(self.data_encryption_key, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("DATA_ENCRYPTION_KEY must be valid base64.") from exc
        if len(key) != 32:
            raise ValueError("DATA_ENCRYPTION_KEY must encode exactly 32 bytes.")
        if not self.allowed_origins or any(not origin.startswith("https://") for origin in self.allowed_origins):
            raise ValueError("CORS_ALLOW_ORIGINS must contain only HTTPS origins outside development.")
        return self

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

settings = Settings()
