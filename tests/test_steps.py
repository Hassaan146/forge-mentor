"""Tests for the build loop's unit of work.

These exist because of a real run. Forge asked its six foundation questions,
compiled nothing, and then wrote `app.js`, `db.js`, `index.html` and
`style.css` in one turn — an entire application, with no question asked after
the sixth. Every write was allowed, because `writes_allowed` had run out of
things to check.

So the assertions here are mostly about refusal: what must *not* be buildable,
and why.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import forge_state as fs
from conftest import pass_lean
import forge_steps as st


@pytest.fixture()
def forge(tmp_path: Path) -> Path:
    fs.init(tmp_path)
    return tmp_path / fs.FORGE_DIR


def accept_plan(forge: Path) -> None:
    """Record that the user has seen the whole plan.

    Its own gate, ahead of the step gate: phases can exist without anyone
    having read them, and that is what happened — five phases compiled into a
    progress file as prose, the first one built before the user knew there
    were five.
    """
    asked = fs.ask(forge, "Does this plan look right?", affects=st.PLAN_MARKER)
    fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")


def write_phase(
    forge: Path,
    number: int,
    steps: list[str] | None = None,
    *,
    accept: bool = True,
    **header,
) -> Path:
    """A phase file, and by default a plan the user has accepted.

    `accept=False` leaves the plan unapproved, which is what the tests for
    that gate need.
    """
    fields = {"phase": str(number), "title": f"Phase {number}", **header}
    body = "---\n" + "".join(f"{k}: {v}\n" for k, v in fields.items()) + "---\n"
    if steps:
        body += "\n## Steps\n\n"
        body += "\n".join(f"{n}. [ ] {text}" for n, text in enumerate(steps, start=1)) + "\n"

    folder = forge / "phases"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{number}-phase.md"
    path.write_text(body, encoding="utf-8")

    if accept and not st.plan_accepted(forge):
        accept_plan(forge)
    return path


def decide(forge: Path, marker: str) -> None:
    """A step decision, with the lean pass that has to come before it."""
    pass_lean(forge, marker)
    asked = fs.ask(forge, f"decision for {marker}", affects=marker)
    fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")


# --------------------------------------------------------------------------
# what must not be buildable
# --------------------------------------------------------------------------


def test_a_project_with_no_phases_cannot_be_built(forge: Path) -> None:
    """The state the real failure ran in.

    Six decisions, a progress file describing the phases in prose, and no
    `phases/` directory at all.
    """
    gap = st.next_gap(forge)
    assert gap is not None
    assert gap.kind == "unplanned"
    assert "have not been compiled" in gap.reason


def test_a_plan_nobody_has_seen_cannot_be_built(forge: Path) -> None:
    """The gap the user found: the plan arrived in instalments.

    Five phases were compiled and the first was built before they knew there
    were five — so the question that set the shape of all of them was answered
    without the shape being visible.
    """
    write_phase(forge, 1, ["first"], accept=False)
    write_phase(forge, 2, ["second"], accept=False)
    gap = st.next_gap(forge)

    assert gap is not None
    assert gap.kind == "unapproved"
    assert "There are 2 phases" in gap.reason, "and it says how many there are"
    assert st.plan_accepted(forge) is False

    accept_plan(forge)
    assert st.plan_accepted(forge) is True
    assert st.next_gap(forge).kind == "unchallenged", "first, is it worth building"

    pass_lean(forge)
    assert st.next_gap(forge).kind == "undecided", "now the steps gate, one at a time"


def test_accepting_the_plan_is_a_decision_not_a_flag(forge: Path) -> None:
    """It rides on the chain, so it cannot be set by editing a file."""
    write_phase(forge, 1, ["first"], accept=False)
    fs.ask(forge, "Does this plan look right?", affects=st.PLAN_MARKER)

    assert st.plan_accepted(forge) is False, "asking is not accepting"


def test_a_phase_with_no_steps_cannot_be_built(forge: Path) -> None:
    """A phase is not a unit of work. It is a list of them."""
    write_phase(forge, 1)
    gap = st.next_gap(forge)

    assert gap is not None
    assert gap.kind == "unplanned"
    assert "broken into steps" in gap.reason


def test_an_undecided_step_names_itself_as_the_question(forge: Path) -> None:
    write_phase(forge, 1, ["Save a typed todo to the browser's storage"])
    pass_lean(forge)
    gap = st.next_gap(forge)

    assert gap is not None
    assert gap.kind == "undecided"
    assert gap.step is not None and gap.step.number == 1
    assert "Save a typed todo" in gap.reason


def test_the_gate_opens_only_for_the_decided_step(forge: Path) -> None:
    write_phase(forge, 1, ["first", "second"])
    decide(forge, "phase-1.step-1")

    assert st.next_gap(forge) is None, "step 1 is decided, so step 1 may be built"

    st.mark_built(forge, 1, 1)
    gap = st.next_gap(forge)

    assert gap is not None, "step 2 has not been decided"
    assert gap.step is not None and gap.step.number == 2


def test_deciding_a_later_step_does_not_unlock_an_earlier_one(forge: Path) -> None:
    """Order is the point. Otherwise a step list is a menu, not a sequence."""
    write_phase(forge, 1, ["first", "second"])
    decide(forge, "phase-1.step-2")

    gap = st.next_gap(forge)
    assert gap is not None
    assert gap.step is not None and gap.step.number == 1


def test_a_finished_phase_is_skipped_and_the_next_one_gates(forge: Path) -> None:
    write_phase(forge, 1, ["first"], status="complete")
    write_phase(forge, 2, ["second"])

    gap = st.next_gap(forge)
    assert gap is not None
    assert gap.phase == 2


def test_an_unreadable_phase_file_stops_the_loop_rather_than_being_skipped(
    forge: Path,
) -> None:
    """Skipping it would silently build the phase after it in its place."""
    folder = forge / "phases"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "1-broken.md").write_text("no header at all\n", encoding="utf-8")

    gap = st.next_gap(forge)
    assert gap is not None
    assert "cannot read the phase file" in gap.reason


# --------------------------------------------------------------------------
# reading the list
# --------------------------------------------------------------------------


def test_phases_run_in_number_order_not_filename_order(forge: Path) -> None:
    """`10-` sorts before `2-` as text, and a loop that runs phase 10 second
    is not a loop."""
    write_phase(forge, 10, ["tenth"])
    write_phase(forge, 2, ["second"])

    assert [n for n, _, _ in st.phase_files(forge)] == [2, 10]


@pytest.mark.parametrize(
    "line",
    ["1. add a todo", "- add a todo", "* add a todo", "- [ ] add a todo", "1. [ ] add a todo"],
)
def test_a_step_list_reads_however_it_was_written(forge: Path, line: str) -> None:
    """A planner writes one shape, a user editing by hand writes another."""
    path = write_phase(forge, 1)
    path.write_text(
        path.read_text(encoding="utf-8") + f"\n## Steps\n\n{line}\n", encoding="utf-8"
    )

    steps = st.read_steps(path, 1)
    assert len(steps) == 1
    assert steps[0].text == "add a todo"
    assert steps[0].built is False


def test_only_lines_under_the_steps_heading_count(forge: Path) -> None:
    """A phase file has other lists in it, and deciding a deliverable is nonsense."""
    path = write_phase(forge, 1, ["the real step"])
    path.write_text(
        path.read_text(encoding="utf-8") + "\n## Done when\n\n- tests pass\n- review is clean\n",
        encoding="utf-8",
    )

    assert [s.text for s in st.read_steps(path, 1)] == ["the real step"]


def test_a_ticked_step_is_built(forge: Path) -> None:
    path = write_phase(forge, 1, ["first", "second"])
    st.mark_built(forge, 1, 1)

    steps = st.read_steps(path, 1)
    assert steps[0].built is True
    assert steps[1].built is False, "only the one asked for"
    assert steps[1].text == "second", "and the text survives the rewrite"


def test_progress_counts_open_phases_only(forge: Path) -> None:
    """A bar that includes finished phases never appears to move."""
    write_phase(forge, 1, ["a", "b"], status="complete")
    write_phase(forge, 2, ["c", "d", "e"])
    st.mark_built(forge, 2, 1)

    assert st.position(forge) == (1, 3)


# --------------------------------------------------------------------------
# writing the list
# --------------------------------------------------------------------------


def test_a_phase_can_be_given_its_steps(forge: Path) -> None:
    write_phase(forge, 1)
    steps = st.write_steps(forge, 1, ["show the list", "save a todo", "read them back"])

    assert [s.number for s in steps] == [1, 2, 3]
    assert steps[1].text == "save a todo"
    assert st.next_gap(forge).step.number == 1


def test_rewriting_a_started_list_is_refused(forge: Path) -> None:
    """The decisions are recorded against step numbers.

    Renumbering them would leave a signed record pointing at a step that no
    longer says what it said when the user answered it.
    """
    write_phase(forge, 1, ["first", "second"])
    decide(forge, "phase-1.step-1")

    with pytest.raises(st.StepError) as err:
        st.write_steps(forge, 1, ["something else entirely"])
    assert "pointing at nothing" in str(err.value)


def test_the_steps_section_replaces_itself_without_eating_the_file(forge: Path) -> None:
    path = write_phase(forge, 1, ["old"])
    path.write_text(
        path.read_text(encoding="utf-8") + "\n## Done when\n\n- tests pass\n", encoding="utf-8"
    )
    st.write_steps(forge, 1, ["new"])

    body = path.read_text(encoding="utf-8")
    assert "## Done when" in body and "tests pass" in body
    assert "old" not in body
    assert [s.text for s in st.read_steps(path, 1)] == ["new"]


def test_a_step_list_cannot_be_empty(forge: Path) -> None:
    write_phase(forge, 1)
    with pytest.raises(st.StepError):
        st.write_steps(forge, 1, ["", "   "])


def test_an_unknown_phase_says_so(forge: Path) -> None:
    with pytest.raises(st.StepError) as err:
        st.write_steps(forge, 4, ["x"])
    assert "no phase 4" in str(err.value)


def test_ticking_a_step_that_does_not_exist_says_so(forge: Path) -> None:
    write_phase(forge, 1, ["only one"])
    with pytest.raises(st.StepError) as err:
        st.mark_built(forge, 1, 9)
    assert "no step 9" in str(err.value)


# --------------------------------------------------------------------------
# the marker, which is what ties a decision to a step
# --------------------------------------------------------------------------


def test_a_step_is_claimed_by_marker_not_by_decision_id(forge: Path) -> None:
    """Decision 018 accepts that two branches can both write a decision 014."""
    write_phase(forge, 1, ["first"])
    assert st.Step(1, 1, "first").marker == "phase-1.step-1"

    decide(forge, "phase-1.step-1")
    assert "phase-1.step-1" in st.decided_markers(forge)


def test_an_open_question_does_not_count_as_a_decided_step(forge: Path) -> None:
    """Asking is not deciding, which is the oldest rule in the product."""
    write_phase(forge, 1, ["first"])
    fs.ask(forge, "step one", affects="phase-1.step-1")

    assert st.decided_markers(forge) == set()
    assert st.next_gap(forge) is not None


# --------------------------------------------------------------------------
# the plan, shown whole
# --------------------------------------------------------------------------


def test_the_roadmap_carries_every_phase_not_just_the_current_one(forge: Path) -> None:
    """The point of it. One phase at a time is what the user objected to."""
    write_phase(forge, 1, ["a", "b"], status="complete", delivers="one todo, end to end")
    write_phase(forge, 2, ["c"], delivers="complete and delete")
    write_phase(forge, 3, delivers="edit in place")

    plan = st.roadmap(forge)
    assert [p.number for p in plan] == [1, 2, 3]
    assert plan[0].delivers == "one todo, end to end"
    assert [p.state() for p in plan] == ["done", "now", "later"]


def test_a_broken_phase_still_appears_on_the_roadmap(forge: Path) -> None:
    """Leaving it out would show a plan with a silent hole in it."""
    folder = forge / "phases"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "1-broken.md").write_text("no header\n", encoding="utf-8")

    assert "unreadable" in st.roadmap(forge)[0].title


def test_the_whole_plan_is_written_at_once(forge: Path) -> None:
    plan = st.compile_phases(
        forge,
        [
            ("One todo, end to end", "type a todo, it survives a refresh"),
            ("Complete and delete", "tick one off, remove one"),
            ("Edit in place", "fix a typo without retyping"),
        ],
    )

    assert [p.number for p in plan] == [1, 2, 3]
    assert plan[1].title == "Complete and delete"
    assert plan[0].delivers == "type a todo, it survives a refresh"
    assert len(list((forge / "phases").glob("*.md"))) == 3


def test_recompiling_a_started_plan_is_refused(forge: Path) -> None:
    """Renumbering would leave signed records pointing at work that moved."""
    st.compile_phases(forge, [("First", "a"), ("Second", "b")])
    st.write_steps(forge, 1, ["only step"])
    accept_plan(forge)
    decide(forge, "phase-1.step-1")
    st.mark_built(forge, 1, 1)

    with pytest.raises(st.StepError) as err:
        st.compile_phases(forge, [("Something else", "c")])
    assert "already under way" in str(err.value)


def test_a_plan_needs_at_least_one_phase(forge: Path) -> None:
    with pytest.raises(st.StepError):
        st.compile_phases(forge, [])
