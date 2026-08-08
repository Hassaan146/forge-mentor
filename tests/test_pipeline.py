"""Tests for the pipeline — Phase 8, the loop the whole thing exists to run.

Two properties carry most of the weight here.

**The stage is read, not decided.** It comes from what is on disk, so two
sessions looking at the same notes reach the same answer and a session
resuming on another machine lands where the last one stopped. A stage that
depended on conversation history would resume wrong, silently.

**Auto only decides furniture.** Decision 030 lets Auto settle small things and
record them, and forbids it from touching anything other work will be built on.
The two mistakes are not the same size — a furniture question wrongly asked
costs one question, a load-bearing question wrongly assumed costs the user a
decision they cannot defend — so the classifier leans towards asking, and these
tests pin that lean.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import forge_pipeline as pl
import forge_state as fs


@pytest.fixture()
def forge(tmp_path: Path) -> Path:
    return fs.init(tmp_path)


def started(forge: Path) -> None:
    """At least one decision recorded — a project that has actually begun.

    A fresh directory now reports INTERROGATION rather than CHALLENGE: there is
    no plan to challenge before anything has been decided. So every test past
    the first question has to have started.
    """
    asked = fs.ask(forge, "which backend")
    fs.answer(forge, asked.id, "# FastAPI\n\n## Why\n\nsmall\n")


def challenge(forge: Path) -> None:
    started(forge)
    (forge / pl.CHALLENGED_MARKER).write_text("# challenged\n", encoding="utf-8")


def plan(forge: Path) -> None:
    (forge / "phases").mkdir(exist_ok=True)
    (forge / "phases" / "1-first.md").write_text("---\nphase: 1\n---\n", encoding="utf-8")


def ready_to_build(forge: Path) -> None:
    challenge(forge)
    plan(forge)


# --------------------------------------------------------------------------
# the mode
# --------------------------------------------------------------------------


def test_a_project_starts_in_the_mode_that_asks_most(forge: Path) -> None:
    """Nobody is opted into Forge deciding things for them."""
    assert pl.mode(forge) is pl.Mode.PIPELINE


def test_the_mode_survives_the_session(forge: Path) -> None:
    """Decision 011: state lives in the repository, not in a running process."""
    pl.set_mode(forge, "auto")
    assert pl.mode(forge) is pl.Mode.AUTO


def test_an_unreadable_mode_falls_back_to_the_safest_one(forge: Path) -> None:
    (forge / fs.SETTINGS).write_text(
        fs.render_header({"type": "settings", "mode": "turbo"}) + "# x\n", encoding="utf-8"
    )
    assert pl.mode(forge) is pl.Mode.PIPELINE


def test_a_damaged_settings_file_does_not_stop_work(forge: Path) -> None:
    (forge / fs.SETTINGS).write_text("no header here\n", encoding="utf-8")
    assert pl.mode(forge) is pl.Mode.PIPELINE


def test_setting_an_unknown_mode_lists_the_real_ones(forge: Path) -> None:
    with pytest.raises(pl.PipelineError, match="pipeline"):
        pl.set_mode(forge, "yolo")


def test_changing_the_mode_keeps_the_rest_of_the_settings(forge: Path) -> None:
    (forge / fs.SETTINGS).write_text(
        fs.render_header({"type": "settings", "token_budget": "500000"}) + "# Settings\n",
        encoding="utf-8",
    )
    pl.set_mode(forge, "auto")

    header, _ = fs.parse_header((forge / fs.SETTINGS).read_text(encoding="utf-8"), forge)
    assert header["mode"] == "auto"
    assert header["token_budget"] == "500000", "an unrelated setting is not lost"


# --------------------------------------------------------------------------
# blast radius — what Auto may and may not settle
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "How should people log in?",
        "Which database should this use?",
        "What framework are we building on?",
        "How should the API contract be shaped?",
        "Where do the secrets live?",
        "How are payments handled?",
        "What is the error handling approach?",
        "How should we deploy this?",
    ],
)
def test_auto_never_settles_a_decision_others_build_on(question: str) -> None:
    assert pl.is_load_bearing(question) is True
    assert pl.should_ask(question, pl.Mode.AUTO) is True


@pytest.mark.parametrize(
    "question",
    [
        "Should this helper be called parse_row or read_row?",
        "Which file should this small function live in?",
        "Do you want the list sorted newest first?",
    ],
)
def test_auto_settles_the_furniture(question: str) -> None:
    assert pl.is_load_bearing(question) is False
    assert pl.should_ask(question, pl.Mode.AUTO) is False


@pytest.mark.parametrize("mode", [pl.Mode.PIPELINE, pl.Mode.ACCEPT_EDITS])
def test_the_other_modes_ask_about_everything(mode: pl.Mode) -> None:
    """Only Auto changes who answers. The other two differ in writing, not asking."""
    assert pl.should_ask("Should this be called x or y?", mode) is True


def test_an_empty_question_is_not_treated_as_furniture() -> None:
    """Better one needless question than a silent decision.

    This asserted the opposite of its own name — `should_ask("") is False`,
    which is Auto settling a question it could not read. There is nothing in a
    blank question to classify, and "I cannot tell" must not resolve to "Forge
    decides".
    """
    assert pl.should_ask("", pl.Mode.AUTO) is True
    assert pl.should_ask("   ", pl.Mode.AUTO) is True
    assert pl.is_load_bearing("") is False, "blank is not load-bearing, it is unreadable"


# --------------------------------------------------------------------------
# the stage comes from disk
# --------------------------------------------------------------------------


def test_an_open_question_stops_everything(forge: Path) -> None:
    """The governor rule, stated as a plan rather than as a refusal."""
    ready_to_build(forge)
    fs.ask(forge, "how people log in")

    step = pl.next_step(forge)
    assert step.blocked is True
    assert step.asks_user is True
    assert "how people log in" in step.question


def test_in_auto_a_small_question_is_settled_not_asked(forge: Path) -> None:
    ready_to_build(forge)
    pl.set_mode(forge, "auto")
    fs.ask(forge, "should this helper be called parse_row")

    step = pl.next_step(forge)
    assert step.asks_user is False
    assert "settle and record" in step.why


def test_in_auto_a_big_question_is_still_asked(forge: Path) -> None:
    ready_to_build(forge)
    pl.set_mode(forge, "auto")
    fs.ask(forge, "which database should this use")

    assert pl.next_step(forge).asks_user is True


def test_a_project_that_has_not_started_is_asked_the_first_question(forge: Path) -> None:
    """There is no plan to challenge before anything has been decided.

    A fresh directory used to fall straight through to CHALLENGE, and
    INTERROGATION was only reachable once a question was already open — so the
    stage that opens the first question could never be the one suggested.
    """
    step = pl.next_step(forge)
    assert step.stage is pl.Stage.INTERROGATION
    assert step.asks_user is True


def test_the_challenge_comes_before_any_code(forge: Path) -> None:
    """Premortem and redteam found three criticals on this project's own plan."""
    started(forge)
    assert pl.next_step(forge).stage is pl.Stage.CHALLENGE


def test_the_challenge_is_a_document_not_a_flag(forge: Path) -> None:
    """If the file is not there the challenge did not happen, whatever a header says."""
    assert pl.challenge_done(forge) is False
    challenge(forge)
    assert pl.challenge_done(forge) is True


def test_phases_are_compiled_after_the_challenge(forge: Path) -> None:
    challenge(forge)
    assert pl.next_step(forge).stage is pl.Stage.PLANNING


def test_with_everything_answered_the_next_step_is_building(forge: Path) -> None:
    ready_to_build(forge)
    step = pl.next_step(forge)

    assert step.stage is pl.Stage.BUILDING
    assert step.agent == "builder"
    assert step.blocked is False


def test_a_failed_gate_sends_the_work_back_before_building_on(forge: Path) -> None:
    """Decision 009: a step is not finished until its tests pass."""
    ready_to_build(forge)
    progress = fs.Progress.read(forge)
    progress.gate_attempts = 2
    progress.write(forge)

    step = pl.next_step(forge)
    assert step.stage is pl.Stage.REVIEW_FIX
    assert "failed 2 time(s)" in step.why


def test_the_same_notes_give_the_same_next_step(forge: Path) -> None:
    """What makes resuming on another machine work at all (decision 011)."""
    ready_to_build(forge)
    assert pl.next_step(forge).as_dict() == pl.next_step(forge).as_dict()


def test_damaged_notes_ask_for_repair_rather_than_guessing(forge: Path) -> None:
    ready_to_build(forge)
    (forge / fs.PROGRESS).write_text("no header\n", encoding="utf-8")

    with pytest.raises(pl.PipelineError, match="repair"):
        pl.next_step(forge)


# --------------------------------------------------------------------------
# every step carries who runs it and with what
# --------------------------------------------------------------------------


def test_a_build_step_runs_on_the_coding_model_with_the_standards(forge: Path) -> None:
    ready_to_build(forge)
    step = pl.next_step(forge)

    assert step.model == "claude-opus-4-8"
    assert "forge-coding-standards" in step.skills


def test_a_question_is_handled_by_the_teaching_model(forge: Path) -> None:
    ready_to_build(forge)
    fs.ask(forge, "how people log in")
    step = pl.next_step(forge)

    assert step.model == "claude-fable-5"
    assert "forge-teaching" in step.skills


def test_every_step_carries_the_security_floor(forge: Path) -> None:
    ready_to_build(forge)
    assert "forge-security-floor" in pl.next_step(forge).skills


# --------------------------------------------------------------------------
# status — what a resuming session reads
# --------------------------------------------------------------------------


def test_status_says_what_the_mode_means_not_just_its_name(forge: Path) -> None:
    """Rule R1: plain language. "accept-edits" tells a non-technical user nothing."""
    report = pl.status(forge)
    assert report["mode"] == "pipeline"
    assert "asks about every decision" in str(report["mode_means"])


def test_status_reports_a_block_and_the_reason(forge: Path) -> None:
    ready_to_build(forge)
    fs.ask(forge, "how people log in")
    report = pl.status(forge)

    assert report["writes_allowed"] is False
    assert report["writes_blocked"] is True


def test_status_reports_damage_rather_than_raising(forge: Path) -> None:
    """A resuming session needs an answer it can show, not an exception."""
    ready_to_build(forge)
    (forge / fs.PROGRESS).write_text("no header\n", encoding="utf-8")

    report = pl.status(forge)
    assert report["needs_repair"] is True


@pytest.mark.parametrize(
    "question",
    [
        "Should we use OAuth or our own accounts?",
        "How does sign-in work?",
        "What is the signing-in flow?",
        "Do we need SSO?",
        "Should sign-up be open to anyone?",
        "Is SAML worth supporting?",
    ],
)
def test_authentication_in_every_spelling_is_load_bearing(question: str) -> None:
    """These forms slipped past the first pattern list.

    `OAuth`, `sign-in` and `signing in` matched nothing, so in Auto mode Forge
    would have settled an authentication architecture decision on its own —
    the exact class the list exists to protect.
    """
    assert pl.is_load_bearing(question) is True
    assert pl.should_ask(question, pl.Mode.AUTO) is True


def test_a_damaged_settings_file_is_never_overwritten(forge: Path) -> None:
    """A mode change must not destroy unrelated settings to record itself."""
    path = forge / fs.SETTINGS
    path.write_text("this file is damaged but it is the user's\n", encoding="utf-8")

    with pytest.raises(pl.PipelineError, match="will not"):
        pl.set_mode(forge, "auto")

    assert "the user's" in path.read_text(encoding="utf-8"), "left exactly as found"


def test_a_finished_step_goes_to_the_teaching_gate(forge: Path) -> None:
    """Decision 009: built and green is not finished until it is said back.

    The loop returned to BUILDING instead, so the gate carrying the product's
    entire teaching claim was never reached by the state machine.
    """
    ready_to_build(forge)
    progress = fs.Progress.read(forge)
    progress.current_step = "the login form"
    progress.next_action = ""
    progress.write(forge)

    step = pl.next_step(forge)
    assert step.stage is pl.Stage.TEACH_BACK
    assert step.asks_user is True
    assert "forge-explain-back" in step.skills
