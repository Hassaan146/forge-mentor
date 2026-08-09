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

It is also the first Forge output most people ever see, so it is the first
place the colour system has to hold (rule R11): green passed, red stops you,
yellow is only missing something optional. `forge_ui` is the one non-stdlib
import allowed here, and only because it is stdlib-only itself and ships in
this same folder — it cannot be the missing thing this file exists to report.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass

import forge_ui as ui

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


def _plugin_python_works() -> tuple[bool, str]:
    """Can the literal command the plugin uses actually run Python?

    `hooks.json` and `.mcp.json` both invoke a bare `python`, so what matters is
    not whether *this* interpreter exists but whether that word resolves to a
    working one in the environment Claude Code launches from.

    That is a different question outside a terminal. An app started from a dock
    or a Start menu does not always inherit the PATH a shell has, and on Windows
    a bare `python` may resolve to the Microsoft Store stub — which exits
    without running anything, so the hook silently does nothing at all.
    """
    found = shutil.which("python")
    if found is None:
        return False, "the command `python` is not on PATH for this process"

    try:
        done = subprocess.run(
            ["python", "-c", "import sys; print(sys.version_info[0])"],
            capture_output=True,
            text=True,
            timeout=20,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"`python` is on PATH but would not run ({exc})"

    if done.returncode != 0 or done.stdout.strip() != "3":
        # The Store stub exits 0 with no output, which is exactly this.
        return False, (
            f"`python` resolves to {found}, which is not a working Python 3 "
            "(on Windows this is usually the Microsoft Store placeholder)"
        )
    return True, f"`python` resolves to {found}"


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

    # Asked separately from the version above, because they can disagree. The
    # interpreter running this check is whichever one you typed; the hooks get
    # whatever `python` means to Claude Code, and outside a terminal those are
    # often not the same thing.
    plugin_python_ok, plugin_python_detail = _plugin_python_works()
    checks.append(
        Check(
            "the `python` command Forge's hooks use",
            plugin_python_ok,
            plugin_python_detail,
            fix=(
                "put a working Python 3 on PATH for the app you launch Claude Code "
                "from, then restart it. On Windows, Settings > Manage app execution "
                "aliases > turn off the python.exe alias if it points at the Store."
            ),
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
    """The answer as a person reads it.

    Three states, three colours, and the word beside each one says the same
    thing — a check list read at a glance is exactly where colour earns its
    place, and exactly where colour alone would fail the user who cannot see
    it. `MISSING` is red and stops you; `not set` is yellow and does not.
    """
    checks = run() if checks is None else checks
    missing = [c for c in checks if not c.ok]
    blocking = [c for c in missing if c.fatal]

    lines = ["", f"  {ui.AMBER}{ui.BOLD}{ui.MARK} Forge — is this machine ready?{ui.NC}", ""]
    for check in checks:
        if check.ok:
            mark, ink, symbol = "ok", ui.GREEN, ui.RECORDED
        elif check.fatal:
            mark, ink, symbol = "MISSING", ui.RED, ui.BLOCKED
        else:
            mark, ink, symbol = "not set", ui.YELLOW, ui.COST

        lines.append(f"    {ink}{symbol} {mark:<8}{ui.NC} {check.name}")
        if not check.ok:
            lines.append(f"               {ui.DIM}{check.detail}{ui.NC}")
            lines.append(f"               {ui.DIM}fix:{ui.NC}  {ui.BLUE}{check.fix}{ui.NC}")
    lines.append("")

    if blocking:
        body = [
            "",
            f"  {ui.RED}{ui.BOLD}Forge cannot run yet.{ui.NC}",
            "",
            f"  {ui.DIM}The hooks would still block writes, but the engine that records{ui.NC}",
            f"  {ui.DIM}your decisions would be missing — so Forge would stop a write and{ui.NC}",
            f"  {ui.DIM}then be unable to record the decision that unblocks it.{ui.NC}",
            "",
        ]
        return "\n".join(lines) + ui.box(
            body, title=f"{ui.RED}{ui.BOLD}{ui.BLOCKED} NOT READY{ui.NC}", edge=ui.RED
        ) + ui.action(
            "Run the fix lines marked MISSING above.",
            hint="then run this check again — it has to come back Ready before Forge starts",
        )

    if missing:
        lines += [
            f"  {ui.GREEN}{ui.RECORDED} Ready.{ui.NC}  "
            f"{ui.DIM}The unset item above only affects reading reviews.{ui.NC}",
            "",
        ]
    else:
        lines += [f"  {ui.GREEN}{ui.BOLD}{ui.RECORDED} Ready.{ui.NC}", ""]
    return "\n".join(lines)


def ready() -> bool:
    return not [c for c in run() if c.fatal and not c.ok]


if __name__ == "__main__":  # pragma: no cover - CLI surface
    print(report())
    sys.exit(0 if ready() else 1)
