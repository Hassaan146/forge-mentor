"""Tests for the foundation questions — decision 033.

The order is the product here. Every question after the stack is asked *inside*
an answer to the stack, so getting that one wrong is not a slightly worse
sequence — it is a question whose options are not knowable yet, which the user
answers anyway because they were asked.

That happened on a real run: the second question offered localStorage,
IndexedDB and a file, every option assuming a browser nobody had chosen. So
these tests pin the order and pin the reason.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import forge_foundation as ff
import forge_state as fs


@pytest.fixture()
def forge(tmp_path: Path) -> Path:
    return fs.init(tmp_path)


def answer(forge: Path, question: str, choice: str = "A") -> None:
    asked = fs.ask(forge, question)
    fs.answer(forge, asked.id, f"# {choice}\n\n## Why\n\nbecause\n")


def test_the_idea_is_asked_first_and_asked_openly(forge: Path) -> None:
    """The user says "I want to make a to-do app" and that is a whole answer.

    No options, on purpose: every option Forge could offer here would already
    assume something about the idea, and a menu narrows what the user was about
    to say. The five questions after it exist so they do not have to think in
    those terms yet.
    """
    first = ff.next_question(forge)

    assert first.options == (), "the only genuinely open question"
    assert "idea" in first.question.lower()

    teaching = " ".join(first.means).lower()
    assert "friend" in teaching, "a description, not a specification"
    assert "complete answer" in teaching, "a one-liner is enough"


def test_the_stack_is_asked_before_anything_it_decides(forge: Path) -> None:
    """Nothing after it can be asked honestly until it is answered."""
    answer(forge, ff.INTENT.question)
    assert ff.next_question(forge).key == "stack"


def test_the_stack_question_names_whole_shapes_not_single_words(forge: Path) -> None:
    """Language, framework and runtime do not separate cleanly.

    Asked one at a time, an answer to the first quietly rules out most answers
    to the next without anyone noticing.
    """
    options = ff.STACK.options
    assert len(options) >= 4

    for _letter, label, consequence in options:
        assert consequence, f"{label} has no consequence stated"
        assert len(consequence) > 40, f"{label} is not a detailed option"


def test_storage_is_never_asked_before_the_stack(forge: Path) -> None:
    """The bug decision 033 was written for.

    A storage question in front of a project with no chosen stack has to guess
    the stack to offer options at all — which is the stack being assumed rather
    than decided, in Forge's own opening move.
    """
    keys = [q.key for q in ff.FOUNDATION]
    assert keys.index("intent") < keys.index("stack") < keys.index("data")


def test_the_data_question_offers_no_fixed_options() -> None:
    """They depend entirely on the stack.

    A fixed list here is exactly what put browser-only storage in front of a
    project that had not chosen a browser.
    """
    assert ff.DATA.options == ()


def test_the_sequence_advances_as_questions_are_answered(forge: Path) -> None:
    assert ff.position(forge) == (0, 6)

    answer(forge, ff.INTENT.question)
    assert ff.next_question(forge).key == "stack"

    answer(forge, ff.STACK.question)
    assert ff.next_question(forge).key == "data"
    assert ff.position(forge)[0] == 2

    answer(forge, ff.DATA.question)
    assert ff.next_question(forge).key == "people"


def test_a_finished_foundation_reports_nothing_left(forge: Path) -> None:
    for question in ff.FOUNDATION:
        answer(forge, question.question)
    assert ff.next_question(forge) is None


def test_an_unrelated_decision_does_not_count_as_a_foundation_answer(
    forge: Path,
) -> None:
    """Projects record other decisions in between; the numbering is shared."""
    answer(forge, "should this helper be called parse_row")
    assert ff.next_question(forge).key == "intent"
    assert ff.position(forge)[0] == 0


def test_questions_that_do_not_apply_are_skipped_not_invented(forge: Path) -> None:
    """A single-file script has no delivery question worth asking."""
    answer(forge, ff.INTENT.question)
    answer(forge, ff.STACK.question)
    answer(forge, ff.DATA.question)

    nxt = ff.next_question(forge, skip={"cli-single-user"})
    assert nxt.key == "done", "people and delivery are not manufactured"


def test_every_question_teaches_before_it_asks(forge: Path) -> None:
    """Rule R1 and the teaching skill: the concept comes before the question."""
    for question in ff.FOUNDATION:
        assert question.means, f"{question.key} asks without explaining"
        assert question.subtitle, f"{question.key} does not say what it decides"


def test_no_question_teaches_for_longer_than_the_cap() -> None:
    """Rule R10, checked at the source rather than only at the renderer.

    The renderer truncates, so a question with eleven lines of teaching would
    still look fine on screen while silently losing nine of them. Better that
    the text is short than that it is cut.
    """
    import forge_ui as ui

    for question in ff.FOUNDATION:
        assert len(question.means) <= ui.MAX_MEANS_LINES, (
            f"{question.key} teaches in {len(question.means)} lines"
        )


def test_nothing_the_user_reads_uses_an_em_dash() -> None:
    """The user asked for none, and that covers what Forge prints."""
    for question in ff.FOUNDATION:
        for text in (question.question, question.subtitle, *question.means):
            assert "\u2014" not in text, f"{question.key}: {text}"
        for _letter, label, note in question.options:
            assert "\u2014" not in label and "\u2014" not in note, question.key
