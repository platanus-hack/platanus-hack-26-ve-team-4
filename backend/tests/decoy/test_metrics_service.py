import pytest
from fastapi.testclient import TestClient

from agent_zero.decoy.metrics_service import rate_of
from agent_zero.decoy.models import MIN_RATE_N
from tests.arena.support import OPERATOR, join, send, wait_attempt


@pytest.mark.parametrize(
    ("k", "n", "value"),
    [(0, 0, None), (1, 1, None), (3, MIN_RATE_N - 1, None), (3, MIN_RATE_N, 0.6), (14, 14, 1.0)],
)
def test_a_rate_is_only_stated_from_the_minimum_n(k: int, n: int, value: float | None) -> None:
    rate = rate_of(k, n)

    assert (rate.k, rate.n, rate.value) == (k, n, value)


def test_summary_without_diverted_sessions_is_empty_and_explicit(decoy_client: TestClient) -> None:
    summary = decoy_client.get("/api/operator/decoy", headers=OPERATOR).json()

    assert summary["diverted_n"] == 0
    assert summary["small_n"] is True
    assert summary["cases"] == []
    assert summary["median_retained_seconds"] is None
    assert summary["deceived"] == {"k": 0, "n": 0, "value": None}


def test_denominator_is_diverted_sessions_only(decoy_client: TestClient) -> None:
    clean = join(decoy_client, "clean")
    attempt = send(decoy_client, clean, f"Consulta el pedido {clean['order_ids'][0]}.")
    wait_attempt(decoy_client, attempt["id"])
    summary = decoy_client.get("/api/operator/decoy", headers=OPERATOR).json()

    assert summary["diverted_n"] == 0
