"""Forge Mentor: the hook that catches an invented reference as it is written.

PostToolUse, on writes. The file has already landed, and that is the right time
rather than a missed one: the reference cannot be checked until it exists, and
blocking a write on suspicion would stop work the user is watching.

**It does not fix anything.** A silent correction is a second guess stacked on
the first, and the user learns nothing from a mistake they never saw. It says
what was named, says the project does not have it, and hands the model an
instruction to put the question to the user before going any further.

Standard library only, silent on every failure, and it never blocks.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _written(payload: dict) -> Path | None:
    target = (payload.get("tool_input") or {}).get("file_path")
    return Path(str(target)) if target else None


def message(payload: dict) -> str:
    """What to hand back, or nothing at all."""
    if os.environ.get("FORGE_NO_GROUNDING"):
        return ""

    try:
        import forge_grounding as gr
        import forge_state as fs
    except Exception:
        return ""

    cwd = Path(str(payload.get("cwd") or os.getcwd()))
    forge = fs.find_forge_dir(cwd)
    if forge is None:
        return ""  # not a Forge project, not Forge's business
    if (forge / "paused.md").exists():
        return ""

    path = _written(payload)
    if path is None or not path.is_file():
        return ""

    project = forge.parent.parent if forge.name == "forge" else forge.parent
    try:
        claims = gr.check_file(path, project)
    except Exception:
        return ""

    if not claims:
        return ""

    lines = [claim.question() for claim in claims[:5]]
    return (
        "Forge checked what that file refers to and found "
        f"{len(claims)} reference{'' if len(claims) == 1 else 's'} this project "
        "does not appear to have:\n\n"
        + "\n".join(f"- {line}" for line in lines)
        + "\n\n**Stop and ask the user before writing anything else.** Do not "
        "quietly change it and do not assume it is a package to install: each "
        "of these is either a dependency that has to be added and recorded, a "
        "file that is about to be written, or something that was invented. "
        "Which one it is, is theirs to say. Put it to them with `render_decision` "
        "and record the answer."
    )


def main() -> None:  # pragma: no cover - exercised as a subprocess
    try:
        payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
        text = message(payload)
    except Exception:
        text = ""

    if not text:
        print(json.dumps({}))
        return

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": text,
                }
            }
        )
    )


if __name__ == "__main__":  # pragma: no cover - CLI surface
    main()
