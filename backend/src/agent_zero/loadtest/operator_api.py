from typing import Any

import httpx


async def operator_rows(client: httpx.AsyncClient, secret: str, path: str) -> list[Any]:
    response = await client.get(path, headers={"X-Operator-Secret": secret})
    response.raise_for_status()
    rows: list[Any] = response.json()
    return rows
