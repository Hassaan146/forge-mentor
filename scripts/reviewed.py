"""Forge Mentor: when the hosted reviews land, the local one runs.

The two GitHub reviewers post to the pull request and a workflow writes them
into `.claude/forge/reviews/pr-<n>.md`. ponytail reviews the same code from
here. Nothing joined the two: filing its findings was a tool somebody had to
remember, which is the shape of every rule this repository has watched get
skipped.

So the arrival of the file is the trigger, and it is checked as **state rather
than as an event**. Catching the moment the file is written would miss the way
it usually arrives: the workflow commits it on GitHub's side and the user pulls
in a terminal, which no hook in the session ever sees. Comparing the review on
disk against the version the local reviewer last saw catches it however it got
there, including a fetch three sessions ago that nobody followed up.

Runs after any tool that could have brought one in, and after a prompt, so a
`git pull` in another window is noticed at the top of the next turn. Says
nothing when everything has been reviewed, which is most of the time.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_PR_FILE = re.compile(r"^pr-(\d+)\.md$")


def _owed(forge: Path) -> list[int]:
    """Every pull request whose current review the local reviewer has not seen."""
    import forge_review as rv

    folder = forge / rv.REVIEWS_DIR
    if not folder.is_dir():
        return []

    out: list[int] = []
    for path in sorted(folder.glob("pr-*.md")):
        match = _PR_FILE.match(path.name)
        if not match:
            continue  # the .local.md files are not reviews of anything
        number = int(match.group(1))
        try:
            if rv.local_review_owed(forge, number):
                out.append(number)
        except Exception:
            continue
    return out


def message(cwd: Path) -> str:
    """What to add to the turn, or nothing at all."""
    if os.environ.get("FORGE_NO_REVIEW_TRIGGER"):
        return ""

    try:
        import forge_state as fs
    except Exception:
        return ""

    forge = fs.find_forge_dir(cwd)
    if forge is None or (forge / "paused.md").exists():
        return ""

    try:
        owed = _owed(forge)
    except Exception:
        return ""

    if not owed:
        return ""

    listed = ", ".join(f"#{number}" for number in owed)
    return (
        f"The hosted review for {listed} is on disk and ponytail has not seen "
        "this version of it.\n\n"
        "**Run ponytail's review over that pull request's diff now**, before "
        "working any of the findings, and file what it raises with "
        "`record_review_findings`. Then `fetch_review` rebuilds the combined "
        "file and the fix loop works all three reviewers in one pass.\n\n"
        "Filing nothing is a valid outcome and still counts as having looked: "
        "'ponytail found nothing' and 'ponytail has not run' are different "
        "states, and only the second one holds a step up."
    )


def main() -> None:  # pragma: no cover - exercised as a subprocess
    try:
        payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
        event = str(payload.get("hook_event_name") or "PostToolUse")
        text = message(Path(str(payload.get("cwd") or os.getcwd())))
    except Exception:
        event, text = "PostToolUse", ""

    if not text:
        print(json.dumps({}))
        return

    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
        )
    )


if __name__ == "__main__":  # pragma: no cover - CLI surface
    main()
