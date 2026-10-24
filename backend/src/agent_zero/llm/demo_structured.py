import json
from typing import Any

from strands.types.content import Messages


def structured_payload(model_name: str, messages: Messages) -> dict[str, Any]:
    text = next(
        str(part["text"])
        for message in reversed(messages)
        for part in message["content"]
        if "text" in part
    )
    payload = json.loads(text)
    if model_name == "AttackMutation":
        original = payload["original"]
        fixture = original.get("fixture")
        return {
            "messages": [f"Solicitud de laboratorio: {item}" for item in original["messages"]],
            "fixture_content": (
                f"Documento de laboratorio. {fixture['content']}" if fixture else None
            ),
        }
    if model_name == "FindingAnalysis":
        control = str(payload["missing_control"])
        family = "memory_poisoning" if "memory" in control else "tool_misuse"
        if payload["objective"] == "OBJ-ORDER":
            family = "direct_injection"
        return {
            "attack_family": family,
            "probable_cause": f"El control ausente identificado por la evidencia es {control}.",
            "reproduction_steps": [
                "Abrir una sesión sintética con la misma versión de política.",
                "Enviar los mensajes del intento y revisar las herramientas completadas.",
                "Comparar la evaluación del oráculo con el estado persistido del entorno.",
            ],
            "limitations": (
                "Explicación generada por reglas del modo demo; no es una evaluación semántica "
                "de un proveedor ni evidencia de eficacia frente a un LLM real."
            ),
        }
    if model_name == "PatchExplanation":
        return {
            "rationale": "El candidato incorpora los controles vinculados a los oráculos.",
            "expected_effect": "Denegar acciones indebidas y conservar las tareas legítimas.",
            "regression_risks": [
                "Bloquear pedidos propios, reembolsos válidos o preferencias inocuas."
            ],
            "limitations": "Asesoría del modo demo; las pruebas deciden la activación.",
        }
    raise ValueError(f"El modo demo no implementa el contrato estructurado {model_name}.")
