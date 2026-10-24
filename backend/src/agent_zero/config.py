from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from agent_zero.llm.models import LlmMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENT_ZERO_", env_file=".env", extra="ignore")

    environment: str = "local"
    data_dir: Path = Path("./data")
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

    session_signing_key: SecretStr = SecretStr("change-me-session")
    session_token_ttl_seconds: int = Field(default=4 * 3600, ge=60)

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

    otel_exporter: Literal["none", "memory", "console", "otlp"] = "none"
    otel_endpoint: str | None = None
    otel_service_name: str = "agent-zero"

    @property
    def app_database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.data_dir / 'app.db'}"

    @property
    def llm_ledger_path(self) -> Path:
        return self.data_dir / "llm" / "calls.jsonl"

    @property
    def llm_default_cassette_path(self) -> Path:
        return self.llm_cassette_path or self.data_dir / "llm" / "cassette.jsonl"

    @property
    def audit_log_path(self) -> Path:
        return self.data_dir / "audit" / "audit.jsonl"
