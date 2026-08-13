"""Tests for the code arriving one file at a time, each one explained.

A decided step used to come back as four finished files. Every one was
permitted and every one was covered by the decision, and the user watched an
application appear. They could defend the decision, because they made it. They
could not defend the code, because they met it all at once and finished, which
is the problem this product exists to solve, moved one level down.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import forge_build as fb
import forge_foundation as ff
import forge_state as fs
import forge_steps as stp
from conftest import pass_lean

MARKER = "phase-1.step-1"


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    fs.init(tmp_path)
    return tmp_path


@pytest.fixture()
def forge(project: Path) -> Path:
    return project / fs.FORGE_DIR


def ready(forge: Path) -> None:
    """A project with a decided step, which is where this begins."""
    while (question := ff.next_question(forge)) is not None:
        asked = fs.ask(forge, question.question)
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "1-first.md").write_text(
        "---\nphase: 1\ntitle: First\n---\n\n## Steps\n\n1. [ ] show the list\n",
        encoding="utf-8",
    )
    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# yes\n\n## Why\n\nlooks right\n")
    pass_lean(forge)
    asked = fs.ask(forge, "how does it render?", affects=MARKER)
    fs.answer(forge, asked.id, "# textContent\n\n## Why\n\nnever innerHTML\n")


# ==========================================================================
# the order
# ==========================================================================


def test_a_step_with_no_plan_is_not_held_up(project: Path, forge: Path) -> None:
    """The ledger is opt-in per step. A step that never planned its files is
    governed by the gates that came before it and nothing new."""
    ready(forge)
    assert fs.writes_allowed(forge, project / "anything.py")[0] is True


def test_only_the_next_file_may_be_written(project: Path, forge: Path) -> None:
    ready(forge)
    fb.plan(forge, MARKER, ["index.html", "style.css", "app.js"])

    allowed, why = fs.writes_allowed(forge, project / "app.js")
    assert allowed is False
    assert "writes index.html next" in why

    assert fs.writes_allowed(forge, project / "index.html")[0] is True


def test_nothing_else_is_written_until_the_last_one_is_explained(
    project: Path, forge: Path
) -> None:
    """The explanation is the price of the next file, not a note somebody
    meant to add at the end."""
    ready(forge)
    fb.plan(forge, MARKER, ["index.html", "style.css"])
    fb.mark_written(forge, MARKER, "index.html")

    allowed, why = fs.writes_allowed(forge, project / "style.css")
    assert allowed is False
    assert "index.html was written and has not been explained" in why

    fb.mark_explained(forge, MARKER, "index.html")
    assert fs.writes_allowed(forge, project / "style.css")[0] is True


def test_the_whole_list_done_hands_back_to_the_ordinary_gates(
    project: Path, forge: Path
) -> None:
    ready(forge)
    fb.plan(forge, MARKER, ["index.html"])
    fb.mark_explained(forge, MARKER, "index.html")

    assert fb.next_file(forge, MARKER) is None
    assert fs.writes_allowed(forge, project / "anything-else.py")[0] is True


def test_the_order_cannot_be_rewritten_once_it_has_started(forge: Path) -> None:
    """Renumbering history: the file somebody was shown as the first of four
    becomes the third of six, and the explanation no longer matches."""
    ready(forge)
    fb.plan(forge, MARKER, ["index.html", "style.css"])
    fb.mark_written(forge, MARKER, "index.html")

    with pytest.raises(fs.StateError):
        fb.plan(forge, MARKER, ["something", "else"])


def test_an_unforeseen_file_can_be_added_and_it_shows(forge: Path) -> None:
    """A list with no way to grow is a list somebody works around, and working
    around it means writing files nobody announced."""
    ready(forge)
    fb.plan(forge, MARKER, ["index.html"])
    fb.add_file(forge, MARKER, "db.js")

    assert [f.path for f in fb.read_plan(forge, MARKER)] == ["index.html", "db.js"]
    assert "db.js" in fb.plan_path(forge, MARKER).read_text(encoding="utf-8")


def test_adding_the_same_file_twice_changes_nothing(forge: Path) -> None:
    ready(forge)
    fb.plan(forge, MARKER, ["index.html"])
    fb.add_file(forge, MARKER, "index.html")

    assert [f.path for f in fb.read_plan(forge, MARKER)] == ["index.html"]


def test_the_ledger_survives_the_session_ending_mid_step(forge: Path) -> None:
    """Read back off disk, like everything else (decision 019)."""
    ready(forge)
    fb.plan(forge, MARKER, ["index.html", "style.css"])
    fb.mark_explained(forge, MARKER, "index.html")

    back = fb.read_plan(forge, MARKER)
    assert [(f.path, f.written, f.explained) for f in back] == [
        ("index.html", True, True),
        ("style.css", False, False),
    ]


def test_asking_whether_anything_may_be_written_is_a_different_question(
    project: Path, forge: Path
) -> None:
    """`writes_allowed` with no target answers "is this project open for work",
    which the status report and the pipeline both ask. Answering that with a
    rule about *which* file would be answering something nobody asked."""
    ready(forge)
    fb.plan(forge, MARKER, ["index.html"])

    assert fs.writes_allowed(forge)[0] is True
    assert fs.writes_allowed(forge, project / "elsewhere.py")[0] is False
