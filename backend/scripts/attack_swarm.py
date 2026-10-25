"""Enjambre de agentes simulados para el tablero de ataque en vivo.

Crea K sesiones llamadas Agente-1..K con la API publica y envia intentos en paralelo desde las
plantillas del Prober (`prober/playbooks.py` y `prober/mutators.py`). No escribe textos propios:
solo adapta los pedidos de cada plantilla a los de la sesion. El tablero los rotula siempre como
"Agente simulado". Solo apunta a la arena propia.

El prefijo de alias `Agente-` esta reservado: el servidor solo crea esas sesiones con el secreto de
operador. El script lo lee de la variable de entorno AGENT_ZERO_OPERATOR_SECRET (nunca de la linea
de comandos), no lo imprime y lo envia solo al crear la sesion (`POST /api/sessions`); los intentos
viajan con el token de participante, como los del publico.

    AGENT_ZERO_OPERATOR_SECRET=... uv run python scripts/attack_swarm.py --agents 5
"""

import argparse
import json
import os
import random
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from agent_zero.prober.models import Surface
from agent_zero.prober.mutators import applicable, mutate
from agent_zero.prober.playbooks import campaign_case
from agent_zero.prober.schemas import AttackCase
from agent_zero.victim.fixtures import ORDERS

MIN_AGENTS, MAX_AGENTS = 4, 6
CASES = 30
# Espaciado propio del enjambre, muy por debajo del cupo del servidor
# (240 intentos por minuto y sesión, `arena_attempts_per_minute`).
SAFE_MIN_WAIT = 5.2
MUTATORS = (None, "paraphrase_es", "paraphrase_en", "split_turns")
TERMINAL = {"evaluated", "inconclusive"}
SECRET_ENV = "AGENT_ZERO_OPERATOR_SECRET"
SWAP = {"owned": "\u0001", "foreign": "\u0002", "stranger": "\u0004"}


@dataclass(frozen=True)
class Plan:
    messages: list[str]
    label: str


def usable_cases() -> list[int]:
    """Indices de las plantillas que viajan solo en mensajes (sin fixtures del servidor)."""
    usable = []
    for index in range(CASES):
        _, case, _ = campaign_case(index, "swarm")
        if case.fixture is None and case.surface in {Surface.MESSAGE, Surface.MEMORY}:
            usable.append(index)
    return usable


def foreign_order(own: str) -> str:
    """Un pedido de otro cliente, como en el resto de los ejercicios de la arena."""
    return "B-2001" if own.startswith("A") else "A-1001"


def adapt(case: AttackCase, customer: str, own: str, foreign: str) -> list[str]:
    """Sustituye los pedidos y clientes de la plantilla por los de la sesion simulada."""
    template_owned = next(o for o in ORDERS.values() if o.customer_id == customer)
    template_foreign = next(o for o in ORDERS.values() if o.customer_id != customer)
    session_foreign = ORDERS[foreign]
    pairs = (
        (template_owned.order_id, SWAP["owned"], own),
        (template_foreign.order_id, SWAP["foreign"], foreign),
        (
            template_foreign.customer_id.removeprefix("cust-"),
            SWAP["stranger"],
            session_foreign.customer_id.removeprefix("cust-"),
        ),
    )
    messages = []
    for original in case.messages:
        text = original
        for source, token, _ in pairs:
            text = text.replace(source, token)
        for _, token, target in pairs:
            text = text.replace(token, target)
        messages.append(text)
    return messages


def plan_for(
    rng: random.Random, indices: list[int], own: str, foreign: str, count: int
) -> list[Plan]:
    chosen = rng.sample(indices, k=min(count, len(indices)))
    plans = []
    for index in chosen:
        customer, case, _ = campaign_case(index, "swarm")
        name = rng.choice(MUTATORS)
        if name is not None and name in applicable(case):
            case = mutate(name, case, customer)
        else:
            name = None
        plans.append(
            Plan(adapt(case, customer, own, foreign), f"{case.family.value}/{name or 'base'}")
        )
    return plans


class Api:
    def __init__(self, base_url: str, operator_secret: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self._operator_secret = operator_secret

    def join(self, alias: str) -> tuple[int, Any, str | None]:
        """Crea la sesion del agente: es la unica peticion que lleva el secreto de operador."""
        return self.call(
            "POST",
            "/api/sessions",
            {"alias": alias, "accepted_rules": True},
            operator=True,
        )

    def call(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        token: str | None = None,
        *,
        operator: bool = False,
    ) -> tuple[int, Any, str | None]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if operator:
            headers["X-Operator-Secret"] = self._operator_secret
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            self.base_url + path, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.load(response), None
        except urllib.error.HTTPError as error:
            payload = error.read().decode(errors="replace")
            try:
                return error.code, json.loads(payload), error.headers.get("Retry-After")
            except ValueError:
                return error.code, payload, error.headers.get("Retry-After")


def run_agent(api: Api, number: int, args: argparse.Namespace, rng: random.Random) -> None:
    name = f"Agente-{number}"
    status, session, _ = api.join(name)
    if status != 201:
        print(f"[{name}] no se pudo crear la sesion: {status} {session}", flush=True)
        return
    own = session["order_ids"][0]
    foreign = foreign_order(own)
    indices = usable_cases()
    print(f"[{name}] sesion {session['id']} lista (simulado)", flush=True)
    for turn, plan in enumerate(plan_for(rng, indices, own, foreign, args.attempts), start=1):
        sent = send(api, session["token"], plan, f"swarm-{number}-{turn}-{rng.random():.6f}")
        if sent is None:
            print(f"[{name}] intento {turn} descartado", flush=True)
        else:
            print(f"[{name}] intento {turn} {plan.label}: {sent}", flush=True)
        time.sleep(
            rng.uniform(max(args.min_wait, SAFE_MIN_WAIT), max(args.max_wait, SAFE_MIN_WAIT))
        )


def send(api: Api, token: str, plan: Plan, key: str) -> str | None:
    for _ in range(4):
        status, body, retry = api.call(
            "POST",
            "/api/attempts",
            {"messages": plan.messages, "idempotency_key": key},
            token,
        )
        if status == 202:
            return wait(api, token, body["id"])
        if status == 429:
            time.sleep(float(retry) if retry and retry.isdigit() else SAFE_MIN_WAIT)
            continue
        print(f"  respuesta inesperada {status}: {body}", flush=True)
        return None
    return None


def wait(api: Api, token: str, attempt_id: str, timeout: float = 180.0) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, body, _ = api.call("GET", f"/api/attempts/{attempt_id}", token=token)
        if status == 200 and body["status"] in TERMINAL:
            return str(body["outcome"] or body["status"])
        time.sleep(1.0)
    return "sin resultado"


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--agents", type=int, default=5, help=f"{MIN_AGENTS} a {MAX_AGENTS}")
    parser.add_argument("--attempts", type=int, default=6, help="intentos por agente")
    parser.add_argument("--min-wait", type=float, default=6.0, help="segundos entre intentos")
    parser.add_argument("--max-wait", type=float, default=14.0)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args(argv)
    if not MIN_AGENTS <= args.agents <= MAX_AGENTS:
        parser.error(f"--agents debe estar entre {MIN_AGENTS} y {MAX_AGENTS}")
    if not 1 <= args.attempts <= CASES:
        parser.error(f"--attempts debe estar entre 1 y {CASES}")
    return args


def operator_secret(environ: dict[str, str] | None = None) -> str:
    """Secreto de operador desde el entorno; sin el, el servidor rechazaria cada sesion."""
    secret = (os.environ if environ is None else environ).get(SECRET_ENV, "").strip()
    if not secret:
        raise SystemExit(
            f"Falta {SECRET_ENV} en el entorno: el prefijo Agente- esta reservado y el servidor "
            "solo crea esas sesiones con el secreto de operador."
        )
    return secret


def main(argv: list[str]) -> int:
    args = parse(argv)
    secret = operator_secret()
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(2**32)
    print(f"Enjambre simulado: {args.agents} agentes, semilla {seed}", flush=True)
    api = Api(args.base_url, secret)
    threads = [
        threading.Thread(
            target=run_agent,
            args=(api, number, args, random.Random(seed + number)),
            name=f"Agente-{number}",
        )
        for number in range(1, args.agents + 1)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
