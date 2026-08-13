"""Shared test setup.

Putting the path setup here removes the duplicated `sys.path.insert` from every
test module — pytest imports `conftest.py` before collecting tests, so the
scripts directory is importable everywhere below this folder.

The equivalent line inside `scripts/governor.py` has to stay: Claude Code runs
that file directly as a hook command, with no package context and no install
step, so it cannot rely on pytest having prepared the path.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def pass_lean(forge_dir: Path, marker: str = "") -> None:
    """Put the current step through the lean pass, the way a session would.

    Shared because six test modules drive a project to "buildable", and every
    one of them now has to answer whether the step is worth building before its
    own question is worth asking. Six copies of that would be six chances to
    write it slightly differently and one chance to notice.
    """
    import forge_lean as ln
    import forge_state as fs
    import forge_steps as stp

    if not marker:
        step = stp.current(forge_dir)
        if step is None:
            return
        marker = step.marker

    asked = fs.ask(forge_dir, "Is this step worth building?", affects=ln.marker_for(marker))
    fs.answer(
        forge_dir,
        asked.id,
        ln.body(
            "as proposed",
            [ln.Finding(rung, "checked") for rung in ln.LADDER_KEYS],
            "nothing already does it",
        ),
    )
