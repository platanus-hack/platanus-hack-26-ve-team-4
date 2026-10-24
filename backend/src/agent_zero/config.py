from pathlib import Path

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
    llm_breaker_failures: int = Field(default=3, ge=1)
    llm_breaker_recovery_seconds: float = Field(default=30.0, gt=0)

    @property
    def app_database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.data_dir / 'app.db'}"

    @property
    def llm_ledger_path(self) -> Path:
        return self.data_dir / "llm" / "calls.jsonl"

    @property
    def llm_default_cassette_path(self) -> Path:
        return self.llm_cassette_path or self.data_dir / "llm" / "cassette.jsonl"
