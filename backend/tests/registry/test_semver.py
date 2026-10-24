import pytest

from agent_zero.registry.semver import semver_key


def test_orders_numerically_not_lexically() -> None:
    versions = ["1.9.0", "1.10.0", "1.2.0"]
    assert sorted(versions, key=semver_key) == ["1.2.0", "1.9.0", "1.10.0"]


def test_release_outranks_prerelease() -> None:
    assert semver_key("1.0.0") > semver_key("1.0.0-rc.1")
    assert semver_key("1.0.0-rc.2") > semver_key("1.0.0-rc.1")
    assert semver_key("1.0.0-rc.1") > semver_key("1.0.0-beta")


@pytest.mark.parametrize("bad", ["1.0", "v1.0.0", "01.0.0", "1.0.0.0", ""])
def test_rejects_invalid(bad: str) -> None:
    with pytest.raises(ValueError, match="semver"):
        semver_key(bad)
