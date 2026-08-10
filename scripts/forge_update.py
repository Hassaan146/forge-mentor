"""Forge Mentor — "there is a newer version", said once, quietly.

**Why this exists.** The installed plugin lagged the repository for four
sessions running. Every one of them looked like a bug: rules that were fixed
still firing, questions that had been reordered still coming out in the old
order, colours that were shipped still absent. Nothing on screen ever said the
copy on disk was two weeks behind, so every session began by debugging the
wrong build.

An app store solves this with one line of text. So does this.

**Stdlib only, like the hooks**, because it runs as one — a plugin that needs a
package installed in order to tell you it is out of date is a plugin that
cannot tell you anything on the machine where it matters.

**It never blocks and never nags.** Any failure at all — no network, a proxy, a
rate limit, a malformed answer — is silence. The check runs at most once a day
and remembers its answer, and `FORGE_NO_UPDATE_CHECK=1` turns it off entirely.
A version notice that interrupts is a version notice people learn to skip.

**Nothing from the network is displayed.** Only a version string, and only
after it matches a strict numeric pattern; anything else is treated as "no
update". Remote text on a user's screen is remote text in a model's context
(challenge finding C3), and a release note is not worth that door.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# Once a day. Often enough that a stale copy is caught the next morning, rare
# enough that it is never in the way of the work.
CHECK_EVERY = 24 * 60 * 60

# Short. This runs before the user's first turn, and a plugin that adds five
# seconds to every session start has made itself the problem it was solving.
TIMEOUT = 5.0

# A version and nothing else. The remote is not trusted to send anything a
# person will read.
_VERSION = re.compile(r"^\d+(?:\.\d+){0,3}$")
_REPO = re.compile(r"github\.com[/:]([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/*$")


@dataclass(frozen=True)
class Update:
    """A newer version exists."""

    installed: str
    latest: str
    repository: str

    @property
    def releases(self) -> str:
        return f"{self.repository}/commits"


def _manifest(plugin_root: Path) -> dict:
    try:
        text = (plugin_root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        loaded = json.loads(text)
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, ValueError):
        return {}


def installed_version(plugin_root: Path) -> str:
    return str(_manifest(plugin_root).get("version", "")).strip()


def repository_of(plugin_root: Path) -> tuple[str, str, str]:
    """Owner, repo, and the browsable URL — read from the manifest.

    Taken from the plugin's own `repository` field rather than hard-coded, so a
    fork checks itself rather than reporting that it is behind the original.
    """
    url = str(_manifest(plugin_root).get("repository", "")).strip()
    found = _REPO.search(url)
    if not found:
        return "", "", ""
    return found.group(1), found.group(2), f"https://github.com/{found.group(1)}/{found.group(2)}"


def _as_numbers(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return ()


def is_newer(latest: str, installed: str) -> bool:
    """Compare as numbers, never as text.

    `"1.10.0" > "1.9.0"` is false as strings, and that is the version where
    everybody's update notice quietly stops appearing.
    """
    a, b = _as_numbers(latest), _as_numbers(installed)
    if not a or not b:
        return False
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


# --------------------------------------------------------------------------
# remembering the answer
# --------------------------------------------------------------------------


def cache_file() -> Path:
    """Kept outside the plugin, deliberately.

    Inside it, the record of "I checked today" would be deleted by the very
    reinstall it exists to make unnecessary — so the first session after every
    update would go to the network again.

    `FORGE_UPDATE_CACHE` moves it, which is how the tests avoid writing to a
    real user's home directory while still exercising the real function.
    """
    override = os.environ.get("FORGE_UPDATE_CACHE")
    if override:
        return Path(override)
    return Path.home() / ".claude" / "forge-update-check.json"


def _read_cache() -> dict:
    try:
        loaded = json.loads(cache_file().read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_cache(latest: str) -> None:
    try:
        path = cache_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"checked_at": int(time.time()), "latest": latest}), encoding="utf-8"
        )
    except OSError:
        pass  # a cache that cannot be written is a slower check, not a failure


# --------------------------------------------------------------------------
# asking
# --------------------------------------------------------------------------


def fetch_latest(owner: str, repo: str, timeout: float = TIMEOUT) -> str:
    """The version on the repository's default branch, or "".

    Asked through the contents API rather than a raw URL because that follows
    the default branch on its own. This repository's default is `merge`, not
    `main`, and a hard-coded branch name is exactly the kind of assumption that
    was already wrong once this week.
    """
    if not owner or not repo:
        return ""

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/.claude-plugin/plugin.json"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github.raw+json",
            "User-Agent": "forge-mentor-update-check",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            if response.status != 200:
                return ""
            body = response.read(64_000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return ""

    try:
        manifest = json.loads(body)
    except ValueError:
        return ""
    if not isinstance(manifest, dict):
        return ""

    version = str(manifest.get("version", "")).strip()
    # The only value that crosses this boundary, and it has to look like a
    # version to do it.
    return version if _VERSION.match(version) else ""


def disabled() -> bool:
    return bool(os.environ.get("FORGE_NO_UPDATE_CHECK"))


def check(plugin_root: Path, *, force: bool = False) -> Update | None:
    """Is there a newer version? None means no, or do not know, or not now."""
    if disabled():
        return None

    installed = installed_version(plugin_root)
    if not installed:
        return None

    owner, repo, url = repository_of(plugin_root)
    if not owner:
        return None

    cached = _read_cache()
    fresh = (time.time() - float(cached.get("checked_at", 0))) < CHECK_EVERY
    if fresh and not force:
        latest = str(cached.get("latest", ""))
    else:
        latest = fetch_latest(owner, repo)
        if latest:
            _write_cache(latest)

    if latest and is_newer(latest, installed):
        return Update(installed=installed, latest=latest, repository=url)
    return None


# --------------------------------------------------------------------------
# saying so
# --------------------------------------------------------------------------


# The command that actually exists. `claude plugin update --help` says it in
# its own words — "Update a plugin to the latest version (restart required to
# apply)" — which is also where the restart line below comes from rather than
# from a guess.
UPDATE_COMMAND = "claude plugin update forge@forge-marketplace"


def notice(update: Update) -> str:
    """One frame, three lines, and the command to run.

    Framed like everything else (decision 035) so it reads as Forge speaking,
    and short because nobody has ever wanted a longer update notice.
    """
    import forge_ui as ui

    return ui.note(
        "An update is available",
        [
            f"You have {update.installed}. {update.latest} is out.",
            "Your decisions and notes are untouched — they live in your project, "
            "not in the plugin.",
        ],
        symbol=ui.COST,
    ) + ui.action(
        UPDATE_COMMAND,
        hint="then restart Claude Code — hooks and the engine register at startup, "
        "so a reload is not enough",
        kind="fix",
    )


def report(plugin_root: Path, *, force: bool = False) -> str:
    """The notice, or nothing at all. Nothing is the common case."""
    found = check(plugin_root, force=force)
    return notice(found) if found else ""


# Prompts that start real work. A stale plugin is harmless while someone is
# reading; it is expensive the moment it starts writing state into a project,
# because the questions, the gates and the file layout are all version-shaped.
STARTING = ("forge:start", "forge:status", "forge:mode", "forge:update")

# How someone gets past it. There is always a way past — decision 004, and
# challenge finding H1: a gate with no exit is a gate that gets ripped out.
OVERRIDE = ("anyway", "skip the update", "ignore the update")


def gate(prompt: str, plugin_root: Path) -> str:
    """Should this prompt be held back, and what should the user be told?

    Returns "" to let it through, which is nearly always.

    **Why a hook and not a line in `start.md`.** That line already exists, and
    rule R13 is what it is: an instruction the model can skip is advice. Setting
    a project up on a stale plugin is not a small waste — `/forge:start` writes
    the notes layout, asks the fixed question sequence and records decisions
    against it, all of which are shaped by the version doing the writing. Doing
    that twice is the whole afternoon this has already cost.
    """
    text = (prompt or "").lower()
    if not any(name in text for name in STARTING):
        return ""
    if any(word in text for word in OVERRIDE):
        return ""

    found = check(plugin_root)
    if found is None:
        return ""

    return (
        f"Forge {found.installed} is running, and {found.latest} is out.\n\n"
        f"    {UPDATE_COMMAND}\n\n"
        "Then restart Claude Code — hooks and the engine register at startup, so a "
        "reload keeps the old ones running.\n\n"
        "Starting a project on the older build is worth avoiding: /forge:start writes "
        "the notes layout, asks the fixed question sequence and records decisions "
        "against it, and all three are shaped by the version doing the writing.\n\n"
        "Your decisions are safe either way — they live in the project, not the plugin.\n"
        "To carry on regardless, say it again with \"anyway\"."
    )


def _plugin_root() -> Path:
    """Where this copy of Forge lives.

    `CLAUDE_PLUGIN_ROOT` when Claude Code sets it, the parent of this file
    otherwise — so the check works the same run from a clone as installed.
    """
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    return Path(root) if root else Path(__file__).resolve().parent.parent


def _gate_mode() -> None:
    """UserPromptSubmit: hold `/forge:start` back when the plugin is stale.

    Fails open on absolutely everything. This one sits in front of every prompt
    the user types, so a bug here does not cost a turn or a session — it costs
    the ability to say anything at all.
    """
    import sys

    try:
        payload = json.load(sys.stdin)
        if payload.get("hook_event_name") != "UserPromptSubmit":
            print(json.dumps({}))
            return

        reason = gate(str(payload.get("prompt", "")), _plugin_root())
    except Exception:
        reason = ""

    print(json.dumps({"decision": "block", "reason": reason} if reason else {}))


def main() -> None:
    """Three shapes of the same answer, chosen by how it was invoked.

    `--gate` speaks the UserPromptSubmit protocol and can hold a prompt back;
    `--hook` speaks SessionStart and only adds context; bare prints the block
    for a terminal. All three say nothing when there is nothing to say, which
    is most days.
    """
    import sys

    if "--gate" in sys.argv:
        _gate_mode()
        return

    hook_mode = "--hook" in sys.argv
    try:
        text = report(_plugin_root(), force="--force" in sys.argv)
    except Exception:
        # An update check is the least important thing in the session and must
        # never be the reason one fails to start.
        text = ""

    if not hook_mode:
        if text:
            print(text)
        return

    if not text:
        print(json.dumps({}))
        return

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        "Forge is out of date. Show the user this block verbatim, "
                        "before anything else, and add nothing around it:\n\n" + text
                    ),
                }
            }
        )
    )


if __name__ == "__main__":  # pragma: no cover - CLI surface
    main()
