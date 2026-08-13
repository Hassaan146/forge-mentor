"""Tests for adding to a project that already works.

Forge could take a project from nothing to ten phases and then had nothing to
say. Every gate reads the phase list, so once the last phase was built the gate
opened: a user coming back a month later to add one feature got no questions at
all, and the builder wrote whatever it thought the sentence meant.

Which is the worst moment to have no rules. A new feature is written against a
codebase full of decisions nobody is re-reading, and the cheapest way to ruin a
working project is to add something that quietly contradicts one of them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import forge_feature as fe
import forge_foundation as ff
import forge_state as fs
import forge_steps as stp


@pytest.fixture()
def forge(tmp_path: Path) -> Path:
    return fs.init(tmp_path)


def answer(forge: Path, question: str, choice: str = "A") -> None:
    asked = fs.ask(forge, question)
    fs.answer(forge, asked.id, f"# {choice}\n\n## Why\n\nbecause\n")


def a_finished_project(forge: Path) -> None:
    """A project with its foundation recorded and one phase built."""
    answers = {"stack": "Both together", "delivery": "Only on my machine", "people": "Only me"}
    while (question := ff.next_question(forge)) is not None:
        answer(forge, question.question, answers.get(question.key, "A"))

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "1-first.md").write_text(
        "---\nphase: 1\ntitle: First\ndone: yes\n---\n\n## Steps\n\n1. [x] the first slice\n",
        encoding="utf-8",
    )
    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# yes\n\n## Why\n\nlooks right\n")


# ==========================================================================
# what it reads instead of asking
# ==========================================================================


def test_the_feature_is_told_what_it_is_being_built_inside(forge: Path) -> None:
    a_finished_project(forge)

    built_on = fe.constraints(forge, "let people upload a photo with each todo")
    questions = " ".join(c.question for c in built_on)

    assert built_on, "a feature with no context is a feature that contradicts something"
    assert "building this with" in questions, "the shape of the project always applies"
    for constraint in built_on:
        assert constraint.choice, f"{constraint.id} came back without what was chosen"


def test_the_context_is_ids_and_choices_rather_than_the_whole_history(
    forge: Path,
) -> None:
    """The token half of the request, and it is a real constraint.

    Re-reading every record to add one feature spends a project's worth of
    context to learn what is already written down, and most of it does not bear
    on the feature at all.
    """
    a_finished_project(forge)
    for number in range(12):
        answer(forge, f"some later decision number {number}")

    built_on = fe.constraints(forge, "add a photo upload")

    assert len(built_on) <= fe.MAX_CONSTRAINTS
    for constraint in built_on:
        assert len(constraint.line()) < 200, "a line, not a record"


def test_the_foundation_is_never_asked_again(forge: Path) -> None:
    a_finished_project(forge)
    assert ff.next_question(forge) is None
    assert fe.owed(forge, "add a photo upload") != [], "but the new subject still owes"

    owed = [q.key for q in fe.owed(forge, "add a photo upload")]
    assert "upload-where" in owed
    assert "stack" not in owed and "delivery" not in owed


# ==========================================================================
# not disturbing what is already there
# ==========================================================================


def test_a_feature_that_contradicts_a_decision_is_named_not_built(forge: Path) -> None:
    """The other half of the request, and the one with teeth.

    The project said it runs only on this machine. A feature that wants hosting
    is not impossible, it is a decision to reopen, and reopening one is
    something the user does rather than something the builder does quietly.
    """
    a_finished_project(forge)

    found = fe.clashes(forge, "deploy it to the cloud so my team can use it")
    assert found, "a feature that needs hosting on a laptop-only project is a clash"

    first = found[0]
    assert "runs only on your own machine" in first.because
    assert first.decision is not None, "and it names the decision to reopen"
    assert "decision" in first.line()


def test_a_feature_that_fits_reports_no_clash(forge: Path) -> None:
    """A gate that fires on everything is one people learn to type past."""
    a_finished_project(forge)
    assert fe.clashes(forge, "let me tick a todo off with the keyboard") == []


def test_a_new_phase_is_appended_and_nothing_existing_is_touched(forge: Path) -> None:
    a_finished_project(forge)
    before = (forge / "phases" / "1-first.md").read_text(encoding="utf-8")

    path = fe.add_phase(forge, "Photos", "a photo on each todo")

    assert path.name.startswith("2-")
    assert (forge / "phases" / "1-first.md").read_text(encoding="utf-8") == before
    assert "[x] the first slice" in before, "and the built step is still built"


def test_a_phase_is_never_written_over(forge: Path) -> None:
    """The number always increments, so a collision means a file nobody expected.

    Refusing is the only safe answer: the alternative is overwriting a phase
    whose steps somebody has already built, which is the one thing appending
    exists to prevent.
    """
    a_finished_project(forge)
    # A file whose name and header disagree, which a hand edit produces. The
    # next number is read from the headers, so without the check the name it
    # lands on is one that already exists.
    (forge / "phases" / "2-photos.md").write_text(
        "---\nphase: 1\ntitle: Photos\n---\n\n## Steps\n\n1. [x] built already\n",
        encoding="utf-8",
    )

    with pytest.raises(stp.StepError):
        fe.add_phase(forge, "Photos", "a photo on each todo")


def test_the_same_title_twice_is_two_phases_not_one_overwritten(forge: Path) -> None:
    a_finished_project(forge)
    first = fe.add_phase(forge, "Photos", "a photo on each todo")
    second = fe.add_phase(forge, "Photos", "and one on each list")

    assert first != second
    assert first.exists() and second.exists()


def test_the_appended_phase_still_has_to_be_broken_into_steps(forge: Path) -> None:
    """Appending is not permission. The ordinary gates apply to it."""
    a_finished_project(forge)
    fe.add_phase(forge, "Photos", "a photo on each todo")

    gap = stp.next_gap(forge)
    assert gap is not None and gap.kind == "unplanned"
    assert fs.writes_allowed(forge)[0] is False
