import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs" / "trazabilidad.md"
TESTS = Path(__file__).resolve().parent
ROW = re.compile(r"^\| ([A-Z0-9]+-\d{2}) \|.*\| ([a-z]+) \|$")
MARKER = re.compile(r"requirement\(([^)]*)\)")
QUOTED = re.compile(r"\"([A-Z0-9]+-\d{2})\"")
DONE = "hecho"


def catalog() -> dict[str, str]:
    rows = (ROW.match(line) for line in CATALOG.read_text(encoding="utf-8").splitlines())
    return {row.group(1): row.group(2) for row in rows if row}


def cited() -> dict[str, set[str]]:
    citations: dict[str, set[str]] = {}
    for path in TESTS.rglob("test_*.py"):
        if path.name == Path(__file__).name:
            continue
        for marker in MARKER.findall(path.read_text(encoding="utf-8")):
            for requirement in QUOTED.findall(marker):
                citations.setdefault(requirement, set()).add(path.name)
    return citations


def test_catalog_is_parseable() -> None:
    assert len(catalog()) >= 20


def test_tests_only_cite_known_requirements() -> None:
    assert set(cited()) - set(catalog()) == set()


def test_every_done_requirement_has_a_test() -> None:
    citations = cited()
    missing = [rid for rid, status in catalog().items() if status == DONE and rid not in citations]
    assert missing == []
