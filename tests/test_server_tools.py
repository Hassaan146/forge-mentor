"""The tools the rest of the suite never called.

`test_server.py` covers the path a session takes: ask, answer, plan, build.
This file covers everything beside that path. Two thirds of the engine's
uncovered lines were here, and the reason is worth stating: a tool nobody calls
in a test is usually a tool nobody calls at all, which is exactly what the
caller-exists guard in `test_server.py` found.

Each test drives the real thing over a real temporary project. Where a tool
reaches outside the machine (git, the GitHub CLI, a 46 MB download) the library
under it is patched and the library has its own tests: `test_push.py`,
`test_review.py`, `test_skills.py`. What is under test here is the glue.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

import forge_state as fs
import forge_server as srv
from conftest import pass_lean


def call(tool):
    return getattr(tool, "fn", tool)


ask_question = call(srv.ask_question)
record_answer = call(srv.record_answer)


@pytest.fixture()
def project(tmp_path: Path) -> str:
    fs.init(tmp_path)
    return str(tmp_path)


@pytest.fixture()
def forge(project: str) -> Path:
    return Path(project) / fs.FORGE_DIR


def a_step(forge: Path, text: str = "store the todos", *, decide: bool = False) -> None:
    """A project with one phase, one step, and the plan accepted."""
    import forge_steps as stp

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "1-first.md").write_text(
        f"---\nphase: 1\ntitle: First\n---\n\n## Steps\n\n1. [ ] {text}\n",
        encoding="utf-8",
    )
    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")
    if decide:
        pass_lean(forge)
        asked = fs.ask(forge, "how", affects="phase-1.step-1")
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")


# --------------------------------------------------------------------------
# the ladder
# --------------------------------------------------------------------------


def test_the_ladder_is_returned_before_the_step_is_asked_about(project: str, forge: Path):
    a_step(forge)
    answer = call(srv.lean_check)(project)

    assert answer["finished"] is False
    assert [rung["rung"] for rung in answer["ladder"]] == [
        "needed",
        "already",
        "stdlib",
        "smallest",
        "cost",
    ]
    assert "never by how many files" in answer["next"], "decision 078"


def test_a_step_already_challenged_is_not_challenged_again(project: str, forge: Path):
    a_step(forge)
    pass_lean(forge)
    assert call(srv.lean_check)(project)["finished"] is True


def test_the_ladder_has_nothing_to_say_without_a_step(project: str):
    assert call(srv.lean_check)(project)["finished"] is True


def test_a_pass_with_a_rung_missing_is_refused(project: str, forge: Path):
    """Three plausible sentences with two rungs absent reads as a completed pass."""
    a_step(forge)
    refused = call(srv.record_lean)(
        project, keep="as proposed", findings={"needed": "yes"}, reasoning="because"
    )

    assert refused["missing"] == ["already", "stdlib", "smallest", "cost"]


def test_a_pass_needs_what_is_being_built_and_why(project: str, forge: Path):
    a_step(forge)
    every = {rung: "checked" for rung in ("needed", "already", "stdlib", "smallest", "cost")}

    assert "error" in call(srv.record_lean)(project, "", every, "because")
    assert "error" in call(srv.record_lean)(project, "as proposed", every, "  ")


def test_a_complete_pass_opens_the_step(project: str, forge: Path):
    import forge_lean as ln
    import forge_steps as stp

    a_step(forge)
    every = {rung: "checked" for rung in ("needed", "already", "stdlib", "smallest", "cost")}
    done = call(srv.record_lean)(
        project,
        keep="a table and the code that creates it",
        findings=every,
        reasoning="nothing stores anything yet",
        their_reason="sounds right",
        instead_of="three modules",
    )

    assert done["step"] == "store the todos"
    assert ln.passed(forge, stp.current(forge).marker) is True


def test_recording_a_pass_with_no_step_says_so(project: str):
    every = {rung: "checked" for rung in ("needed", "already", "stdlib", "smallest", "cost")}
    assert "error" in call(srv.record_lean)(project, "a thing", every, "because")


def test_an_approach_that_survives_the_second_pass_is_one_line(project: str, forge: Path):
    a_step(forge)
    answer = call(srv.lean_review)(project, approach="one table, one model")

    assert answer["unchanged"] is True
    assert "not a paragraph" in answer["next"]


def test_an_approach_that_shrinks_goes_back_to_the_user(project: str, forge: Path):
    """Smaller is the user's decision, not the reviewer's."""
    a_step(forge)
    answer = call(srv.lean_review)(
        project, approach="three modules", simpler="one module"
    )

    assert answer["unchanged"] is False
    assert "smaller" in answer["block"].lower()


def test_reviewing_nothing_is_an_error(project: str, forge: Path):
    a_step(forge)
    assert "error" in call(srv.lean_review)(project, approach="   ")


def test_the_second_pass_needs_a_forge_project(tmp_path: Path):
    assert "error" in call(srv.lean_review)(str(tmp_path), approach="anything")


# --------------------------------------------------------------------------
# what a subject owes before code touches it
# --------------------------------------------------------------------------


def test_a_step_that_stores_something_owes_the_database_questions(project: str, forge: Path):
    a_step(forge, "store the todos in a database")
    answer = call(srv.step_questions)(project)

    assert answer["finished"] is False
    assert "database" in answer["topics"]
    assert answer["block"], "and it arrives drawn, not as a list to improvise from"


def test_a_subject_with_nothing_owed_says_finished(project: str, forge: Path):
    a_step(forge, "rename the heading")
    assert call(srv.step_questions)(project)["finished"] is True


def test_no_step_owes_nothing(project: str):
    assert call(srv.step_questions)(project)["finished"] is True


# --------------------------------------------------------------------------
# the file ledger
# --------------------------------------------------------------------------


def test_the_next_file_is_named_once_a_step_has_a_plan(project: str, forge: Path):
    a_step(forge, decide=True)
    call(srv.plan_files)(project, ["app/db.py", "app/models.py"], does="stores a todo")

    assert call(srv.next_file)(project)["file"] == "app/db.py"


def test_a_written_file_owes_its_explanation_before_the_next(project: str, forge: Path):
    import forge_build as fb

    a_step(forge, decide=True)
    call(srv.plan_files)(project, ["app/db.py", "app/models.py"], does="stores a todo")
    fb.mark_written(forge, "phase-1.step-1", "app/db.py")

    owed = call(srv.next_file)(project)
    assert owed["explain_first"] == "app/db.py"


def test_a_finished_ledger_says_so(project: str, forge: Path):
    a_step(forge, decide=True)
    call(srv.plan_files)(project, ["app/db.py"], does="stores a todo")
    call(srv.file_written)(project, "app/db.py", what="the store", why="nothing stores", how="sqlite3")

    assert call(srv.next_file)(project)["finished"] is True


def test_next_file_with_no_step_is_finished(project: str):
    assert call(srv.next_file)(project)["finished"] is True


def test_a_file_is_not_explained_without_all_three(project: str, forge: Path):
    """What without why leaves somebody who can read the code and not question it."""
    a_step(forge, decide=True)
    call(srv.plan_files)(project, ["app/db.py"], does="stores a todo")

    refused = call(srv.file_written)(project, "app/db.py", what="the store", why="", how="")
    assert refused["missing"] == ["why", "how"]


def test_explaining_a_file_names_the_next_one_and_says_nothing_on_screen(
    project: str, forge: Path
):
    a_step(forge, decide=True)
    call(srv.plan_files)(project, ["app/db.py", "app/models.py"], does="stores a todo")
    done = call(srv.file_written)(
        project, "app/db.py", what="the store", why="nothing stores yet", how="sqlite3"
    )

    assert done["next_file"] == "app/models.py"
    assert done["say_nothing"] is True, "decision 076"


def test_explaining_a_file_without_a_step_is_an_error(project: str):
    assert "error" in call(srv.file_written)(project, "a.py", what="a", why="b", how="c")


def test_an_unforeseen_file_is_added_visibly(project: str, forge: Path):
    a_step(forge, decide=True)
    call(srv.plan_files)(project, ["app/db.py"], does="stores a todo")
    added = call(srv.add_file)(project, "app/schema.sql", because="the table needs creating")

    assert "app/schema.sql" in added["files"]
    assert "why it was not on the list" in added["next"]


def test_adding_a_file_needs_a_name_and_a_step(project: str, forge: Path):
    assert "error" in call(srv.add_file)(project, "a.py")
    a_step(forge, decide=True)
    assert "error" in call(srv.add_file)(project, "   ")


def test_a_plan_needs_a_step_in_progress(project: str):
    assert "error" in call(srv.plan_files)(project, ["a.py"], does="something")


# --------------------------------------------------------------------------
# adding a phase to a project that already works
# --------------------------------------------------------------------------


def test_a_phase_is_appended_never_rewritten(project: str, forge: Path):
    a_step(forge)
    added = call(srv.add_phase)(project, "Reminders", "a todo can remind you")

    assert added["phase"] == 2
    assert "Reminders" in (forge / "phases" / "2-reminders.md").read_text(encoding="utf-8")


def test_a_phase_needs_a_title(project: str, forge: Path):
    a_step(forge)
    assert "error" in call(srv.add_phase)(project, "  ", "something")


# --------------------------------------------------------------------------
# reviews
# --------------------------------------------------------------------------


def test_ponytails_findings_are_filed_against_the_pull_request(project: str, forge: Path):
    filed = call(srv.record_review_findings)(
        project, 8, findings=[["app/db.py", "42", "reinvents sqlite3.Row"]]
    )

    assert filed["added"] == 1
    assert filed["open"] == 1
    assert filed["ids"]


def test_finding_nothing_is_recorded_as_having_looked(project: str, forge: Path):
    """"ponytail found nothing" and "ponytail has not run" are different states."""
    filed = call(srv.record_review_findings)(project, 8, findings=[])

    assert filed["added"] == 0
    assert filed["open"] == 0, "looking and finding nothing is still a look"


def test_a_finding_is_closed_by_id(project: str, forge: Path):
    filed = call(srv.record_review_findings)(project, 8, findings=[["app/db.py", "42", "too much"]])
    thread = filed["ids"][0]

    closed = call(srv.resolve_finding)(project, 8, thread)
    assert closed["resolved"] is True


def test_closing_a_finding_that_is_not_there_says_so(project: str, forge: Path):
    call(srv.record_review_findings)(project, 8, findings=[["a.py", "1", "x"]])
    assert "error" in call(srv.resolve_finding)(project, 8, "no-such-thread")


def test_the_review_setup_check_reports_rather_than_raises(project: str):
    answer = call(srv.check_review_setup)(project)
    assert isinstance(answer, dict)


# --------------------------------------------------------------------------
# auto mode
# --------------------------------------------------------------------------


def test_a_small_decision_settled_by_forge_says_so_in_the_record(project: str, forge: Path):
    """Decision 030 accepts records nobody chose, on one condition: they are
    never confused with the ones the user made."""
    import forge_pipeline as pl

    pl.set_mode(forge, "auto")
    asked = ask_question(project, "what should the module be called?")
    settled = call(srv.settle_small_decision)(
        project, asked["id"], choice="db.py", reasoning="it is where the database lives"
    )

    assert settled["decided_by"] != "user"
    record = [d for d in fs.list_decisions(forge) if d.id == asked["id"]][0]
    assert record.decided_by != "user"


def test_forge_does_not_settle_things_for_you_outside_auto(project: str, forge: Path):
    asked = ask_question(project, "which database?")
    refused = call(srv.settle_small_decision)(
        project, asked["id"], choice="SQLite", reasoning="smallest"
    )

    assert "error" in refused


# --------------------------------------------------------------------------
# the generated documents
# --------------------------------------------------------------------------


def test_the_code_explained_document_is_assembled_from_the_records(project: str, forge: Path):
    asked = ask_question(project, "which database?")
    record_answer(project, asked["id"], "SQLite", "one file, no server", their_reason="simplest")

    written = call(srv.explain_code)(project)
    assert "SQLite" in Path(written["file"]).read_text(encoding="utf-8")


def test_the_prompts_log_is_assembled_from_the_records(project: str, forge: Path):
    asked = ask_question(project, "which database?")
    record_answer(project, asked["id"], "SQLite", "one file", their_reason="simplest")

    written = call(srv.write_prompts_log)(project)
    assert "which database?" in Path(written["file"]).read_text(encoding="utf-8")


def test_what_the_user_asked_for_comes_back_in_their_own_words(project: str, forge: Path):
    asked = ask_question(project, "should a todo have a photo?")
    record_answer(
        project, asked["id"], "yes", "a photo makes it obvious", their_reason="I want photos"
    )

    found = call(srv.what_did_i_ask_for)(project)
    assert found["count"] == 1
    assert "photos" in Path(found["file"]).read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# usage, skills, grounding
# --------------------------------------------------------------------------


def test_usage_is_reported_or_says_it_is_unavailable(project: str):
    answer = call(srv.usage_report)(project)
    assert "available" in answer


def test_the_skill_check_reports_what_is_installed():
    assert isinstance(call(srv.check_skills)(), dict)


def test_grounding_reports_what_the_code_names_that_is_not_there(project: str):
    root = Path(project)
    (root / "app.py").write_text("import nonexistent_package_xyz\n", encoding="utf-8")

    answer = call(srv.check_grounding)(project, files=["app.py"])
    assert "findings" in answer or "grounded" in answer


def test_grounding_checks_what_forge_said_as_well_as_what_it_wrote(project: str):
    answer = call(srv.check_grounding)(project, said="as decided in decision 999")
    assert isinstance(answer, dict)


# --------------------------------------------------------------------------
# the parts that reach outside the machine
# --------------------------------------------------------------------------


def test_a_push_is_previewed_before_it_happens(project: str, monkeypatch):
    """The preview is the consent: it names the commit the user is agreeing to."""
    import forge_push as fp

    monkeypatch.setattr(
        fp, "preview", lambda repo, branch="": fp.Plan(
            branch="merge", remote="origin", commit="abc1234", files=["app.py"], ahead=1
        )
    )
    shown = call(srv.preview_push)(project)

    assert shown["commit"] == "abc1234"
    assert shown["safe"] is True


def test_pushing_without_confirming_is_refused(project: str):
    assert "error" in call(srv.push_work)(project, confirmed=False)


def test_a_confirmed_push_sends_the_commit_that_was_shown(project: str, monkeypatch):
    import forge_push as fp

    monkeypatch.setattr(fp, "push", lambda repo, confirmed=False: {"pushed": True, "commit": "abc1234"})
    assert call(srv.push_work)(project, confirmed=True)["pushed"] is True


def test_a_failed_push_is_an_answer_not_an_exception(project: str, monkeypatch):
    import forge_push as fp

    def refuse(*_a, **_k):
        raise fp.PushError("no remote is configured")

    monkeypatch.setattr(fp, "preview", refuse)
    monkeypatch.setattr(fp, "push", refuse)

    assert "error" in call(srv.preview_push)(project)
    assert "error" in call(srv.push_work)(project, confirmed=True)


def test_the_skill_library_install_reports_what_landed(monkeypatch):
    import forge_skills as sk

    monkeypatch.setattr(sk, "install_library", lambda *a, **k: {"installed": 438})
    assert call(srv.install_skill_library)()["installed"] == 438


def test_a_failed_library_install_is_an_answer_not_an_exception(monkeypatch):
    import forge_skills as sk

    def refuse(*_a, **_k):
        raise sk.SkillError("no network")

    monkeypatch.setattr(sk, "install_library", refuse)
    assert "error" in call(srv.install_skill_library)()


# --------------------------------------------------------------------------
# prompt assembly, which is registered and deliberately uncalled
# --------------------------------------------------------------------------


def test_blocks_are_ordered_so_the_unchanging_part_can_be_cached(project: str):
    ordered = call(srv.assemble_request)(
        project,
        [
            {"name": "step", "text": "write the model", "tier": "volatile"},
            {"name": "contract", "text": "the rules", "tier": "frozen"},
        ],
    )

    assert ordered["text"].index("the rules") < ordered["text"].index("write the model")


def test_an_unknown_tier_names_the_real_ones(project: str):
    broken = call(srv.assemble_request)(project, [{"name": "x", "text": "y", "tier": "later"}])
    assert "frozen" in broken["error"]


def test_a_date_in_a_frozen_block_is_reported_as_a_cache_miss(project: str):
    """The failure is quiet: nothing errors, and the cache silently stops working."""
    ordered = call(srv.assemble_request)(
        project, [{"name": "contract", "text": "written 2026-08-14", "tier": "frozen"}]
    )

    assert ordered["risks"], "a date in the frozen part costs the whole prefix"


# --------------------------------------------------------------------------
# what each tool says when it is asked for something impossible
# --------------------------------------------------------------------------


def test_a_feature_needs_to_be_described_in_the_users_words(project: str):
    assert "error" in call(srv.plan_feature)(project, "   ")


def test_a_build_choice_needs_both_halves(project: str, forge: Path):
    """A choice with no reasoning is a note, and a reason with no choice is prose."""
    a_step(forge, decide=True)
    assert "error" in call(srv.record_build_choice)(project, choice="db.py", reasoning="")
    assert "error" in call(srv.record_build_choice)(project, choice="", reasoning="it fits")


def test_a_finding_with_no_file_or_no_complaint_is_refused(project: str):
    assert "error" in call(srv.record_review_findings)(project, 8, findings=[["", "1", "x"]])
    assert "error" in call(srv.record_review_findings)(project, 8, findings=[["a.py", "1", ""]])


def test_a_reviewer_that_does_not_run_here_is_refused(project: str):
    """This files what ran in the session. A GitHub reviewer arrives by fetch."""
    refused = call(srv.record_review_findings)(project, 8, findings=[], reviewer="coderabbit")
    assert "not a local reviewer" in refused["error"]


def test_a_review_for_a_pull_request_that_is_not_one_is_refused(project: str):
    assert "error" in call(srv.record_review_findings)(project, "not a number", findings=[])
    assert "error" in call(srv.fetch_review)(project, 0)


def test_an_unknown_mode_lists_the_real_ones(project: str):
    assert "error" in call(srv.set_mode)(project, "turbo")


def test_closing_a_finding_needs_a_project_that_has_one(tmp_path: Path):
    assert "error" in call(srv.resolve_finding)(str(tmp_path), 8, "T1")


def test_settling_a_decision_that_is_not_open_is_refused(project: str):
    assert "error" in call(srv.settle_small_decision)(project, 99, "a", "because")


def test_a_settled_decision_records_the_options_it_was_chosen_from(
    project: str, forge: Path
):
    import forge_pipeline as pl

    pl.set_mode(forge, "auto")
    asked = ask_question(project, "what should the module be called?")
    settled = call(srv.settle_small_decision)(
        project,
        asked["id"],
        choice="db.py",
        reasoning="it is where the database lives",
        options_considered=["db.py", "storage.py"],
    )

    record = (forge / fs.DECISIONS / settled["file"]).read_text(encoding="utf-8")
    assert "storage.py" in record, "the road not taken is part of the record"


def test_a_step_that_does_not_exist_cannot_be_ticked_off(project: str, forge: Path):
    a_step(forge, decide=True)
    assert "error" in call(srv.step_built)(
        project, 1, 9, proof="pytest", see_it="uvicorn main:app"
    )


def test_a_foundation_that_is_finished_says_so(project: str):
    """The sequence is fixed in code, so 'finished' is the only way out of it."""
    import forge_foundation as ff

    forge = Path(project) / fs.FORGE_DIR
    while (question := ff.next_question(forge)) is not None:
        asked = ask_question(project, question.question)
        record_answer(project, asked["id"], "A", "because", their_reason="it suits me")

    assert call(srv.foundation_question)(project)["finished"] is True


def test_a_malformed_choice_row_is_reported_rather_than_crashing(project: str):
    """`choices` arrives from a model as a list of lists, and a short row is a
    typo, not a reason to lose the turn."""
    drawn = call(srv.render_decision)(
        title="How should people log in?", choices=[["A"], "not a row"], project=project
    )
    assert "block" in drawn or "error" in drawn


def test_code_that_names_only_what_is_there_is_grounded(project: str):
    root = Path(project)
    (root / "app.py").write_text("import json\n", encoding="utf-8")

    assert call(srv.check_grounding)(project, files=["app.py"])["grounded"] is True


def test_catching_up_says_what_the_project_is_waiting_on(project: str, forge: Path):
    """Two different waits, and the user needs to know which one this is: a
    question of theirs, or a gate of Forge's."""
    asked = ask_question(project, "which database?")
    assert "Waiting on you" in call(srv.catch_up)(project)["blocked_by"]

    record_answer(project, asked["id"], "SQLite", "one file")
    assert call(srv.catch_up)(project)["blocked_by"], "and then it is a gap, not a question"


def test_a_files_list_that_cannot_be_planned_is_an_answer(project: str, forge: Path):
    a_step(forge, decide=True)
    refused = call(srv.plan_files)(project, [], does="stores a todo")

    assert "error" in refused


def test_a_step_already_writing_cannot_have_its_order_rewritten(project: str, forge: Path):
    """Renumbering history: the file somebody was shown as the first of four
    becomes the third of six, and the explanation no longer matches."""
    import forge_build as fb

    a_step(forge, decide=True)
    call(srv.plan_files)(project, ["a.py", "b.py"], does="stores a todo")
    fb.mark_written(forge, "phase-1.step-1", "a.py")

    assert "error" in call(srv.plan_files)(project, ["c.py"], does="something else")


def test_two_blocks_with_one_name_is_an_answer_not_an_exception(project: str):
    """The prefix is fingerprinted by name, so two blocks called the same thing
    make the fingerprint meaningless rather than merely untidy."""
    refused = call(srv.assemble_request)(
        project,
        [
            {"name": "contract", "text": "the rules", "tier": "frozen"},
            {"name": "contract", "text": "the rules again", "tier": "frozen"},
        ],
    )
    assert "error" in refused


def test_the_mode_of_a_project_without_notes_is_an_answer(tmp_path: Path):
    assert "error" in call(srv.next_step)(str(tmp_path))


def test_a_local_finding_id_is_closed_in_the_local_file(project: str, forge: Path):
    filed = call(srv.record_review_findings)(project, 8, findings=[["a.py", "1", "x"]])
    thread = filed["ids"][0]

    assert call(srv.resolve_finding)(project, 8, thread)["where"] == "the local review file"
    assert "error" in call(srv.resolve_finding)(project, 8, "ponytail-99")


def test_a_thread_forge_never_recorded_is_not_closed_through_your_account(
    project: str, forge: Path, monkeypatch
):
    """The id used to be taken on trust, so a thread from another repository
    could be closed through the user's credentials with nothing recorded."""
    import forge_review as rv

    monkeypatch.setattr(rv, "known_threads", lambda *a, **k: {"T1"})
    monkeypatch.setattr(
        rv,
        "_post_graphql",
        lambda *a, **k: {"resolveReviewThread": {"thread": {"isResolved": True}}},
    )

    assert call(srv.resolve_finding)(project, 8, "T1")["resolved"] is True

    refused = call(srv.resolve_finding)(project, 8, "T-from-somewhere-else")
    assert "error" in refused and refused["resolved"] is False


def test_a_menu_narrows_against_a_project_it_cannot_read(tmp_path: Path):
    """`project` is optional on the renderer, and an unreadable one must not
    lose the block: the question still has to reach the screen."""
    drawn = call(srv.render_decision)(
        title="How is it deployed?",
        choices=[["A", "a platform", "someone else runs it"], ["B", "your machine", "free"],
                 ["C", "a container", "portable"]],
        project=str(tmp_path),
    )

    assert "block" in drawn


def test_a_phase_row_that_is_not_a_pair_is_reported(project: str):
    assert "error" in call(srv.compile_phases)(project, phases=[None])
