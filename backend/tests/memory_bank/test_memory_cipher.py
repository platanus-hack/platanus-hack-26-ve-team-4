from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from agent_zero.config import Settings
from agent_zero.memory_bank.errors import MemoryConfigError
from agent_zero.memory_bank.memory_cipher import MemoryCipher


@pytest.mark.requirement("MEM-03")
def test_roundtrip_and_ciphertext_hides_plaintext(cipher: MemoryCipher) -> None:
    token = cipher.encrypt("dato secreto del cliente")
    assert "secreto" not in token
    assert cipher.decrypt(token) == "dato secreto del cliente"


@pytest.mark.requirement("MEM-03")
def test_local_key_is_derived_deterministically(memory_settings: Settings) -> None:
    first = MemoryCipher.from_settings(memory_settings)
    second = MemoryCipher.from_settings(memory_settings)
    assert second.decrypt(first.encrypt("hola")) == "hola"


@pytest.mark.requirement("MEM-03")
def test_different_operator_secret_cannot_decrypt(tmp_path: Path) -> None:
    one = MemoryCipher.from_settings(
        Settings(data_dir=tmp_path, environment="test", operator_secret=SecretStr("uno"))
    )
    two = MemoryCipher.from_settings(
        Settings(data_dir=tmp_path, environment="test", operator_secret=SecretStr("dos"))
    )
    with pytest.raises(MemoryConfigError):
        two.decrypt(one.encrypt("hola"))


@pytest.mark.requirement("MEM-03")
def test_explicit_key_is_used(tmp_path: Path) -> None:
    key = Fernet.generate_key().decode()
    settings = Settings(
        data_dir=tmp_path, environment="production", memory_encryption_key=SecretStr(key)
    )
    cipher = MemoryCipher.from_settings(settings)
    assert Fernet(key.encode()).decrypt(cipher.encrypt("x").encode()) == b"x"


@pytest.mark.requirement("MEM-03")
def test_missing_key_outside_local_fails(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, environment="production")
    with pytest.raises(MemoryConfigError, match="MEMORY_ENCRYPTION_KEY"):
        MemoryCipher.from_settings(settings)


@pytest.mark.requirement("MEM-03")
def test_invalid_key_fails(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, memory_encryption_key=SecretStr("corta"))
    with pytest.raises(MemoryConfigError, match="Fernet"):
        MemoryCipher.from_settings(settings)
