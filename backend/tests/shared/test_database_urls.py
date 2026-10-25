from pathlib import Path

from pydantic import SecretStr

from agent_zero.config import Settings
from agent_zero.shared.database import is_postgres

POSTGRES = "postgresql+asyncpg://agent_zero:s3cret@postgres:5432/agent_zero"


def test_without_a_database_url_every_store_is_a_sqlite_file(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, database_url="")

    assert settings.database_url is None
    assert settings.app_database_url == f"sqlite+aiosqlite:///{tmp_path / 'app.db'}"
    assert settings.environment_database_url("honeypot").endswith("/honeypot.db")


def test_postgres_keeps_each_store_in_its_own_database(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, database_url=SecretStr(POSTGRES))

    assert settings.app_database_url == POSTGRES
    assert settings.environment_database_url("protected") == f"{POSTGRES}_protected"
    assert settings.environment_database_url("honeypot") == f"{POSTGRES}_honeypot"
    assert is_postgres(settings.environment_database_url("honeypot"))
    assert "s3cret" not in repr(settings)


def test_a_hosted_postgres_url_uses_the_async_driver(tmp_path: Path) -> None:
    for scheme in ("postgres", "postgresql"):
        hosted = f"{scheme}://agent_zero:s3cret@dpg-internal/agent_zero"
        settings = Settings(data_dir=tmp_path, database_url=SecretStr(hosted))

        assert settings.app_database_url == (
            "postgresql+asyncpg://agent_zero:s3cret@dpg-internal/agent_zero"
        )
