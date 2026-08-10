"""Tests for the state layer and the governor.

No model is ever called here — every test runs on files alone. That is what
makes the core logic testable at all, and it is how the ≥70% coverage target
is reached without spending a token.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import forge_state as fs

GOVERNOR = Path(__file__).resolve().parents[1] / "scripts" / "governor.py"


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """An initialised Forge project."""
    fs.init(tmp_path, total_questions=8)
    return tmp_path


def run_governor(cwd: Path, tool: str = "Write", file_path: str | None = None) -> dict:
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "cwd": str(cwd),
        "tool_input": {"file_path": file_path or str(cwd / "app.py")},
    }
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(GOVERNOR)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, f"governor must never fail: {result.stderr}"
    return json.loads(result.stdout or "{}")


def denied(response: dict) -> bool:
    out = response.get("hookSpecificOutput")
    return bool(out) and out.get("permissionDecision") == "deny"


# --------------------------------------------------------------------------
# header parsing — decision 001
# --------------------------------------------------------------------------


def test_header_and_body_split(tmp_path: Path) -> None:
    header, body = fs.parse_header("---\na: 1\nb: two\n---\n\n# Body\n", tmp_path / "f.md")
    assert header == {"a": "1", "b": "two"}
    assert body.startswith("# Body")


def test_missing_header_names_the_repair(tmp_path: Path) -> None:
    with pytest.raises(fs.StateError) as err:
        fs.parse_header("no header here\n", tmp_path / "progress.md")
    assert "git checkout" in str(err.value)


def test_unclosed_header_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(fs.StateError):
        fs.parse_header("---\na: 1\n", tmp_path / "progress.md")


def test_line_without_colon_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(fs.StateError) as err:
        fs.parse_header("---\nbroken line\n---\n", tmp_path / "progress.md")
    assert "colon" in str(err.value)


def test_comments_blank_lines_and_padding_are_tolerated(tmp_path: Path) -> None:
    """Users edit these files by hand, so the parser must forgive human spacing."""
    text = (
        "---\n"
        "# a comment, ignored\n"
        "\n"
        "   stage   :   live-loop   \n"
        "open_question:  none  \n"
        "---\n"
        "\n"
        "Body starts here\n"
    )
    header, body = fs.parse_header(text, tmp_path / "progress.md")
    assert header == {"stage": "live-loop", "open_question": "none"}
    assert body.startswith("Body starts here")


# --------------------------------------------------------------------------
# init and resume — decisions 011, 016, 019
# --------------------------------------------------------------------------


def test_init_creates_committable_notes(tmp_path: Path) -> None:
    forge = fs.init(tmp_path)
    assert (forge / "progress.md").exists()
    assert (forge / "decisions").is_dir()
    assert forge == tmp_path / fs.FORGE_DIR


def test_init_refuses_to_overwrite(project: Path) -> None:
    with pytest.raises(fs.StateError):
        fs.init(project)


def test_found_from_a_subdirectory(project: Path) -> None:
    deep = project / "src" / "api" / "routers"
    deep.mkdir(parents=True)
    assert fs.find_forge_dir(deep) == project / fs.FORGE_DIR


def test_not_a_forge_project(tmp_path: Path) -> None:
    assert fs.find_forge_dir(tmp_path) is None
    assert fs.is_forge_project(tmp_path) is False


def test_a_stray_home_forge_never_adopts_a_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression guard for a real bug.

    An unbounded upward walk found a stray notes folder in a home directory
    and switched Forge on in every
    project on the machine — the opposite of decision 014, which says Forge
    acts only where it was invited.
    """
    home = tmp_path / "home"
    (home / fs.FORGE_DIR).mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    project = home / "some-project"
    project.mkdir()

    assert fs.find_forge_dir(project) is None


def test_the_search_stops_at_the_repository_root(tmp_path: Path) -> None:
    """The notes live inside the project repo (016), so the repo bounds it."""
    outer = tmp_path / "outer"
    (outer / fs.FORGE_DIR).mkdir(parents=True)

    repo = outer / "repo"
    (repo / ".git").mkdir(parents=True)
    inside = repo / "src"
    inside.mkdir()

    assert fs.find_forge_dir(inside) is None, "must not escape past the repo root"


def test_progress_survives_a_write_read_cycle(project: Path) -> None:
    forge = project / fs.FORGE_DIR
    before = fs.Progress.read(forge)
    before.current_step = "rate limiting"
    before.stage = "live-loop"
    before.write(forge)

    after = fs.Progress.read(forge)
    assert after.current_step == "rate limiting"
    assert after.stage == "live-loop"


def test_missing_progress_file_says_how_to_recover(project: Path) -> None:
    (project / fs.FORGE_DIR / "progress.md").unlink()
    with pytest.raises(fs.StateError) as err:
        fs.Progress.read(project / fs.FORGE_DIR)
    assert "/forge:start" in str(err.value)


def test_in_flight_work_travels_to_the_next_session(project: Path) -> None:
    """Decision 011: another account resumes mid-question, not at the start."""
    forge = project / fs.FORGE_DIR
    fs.ask(forge, "how people log in")
    progress = fs.Progress.read(forge)
    progress.current_step = "rate limiting"
    progress.write(forge)

    # What a fresh session on another account would read. The open question
    # comes first, because it is the thing blocking work — and it is passed in
    # from the records rather than read from the summary field.
    #
    # This assertion used to look for "rate limiting" and passed only because
    # the summary's own `open_question` was never written by `ask()`. So the
    # resume line named the step in progress and stayed silent about the
    # question the user was actually stuck on — on exactly the account-switch
    # path decision 011 exists to protect.
    progress = fs.Progress.read(forge)
    assert progress.current_step == "rate limiting"

    pending = fs.open_question(forge)
    assert pending.question == "how people log in"
    assert "how people log in" in progress.resume_line(pending.question)

    # With nothing open, the step in progress is what a session resumes on.
    assert "rate limiting" in progress.resume_line(None)


def test_resume_line_falls_back_through_what_it_knows(project: Path) -> None:
    forge = project / fs.FORGE_DIR
    progress = fs.Progress.read(forge)

    progress.current_step = ""
    progress.next_action = "begin the interrogation"
    assert "begin the interrogation" in progress.resume_line()

    progress.next_action = ""
    progress.stage = "live-loop"
    assert "live-loop" in progress.resume_line()


def test_missing_required_field_is_a_broken_file(project: Path) -> None:
    progress = project / fs.FORGE_DIR / "progress.md"
    progress.write_text("---\nstage: x\n---\n\nbody\n", encoding="utf-8")
    with pytest.raises(fs.StateError) as err:
        fs.Progress.read(progress.parent)
    assert "open_question" in str(err.value)


# --------------------------------------------------------------------------
# questions become files when asked — decision 018
# --------------------------------------------------------------------------


def test_asking_creates_an_open_record(project: Path) -> None:
    forge = project / fs.FORGE_DIR
    asked = fs.ask(forge, "which backend")
    assert asked.id == 1
    assert fs.open_question(forge).question == "which backend"
    assert (forge / "decisions" / asked.filename()).exists()


def test_answering_flips_the_same_file(project: Path) -> None:
    forge = project / fs.FORGE_DIR
    asked = fs.ask(forge, "which backend")
    path = forge / "decisions" / asked.filename()

    fs.answer(forge, asked.id, "# FastAPI\n\nSmall and agent-centric.\n")

    assert fs.open_question(forge) is None
    assert path.exists(), "the answer must land in the file the question opened"
    assert "FastAPI" in path.read_text(encoding="utf-8")


def test_oldest_open_question_wins(project: Path) -> None:
    forge = project / fs.FORGE_DIR
    first = fs.ask(forge, "which backend")
    fs.ask(forge, "which database")
    assert fs.open_question(forge).id == first.id


def test_ids_increment_across_separate_files(project: Path) -> None:
    forge = project / fs.FORGE_DIR
    fs.ask(forge, "one")
    fs.answer(forge, 1, "done")
    assert fs.ask(forge, "two").id == 2
    assert fs.next_decision_id(forge) == 3


def test_answering_a_settled_question_is_refused(project: Path) -> None:
    forge = project / fs.FORGE_DIR
    fs.ask(forge, "which backend")
    fs.answer(forge, 1, "FastAPI")
    with pytest.raises(fs.StateError):
        fs.answer(forge, 1, "Django")


def test_answering_an_unknown_id_is_refused(project: Path) -> None:
    with pytest.raises(fs.StateError):
        fs.answer(project / fs.FORGE_DIR, 99, "x")


# --------------------------------------------------------------------------
# the governor — decision 004, the product's core promise
# --------------------------------------------------------------------------


def test_writes_blocked_while_a_question_is_open(project: Path) -> None:
    fs.ask(project / fs.FORGE_DIR, "rate limiting")
    response = run_governor(project)
    assert denied(response)
    assert "rate limiting" in response["hookSpecificOutput"]["permissionDecisionReason"]


def ready_to_build(forge) -> None:
    """Everything that has to be true before a single line may be written.

    The six foundation questions, then a compiled phase, a step list inside it,
    and a decision recorded against the current step. The first gate was added
    when a fresh project turned out to allow writes because nothing was open;
    the last two after a real run wrote four files and a whole application in
    one turn, having asked nothing since the sixth question.
    """
    import forge_foundation as ff

    for question in ff.FOUNDATION:
        asked = fs.ask(forge, question.question)
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "1-first.md").write_text(
        "---\nphase: 1\ntitle: First\n---\n\n## Steps\n\n1. [ ] the first slice\n",
        encoding="utf-8",
    )
    import forge_steps as st

    asked = fs.ask(forge, "Does this plan look right?", affects=st.PLAN_MARKER)
    fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")

    asked = fs.ask(forge, "phase 1 step 1", affects="phase-1.step-1")
    fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")


def test_writes_allowed_once_answered(project: Path) -> None:
    forge = project / fs.FORGE_DIR
    fs.ask(forge, "rate limiting")
    fs.answer(forge, 1, "per-IP, 60/min")
    ready_to_build(forge)
    assert not denied(run_governor(project))


def test_an_answered_foundation_is_not_a_licence_to_build(project: Path) -> None:
    """Decision 034 opened the gate at the end of the foundation and left it open.

    That is the whole of the failure: six questions, then an application. The
    foundation says what is being built; it does not say what the next file is,
    and nobody was ever asked.
    """
    import forge_foundation as ff

    forge = project / fs.FORGE_DIR
    for question in ff.FOUNDATION:
        asked = fs.ask(forge, question.question)
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")

    allowed, reason = fs.writes_allowed(forge)
    assert allowed is False
    assert "phases have not been compiled" in reason


def test_override_lets_the_write_through(project: Path) -> None:
    forge = project / fs.FORGE_DIR
    fs.ask(forge, "rate limiting")
    progress = fs.Progress.read(forge)
    progress.override_active = True
    progress.write(forge)
    assert not denied(run_governor(project))


def test_reads_are_never_blocked(project: Path) -> None:
    fs.ask(project / fs.FORGE_DIR, "rate limiting")
    assert not denied(run_governor(project, tool="Read"))


def test_forge_can_always_write_its_own_notes(project: Path) -> None:
    fs.ask(project / fs.FORGE_DIR, "rate limiting")
    target = str(project / fs.FORGE_DIR / "decisions" / "001-x.md")
    assert not denied(run_governor(project, file_path=target))


def test_non_forge_projects_are_untouched(tmp_path: Path) -> None:
    assert not denied(run_governor(tmp_path))


def test_broken_notes_fail_closed_with_a_repair(project: Path) -> None:
    fs.ask(project / fs.FORGE_DIR, "rate limiting")
    bad = project / fs.FORGE_DIR / "decisions" / "002-broken.md"
    bad.write_text("no header at all\n", encoding="utf-8")

    response = run_governor(project)
    assert denied(response)
    reason = response["hookSpecificOutput"]["permissionDecisionReason"]
    assert "cannot read" in reason.lower()
    assert "git checkout" in reason


def test_governor_never_returns_a_failure_code(project: Path) -> None:
    # already asserted inside run_governor, but stated explicitly: a crash in
    # the safety check must never wedge the user's session.
    run_governor(project)


# --------------------------------------------------------------------------
# no account identity anywhere — decision 019
# --------------------------------------------------------------------------


def test_notes_contain_nothing_account_specific(project: Path) -> None:
    forge = project / fs.FORGE_DIR
    fs.ask(forge, "which backend")
    fs.answer(forge, 1, "FastAPI")

    for path in forge.rglob("*.md"):
        text = path.read_text(encoding="utf-8").lower()
        for forbidden in ("account_id", "session_key", "api_key", "oauth", "@gmail", "token:"):
            assert forbidden not in text, f"{forbidden} leaked into {path.name}"


def test_a_record_with_an_unreadable_id_is_named_not_guessed(project: Path) -> None:
    """The id orders the chain and identifies what the governor waits on.

    Guessing 0 invented a record that collides with the default
    `next_decision_id` returns — and this module's whole stance is to fail
    loudly on a broken file rather than interpret it.
    """
    forge = project / fs.FORGE_DIR
    (forge / fs.DECISIONS).mkdir(exist_ok=True)
    broken = forge / fs.DECISIONS / "0xx-bad-id.md"
    broken.write_text(
        fs.render_header({"id": "not-a-number", "question": "q", "status": "decided"}),
        encoding="utf-8",
    )

    with pytest.raises(fs.StateError, match="not a number"):
        fs.Decision.read(broken)


def test_a_missing_count_in_the_summary_is_still_forgiving(project: Path) -> None:
    """The strictness is for ids only. A cosmetic count is not worth stopping for."""
    forge = project / fs.FORGE_DIR
    progress = fs.Progress.read(forge)
    progress.questions_answered = 0
    progress.write(forge)
    assert fs.Progress.read(forge).questions_answered == 0


def test_the_resume_line_never_reads_the_stale_summary_field(project: Path) -> None:
    """Decision 018 makes the records authoritative.

    `ask()` writes a decision file and does not touch the summary, so anything
    reading `Progress.open_question` shows whatever was last written there —
    which is exactly the account-switch path decision 011 protects.
    """
    forge = project / fs.FORGE_DIR
    fs.ask(forge, "the real open question")

    progress = fs.Progress.read(forge)
    progress.open_question = "something stale from weeks ago"
    progress.write(forge)

    line = fs.Progress.read(forge).resume_line(fs.open_question(forge).question)
    assert "the real open question" in line
    assert "stale" not in line


def test_an_unrecognised_status_is_refused(project: Path) -> None:
    """A typo in a hand-edited file switched the product's guarantee off.

    `open_question` only treats "open" as pending, so `status: pending` read as
    settled and the governor let code past a decision nobody had made.
    """
    forge = project / fs.FORGE_DIR
    (forge / fs.DECISIONS).mkdir(exist_ok=True)
    path = forge / fs.DECISIONS / "001-typo.md"
    path.write_text(
        fs.render_header({"id": "001", "question": "q", "status": "pending"}),
        encoding="utf-8",
    )

    with pytest.raises(fs.StateError, match="does not recognise"):
        fs.Decision.read(path)


def test_unreadable_notes_block_writes(project: Path) -> None:
    """Decision 004: the safety path fails closed.

    This swallowed the error, so a damaged progress file with no decision open
    came out as "writes allowed" — Forge could not tell whether a question was
    open and said yes anyway.
    """
    forge = project / fs.FORGE_DIR
    (forge / fs.PROGRESS).write_text("no header at all\n", encoding="utf-8")

    allowed, reason = fs.writes_allowed(forge)
    assert allowed is False
    assert "cannot read" in reason.lower()


def test_an_unreadable_decision_record_blocks_writes(project: Path) -> None:
    forge = project / fs.FORGE_DIR
    (forge / fs.DECISIONS).mkdir(exist_ok=True)
    (forge / fs.DECISIONS / "001-broken.md").write_text("no header\n", encoding="utf-8")

    allowed, reason = fs.writes_allowed(forge)
    assert allowed is False
    assert "cannot read" in reason.lower()


def test_two_open_records_sharing_an_id_stop_rather_than_guess(project: Path) -> None:
    """Decision 018 accepts duplicate ids after a merge, so an id is not unique.

    Answering the first match filled in the wrong record — and then the second
    could never be answered at all, because the first was no longer open.
    """
    forge = project / fs.FORGE_DIR
    first = fs.ask(forge, "the real question")

    twin = forge / fs.DECISIONS / "001-from-another-branch.md"
    twin.write_text(
        fs.render_header(
            {"id": f"{first.id:03d}", "question": "a question from a merge",
             "status": "open", "date": "2026-08-01", "decided_by": "user"}
        ),
        encoding="utf-8",
    )

    with pytest.raises(fs.StateError, match="share id"):
        fs.answer(forge, first.id, "# anything\n")


# --------------------------------------------------------------------------
# switching Forge off in a project
# --------------------------------------------------------------------------


def test_a_paused_project_allows_every_write(project: Path) -> None:
    """`/forge:stop` means stop, not "stop except for the gates"."""
    forge = project / fs.FORGE_DIR
    fs.ask(forge, "something nobody has answered")

    assert fs.writes_allowed(forge)[0] is False

    (forge / fs.PAUSED).write_text("paused\n", encoding="utf-8")
    assert fs.paused(forge) is True
    assert fs.writes_allowed(forge)[0] is True


def test_pausing_beats_notes_that_cannot_be_read(project: Path) -> None:
    """Otherwise a damaged file locks someone out of their own repository.

    Everywhere else the safety path fails closed, and it should. Here it must
    not: the user has said stop, and a broken note is not a reason to keep
    refusing their writes.
    """
    forge = project / fs.FORGE_DIR
    (forge / fs.PROGRESS).write_text("no header at all\n", encoding="utf-8")
    assert fs.writes_allowed(forge)[0] is False

    (forge / fs.PAUSED).write_text("paused\n", encoding="utf-8")
    assert fs.writes_allowed(forge)[0] is True


def test_pausing_destroys_nothing(project: Path) -> None:
    """The records outlive the tool that produced them. That is decision 016."""
    forge = project / fs.FORGE_DIR
    asked = fs.ask(forge, "which backend")
    fs.answer(forge, asked.id, "# FastAPI\n\n## Why\n\nsmall\n")
    before = fs.list_decisions(forge)

    (forge / fs.PAUSED).write_text("paused\n", encoding="utf-8")

    assert [d.question for d in fs.list_decisions(forge)] == [d.question for d in before]
    assert (forge / fs.PROGRESS).is_file()


def test_resuming_is_deleting_one_file(project: Path) -> None:
    forge = project / fs.FORGE_DIR
    fs.ask(forge, "still open")
    (forge / fs.PAUSED).write_text("paused\n", encoding="utf-8")

    (forge / fs.PAUSED).unlink()
    assert fs.paused(forge) is False
    assert fs.writes_allowed(forge)[0] is False, "and the open question is still open"
