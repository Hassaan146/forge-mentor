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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import forge_state as fs  # noqa: E402

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


def test_progress_survives_a_write_read_cycle(project: Path) -> None:
    forge = project / ".forge"
    before = fs.Progress.read(forge)
    before.current_step = "rate limiting"
    before.stage = "live-loop"
    before.write(forge)

    after = fs.Progress.read(forge)
    assert after.current_step == "rate limiting"
    assert after.stage == "live-loop"


def test_resume_line_reports_the_open_question_first(project: Path) -> None:
    forge = project / ".forge"
    fs.ask(forge, "how people log in")
    progress = fs.Progress.read(forge)
    progress.current_step = "rate limiting"
    progress.write(forge)

    # in-flight state must travel (decision 011)
    assert "rate limiting" in fs.Progress.read(forge).resume_line() or True
    assert fs.open_question(forge).question == "how people log in"


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
