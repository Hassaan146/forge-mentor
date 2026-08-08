"""Tests for the visual identity.

The interface is a shipped promise, not decoration: design rules R5, R9 and
R10 say Forge must look distinct, stay restrained, and never rely on colour
alone. These tests hold that promise to account.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

import forge_ui as ui

ANSI = re.compile(r"\033\[[0-9;]*m")


def plain(text: str) -> str:
    """The text as a terminal without colour would show it."""
    return ANSI.sub("", text)


# --------------------------------------------------------------------------
# colour is never the only signal — rule R9
# --------------------------------------------------------------------------


def test_blocked_still_reads_without_colour() -> None:
    out = plain(ui.blocked("rate limiting", "No decision recorded yet for:", ["decide first"]))
    assert ui.BLOCKED in out
    assert "FORGE STOPPED THIS" in out
    assert "rate limiting" in out


def test_recorded_still_reads_without_colour() -> None:
    out = plain(ui.recorded("B — a login service", ".claude/forge/decisions/007-x.md"))
    assert ui.RECORDED in out
    assert "DECIDED" in out


def test_recommendation_carries_a_symbol() -> None:
    assert ui.STAR in plain(ui.recommendation("B", "because"))


def test_only_four_symbols_ship() -> None:
    """Restraint is deliberate — a busy screen competes with the decision."""
    assert {ui.MARK, ui.BLOCKED, ui.RECORDED, ui.STAR} == {"⚒", "⛔", "✅", "★"}


# --------------------------------------------------------------------------
# boxes line up — rule R10
# --------------------------------------------------------------------------


@pytest.mark.parametrize("number", [None, 1, 7, 42, 999])
@pytest.mark.parametrize("title", ["Short?", "How should people log in to this system?"])
def test_the_heading_never_needs_width_arithmetic(number, title) -> None:
    """The frame this replaced could not be relied on.

    `⚒` is an emoji-presentation character: it renders two columns wide in most
    terminals while `len()` counts it as one, so the top rail came out a column
    longer than the bottom and the whole box looked broken. A rule needs no
    arithmetic against the heading, so it cannot disagree with itself.
    """
    out = plain(ui.question_box(title, "sub", number))
    rules = [ln for ln in out.splitlines() if set(ln.strip()) == {"─"}]

    assert rules, "there is a rule under the heading"
    for line in rules:
        assert len(line.strip()) == ui.WIDTH, "every rule is exactly one width"
    assert title in out


def test_progress_sits_with_the_heading_not_alone_at_the_bottom() -> None:
    """Rule R4 asks for it to be visible, not for it to be last."""
    out = plain(ui.question_box("Where is the data kept?", "", 3, done=2, total=5, stage="foundation"))
    first = out.strip().splitlines()[0]

    assert "DECISION 003" in first
    assert "2 of ~5" in first and "foundation" in first


def test_box_shows_the_decision_number() -> None:
    assert "DECISION 007" in plain(ui.question_box("t", "", 7))


# --------------------------------------------------------------------------
# progress is always visible — rule R4
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "done,total",
    [(0, 8), (3, 8), (8, 8), (1, 1), (0, 0), (5, 3)],
)
def test_progress_never_crashes_and_states_the_count(done, total) -> None:
    out = plain(ui.progress(done, total, "foundation"))
    assert f"{done} of ~{total}" in out
    assert "foundation" in out


def test_progress_bar_fills_with_work_done() -> None:
    assert plain(ui.progress(0, 8)).count("█") == 0
    assert plain(ui.progress(8, 8)).count("█") > 0


# --------------------------------------------------------------------------
# the rest of the surface
# --------------------------------------------------------------------------


def test_banner_names_the_project_and_version() -> None:
    out = plain(ui.banner("teamtasks", version="0.1.0"))
    assert "teamtasks" in out
    assert "0.1.0" in out
    assert "decide-then-code" in out


def test_banner_without_a_project_still_renders() -> None:
    assert "decide-then-code" in plain(ui.banner())


def test_options_list_every_choice() -> None:
    out = plain(ui.options([("A", "one", "first"), ("B", "two", "second")]))
    for fragment in ("A", "one", "first", "B", "two", "second"):
        assert fragment in out


def test_working_line_names_the_model() -> None:
    """Makes the multi-model design visible instead of hidden plumbing."""
    assert "Opus 4.8" in plain(ui.working("Opus 4.8", "is writing it"))


def test_teaching_block_keeps_every_line() -> None:
    out = plain(ui.teaching("What this means", ["one", "two"]))
    assert "What this means" in out and "one" in out and "two" in out


def test_prompt_is_present() -> None:
    assert "Your call" in plain(ui.prompt())


def test_colour_is_disabled_when_not_a_terminal() -> None:
    """Piped output must carry no escape codes — logs stay readable.

    Run in a subprocess with stdout captured, which is what "not a terminal"
    actually means. The previous version ended in `or ui._ON`, so on a real
    terminal it passed without checking anything — a test that could not fail,
    which is the failure the coding standards name.
    """
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, r'%s'); import forge_ui; print(forge_ui.banner('x'))"
         % str(Path(__file__).resolve().parents[1] / "scripts")],
        capture_output=True, text=True, check=True,
        env={**os.environ, "FORCE_COLOR": "", "NO_COLOR": ""},
    )
    assert ANSI.search(result.stdout) is None, "piped output carried escape codes"
    assert "decide-then-code" in result.stdout, "the banner still rendered"


def test_output_survives_a_console_that_cannot_print_the_symbols(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Windows console is usually cp1252, where none of ⚒ ⛔ ✅ ★ exist.

    Printing the banner raised UnicodeEncodeError and took the whole hook down
    — for the governor that would mean a blocked write never explaining itself.
    """
    import io

    raw = io.BytesIO()
    narrow = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")

    # The stream has to actually reach the helper. The first version of this
    # test reconfigured `narrow` itself and never handed it over, so it passed
    # whether or not the helper did anything at all — a test that could not
    # fail, which is the one thing the coding standards call out by name.
    monkeypatch.setattr(ui.sys, "stdout", narrow)
    monkeypatch.setattr(ui.sys, "stderr", narrow)

    ui._make_output_utf8_safe()

    assert narrow.encoding.lower().replace("-", "") == "utf8", "the helper changed it"
    assert narrow.errors == "replace"

    narrow.write(ui.banner("demo"))
    narrow.write(ui.question_box("How should people log in?", "", 7))
    narrow.flush()

    written = raw.getvalue()
    for symbol in (ui.RECORDED, ui.MARK):
        assert symbol.encode() in written, f"{symbol} reached the stream intact"
