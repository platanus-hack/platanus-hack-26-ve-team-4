import time
from collections.abc import Callable
from typing import Any, Protocol

TERMINAL_STATUSES = frozenset({"succeeded", "failed", "cancelled"})


class HttpResponse(Protocol):
    status_code: int

    def json(self) -> Any: ...


class HttpClient(Protocol):
    def get(self, url: str, *, params: Any = ..., headers: Any = ...) -> Any: ...

    def post(self, url: str, *, json: Any = ..., headers: Any = ...) -> Any: ...


class RunTimeoutError(TimeoutError):
    pass


class FleetClient:
    def __init__(
        self,
        http: HttpClient,
        operator_secret: str,
        poll_seconds: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._http = http
        self._headers = {"x-operator-secret": operator_secret}
        self._poll_seconds = poll_seconds
        self._sleep = sleep

    def get(self, path: str, operator: bool = True, **params: Any) -> HttpResponse:
        headers = self._headers if operator else {}
        response: HttpResponse = self._http.get(path, headers=headers, params=params)
        return response

    def post(self, path: str, body: Any = None, operator: bool = True) -> HttpResponse:
        headers = self._headers if operator else {}
        response: HttpResponse = self._http.post(path, headers=headers, json=body)
        return response

    def enqueue(self, agent_id: str, handler: str, payload: dict[str, Any]) -> str:
        body = {
            "agent_id": agent_id,
            "agent_version": "1.0.0",
            "handler": handler,
            "input": payload,
        }
        response = self.post("/api/runtime/runs", body)
        if response.status_code != 202:
            raise RuntimeError(f"no se pudo encolar: {response.status_code} {response.json()}")
        run_id: str = response.json()["run_id"]
        return run_id

    def wait_for(self, run_id: str, timeout_seconds: float) -> tuple[dict[str, Any], set[str]]:
        seen: set[str] = set()
        waited = 0.0
        while waited <= timeout_seconds:
            run: dict[str, Any] = self.get(f"/api/runtime/runs/{run_id}").json()
            seen.add(run["status"])
            if run["status"] in TERMINAL_STATUSES:
                return run, seen
            self._sleep(self._poll_seconds)
            waited += self._poll_seconds
        raise RunTimeoutError(f"la ejecución {run_id} no terminó en {timeout_seconds} s")
