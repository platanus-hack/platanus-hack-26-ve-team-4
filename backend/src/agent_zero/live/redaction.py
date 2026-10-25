"""Redacción del tablero en vivo: lo que el Público puede leer mientras la ronda sigue abierta.

`public_reply` cubre solo los canarios internos `AZ[PH]_…`. El honeytoken `AZH-KEY-…` aparece en
las respuestas de la ruta señuelo, así que se sustituye aquí, además de la redacción base.
"""

import re

from agent_zero.attempts.conversation import public_reply

HONEYTOKEN = re.compile(r"AZH-KEY-[A-Z0-9-]+")
REFERENCE = "[referencia]"


def redact_live(text: str) -> str:
    """Texto apto para el tablero público: sin canarios ni honeytokens."""
    return HONEYTOKEN.sub(REFERENCE, public_reply(text))
