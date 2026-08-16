"""The final branches, each one reached only when something has gone wrong.

Written last, and deliberately: these are the lines that separate "the tests
pass" from "every documented answer has been checked". Several took a specific
setup to reach at all, which is itself the argument for writing them: a branch
this hard to enter is a branch nobody has ever seen run.
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


# --------------------------------------------------------------------------
# forge_skills.py — a library that is a clone, and a git that will not answer
# --------------------------------------------------------------------------


def cloned_library(home: Path):
    import forge_skills as sk

    folder = sk.library_dir(home)
    (folder / ".git").mkdir(parents=True)
    return folder


def test_git_that_is_not_there_leaves_the_library_unverifiable(
    monkeypatch, tmp_path: Path
) -> None:
    """Unverifiable is reported as dirty, never as clean: "I could not check"
    and "it is unchanged" are different answers about a pinned library."""
    import forge_skills as sk

    cloned_library(tmp_path)

    def missing(*_a, **_k):
        raise FileNotFoundError("no git on this machine")

    monkeypatch.setattr(sk.subprocess, "run", missing)

    assert sk.library_commit(tmp_path) == ""
    assert sk.library_is_clean(tmp_path) is False


def test_git_that_hangs_leaves_the_library_unverifiable(monkeypatch, tmp_path: Path) -> None:
    import forge_skills as sk

    cloned_library(tmp_path)

    def hangs(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="git", timeout=30)

    monkeypatch.setattr(sk.subprocess, "run", hangs)

    assert sk.library_commit(tmp_path) == ""
    assert sk.library_is_clean(tmp_path) is False


def test_a_read_only_file_is_forced_open_before_the_cleanup_gives_up(
    monkeypatch, tmp_path: Path
) -> None:
    """Git objects land read-only on Windows, so a plain delete fails and the
    cleanup after a failed install would leave half a library behind."""
    import forge_skills as sk

    folder = tmp_path / "library"
    folder.mkdir()
    victim = folder / "a.md"
    victim.write_text("x", encoding="utf-8")

    forced: list[Path] = []

    def refuse_then_note(path, _mode):
        forced.append(Path(path))
        raise OSError("still read-only")

    monkeypatch.setattr(sk.os, "chmod", refuse_then_note)
    monkeypatch.setattr(
        sk.shutil,
        "rmtree",
        lambda p, onexc=None, onerror=None: (onexc or onerror)(
            Path.unlink, str(victim), None
        ),
    )

    sk._remove(folder)
    assert forced, "it tried to clear the flag before giving up"


# --------------------------------------------------------------------------
# safety.py — every shape of secret
# --------------------------------------------------------------------------


def test_an_env_file_of_any_flavour_is_a_secret() -> None:
    import safety

    assert safety._name_is_secret(".env") is True
    assert safety._name_is_secret(".env.production") is True
    assert safety._name_is_secret(".env.example") is False, "an example carries names only"


def test_a_symlink_resolving_onto_a_credential_is_refused(tmp_path: Path, monkeypatch) -> None:
    """The obvious way around a name check: a harmless name pointing at `.env`."""
    import safety

    real = tmp_path / ".env"
    real.write_text("TOKEN=x", encoding="utf-8")
    link = tmp_path / "notes.md"

    monkeypatch.setattr(Path, "resolve", lambda self, *a, **k: real)
    assert safety.is_secret_file(str(link)) is True


def test_a_file_beside_a_credential_folder_is_refused(tmp_path: Path, monkeypatch) -> None:
    """A link may sit inside a directory of credentials rather than be one."""
    import safety

    inside = tmp_path / ".ssh" / "notes.md"
    monkeypatch.setattr(Path, "resolve", lambda self, *a, **k: inside)

    assert safety.is_secret_file(str(tmp_path / "harmless.md")) is True


def test_a_token_that_cannot_be_checked_is_treated_as_a_path(
    tmp_path: Path, monkeypatch
) -> None:
    """"Cannot tell" must not relax a check whose failure is a leaked secret."""
    import safety

    monkeypatch.setattr(Path, "exists", unreadable)
    assert safety._looks_like_code_not_a_path("settings.env", cwd=str(tmp_path)) is False


# --------------------------------------------------------------------------
# forge_pipeline.py — the stage, at each gate
# --------------------------------------------------------------------------


def answer_the_foundation(forge: Path) -> None:
    """Everything the foundation loop needs before a phase can be planned.

    The challenge is a file rather than a header flag: it produces a document,
    and if the document is not there the challenge did not happen, whatever a
    header claims.
    """
    import forge_foundation as ff
    import forge_pipeline as pl

    while (question := ff.next_question(forge)) is not None:
        asked = fs.ask(forge, question.question)
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")

    (forge / pl.CHALLENGED_MARKER).write_text("# challenged\n", encoding="utf-8")


def test_a_phase_with_no_steps_is_reported_as_needing_planning(forge: Path) -> None:
    """The hole this closed: the pipeline fell straight to BUILDING, so a whole
    phase came out in a single turn with nothing asked."""
    import forge_pipeline as pl
    import forge_steps as stp

    answer_the_foundation(forge)
    stp.compile_phases(forge, [("First", "a thing that works")])
    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")

    status = pl.status(forge)
    assert status["stage"] == pl.Stage.PLANNING.value
    assert status["writes_blocked"] is True


def test_a_plan_nobody_has_accepted_is_a_question_not_a_compile(forge: Path) -> None:
    import forge_pipeline as pl
    import forge_steps as stp

    answer_the_foundation(forge)
    stp.compile_phases(forge, [("First", "a thing that works")])

    status = pl.status(forge)
    assert status["stage"] == pl.Stage.PLANNING.value
    assert status["asks_user"] is True, "the user has not seen the plan yet"


def test_a_decided_step_is_the_one_state_that_lets_the_builder_run(forge: Path) -> None:
    import forge_pipeline as pl
    import forge_steps as stp
    from conftest import pass_lean

    answer_the_foundation(forge)
    stp.compile_phases(forge, [("First", "a thing that works")])
    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")
    stp.write_steps(forge, 1, ["the first slice"])
    pass_lean(forge)
    asked = fs.ask(forge, "how does it render?", affects="phase-1.step-1")
    fs.answer(forge, asked.id, "# textContent\n\n## Why\n\nnever innerHTML\n")

    status = pl.status(forge)
    assert status["stage"] == pl.Stage.BUILDING.value
    assert status["writes_blocked"] is False


def test_every_step_built_leaves_no_step_in_hand(forge: Path) -> None:
    import forge_pipeline as pl
    import forge_steps as stp
    from conftest import pass_lean

    answer_the_foundation(forge)
    stp.compile_phases(forge, [("First", "a thing that works")])
    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")
    stp.write_steps(forge, 1, ["the only step"])
    pass_lean(forge)
    asked = fs.ask(forge, "how", affects="phase-1.step-1")
    fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")
    stp.mark_built(forge, 1, 1)

    assert pl.status(forge)["stage"]


# --------------------------------------------------------------------------
# reviewed.py — has ponytail seen this version of the review?
# --------------------------------------------------------------------------


def test_a_review_already_seen_is_not_asked_for_twice(project: Path, forge: Path) -> None:
    import forge_review as rv
    import reviewed

    reviews = forge / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    (reviews / "pr-8.md").write_text("# review of pr 8\n", encoding="utf-8")

    assert "ponytail" in reviewed.message(project), "not seen yet, so it is owed"

    rv.save_local(forge, 8, [], upto=rv.remote_fingerprint(forge, 8))
    assert reviewed.message(project) == "", "and once seen, it is quiet"


def test_a_review_file_that_cannot_be_read_owes_nothing(
    monkeypatch, project: Path, forge: Path
) -> None:
    import reviewed

    reviews = forge / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    (reviews / "pr-8.md").write_text("# review\n", encoding="utf-8")

    monkeypatch.setattr(Path, "glob", unreadable)
    assert reviewed.message(project) == ""


# --------------------------------------------------------------------------
# the last few
# --------------------------------------------------------------------------


def test_a_record_the_chain_cannot_read_is_left_out_of_the_signatures(
    monkeypatch, forge: Path
) -> None:
    import forge_integrity as fi

    asked = fs.ask(forge, "which database?")
    fs.answer(forge, asked.id, "# SQLite\n\n## Why\n\nsmall\n")
    (forge / fs.DECISIONS / "002-odd.md").write_text(
        "---\nid: not-a-number\nquestion: q\nstatus: decided\n---\n\n# x\n", encoding="utf-8"
    )

    assert len(fi._read_signatures(forge)) == 1


def test_a_quarantine_that_cannot_be_flagged_read_only_still_happens(
    monkeypatch, forge: Path
) -> None:
    import forge_repair as fr

    asked = fs.ask(forge, "which database?")
    fs.answer(forge, asked.id, "# SQLite\n\n## Why\n\nsmall\n")
    record = forge / fs.DECISIONS / fs.list_decisions(forge)[0].filename()
    record.write_text(record.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")

    problem = fr.diagnose(forge)[0]
    monkeypatch.setattr(Path, "chmod", unreadable)

    moved = fr.quarantine(problem, forge)
    assert moved.is_file(), "the evidence is set aside even when the flag will not set"


def test_two_records_quarantined_in_the_same_second_do_not_collide(forge: Path) -> None:
    """A timestamp alone is not unique, and the second would overwrite the first,
    destroying the evidence this function exists to preserve."""
    import forge_repair as fr

    for question in ("which database?", "how do people log in?"):
        asked = fs.ask(forge, question)
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")

    records = fs.list_decisions(forge)
    for record in records:
        path = forge / fs.DECISIONS / record.filename()
        path.write_text(path.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")

    problems = fr.diagnose(forge)
    moved = [fr.quarantine(problem, forge) for problem in problems]

    assert len({path.name for path in moved}) == len(moved)


def test_a_ledger_the_hook_cannot_tick_off_is_not_a_failure(
    monkeypatch, project: Path, forge: Path
) -> None:
    """The grounding hook runs after every write. It reports; it never blocks."""
    import forge_build as fb
    import grounded

    (project / "app.py").write_text("import json\n", encoding="utf-8")
    monkeypatch.setattr(fb, "mark_written", unreadable)

    payload = {"cwd": str(project), "tool_input": {"file_path": str(project / "app.py")}}
    assert grounded.message(payload) == ""


def test_the_presenter_allows_a_turn_it_cannot_read_at_all(
    monkeypatch, capsys, forge: Path
) -> None:
    """Fail open, absolutely. A Stop hook that errors ends the conversation."""
    import presenter

    fs.ask(forge, "which database?")
    monkeypatch.setattr(presenter, "last_assistant_text", unreadable)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({
            "hook_event_name": "Stop",
            "cwd": str(forge.parent.parent),
            "transcript_path": str(forge / "nope.jsonl"),
        })),
    )

    with pytest.raises(SystemExit):
        presenter.main()
    assert json.loads(capsys.readouterr().out or "{}") == {}


def test_a_turn_carrying_no_text_at_all_is_not_speech(tmp_path: Path) -> None:
    import presenter

    path = tmp_path / "t.jsonl"
    path.write_text(
        json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use"}]}}) + "\n",
        encoding="utf-8",
    )

    assert presenter.last_assistant_text(path) == ""


def test_a_home_that_raises_does_not_stop_the_walk_upward(monkeypatch, tmp_path: Path) -> None:
    def refuse():
        raise RuntimeError("no home directory on this machine")

    monkeypatch.setattr(Path, "home", staticmethod(refuse))
    assert fs.find_forge_dir(tmp_path) is None


def test_a_phase_file_whose_steps_section_is_last_still_parses(forge: Path) -> None:
    import forge_steps as stp

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    path = phases / "1-first.md"
    path.write_text(
        "---\nphase: 1\ntitle: First\n---\n\n## Notes\n\nsomething first\n\n"
        "## Steps\n\n1. [ ] the only step\n",
        encoding="utf-8",
    )

    assert [step.text for step in stp.read_steps(path, 1)] == ["the only step"]


def test_a_feature_whose_subject_nothing_has_settled_owes_the_lot(forge: Path) -> None:
    import forge_feature as ff

    assert ff.owed(forge, "store a photo on each todo")


def test_an_option_that_shares_every_word_with_the_choice_is_the_choice(forge: Path) -> None:
    """When two options share all their distinguishing words, the match falls
    back to how much of the option the choice covers."""
    import forge_explain as fe

    asked = fs.ask(forge, "which database?")
    fs.answer(
        forge,
        asked.id,
        "# SQLite\n\n**Options considered**\n\n- SQLite\n- SQLite\n\n## Why\n\nsmall\n",
    )

    entry = fe.collect(forge)[0]
    assert entry.choice == "SQLite"


def test_a_repository_with_no_commit_yet_has_nothing_to_push(
    monkeypatch, project: Path
) -> None:
    import forge_push as fp

    class Result:
        def __init__(self, code: int, out: str = "") -> None:
            self.returncode = code
            self.stdout = out
            self.stderr = ""

    def git(_repo, *args, **_k):
        if "rev-parse" in args and "HEAD" in args:
            return Result(128)
        return Result(0, "merge\n")

    monkeypatch.setattr(fp, "_git", git)
    with pytest.raises(fp.PushError, match="nothing to push"):
        fp.preview(project)


def test_a_marker_file_that_cannot_be_written_is_not_a_failure(
    monkeypatch, project: Path
) -> None:
    import companion

    monkeypatch.setattr(Path, "write_text", unreadable)
    companion.message(project)
