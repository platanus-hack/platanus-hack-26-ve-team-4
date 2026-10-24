from agent_zero.armor.decoding import decoded_candidates
from agent_zero.armor.hidden_text import has_invisible_run, has_tag_characters
from agent_zero.armor.injection_patterns import INJECTION_PATTERNS
from agent_zero.armor.models import POISONING_SURFACES, TOOL_SURFACES, Surface, ThreatKind
from agent_zero.armor.normalization import text_variants
from agent_zero.armor.poisoning_patterns import POISONING_PATTERNS
from agent_zero.armor.schemas import ArmorFinding
from agent_zero.armor.threat_pattern import ThreatPattern


def patterns_for(surface: Surface) -> tuple[ThreatPattern, ...]:
    if surface in POISONING_SURFACES:
        return (*INJECTION_PATTERNS, *POISONING_PATTERNS)
    return INJECTION_PATTERNS


def threat_kind_for(surface: Surface) -> ThreatKind:
    if surface in TOOL_SURFACES:
        return ThreatKind.TOOL_POISONING
    return ThreatKind.PROMPT_INJECTION


def matching_labels(text: str, patterns: tuple[ThreatPattern, ...]) -> list[str]:
    variants = text_variants(text)
    return [
        item.label for item in patterns if any(item.regex.search(variant) for variant in variants)
    ]


def scan_threats(text: str, surface: Surface) -> tuple[ArmorFinding, ...]:
    patterns = patterns_for(surface)
    findings: list[ArmorFinding] = []
    seen: set[tuple[ThreatKind, str]] = set()

    def add(kind: ThreatKind, detail: str) -> None:
        if (kind, detail) not in seen:
            seen.add((kind, detail))
            findings.append(ArmorFinding(kind=kind, surface=surface, detail=detail))

    for label in matching_labels(text, patterns):
        add(threat_kind_for(surface), label)
    if has_tag_characters(text):
        add(ThreatKind.ENCODED_PAYLOAD, "caracteres de etiqueta Unicode ocultos en el texto")
    if has_invisible_run(text):
        add(ThreatKind.ENCODED_PAYLOAD, "secuencia de caracteres invisibles en el texto")
    for technique, decoded in decoded_candidates(text):
        for label in matching_labels(decoded, patterns):
            add(ThreatKind.ENCODED_PAYLOAD, f"carga codificada ({technique}): {label}")
    return tuple(findings)
