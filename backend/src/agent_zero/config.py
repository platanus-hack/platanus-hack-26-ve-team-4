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
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=100)
    # Vectorizador de la base de conocimiento `<name>_knowledge`, que solo existe con Postgres.
    # `fake` es determinista y no descarga nada; lo usan los tests y la CI.
    knowledge_embedder: Literal["local", "fake"] = "local"
    operator_secret: SecretStr = SecretStr("change-me")
    guard_api_key: SecretStr = SecretStr("change-me-guard")
    contracts_dir: Path = Path("./contracts")
    cors_origins: list[str] = []

    llm_mode: LlmMode = LlmMode.OFFLINE
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = "claude-haiku-5-5"
    llm_role_models: dict[str, str] = {}
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_retry_attempts: int = Field(default=4, ge=1)
    llm_cassette_path: Path | None = None
    llm_daily_call_limit: int = Field(default=2000, ge=1)
    llm_session_call_limit: int = Field(default=400, ge=1)
    llm_campaign_call_limit: int = Field(default=300, ge=1)
    llm_campaign_token_limit: int = Field(default=1_500_000, ge=1)
    llm_daily_usd_limit: float = Field(default=15.0, gt=0)
    llm_breaker_failures: int = Field(default=3, ge=1)
    llm_breaker_recovery_seconds: float = Field(default=30.0, gt=0)

    identity_signing_key: SecretStr = SecretStr("change-me-identity")
    identity_token_ttl_seconds: int = Field(default=900, ge=30)

    memory_encryption_key: SecretStr = SecretStr("")
    memory_default_ttl_days: int = Field(default=90, ge=1)

    data_region: str = "ve"
    allowed_data_regions: list[str] = ["ve"]

    runtime_worker_concurrency: int = Field(default=2, ge=1)
    runtime_poll_seconds: float = Field(default=0.5, gt=0)
    runtime_priority_handlers: list[str] = ["validate_patch", "finding_analysis"]
    runtime_max_attempts: int = Field(default=3, ge=1)
    defense_activation_hold_seconds: float = Field(default=30.0, ge=0)
    routing_risk_threshold: int = Field(default=6, ge=1)
    routing_risk_window_seconds: float = Field(default=600.0, gt=0)

    gateway_rate_limit_per_minute: int = Field(default=480, ge=1)

    arena_session_ttl_seconds: int = Field(default=3600, ge=60)
    arena_session_limit: int = Field(default=100, ge=1, le=500)
    arena_queue_limit: int = Field(default=40, ge=1)
    arena_session_queue_limit: int = Field(default=1, ge=1)
    arena_attempts_per_minute: int = Field(default=240, ge=1)
    prober_round_query_budget: int = Field(default=8, ge=1)
    prober_round_close_wait_seconds: float = Field(default=90.0, gt=0)
    arena_auto_patch: bool = True
    arena_flow_synthesis: bool = False
    arena_validation_concurrency: int = Field(default=8, ge=1, le=8)

    otel_exporter: Literal["none", "memory", "console", "otlp"] = "none"
    otel_endpoint: str | None = None
    otel_service_name: str = "agent-zero"

    @field_validator("database_url", mode="before")
    @classmethod
    def _blank_database_url_means_sqlite(cls, value: object) -> object:
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if value == "":
            return None
        if isinstance(value, str):
            for scheme in ("postgres://", "postgresql://"):
                if value.startswith(scheme):
                    return "postgresql+asyncpg://" + value.removeprefix(scheme)
        return value

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
    def knowledge_database_url(self) -> str | None:
        """Base de conocimiento híbrida; sin Postgres no existe y se usan palabras clave."""
        if self.database_url is None:
            return None
        return self.environment_database_url("knowledge")

    @property
    def knowledge_model_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def llm_ledger_path(self) -> Path:
        return self.data_dir / "llm" / "calls.jsonl"

    @property
    def llm_default_cassette_path(self) -> Path:
        return self.llm_cassette_path or self.data_dir / "llm" / "cassette.jsonl"

    @property
    def audit_log_path(self) -> Path:
        return self.data_dir / "audit" / "audit.jsonl"
