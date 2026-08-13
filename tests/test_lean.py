"""Tests for the pass that asks whether a thing should be built at all.

Forge's question has always been *which* decision. This is the one before it:
does this need writing, and if so how much of it. A step that arrived on a plan
used to get built at whatever size the model first imagined it, and nobody was
ever asked.

Nothing here judges whether code is minimal. That is the model's job, and it is
better at it with ponytail loaded. What is tested is the division of labour:
the model reasons, and the gate refuses to move until the answer is on disk.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import forge_foundation as ff
import forge_lean as ln
import forge_state as fs
import forge_steps as stp


@pytest.fixture()
def forge(tmp_path: Path) -> Path:
    return fs.init(tmp_path)


def answer(forge: Path, question: str, choice: str = "A") -> None:
    asked = fs.ask(forge, question)
    fs.answer(forge, asked.id, f"# {choice}\n\n## Why\n\nbecause\n")


def ready(forge: Path, step: str = "let a todo be ticked off") -> None:
    """A project with everything answered except this step's own questions."""
    while (question := ff.next_question(forge)) is not None:
        answer(forge, question.question)

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "1-first.md").write_text(
        f"---\nphase: 1\ntitle: First\n---\n\n## Steps\n\n1. [ ] {step}\n",
        encoding="utf-8",
    )
    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# yes\n\n## Why\n\nlooks right\n")


def full_ladder() -> list[ln.Finding]:
    return [ln.Finding(rung, f"answer about {rung}") for rung in ln.LADDER_KEYS]


def test_the_ladder_asks_whether_it_should_exist_before_how_big_it_is() -> None:
    """Order matters. Put the size question after the design question and the
    design has already settled the size."""
    assert ln.LADDER_KEYS[0] == "needed"
    assert ln.LADDER_KEYS.index("already") < ln.LADDER_KEYS.index("smallest")
    assert "standard library" in dict(ln.LADDER)["stdlib"]


def test_a_step_is_held_until_somebody_has_asked_whether_to_build_it(
    forge: Path,
) -> None:
    ready(forge)

    gap = stp.next_gap(forge)
    assert gap is not None and gap.kind == "unchallenged"
    assert "needs building" in gap.reason

    allowed, reason = fs.writes_allowed(forge)
    assert allowed is False
    assert "lean pass" in reason


def test_the_pass_opens_the_step_without_settling_it(forge: Path) -> None:
    """One does not stand in for the other.

    Deciding a feature is worth building is not deciding how it works, and a
    pass that opened the gate outright would replace the question it exists to
    come before.
    """
    ready(forge)
    step = stp.current(forge)

    asked = fs.ask(forge, "worth building?", affects=ln.marker_for(step.marker))
    fs.answer(forge, asked.id, ln.body("the smaller one", full_ladder(), "because"))

    gap = stp.next_gap(forge)
    assert gap.kind == "undecided", "its own question is still owed"

    decided = fs.ask(forge, "how it works", affects=step.marker)
    fs.answer(forge, decided.id, "# like this\n\n## Why\n\nbecause\n")
    assert stp.next_gap(forge) is None


def test_the_pass_cannot_open_the_gate_it_exists_to_come_before(forge: Path) -> None:
    """The lean marker contains the step marker, and that nearly cost the gate.

    `lean:phase-1.step-1` matches the pattern that reads step decisions out of
    `affects`, so recording the pass counted as deciding the step: the question
    the pass exists to precede was skipped by the pass itself.
    """
    ready(forge)
    step = stp.current(forge)

    asked = fs.ask(forge, "worth building?", affects=ln.marker_for(step.marker))
    fs.answer(forge, asked.id, ln.body("yes", full_ladder(), "because"))

    assert step.marker not in stp.decided_markers(forge)


def test_a_ladder_with_a_rung_missing_is_not_a_ladder() -> None:
    """The failure here is not a wrong answer.

    It is three plausible sentences with two rungs quietly absent, which reads
    as a completed pass in every summary anybody will ever look at.
    """
    partial = [ln.Finding("needed", "yes"), ln.Finding("smallest", "one function")]
    assert set(ln.missing_rungs(partial)) == {"already", "stdlib", "cost"}
    assert ln.missing_rungs(full_ladder()) == []


def test_a_blank_answer_does_not_count_as_a_rung() -> None:
    findings = full_ladder()[:-1] + [ln.Finding("cost", "   ")]
    assert ln.missing_rungs(findings) == ["cost"]


def test_what_the_ladder_found_is_kept_even_when_nothing_changed() -> None:
    """A pass that only leaves a trace when it changes something looks, in the
    history, exactly like a pass that never ran."""
    text = ln.body(
        "as proposed",
        full_ladder(),
        "nothing in the project does this yet",
        their_reason="I want it visible on the first screen",
        instead_of="a settings page for it",
    )

    assert "Before writing it, the ladder said" in text
    for rung in ln.LADDER_KEYS:
        assert rung in text
    assert "In their words" in text
    assert "a settings page for it" in text


def test_the_pass_belongs_to_one_step_and_does_not_cover_the_next(
    forge: Path,
) -> None:
    ready(forge)
    phases = forge / "phases"
    (phases / "1-first.md").write_text(
        "---\nphase: 1\ntitle: First\n---\n\n## Steps\n\n"
        "1. [ ] let a todo be ticked off\n2. [ ] let a todo be deleted\n",
        encoding="utf-8",
    )

    first = stp.current(forge)
    asked = fs.ask(forge, "worth it?", affects=ln.marker_for(first.marker))
    fs.answer(forge, asked.id, ln.body("yes", full_ladder(), "because"))
    decided = fs.ask(forge, "how", affects=first.marker)
    fs.answer(forge, decided.id, "# like this\n\n## Why\n\nbecause\n")

    stp.mark_built(forge, first.phase, first.number)

    gap = stp.next_gap(forge)
    assert gap is not None and gap.kind == "unchallenged", "the second step owes its own"
    assert "deleted" in gap.reason
