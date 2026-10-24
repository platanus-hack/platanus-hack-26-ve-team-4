from types import SimpleNamespace
from typing import cast

import pytest

from agent_zero.armor.model_armor import ModelArmor
from agent_zero.events.broker import EventBroker
from agent_zero.events.event_store import EventStore
from agent_zero.fleet.fleet_builder import Fleet

# The hex part "929410922" matches the Chilean mobile pattern (9 followed by eight digits).
PHONE_LIKE_ID = "finding-929410922ffb"


def store() -> EventStore:
    return EventStore(cast(Fleet, SimpleNamespace(armor=ModelArmor())), EventBroker())


@pytest.mark.requirement("CORE-05")
def test_server_ids_survive_redaction_even_when_they_look_like_phones() -> None:
    data = store()._sanitize(
        {
            "finding_id": PHONE_LIKE_ID,
            "finding_ids": [PHONE_LIKE_ID, "finding-0123456789ab"],
            "nested": {"attempt_id": "attempt-912345678abc"},
        }
    )

    assert data == {
        "finding_id": PHONE_LIKE_ID,
        "finding_ids": [PHONE_LIKE_ID, "finding-0123456789ab"],
        "nested": {"attempt_id": "attempt-912345678abc"},
    }


@pytest.mark.requirement("CORE-05")
def test_personal_data_is_still_redacted_in_id_fields_and_free_text() -> None:
    data = store()._sanitize(
        {
            "order_id": "+56 9 1234 5678",
            "reply": f"Llámame al 912345678 por {PHONE_LIKE_ID}",
            "note": PHONE_LIKE_ID,
        }
    )

    assert "1234" not in data["order_id"]
    assert "912345678" not in data["reply"]
    assert "[PHONE]" in data["reply"]
    assert data["note"] != PHONE_LIKE_ID
