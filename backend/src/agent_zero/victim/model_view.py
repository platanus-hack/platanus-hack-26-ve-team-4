from typing import Any

INTERNAL_CUSTOMER_FIELDS = ("customer_id",)


def without_internal_ids(output: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in output.items() if key not in INTERNAL_CUSTOMER_FIELDS}
