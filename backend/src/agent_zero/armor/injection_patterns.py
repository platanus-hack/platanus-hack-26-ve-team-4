from agent_zero.armor.threat_pattern import ThreatPattern, pattern

_ES_RULES = (
    r"(?:instrucciones|reglas|indicaciones|directrices|restricciones|politicas|limites|"
    r"ordenes|salvaguardas)"
)
_EN_RULES = (
    r"(?:instructions?|rules|guidelines|directives|prompts?|restrictions|programming|"
    r"configuration|safeguards|system\s+prompt|training)"
)
_ES_FORGET = r"(?:ignor|olvid|descart|omit|anul|borr|deshaz|desestim|salt|obvi)\w*"
_EN_FORGET = r"(?:ignore|disregard|forget|override|bypass|discard|overlook|skip|drop)"

OVERRIDE_PATTERNS: tuple[ThreatPattern, ...] = (
    pattern(
        "anulación de las reglas propias del agente",
        rf"\b{_ES_FORGET}\s+(?:(?:todas?|todo)\s+)?(?:tus|sus)\s+(?:\w+\s+)?{_ES_RULES}",
    ),
    pattern(
        "anulación de instrucciones anteriores",
        rf"\b{_ES_FORGET}\s+(?:(?:todas?|todo)\s+)?(?:las\s+|los\s+)?{_ES_RULES}\s+"
        r"(?:anteriores|previas|de\s+arriba|del\s+sistema|iniciales|originales)",
    ),
    pattern(
        "anulación de todo lo anterior",
        r"\b(?:ignor|olvid|descart|obvi)\w*\s+(?:todo|todas?)\s+(?:lo\s+)?"
        r"(?:anterior|previo|que\s+te\s+(?:dijeron|dieron|programaron|indicaron))",
    ),
    pattern(
        "override of the agent's own rules",
        rf"\b{_EN_FORGET}\s+(?:all\s+|any\s+|every\s+)?(?:of\s+)?(?:your|these|those)\s+"
        rf"(?:\w+\s+)?{_EN_RULES}",
    ),
    pattern(
        "override of previous instructions",
        rf"\b{_EN_FORGET}\s+(?:all\s+|any\s+|every\s+)?(?:of\s+)?(?:the\s+)?"
        rf"(?:previous|prior|above|earlier|preceding|original|initial)\s+(?:\w+\s+)?{_EN_RULES}",
    ),
    pattern(
        "override of everything said before",
        rf"\b{_EN_FORGET}\s+(?:everything|all)\s+(?:you\s+(?:were|have\s+been)\s+told|above|"
        r"before|previous\w*|prior)",
    ),
    pattern(
        "instrucciones nuevas dirigidas al agente",
        r"\b(?:nuevas?\s+instrucciones|new\s+instructions?|updated\s+instructions?)\s+"
        r"(?:para|for)\s+(?:el\s+|the\s+)?(?:asistente|agente|modelo|assistant|agent|model|ai)\b",
    ),
)

ROLE_PATTERNS: tuple[ThreatPattern, ...] = (
    pattern(
        "cambio de rol del agente",
        r"\b(?:ahora\s+eres\s+(?:un|una|el|la|mi)\b|a\s+partir\s+de\s+ahora\s+(?:eres|seras|actua)"
        r"|actua\s+como\s+si\s+(?:fueras|no\s+tuvieras|estuvieras)"
        r"|eres\s+un\s+(?:asistente|modelo|ia|bot)\s+sin|haz\s+de\s+cuenta\s+que\s+(?:eres|no\s+tienes)"
        r"|finge\s+(?:ser|que\s+eres|que\s+no\s+tienes))",
    ),
    pattern(
        "modo sin restricciones",
        r"\b(?:(?:activa\w*|entra\w*|habilita\w*|cambia\w*\s+a|pasa\w*\s+a)\s+(?:el\s+|en\s+)?modo\s+"
        r"(?:dios|jailbreak|sin\s+restricciones|sin\s+filtros)"
        r"|(?:entra\w*\s+en\s+)modo\s+desarrollador"
        r"|modo\s+(?:desarrollador|dios|jailbreak)\s+(?:activado|habilitado)"
        r"|(?:respond\w*|actua|comportate|contesta|funciona|habla)\s+(?:\w+\s+){0,2}"
        r"sin\s+(?:filtros|restricciones|censura|reglas|limites))",
    ),
    pattern(
        "role switch",
        r"\b(?:you\s+are\s+now\s+(?:a|an|the|my|in|dan|free)\b"
        r"|from\s+now\s+on\s+you\s+(?:are|will|must)"
        r"|act\s+as\s+(?:if\s+you\s+(?:were|had\s+no|are)|an?\s+(?:unrestricted|unfiltered|jailbroken|evil))"
        r"|pretend\s+(?:you\s+are|to\s+be|you\s+have\s+no|that\s+you\s+(?:are|have\s+no))"
        r"|roleplay\s+as|do\s+anything\s+now|take\s+on\s+the\s+(?:role|persona))",
    ),
    pattern(
        "unrestricted mode",
        r"\b(?:(?:enter|enable|activate|switch\s+to)\s+(?:the\s+|into\s+)?(?:god|jailbreak|dan)\s+mode"
        r"|(?:enter|enter\s+into)\s+developer\s+mode"
        r"|(?:developer|god|jailbreak|dan)\s+mode\s+(?:enabled|activated)\b)"
        r"|\b(?:respond|answer|reply|behave|operate)\w*\s+(?:\w+\s+){0,2}without\s+(?:any\s+)?"
        r"(?:restrictions|filters|rules|limits|limitations|censorship)",
    ),
)

SPOOF_PATTERNS: tuple[ThreatPattern, ...] = (
    pattern(
        "etiqueta falsa de mensaje de sistema",
        r"(?:\[\s*(?:system|sistema|inst|admin|developer)\s*\]|<\s*\|?\s*(?:system|sistema|im_start|"
        r"developer)\s*\|?\s*>|^\s*(?:system|developer)\s*:)",
    ),
    pattern(
        "mensaje presentado como del sistema o del desarrollador",
        r"\b(?:mensaje|aviso|nota|comunicado)\s+(?:oficial\s+)?(?:del|de\s+la)\s+"
        r"(?:sistema|desarrollador|equipo\s+de\s+ingenieria|administrador)"
        r"|\b(?:system|developer|admin)\s+(?:message|notice|override|note)\b",
    ),
)

EXFILTRATION_PATTERNS: tuple[ThreatPattern, ...] = (
    pattern(
        "solicitud de revelar la configuración interna",
        r"\b(?:revela|muestra\w*|imprime|repite|dime|comparte|filtra|escribe|traduce|resume|enumera|"
        r"dame|devuelve|lista)\s+(?:\w+\s+){0,3}(?:tu|tus)\s+(?:\w+\s+)?"
        r"(?:prompt|instrucciones|reglas|configuracion|herramientas|claves?|secretos?|directrices)"
        r"|\b(?:revela|muestra\w*|imprime|repite|dime|filtra)\s+(?:\w+\s+){0,3}"
        r"(?:el\s+)?(?:prompt|mensaje)\s+(?:de\s+)?(?:sistema|inicial|oculto)",
    ),
    pattern(
        "request to reveal internal configuration",
        r"\b(?:reveal|show|print|repeat|output|display|leak|tell|translate|summarize|list|"
        r"give|dump)\s+(?:me\s+)?(?:\w+\s+){0,3}(?:your\s+(?:\w+\s+)?"
        r"(?:instructions|prompt|rules|configuration|guidelines|secrets?|keys?|tools)"
        r"|the\s+(?:system|hidden|initial|original)\s+prompt)"
        r"|\beverything\s+(?:written\s+)?above\b",
    ),
)

AUTHORITY_PATTERNS: tuple[ThreatPattern, ...] = (
    pattern(
        "suplantación de autoridad",
        r"\bsoy\s+tu\s+(?:administrador\w*|desarrollador\w*|creador\w*|dueno)\b|\bautorizo\s+(?:a\s+)?(?:revelar|saltar|desactivar|ignorar|omitir)"
        r"|\bte\s+ordeno\s+(?:que\s+)?(?:ignores|reveles|desactives|borres|ejecutes)",
    ),
    pattern(
        "authority impersonation",
        r"\bi\s+am\s+(?:your|the)\s+(?:administrator|admin|developer|creator|owner|operator)\b"
        r"|\bi\s+authorize\s+you\s+to\b|\bi\s+order\s+you\s+to\b",
    ),
    pattern(
        "desactivación de protecciones",
        r"\b(?:desactiva|deshabilita|apaga|quita|elimina)\s+(?:\w+\s+){0,2}(?:tus|los|las)\s+"
        r"(?:filtros|guardarrailes|controles|protecciones|reglas|restricciones|medidas\s+de\s+seguridad)"
        r"|\b(?:disable|turn\s+off|deactivate|remove)\s+(?:\w+\s+){0,2}(?:your|the)\s+"
        r"(?:safety|filters?|guardrails?|rules|restrictions|protections|safeguards)",
    ),
)

INJECTION_PATTERNS: tuple[ThreatPattern, ...] = (
    *OVERRIDE_PATTERNS,
    *ROLE_PATTERNS,
    *SPOOF_PATTERNS,
    *EXFILTRATION_PATTERNS,
    *AUTHORITY_PATTERNS,
)
