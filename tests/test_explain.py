"""Tests for Code Explained — Phase 8.

The document answers "why is it like this", which is the question the user gets
asked and the one the code cannot answer for itself. So these tests are mostly
about what it refuses to lose: the options that were turned down, the user's
own reasoning in their own words, and which decisions they did not actually
make.

That last one matters because of decision 030. Auto produces records nobody
chose, and the mitigation accepted there was that the two never get confused
when read back — a promise that only holds if this document keeps them apart.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import forge_explain as ex
import forge_state as fs


@pytest.fixture()
def forge(tmp_path: Path) -> Path:
    return fs.init(tmp_path)


def decide(
    forge: Path,
    question: str,
    choice: str,
    reasoning: str,
    options: list[str] | None = None,
    decided_by: str = "user",
) -> int:
    """Record a decision the way the server does, so the parsing is real."""
    asked = fs.ask(forge, question)
    body = [f"# {choice}", ""]
    if options:
        body += ["**Options considered**", ""] + [f"- {o}" for o in options] + [""]
        body += [f"**Recommended:** {options[0]} · **Decided:** {choice}", ""]
    body += ["## Why", "", reasoning, ""]
    fs.answer(forge, asked.id, "\n".join(body), decided_by=decided_by)
    return asked.id


# --------------------------------------------------------------------------
# what the document has to keep
# --------------------------------------------------------------------------


def test_the_reasoning_is_the_users_own_words(forge: Path) -> None:
    """A tidier summary written afterwards is a reconstruction, not the reason."""
    decide(
        forge,
        "how people log in",
        "a login service",
        "I don't want to be responsible for keeping passwords safe.",
        ["build it ourselves", "a login service"],
    )
    text = ex.render(ex.collect(forge))
    assert "I don't want to be responsible for keeping passwords safe." in text


def test_the_options_that_were_turned_down_survive(forge: Path) -> None:
    """"Why not the other thing" is most of what a reader is really asking."""
    decide(
        forge,
        "which backend",
        "FastAPI",
        "small and agent-centric",
        ["FastAPI", "Django", "Flask"],
    )
    text = ex.render(ex.collect(forge))

    assert "Django" in text and "Flask" in text
    assert "Also considered" in text


def test_the_option_that_was_taken_is_not_listed_as_rejected(forge: Path) -> None:
    decide(forge, "which backend", "FastAPI", "because", ["FastAPI", "Django"])
    rejected = ex.render(ex.collect(forge)).split("Also considered:")[1].split("\n")[0]
    assert "Django" in rejected
    assert "FastAPI" not in rejected


def test_a_free_text_answer_still_matches_its_option(forge: Path) -> None:
    """The user answers in their own words — that is the point of asking that way."""
    assert ex._is_chosen("a login service", "use a login service") is True
    assert ex._is_chosen("build it ourselves", "use a login service") is False


def test_decisions_read_in_the_order_they_were_made(forge: Path) -> None:
    """Each was decided knowing the ones above it, which the file listing loses."""
    decide(forge, "first question", "A", "because")
    decide(forge, "second question", "B", "because")

    text = ex.render(ex.collect(forge))
    assert text.index("first question") < text.index("second question")


# --------------------------------------------------------------------------
# decisions the user did not make — decision 030
# --------------------------------------------------------------------------


def test_what_forge_settled_itself_is_marked_as_such(forge: Path) -> None:
    """Otherwise Auto's records read as the user's understanding, which they are not."""
    decide(forge, "helper name", "parse_row", "reads better", decided_by="forge")
    text = ex.render(ex.collect(forge))

    assert "settled by Forge" in text


def test_a_users_own_decision_carries_no_such_mark(forge: Path) -> None:
    decide(forge, "which backend", "FastAPI", "because", decided_by="user")
    assert "settled by Forge" not in ex.render(ex.collect(forge))


def test_the_header_counts_what_the_user_actually_chose(forge: Path) -> None:
    decide(forge, "which backend", "FastAPI", "because", decided_by="user")
    decide(forge, "helper name", "parse_row", "because", decided_by="forge")

    text = ex.render(ex.collect(forge))
    assert "decisions: 2" in text
    assert "chosen_by_you: 1" in text


# --------------------------------------------------------------------------
# the edges
# --------------------------------------------------------------------------


def test_an_open_question_is_not_yet_part_of_the_account(forge: Path) -> None:
    fs.ask(forge, "still thinking about this")
    assert ex.collect(forge) == []


def test_a_project_with_no_decisions_explains_that_rather_than_nothing(forge: Path) -> None:
    text = ex.render([])
    assert "nothing to explain" in text
    assert "fills itself in" in text, "the reader is told where it comes from"


def test_a_hand_written_record_from_before_the_writer_existed_still_reads(
    forge: Path,
) -> None:
    """Phase 1's records were written by hand. They have to keep working."""
    folder = forge / fs.DECISIONS
    folder.mkdir(exist_ok=True)
    (folder / "001-by-hand.md").write_text(
        fs.render_header(
            {"id": "001", "question": "how notes are saved", "status": "decided",
             "date": "2026-07-31", "decided_by": "user"}
        )
        + "# Both readable, with a labelled header\n\n"
        "**Options considered**\n\n- one file\n- two files\n\n"
        "**Recommended:** two files · **Decided:** Both readable\n\n"
        "## Why\n\nA person has to be able to read it.\n",
        encoding="utf-8",
    )

    entries = ex.collect(forge)
    assert len(entries) == 1
    assert entries[0].choice == "Both readable"
    assert "A person has to be able to read it." in entries[0].why


def test_a_damaged_record_does_not_take_the_document_down(forge: Path) -> None:
    """One unreadable file must not cost the reader every other explanation."""
    decide(forge, "which backend", "FastAPI", "because")
    folder = forge / fs.DECISIONS
    (folder / "002-broken.md").write_text("no header at all\n", encoding="utf-8")

    text = ex.render(ex.collect(forge))
    assert "FastAPI" in text


def test_the_document_is_written_where_it_gets_committed(forge: Path) -> None:
    """Decision 016: it travels with the code, not with the session."""
    decide(forge, "which backend", "FastAPI", "because")
    path = ex.write(forge, "teamtasks")

    assert path == forge / ex.EXPLAINED_FILE
    assert "teamtasks" in path.read_text(encoding="utf-8")


def test_the_report_says_who_decided_what(forge: Path) -> None:
    decide(forge, "which backend", "FastAPI", "because", decided_by="user")
    decide(forge, "helper name", "parse_row", "because", decided_by="forge")

    result = ex.report(forge)
    assert result["chosen_by_you"] == 1
    assert result["settled_by_forge"] == 1
