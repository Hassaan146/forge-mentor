"""Tests for the update check.

The installed plugin lagged the repository for four sessions running, and every
one of them opened by debugging the wrong build — rules that were fixed still
firing, questions that had been reordered still coming out in the old order,
colours that had shipped still absent. Nothing on screen ever said the copy on
disk was two weeks behind.

The check itself is one line of text. Nearly every test here is about the ways
it must stay out of the way: no network, a proxy, a rate limit, junk in the
response, a machine that has never had a cache file.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import forge_update as up


@pytest.fixture()
def plugin(tmp_path: Path) -> Path:
    """A plugin root that looks like an installed copy."""
    manifest = tmp_path / ".claude-plugin"
    manifest.mkdir(parents=True)
    (manifest / "plugin.json").write_text(
        json.dumps(
            {
                "name": "forge",
                "version": "1.0.0",
                "repository": "https://github.com/Hassaan146/forge-mentor",
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Never touch the real one — these tests must not affect a real session.

    Redirected through the env var the function itself honours, rather than by
    replacing the function. Patching it out would mean the real one is never
    the thing under test, and where the cache lives is exactly what one of
    these tests is about.
    """
    path = tmp_path / "cache" / "forge-update-check.json"
    monkeypatch.setenv("FORGE_UPDATE_CACHE", str(path))
    monkeypatch.delenv("FORGE_NO_UPDATE_CHECK", raising=False)
    return path


def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a, **_k):
        raise OSError("no network")

    monkeypatch.setattr(up.urllib.request, "urlopen", refuse)


def answers(monkeypatch: pytest.MonkeyPatch, version: str) -> None:
    monkeypatch.setattr(up, "fetch_latest", lambda *a, **k: version)


# --------------------------------------------------------------------------
# comparing versions
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "latest,installed,expected",
    [
        ("1.1.0", "1.0.0", True),
        ("1.0.0", "1.0.0", False),
        ("1.0.0", "1.1.0", False),
        # The one that quietly stops every update notice from ever appearing
        # again, because "1.10.0" < "1.9.0" as text.
        ("1.10.0", "1.9.0", True),
        ("1.1", "1.0.9", True),
        ("2.0", "1.9.9", True),
        ("", "1.0.0", False),
        ("latest", "1.0.0", False),
        ("1.0.0", "", False),
    ],
)
def test_versions_compare_as_numbers_not_as_text(latest, installed, expected) -> None:
    assert up.is_newer(latest, installed) is expected


def test_the_repository_comes_from_the_manifest(plugin: Path) -> None:
    """A fork must check itself, not report that it is behind the original."""
    owner, repo, url = up.repository_of(plugin)
    assert (owner, repo) == ("Hassaan146", "forge-mentor")
    assert url == "https://github.com/Hassaan146/forge-mentor"


def test_a_manifest_without_a_repository_checks_nothing(tmp_path: Path) -> None:
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "plugin.json").write_text('{"version": "1.0.0"}', "utf-8")
    assert up.repository_of(tmp_path) == ("", "", "")
    assert up.check(tmp_path) is None


# --------------------------------------------------------------------------
# saying so, once
# --------------------------------------------------------------------------


def test_a_newer_version_is_reported(plugin: Path, monkeypatch) -> None:
    answers(monkeypatch, "1.1.0")
    found = up.check(plugin)

    assert found is not None
    assert (found.installed, found.latest) == ("1.0.0", "1.1.0")


def test_the_same_version_says_nothing(plugin: Path, monkeypatch) -> None:
    answers(monkeypatch, "1.0.0")
    assert up.check(plugin) is None


def test_the_notice_says_what_to_run_and_that_notes_are_safe(plugin: Path, monkeypatch) -> None:
    """The two things anybody wants to know before updating anything."""
    answers(monkeypatch, "1.1.0")
    text = up.report(plugin)

    assert "1.0.0" in text and "1.1.0" in text
    assert "claude plugin update" in text, "and it is a command that exists"
    assert "restart" in text.lower()
    assert "untouched" in text, "their decisions live in the project, not the plugin"


def test_the_notice_is_framed_like_everything_else(plugin: Path, monkeypatch) -> None:
    answers(monkeypatch, "1.1.0")
    text = up.report(plugin)
    assert any(char in text for char in "┌│└"), "decision 035: every block is framed"


# --------------------------------------------------------------------------
# staying out of the way
# --------------------------------------------------------------------------


def test_no_network_is_silence_not_an_error(plugin: Path, monkeypatch) -> None:
    offline(monkeypatch)
    assert up.check(plugin) is None
    assert up.report(plugin) == ""


def test_junk_in_the_response_is_treated_as_no_update(plugin: Path, monkeypatch) -> None:
    """Nothing from the network reaches a screen except a version.

    Remote text on the user's screen is remote text in a model's context
    (challenge finding C3), and a release note is not worth that door.
    """

    class Response:
        status = 200

        def read(self, _n=None):
            return b'{"version": "<script>alert(1)</script>"}'

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(up.urllib.request, "urlopen", lambda *a, **k: Response())
    assert up.fetch_latest("o", "r") == ""


def test_a_non_200_is_treated_as_no_answer(plugin: Path, monkeypatch) -> None:
    class Response:
        status = 403  # rate limited, which is the common one

        def read(self, _n=None):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(up.urllib.request, "urlopen", lambda *a, **k: Response())
    assert up.fetch_latest("o", "r") == ""


def test_the_switch_turns_it_off_entirely(plugin: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGE_NO_UPDATE_CHECK", "1")

    def never(*_a, **_k):
        raise AssertionError("it asked the network anyway")

    monkeypatch.setattr(up, "fetch_latest", never)
    assert up.check(plugin) is None


def test_it_asks_at_most_once_a_day(plugin: Path, monkeypatch, isolated_cache: Path) -> None:
    """A check that runs every session is a check that is in the way."""
    calls = []

    def counted(*_a, **_k):
        calls.append(1)
        return "1.1.0"

    monkeypatch.setattr(up, "fetch_latest", counted)

    assert up.check(plugin) is not None
    assert up.check(plugin) is not None
    assert len(calls) == 1, "the second one came from the cache"


def test_a_stale_cache_is_asked_again(plugin: Path, monkeypatch, isolated_cache: Path) -> None:
    isolated_cache.parent.mkdir(parents=True, exist_ok=True)
    isolated_cache.write_text(
        json.dumps({"checked_at": int(time.time()) - up.CHECK_EVERY - 60, "latest": "1.0.0"}),
        encoding="utf-8",
    )
    answers(monkeypatch, "1.1.0")

    assert up.check(plugin) is not None, "yesterday's answer is not this morning's"


def test_a_corrupt_cache_does_not_stop_the_check(plugin: Path, monkeypatch, isolated_cache) -> None:
    isolated_cache.parent.mkdir(parents=True, exist_ok=True)
    isolated_cache.write_text("not json", encoding="utf-8")
    answers(monkeypatch, "1.1.0")

    assert up.check(plugin) is not None


def test_the_cache_lives_outside_the_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inside it, the reinstall it exists to make unnecessary would delete it."""
    monkeypatch.delenv("FORGE_UPDATE_CACHE", raising=False)
    where = up.cache_file()

    assert where.parent.name == ".claude"
    assert "plugins" not in str(where), "not somewhere a reinstall wipes"


def test_a_missing_manifest_is_silence(tmp_path: Path) -> None:
    assert up.installed_version(tmp_path) == ""
    assert up.check(tmp_path) is None


# --------------------------------------------------------------------------
# holding /forge:start back — the gate the user asked for
# --------------------------------------------------------------------------


def test_starting_a_project_on_a_stale_plugin_is_held_back(plugin: Path, monkeypatch) -> None:
    """`/forge:start` writes the notes layout and the question sequence.

    Both are shaped by the version doing the writing, so doing it twice is the
    afternoon this has already cost.
    """
    answers(monkeypatch, "1.1.0")
    held = up.gate("/forge:start", plugin)

    assert held
    assert up.UPDATE_COMMAND in held
    assert "restart" in held.lower()
    assert "anyway" in held, "and there is always a way past"


def test_the_command_it_hands_over_is_one_that_exists(plugin: Path) -> None:
    """`claude plugin update` is real; a slash command was a guess.

    Its own help says "(restart required to apply)", which is where the restart
    line comes from rather than from an assumption.
    """
    assert up.UPDATE_COMMAND.startswith("claude plugin update ")
    assert "forge@forge-marketplace" in up.UPDATE_COMMAND


def test_a_current_plugin_holds_nothing_back(plugin: Path, monkeypatch) -> None:
    answers(monkeypatch, "1.0.0")
    assert up.gate("/forge:start", plugin) == ""


@pytest.mark.parametrize(
    "prompt",
    ["what does this project do?", "fix the login bug", "", "forge is a good name"],
)
def test_ordinary_prompts_are_never_touched(plugin: Path, monkeypatch, prompt) -> None:
    """It sits in front of every prompt the user types. Nearly all of them pass."""
    answers(monkeypatch, "1.1.0")
    assert up.gate(prompt, plugin) == ""


@pytest.mark.parametrize("prompt", ["/forge:start", "/forge:status", "run /forge:mode auto"])
def test_every_command_that_starts_work_is_covered(plugin: Path, monkeypatch, prompt) -> None:
    answers(monkeypatch, "1.1.0")
    assert up.gate(prompt, plugin) != ""


@pytest.mark.parametrize("prompt", ["/forge:start anyway", "/forge:start, skip the update"])
def test_saying_anyway_gets_past_it(plugin: Path, monkeypatch, prompt) -> None:
    """Decision 004 and challenge finding H1: a gate with no exit gets ripped out."""
    answers(monkeypatch, "1.1.0")
    assert up.gate(prompt, plugin) == ""


def test_no_network_never_holds_a_prompt_back(plugin: Path, monkeypatch) -> None:
    """This runs in front of every prompt. It cannot be the reason one fails."""
    offline(monkeypatch)
    assert up.gate("/forge:start", plugin) == ""


def test_the_switch_turns_the_gate_off_too(plugin: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGE_NO_UPDATE_CHECK", "1")
    answers(monkeypatch, "1.1.0")
    assert up.gate("/forge:start", plugin) == ""


# --------------------------------------------------------------------------
# downloaded, but not yet running
# --------------------------------------------------------------------------


def cache_with(tmp_path: Path, *versions: str, running: str) -> Path:
    """A plugin cache holding several versions, with one of them running."""
    for version in versions:
        (tmp_path / version / ".claude-plugin").mkdir(parents=True, exist_ok=True)
        (tmp_path / version / ".claude-plugin" / "plugin.json").write_text(
            json.dumps(
                {
                    "name": "forge",
                    "version": version,
                    "repository": "https://github.com/Hassaan146/forge-mentor",
                }
            ),
            encoding="utf-8",
        )
    return tmp_path / running


def test_a_newer_version_on_disk_is_a_pending_restart(tmp_path: Path) -> None:
    """The state that cost four sessions.

    `claude plugin update` writes the new version into the cache and changes
    nothing about the running process. The update succeeds, the user carries on,
    and every symptom they were updating to fix is still in front of them.
    """
    root = cache_with(tmp_path, "1.2.1", "1.3.0", "1.4.0", running="1.3.0")
    waiting = up.pending_restart(root)

    assert waiting is not None
    assert (waiting.installed, waiting.latest) == ("1.3.0", "1.4.0")


def test_running_the_newest_downloaded_version_is_not(tmp_path: Path) -> None:
    root = cache_with(tmp_path, "1.2.1", "1.3.0", "1.4.0", running="1.4.0")
    assert up.pending_restart(root) is None


def test_the_restart_notice_says_it_costs_nothing(tmp_path: Path) -> None:
    """The reason people put a restart off is not knowing what it will lose."""
    root = cache_with(tmp_path, "1.3.0", "1.4.0", running="1.3.0")
    text = up.report(root)

    assert "1.3.0" in text and "1.4.0" in text
    assert "Nothing is lost" in text
    assert "startup" in text, "and why updating alone did not work"
    assert "/forge:status" in text, "and how to pick the thread back up"


def test_a_pending_restart_outranks_the_version_check(tmp_path: Path, monkeypatch) -> None:
    """Telling them to download what they already have is worse than silence.

    They run the update command, it reports success, and nothing changes.
    """
    answers(monkeypatch, "9.9.9")
    root = cache_with(tmp_path, "1.3.0", "1.4.0", running="1.3.0")

    assert "downloaded" in up.report(root)
    assert "9.9.9" not in up.report(root)


def test_a_pending_restart_needs_no_network(tmp_path: Path, monkeypatch) -> None:
    """So it can run on every session and every command without costing one."""
    offline(monkeypatch)
    root = cache_with(tmp_path, "1.3.0", "1.4.0", running="1.3.0")

    assert up.pending_restart(root) is not None
    assert up.report(root) != ""


def test_a_clone_is_not_a_version_directory(tmp_path: Path) -> None:
    """Run from a checkout there are no sibling versions, and no restart to ask for."""
    root = tmp_path / "forge-mentor"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text('{"version": "1.4.0"}', "utf-8")

    assert up.pending_restart(root) is None


def test_the_gate_holds_forge_start_on_a_pending_restart(tmp_path: Path) -> None:
    """It is the more urgent of the two: the update is done, one restart is left."""
    root = cache_with(tmp_path, "1.3.0", "1.4.0", running="1.3.0")
    held = up.gate("/forge:start", root)

    assert "already downloaded" in held
    assert "Quit Claude Code" in held
    assert "anyway" in held
