"""Tests for the MCP server — the engine's tool surface.

The tools are called through their plain Python functions rather than over the
protocol. What matters here is that each one does the right thing to the notes;
whether the SDK serialises correctly is the SDK's own concern.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

import forge_integrity as fi
import forge_state as fs
from conftest import pass_lean
import forge_server as srv


def call(tool) -> object:
    """Unwrap a registered tool back to the function under it."""
    return getattr(tool, "fn", getattr(tool, "__wrapped__", tool))


choose_model = call(srv.choose_model)
ask_question = call(srv.ask_question)
record_answer = call(srv.record_answer)
current_state = call(srv.current_state)
record_override = call(srv.record_override)
clear_override = call(srv.clear_override)
check_history = call(srv.check_history)
repair_history = call(srv.repair_history)
resume = call(srv.resume)
foundation_question = call(srv.foundation_question)


@pytest.fixture()
def project(tmp_path: Path) -> str:
    fs.init(tmp_path)
    return str(tmp_path)


@pytest.fixture()
def forge(project: str) -> Path:
    return Path(project) / fs.FORGE_DIR


# ==========================================================================
# choosing a model — decisions 002 and 003
# ==========================================================================


def test_each_job_gets_its_intended_model() -> None:
    assert choose_model("teaching")["model"] == "claude-fable-5"
    assert choose_model("building")["model"] == "claude-opus-5"
    assert choose_model("structuring")["model"] == "claude-haiku-4-5"


def test_the_choice_explains_itself() -> None:
    """Rule R2 — name the reason, not just the answer."""
    assert "teaching quality is the product" in choose_model("teaching")["why"]


def test_a_missing_model_falls_back(forge: Path) -> None:
    """Decision 003: nobody is blocked because of their plan."""
    result = choose_model("teaching", available=["claude-opus-5", "claude-haiku-4-5"])
    assert result["model"] == "claude-opus-5"
    assert result["fell_back"] is True


def test_nothing_preferred_still_returns_something_usable() -> None:
    result = choose_model("building", available=["some-other-model"])
    assert result["model"] == "some-other-model"
    assert result["fell_back"] is True


def test_an_unknown_job_lists_the_real_ones() -> None:
    result = choose_model("cooking")
    assert "error" in result
    assert "teaching" in result["jobs"]


def test_job_names_are_forgiving() -> None:
    assert choose_model("  TEACHING  ")["model"] == "claude-fable-5"


# ==========================================================================
# asking and answering
# ==========================================================================


def test_asking_blocks_writes_and_records_the_question(project: str, forge: Path) -> None:
    result = ask_question(project, "how people log in")
    assert result["writes_blocked"] is True
    assert fs.open_question(forge).question == "how people log in"


def test_answering_unblocks_and_verifies(project: str, forge: Path) -> None:
    asked = ask_question(project, "which backend")
    result = record_answer(
        project,
        asked["id"],
        choice="FastAPI",
        reasoning="Small and agent-centric.",
        options_considered=["FastAPI", "Django", "Flask"],
        recommendation="FastAPI",
    )

    assert result["verified"] is True, "a record Forge wrote must be trusted"
    assert fs.open_question(forge) is None, "the question is closed"

    # Still blocked, and that is the point. Answering one question no longer
    # opens the gate — the foundation has to be recorded first. A fresh project
    # used to allow writes because nothing was open, which let Forge write a
    # whole file before a single decision existed.
    assert result["writes_blocked"] is True

    import forge_foundation as ff

    while (question := ff.next_question(forge)) is not None:
        pending = ask_question(project, question.question)
        last = record_answer(
            project, pending["id"], "A", "because", their_reason="it suits me"
        )

    # And still blocked, which is the second half of the same lesson. The
    # foundation being answered says what is being built, not what the next
    # file is. Opening the gate here is what let a real run write an entire
    # application in one turn without asking anything after question six.
    assert last["writes_blocked"] is True, "a plan and a decided step come first"

    forge = Path(project) / fs.FORGE_DIR
    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "1-first.md").write_text(
        "---\nphase: 1\ntitle: First\n---\n\n## Steps\n\n1. [ ] the first slice\n",
        encoding="utf-8",
    )
    import forge_steps as stp

    pending = ask_question(project, "Does this plan look right?", affects=stp.PLAN_MARKER)
    record_answer(project, pending["id"], "yes", "looks right")

    pass_lean(forge)
    pending = ask_question(project, "phase 1 step 1", affects="phase-1.step-1")
    last = record_answer(project, pending["id"], "A", "because")

    assert last["writes_blocked"] is False, "the current step is decided"


def test_the_record_keeps_what_the_user_will_want_later(project: str, forge: Path) -> None:
    """The options and the reasoning are the point — not just the answer."""
    asked = ask_question(project, "which backend")
    record_answer(
        project,
        asked["id"],
        choice="FastAPI",
        reasoning="Small and agent-centric.",
        options_considered=["FastAPI", "Django"],
        recommendation="FastAPI",
    )

    text = (forge / fs.DECISIONS / fs.list_decisions(forge)[0].filename()).read_text(
        encoding="utf-8"
    )
    for expected in ("FastAPI", "Django", "Options considered", "Small and agent-centric"):
        assert expected in text


def test_a_project_without_forge_says_what_to_do(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as err:
        ask_question(str(tmp_path), "anything")
    assert "/forge:start" in str(err.value)


# ==========================================================================
# resuming — decisions 011 and 019
# ==========================================================================


def test_state_reports_what_a_new_session_needs(project: str) -> None:
    ask_question(project, "how people log in")
    state = current_state(project)

    assert state["open_question"] == "how people log in"
    assert state["writes_blocked"] is True
    assert "how people log in" in state["resume"]


def test_state_counts_decided_against_total(project: str) -> None:
    first = ask_question(project, "one")
    record_answer(project, first["id"], "yes", "because")
    ask_question(project, "two")

    state = current_state(project)
    assert state["decided"] == 1
    assert state["total"] == 2


def test_broken_notes_are_reported_rather_than_crashing(project: str, forge: Path) -> None:
    (forge / fs.PROGRESS).write_text("no header at all\n", encoding="utf-8")
    state = current_state(project)
    assert state["needs_repair"] is True
    assert "fix:" in state["error"]


def _answer(project: str, question: str, choice: str = "A") -> None:
    asked = ask_question(project, question)
    record_answer(project, asked["id"], choice, "because", their_reason="it suits me")


def _answer_everything(project: str) -> None:
    """Answer whatever the interrogation asks, until it stops asking.

    Not a loop over the six. An answer can open further questions, and a fixed
    loop leaves one of them open, so the gate stays shut for a reason the test
    never mentions.
    """
    import forge_foundation as ff

    forge = Path(project) / fs.FORGE_DIR
    while (question := ff.next_question(forge)) is not None:
        _answer(project, question.question)


def test_resuming_hands_back_the_block_not_a_summary(project: str) -> None:
    """The screen the user left, in the same shape they left it in.

    A resumed session that says "decision 001 is still open" makes the user
    reconstruct the question from a summary of it, which is exactly the work
    keeping the notes on disk was meant to remove.
    """
    import forge_foundation as ff

    ask_question(project, ff.INTENT.question)

    picked_up = resume(project)
    assert picked_up["open_question"] == ff.INTENT.question
    assert picked_up["stage"] == "open-question"
    assert picked_up["writes_blocked"] is True
    assert ff.INTENT.question in picked_up["block"]

    # The same block, byte for byte, as the one it was asked with. Redrawing it
    # in a slightly different shape reads as a different question.
    assert picked_up["block"] == foundation_question(project)["block"]


def test_resuming_between_answers_asks_the_next_question(project: str) -> None:
    """The gap between one answer and the next question is a resume point too.

    Nothing is open here, and the foundation is not finished. Answering "carry
    on with the build" would send the client at a governor that blocks every
    write for a reason it has not been told.
    """
    import forge_foundation as ff

    _answer(project, ff.INTENT.question, "a to-do app for myself")

    picked_up = resume(project)
    assert picked_up["open_question"] is None
    assert picked_up["stage"] == "foundation"
    assert ff.NAME.question in picked_up["block"], "the name comes second now"
    assert "next_step" not in picked_up["next"]
    assert (picked_up["answered"], picked_up["total"]) == (1, len(ff.FOUNDATION))


def test_a_question_of_its_own_comes_back_whole(project: str) -> None:
    """Not every open question is one of the six."""
    ask_question(project, "how people log in")

    picked_up = resume(project)
    assert "how people log in" in picked_up["block"]
    assert "how people log in" in picked_up["resume"]


def test_resuming_a_finished_foundation_points_at_the_work(project: str, forge: Path) -> None:
    _answer_everything(project)

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "1-first.md").write_text(
        "---\nphase: 1\ntitle: First\n---\n\n## Steps\n\n1. [ ] the first slice\n",
        encoding="utf-8",
    )

    picked_up = resume(project)
    assert picked_up["block"] == "", "there is nothing to put back on screen"
    assert picked_up["step"] == {"phase": 1, "number": 1, "text": "the first slice"}
    assert "next_step" in picked_up["next"]
    assert picked_up["writes_blocked"] is True, "a decided step is still owed"


def test_resuming_broken_notes_asks_for_repair(project: str, forge: Path) -> None:
    (forge / fs.PROGRESS).write_text("no header at all\n", encoding="utf-8")
    picked_up = resume(project)
    assert picked_up["needs_repair"] is True


def test_resuming_outside_a_forge_project_says_what_to_do(tmp_path: Path) -> None:
    assert "/forge:start" in resume(str(tmp_path))["error"]


# ==========================================================================
# the user's own reason, and the choices made while coding
# ==========================================================================


def test_a_load_bearing_answer_is_not_recorded_without_the_users_reason(
    project: str, forge: Path
) -> None:
    """The thesis of the product, enforced where it can be.

    A user who cannot say why their app is built a certain way does not own it.
    The record is where that is either true or not, and a record that says only
    "B" is evidence of nothing.
    """
    asked = ask_question(project, "how people log in")
    refused = record_answer(project, asked["id"], "a login service", "less to get wrong")

    assert refused["needs_their_reason"] is True
    assert "why that one" in refused["error"].lower()
    assert fs.open_question(forge) is not None, "still open, so nothing moved on"

    done = record_answer(
        project,
        asked["id"],
        "a login service",
        "less to get wrong",
        their_reason="I do not want to be responsible for password resets",
    )
    assert done["their_reason_recorded"] is True

    text = (forge / fs.DECISIONS / fs.list_decisions(forge)[0].filename()).read_text(
        encoding="utf-8"
    )
    assert "In their words" in text
    assert "responsible for password resets" in text


def test_furniture_is_not_held_up_for_a_reason(project: str) -> None:
    """The rule is about blast radius, not about ceremony.

    Requiring it everywhere would make the cheap questions expensive, and a
    gate that fires on everything is one people learn to type past.
    """
    asked = ask_question(project, "should this helper be called parse_row")
    assert record_answer(project, asked["id"], "yes", "it reads better")["id"]


def test_a_choice_made_while_coding_is_written_down(project: str, forge: Path) -> None:
    """They were invisible, and invisible is how a project acquires conventions
    nobody chose and the user cannot explain when asked."""
    written = call(srv.record_build_choice)(
        project,
        choice="the parser returns None rather than raising",
        reasoning="the caller already checks for an empty result",
        instead_of="raising a ParseError",
        step_marker="phase-1.step-1",
    )

    assert written["opens_the_gate"] is False
    text = (forge / fs.DECISIONS / f"{written['file']}").read_text(encoding="utf-8")
    assert "raising a ParseError" in text
    assert "decided_by: forge-builder" in text


def test_a_build_note_cannot_open_the_gate_it_was_written_against(
    project: str, forge: Path
) -> None:
    """Otherwise the builder clears its own gate by describing its work.

    A decided record naming a step is what tells the governor that step was
    asked about. If the builder can write one, the one guarantee this product
    makes becomes a formality it performs on itself.
    """
    import forge_steps as stp

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "1-first.md").write_text(
        "---\nphase: 1\ntitle: First\n---\n\n## Steps\n\n1. [ ] the first slice\n",
        encoding="utf-8",
    )

    call(srv.record_build_choice)(
        project,
        choice="the helper lives in utils.py",
        reasoning="nothing else needed a new module",
        step_marker="phase-1.step-1",
    )

    assert "phase-1.step-1" not in stp.decided_markers(forge)
    assert fs.writes_allowed(forge)[0] is False


def test_a_load_bearing_choice_is_refused_as_a_build_note(project: str) -> None:
    """The side door, closed. Recorded here it would be answered by Forge,
    attributed to Forge, and never seen by the user."""
    refused = call(srv.record_build_choice)(
        project,
        choice="use Postgres for the database",
        reasoning="it scales better",
    )

    assert refused["load_bearing"] is True
    assert "ask_question" in refused["error"]


def test_adding_a_feature_reads_the_foundation_instead_of_re_asking_it(
    project: str, forge: Path
) -> None:
    """Both halves of the request, at the tool that serves them.

    Fewer tokens: what comes back is ids and one-line choices, not a history.
    Nothing disturbed: what the feature would contradict is named, with the
    decision that would have to be reopened.
    """
    import forge_foundation as ff

    _answer(project, ff.INTENT.question, "a todo app")
    _answer(project, ff.STACK.question, "Both together")
    _answer(project, ff.DELIVERY.question, "Only on my machine")

    plan = call(srv.plan_feature)(project, "deploy it to the cloud for my team")

    assert plan["built_on"], "a feature with no context contradicts something"
    assert any("runs only on your own machine" in line for line in plan["clashes"])
    assert "reopened" in plan["next"]
    assert ff.STACK.question not in plan["still_to_ask"], "already answered, never re-asked"


def test_a_replaced_decision_points_at_the_one_it_replaced(
    project: str, forge: Path
) -> None:
    """A change of mind is a new record, never an edit of the old one."""
    first = ask_question(project, "how people log in")
    record_answer(project, first["id"], "passwords", "simplest", their_reason="I know it")

    second = ask_question(project, "how people log in, revisited")
    done = record_answer(
        project,
        second["id"],
        "a login service",
        "password resets were a fortnight",
        their_reason="I would rather not hold passwords",
        supersedes=first["id"],
    )

    text = (forge / fs.DECISIONS / f"{done['file']}").read_text(encoding="utf-8")
    assert f"Supersedes decision {first['id']:03d}" in text

    earlier = forge / fs.DECISIONS / fs.list_decisions(forge)[0].filename()
    assert "passwords" in earlier.read_text(encoding="utf-8"), "the old record survives"


def test_superseding_something_that_does_not_exist_is_refused(project: str) -> None:
    asked = ask_question(project, "which cache")
    refused = record_answer(project, asked["id"], "none", "not needed", supersedes=99)
    assert "no decision 099" in refused["error"]


def test_the_add_command_actually_calls_plan_feature() -> None:
    """The same guard as `resume`: a tool nothing calls is a file."""
    add = (Path(__file__).resolve().parents[1] / "commands" / "add.md").read_text(
        encoding="utf-8"
    )
    assert "`plan_feature`" in add
    assert "`compile_phases`" in add, "and it says which tool not to use here"


def test_the_start_command_actually_calls_resume() -> None:
    """A tool nothing calls is not a feature, it is a file.

    This is the failure this repository keeps repeating in different clothes:
    the fixed question order existed and was tested while `start.md` never
    called it, so the planner improvised its own questions and every test still
    passed. Registering a tool proves it can be called, not that anything does.
    """
    start = (Path(__file__).resolve().parents[1] / "commands" / "start.md").read_text(
        encoding="utf-8"
    )
    assert "`resume`" in start
    assert start.index("`resume`") < start.index("Step 1"), "before setup, not after it"


# ==========================================================================
# the override — decision 004
# ==========================================================================


def test_an_override_is_written_into_the_notes(project: str, forge: Path) -> None:
    """A bypass that leaves no trace is not a bypass, it is a hole."""
    ask_question(project, "rate limiting")
    result = record_override(project, reason="prototype, will revisit")

    assert result["override_active"] is True
    assert fs.Progress.read(forge).override_active is True

    recorded = [d for d in fs.list_decisions(forge) if "Override" in d.question]
    assert len(recorded) == 1
    body = (forge / fs.DECISIONS / recorded[0].filename()).read_text(encoding="utf-8")
    assert "prototype, will revisit" in body
    assert "rate limiting" in body, "must name what was skipped"


def test_an_override_without_a_reason_still_records(project: str, forge: Path) -> None:
    ask_question(project, "rate limiting")
    record_override(project)
    recorded = [d for d in fs.list_decisions(forge) if "Override" in d.question]
    assert "none given" in (forge / fs.DECISIONS / recorded[0].filename()).read_text(
        encoding="utf-8"
    )


def test_the_override_can_be_turned_off(project: str, forge: Path) -> None:
    ask_question(project, "rate limiting")
    record_override(project)
    assert clear_override(project)["override_active"] is False
    assert fs.Progress.read(forge).override_active is False


# ==========================================================================
# integrity — decisions 021 and 022
# ==========================================================================


def test_a_clean_history_reports_intact(project: str) -> None:
    asked = ask_question(project, "which backend")
    record_answer(project, asked["id"], "FastAPI", "because")
    assert check_history(project)["intact"] is True


def test_an_altered_record_is_reported_in_plain_words(project: str, forge: Path) -> None:
    asked = ask_question(project, "how passwords are stored")
    record_answer(
        project,
        asked["id"],
        "hashed",
        "never plain text",
        their_reason="I do not want to be the one holding readable passwords",
    )

    path = forge / fs.DECISIONS / fs.list_decisions(forge)[0].filename()
    path.write_text(path.read_text(encoding="utf-8").replace("hashed", "plain"), encoding="utf-8")

    result = check_history(project)
    assert result["intact"] is False
    assert result["problems"][0]["state"] == fi.Integrity.MODIFIED.value
    assert "changed after it was written" in result["problems"][0]["meaning"]
    assert "Nothing has been changed yet" in result["warning"]


def test_repair_reports_what_it_did(project: str, forge: Path) -> None:
    asked = ask_question(project, "which backend")
    record_answer(project, asked["id"], "FastAPI", "because")

    (forge / fs.DECISIONS / "099-added-later.md").write_text(
        "---\nid: 099\nquestion: added later\nstatus: decided\n---\n\nbody\n",
        encoding="utf-8",
    )

    # Asked first. This is the only code that overwrites the user's files, and
    # it used to repair on the first call while its description claimed to
    # want confirmation — a rule nothing checked.
    asked_first = repair_history(project)
    assert asked_first["needs_confirmation"] is True
    assert asked_first["repaired"] is False
    assert any("099" in line for line in asked_first["would_change"])
    assert "quarantine" in asked_first["ask"], "the user is told nothing is deleted"

    assert (forge / fs.DECISIONS / "099-added-later.md").exists(), "untouched so far"

    result = repair_history(project, confirmed=True)
    assert result["intact_now"] is True
    assert any("099" in action for action in result["actions"])


def test_nothing_to_repair_is_not_a_confirmation_prompt(project: str) -> None:
    """Asking about damage that does not exist trains the user to click yes."""
    asked = ask_question(project, "which backend")
    record_answer(project, asked["id"], "FastAPI", "because")

    result = repair_history(project)
    assert result["nothing_to_do"] is True
    assert result["intact_now"] is True


# ==========================================================================
# the chain file is kept current — decision 023
# ==========================================================================


def test_the_chain_file_is_written_as_decisions_are_made(project: str, forge: Path) -> None:
    asked = ask_question(project, "which backend")
    assert (forge / "chain.log").exists(), "written when a question is asked"

    record_answer(project, asked["id"], "FastAPI", "because")
    assert "001" in (forge / "chain.log").read_text(encoding="utf-8")


# ==========================================================================
# the protocol surface — what Claude Code actually sees
# ==========================================================================


def test_every_tool_is_registered_with_the_protocol() -> None:
    """The tests above call plain functions; this proves the MCP surface too.

    This assertion is exact rather than a subset on purpose. `server.run()`
    once sat above the review tools in this file, and because it blocks, every
    tool defined below it was never registered — invisible in a real session
    while these tests still passed, because a test imports the module instead
    of running it. An exact set is what catches that.
    """
    import asyncio

    names = {tool.name for tool in asyncio.run(srv.server.list_tools())}
    assert names == {
        "choose_model",
        "ask_question",
        "record_answer",
        "current_state",
        "resume",
        "catch_up",
        "record_build_choice",
        "record_override",
        "clear_override",
        "usage_report",
        "assemble_request",
        "check_history",
        "repair_history",
        "check_review_setup",
        "fetch_review",
        "record_review_findings",
        "skills_for_stage",
        "check_skills",
        "install_skill_library",
        "next_step",
        "set_mode",
        "explain_code",
        "preview_push",
        "push_work",
        "resolve_finding",
        "settle_small_decision",
        "write_prompts_log",
        "what_did_i_ask_for",
        "render_decision",
        "foundation_question",
        "render_note",
        "render_action",
        "color_legend",
        "plan_steps",
        "step_questions",
        "plan_files",
        "next_file",
        "file_written",
        "add_file",
        "lean_check",
        "record_lean",
        "lean_review",
        "check_grounding",
        "plan_feature",
        "add_phase",
        "current_step",
        "step_built",
        "compile_phases",
        "show_roadmap",
    }


def test_the_stage_tool_names_the_skills_and_the_model() -> None:
    """The plugin has to be able to ask, or the routing table helps nobody."""
    answer = srv.skills_for_stage("building")
    assert "forge-coding-standards" in answer["skills"]
    assert answer["agent"] == "builder"
    assert answer["model"] == "claude-opus-5"


def test_an_unknown_stage_returns_an_error_rather_than_raising() -> None:
    """A tool that raises reads to the model as a broken server."""
    assert "error" in srv.skills_for_stage("vibes")


def test_the_server_starts_only_after_every_tool_is_registered() -> None:
    """`server.run()` blocks, so anything defined below it never registers.

    Checked against the source rather than the imported module because the bug
    is invisible to an import: when this file is imported, `__name__` is not
    "__main__", the guard is skipped, and all the tools register normally. It
    only bites when Claude Code runs the file for real.
    """
    source = Path(srv.__file__).read_text(encoding="utf-8")
    # rindex on both. `index` found the first occurrence, which is inside the
    # comment above the call explaining this very bug — so any future comment
    # writing the literal would fail the test while the code was correct.
    assert source.rindex("server.run()") > source.rindex("@server.tool("), (
        "server.run() must stay at the very bottom of the module"
    )


def test_every_tool_describes_itself() -> None:
    """A tool without a description is a tool the model will use wrongly."""
    import asyncio

    for tool in asyncio.run(srv.server.list_tools()):
        assert tool.description and len(tool.description) > 30, tool.name


def test_an_active_override_is_reported_and_unblocks_writes(project: str) -> None:
    """The governor's rule must not be restated anywhere.

    current_state used to report writes as blocked whenever a question was
    open, ignoring the override — so a client would refuse work the governor
    would have allowed. Both now ask the same function.
    """
    ask_question(project, "rate limiting")
    assert current_state(project)["writes_blocked"] is True

    record_override(project, reason="prototype")
    state = current_state(project)

    assert state["override_active"] is True
    assert state["writes_blocked"] is False, "must agree with the governor"


def test_clearing_the_override_blocks_again(project: str) -> None:
    ask_question(project, "rate limiting")
    record_override(project)
    clear_override(project)
    assert current_state(project)["writes_blocked"] is True


def test_the_pipeline_tool_says_what_happens_next(project: str) -> None:
    """The stage is derived from disk, so the plugin has to be able to ask."""
    answer = call(srv.next_step)(project)
    assert answer["stage"] == "interrogation", "a fresh project starts by asking"
    assert answer["asks_user"] is True
    assert answer["mode"] == "pipeline"

    # The foundation questions come first, in the fixed order of decision 033.
    # One arbitrary decision does not get past them, and should not: every
    # question after the stack is asked inside an answer to it. The count is
    # not six, because an answer can open more.
    _answer_everything(project)

    # Only then is there a plan worth challenging.
    assert call(srv.next_step)(project)["stage"] == "challenge"


def test_the_mode_can_be_changed_and_explains_itself(project: str) -> None:
    result = call(srv.set_mode)(project, "auto")
    assert result["mode"] == "auto"
    assert "still asks about the big ones" in result["means"]


def test_an_unknown_mode_returns_an_error_not_an_exception(project: str) -> None:
    assert "error" in call(srv.set_mode)(project, "turbo")


def test_code_explained_is_written_from_the_records(project: str, forge) -> None:
    asked = ask_question(project, "which backend")
    record_answer(project, asked["id"], "FastAPI", "small and agent-centric", ["FastAPI", "Django"])

    result = call(srv.explain_code)(project)
    assert result["decisions"] == 1
    text = (forge / "code-explained.md").read_text(encoding="utf-8")
    assert "Django" in text, "what was turned down is kept"
    assert "small and agent-centric" in text, "in the user's own words"


# ==========================================================================
# what the user is asked to do — the render surface
# ==========================================================================


def test_a_decision_ends_in_the_action_frame_and_nothing_after_it() -> None:
    """The planner must not have to remember to ask the question separately.

    Two asks on screen and only one of them framed is worse than none: the
    user answers the unframed one, and the frame stops meaning "act here".
    """
    block = call(srv.render_decision)(
        "How should people log in?",
        choices=[
            ["A", "by us", "most work, nothing to depend on"],
            ["B", "a service", "less control, less to get wrong"],
            ["C", "a link by email", "no passwords at all, and slower to use"],
        ],
    )["block"]

    assert "YOUR TURN" in block
    assert "A, B, or C?" in block, "the ask names the letters that were offered"

    # The presentation depends on where the block is going: a double-ruled
    # The ask is last, whichever presentation the destination gets.
    assert "YOUR TURN" in "\n".join(block.rstrip().splitlines()[-8:])


def test_a_detail_that_cannot_be_undone_gets_its_own_bar() -> None:
    block = call(srv.render_decision)(
        "Public or private?",
        choices=[
            ["A", "public", "free review, and anyone can read it"],
            ["B", "private", "nobody can read it, and review costs money"],
        ],
        binary_because="a repository is one or the other, there is no third state",
        important_lines=["Anyone will be able to read this code."],
    )["block"]

    assert "▌" in block
    assert "Anyone will be able to read this code." in block


def test_two_options_are_refused_unless_the_question_really_has_two_sides() -> None:
    """The defect, in the place the user met it.

    A per-step question is written by the planner in the moment, and improvising
    a menu under no constraint produced "Docker, or run it locally" for a
    project that runs on one laptop. The floor is checked where the block is
    drawn, because a brief asking for three options is a brief nothing reads
    back.
    """
    thin = call(srv.render_decision)(
        "How do we run this?",
        choices=[["A", "Docker", "reproducible"], ["B", "locally", "simpler"]],
    )

    assert "block" not in thin
    assert "at least 3" in thin["error"]
    assert "false binary" in thin["error"]

    # And a genuine binary still gets through, at the price of saying why.
    real = call(srv.render_decision)(
        "Public or private?",
        choices=[
            ["A", "public", "free review, and anyone can read it"],
            ["B", "private", "nobody can read it, and review costs money"],
        ],
        binary_because="a repository is one or the other",
    )
    assert "a repository is one or the other" in real["block"]


def test_an_option_without_its_cost_is_a_word_not_a_choice() -> None:
    refused = call(srv.render_decision)(
        "Which database?",
        choices=[["A", "Postgres", ""], ["B", "SQLite", "one file"], ["C", "MySQL", "familiar"]],
    )
    assert "no consequence line" in refused["error"]


def test_the_menu_narrows_against_what_this_project_already_decided(
    project: str,
) -> None:
    """The user's example, exactly: no container for a laptop-only project.

    The rule reaches per-step questions, not only the foundation ones, because
    per-step questions are where the menu is improvised and where they saw it.
    """
    import forge_foundation as ff

    _answer(project, ff.INTENT.question, "a todo app")
    _answer(project, ff.DELIVERY.question, "Only on my machine")

    drawn = call(srv.render_decision)(
        "How do we run this?",
        project=project,
        choices=[
            ["A", "In Docker", "the same everywhere, and it is a container to learn"],
            ["B", "A local script", "one command, nothing else to install"],
            ["C", "A scheduled task", "it runs without you, and it is invisible when it fails"],
            ["D", "By hand each time", "nothing to build, and you have to remember"],
        ],
    )

    assert drawn["ruled_out"] == [
        "Ruled out, In Docker: this project runs only on your own machine"
    ]
    assert "Ruled out, In Docker" in drawn["block"], "shown, because it teaches"

    options = drawn["block"].split("Options")[1].split("Ruled out")[0]
    assert "Docker" not in options, "and it is not still on the menu"


def test_narrowing_that_leaves_a_thin_menu_is_sent_back_to_be_widened(
    project: str,
) -> None:
    """The first check passes and the block still arrives with two options.

    Four that lose two to a recorded decision is a menu of two, and it is the
    one the user reads. A per-step menu can simply be widened, so it is asked
    for rather than drawn thin.
    """
    import forge_foundation as ff

    _answer(project, ff.INTENT.question, "a todo app")
    _answer(project, ff.DELIVERY.question, "Only on my machine")

    refused = call(srv.render_decision)(
        "How do we run this?",
        project=project,
        choices=[
            ["A", "In Docker", "the same everywhere, and a container to learn"],
            ["B", "On a hosted service", "you push and it deploys, for a monthly bill"],
            ["C", "A local script", "one command, nothing else to install"],
        ],
    )

    assert "block" not in refused
    assert "leaves 1" in refused["error"]
    assert "at least 3" in refused["error"]


def test_the_action_frame_states_what_shape_of_answer_is_wanted() -> None:
    confirmed = call(srv.render_action)("Make the repository public?", kind="confirm")["block"]
    assert "type yes" in confirmed and "no to stop" in confirmed

    open_ended = call(srv.render_action)("What are you building?", kind="answer")["block"]
    assert "your own words" in open_ended


def test_an_unknown_kind_of_ask_is_an_error_not_an_exception() -> None:
    assert "error" in call(srv.render_action)("go?", kind="shout")


def test_an_action_frame_needs_something_to_act_on() -> None:
    assert "error" in call(srv.render_action)("   ")


def test_the_legend_returns_the_meanings_as_data_too() -> None:
    """The block is for the user; the list is so the planner cannot misquote it.

    The block itself now depends on where it is going: inside a client that
    strips escape codes it teaches the symbols instead, because teaching six
    colours to someone who will never see one is worse than teaching nothing.
    The data is the same either way.
    """
    import forge_ui as ui

    answer = call(srv.color_legend)()

    assert len(answer["meanings"]) == 6
    assert {m["colour"] for m in answer["meanings"]} == {
        "AMBER", "BLUE", "GREEN", "YELLOW", "RED", "PURPLE",
    }

    # The block teaches whichever key the destination can actually use: the six
    # colours in a terminal, the nine symbols where no escape code survives.
    # Teaching colours to someone who will never see one is worse than nothing.
    if ui._ON:
        for meaning in answer["meanings"]:
            assert meaning["name"] in answer["block"]
    else:
        for symbol, _ in ui.SYMBOL_MEANINGS:
            assert symbol in answer["block"]
        assert answer["block"].startswith("```diff"), "drawn, and coloured by the client"


def test_a_follow_up_can_carry_an_important_line_and_a_separate_ask() -> None:
    block = call(srv.render_note)(
        "Why not the others",
        ["No backup."],
        symbol="cost",
        ask="A, B, or C?",
        important_lines=["Moving off it later means every account signs up again."],
    )["block"]

    assert "▌" in block
    assert "YOUR TURN" in block and "A, B, or C?" in block


def test_an_unknown_symbol_is_still_rejected() -> None:
    assert "error" in call(srv.render_note)("h", ["one"], symbol="sparkle")


# ==========================================================================
# the build loop — one step at a time
# ==========================================================================


def plan_one_phase(forge: Path, number: int = 1, *, accept: bool = True) -> None:
    """A compiled phase, and by default a plan the user has accepted.

    Accepting is its own gate ahead of the steps: phase files can exist
    without anybody having read them, which is how the plan reached the user
    one instalment at a time.
    """
    import forge_steps as stp

    folder = forge / "phases"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{number}-phase.md").write_text(
        f"---\nphase: {number}\ntitle: Phase {number}\n---\n", encoding="utf-8"
    )
    if accept and not stp.plan_accepted(forge):
        asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
        fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")


def test_a_phase_must_be_broken_into_steps_before_anything_is_built(
    project: str, forge: Path
) -> None:
    """The failure this whole loop exists to stop.

    Six answers and a compiled phase used to be enough for the governor, and a
    real run wrote four files and a whole application in one turn.
    """
    plan_one_phase(forge)
    answer = call(srv.current_step)(project)

    assert answer["step"] is None
    assert "broken into steps" in answer["blocked_by"]


def test_planning_steps_names_the_first_question(project: str, forge: Path) -> None:
    plan_one_phase(forge)
    answer = call(srv.plan_steps)(project, 1, ["show the list", "save a todo"])

    assert [s["number"] for s in answer["steps"]] == [1, 2]
    assert answer["steps"][0]["marker"] == "phase-1.step-1"
    assert "show the list" in answer["next"]


def test_the_step_tool_hands_back_the_marker_to_record_against(
    project: str, forge: Path
) -> None:
    """A decision recorded without it unblocks nothing, and the loop stalls."""
    plan_one_phase(forge)
    call(srv.plan_steps)(project, 1, ["show the list"])
    answer = call(srv.current_step)(project)

    assert answer["step"]["marker"] == "phase-1.step-1"
    assert answer["decided"] is False
    assert "phase-1.step-1" in answer["how_to_ask"]


def test_a_step_decision_unblocks_only_that_step(project: str, forge: Path) -> None:
    plan_one_phase(forge)
    call(srv.plan_steps)(project, 1, ["show the list", "save a todo"])

    pass_lean(forge)
    asked = ask_question(project, "how does the list render?", affects="phase-1.step-1")
    record_answer(project, asked["id"], "textContent", "never innerHTML")

    assert call(srv.current_step)(project)["decided"] is True

    done = call(srv.step_built)(
        project, 1, 1, proof="pytest -q, 3 passed", see_it="uvicorn main:app, :8000/docs"
    )
    assert done["steps_built"] == 1
    assert done["next_is_a_question"] is True
    assert "save a todo" in done["next"]

    assert call(srv.current_step)(project)["decided"] is False, "step 2 is a fresh question"


def test_a_step_nobody_has_watched_run_is_not_built(project: str, forge: Path) -> None:
    """The user's second complaint, in one gate: "it should run the server".

    The builder proved it on a spare port, shut it down and reported success, so
    what reached the user was a description of a run they never saw.
    """
    plan_one_phase(forge)
    call(srv.plan_steps)(project, 1, ["show the list"])
    pass_lean(forge)
    asked = ask_question(project, "how does it render?", affects="phase-1.step-1")
    record_answer(project, asked["id"], "textContent", "never innerHTML")

    refused = call(srv.step_built)(project, 1, 1)
    assert refused["missing"] == ["proof", "see_it"]

    half = call(srv.step_built)(project, 1, 1, proof="pytest -q, 3 passed")
    assert half["missing"] == ["see_it"], "running it privately is not showing it"

    assert call(srv.current_step)(project)["decided"] is True, "and the step is still open"


def test_the_plan_says_what_the_step_does_before_any_file_appears(
    project: str, forge: Path
) -> None:
    """A list of filenames says what is coming, not what it is for."""
    plan_one_phase(forge)
    call(srv.plan_steps)(project, 1, ["show the list"])
    pass_lean(forge)
    asked = ask_question(project, "how does it render?", affects="phase-1.step-1")
    record_answer(project, asked["id"], "textContent", "never innerHTML")

    bare = call(srv.plan_files)(project, ["index.html", "app.js"])
    assert "error" in bare

    planned = call(srv.plan_files)(
        project,
        ["index.html", "app.js"],
        does="puts the todo list on screen and nothing else yet",
    )
    assert planned["first"] == "index.html"
    assert "puts the todo list on screen" in planned["block"]
    assert "index.html" in planned["block"]


def test_ticking_a_step_that_does_not_exist_is_an_error_not_an_exception(
    project: str, forge: Path
) -> None:
    plan_one_phase(forge)
    call(srv.plan_steps)(project, 1, ["only one"])
    assert "error" in call(srv.step_built)(project, 1, 7)


def test_rewriting_a_started_step_list_is_refused(project: str, forge: Path) -> None:
    plan_one_phase(forge)
    call(srv.plan_steps)(project, 1, ["first", "second"])
    asked = ask_question(project, "step one", affects="phase-1.step-1")
    record_answer(project, asked["id"], "A", "because")

    assert "error" in call(srv.plan_steps)(project, 1, ["something else"])


def test_the_whole_plan_is_compiled_in_one_call(project: str, forge: Path) -> None:
    """One phase at a time is how a plan becomes a surprise in instalments."""
    answer = call(srv.compile_phases)(
        project,
        [
            ["One todo, end to end", "type a todo, it survives a refresh"],
            ["Complete and delete", "tick one off, remove one"],
            ["Edit in place", "fix a typo without retyping"],
        ],
    )

    assert [p["number"] for p in answer["phases"]] == [1, 2, 3]
    assert answer["phases"][2]["title"] == "Edit in place"
    assert Path(answer["page"]).is_file(), "and a page the user can open"


def test_a_phase_needs_a_title_and_what_it_delivers(project: str) -> None:
    assert "error" in call(srv.compile_phases)(project, [])


def test_nothing_is_built_until_the_user_has_seen_the_whole_plan(
    project: str, forge: Path
) -> None:
    """The failure the user reported, as a test.

    Five phases existed and the first was built before they knew there were
    five — so the question that set the shape of all of them was answered
    without the shape being visible.
    """
    call(srv.compile_phases)(project, [["First", "a"], ["Second", "b"]])
    call(srv.plan_steps)(project, 1, ["the first slice"])

    blocked = call(srv.current_step)(project)
    assert "have not seen the whole plan" in blocked["blocked_by"]

    roadmap = call(srv.show_roadmap)(project)
    assert roadmap["accepted"] is False
    assert "First" in roadmap["block"] and "Second" in roadmap["block"]

    import forge_steps as stp

    asked = ask_question(project, "Does this plan look right?", affects=stp.PLAN_MARKER)
    record_answer(project, asked["id"], "yes", "two phases, each usable")

    assert call(srv.show_roadmap)(project)["accepted"] is True

    # And the block moves on to the first step, naming it. What holds it now is
    # the lean pass, which comes before the step's own question: whether the
    # thing is worth building is asked before how it should work.
    blocked = call(srv.current_step)(project)["blocked_by"].lower()
    assert "the first slice" in blocked
    assert "needs building" in blocked


def test_the_roadmap_needs_a_plan_to_show(project: str) -> None:
    assert "error" in call(srv.show_roadmap)(project)



def test_the_foundation_question_hands_over_the_block_itself(project: str) -> None:
    """Not a command. Claude Code collapses tool output.

    A block printed by a shell command never reaches the screen: the user is
    shown "ran 2 shell commands" and, on a real run, one line of prose as
    question 3 while the block sat invisible behind that summary.
    """
    answer = call(srv.foundation_question)(project)

    assert "block" in answer and "render" not in answer
    assert "What's the idea?" in answer["block"]
    assert "YOUR TURN" in answer["block"]
    assert "into your reply verbatim" in answer["next"]
    assert "collapsed" in answer["next"], "and why a command will not do"


def test_every_render_tool_hands_back_a_pasteable_block(project: str, forge: Path) -> None:
    """One presentation decision, made in one place, for every one of them."""
    import forge_ui as ui

    blocks = [
        call(srv.render_decision)(
            "t",
            choices=[
                ["A", "one", "the first cost"],
                ["B", "two", "the second cost"],
                ["C", "three", "the third cost"],
            ],
        )["block"],
        call(srv.render_note)("h", ["one"])["block"],
        call(srv.render_action)("go?", kind="confirm")["block"],
        call(srv.color_legend)()["block"],
    ]

    for block in blocks:
        assert block.strip(), "a render tool returned nothing"
        # One presentation decision, made in one place: box characters where
        # escape codes work, an ASCII border that doubles as the colour token
        # where the client has a highlighter.
        if ui._ON:
            assert any(char in block for char in "┌╔"), "every block is drawn"
        else:
            assert block.startswith("```diff"), "a language the highlighter knows"
            body = block.split("```diff\n", 1)[1].rsplit("\n```", 1)[0]
            for line in [ln for ln in body.splitlines() if ln.strip()]:
                assert line[0] in "+-|", "every line carries a border"


def test_catching_up_summarises_and_then_continues(project: str, forge: Path) -> None:
    """Two blocks: where you left off, and the thing you were on.

    The common path is somebody reopening after a gap, and what they need is
    not a report. It is the report followed by the question, so the session
    continues rather than restarts.
    """
    import forge_foundation as ff

    _answer(project, ff.INTENT.question, "a to-do app I can use from my phone")

    caught = call(srv.catch_up)(project)

    assert "WHERE YOU LEFT OFF" in caught["block"]
    assert "a to-do app I can use from my phone" in caught["block"], "in their own words"
    assert "Decisions" in caught["block"]
    assert ff.NAME.question in caught["next_block"], "and it hands over the next question"


def test_the_summary_is_assembled_from_the_records_not_from_a_log(
    project: str, forge: Path
) -> None:
    """No second version of the history to drift from the first.

    Deleting a record changes the summary, which is the property a log would
    not have: it would keep asserting work that is no longer written down.
    """
    import forge_foundation as ff

    _answer(project, ff.INTENT.question, "a to-do app")
    _answer(project, ff.STACK.question, "Both together")
    assert "2 recorded" in call(srv.catch_up)(project)["block"]

    for record in fs.list_decisions(forge)[1:]:
        (forge / fs.DECISIONS / record.filename()).unlink()

    assert "1 recorded" in call(srv.catch_up)(project)["block"]


def test_catching_up_on_damaged_notes_asks_for_repair(project: str, forge: Path) -> None:
    (forge / fs.PROGRESS).write_text("no header at all\n", encoding="utf-8")
    assert call(srv.catch_up)(project)["needs_repair"] is True


def test_the_status_command_actually_calls_catch_up() -> None:
    """The same guard as `resume` and `plan_feature`: a tool nothing calls."""
    status = (Path(__file__).resolve().parents[1] / "commands" / "status.md").read_text(
        encoding="utf-8"
    )
    assert "`catch_up`" in status
