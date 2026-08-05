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
    assert forge.name == ".forge"


def test_init_refuses_to_overwrite(project: Path) -> None:
    with pytest.raises(fs.StateError):
        fs.init(project)


def test_found_from_a_subdirectory(project: Path) -> None:
    deep = project / "src" / "api" / "routers"
    deep.mkdir(parents=True)
    assert fs.find_forge_dir(deep) == project / ".forge"


def test_not_a_forge_project(tmp_path: Path) -> None:
    assert fs.find_forge_dir(tmp_path) is None
    assert fs.is_forge_project(tmp_path) is False


def test_a_stray_home_forge_never_adopts_a_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression guard for a real bug.

    An unbounded upward walk found `~/.forge` and switched Forge on in every
    project on the machine — the opposite of decision 014, which says Forge
    acts only where it was invited.
    """
    home = tmp_path / "home"
    (home / ".forge").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    project = home / "some-project"
    project.mkdir()

    assert fs.find_forge_dir(project) is None


def test_the_search_stops_at_the_repository_root(tmp_path: Path) -> None:
    """`.forge/` lives inside the project repo (016), so the repo bounds it."""
    outer = tmp_path / "outer"
    (outer / ".forge").mkdir(parents=True)

    repo = outer / "repo"
    (repo / ".git").mkdir(parents=True)
    inside = repo / "src"
    inside.mkdir()

    assert fs.find_forge_dir(inside) is None, "must not escape past the repo root"


def test_progress_survives_a_write_read_cycle(project: Path) -> None:
    forge = project / ".forge"
    before = fs.Progress.read(forge)
    before.current_step = "rate limiting"
    before.stage = "live-loop"
    before.write(forge)

    after = fs.Progress.read(forge)
    assert after.current_step == "rate limiting"
    assert after.stage == "live-loop"


def test_missing_progress_file_says_how_to_recover(project: Path) -> None:
    (project / ".forge" / "progress.md").unlink()
    with pytest.raises(fs.StateError) as err:
        fs.Progress.read(project / ".forge")
    assert "/forge:start" in str(err.value)


def test_in_flight_work_travels_to_the_next_session(project: Path) -> None:
    """Decision 011: another account resumes mid-question, not at the start."""
    forge = project / ".forge"
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
    forge = project / ".forge"
    progress = fs.Progress.read(forge)

    progress.current_step = ""
    progress.next_action = "begin the interrogation"
    assert "begin the interrogation" in progress.resume_line()

    progress.next_action = ""
    progress.stage = "live-loop"
    assert "live-loop" in progress.resume_line()


def test_missing_required_field_is_a_broken_file(project: Path) -> None:
    progress = project / ".forge" / "progress.md"
    progress.write_text("---\nstage: x\n---\n\nbody\n", encoding="utf-8")
    with pytest.raises(fs.StateError) as err:
        fs.Progress.read(progress.parent)
    assert "open_question" in str(err.value)


# --------------------------------------------------------------------------
# questions become files when asked — decision 018
# --------------------------------------------------------------------------


def test_asking_creates_an_open_record(project: Path) -> None:
    forge = project / ".forge"
    asked = fs.ask(forge, "which backend")
    assert asked.id == 1
    assert fs.open_question(forge).question == "which backend"
    assert (forge / "decisions" / asked.filename()).exists()


def test_answering_flips_the_same_file(project: Path) -> None:
    forge = project / ".forge"
    asked = fs.ask(forge, "which backend")
    path = forge / "decisions" / asked.filename()

    fs.answer(forge, asked.id, "# FastAPI\n\nSmall and agent-centric.\n")

    assert fs.open_question(forge) is None
    assert path.exists(), "the answer must land in the file the question opened"
    assert "FastAPI" in path.read_text(encoding="utf-8")


def test_oldest_open_question_wins(project: Path) -> None:
    forge = project / ".forge"
    first = fs.ask(forge, "which backend")
    fs.ask(forge, "which database")
    assert fs.open_question(forge).id == first.id


def test_ids_increment_across_separate_files(project: Path) -> None:
    forge = project / ".forge"
    fs.ask(forge, "one")
    fs.answer(forge, 1, "done")
    assert fs.ask(forge, "two").id == 2
    assert fs.next_decision_id(forge) == 3


def test_answering_a_settled_question_is_refused(project: Path) -> None:
    forge = project / ".forge"
    fs.ask(forge, "which backend")
    fs.answer(forge, 1, "FastAPI")
    with pytest.raises(fs.StateError):
        fs.answer(forge, 1, "Django")


def test_answering_an_unknown_id_is_refused(project: Path) -> None:
    with pytest.raises(fs.StateError):
        fs.answer(project / ".forge", 99, "x")


# --------------------------------------------------------------------------
# the governor — decision 004, the product's core promise
# --------------------------------------------------------------------------


def test_writes_blocked_while_a_question_is_open(project: Path) -> None:
    fs.ask(project / ".forge", "rate limiting")
    response = run_governor(project)
    assert denied(response)
    assert "rate limiting" in response["hookSpecificOutput"]["permissionDecisionReason"]


def test_writes_allowed_once_answered(project: Path) -> None:
    forge = project / ".forge"
    fs.ask(forge, "rate limiting")
    fs.answer(forge, 1, "per-IP, 60/min")
    assert not denied(run_governor(project))


def test_override_lets_the_write_through(project: Path) -> None:
    forge = project / ".forge"
    fs.ask(forge, "rate limiting")
    progress = fs.Progress.read(forge)
    progress.override_active = True
    progress.write(forge)
    assert not denied(run_governor(project))


def test_reads_are_never_blocked(project: Path) -> None:
    fs.ask(project / ".forge", "rate limiting")
    assert not denied(run_governor(project, tool="Read"))


def test_forge_can_always_write_its_own_notes(project: Path) -> None:
    fs.ask(project / ".forge", "rate limiting")
    target = str(project / ".forge" / "decisions" / "001-x.md")
    assert not denied(run_governor(project, file_path=target))


def test_non_forge_projects_are_untouched(tmp_path: Path) -> None:
    assert not denied(run_governor(tmp_path))


def test_broken_notes_fail_closed_with_a_repair(project: Path) -> None:
    fs.ask(project / ".forge", "rate limiting")
    bad = project / ".forge" / "decisions" / "002-broken.md"
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
    forge = project / ".forge"
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
    forge = project / ".forge"
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
    forge = project / ".forge"
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
    forge = project / ".forge"
    fs.ask(forge, "the real open question")

    progress = fs.Progress.read(forge)
    progress.open_question = "something stale from weeks ago"
    progress.write(forge)

    line = fs.Progress.read(forge).resume_line(fs.open_question(forge).question)
    assert "the real open question" in line
    assert "stale" not in line
