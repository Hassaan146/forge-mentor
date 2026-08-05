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
    return Path(project) / ".forge"


# ==========================================================================
# choosing a model — decisions 002 and 003
# ==========================================================================


def test_each_job_gets_its_intended_model() -> None:
    assert choose_model("teaching")["model"] == "claude-fable-5"
    assert choose_model("building")["model"] == "claude-opus-4-8"
    assert choose_model("structuring")["model"] == "claude-haiku-4-5"


def test_the_choice_explains_itself() -> None:
    """Rule R2 — name the reason, not just the answer."""
    assert "teaching quality is the product" in choose_model("teaching")["why"]


def test_a_missing_model_falls_back(forge: Path) -> None:
    """Decision 003: nobody is blocked because of their plan."""
    result = choose_model("teaching", available=["claude-opus-4-8", "claude-haiku-4-5"])
    assert result["model"] == "claude-opus-4-8"
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
    assert result["writes_blocked"] is False
    assert fs.open_question(forge) is None


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

    result = repair_history(project)
    assert result["intact_now"] is True
    assert any("099" in action for action in result["actions"])


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
    }


def test_the_stage_tool_names_the_skills_and_the_model() -> None:
    """The plugin has to be able to ask, or the routing table helps nobody."""
    answer = srv.skills_for_stage("building")
    assert "forge-coding-standards" in answer["skills"]
    assert answer["agent"] == "builder"
    assert answer["model"] == "claude-opus-4-8"


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

    # Once something is decided, the plan gets challenged before any code.
    asked = ask_question(project, "which backend")
    record_answer(project, asked["id"], "FastAPI", "small")
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
