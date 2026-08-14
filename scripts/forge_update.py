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


# --------------------------------------------------------------------------
# downloaded, but not yet running
# --------------------------------------------------------------------------


def downloaded_versions(plugin_root: Path) -> list[str]:
    """Every version of Forge sitting in the plugin cache beside this one.

    The cache keeps one directory per version, named for it, so the siblings of
    the running copy are the whole set. Read from the filesystem rather than
    from the install record, because the record says what was installed and the
    directories say what is actually there.
    """
    try:
        siblings = [p.name for p in plugin_root.parent.iterdir() if p.is_dir()]
    except OSError:
        return []
    return sorted([name for name in siblings if _VERSION.match(name)], key=_as_numbers)


def pending_restart(plugin_root: Path) -> Update | None:
    """A newer Forge is on disk, and this session is still running the old one.

    **This is the state that cost four sessions.** `claude plugin update` puts
    the new version in the cache and changes nothing about the running process:
    hooks, the engine and the command table were all read at startup and keep
    pointing at the directory they were loaded from. So the update succeeds, the
    user carries on, and every symptom they were updating to fix is still there.

    Nothing about it needs the network, so unlike the version check this can run
    on every session and every Forge command without costing anything.
    """
    running = plugin_root.name
    if not _VERSION.match(running):
        return None  # running from a clone, not from the versioned cache

    available = downloaded_versions(plugin_root)
    newest = available[-1] if available else ""
    if newest and is_newer(newest, running):
        _, _, url = repository_of(plugin_root)
        return Update(installed=running, latest=newest, repository=url)
    return None


def resume_command(cwd: Path | None = None) -> str:
    """What to type after the restart, which is not the same command every time.

    `/forge:status` reads the notes and says which question is open. A project
    that has no notes yet has no open question and nothing for it to read, so
    telling someone who is *setting up* to run it sends them to an empty answer
    and leaves the setup they came for unstarted. There, the command to pick
    back up with is the one they were already running.
    """
    import forge_state as st

    root = Path(cwd) if cwd is not None else Path.cwd()
    try:
        started = (root / st.FORGE_DIR / st.PROGRESS).is_file()
    except OSError:
        started = False
    return "/forge:status" if started else "/forge:start"


def restart_notice(update: Update, *, resume: str | None = None) -> str:
    """What to do, and what it costs, which is nothing.

    No commands here on purpose. There is no command for this: the download is
    already done and what is left is closing a window. Offering one would send
    the user back to the update they have already run, which is the loop this
    whole notice exists to end.
    """
    import forge_ui as ui

    command = resume or resume_command()
    tail = (
        "it reads your notes and says which question is open"
        if command == "/forge:status"
        else "you have no notes yet, so this picks the setup up where it was"
    )
    body = [
        "",
        f"  {ui.DIM}A session reads its hooks and its engine once, at startup, so this{ui.NC}",
        f"  {ui.DIM}one keeps the old ones however many times you update.{ui.NC}",
        "",
        f"  {ui.YELLOW}{ui.BOLD}Quit Claude Code completely{ui.NC}",
        f"      {ui.DIM}the whole application. Not /clear, not a new tab.{ui.NC}",
        "",
        f"  {ui.YELLOW}{ui.BOLD}Open it again, then run{ui.NC}",
        f"      {ui.BOLD}{command}{ui.NC}",
        f"      {ui.DIM}{tail}{ui.NC}",
        "",
        f"  {ui.DIM}None of that has to happen now. Whatever you just ran carries on,{ui.NC}",
        f"  {ui.DIM}on this version, and the restart keeps until it suits you.{ui.NC}",
        "",
    ]
    body += ui._important_lines(
        ["Nothing is lost. Your decisions live in the project, not in the plugin."]
    )
    body.append("")

    title = (
        f"{ui.YELLOW}{ui.BOLD}{ui.COST} Forge {update.latest} is downloaded, "
        f"this session runs {update.installed}{ui.NC}"
    )
    return "\n" + ui.box(body, title=title, edge=ui.YELLOW) + "\n"


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
            "Your decisions and notes are untouched. They live in your project, "
            "not in the plugin.",
            "Nothing waits on it. What you just ran carries on, and the commands "
            "below keep until you want them.",
        ],
        symbol=ui.COST,
    ) + how_to_update()


# The pair, in order. The second reads the local catalogue and the first is what
# refreshes it, so running the second alone finds nothing and reports success:
# the loop that cost this project an afternoon.
UPDATE_COMMANDS = (
    "claude plugin marketplace update forge-marketplace",
    UPDATE_COMMAND,
)

# Inside a session it is **one** command, and that is not a shorter version of
# the terminal pair. Refreshing the marketplace downloads the new plugin with
# it: `/plugin marketplace update` reports "1 plugin bumped", and the bump is
# the download.
#
# There is no `/plugin update <name>`. Claude Code takes `/plugin` and opens the
# plugin browser, arguments and all, so a user told to run it lands in a list of
# 284 plugins wondering what went wrong. That was written here on the assumption
# that the slash commands mirror the CLI, which they do not, and it cost a
# round trip to find out. Anything in this file that a user is told to type is
# now something that has been watched running.
SLASH_COMMANDS = ("/plugin marketplace update forge-marketplace",)



def how_to_update() -> str:
    """Both surfaces, labelled, one command to a line.

    This was a paragraph with the commands inline in backticks, wrapped by the
    frame, and it read as prose rather than as something to run. A command the
    user has to extract from a sentence is a command they will mistype.
    """
    import forge_ui as ui

    here = bool(os.environ.get("CLAUDECODE"))
    rows: list[str] = [""]

    def block(title: str, commands: tuple[str, ...], current: bool) -> None:
        mark = f"  {ui.DIM}(you are here){ui.NC}" if current else ""
        ink = ui.YELLOW if current else ui.DIM
        rows.append(f"  {ink}{ui.BOLD}{title}{ui.NC}{mark}")
        rows.extend(f"      {ui.BOLD}{command}{ui.NC}" for command in commands)
        rows.append("")

    if here:
        block("Inside Claude Code, one command", SLASH_COMMANDS, True)
        rows.insert(
            len(rows) - 1,
            f"      {ui.DIM}refreshing the marketplace downloads the plugin with it{ui.NC}",
        )
        block("Or in a terminal, outside Claude Code", UPDATE_COMMANDS, False)
        rows.insert(
            len(rows) - 1,
            f"      {ui.DIM}two, in that order: the second reads what the first refreshes{ui.NC}",
        )
    else:
        block("In this terminal, both in this order", UPDATE_COMMANDS, True)
        rows.insert(
            len(rows) - 1,
            f"      {ui.DIM}the second reads the catalogue the first refreshes{ui.NC}",
        )
        block("Or inside Claude Code, one command", SLASH_COMMANDS, False)

    rows += [
        f"  {ui.DIM}There is no /plugin update. Claude Code reads /plugin as the{ui.NC}",
        f"  {ui.DIM}plugin browser and opens it, arguments and all.{ui.NC}",
        "",
    ]
    return "\n" + ui.box(rows, title=f"{ui.AMBER}{ui.BOLD}{ui.MARK} How to update{ui.NC}") + "\n"


def report(plugin_root: Path, *, force: bool = False) -> str:
    """The notice, or nothing at all. Nothing is the common case.

    A pending restart is checked first and wins. If a newer Forge is already on
    disk, telling the user to download it again is worse than saying nothing:
    they run the update command, it reports success, and every symptom stays
    exactly where it was.
    """
    waiting = pending_restart(plugin_root)
    if waiting is not None:
        return restart_notice(waiting)

    found = check(plugin_root, force=force)
    return notice(found) if found else ""


# **There was a gate here, and it deadlocked a real session.**
#
# A `UserPromptSubmit` hook held `/forge:start` back whenever a newer version
# sat in the plugin cache unloaded, on the reasoning that setting a project up
# on a stale build writes a notes layout and a question sequence shaped by the
# wrong version. The block named `/forge:status` as the way out. In an empty
# directory `/forge:status` has nothing to read, so it answered "this is not a
# Forge project, run /forge:start" — and the gate blocked that too. The user ran
# the pair four times before reporting it.
#
# The check itself was never the problem; refusing to start was. A stale build
# is worth a sentence, not a locked door, and `start.md` prints the notice
# before Step 1 and then carries on — the user gets the update command and the
# project they asked for in the same turn. Every notice in this file is now
# something the user reads on the way past.
#
# Nothing replaced it on purpose. Its one remaining job, saying the version is
# behind, is already done twice: once by the SessionStart hook and once by
# `start.md` itself. A third copy in front of every prompt was the noise.


def _plugin_root() -> Path:
    """Where this copy of Forge lives.

    `CLAUDE_PLUGIN_ROOT` when Claude Code sets it, the parent of this file
    otherwise — so the check works the same run from a clone as installed.
    """
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    return Path(root) if root else Path(__file__).resolve().parent.parent


def main() -> None:
    """Two shapes of the same answer, chosen by how it was invoked.

    `--hook` speaks SessionStart and only adds context; bare prints the block
    for a terminal. Both say nothing when there is nothing to say, which is most
    days, and neither can hold anything back — see the note above `report`.

    `--gate` is accepted and does nothing, so a hooks file left over from an
    earlier install prints an empty object rather than an error into a prompt.
    """
    import sys

    if "--gate" in sys.argv:
        print(json.dumps({}))
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
