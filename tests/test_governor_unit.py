"""Direct tests for the governor's decision logic.

`test_state.py` drives the governor as a real subprocess, which proves the
contract with Claude Code end to end but hides the branches from coverage.
These tests call the same code in-process so every path is measured.

Both layers are kept: the subprocess tests prove the wire format, these prove
the reasoning.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

import forge_state as fs
import governor


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    fs.init(tmp_path)
    return tmp_path


def invoke(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, payload: dict) -> dict:
    """Run governor.main() with a payload on stdin and capture its answer."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    with pytest.raises(SystemExit) as exit_info:
        governor.main()
    assert exit_info.value.code == 0, "the governor must always exit 0"
    return json.loads(capsys.readouterr().out or "{}")


def write_payload(cwd: Path, tool: str = "Write", target: str | None = None) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "cwd": str(cwd),
        "tool_input": {"file_path": target or str(cwd / "app.py")},
    }


def is_deny(response: dict) -> bool:
    out = response.get("hookSpecificOutput")
    return bool(out) and out.get("permissionDecision") == "deny"


def reason(response: dict) -> str:
    return response["hookSpecificOutput"]["permissionDecisionReason"]


# --------------------------------------------------------------------------
# the blocking rule — decision 004
# --------------------------------------------------------------------------


def test_open_question_blocks_and_names_it(project, monkeypatch, capsys) -> None:
    fs.ask(project / fs.FORGE_DIR, "rate limiting")
    response = invoke(monkeypatch, capsys, write_payload(project))
    assert is_deny(response)
    assert "rate limiting" in reason(response)
    assert "write it anyway" in reason(response)


def complete_foundation(forge) -> None:
    """Answer the six foundation questions.

    The governor blocks until they are all recorded, not just between asking
    and answering — a fresh project used to allow a write because nothing was
    open, which let Forge write a whole file before a single decision existed.
    Anything testing "a write is allowed" has to get past that first.
    """
    import forge_foundation as ff

    for question in ff.FOUNDATION:
        asked = fs.ask(forge, question.question)
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")


def test_answered_question_allows(project, monkeypatch, capsys) -> None:
    forge = project / fs.FORGE_DIR
    fs.ask(forge, "rate limiting")
    fs.answer(forge, 1, "per-IP, 60/min")
    complete_foundation(forge)
    assert not is_deny(invoke(monkeypatch, capsys, write_payload(project)))


def test_override_allows(project, monkeypatch, capsys) -> None:
    forge = project / fs.FORGE_DIR
    fs.ask(forge, "rate limiting")
    progress = fs.Progress.read(forge)
    progress.override_active = True
    progress.write(forge)
    assert not is_deny(invoke(monkeypatch, capsys, write_payload(project)))


# --------------------------------------------------------------------------
# staying out of the way — decision 014
# --------------------------------------------------------------------------


@pytest.mark.parametrize("tool", ["Read", "Grep", "Glob", "Bash", "WebFetch"])
def test_non_write_tools_are_never_blocked(project, monkeypatch, capsys, tool) -> None:
    fs.ask(project / fs.FORGE_DIR, "rate limiting")
    assert not is_deny(invoke(monkeypatch, capsys, write_payload(project, tool=tool)))


@pytest.mark.parametrize("tool", ["Write", "Edit", "NotebookEdit"])
def test_every_write_tool_is_covered(project, monkeypatch, capsys, tool) -> None:
    fs.ask(project / fs.FORGE_DIR, "rate limiting")
    assert is_deny(invoke(monkeypatch, capsys, write_payload(project, tool=tool)))


def test_other_hook_events_are_ignored(project, monkeypatch, capsys) -> None:
    fs.ask(project / fs.FORGE_DIR, "rate limiting")
    payload = write_payload(project)
    payload["hook_event_name"] = "PostToolUse"
    assert not is_deny(invoke(monkeypatch, capsys, payload))


def test_project_without_forge_is_untouched(tmp_path, monkeypatch, capsys) -> None:
    assert not is_deny(invoke(monkeypatch, capsys, write_payload(tmp_path)))


def test_forge_writing_its_own_notes_is_allowed(project, monkeypatch, capsys) -> None:
    fs.ask(project / fs.FORGE_DIR, "rate limiting")
    target = str(project / fs.FORGE_DIR / "decisions" / "002-next.md")
    assert not is_deny(invoke(monkeypatch, capsys, write_payload(project, target=target)))


def test_malformed_input_does_not_block(project, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("this is not json"))
    with pytest.raises(SystemExit) as exit_info:
        governor.main()
    assert exit_info.value.code == 0
    assert not is_deny(json.loads(capsys.readouterr().out or "{}"))


# --------------------------------------------------------------------------
# failing closed, with a way out — decision 004 + challenge finding H1
# --------------------------------------------------------------------------


def test_corrupt_notes_block_but_explain_the_repair(project, monkeypatch, capsys) -> None:
    fs.ask(project / fs.FORGE_DIR, "rate limiting")
    (project / fs.FORGE_DIR / "decisions" / "003-broken.md").write_text("no header", encoding="utf-8")

    response = invoke(monkeypatch, capsys, write_payload(project))
    assert is_deny(response)
    assert "cannot read" in reason(response).lower()
    assert "git checkout" in reason(response)


def test_deny_and_allow_emit_valid_wire_format(capsys) -> None:
    with pytest.raises(SystemExit):
        governor.deny("because")
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"

    with pytest.raises(SystemExit):
        governor.allow()
    assert json.loads(capsys.readouterr().out) == {}


# --------------------------------------------------------------------------
# Forge writing its own notes — path handling, not string matching
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target",
    [
        f"{fs.FORGE_DIR}/decisions/001-x.md",          # relative, no leading separator
        ".claude/forge/progress.md",              # relative, no leading separator
        "/abs/proj/.claude/forge/decisions/002.md",  # absolute posix
        r"C:\proj\.claude\forge\progress.md",    # windows separators
        ".claude/forge",                          # the folder itself
    ],
)
def test_forge_owned_paths_are_recognised(target: str) -> None:
    """A substring heuristic missed relative paths and blocked Forge's own writes."""
    assert governor.is_forge_owned(target) is True


@pytest.mark.parametrize(
    "target",
    ["app.py", "src/.forgery/x.md", "notforge/progress.md", "src/forge/app.py", ""],
)
def test_ordinary_paths_are_not_forge_owned(target: str) -> None:
    assert governor.is_forge_owned(target) is False


def test_relative_forge_write_is_allowed(project, monkeypatch, capsys) -> None:
    """End to end: the bug Sourcery caught would have blocked this."""
    fs.ask(project / fs.FORGE_DIR, "rate limiting")
    payload = write_payload(project, target=f"{fs.FORGE_DIR}/decisions/002-next.md")
    assert not is_deny(invoke(monkeypatch, capsys, payload))
