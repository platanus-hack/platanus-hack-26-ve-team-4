"""Assemble the self-contained review from source and captured backend records."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def safe_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def main():
    snapshots = [json.loads((HERE / name).read_text()) for name in (
        "runtime-snapshot.json", "runtime-playback-snapshot.json"
    )]
    text = (HERE / "zero-workbench.fragment.html").read_text()
    replacements = {
        "/*__ZERO_CSS__*/": (HERE / "zero-workbench.css").read_text(),
        "/*__ZERO_DATASETS__*/": safe_json(snapshots),
        "/*__ZERO_AUDIT__*/": safe_json(json.loads((HERE / "ux-audit.json").read_text())),
        "/*__ZERO_DESIGN__*/": safe_json(json.loads((HERE / "design-system.json").read_text())),
        "/*__ZERO_ADAPTER__*/": (HERE / "zero-data.js").read_text(),
        "/*__ZERO_APP__*/": (HERE / "zero-workbench.js").read_text(),
    }
    for key, value in replacements.items():
        assert text.count(key) == 1, key
        text = text.replace(key, value)
    assert "/*__ZERO_" not in text
    assert len(text.encode()) < 1_000_000
    output = HERE / "agent-zero-frontend.html"
    output.write_text(text)
    print(json.dumps({"file": str(output), "bytes": len(text.encode()), "sources": [s["run_id"] for s in snapshots]}))


if __name__ == "__main__":
    main()
