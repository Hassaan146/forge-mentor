"""Tests for chain repair — decisions 022 and 023.

The behaviour under test: warn, stop, restore from the committed version, and
verify the chain is whole again. Nothing is ever deleted.

These use a real git repository rather than a mock, because the whole design
rests on git actually holding the last good version (decision 005 commits on
every step). A mock would prove the code calls git, not that the recovery works.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import forge_integrity as fi
import forge_repair as fr
import forge_state as fs


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A real git repository with one committed decision."""
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")

    fs.init(tmp_path)
    forge = tmp_path / ".forge"
    asked = fs.ask(forge, "how passwords are stored")
    fs.answer(forge, asked.id, "# Hashed with bcrypt\n\nNever plain text.\n")

    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "decision 001")
    return tmp_path


@pytest.fixture()
def forge(repo: Path) -> Path:
    return repo / ".forge"


def record_path(forge_dir: Path, decision_id: int = 1) -> Path:
    decision = next(d for d in fs.list_decisions(forge_dir) if d.id == decision_id)
    return forge_dir / fs.DECISIONS / decision.filename()


# --------------------------------------------------------------------------
# nothing wrong
# --------------------------------------------------------------------------


def test_a_clean_history_reports_no_problems(forge: Path) -> None:
    assert fr.diagnose(forge) == []
    assert fr.warn([]) == ""
    assert fr.verify_after_repair(forge)


# --------------------------------------------------------------------------
# an altered approval — the case decision 022 exists for
# --------------------------------------------------------------------------


def test_an_altered_record_is_diagnosed_as_restorable(forge: Path) -> None:
    path = record_path(forge)
    path.write_text(
        path.read_text(encoding="utf-8").replace("Hashed with bcrypt", "Plain text is fine"),
        encoding="utf-8",
    )

    problems = fr.diagnose(forge)
    assert len(problems) == 1
    assert problems[0].integrity is fi.Integrity.MODIFIED
    assert problems[0].remedy is fr.Remedy.RESTORE


def test_the_warning_names_the_record_and_the_remedy(forge: Path) -> None:
    """Rule R1 — the user must understand what they are being told."""
    path = record_path(forge)
    path.write_text(path.read_text(encoding="utf-8").replace("bcrypt", "nothing"), encoding="utf-8")

    message = fr.warn(fr.diagnose(forge))
    assert "Decision 001" in message
    assert "restore the committed version" in message
    assert "Nothing has been changed yet" in message, "must warn before it acts"


def test_repair_puts_the_committed_version_back(forge: Path) -> None:
    path = record_path(forge)
    good = path.read_text(encoding="utf-8")
    path.write_text(good.replace("Hashed with bcrypt", "Plain text is fine"), encoding="utf-8")

    fr.repair(forge)

    assert "Hashed with bcrypt" in path.read_text(encoding="utf-8")
    assert "Plain text is fine" not in path.read_text(encoding="utf-8")


def test_the_chain_is_whole_again_after_repair(forge: Path) -> None:
    path = record_path(forge)
    path.write_text(path.read_text(encoding="utf-8").replace("bcrypt", "nothing"), encoding="utf-8")

    assert not fr.verify_after_repair(forge), "broken before"
    fr.repair(forge)
    assert fr.verify_after_repair(forge), "whole after"


def test_repair_reports_what_it_did(forge: Path) -> None:
    path = record_path(forge)
    path.write_text(path.read_text(encoding="utf-8").replace("bcrypt", "nothing"), encoding="utf-8")

    assert any("restored from git" in line for line in fr.repair(forge))


# --------------------------------------------------------------------------
# a plan added afterwards — never committed, so it cannot be restored
# --------------------------------------------------------------------------


def test_a_forged_record_is_quarantined_not_deleted(forge: Path) -> None:
    """Nothing is destroyed: the evidence has to survive for review."""
    forged = forge / fs.DECISIONS / "002-my-own-plan.md"
    forged.write_text(
        "---\nid: 002\nquestion: my own plan\nstatus: decided\n---\n\n# Skip the checks\n",
        encoding="utf-8",
    )

    problems = fr.diagnose(forge)
    assert problems[0].remedy is fr.Remedy.QUARANTINE

    fr.repair(forge)

    assert not forged.exists(), "removed from the decision history"
    moved = list((forge / fr.QUARANTINE).glob("*my-own-plan.md"))
    assert len(moved) == 1, "kept for review"
    assert "Skip the checks" in moved[0].read_text(encoding="utf-8")


def test_quarantine_makes_the_chain_whole(forge: Path) -> None:
    (forge / fs.DECISIONS / "002-added-later.md").write_text(
        "---\nid: 002\nquestion: added later\nstatus: decided\n---\n\nbody\n",
        encoding="utf-8",
    )
    fr.repair(forge)
    assert fr.verify_after_repair(forge)


def test_quarantined_names_do_not_collide(forge: Path) -> None:
    for _ in range(2):
        (forge / fs.DECISIONS / "002-added-later.md").write_text(
            "---\nid: 002\nquestion: added later\nstatus: decided\n---\n\nbody\n",
            encoding="utf-8",
        )
        fr.repair(forge)
    assert len(list((forge / fr.QUARANTINE).glob("*added-later.md"))) == 2


# --------------------------------------------------------------------------
# the chain file — decision 023
# --------------------------------------------------------------------------


def test_the_chain_file_lists_every_record(forge: Path) -> None:
    fs.answer(forge, fs.ask(forge, "second question").id, "decided")
    text = fr.write_chain(forge).read_text(encoding="utf-8")
    assert "001" in text and "002" in text
    assert "do not edit" in text


def test_the_chain_file_is_marked_read_only(forge: Path) -> None:
    """A guard against accidents — never mistaken for a security control."""
    import os

    path = fr.write_chain(forge)
    assert not os.access(path, os.W_OK) or os.name == "nt" and path.stat().st_mode & 0o200 == 0


def test_writing_the_chain_twice_succeeds(forge: Path) -> None:
    """The read-only flag must not stop Forge updating its own file."""
    fr.write_chain(forge)
    fr.write_chain(forge)  # would raise if the flag were not cleared first


# --------------------------------------------------------------------------
# working outside a git repository
# --------------------------------------------------------------------------


def test_no_git_means_quarantine_rather_than_restore(tmp_path: Path) -> None:
    """Without git there is no committed version, so nothing can be restored."""
    fs.init(tmp_path)
    forge = tmp_path / ".forge"
    fs.answer(forge, fs.ask(forge, "a question").id, "decided")

    path = record_path(forge)
    path.write_text(path.read_text(encoding="utf-8").replace("decided", "changed", 1), encoding="utf-8")

    problems = fr.diagnose(forge)
    assert problems[0].remedy is fr.Remedy.QUARANTINE

    fr.repair(forge)
    assert list((forge / fr.QUARANTINE).glob("*.md")), "moved aside, not lost"


def test_repo_root_is_none_outside_a_repository(tmp_path: Path) -> None:
    assert fr.repo_root(tmp_path) is None


def test_committed_version_of_an_uncommitted_file_is_none(repo: Path) -> None:
    new = repo / "never-committed.md"
    new.write_text("x", encoding="utf-8")
    assert fr.committed_version(repo, new) is None


def test_every_remedy_explains_itself(forge: Path) -> None:
    for remedy in fr.Remedy:
        assert remedy.description
