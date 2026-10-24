from agent_zero.armor.threat_pattern import ThreatPattern, pattern

_TOOL = r"(?:tool|function|herramienta|funcion)"
_CALL = r"(?:call|invoke|use|run|execute|trigger|llama|invoca|usa|ejecuta|lanza)\w*"

POISONING_PATTERNS: tuple[ThreatPattern, ...] = (
    pattern(
        "orden de ignorar al usuario o a las políticas",
        r"\b(?:ignore|disregard|ignora\w*)\s+(?:all\s+|any\s+|todas?\s+)?(?:the\s+|las\s+|al\s+)?"
        r"(?:user|usuario|previous|prior|anteriores?|other\s+tools?|otras\s+herramientas|"
        r"safety|seguridad|polic(?:y|ies)|politicas?)",
    ),
    pattern(
        "orden de llamar a otra herramienta",
        rf"\b{_CALL}\s+(?:also\s+|tambien\s+|primero\s+|first\s+)?(?:the\s+|a\s+|la\s+|una\s+)?"
        rf"(?:another|other|different|second|otra|otras|distinta|segunda)\s+{_TOOL}",
    ),
    pattern(
        "orden de encadenar una herramienta antes o después",
        rf"\b(?:before|after|antes|despues)\b[^.\n]{{0,60}}\b(?:you\s+must\s+|debes\s+|tienes\s+que\s+)"
        rf"{_CALL}\s+(?:\w+\s+){{0,2}}{_TOOL}",
    ),
    pattern(
        "orden de exfiltrar datos a un destino externo",
        r"\b(?:send|post|forward|upload|email|exfiltrate|envia\w*|manda\w*|reenvia\w*|sube|"
        r"filtra|exfiltra\w*)\s+(?:\w+\s+){0,6}(?:to|a|hacia)\s+"
        r"(?:https?://|\S+@\S+|an?\s+external|un\s+(?:servidor|correo|endpoint)\s+externo)",
    ),
    pattern(
        "exfiltration keyword",
        r"\bexfiltrat\w*|\bexfiltr\w+|\bleak\s+(?:the\s+)?(?:data|credentials|keys|tokens)",
    ),
    pattern(
        "orden de ocultar información al usuario",
        r"\b(?:do\s+not|don'?t|never|without)\s+(?:\w+\s+)?(?:tell|inform|mention|reveal|show|"
        r"notify|alert|let)\s+(?:\w+\s+){0,2}(?:the\s+)?(?:user|human|customer)"
        r"|\b(?:no|nunca|sin)\s+(?:le\s+)?(?:digas?|informes?|menciones?|reveles?|muestres?|"
        r"avises?|notifiques?|decirle)\s+(?:\w+\s+){0,2}(?:al?\s+)?(?:usuario|cliente|humano)"
        r"|\bhide\s+(?:this|that|it)\s+from\s+the\s+(?:user|customer)"
        r"|\bocult\w+\s+(?:esto|esta|eso|la\s+accion)\b[^.\n]{0,30}(?:usuario|cliente)"
        r"|\bkeep\s+(?:this|it)\s+(?:secret|hidden)|\bmanten\w*\s+(?:esto\s+)?en\s+secreto",
    ),
    pattern(
        "directiva dirigida al agente dentro de datos de herramienta",
        r"\b(?:note|nota|aviso|message|mensaje)\s+(?:to|for|para)\s+(?:the\s+|el\s+)?"
        r"(?:assistant|agent|ai|llm|asistente|agente|modelo)"
        r"|\b(?:assistant|agent|ai|llm|asistente|agente)\s*[,:]\s*(?:you\s+)?"
        r"(?:must|should|need\s+to|debes|tienes\s+que|ahora|ignore|ignora|call|llama|send|envia)",
    ),
    pattern(
        "cambio de tarea impuesto al agente",
        r"\b(?:your\s+new\s+(?:task|mission|goal|role)|tu\s+nueva\s+(?:tarea|mision|funcion)|"
        r"ahora\s+debes|a\s+partir\s+de\s+ahora\s+debes|instead\s+of\s+(?:that|the\s+task),?\s+you\s+"
        r"(?:must|should)|en\s+lugar\s+de\s+eso\s+debes)",
    ),
    pattern(
        "etiqueta de instrucción oculta",
        r"<\s*(?:important|system|instructions?|secret|hidden|override)\s*>"
        r"|\bimportant\s*:\s*(?:you|before|always|ignore|do\s+not)\b",
    ),
)
