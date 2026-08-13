"""Tests for the questions a subject owes before it is built.

The gap these close was reported as a final check: *"you have to ask me about
the database, then how I want to configure it, then whether I want to deploy,
whether I want it orchestrated. I want to figure out whether I have to use
Supabase or something else."*

None of that could happen. The whole product held twelve questions, all of them
in the foundation, and everything after it was written by the planner in the
moment. A step called "store the todos" could be asked one question about it,
or none worth the name, and a database would be chosen by whichever model was
writing that turn.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import forge_foundation as ff
import forge_state as fs
from conftest import pass_lean
import forge_steps as stp
import forge_topics as tp


@pytest.fixture()
def forge(tmp_path: Path) -> Path:
    return fs.init(tmp_path)


def answer(forge: Path, question: str, choice: str = "A") -> None:
    asked = fs.ask(forge, question)
    fs.answer(forge, asked.id, f"# {choice}\n\n## Why\n\nbecause\n")


def plan(forge: Path, step: str, title: str = "First") -> None:
    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "1-first.md").write_text(
        f"---\nphase: 1\ntitle: {title}\n---\n\n## Steps\n\n1. [ ] {step}\n",
        encoding="utf-8",
    )
    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# yes\n\n## Why\n\nlooks right\n")


# ==========================================================================
# recognising the subject
# ==========================================================================


def test_a_step_that_stores_something_is_a_database_step(forge: Path) -> None:
    assert [t.key for t in tp.topics_in("store the todos in a database")] == ["database"]
    assert [t.key for t in tp.topics_in("add a migration for the users table")] == ["database"]


def test_a_step_that_ships_is_a_deployment_step(forge: Path) -> None:
    keys = [t.key for t in tp.topics_in("deploy the app with docker compose")]
    assert "deploy" in keys


def test_a_step_about_nothing_in_particular_owes_nothing(forge: Path) -> None:
    assert tp.topics_in("write the readme") == []
    assert tp.owed(forge, "write the readme") == []


def test_a_word_inside_another_word_is_not_a_subject(forge: Path) -> None:
    """"Restoring" is not "storing", and "db" is inside a hundred words.

    Matched whole, or a step about wording would demand five database
    decisions and the gate would become the thing people learn to override.
    """
    assert tp.topics_in("restoring the previous wording") == []


# ==========================================================================
# what the subject owes
# ==========================================================================


def test_the_database_is_asked_properly_or_not_at_all(forge: Path) -> None:
    """The user's list, in code: which one, where it runs, how it changes."""
    owed = [q.key for q in tp.owed(forge, "store the todos in a database")]

    assert owed[:3] == ["db-choice", "db-where", "db-shape"]
    assert "db-access" in owed and "db-testdata" in owed


def test_the_database_options_are_named_products_not_categories(forge: Path) -> None:
    """Rule R2, and the user asked for it by name: Supabase or something else.

    Decision 041 made the *stack* question name shapes rather than
    technologies, on purpose. That was about the first question, where naming a
    product assumes the shape. By the time a step is storing something, the
    shape is decided and a category is no help.
    """
    labels = " ".join(o.label for o in tp.DB_CHOICE.options).lower()

    for named in ("postgres", "supabase", "neon", "sqlite", "mysql", "mongodb"):
        assert named in labels, f"{named} is not offered"


def test_deploying_asks_about_orchestration_by_name(forge: Path) -> None:
    owed = [q.key for q in tp.owed(forge, "deploy the app")]

    assert "deploy-parts" in owed
    assert "deploy-orchestration" in owed
    assert "deploy-rollback" in owed

    labels = " ".join(o.label for o in tp.DEPLOY_ORCHESTRATION.options).lower()
    for named in ("compose", "kubernetes", "service manager"):
        assert named in labels


def test_every_topic_question_explains_why_it_matters() -> None:
    """The ones with the worst consequences sound the most administrative.

    "Where does configuration live" reads like paperwork until the day the key
    is in the repository, so the consequence is on screen with a bar down the
    side rather than left for the user to infer.
    """
    for question in tp.ALL_QUESTIONS:
        assert question.concept, f"{question.key} names no concept"
        assert question.matters, f"{question.key} does not say what it costs"
        assert question.means, f"{question.key} asks without teaching"


def test_every_topic_menu_meets_the_option_floor() -> None:
    import forge_options as fo

    for question in tp.ALL_QUESTIONS:
        if not question.options:
            continue
        assert len(question.options) >= fo.MIN_OPTIONS, question.key
        assert len(question.options) <= fo.MAX_OPTIONS, question.key
        for option in question.options:
            assert option.note.strip(), f"{question.key}: {option.label}"


def test_nothing_a_topic_prints_uses_an_em_dash() -> None:
    for question in tp.ALL_QUESTIONS:
        for text in (question.question, question.subtitle, question.concept,
                     question.matters, *question.means):
            assert "—" not in text, f"{question.key}: {text}"
        for option in question.options:
            assert "—" not in option.label and "—" not in option.note, question.key


def test_a_subject_is_asked_once_per_project_not_once_per_step(forge: Path) -> None:
    """Which database is a project question that a step is merely first to need.

    Asking it again at step nine would be the failure this product exists to
    prevent, performed by the product.
    """
    for question in tp.BY_KEY["database"].questions:
        answer(forge, question.question)

    assert tp.owed(forge, "store the todos in a database") == []


def test_a_question_the_project_ruled_out_is_not_owed(forge: Path) -> None:
    """A command-line tool for one person is not asked about permissions."""
    answer(forge, ff.STACK.question, "Command line")

    owed = [q.key for q in tp.owed(forge, "add a login")]
    assert "permissions" not in owed


# ==========================================================================
# the gate
# ==========================================================================


def test_code_for_a_database_step_is_blocked_until_the_database_is_decided(
    forge: Path,
) -> None:
    """The whole point. Not advice in a brief: the write is refused.

    Every rule this repository put in a brief was eventually skipped by a model
    in a hurry, and nobody noticed, because a skipped question is invisible in
    a way a wrong answer is not.
    """
    while (question := ff.next_question(forge)) is not None:
        answer(forge, question.question)
    plan(forge, "store the todos in a database")

    gap = stp.next_gap(forge)
    assert gap is not None
    assert gap.kind == "unasked"
    assert gap.question == "db-choice"
    assert "Which database" in gap.reason

    allowed, reason = fs.writes_allowed(forge)
    assert allowed is False
    assert "Which database" in reason


def test_the_step_opens_once_its_subject_has_been_answered(forge: Path) -> None:
    while (question := ff.next_question(forge)) is not None:
        answer(forge, question.question)
    plan(forge, "store the todos in a database")

    for question in tp.BY_KEY["database"].questions:
        answer(forge, question.question)

    # The subject is settled, so the gate moves on. One does not stand in
    # for another: the subject, then whether it is worth building, then how.
    assert stp.next_gap(forge).kind == "unchallenged"
    pass_lean(forge)
    gap = stp.next_gap(forge)
    assert gap.kind == "undecided"

    pass_lean(forge)
    asked = fs.ask(forge, "phase 1 step 1", affects="phase-1.step-1")
    fs.answer(forge, asked.id, "# yes\n\n## Why\n\nbecause\n")
    assert stp.next_gap(forge) is None


def test_a_hosted_project_is_offered_the_hosted_databases(forge: Path) -> None:
    """The named ones the user asked for, on a project that can use them."""
    answer(forge, ff.INTENT.question, "a to-do app for my phone and my laptop")
    answer(forge, ff.STACK.question, "Both together")
    answer(forge, ff.DELIVERY.question, "A service that runs it for me")

    menu = ff.menu_for(tp.DB_CHOICE, facts_known=ff.facts(forge))
    labels = " ".join(label for _letter, label, _note in menu.rows).lower()

    assert "supabase" in labels and "neon" in labels
    assert menu.removed == []


def test_a_laptop_project_is_not_offered_a_hosted_database(forge: Path) -> None:
    answer(forge, ff.INTENT.question, "a to-do app")
    answer(forge, ff.STACK.question, "Both together")
    answer(forge, ff.DELIVERY.question, "Only on my machine")

    menu = ff.menu_for(tp.DB_CHOICE, facts_known=ff.facts(forge))
    labels = " ".join(label for _letter, label, _note in menu.rows).lower()

    assert "supabase" not in labels
    assert "postgres you run yourself" in labels
    assert any("Supabase" in line for line in menu.ruled_out_lines())


def test_a_step_that_touches_nothing_is_not_held_up(forge: Path) -> None:
    """A gate that fires on everything is one people learn to type past."""
    while (question := ff.next_question(forge)) is not None:
        answer(forge, question.question)
    plan(forge, "write the readme")
    pass_lean(forge)

    gap = stp.next_gap(forge)
    assert gap.kind == "undecided", "its own question, and nothing else"
