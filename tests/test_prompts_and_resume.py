"""Tests for prompts.md and for resuming — Phase 10.

Two programme requirements meet here.

**prompts.md** has to be a record rather than a recollection. Written by hand at
the end it becomes whatever the author remembers, tidied — and the first thing
that goes missing is the question whose answer turned out wrong. Generated from
the records, those survive, so the tests are mostly about what it refuses to
drop.

**Resuming** is the promise decision 011 made: the repository is the memory.
The way to test that is not to check a function returns the right value but to
throw the session away — build state, forget everything, read it back from disk
in a fresh process state, and confirm the work lands on the same step.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import forge_pipeline as pl
import forge_prompts as fp
import forge_state as fs


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    fs.init(tmp_path)
    return tmp_path


@pytest.fixture()
def forge(project: Path) -> Path:
    return project / fs.FORGE_DIR


def decide(forge: Path, question: str, choice: str, why: str, options=None, by="user") -> None:
    asked = fs.ask(forge, question)
    body = [f"# {choice}", ""]
    if options:
        body += ["**Options considered**", ""] + [f"- {o}" for o in options] + [""]
        body += [f"**Recommended:** {options[0]} · **Decided:** {choice}", ""]
    body += ["## Why", "", why, ""]
    fs.answer(forge, asked.id, "\n".join(body), decided_by=by)


# --------------------------------------------------------------------------
# prompts.md — a record, not a recollection
# --------------------------------------------------------------------------


def test_the_question_and_the_answer_are_both_logged(project: Path, forge: Path) -> None:
    decide(forge, "how people log in", "a login service", "I don't want to keep passwords safe")
    text = fp.render(__import__("forge_explain").collect(forge))

    assert "how people log in" in text
    assert "a login service" in text
    assert "I don't want to keep passwords safe" in text


def test_the_options_that_were_offered_are_logged(project: Path, forge: Path) -> None:
    """A log showing only the answer hides that there was a choice at all."""
    decide(forge, "which backend", "FastAPI", "small", ["FastAPI", "Django", "Flask"])
    text = fp.render(__import__("forge_explain").collect(forge))

    assert "Options put to the user" in text
    for option in ("FastAPI", "Django", "Flask"):
        assert option in text


def test_the_log_says_which_model_did_what(project: Path, forge: Path) -> None:
    """Decision 002 routes work across models; one model in the log would lie."""
    decide(forge, "which backend", "FastAPI", "small")
    text = fp.render(__import__("forge_explain").collect(forge))

    assert "claude-fable-5" in text and "claude-opus-4-8" in text
    assert "claude-haiku-4-5" in text


def test_the_models_come_from_the_same_table_as_everything_else() -> None:
    """Decision 029: one fact, however many files hold it."""
    import forge_skills as sk

    assert fp._STAGE_MODEL["the code"] == sk.AGENTS_BY_NAME["builder"].model


def test_what_forge_answered_itself_is_not_logged_as_the_users(
    project: Path, forge: Path
) -> None:
    """Auto's records are not evidence of what the user understands."""
    decide(forge, "helper name", "parse_row", "reads better", by="forge")
    text = fp.render(__import__("forge_explain").collect(forge))

    assert "not chosen by the user" in text


def test_the_log_lands_where_a_reader_expects_a_project_file(
    project: Path, forge: Path
) -> None:
    decide(forge, "which backend", "FastAPI", "small")
    path = fp.write(project, forge, "teamtasks")

    assert path == project / "prompts.md"
    assert path.parent == project, "not buried inside .forge/"


def test_a_project_with_no_decisions_still_produces_a_valid_log(
    project: Path, forge: Path
) -> None:
    text = fp.render([])
    assert "no prompts to log" in text
    assert text.startswith("---"), "the labelled header is always there"


# --------------------------------------------------------------------------
# resuming — decision 011, the repository is the memory
# --------------------------------------------------------------------------


def test_an_interrupted_session_resumes_on_the_same_step(
    project: Path, forge: Path
) -> None:
    """The resilience check the programme asks for.

    Nothing is carried over in memory: the modules are reloaded, which is as
    close to a new process as a test gets. If any part of the pipeline kept
    state in a variable rather than on disk, this is where it shows.
    """
    (forge / pl.CHALLENGED_MARKER).write_text("# challenged\n", encoding="utf-8")
    (forge / "phases").mkdir(exist_ok=True)
    (forge / "phases" / "1-x.md").write_text("---\nphase: 1\n---\n", encoding="utf-8")
    pl.set_mode(forge, "auto")
    fs.ask(forge, "which database should this use")

    before = pl.next_step(forge).as_dict()

    # Throw the session away.
    importlib.reload(fs)
    importlib.reload(pl)

    after = pl.next_step(forge).as_dict()
    assert after == before
    assert after["asks_user"] is True, "a blast-radius question survives the restart"
    assert after["mode"] if "mode" in after else True


def test_the_mode_survives_an_interruption(project: Path, forge: Path) -> None:
    pl.set_mode(forge, "accept-edits")
    importlib.reload(pl)
    assert pl.mode(forge) is pl.Mode.ACCEPT_EDITS


def test_a_half_written_answer_leaves_the_question_open(
    project: Path, forge: Path
) -> None:
    """A crash between asking and answering must not lose the question.

    The dangerous outcome is not the lost answer — it is a question silently
    marked decided, because the governor would then let code past a decision
    nobody made.
    """
    asked = fs.ask(forge, "how people log in")
    assert fs.open_question(forge) is not None

    importlib.reload(fs)
    still_open = fs.open_question(forge)
    assert still_open is not None
    assert still_open.id == asked.id


def test_writes_stay_blocked_across_a_restart(project: Path, forge: Path) -> None:
    """If the block lived in memory, a crash would be a way through the governor."""
    fs.ask(forge, "how people log in")
    assert fs.writes_allowed(forge)[0] is False

    importlib.reload(fs)
    assert fs.writes_allowed(forge)[0] is False


def test_the_gate_count_survives_a_restart(project: Path, forge: Path) -> None:
    """Decision 009's three-strike rule cannot be reset by restarting."""
    progress = fs.Progress.read(forge)
    progress.gate_attempts = 2
    progress.write(forge)

    importlib.reload(fs)
    assert fs.Progress.read(forge).gate_attempts == 2


# --------------------------------------------------------------------------
# credentials never reach the project root — PR #8
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "postgres://admin:hunter2@db.example.com/app",
        "we used sk-abcdefghij0123456789XYZ for it",
        "API_KEY=supersecretvalue",
        "AKIA1234567890ABCDEF",
        "password: correcthorsebattery",
    ],
)
def test_credential_shaped_text_never_reaches_prompts_md(text: str) -> None:
    """The reasoning is free text typed into a terminal, and people paste keys.

    prompts.md lands in the project root of a repository that may be public,
    so it is the last place that should carry one through verbatim.
    """
    out, hits = fp.redact(text)
    assert hits >= 1
    assert fp.REDACTED in out


@pytest.mark.parametrize(
    "text",
    [
        "because it is small and agent-centric, like FastAPI",
        "I don't want to be responsible for keeping passwords safe",
        "https://example.com/docs",
    ],
)
def test_ordinary_reasoning_is_left_alone(text: str) -> None:
    """Over-redacting is preferred, but not to the point of erasing the reason."""
    out, hits = fp.redact(text)
    assert hits == 0
    assert out == text


def test_the_patterns_are_real_escapes_not_control_bytes() -> None:
    """A regression guard for a bug that was invisible in every view of the file.

    `\b` was written as an actual backspace byte, so every pattern silently
    required a backspace to match and the redaction did nothing at all. The
    file looked correct in editors, in diffs and in review.
    """
    for pattern in fp._SECRET_SHAPES:
        assert "\x08" not in pattern.pattern, "a literal backspace is never intended"


def test_a_redacted_log_says_so(project: Path, forge: Path) -> None:
    """Silent redaction would leave the reader trusting a doctored record."""
    decide(forge, "which database", "hosted Postgres", "connect via postgres://u:p@h/db")
    text = fp.render(__import__("forge_explain").collect(forge))

    assert fp.REDACTED in text
    assert "were blanked" in text
    assert "in its decision record" in text, "the reader is told where the original is"
