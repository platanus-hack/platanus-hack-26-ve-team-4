from agent_zero.victim.model_view import without_internal_ids


def test_the_customer_id_is_removed_and_the_rest_is_kept() -> None:
    output = {"order_id": "A-1001", "customer_id": "cust-ana", "total": 25}

    assert without_internal_ids(output) == {"order_id": "A-1001", "total": 25}
    assert output["customer_id"] == "cust-ana"
