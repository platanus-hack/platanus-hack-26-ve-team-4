from agent_zero.armor.models import ArmorAction, Surface, ThreatKind
from agent_zero.armor.pattern_scanner import scan_threats
from agent_zero.armor.pii_redactor import redact_with_kinds
from agent_zero.armor.schemas import ArmorFinding, ArmorVerdict


class ModelArmor:
    def screen(self, text: str, surface: Surface) -> ArmorVerdict:
        threats = scan_threats(text, surface)
        redacted, kinds = redact_with_kinds(text)
        pii = tuple(
            ArmorFinding(kind=ThreatKind.PII, surface=surface, detail=kind.description)
            for kind in kinds
        )
        findings = (*threats, *pii)
        if threats:
            return ArmorVerdict(action=ArmorAction.BLOCK, findings=findings)
        if pii:
            return ArmorVerdict(
                action=ArmorAction.REDACT, findings=findings, sanitized_text=redacted
            )
        return ArmorVerdict(action=ArmorAction.ALLOW, sanitized_text=text)

    def redact_pii(self, text: str) -> str:
        return redact_with_kinds(text)[0]
