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
