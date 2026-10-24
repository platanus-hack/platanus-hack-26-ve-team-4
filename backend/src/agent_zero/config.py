from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENT_ZERO_", env_file=".env", extra="ignore")

    environment: str = "local"
    data_dir: Path = Path("./data")
    operator_secret: SecretStr = SecretStr("change-me")
    llm_provider: str = "anthropic"
    llm_api_key: SecretStr = SecretStr("")
    cors_origins: list[str] = []

    @property
    def app_database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.data_dir / 'app.db'}"
