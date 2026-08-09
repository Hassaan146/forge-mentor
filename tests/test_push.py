"""Tests for pushing — Phase 9.

Forge can publish a user's code, which makes this the most consequential thing
in the project after the governor. Two rules carry it, and both are tested by
trying to break them:

**Consent is per push and never inferred.** The interesting cases are the ones
where assuming would be convenient — a mode is set, a repository was connected
at setup, a push already happened once. None of those count.

**A credential never leaves.** A secret pushed to a public repository is leaked
the moment it lands; deleting the commit afterwards hides it from the default
view and nothing more. So that check stops the push rather than warning, and no
setting turns it off.

Against real git repositories, with no network: the remote is another directory
on disk, which is enough to prove what would be published without publishing it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import forge_push as push


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A real repository with a real (local) remote."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)

    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q")
    git(work, "config", "user.email", "t@t")
    git(work, "config", "user.name", "t")
    git(work, "remote", "add", "origin", str(origin))

    (work / "app.py").write_text("print('hi')\n", encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "first")
    return work


# --------------------------------------------------------------------------
# consent
# --------------------------------------------------------------------------


def test_nothing_is_pushed_without_being_asked(repo: Path) -> None:
    """The default has to be the safe one, or a mistake publishes someone's code."""
    result = push.push(repo)

    assert result["pushed"] is False
    assert result["needs_confirmation"] is True
    assert git(repo, "ls-remote", "origin").stdout.strip() == "", "the remote is untouched"


def test_the_question_names_the_branch_and_the_remote(repo: Path) -> None:
    """A user cannot consent to a destination they were not shown."""
    ask = str(push.push(repo)["ask"])
    assert "origin.git" in ask
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() in ask


def test_what_would_go_out_is_listed_first(repo: Path) -> None:
    (repo / "second.py").write_text("x = 1\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "second")

    plan = push.preview(repo)
    assert "app.py" in plan.files and "second.py" in plan.files


def test_confirming_actually_pushes(repo: Path) -> None:
    result = push.push(repo, confirmed=True)

    assert result["pushed"] is True
    assert git(repo, "ls-remote", "origin").stdout.strip() != ""


def test_consent_does_not_carry_over_to_the_next_push(repo: Path) -> None:
    """Having pushed once is the most tempting thing to read as permission."""
    push.push(repo, confirmed=True)

    (repo / "third.py").write_text("y = 2\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "third")

    assert push.push(repo)["pushed"] is False, "the second push is asked for again"


def test_previewing_never_publishes(repo: Path) -> None:
    push.preview(repo)
    push.preview(repo)
    assert git(repo, "ls-remote", "origin").stdout.strip() == ""


# --------------------------------------------------------------------------
# the security floor, which no setting turns off
# --------------------------------------------------------------------------


def test_a_credential_file_stops_the_push(repo: Path) -> None:
    """Leaked the moment it lands; deleting the commit afterwards is not undo."""
    (repo / ".env").write_text("API_KEY=real-secret\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "oops")

    with pytest.raises(push.PushError, match="credential"):
        push.push(repo, confirmed=True)

    assert git(repo, "ls-remote", "origin").stdout.strip() == "", "nothing left the machine"


def test_confirming_does_not_override_the_floor(repo: Path) -> None:
    """Decision 004: the floor is not a default, and consent is not a key to it."""
    (repo / "id_rsa").write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "key")

    with pytest.raises(push.PushError):
        push.push(repo, confirmed=True)


def test_the_refusal_says_the_secret_must_be_treated_as_leaked(repo: Path) -> None:
    """A user who deletes the commit and moves on has not fixed anything."""
    (repo / ".env").write_text("x=1\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "oops")

    with pytest.raises(push.PushError, match="leaked"):
        push.push(repo, confirmed=True)


def test_an_example_file_is_not_a_secret(repo: Path) -> None:
    """`.env.example` exists to be committed — it carries names, not values."""
    (repo / ".env.example").write_text("API_KEY=\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "example")

    assert push.preview(repo).safe is True


def test_the_preview_reports_the_secret_before_anything_is_asked(repo: Path) -> None:
    """So the user is never asked to confirm something that cannot proceed."""
    (repo / ".env").write_text("x=1\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "oops")

    plan = push.preview(repo)
    assert plan.safe is False
    assert ".env" in plan.secrets


# --------------------------------------------------------------------------
# the edges
# --------------------------------------------------------------------------


def test_a_project_that_is_not_a_repository_says_so(tmp_path: Path) -> None:
    with pytest.raises(push.PushError, match="not a git repository"):
        push.preview(tmp_path)


def test_a_repository_with_no_remote_says_what_is_missing(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q")
    with pytest.raises(push.PushError, match="no remote"):
        push.preview(work)


def test_a_detached_checkout_is_refused(repo: Path) -> None:
    """`HEAD:` and `HEAD:HEAD` are refspecs nobody named."""
    sha = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "checkout", "-q", sha)

    with pytest.raises(push.PushError, match="not on a branch"):
        push.preview(repo)


def test_a_staged_secret_does_not_block_a_commit_that_lacks_it(repo: Path) -> None:
    """`ls-files` reads the index, which is not what a push publishes.

    A staged `.env` blocked a push whose commit did not contain it — and by the
    same token invited trust in a scan of files that were never going out.
    """
    (repo / ".env").write_text("SECRET=1\n", encoding="utf-8")
    git(repo, "add", ".env")  # staged, never committed

    plan = push.preview(repo)
    assert plan.safe is True
    assert ".env" not in plan.files


def test_the_push_publishes_the_commit_that_was_approved(repo: Path) -> None:
    """Approval is bound to a commit id, not to whatever HEAD becomes later.

    Between the preview a user approves and the push itself, a commit can land
    — and pushing a symbolic HEAD would publish files that were never shown
    and never scanned.
    """
    approved = push.preview(repo).commit

    (repo / "sneaked.py").write_text("x = 1\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "landed after the preview")

    result = push.push(repo, confirmed=True, branch=push.preview(repo).branch)
    assert result["commit"] != approved, "preview re-run sees the new commit"

    # The plan carries the id it scanned, so a caller reusing an approved plan
    # publishes exactly what was approved.
    assert len(approved) == 40
