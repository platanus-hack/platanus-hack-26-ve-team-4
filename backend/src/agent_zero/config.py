from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from agent_zero.llm.models import LlmMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENT_ZERO_", env_file=".env", extra="ignore")

    environment: str = "local"
    data_dir: Path = Path("./data")
    # Without it every database is a SQLite file in data_dir. With a postgresql+asyncpg URL the
    # app uses that database and adds `<name>_protected` and `<name>_honeypot` for the stores.
    database_url: SecretStr | None = None
    operator_secret: SecretStr = SecretStr("change-me")
    cors_origins: list[str] = []

    llm_mode: LlmMode = LlmMode.OFFLINE
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = "claude-haiku-5-5"
    llm_role_models: dict[str, str] = {}
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_retry_attempts: int = Field(default=4, ge=1)
    llm_cassette_path: Path | None = None
    llm_daily_call_limit: int = Field(default=2000, ge=1)
    llm_session_call_limit: int = Field(default=40, ge=1)
    llm_campaign_call_limit: int = Field(default=300, ge=1)
    llm_campaign_token_limit: int = Field(default=1_500_000, ge=1)
    llm_daily_usd_limit: float = Field(default=2.0, gt=0)
    llm_breaker_failures: int = Field(default=3, ge=1)
    llm_breaker_recovery_seconds: float = Field(default=30.0, gt=0)

    identity_signing_key: SecretStr = SecretStr("change-me-identity")
    identity_token_ttl_seconds: int = Field(default=900, ge=30)

    memory_encryption_key: SecretStr = SecretStr("")
    memory_default_ttl_days: int = Field(default=90, ge=1)

    data_region: str = "cl"
    allowed_data_regions: list[str] = ["cl"]

    runtime_worker_concurrency: int = Field(default=2, ge=1)
    runtime_poll_seconds: float = Field(default=0.5, gt=0)
    runtime_max_attempts: int = Field(default=3, ge=1)

    gateway_rate_limit_per_minute: int = Field(default=60, ge=1)

    arena_session_ttl_seconds: int = Field(default=3600, ge=60)
    arena_session_limit: int = Field(default=100, ge=1, le=500)
    arena_queue_limit: int = Field(default=40, ge=1)
    arena_session_queue_limit: int = Field(default=1, ge=1)
    arena_attempts_per_minute: int = Field(default=12, ge=1)
    arena_auto_patch: bool = True
    arena_validation_concurrency: int = Field(default=8, ge=1, le=8)

    otel_exporter: Literal["none", "memory", "console", "otlp"] = "none"
    otel_endpoint: str | None = None
    otel_service_name: str = "agent-zero"

    @field_validator("database_url", mode="before")
    @classmethod
    def _blank_database_url_means_sqlite(cls, value: object) -> object:
        return None if value == "" else value

    @property
    def app_database_url(self) -> str:
        if self.database_url is None:
            return f"sqlite+aiosqlite:///{self.data_dir / 'app.db'}"
        return self.database_url.get_secret_value()

    def environment_database_url(self, name: str) -> str:
        if self.database_url is None:
            return f"sqlite+aiosqlite:///{self.data_dir / (name + '.db')}"
        url = make_url(self.database_url.get_secret_value())
        return url.set(database=f"{url.database}_{name}").render_as_string(hide_password=False)

    @property
    def llm_ledger_path(self) -> Path:
        return self.data_dir / "llm" / "calls.jsonl"

    @property
    def llm_default_cassette_path(self) -> Path:
        return self.llm_cassette_path or self.data_dir / "llm" / "cassette.jsonl"

    @property
    def audit_log_path(self) -> Path:
        return self.data_dir / "audit" / "audit.jsonl"
