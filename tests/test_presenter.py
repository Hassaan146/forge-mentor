"""Tests for the hook that gates speech.

The governor gates writes, which are a file path a hook can see. Most of what
Forge does is talk, and nothing gated that — so rules R10 and R12 held exactly
as long as a model felt like following them, which on a real run was not long.

Two things matter here and they pull against each other: it has to catch an
unframed question, and it must never wedge a session. Every test below is one
or the other.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import forge_state as fs

PRESENTER = Path(__file__).resolve().parents[1] / "scripts" / "presenter.py"


def run(payload: dict) -> dict:
    """Invoke the hook the way Claude Code does, and read its answer."""
    done = subprocess.run(
        [sys.executable, str(PRESENTER)],
        input=json.dumps(payload),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout or "{}")


def blocked(answer: dict) -> bool:
    return answer.get("decision") == "block"


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    fs.init(tmp_path)
    return tmp_path


def transcript(project: Path, text: str) -> str:
    """A transcript whose last assistant turn said `text`."""
    path = project / "transcript.jsonl"
    path.write_text(
        json.dumps({"type": "user", "message": {"content": "go on"}})
        + "\n"
        + json.dumps(
            {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}
        )
        + "\n",
        encoding="utf-8",
    )
    return str(path)


def stop(project: Path, text: str, **extra) -> dict:
    return run(
        {
            "hook_event_name": "Stop",
            "cwd": str(project),
            "transcript_path": transcript(project, text),
            **extra,
        }
    )


def ask(project: Path) -> None:
    fs.ask(project / fs.FORGE_DIR, "How should people log in?")


# --------------------------------------------------------------------------
# what it catches
# --------------------------------------------------------------------------


def test_an_open_question_asked_as_prose_is_refused(project: Path) -> None:
    """The failure, exactly as it happened.

    Three paragraphs, no frame, and nothing anywhere could tell the difference
    between Forge asking and the assistant chatting.
    """
    ask(project)
    answer = stop(project, "So, how do you want people to log in? Let me know.")

    assert blocked(answer)
    assert "asked as prose" in answer["reason"]
    assert "render_decision" in answer["reason"], "and it names the tool to use"


def test_a_framed_question_passes(project: Path) -> None:
    ask(project)
    framed = "\n".join(
        [
            "  ┌─ ⚒ FORGE · DECISION 001 ──────┐",
            "  │  How should people log in?    │",
            "  └───────────────────────────────┘",
        ]
    )
    assert not blocked(stop(project, framed))


def test_the_double_frame_counts_too(project: Path) -> None:
    """An action frame is Forge speaking in its own shape as much as a box is."""
    ask(project)
    action = "  ╔═ → YOUR TURN ═══╗\n  ║  A, B, or C?    ║\n  ╚═════════════════╝"
    assert not blocked(stop(project, action))


def test_a_frame_buried_in_prose_is_still_refused(project: Path) -> None:
    """Rule R10 is about the wall of text, not about whether a box exists.

    A block with ten paragraphs around it is the same failure wearing a frame.
    """
    ask(project)
    wall = "\n".join([f"Some explanation, line {n}." for n in range(1, 12)])
    answer = stop(project, wall + "\n  ┌──┐\n  │x │\n  └──┘")

    assert blocked(answer)
    assert "loose prose" in answer["reason"]


def test_a_short_lead_in_is_allowed(project: Path) -> None:
    """One line before the block is a sentence, not a wall."""
    ask(project)
    assert not blocked(stop(project, "Here is the next one.\n  ┌──┐\n  │x │\n  └──┘"))


# --------------------------------------------------------------------------
# what it must never do
# --------------------------------------------------------------------------


def test_nothing_open_means_nothing_to_frame(project: Path) -> None:
    """Most turns are not questions. It has no opinion about those."""
    assert not blocked(stop(project, "I have written the file and the tests pass."))


def test_a_project_without_forge_is_left_alone(tmp_path: Path) -> None:
    """Every other project stays plain Claude Code."""
    answer = run(
        {
            "hook_event_name": "Stop",
            "cwd": str(tmp_path),
            "transcript_path": str(tmp_path / "nope.jsonl"),
        }
    )
    assert not blocked(answer)


def test_it_never_asks_twice_for_the_same_turn(project: Path) -> None:
    """`stop_hook_active` is absolute.

    A Stop hook that can block the response to its own block does not cost a
    turn, it ends the session.
    """
    ask(project)
    answer = stop(project, "still no frame here", stop_hook_active=True)
    assert not blocked(answer)


def test_an_unreadable_transcript_allows(project: Path) -> None:
    ask(project)
    answer = run(
        {
            "hook_event_name": "Stop",
            "cwd": str(project),
            "transcript_path": str(project / "does-not-exist.jsonl"),
        }
    )
    assert not blocked(answer)


def test_a_transcript_of_junk_allows(project: Path) -> None:
    ask(project)
    path = project / "junk.jsonl"
    path.write_text("not json\n{\"type\": \"assistant\"}\n", encoding="utf-8")

    answer = run(
        {"hook_event_name": "Stop", "cwd": str(project), "transcript_path": str(path)}
    )
    assert not blocked(answer)


def test_malformed_input_allows(project: Path) -> None:
    done = subprocess.run(
        [sys.executable, str(PRESENTER)],
        input="not json at all",
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    assert done.returncode == 0
    assert json.loads(done.stdout or "{}").get("decision") != "block"


def test_another_hook_event_is_ignored(project: Path) -> None:
    ask(project)
    answer = run(
        {
            "hook_event_name": "PreToolUse",
            "cwd": str(project),
            "transcript_path": transcript(project, "no frame"),
        }
    )
    assert not blocked(answer)


def test_a_turn_that_only_called_tools_is_not_treated_as_speech(project: Path) -> None:
    """An assistant entry carrying tool calls and no text said nothing.

    Judging it as an unframed answer would block a turn that was still working.
    """
    ask(project)
    path = project / "tools.jsonl"
    path.write_text(
        json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "  ┌──┐\n  │x │\n  └──┘"}]},
            }
        )
        + "\n"
        + json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "tool_use", "name": "Read", "input": {}}]},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    answer = run(
        {"hook_event_name": "Stop", "cwd": str(project), "transcript_path": str(path)}
    )
    assert not blocked(answer), "it looked back to the turn that actually spoke"
