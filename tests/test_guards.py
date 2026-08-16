"""The last branches: guards that only fire when something has gone wrong.

Split from `test_edges.py` to keep that file readable. Same intent: every
defensive branch in Forge has a documented answer, and a branch nobody has run
is a promise nobody has checked.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

import forge_state as fs


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    fs.init(tmp_path)
    return tmp_path


@pytest.fixture()
def forge(project: Path) -> Path:
    return project / fs.FORGE_DIR


def unreadable(*_a, **_k):
    raise OSError("permission denied")


def a_plan(forge: Path) -> None:
    import forge_steps as stp

    stp.compile_phases(forge, [("First", "a thing that works")])
    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")


# --------------------------------------------------------------------------
# safety.py — the one hook whose failure would be a leak
# --------------------------------------------------------------------------


def test_a_link_pointing_at_a_secret_is_still_a_secret(tmp_path: Path, monkeypatch) -> None:
    """A symlink is the obvious way around a name check, and the check follows
    it: the resolved name and its parent folder both count."""
    import safety

    ssh = tmp_path / ".ssh"
    ssh.mkdir()
    (ssh / "config").write_text("Host *", encoding="utf-8")

    assert safety.is_secret_file(str(tmp_path / ".env.production")) is True
    assert safety.is_secret_file(str(ssh / "config")) is True, (
        "a file inside a credentials folder is one too"
    )


def test_a_path_that_will_not_resolve_is_treated_as_a_secret(tmp_path: Path, monkeypatch) -> None:
    """Fail closed. Refusing to read a harmless file costs a turn; reading a
    credential because the path was odd cannot be taken back."""
    import safety

    monkeypatch.setattr(Path, "resolve", unreadable)
    assert safety.is_secret_file(str(tmp_path / "anything.txt")) is True


def test_the_safety_hook_ignores_anything_that_is_not_a_tool_call(
    monkeypatch, capsys, project: Path
) -> None:
    import safety

    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    with pytest.raises(SystemExit):
        safety.main()
    assert json.loads(capsys.readouterr().out or "{}") == {}

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"hook_event_name": "Stop"})))
    with pytest.raises(SystemExit):
        safety.main()
    assert json.loads(capsys.readouterr().out or "{}") == {}


# --------------------------------------------------------------------------
# forge_skills.py — git, and the machine it is not on
# --------------------------------------------------------------------------


def test_no_library_folder_means_no_commit_to_report(tmp_path: Path) -> None:
    import forge_skills as sk

    assert sk.library_commit(tmp_path) == ""


def test_git_missing_while_reading_the_library_is_not_a_crash(
    monkeypatch, tmp_path: Path
) -> None:
    import forge_skills as sk

    library = sk.library_dir(tmp_path)
    library.mkdir(parents=True)

    def missing(*_a, **_k):
        raise FileNotFoundError("no git")

    monkeypatch.setattr(sk.subprocess, "run", missing)
    assert sk.library_commit(tmp_path) == ""
    assert sk.library_is_clean(tmp_path) is False


def test_a_file_that_will_not_delete_leaves_the_rest_of_the_cleanup_alone(
    monkeypatch, tmp_path: Path
) -> None:
    import forge_skills as sk

    folder = tmp_path / "library"
    folder.mkdir()
    (folder / "a.md").write_text("x", encoding="utf-8")

    monkeypatch.setattr(sk.os, "chmod", unreadable)
    sk._remove(folder)


# --------------------------------------------------------------------------
# forge_foundation.py — what an answer settles
# --------------------------------------------------------------------------


def test_an_open_question_settles_nothing_and_answers_nothing(forge: Path) -> None:
    import forge_foundation as ff

    fs.ask(forge, ff.INTENT.question)

    assert ff.answered_from(forge, (ff.INTENT,)) == set()
    assert ff.facts(forge) == set()
    assert ff.source_of(forge, "runs-locally") is None


def test_prose_that_names_a_known_shape_settles_it(forge: Path) -> None:
    """The keyword fallback exists for one case: somebody who typed their own
    answer rather than picking a letter."""
    import forge_foundation as ff

    settled = ff._facts_from(ff.STACK, "it only ever runs on my own machine", set())
    assert isinstance(settled, set)


def test_the_decision_behind_a_fact_can_be_found_again(forge: Path) -> None:
    """`where_from` is how a menu explains why an option was ruled out, and
    "ruled out by decision 004" is the teaching part."""
    import forge_foundation as ff

    while (question := ff.next_question(forge)) is not None:
        asked = fs.ask(forge, question.question)
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")

    for fact in sorted(ff.facts(forge)):
        assert ff.source_of(forge, fact) is not None
        break


def test_a_question_unlocked_by_an_answer_is_added_once(forge: Path) -> None:
    """An answer can open further questions, and adding one twice would ask the
    user the same thing twice."""
    import forge_foundation as ff

    asked = fs.ask(forge, ff.INTENT.question)
    fs.answer(forge, asked.id, "# a to-do app\n\n## Why\n\nmine\n")

    sequence = ff.sequence(forge)
    assert len(sequence) == len({q.key for q in sequence})


# --------------------------------------------------------------------------
# grounded.py — after the write, never before
# --------------------------------------------------------------------------


def test_the_grounding_hook_survives_a_check_that_raises(monkeypatch, project: Path) -> None:
    import forge_grounding as gr
    import grounded

    (project / "app.py").write_text("import json\n", encoding="utf-8")
    monkeypatch.setattr(gr, "check_file", unreadable)

    payload = {"cwd": str(project), "tool_input": {"file_path": str(project / "app.py")}}
    assert grounded.message(payload) == ""


def test_a_written_file_is_ticked_off_the_ledger_as_it_lands(
    project: Path, forge: Path
) -> None:
    """The ledger tracks what was written, and the hook is what sees the write
    actually happen rather than being told about it."""
    import forge_build as fb
    import forge_steps as stp
    import grounded

    a_plan(forge)
    stp.write_steps(forge, 1, ["the first slice"])
    fb.plan(forge, "phase-1.step-1", ["app.py"])
    (project / "app.py").write_text("import json\n", encoding="utf-8")

    grounded.message({"cwd": str(project), "tool_input": {"file_path": str(project / "app.py")}})
    assert [item.written for item in fb.read_plan(forge, "phase-1.step-1")] == [True]


# --------------------------------------------------------------------------
# forge_pipeline.py — which stage the project is in
# --------------------------------------------------------------------------


def test_the_stage_names_what_is_missing_at_each_point(project: Path, forge: Path) -> None:
    """Four states, and the middle two were the hole: the pipeline fell straight
    to BUILDING, so a whole phase came out in one turn with nothing asked."""
    import forge_foundation as ff
    import forge_pipeline as pl
    import forge_steps as stp

    while (question := ff.next_question(forge)) is not None:
        asked = fs.ask(forge, question.question)
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")

    assert pl.status(forge)["stage"] in {pl.Stage.CHALLENGE.value, pl.Stage.PLANNING.value}

    stp.compile_phases(forge, [("First", "a thing that works")])
    assert pl.status(forge)["stage"]

    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")
    stp.write_steps(forge, 1, ["the first slice"])

    assert pl.status(forge)["stage"] in {
        pl.Stage.STEP_DECISION.value,
        pl.Stage.CHALLENGE.value,
    }, "a step is in front of the user, whichever gate names it"


def test_a_project_with_every_step_built_is_between_phases(forge: Path) -> None:
    import forge_pipeline as pl
    import forge_steps as stp
    from conftest import pass_lean

    a_plan(forge)
    stp.write_steps(forge, 1, ["the only step"])
    pass_lean(forge)
    asked = fs.ask(forge, "how", affects="phase-1.step-1")
    fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")
    stp.mark_built(forge, 1, 1)

    assert pl.status(forge)["stage"]


# --------------------------------------------------------------------------
# the rest, one line each
# --------------------------------------------------------------------------


def test_a_project_with_no_decisions_folder_has_no_signatures(tmp_path: Path) -> None:
    import forge_integrity as fi

    assert fi._read_signatures(tmp_path / "nowhere") == {}


def test_a_record_the_chain_cannot_parse_is_left_out_of_it(forge: Path) -> None:
    import forge_integrity as fi

    asked = fs.ask(forge, "which database?")
    fs.answer(forge, asked.id, "# SQLite\n\n## Why\n\nsmall\n")
    (forge / fs.DECISIONS / "002-broken.md").write_text("no header\n", encoding="utf-8")

    assert len(fi._read_signatures(forge)) == 1


def test_a_review_folder_with_nothing_in_it_owes_nothing(project: Path) -> None:
    import reviewed

    (project / fs.FORGE_DIR / "reviews").mkdir(parents=True, exist_ok=True)
    assert reviewed.message(project) == ""


def test_a_review_that_ponytail_has_not_seen_is_asked_for(project: Path, forge: Path) -> None:
    import forge_review as rv
    import reviewed

    reviews = forge / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    (reviews / "pr-8.md").write_text("# review of pr 8\n", encoding="utf-8")

    assert rv.local_review_owed(forge, 8) is True
    assert "ponytail" in reviewed.message(project)


def test_an_explained_project_with_no_records_explains_nothing(tmp_path: Path) -> None:
    import forge_explain as fe

    assert fe.collect(tmp_path / "nowhere") == []


def test_an_option_worded_differently_from_the_choice_still_matches(forge: Path) -> None:
    """"SQLite, one file on disk" chosen against "SQLite" offered is the same
    option, and listing it as rejected reads as a contradiction."""
    import forge_explain as fe

    asked = fs.ask(forge, "which database?")
    fs.answer(
        forge,
        asked.id,
        "# SQLite, one file on disk\n\n**Options considered**\n\n"
        "- SQLite, one file on disk\n- Postgres, a server\n\n## Why\n\nsmall\n",
    )

    entry = fe.collect(forge)[0]
    assert entry.options, "the road not taken is still listed"
    assert any("postgres" in option.lower() for option in entry.options)


def test_the_presenter_reads_past_a_tool_result_to_the_speech(tmp_path: Path) -> None:
    """Tool results arrive as `user` entries, and stopping at those would cut
    the turn at its first tool call, which is where the speech starts."""
    import presenter

    path = tmp_path / "t.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"type": "user", "message": {"content": "go on"}}),
                json.dumps({"type": "assistant", "message": {"content": [
                    {"type": "text", "text": "first"}]}}),
                json.dumps({"type": "user", "message": {"content": [
                    {"type": "tool_result", "content": "ok"}]}}),
                json.dumps({"type": "assistant", "message": {"content": [
                    {"type": "text", "text": "second"}]}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    said = presenter.last_assistant_text(path)
    assert "first" in said and "second" in said


def test_a_steps_section_is_added_when_a_phase_file_has_none(forge: Path) -> None:
    import forge_steps as stp

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "1-first.md").write_text(
        "---\nphase: 1\ntitle: First\n---\n\nit delivers a thing\n", encoding="utf-8"
    )

    stp.write_steps(forge, 1, ["the first slice"])
    text = (phases / "1-first.md").read_text(encoding="utf-8")

    assert "the first slice" in text and "it delivers a thing" in text


def test_a_heading_after_the_steps_ends_the_list(forge: Path) -> None:
    """Otherwise a numbered list further down the file is read as more steps."""
    import forge_steps as stp

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    path = phases / "1-first.md"
    path.write_text(
        "---\nphase: 1\ntitle: First\n---\n\n## Steps\n\n1. [ ] the real step\n\n"
        "## Notes\n\n1. not a step at all\n",
        encoding="utf-8",
    )

    assert [step.text for step in stp.read_steps(path, 1)] == ["the real step"]


def test_a_home_directory_that_cannot_be_read_does_not_stop_the_search(
    monkeypatch, tmp_path: Path
) -> None:
    def refuse():
        raise OSError("no home")

    monkeypatch.setattr(Path, "home", staticmethod(refuse))
    assert fs.find_forge_dir(tmp_path) is None


def test_a_quarantine_folder_that_cannot_be_flagged_is_still_used(
    monkeypatch, forge: Path
) -> None:
    import forge_repair as fr

    monkeypatch.setattr(Path, "chmod", unreadable)
    fr.write_chain(forge)
    assert (forge / "chain.log").is_file()


def test_a_feature_reads_only_the_decisions_that_are_settled(forge: Path) -> None:
    import forge_feature as ff

    fs.ask(forge, "which database?")
    assert ff.constraints(forge, "store a photo on each todo") == []
    assert ff.clashes(forge, "store a photo on each todo") == []


def test_a_marker_file_that_cannot_be_written_does_not_stop_the_message(
    monkeypatch, project: Path
) -> None:
    import companion

    monkeypatch.setattr(Path, "write_text", unreadable)
    companion.message(project)


def test_a_long_action_line_wraps_inside_the_frame() -> None:
    """Wrapped flat, the continuation starts in column zero and reads as a
    second action rather than the rest of this one."""
    import forge_say as say

    drawn = say.framed("A title", "a body", [" ".join(["a long instruction"] * 8)])
    assert drawn.count("→") == 1


def test_a_repository_with_no_head_has_nothing_to_push(monkeypatch, project: Path) -> None:
    import forge_push as fp

    calls = {"n": 0}

    class Result:
        def __init__(self, code: int) -> None:
            self.returncode = code
            self.stdout = "merge\n"
            self.stderr = ""

    def git(_repo, *args, **_k):
        calls["n"] += 1
        return Result(0 if "rev-parse" not in args or "HEAD" not in args else 128)

    monkeypatch.setattr(fp, "_git", git)
    with pytest.raises(fp.PushError):
        fp.preview(project)


def test_empty_text_carries_no_secrets() -> None:
    import forge_prompts as fpr

    assert fpr.redact("") == ("", 0)


def test_a_missing_gh_command_is_not_a_sign_in(monkeypatch) -> None:
    import forge_preflight as pf

    monkeypatch.setattr(pf, "_has_command", lambda _n: False)
    assert pf._gh_signed_in() is False
