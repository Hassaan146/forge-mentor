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


def test_the_sequence_is_the_fixed_set_until_an_answer_opens_more(forge: Path) -> None:
    """A fresh project is asked the fixed set, and it is told how many."""
    assert [q.key for q in ff.sequence(forge)] == [q.key for q in ff.FOUNDATION]
    assert ff.position(forge) == (0, 7)


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
    assert ff.next_question(forge).key == "name", "what it is called comes before what it is built with"

    answer(forge, ff.NAME.question)
    assert ff.next_question(forge).key == "stack"


def test_the_stack_question_names_whole_shapes_not_single_words(forge: Path) -> None:
    """Language, framework and runtime do not separate cleanly.

    Asked one at a time, an answer to the first quietly rules out most answers
    to the next without anyone noticing.
    """
    options = ff.STACK.options
    assert len(options) >= 4

    for option in options:
        assert option.note, f"{option.label} has no consequence stated"
        assert len(option.note) > 40, f"{option.label} is not a detailed option"


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
    project that had not chosen a browser. What replaced it is not "no options"
    but a menu per shape, chosen by what the stack answer settled.
    """
    assert ff.DATA.options == ()
    assert ff.DATA.options_when, "it has menus, they are just not unconditional"


def test_the_storage_menu_follows_the_shape_that_was_chosen() -> None:
    """The whole point of asking the stack first, now visible in the options."""
    browser, _ = ff.DATA.menu({"no-server"})
    local, _ = ff.DATA.menu({"local-only"})
    served, _ = ff.DATA.menu({"server"})

    assert any("browser" in o.label.lower() for o in browser)
    assert not any("browser" in o.label.lower() for o in local)
    assert any("sqlite" in o.label.lower() for o in local)
    assert any("postgres" in o.label.lower() for o in served)


def test_every_menu_is_at_least_three_real_options() -> None:
    """The user's report: "it is giving very limited options".

    A question that arrives with two has usually had its answer picked by
    whoever chose the pair. Checked against every menu in the file, including
    the conditional ones, because the conditional ones are where a shape with
    few answers quietly becomes a false binary.
    """
    import forge_options as fo

    menus = [(q.key, "", q.options) for q in ff.ALL_QUESTIONS if q.options]
    menus += [
        (q.key, fact, options)
        for q in ff.ALL_QUESTIONS
        for fact, options in q.options_when
    ]

    for key, fact, options in menus:
        where = f"{key}{' when ' + fact if fact else ''}"
        assert len(options) >= fo.MIN_OPTIONS, f"{where} offers {len(options)}"
        assert len(options) <= fo.MAX_OPTIONS, f"{where} offers {len(options)}"
        for option in options:
            assert option.note.strip(), f"{where}: {option.label} has no consequence"


def test_an_option_the_project_ruled_out_is_shown_struck_out_not_dropped(
    forge: Path,
) -> None:
    """Shown rather than silently removed, because the exclusion is teaching.

    A user who reads "a second person signs off, ruled out because only one
    person uses this" has learned what the option was for, and it cost no
    question. One who simply never sees it cannot tell the difference between
    an option Forge weighed and one it never thought of.
    """
    menu = ff.menu_for(ff.DONE, facts_known={"single-user"})

    offered = " ".join(label for _letter, label, _note in menu.rows).lower()
    assert "someone else has looked" not in offered

    struck = " ".join(menu.ruled_out_lines()).lower()
    assert "someone else has looked" in struck
    assert "only one person uses this" in struck


def test_a_question_is_never_narrowed_by_its_own_answers(forge: Path) -> None:
    """The delivery question is what settles local-only in the first place.

    Applying that fact to its own menu strikes out four of its five options and
    leaves the one that produced it: the question answers itself and then
    presents the result as a choice.
    """
    menu = ff.menu_for(ff.DELIVERY, facts_known={"local-only", "deployed"})
    assert len(menu.rows) == len(ff.DELIVERY.options)
    assert menu.removed == []


def test_a_menu_narrowed_past_the_floor_is_asked_openly_instead() -> None:
    """A menu of one is not a question, and a traceback is not one either.

    The question is still worth asking, so it is asked in the user's own words
    with the exclusions shown. Raising here would take the tool down and hand
    the model a stack trace in place of something to ask.
    """
    menu = ff.menu_for(ff.IDENTITY, facts_known={"single-user"})

    assert menu.rows == []
    assert menu.removed, "and it says which answers the project ruled out"


def test_a_project_with_no_server_can_still_be_put_somewhere(forge: Path) -> None:
    """Found by running it: the rule meant to widen the menu nearly emptied it.

    A browser app has no server of its own and is still hosted, on static
    hosting, which is the answer built for exactly that shape. Ruling all
    hosting out struck four of the five delivery options and left one.
    """
    menu = ff.menu_for(ff.DELIVERY, facts_known={"no-server", "screens"})

    labels = [label.lower() for _letter, label, _note in menu.rows]
    assert len(menu.rows) >= 3
    assert any("static host" in label for label in labels)


def test_the_sequence_advances_as_questions_are_answered(forge: Path) -> None:
    assert ff.position(forge) == (0, 7)

    answer(forge, ff.INTENT.question)
    answer(forge, ff.NAME.question)
    assert ff.next_question(forge).key == "stack"

    answer(forge, ff.STACK.question)
    assert ff.next_question(forge).key == "data"
    assert ff.position(forge)[0] == 3

    answer(forge, ff.DATA.question)
    assert ff.next_question(forge).key == "people"


def test_a_finished_foundation_reports_nothing_left(forge: Path) -> None:
    while (question := ff.next_question(forge)) is not None:
        answer(forge, question.question)
    assert ff.next_question(forge) is None


def test_deciding_to_deploy_opens_the_questions_deploying_needs(forge: Path) -> None:
    """One answer is not one decision.

    Choosing to put this somewhere else settles nothing about how a change gets
    there, what happens when it falls over, or where the keys live. Those are
    load-bearing and they only exist for a project that deploys, so they are
    opened by the answer rather than sitting in the fixed list being skipped in
    front of everyone else.
    """
    answer(forge, ff.INTENT.question, "a todo app")
    answer(forge, ff.NAME.question, "todo, on my github")
    answer(forge, ff.STACK.question, "C")
    answer(forge, ff.DATA.question, "B")
    answer(forge, ff.PEOPLE.question, "A")

    before = ff.position(forge)[1]
    answer(forge, ff.DELIVERY.question, "A small server I rent")

    opened = [q.key for q in ff.sequence(forge)]
    assert "release" in opened and "failure" in opened and "secrets" in opened
    assert ff.position(forge)[1] > before, "the count moves, and it says so"
    assert ff.next_question(forge).key == "release"


def test_staying_local_never_opens_the_deployment_questions(forge: Path) -> None:
    """The other half of the same rule, and the one the user asked for.

    A question that does not apply was never in the sequence. It is not skipped
    with an apology, and a container is never mentioned as a thing that was
    considered.
    """
    answer(forge, ff.INTENT.question, "a todo app")
    answer(forge, ff.NAME.question, "todo, on my github")
    answer(forge, ff.STACK.question, "A")
    answer(forge, ff.DATA.question, "A")
    answer(forge, ff.PEOPLE.question, "Only me")
    answer(forge, ff.DELIVERY.question, "Only on my machine")

    opened = [q.key for q in ff.sequence(forge)]
    assert "release" not in opened and "secrets" not in opened
    assert "backup" in opened, "what a local project actually risks is asked instead"


def test_the_facts_are_read_back_out_of_the_records(forge: Path) -> None:
    """State is re-read from disk every time, never remembered (decision 019)."""
    answer(forge, ff.INTENT.question, "a todo app")
    answer(forge, ff.STACK.question, "D")

    known = ff.facts(forge)
    assert "cli" in known and "no-screens" in known


def test_the_idea_is_a_description_and_never_a_source_of_facts(forge: Path) -> None:
    """Found by running it, and it had already done damage.

    "A to-do app I can use from my phone and my laptop" was read as local-only,
    because the keyword fallback ran on a question that never had a menu. The
    project had just chosen a hosted service, and Supabase and Neon were struck
    off its database menu for a reason the user would have argued with.
    """
    answer(forge, ff.INTENT.question, "a to-do app I can use from my phone and my laptop")
    assert ff.facts(forge) == set()


def test_an_answer_in_the_users_own_words_still_settles_the_facts(forge: Path) -> None:
    """People do not answer with letters. Rule: take it, and read it."""
    answer(forge, ff.INTENT.question, "a todo app")
    answer(forge, ff.STACK.question, "Command line")
    answer(forge, ff.DELIVERY.question, "only on my machine, nothing hosted")

    assert "local-only" in ff.facts(forge)


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
    answer(forge, ff.NAME.question)
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
    for question in ff.ALL_QUESTIONS:
        for text in (question.question, question.subtitle, question.concept, *question.means):
            assert "\u2014" not in text, f"{question.key}: {text}"
        every = list(question.options) + [
            option for _fact, options in question.options_when for option in options
        ]
        for option in every:
            assert "\u2014" not in option.label, question.key
            assert "\u2014" not in option.note, question.key


def test_the_stack_options_name_shapes_not_technologies() -> None:
    """The user's report: the shape they wanted was on the list, unrecognisably.

    "Browser + small API" and "Python service" described what you would type
    rather than what you would end up with, so "build the API first and add
    screens later" was option B and nobody could see it. A menu that hides an
    answer fails the same way as one that omits it.
    """
    labels = [option.label for option in ff.STACK.options]

    assert labels[:4] == ["Front end only", "Back end only", "Both together", "Command line"]
    for shape in ("front end", "back end"):
        assert any(shape in label.lower() for label in labels)


def test_building_the_api_first_is_visibly_offered() -> None:
    """It is the one that was missing in practice, so it gets its own test."""
    back_end = [o for o in ff.STACK.options if o.label == "Back end only"][0]
    assert "later" in back_end.note, "it has to say the screens come afterwards"


def test_every_question_names_the_concept_underneath_it() -> None:
    """A user who remembers that they picked B has learned nothing.

    The concept is what makes the answer worth something on the next project,
    which is the only part of this that outlives the one being built.
    """
    for question in ff.ALL_QUESTIONS:
        assert question.concept, f"{question.key} teaches a menu, not an idea"
        assert question.concept != question.question, question.key
