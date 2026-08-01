#!/usr/bin/env python3
"""Forge Mentor — the governor.

Runs as a PreToolUse hook before any write to the project. Its single job is
decision 004: code may not be written until the current decision is recorded.

Contract with Claude Code:
  stdin   JSON with hook_event_name, tool_name, tool_input, cwd
  stdout  JSON; permissionDecision "deny" blocks the call and shows the reason
  exit 0  always — a crash here must not wedge the user's session

Behaviour:
  decision 004  fail closed. Blocked by default; an explicit, recorded
                override is the only way through.
  decision 018  the open question is *computed* from the decision files, not
                read from a mutable field. A question is a file with
                `status: open`.
  decision 019  state is re-read from disk every time. Nothing is cached and
                nothing is keyed to a Claude account, so switching accounts
                changes nothing.
  decision 014  Forge only acts where it was invited. No `.forge/` means this
                is not a Forge project — stay completely out of the way.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Claude Code invokes this file directly as a hook command, so it runs as a
# standalone script with no package context. There is no install step for a
# plugin, so the sibling import has to be made reachable here.
sys.path.insert(0, str(Path(__file__).parent))

from forge_state import FORGE_DIR, StateError, find_forge_dir, writes_allowed  # noqa: E402

# Tools that write to the project. Reads are never blocked — the mentor has to
# be able to look at the code in order to teach it.
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}


def is_forge_owned(target: str) -> bool:
    """True when this write is Forge writing its own notes.

    Compares path *segments* rather than matching a substring. A separator
    heuristic such as "/.forge/" misses a relative target like
    ".forge/decisions/001.md" — which would block Forge from recording the very
    decision that unblocks the user.
    """
    if not target:
        return False
    return FORGE_DIR in Path(target.replace("\\", "/")).parts


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

    forge_dir = find_forge_dir(Path(payload.get("cwd") or "."))
    if forge_dir is None:
        allow()  # not a Forge project

    if is_forge_owned(str(payload.get("tool_input", {}).get("file_path", ""))):
        allow()  # Forge writing its own notes

    try:
        permitted, question = writes_allowed(forge_dir)
    except StateError as exc:
        # Fail closed (004), but always with a way out (challenge finding H1).
        deny(f"Forge cannot read its own notes.\n{exc}")

    if permitted:
        allow()

    deny(
        f"No decision recorded yet for: {question}\n"
        "Code cannot be written until you decide this.\n"
        "  → answer the open question, or\n"
        '  → say "write it anyway" and confirm (the override is recorded)'
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # never wedge the session
        deny(
            f"Forge's safety check failed to run: {exc}\n"
            'Blocked by default. Say "write it anyway" to override.'
        )
