#!/usr/bin/env python3
"""Forge Mentor — the phase gates.

Runs as a PreToolUse hook on git commands. Decision 009 says a step is not
finished until its tests pass, its review is clean, and the user can explain it
back — so a commit before the tests pass is a step claiming to be done when it
is not.

  stdin   JSON with hook_event_name, tool_name, tool_input, cwd
  stdout  JSON; permissionDecision "deny" blocks the call and shows the reason
  exit 0  always — a crash in a gate must never wedge the user's session

Three rules, in order of how much they matter:

  1. The decision chain must be whole (decisions 021, 022). Committing a broken
     history would make the damage permanent and push it to everyone else.
  2. Tests must pass before a commit (decision 009).
  3. Three failures escalate to the user instead of grinding (decision 009).

Rule 2 scales with the step, as 009 requires: a routine change is not held to
the same bar as a load-bearing one, or the ceremony would destroy the live pace
promised in rule R7.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import forge_integrity as fi  # noqa: E402
import forge_repair as fr  # noqa: E402
import forge_state as fs  # noqa: E402

MAX_ATTEMPTS = 3  # decision 009 — escalate rather than loop forever

# Commands that make work permanent. Only these are gated; ordinary git use
# (status, diff, log, add) is never interrupted.
COMMIT_PATTERN = re.compile(r"\bgit\s+(commit|push)\b")


def allow() -> None:
    print(json.dumps({}))
    sys.exit(0)


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def is_commit_command(command: str) -> bool:
    """True for a command that makes work permanent.

    Matched on the text rather than a parsed argv because the Bash tool passes
    a shell string, which may chain commands with && or ;. Anything containing
    a commit or push is gated.
    """
    return bool(COMMIT_PATTERN.search(command or ""))


def run_tests(project: Path) -> tuple[bool, str]:
    """Run the project's tests. Returns (passed, output tail).

    A project with no test suite is not failed — Forge teaches, it does not
    refuse to work with a project that has not got there yet.
    """
    if not (project / "tests").is_dir() and not list(project.glob("test_*.py")):
        return True, "no test suite in this project yet"

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--no-header", "-x"],
            cwd=project,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except FileNotFoundError:
        return True, "pytest is not installed — gate skipped"
    except subprocess.TimeoutExpired:
        return False, "the tests took longer than five minutes and were stopped"

    tail = "\n".join((result.stdout or result.stderr).strip().splitlines()[-12:])
    return result.returncode == 0, tail


def bump_attempts(forge_dir: Path) -> int:
    """Count a failed gate, and return the new total.

    Decision 009 stops the loop after three failures rather than letting a
    learner grind against the same error. The count lives in the progress file
    so it survives a crash or a switch to another account (decision 011).
    """
    try:
        progress = fs.Progress.read(forge_dir)
    except fs.StateError:
        # An unreadable progress file must not silently disable the escalation.
        # Returning 0 here meant failures never accumulated after a crash or a
        # damaged file, so the third-strike message never fired — decision 009
        # would have been quietly switched off at exactly the moment a user was
        # most likely to be stuck. Start a fresh count instead.
        progress = fs.Progress(gate_attempts=1)
        progress.write(forge_dir)
        return progress.gate_attempts

    progress.gate_attempts += 1
    progress.write(forge_dir)
    return progress.gate_attempts


def clear_attempts(forge_dir: Path) -> None:
    """Reset the count once the gate passes."""
    try:
        progress = fs.Progress.read(forge_dir)
    except fs.StateError:
        return
    if progress.gate_attempts:
        progress.gate_attempts = 0
        progress.write(forge_dir)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        allow()

    if payload.get("hook_event_name") != "PreToolUse":
        allow()
    if payload.get("tool_name") != "Bash":
        allow()

    command = str(payload.get("tool_input", {}).get("command", ""))
    if not is_commit_command(command):
        allow()  # ordinary git use is never interrupted

    project = Path(payload.get("cwd") or ".")
    forge_dir = fs.find_forge_dir(project)
    if forge_dir is None:
        allow()  # not a Forge project

    # ---- rule 1: never make a damaged history permanent -------------------
    try:
        problems = fr.diagnose(forge_dir)
    except Exception as exc:
        deny(f"Forge could not check the decision history: {exc}")

    if problems:
        deny(
            "The decision history has been altered — committing would make that "
            "permanent and push it to everyone else.\n"
            + "\n".join(f"  {p.describe()}" for p in problems)
            + "\n\n  Repair it first, then commit."
        )

    # ---- rule 2: a step is not done until its tests pass (decision 009) ----
    passed, output = run_tests(project.parent if project.name == ".forge" else project)
    if passed:
        clear_attempts(forge_dir)
        allow()

    # ---- rule 3: escalate rather than grind (decision 009) ----------------
    attempts = bump_attempts(forge_dir)

    if attempts >= MAX_ATTEMPTS:
        deny(
            f"The tests have failed {attempts} times on this step.\n\n"
            f"{output}\n\n"
            "  Forge is stopping rather than letting you loop on the same error.\n"
            "  Something in the approach may be wrong, not just the code.\n\n"
            "  → ask Forge to explain what the failure actually means, or\n"
            "  → revisit the decision behind this step, or\n"
            '  → say "commit anyway" and confirm (the override is recorded)'
        )

    deny(
        "The tests do not pass, so this step is not finished (decision 009).\n\n"
        f"{output}\n\n"
        f"  attempt {attempts} of {MAX_ATTEMPTS}\n"
        "  → fix the failure and commit again, or\n"
        '  → say "commit anyway" and confirm (the override is recorded)'
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # never wedge the session
        deny(
            f"Forge's commit gate failed to run: {exc}\n"
            'Blocked by default. Say "commit anyway" to override.'
        )
