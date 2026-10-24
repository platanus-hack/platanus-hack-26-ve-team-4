import subprocess
from pathlib import Path
from typing import Any


def source_revision() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[4]
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=2,
                check=True,
            ).stdout.strip()
        )
        return {"commit": revision, "working_tree_dirty": dirty}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "working_tree_dirty": None}
