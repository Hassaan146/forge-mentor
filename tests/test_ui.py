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


def test_the_original_four_symbols_still_mean_what_they_meant() -> None:
    """Rule R9's set, pinned. Later decisions added to it; none may redefine it.

    A symbol whose meaning moves is worse than no symbol: the user has already
    learned it, and nothing on the screen announces that it changed.
    """
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
        capture_output=True, check=True, encoding="utf-8", errors="replace",
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


# --------------------------------------------------------------------------
# the box, and why it needs a width function
# --------------------------------------------------------------------------


def test_every_framed_line_closes_at_the_same_column() -> None:
    """The bug this replaced, stated as a test.

    `⚒` is East-Asian "Neutral", so `len()` says one column — but terminals
    give it emoji presentation and draw two. The top rail came out a column
    longer than the bottom and the frame looked broken.
    """
    out = ui.decision(
        "What are you building this with?",
        number=1,
        subtitle="the first decision",
        means=["a line of teaching"],
        choices=[("A", "Browser only", "no server, nothing to deploy")],
        recommend=("A", "nothing to host"),
        against="the data lives in one browser",
        done=0,
        total=6,
        stage="foundation",
    )

    framed = [ln for ln in out.splitlines() if ln.strip()[:1] in {"┌", "│", "└"}]
    widths = {ui.visible_width(ln) for ln in framed}

    assert len(framed) > 8, "the whole decision is inside the frame"
    assert len(widths) == 1, f"the frame is ragged: {sorted(widths)}"


def test_colour_codes_are_not_counted_as_columns() -> None:
    """They are bytes the terminal consumes and never draws.

    Counting them is the other way padding goes silently wrong — and it only
    shows up with colour on, which is not how tests usually run.
    """
    assert ui.visible_width(f"{ui.AMBER}{ui.BOLD}abc{ui.RESET}") == 3


def test_the_symbols_are_measured_at_their_rendered_width() -> None:
    """Pinned explicitly, because Python cannot ask the terminal.

    If one of these is wrong the box goes crooked, so the assumption belongs
    somewhere a reviewer can see and argue with it.
    """
    assert ui.visible_width(ui.MARK) == 2, "emoji presentation despite Neutral class"
    assert ui.visible_width(ui.BLOCKED) == 2
    assert ui.visible_width(ui.RECORDED) == 2
    assert ui.visible_width(ui.STAR) == 1


# --------------------------------------------------------------------------
# follow-ups are framed and short — decision 035
# --------------------------------------------------------------------------


def test_a_follow_up_is_framed_like_everything_else() -> None:
    """An unframed paragraph is indistinguishable from ordinary chat.

    A session looked like Forge while a question was on screen and like plain
    assistant text for everything in between, so the user could not tell which
    of the two was bound by Forge's rules.
    """
    out = ui.note("Why not the others", ["No backup.", "One browser only."])
    framed = [ln for ln in out.splitlines() if ln.strip()[:1] in {"┌", "│", "└"}]

    assert framed, "the follow-up is inside a frame"
    assert len({ui.visible_width(ln) for ln in framed}) == 1, "and the frame is square"


def test_a_follow_up_is_capped_at_three_lines() -> None:
    """The cap is the feature. It sprawled because it had nowhere to be short."""
    out = plain(ui.note("Costs", [f"line {n}" for n in range(1, 8)]))

    for kept in ("line 1", "line 2", "line 3"):
        assert kept in out
    assert "line 4" not in out
    assert "4 more in the decision record" in out, "and it says what it withheld"


def test_a_short_follow_up_is_left_alone() -> None:
    out = plain(ui.note("Costs", ["only one point"]))
    assert "only one point" in out
    assert "more in the decision record" not in out


def test_every_symbol_carries_exactly_one_meaning() -> None:
    """Decision 035 replaced R9's count with a test: no symbol without a meaning.

    Eight now. `→` earned the eighth place by that test — "Forge has stopped and
    is waiting for you" is a meaning none of the others carries, and it had no
    marker at all until the action frame existed.
    """
    assert len(ui.SYMBOLS) == 8
    assert len(set(ui.SYMBOLS)) == 8, "no symbol used twice"


def test_the_symbols_still_read_without_colour() -> None:
    """R9's real point, which decision 035 keeps: colour is never alone."""
    out = plain(ui.note("Costs", ["no backup"], symbol=ui.COST, ask="A, B, or C?"))
    assert ui.COST in out
    assert "Costs" in out and "A, B, or C?" in out


# --------------------------------------------------------------------------
# the colour system — rule R11
# --------------------------------------------------------------------------


def in_colour(snippet: str) -> str:
    """Run `snippet` in a subprocess with colour forced on, and return stdout.

    Colour is off under pytest, because stdout is captured and `isatty()` is
    false — which is correct behaviour and useless for testing the colours
    themselves. A subprocess with FORCE_COLOR set is the only place the real
    escape codes exist.

    `encoding` is pinned, and that is not tidiness. The child writes its frames
    as UTF-8; a Windows parent decodes a pipe in the system code page, which
    has no byte for `╔`. The decode happens on a reader thread, so the error
    never surfaces as an exception — `subprocess` hands back `stdout=None` and
    the test fails somewhere else entirely, pointing at nothing.
    """
    import subprocess

    scripts = str(Path(__file__).resolve().parents[1] / "scripts")
    result = subprocess.run(
        [sys.executable, "-c", f"import sys; sys.path.insert(0, r'{scripts}');\n{snippet}"],
        capture_output=True,
        check=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "FORCE_COLOR": "1", "NO_COLOR": ""},
    )
    return result.stdout


def test_each_meaning_has_its_own_colour() -> None:
    """Six meanings, six codes, no two the same.

    Two meanings sharing a colour is the failure the whole scheme exists to
    avoid: the user learns the colour, applies it, and is wrong half the time.
    """
    codes = in_colour(
        "import forge_ui as ui\n"
        "print('|'.join(ui._PALETTE[key] for _, key, _ in ui.MEANINGS))"
    ).strip().split("|")

    assert len(codes) == 6
    assert len(set(codes)) == 6, "two meanings are drawn in the same colour"


def test_the_legend_teaches_every_colour_it_uses() -> None:
    """A colour system nobody was told about is a colour system nobody reads."""
    out = plain(ui.legend())
    for name, _, meaning in ui.MEANINGS:
        assert name in out, f"the legend never names {name}"
        assert meaning.split(" — ")[0][:20] in out
    assert "double-ruled" in out, "and what the double frame means"


def test_the_legend_still_names_its_colours_without_colour() -> None:
    """The swatch is the one thing that cannot survive NO_COLOR, so it is named."""
    out = plain(ui.legend())
    for _, key, _ in ui.MEANINGS:
        assert f"[{key.lower()}]" in out


def test_the_legend_frame_is_square_at_any_width() -> None:
    framed = [ln for ln in ui.legend().splitlines() if ln.strip()[:1] in {"┌", "│", "└"}]
    assert framed
    assert len({ui.visible_width(ln) for ln in framed}) == 1, "the legend frame is ragged"


def test_nc_is_the_reset_under_the_name_shell_scripts_use() -> None:
    assert ui.NC == ui.RESET


def test_paint_always_closes_the_span() -> None:
    """An unclosed span does not stop at the end of Forge's output.

    It recolours whatever the terminal prints next — usually the user's own
    shell prompt, which reads as Forge having broken their terminal.
    """
    out = in_colour(
        "import forge_ui as ui\n"
        "print(ui.paint(ui.RED, 'stopped'), ui.paint(ui.GREEN, 'done', bold=True))"
    )
    assert "stopped" in out and "done" in out
    assert out.rstrip().endswith("\033[0m"), "the last thing printed is a reset"


@pytest.mark.parametrize(
    "call",
    [
        "ui.decision('t', means=['m'], choices=[('A','one','first')])",
        "ui.note('h', ['one'], ask='yes?')",
        "ui.blocked('rate limiting', 'nothing recorded for', ['decide it'])",
        "ui.important(['this cannot be undone'])",
        "ui.legend()",
        "ui.recorded('B', 'x.md')",
        "ui.confirm('go ahead?')",
    ],
)
def test_no_block_leaves_a_colour_open(call: str) -> None:
    """Every block closes its own colour, whichever block it is."""
    out = in_colour(f"import forge_ui as ui\nprint({call}.rstrip())")
    assert out.rstrip().endswith("\033[0m"), f"{call} left a colour running"


# --------------------------------------------------------------------------
# the action frame — the moment the turn passes to the user
# --------------------------------------------------------------------------


def test_the_ask_is_in_its_own_frame_not_the_content_one() -> None:
    """The one thing the user has to act on is not the last line of a block.

    Inside the box it carried the same weight as the option above it, and it
    was the first thing lost when the block scrolled.
    """
    out = plain(ui.decision("How should people log in?", choices=[("A", "one", "first")]))
    single = [ln for ln in out.splitlines() if ln.strip()[:1] in {"┌", "│", "└"}]
    double = [ln for ln in out.splitlines() if ln.strip()[:1] in {"╔", "║", "╚"}]

    assert single, "the decision is still framed"
    assert double, "and the ask has a frame of its own"
    assert "YOUR TURN" in out
    assert ui.ACTION in out, "and a symbol, for a terminal with no colour"


def test_the_action_frame_is_square() -> None:
    framed = [ln for ln in ui.confirm("go ahead?").splitlines() if ln.strip()[:1] in {"╔", "║", "╚"}]
    assert framed
    assert len({ui.visible_width(ln) for ln in framed}) == 1, "the action frame is ragged"


def test_the_ask_names_the_letters_that_were_actually_offered() -> None:
    """A two-option question must not ask for a C that was never shown."""
    two = plain(ui.decision("t", choices=[("A", "one", "x"), ("B", "two", "y")]))
    three = plain(ui.decision("t", choices=[("A", "1", "x"), ("B", "2", "y"), ("C", "3", "z")]))

    assert "A, or B?" in two
    assert "A, B, or C?" in three


def test_a_yes_no_gate_says_what_yes_and_no_do() -> None:
    """"Type yes to continue" is only clear if the alternative is stated too."""
    out = plain(ui.confirm("This makes the repository public. Continue?"))
    assert "type yes" in out and "no to stop" in out
    assert "public" in out


def test_an_open_question_asks_for_words_not_a_letter() -> None:
    out = plain(ui.decision("What are you building?", means=["a line"]))
    assert "your own words" in out
    assert "A, B, or C" not in out


# --------------------------------------------------------------------------
# details that must not be skimmed past
# --------------------------------------------------------------------------


def test_an_important_detail_is_barred_and_framed() -> None:
    out = plain(ui.important(["This cannot be undone."]))
    assert ui.BAR in out, "the bar puts it on its own vertical"
    assert "This cannot be undone." in out

    framed = [ln for ln in ui.important(["x"]).splitlines() if ln.strip()[:1] in {"┌", "│", "└"}]
    assert len({ui.visible_width(ln) for ln in framed}) == 1


def test_a_decision_can_carry_an_important_detail_inside_it() -> None:
    out = plain(
        ui.decision(
            "Public or private?",
            choices=[("A", "public", "free review")],
            important_lines=["Anyone will be able to read this code."],
        )
    )
    assert ui.BAR in out
    assert "Anyone will be able to read this code." in out


def test_a_long_important_detail_wraps_inside_its_frame() -> None:
    """It is the line the user most needs to read; it cannot break the box."""
    long_line = "This cannot be undone once the repository is public. " * 3
    framed = [
        ln for ln in ui.important([long_line]).splitlines() if ln.strip()[:1] in {"┌", "│", "└"}
    ]
    assert len({ui.visible_width(ln) for ln in framed}) == 1, "a long detail broke the frame"


def test_a_block_names_the_undecided_thing_on_its_own_line() -> None:
    """It tells the user which question to go and answer.

    As the tail of a sentence it was the easiest part of the message to read
    past — which for the governor means a user who cannot find the way out.
    """
    out = plain(ui.blocked("rate limiting", "No decision recorded yet for:", ["answer it"]))
    barred = [ln for ln in out.splitlines() if ui.BAR in ln]

    assert any("rate limiting" in ln for ln in barred)
    assert "YOUR TURN" in out and "answer it" in out


# --------------------------------------------------------------------------
# the plan, on one screen
# --------------------------------------------------------------------------


def a_plan() -> list[dict]:
    return [
        {
            "number": 1, "title": "One todo, end to end", "delivers": "it survives a refresh",
            "state": "done", "built": 2,
            "steps": [{"text": "show the list", "built": True},
                      {"text": "save a todo", "built": True}],
        },
        {
            "number": 2, "title": "Complete and delete", "delivers": "tick one off",
            "state": "now", "built": 1,
            "steps": [{"text": "mark complete", "built": True},
                      {"text": "delete one", "built": False}],
        },
        {
            "number": 3, "title": "Edit in place", "delivers": "fix a typo",
            "state": "later", "built": 0, "steps": [],
        },
    ]


def test_the_roadmap_shows_every_phase_at_once() -> None:
    """A plan revealed one phase at a time is not a plan."""
    out = plain(ui.roadmap(a_plan()))
    for title in ("One todo, end to end", "Complete and delete", "Edit in place"):
        assert title in out


def test_each_phase_says_which_state_it_is_in_without_colour() -> None:
    out = plain(ui.roadmap(a_plan()))
    for word in ("done", "now", "later"):
        assert word in out


def test_only_the_current_phase_lists_its_steps() -> None:
    """Every step of every phase would bury the shape the user is here to see."""
    out = plain(ui.roadmap(a_plan()))
    assert "mark complete" in out, "the phase being worked on shows its steps"
    assert "show the list" not in out, "a finished phase does not"


def test_a_phase_with_no_steps_says_so_rather_than_looking_empty() -> None:
    assert "not broken into steps yet" in plain(ui.roadmap(a_plan()))


def test_the_roadmap_frame_is_square() -> None:
    framed = [ln for ln in ui.roadmap(a_plan()).splitlines() if ln.strip()[:1] in {"┌", "│", "└"}]
    assert framed
    assert len({ui.visible_width(ln) for ln in framed}) == 1, "the roadmap frame is ragged"


def test_an_empty_plan_says_so_instead_of_drawing_nothing() -> None:
    assert "No phases have been compiled yet" in plain(ui.roadmap([]))
