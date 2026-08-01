#!/usr/bin/env python3
"""Forge Mentor — the governor.

Runs as a PreToolUse hook before any write to the project. Its single job is
decision 004: code may not be written until the current decision is recorded.

Contract with Claude Code:
  stdin   JSON with hook_event_name, tool_name, tool_input, cwd
  stdout  JSON; permissionDecision "deny" blocks the call and shows the reason
  exit 0  always — a crash here must not wedge the user's session

Behaviour is decision 004 (fail closed) with decision 017 (all-or-nothing):
  * a project with no .forge/ is not a Forge project — stay out of the way
  * an open question with no recorded answer blocks writes
  * an explicit, recorded override lets the write through

Rule R3 applies: everything it needs is read from files in the repo, so a
fresh session on another account behaves identically.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Tools that write to the project. Reads are never blocked — the mentor has to
# be able to look at the code in order to teach it.
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}

# Files Forge owns. Writing its own records must never be blocked by itself.
SELF_PATHS = (".forge/",)


def allow() -> None:
    """Say nothing and let the normal permission flow decide."""
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


def read_progress(forge_dir: Path) -> dict:
    """Read the progress file's labelled header.

    Decision 001 accepts that a hand edit can break this file, and requires
    Forge to say exactly what is wrong rather than guess. Decision 011 requires
    in-flight state to live here so another account can pick the work up.
    """
    progress = forge_dir / "progress.md"
    if not progress.exists():
        return {}

    text = progress.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        raise ValueError(
            f"{progress} is missing its labelled section at the top. "
            "Restore it with:  git checkout -- .forge/progress.md"
        )

    end = text.find("---", 3)
    if end == -1:
        raise ValueError(
            f"{progress} has an unterminated labelled section. "
            "Restore it with:  git checkout -- .forge/progress.md"
        )

    header: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            header[key.strip()] = value.strip()
    return header


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # Malformed input is not the user's fault and must not block them.
        allow()

    if payload.get("hook_event_name") != "PreToolUse":
        allow()
    if payload.get("tool_name") not in WRITE_TOOLS:
        allow()

    cwd = Path(payload.get("cwd") or ".")
    forge_dir = cwd / ".forge"

    # Not a Forge project. Forge only acts where it was invited (decision 014).
    if not forge_dir.is_dir():
        allow()

    target = str(payload.get("tool_input", {}).get("file_path", ""))
    if any(part in target.replace("\\", "/") for part in SELF_PATHS):
        allow()

    try:
        header = read_progress(forge_dir)
    except ValueError as exc:
        # Fail closed (decision 004), but always with a way out (challenge H1).
        deny(f"Forge cannot read its own notes.\n{exc}")

    open_question = header.get("open_question", "").strip()
    override = header.get("override_active", "").strip().lower()

    if override in {"true", "yes"}:
        allow()

    if open_question and open_question.lower() not in {"none", "", "null"}:
        deny(
            f"No decision recorded yet for: {open_question}\n"
            "Code cannot be written until you decide this.\n"
            "  → answer the open question, or\n"
            "  → say \"write it anyway\" and confirm (the override is recorded)"
        )

    allow()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never wedge the session
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"Forge's safety check failed to run: {exc}\n"
                            "Blocked by default. Say \"write it anyway\" to override."
                        ),
                    }
                }
            )
        )
        sys.exit(0)
