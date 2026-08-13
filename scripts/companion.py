"""Forge Mentor: bringing the companion plugin in with Forge, every session.

Routing ponytail at the building stage puts it in a table. A table is read by
whatever asks the table, and if the builder forgets to ask, nothing happens and
nothing says so. That is the failure this repository has repeated more than any
other: the rule was in the code, and the code was not in the path.

So this is a hook. It runs at the start of every session in a Forge project and
puts one line into the context: ponytail is installed, apply it. Or, once per
project and never again, the command to install it.

**What it does not do.** It does not block, it does not decide, and it cannot
fail loudly. Being a nudge, the correct behaviour on any error is silence: a
companion is optional by definition (decision 058), and a hook that wedges a
session to recommend a plugin has done more harm than the plugin could do good.

`FORGE_NO_COMPANION=1` turns it off.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = "https://github.com/DietrichGebert/ponytail"

# Said once per session when it is there. Short on purpose: this is context tax
# paid on every session in every Forge project, and the argument for the
# companion was token efficiency in the first place.
PRESENT = (
    "ponytail is installed. Apply it when writing code: check whether the thing "
    "needs writing at all, whether this project already does it, and whether the "
    "standard library does it, before adding anything new. Forge's security floor "
    "and the recorded decision win wherever the two disagree."
)

# Said once per project, ever. A suggestion repeated is an advertisement.
ABSENT = (
    "Mention once, in one line, then never again this project: ponytail is a "
    "companion plugin that gets an agent to write the least code that works, and "
    "Forge routes it at the build and review stages when it is present. It is "
    "optional and Forge works without it.\n\n"
    "    /plugin marketplace add DietrichGebert/ponytail\n"
    "    /plugin install ponytail@ponytail\n"
)

MARKER = "companion-offered"


def _forge_dir(start: Path) -> Path | None:
    """The project's notes, or None when this is not a Forge project."""
    try:
        import forge_state as fs

        return fs.find_forge_dir(start)
    except Exception:
        return None


def _installed() -> bool:
    try:
        import forge_skills as sk

        return sk.companion_installed("ponytail")
    except Exception:
        # Unknown counts as installed, so the fallback is silence rather than
        # advertising something the user may already have.
        return True


def message(cwd: Path) -> str:
    """What to add to this session's context, or nothing at all."""
    if os.environ.get("FORGE_NO_COMPANION"):
        return ""

    forge = _forge_dir(cwd)
    if forge is None:
        return ""  # not a Forge project, so not Forge's business

    if (forge / "paused.md").exists():
        return ""

    if _installed():
        return PRESENT

    offered = forge / MARKER
    if offered.exists():
        return ""
    try:
        offered.write_text(
            "Forge mentioned the ponytail companion here once. It does not ask again.\n",
            encoding="utf-8",
        )
    except OSError:
        # Cannot remember having asked, so do not ask: repeating is worse than
        # staying quiet, and the user can install it from the README.
        return ""
    return ABSENT


def main() -> None:  # pragma: no cover - exercised as a subprocess
    try:
        payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
        cwd = Path(str(payload.get("cwd") or os.getcwd()))
        text = message(cwd)
    except Exception:
        text = ""

    if not text:
        print(json.dumps({}))
        return

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": text,
                }
            }
        )
    )


if __name__ == "__main__":  # pragma: no cover - CLI surface
    main()
