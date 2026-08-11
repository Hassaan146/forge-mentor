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
    assert "in your reply" in answer["reason"], "and it names where the block goes"
    assert "collapsed" in answer["reason"], "and why a shell command will not do"

    # Short, because Claude Code shows a Stop hook's reason on screen. A
    # fourteen-line correction with a JSON example in it arrived looking like
    # the plugin had crashed, in the middle of a user's first run.
    assert len(answer["reason"].splitlines()) <= 2


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
    assert "lines of prose" in answer["reason"]
    assert len(answer["reason"].splitlines()) <= 2


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


def test_an_unrelated_command_does_not_count_as_a_frame(project: Path) -> None:
    """Otherwise any turn that ran anything would pass."""
    ask(project)
    path = project / "other.jsonl"
    path.write_text(
        json.dumps({"type": "user", "message": {"content": "go on"}})
        + "\n"
        + json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Bash", "input": {"command": "git status"}}
                    ]
                },
            }
        )
        + "\n"
        + json.dumps(
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "so, which?"}]}}
        )
        + "\n",
        encoding="utf-8",
    )

    answer = run(
        {"hook_event_name": "Stop", "cwd": str(project), "transcript_path": str(path)}
    )
    assert blocked(answer)


def test_a_paused_project_gets_no_opinion_about_its_answers(project: Path) -> None:
    """`/forge:stop` means stop, including the part that shapes replies."""
    ask(project)
    (project / fs.FORGE_DIR / fs.PAUSED).write_text("paused\n", encoding="utf-8")

    assert not blocked(stop(project, "no frame here at all"))


def test_a_real_user_message_still_ends_the_search(project: Path) -> None:
    """Otherwise a render from three turns ago would excuse this one forever."""
    ask(project)
    path = project / "older.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "name": "Bash",
                                    "input": {"command": 'forge_ui.py render <<JSON'},
                                }
                            ]
                        },
                    }
                ),
                json.dumps({"type": "user", "message": {"content": "next question please"}}),
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {"content": [{"type": "text", "text": "so which is it?"}]},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    answer = run(
        {"hook_event_name": "Stop", "cwd": str(project), "transcript_path": str(path)}
    )
    assert blocked(answer), "that render belonged to the previous turn"


def test_the_markdown_presentation_counts_as_framed(project: Path) -> None:
    """It exists because the box could not be coloured, so it must not be refused.

    Inside Claude Code the escape codes never arrive, so the block is handed to
    the client as markdown for the client to colour. None of those lines carry a
    frame character.
    """
    ask(project)
    block = "\n".join(
        [
            "### ⚒ FORGE · DECISION 001",
            "",
            "**What's the idea?**",
            "",
            "💡 **What this means**",
            "> Say it the way you would to a friend.",
            "",
            "---",
            "",
            "### → YOUR TURN",
            "",
            "**Your call**",
        ]
    )
    assert not blocked(stop(project, block))


def test_prose_is_counted_before_the_block_not_across_it(project: Path) -> None:
    """The rule is about the lead-in, not the block's own body.

    Counting every line without a frame character refused every markdown
    question it was ever given, because in that presentation there are none.
    """
    ask(project)
    body = "\n".join([f"line {n} of the block body" for n in range(1, 15)])

    assert not blocked(stop(project, f"### ⚒ FORGE · DECISION 001\n{body}"))

    wall = "\n".join([f"Some explanation, line {n}." for n in range(1, 12)])
    assert blocked(stop(project, f"{wall}\n### ⚒ FORGE · DECISION 001\n{body}"))


def test_a_block_printed_by_a_shell_command_does_not_count(project: Path) -> None:
    """This is the whole bug, as a test.

    Claude Code collapses tool output into "ran 2 shell commands", so a block
    printed that way never reaches the screen. Accepting it here put a bare
    prose line in front of a user as question 3 of their real run, while the
    block sat invisible behind a summary line.
    """
    ask(project)
    path = project / "via-command.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"type": "user", "message": {"content": "/forge:start"}}),
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "name": "Bash",
                                    "input": {"command": 'forge_ui.py render <<JSON'},
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "user",
                        "message": {"content": [{"type": "tool_result", "content": "block"}]},
                    }
                ),
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "text", "text": "Question 3 of ~6. It's open."}
                            ]
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    answer = run(
        {"hook_event_name": "Stop", "cwd": str(project), "transcript_path": str(path)}
    )
    assert blocked(answer), "the user saw one line of prose, not a block"


def test_the_presenter_accepts_what_the_render_tools_actually_produce(project: Path) -> None:
    """The cross-check that caught this before it shipped.

    The hook looked for a symbol on a markdown heading. The block is drawn as a
    table on this surface, which has no heading, so it would have refused every
    question the tools produced. Written against the real output of each tool
    rather than against a sample of what it is assumed to look like.
    """
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
    import forge_server as srv

    unwrap = lambda tool: getattr(tool, "fn", tool)  # noqa: E731
    ask(project)

    blocks = {
        "foundation_question": unwrap(srv.foundation_question)(str(project))["block"],
        "render_decision": unwrap(srv.render_decision)(
            "t", choices=[["A", "one", "x"]]
        )["block"],
        "render_note": unwrap(srv.render_note)("h", ["one"])["block"],
        "render_action": unwrap(srv.render_action)("go?", kind="confirm")["block"],
        "color_legend": unwrap(srv.color_legend)()["block"],
    }

    for name, block in blocks.items():
        assert not blocked(stop(project, block)), f"{name} would have been refused"


def test_a_table_row_carrying_a_symbol_is_the_block(project: Path) -> None:
    """The third shape. A frame, a heading, or a table row, and it must know all."""
    ask(project)
    table = "\n".join(["| ⚒ **FORGE** · **DECISION 001** |", "| :--- |", "| **What's the idea?** |"])
    assert not blocked(stop(project, table))

    plain_table = "\n".join(["| a | b |", "|---|---|", "| 1 | 2 |"])
    assert blocked(stop(project, plain_table)), "any old table is not a Forge block"
