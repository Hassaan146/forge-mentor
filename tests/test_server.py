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

    for question in ff.FOUNDATION:
        pending = ask_question(project, question.question)
        last = record_answer(project, pending["id"], "A", "because")

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
    record_answer(project, asked["id"], "hashed", "never plain text")

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
        "record_override",
        "clear_override",
        "usage_report",
        "assemble_request",
        "check_history",
        "repair_history",
        "check_review_setup",
        "fetch_review",
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
        "render_decision",
        "foundation_question",
        "render_note",
        "render_action",
        "color_legend",
        "plan_steps",
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

    # The five foundation questions come first, in the fixed order of decision
    # 033 — one arbitrary decision does not get past them, and should not:
    # every question after the stack is asked inside an answer to it.
    import forge_foundation as ff

    for question in ff.FOUNDATION:
        asked = ask_question(project, question.question)
        record_answer(project, asked["id"], "A", "because")

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
        choices=[["A", "by us", "most work"], ["B", "a service", "less control"]],
    )["block"]

    assert "YOUR TURN" in block
    assert "A, or B?" in block, "the ask names the letters that were offered"

    # The presentation depends on where the block is going: a double-ruled
    # frame where escape codes work, a heading where the client colours
    # markdown instead. The ask being last is what matters either way.
    tail = block.rstrip()
    assert tail.endswith("╝") or "YOUR TURN" in tail.rsplit("---", 1)[-1]


def test_a_detail_that_cannot_be_undone_gets_its_own_bar() -> None:
    block = call(srv.render_decision)(
        "Public or private?",
        choices=[["A", "public", "free review"]],
        important_lines=["Anyone will be able to read this code."],
    )["block"]

    assert "▌" in block
    assert "Anyone will be able to read this code." in block


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

    # The block teaches whichever key the destination can actually use. In a
    # terminal, and inside an `ansi` fence where the client interprets the
    # codes, that is the six colours. Where the codes would show raw it is the
    # nine symbols instead.
    for meaning in answer["meanings"]:
        assert meaning["name"] in answer["block"]
    if not ui._ON:
        assert answer["block"].startswith("```ansi"), "fenced, codes left in"


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

    asked = ask_question(project, "how does the list render?", affects="phase-1.step-1")
    record_answer(project, asked["id"], "textContent", "never innerHTML")

    assert call(srv.current_step)(project)["decided"] is True

    done = call(srv.step_built)(project, 1, 1)
    assert done["steps_built"] == 1
    assert done["next_is_a_question"] is True
    assert "save a todo" in done["next"]

    assert call(srv.current_step)(project)["decided"] is False, "step 2 is a fresh question"


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
    assert "step 1" in call(srv.current_step)(project)["blocked_by"].lower()


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
        call(srv.render_decision)("t", choices=[["A", "one", "first"]])["block"],
        call(srv.render_note)("h", ["one"])["block"],
        call(srv.render_action)("go?", kind="confirm")["block"],
        call(srv.color_legend)()["block"],
    ]

    for block in blocks:
        assert block.strip(), "a render tool returned nothing"
        # Whichever presentation is right for the destination, it is one the
        # presenter hook recognises as Forge speaking.
        # One presentation decision, made in one place. Inside a client that
        # strips escape codes the block arrives fenced so nothing reflows it;
        # in a terminal it is the same drawing with colour in it. Either way
        # the presenter hook has to see a frame.
        assert any(char in block for char in "┌╔"), "every block is drawn"
        if not ui._ON:
            assert block.startswith("```"), "and fenced where markdown would reflow it"
