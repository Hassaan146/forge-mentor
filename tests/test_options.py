"""Tests for the option rules — what a menu has to be before a user sees it.

The defect these exist for was reported in one sentence: "it is giving very
limited options". Underneath it, nothing generated options at all. One question
in the whole product carried a menu; every other one was improvised in the
moment against no rule, and improvisation with no rule produced "Docker, or run
it locally" for a project that had already said it runs on one laptop.

So two rules, and both are checked in code rather than asked for in a brief.
A brief is not read back.
"""

from __future__ import annotations

import pytest

import forge_options as fo


def option(label: str, note: str = "a real cost", **kw) -> fo.Option:
    return fo.Option(label, note, **kw)


def test_two_options_is_a_false_binary() -> None:
    problems = fo.problems([option("Docker"), option("Locally")])
    assert any("at least 3" in p for p in problems)


def test_an_option_with_no_consequence_is_a_word() -> None:
    problems = fo.problems([option("Postgres", ""), option("SQLite"), option("MySQL")])
    assert any("no consequence line" in p for p in problems)


def test_a_menu_nobody_finishes_reading_is_also_wrong() -> None:
    problems = fo.problems([option(f"choice {n}") for n in range(9)])
    assert any("more than anyone reads" in p for p in problems)


def test_the_same_option_twice_is_caught() -> None:
    problems = fo.problems([option("SQLite"), option("sqlite"), option("Postgres")])
    assert any("listed twice" in p for p in problems)


def test_an_option_that_repeats_the_question_is_not_an_answer() -> None:
    problems = fo.problems(
        [option("which database"), option("SQLite"), option("Postgres")],
        question="Which database?",
    )
    assert any("repeats the question" in p for p in problems)


def test_a_good_menu_raises_nothing() -> None:
    fo.check([option("SQLite"), option("Postgres"), option("A file")])


def test_what_the_project_ruled_out_is_returned_rather_than_dropped() -> None:
    """Silently removing an option teaches nothing.

    The user cannot tell the difference between one Forge weighed and one it
    never thought of, and the difference is the whole lesson.
    """
    offered, removed = fo.rule_out(
        [
            option("A container", needs=("container",)),
            option("A local script"),
            option("A scheduled task"),
        ],
        {"local-only"},
    )

    assert [o.label for o in offered] == ["A local script", "A scheduled task"]
    assert removed[0].option.label == "A container"
    assert "runs only on your own machine" in removed[0].line()


def test_letters_are_assigned_after_the_ruling_out_not_before() -> None:
    """Otherwise the menu shows A, C, D and the user answers B for something
    that is not on screen."""
    rows, _removed = fo.offer(
        [
            option("A container", needs=("container",)),
            option("A local script"),
            option("A scheduled task"),
            option("Nothing, run it by hand"),
        ],
        {"local-only"},
    )

    assert [row[0] for row in rows] == ["A", "B", "C"]


def test_narrowing_to_a_false_binary_is_still_refused() -> None:
    """The count is checked after the exclusions, because that is the menu the
    user actually sees."""
    with pytest.raises(fo.OptionError):
        fo.offer(
            [
                option("A container", needs=("container",)),
                option("A hosted service", needs=("hosting",)),
                option("A local script"),
            ],
            {"local-only"},
        )


def test_an_option_written_as_prose_is_still_checked_against_the_facts() -> None:
    """Per-step options arrive as text with no tags, and those are the ones the
    planner improvises."""
    fact, why = fo.contradicted("Run it in Docker so it is the same everywhere", {"local-only"})
    assert fact == "local-only"
    assert "your own machine" in why


def test_an_innocent_word_is_not_read_as_a_container() -> None:
    """An image upload is not a container, and a rule that says otherwise
    removes an option the user wanted."""
    assert fo.contradicted("Let people upload an image", {"local-only"}) == ("", "")


def test_nothing_is_contradicted_when_nothing_is_known_yet() -> None:
    assert fo.contradicted("Run it in Docker", set()) == ("", "")


def test_an_option_that_counts_files_is_not_an_option() -> None:
    """"Dont tell me how many files to add, just tell what functionality."

    The size question invites it: "how big should this step be" is answered in
    the model's head as a number of files, and what reached a real screen was
    "A Three files / B Five files" — a layout for code the user had not seen.
    """
    counted = [
        fo.Option("Three files", "db.py, the .sql file, a test"),
        fo.Option("Five files", "the same, split into three modules"),
        fo.Option("Skip it", "fold the table into step 3"),
    ]
    found = fo.problems(counted, "How big should step 2 be?")

    assert any("quantity, not a thing" in problem for problem in found)
    assert sum("quantity, not a thing" in problem for problem in found) == 2

    named = [
        fo.Option("The table and the code that creates it", "three files, one to open"),
        fo.Option("The table, with the layout split up front", "five files, three imports"),
        fo.Option("Skip it", "fold the table into step 3"),
    ]
    assert fo.problems(named, "How big should step 2 be?") == []


def test_a_label_that_names_the_thing_and_counts_it_is_fine() -> None:
    """The rule is about labels that are *only* a count, not any count at all."""
    assert fo.problems(
        [
            fo.Option("One table, one model, one migration", "one file to open"),
            fo.Option("A table per feature", "more files, less coupling"),
            fo.Option("No table yet", "nothing is stored until step 3"),
        ],
        "How big should step 2 be?",
    ) == []
