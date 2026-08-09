"""Tests for the plan as a page.

The terminal roadmap is what gates the build; this is the copy that survives
the scrollback and can be sent to someone. It is generated from the files, so
the thing worth testing is that it says what the files say — and that nothing
in a user's own project can turn it into markup.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import forge_roadmap as rm
import forge_state as fs
import forge_steps as st


@pytest.fixture()
def forge(tmp_path: Path) -> Path:
    fs.init(tmp_path)
    return tmp_path / fs.FORGE_DIR


def a_project(forge: Path) -> None:
    st.compile_phases(
        forge,
        [
            ("One todo, end to end", "type a todo, it survives a refresh"),
            ("Complete and delete", "tick one off, remove one"),
            ("Edit in place", "fix a typo without retyping"),
        ],
    )
    asked = fs.ask(forge, "Does this plan look right?", affects=st.PLAN_MARKER)
    fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")

    st.write_steps(forge, 1, ["Show the list", "Save a todo"])
    asked = fs.ask(forge, "How does a typed todo reach the page?", affects="phase-1.step-1")
    fs.answer(forge, asked.id, "# textContent\n\n## Why\n\nnever innerHTML\n")
    st.mark_built(forge, 1, 1)


def test_the_page_carries_every_phase(forge: Path) -> None:
    a_project(forge)
    page = rm.render(forge, "todo")

    assert page.count('<article class="phase') == 3
    for title in ("One todo, end to end", "Complete and delete", "Edit in place"):
        assert title in page


def test_the_page_shows_which_decision_settled_each_step(forge: Path) -> None:
    """The point of keeping it. In week six nobody remembers why."""
    a_project(forge)
    page = rm.render(forge, "todo")

    assert "How does a typed todo reach the page?" in page
    assert "1 of 2 steps built" in page


def test_a_project_can_never_turn_its_own_roadmap_into_markup(forge: Path) -> None:
    """Every string on this page came out of a file the user edits.

    A phase title with a `<script>` in it would run in a page the user is told
    to open in a browser. The security floor covers what Forge generates, not
    only what it writes for you.
    """
    st.compile_phases(forge, [("<script>alert(1)</script>", "a & b <b>c</b>")])
    page = rm.render(forge, "todo")

    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
    assert "a &amp; b" in page


def test_the_page_asks_nothing_of_the_network(forge: Path) -> None:
    """It opens from disk on a machine with nothing installed and no network.

    The same stance the plugin takes about its own dependencies — and what
    makes the generated page safe to commit to the project repository.
    """
    a_project(forge)
    page = rm.render(forge, "todo")

    assert re.search(r'(?:src|href)\s*=\s*"(?!#)https?://', page) is None
    assert "<link" not in page
    assert "@import" not in page


def test_an_unaccepted_plan_says_so_on_the_page(forge: Path) -> None:
    st.compile_phases(forge, [("First", "a")])
    page = rm.render(forge, "todo")

    assert "has not been accepted yet" in page


def test_an_accepted_plan_does_not(forge: Path) -> None:
    a_project(forge)
    assert "has not been accepted yet" not in rm.render(forge, "todo")


def test_writing_it_puts_it_where_the_notes_live(forge: Path) -> None:
    a_project(forge)
    path = rm.write(forge, "todo")

    assert path == forge / rm.PAGE
    assert path.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_a_plan_with_no_phases_still_renders(forge: Path) -> None:
    """Called before anything is compiled, it must not crash the tool."""
    page = rm.render(forge, "todo")
    assert "0 phases" in page


def test_the_page_uses_the_same_six_meanings_as_the_terminal(forge: Path) -> None:
    """Two palettes drifting apart is how "yellow" comes to mean two things."""
    import forge_ui as ui

    assert {name for _, name, _ in ui.MEANINGS} == set(rm._PALETTE)
