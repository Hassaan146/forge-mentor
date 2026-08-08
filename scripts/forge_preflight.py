"""Forge Mentor — is this machine ready to run Forge?

There is nothing to deploy: Forge is a plugin, it has no server and no hosted
anything (the non-goals in the plan are explicit about it). But "no deployment"
is not the same as "no prerequisites", and the difference is where a new laptop
gets stuck.

The failure this exists to prevent is a quiet half-install. The hooks are
stdlib-only, so the governor keeps working on a machine with nothing else set
up — Forge looks alive, blocks writes, and behaves. Meanwhile the MCP server
cannot start for want of one package, so every tool that records a decision is
gone. Forge would block a write and then be unable to record the decision that
unblocks it, which is the worst state the product has.

So this is checked up front, in plain language, with the exact command to fix
each thing. Stdlib only, deliberately — a readiness check that needs a
dependency installed cannot report that the dependency is missing.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass

# 3.12 is where `shutil.rmtree(onexc=...)` arrives, which the library cleanup
# uses. Below that Forge still runs, so this is a warning rather than a refusal.
WANTED_PYTHON = (3, 12)


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""
    fatal: bool = False


def _has_command(name: str) -> bool:
    return shutil.which(name) is not None


def _gh_signed_in() -> bool:
    if not _has_command("gh"):
        return False
    try:
        done = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, text=True, timeout=15, shell=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def run() -> list[Check]:
    """Everything Forge needs, and what to do about anything missing."""
    checks: list[Check] = []

    version = sys.version_info
    checks.append(
        Check(
            "Python 3.12 or newer",
            version >= WANTED_PYTHON,
            f"found {version.major}.{version.minor}.{version.micro}",
            fix="install Python 3.12+ from python.org, then restart Claude Code",
        )
    )

    # The one that actually stops Forge working, and the one nothing installs
    # for you. Claude Code does not manage a plugin's Python dependencies.
    has_mcp = importlib.util.find_spec("mcp") is not None
    checks.append(
        Check(
            "the mcp package",
            has_mcp,
            "the engine cannot start without it — every Forge tool would be missing",
            fix=f'"{sys.executable}" -m pip install "mcp>=2.0.0,<3"',
            fatal=True,
        )
    )

    checks.append(
        Check(
            "git",
            _has_command("git"),
            "used for the decision history and for review",
            fix="install git from git-scm.com",
            fatal=True,
        )
    )

    checks.append(
        Check(
            "GitHub sign-in",
            _gh_signed_in(),
            "needed to read review findings; everything else works without it",
            fix="gh auth login",
        )
    )

    return checks


def report(checks: list[Check] | None = None) -> str:
    """The answer as a person reads it."""
    checks = run() if checks is None else checks
    missing = [c for c in checks if not c.ok]
    blocking = [c for c in missing if c.fatal]

    lines = ["", "  Forge — is this machine ready?", ""]
    for check in checks:
        mark = "ok  " if check.ok else ("MISSING" if check.fatal else "not set")
        lines.append(f"    [{mark:>7}]  {check.name}")
        if not check.ok:
            lines.append(f"               {check.detail}")
            lines.append(f"               fix:  {check.fix}")
    lines.append("")

    if blocking:
        lines += [
            "  Forge cannot run yet. The hooks would still block writes, but the",
            "  engine that records your decisions would be missing — so Forge would",
            "  stop a write and then be unable to record the decision that unblocks",
            "  it. Fix the lines marked MISSING first.",
            "",
        ]
    elif missing:
        lines += ["  Ready. The unset item above only affects reading reviews.", ""]
    else:
        lines += ["  Ready.", ""]
    return "\n".join(lines)


def ready() -> bool:
    return not [c for c in run() if c.fatal and not c.ok]


if __name__ == "__main__":  # pragma: no cover - CLI surface
    print(report())
    sys.exit(0 if ready() else 1)
