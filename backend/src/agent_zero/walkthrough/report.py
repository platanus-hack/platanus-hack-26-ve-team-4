from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Check:
    component: str
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)
    runs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add(self, component: str, name: str, ok: bool, detail: Any = "") -> bool:
        self.checks.append(Check(component, name, ok, str(detail)))
        return ok

    @property
    def ok(self) -> bool:
        return bool(self.checks) and all(check.ok for check in self.checks)

    def render(self) -> str:
        lines = [
            f"{'OK ' if check.ok else 'FALLA'} [{check.component}] {check.name}"
            + (f" -> {check.detail}" if check.detail else "")
            for check in self.checks
        ]
        passed = sum(check.ok for check in self.checks)
        lines.append(f"\n{passed}/{len(self.checks)} comprobaciones pasaron")
        return "\n".join(lines)
