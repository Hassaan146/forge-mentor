"""Forge Mentor, chain repair.

Implements decisions 022 and 023: when a record has been altered or a plan
added afterwards, Forge warns, stops, and restores the record from its
committed version.

**Why repair rather than only refuse.** Decision 021 chose to detect rather
than prevent, because refusing outright could strand a user behind one damaged
old record (challenge finding H1). Repair removes that objection, enforcement
is safe when the fix is automatic.

**Where the correct version comes from.** Git. Decision 005 commits on every
step, so a good version of every record always exists. A fingerprint cannot be
reversed into text; the commit history is the only real source, and it is
already there.

**What is never done.** Nothing is deleted. A forged record with no earlier
version cannot be restored, so it is moved to `.claude/forge/quarantine/`, the chain
becomes whole, the evidence survives, and nothing is destroyed.
"""

from __future__ import annotations

import shutil
import stat
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import forge_integrity as fi
import forge_state as fs

CHAIN_FILE = "chain.log"
QUARANTINE = "quarantine"


class Remedy(str, Enum):
    """What can be done about a record that does not verify."""

    RESTORE = "restore"       # a committed version exists, put it back
    QUARANTINE = "quarantine" # never committed, move it aside
    NONE = "none"             # nothing wrong

    @property
    def description(self) -> str:
        return {
            Remedy.RESTORE: "restore the committed version",
            Remedy.QUARANTINE: "move aside, this record was never committed",
            Remedy.NONE: "nothing to do",
        }[self]


@dataclass
class Problem:
    """A record that failed verification, and what can be done about it."""

    decision_id: int
    path: Path
    integrity: fi.Integrity
    remedy: Remedy

    def describe(self) -> str:
        """Plain words, per rule R1, the user may not be technical."""
        return (
            f"Decision {self.decision_id:03d}, {self.integrity.explanation}.\n"
            f"  file:   {self.path.name}\n"
            f"  remedy: {self.remedy.description}"
        )


# --------------------------------------------------------------------------
# git, the source of the correct version
# --------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def repo_root(start: Path) -> Path | None:
    result = _git(start, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def committed_version(repo: Path, path: Path) -> str | None:
    """The file's content as last committed, or None if it was never committed."""
    try:
        relative = path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return None
    result = _git(repo, "show", f"HEAD:{relative}")
    return result.stdout if result.returncode == 0 else None


# --------------------------------------------------------------------------
# finding what is wrong
# --------------------------------------------------------------------------


def diagnose(forge_dir: Path) -> list[Problem]:
    """Every record that does not verify, with the remedy available for it."""
    repo = repo_root(forge_dir)
    problems: list[Problem] = []

    for checked in fi.check_all(forge_dir):
        if checked.trusted:
            continue

        path = forge_dir / fs.DECISIONS / checked.decision.filename()
        remedy = Remedy.QUARANTINE
        if repo is not None and committed_version(repo, path) is not None:
            remedy = Remedy.RESTORE

        problems.append(Problem(checked.decision.id, path, checked.integrity, remedy))

    return problems


def warn(problems: list[Problem]) -> str:
    """The warning shown before anything is changed (decision 022, step 1)."""
    if not problems:
        return ""
    lines = [
        "",
        "  The decision history has been altered.",
        "",
    ]
    lines += [f"  {p.describe()}\n" for p in problems]
    lines.append("  Nothing has been changed yet. Confirm to repair.")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# fixing it
# --------------------------------------------------------------------------


def restore(problem: Problem, repo: Path, forge_dir: Path) -> bool:
    """Put back the committed version of an altered record.

    **The current file is quarantined first.** This module's whole promise is
    that nothing is ever destroyed, and `quarantine` honoured it while this
    function did not, it wrote the committed text straight over whatever was
    there. What it overwrote is exactly the thing worth keeping: either
    evidence of tampering, or an edit the user made and had not committed yet.
    Neither is recoverable once it is gone.
    """
    original = committed_version(repo, problem.path)
    if original is None:
        return False

    # No default on `forge_dir`, deliberately. It was optional, and a caller
    # that omitted it skipped the quarantine and overwrote the file anyway —
    # an opt-in safeguard on the one function in this project that destroys
    # data. Now it cannot be called without somewhere to put the evidence.
    if problem.path.is_file():
        try:
            quarantine(problem, forge_dir)
        except OSError:
            # Cannot set the evidence aside, so do not destroy it either.
            return False

    _make_writable(problem.path)
    problem.path.write_text(original, encoding="utf-8")
    return True


def quarantine(problem: Problem, forge_dir: Path) -> Path:
    """Move a record aside rather than delete it.

    Deleting is irreversible and would destroy the evidence of what happened.
    Moving makes the chain whole while keeping the file for review.
    """
    folder = forge_dir / QUARANTINE
    folder.mkdir(parents=True, exist_ok=True)

    # The timestamp alone is not unique: two records quarantined in the same
    # second would collide and the first would be overwritten, destroying the
    # evidence this function exists to preserve. A counter guarantees a free name.
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = folder / f"{stamp}-{problem.path.name}"
    attempt = 2
    while destination.exists():
        destination = folder / f"{stamp}-{attempt}-{problem.path.name}"
        attempt += 1

    _make_writable(problem.path)
    shutil.move(str(problem.path), str(destination))
    return destination


def repair(forge_dir: Path, problems: list[Problem] | None = None) -> list[str]:
    """Repair every problem. Only ever called after the user confirms."""
    problems = diagnose(forge_dir) if problems is None else problems
    repo = repo_root(forge_dir)
    done: list[str] = []

    for problem in problems:
        if (
            problem.remedy is Remedy.RESTORE
            and repo is not None
            and restore(problem, repo, forge_dir)
        ):
            done.append(
                f"Decision {problem.decision_id:03d}: restored from git "
                "(the altered version was kept in quarantine)"
            )
        else:
            moved = quarantine(problem, forge_dir)
            done.append(f"Decision {problem.decision_id:03d}: moved to {moved.name}")

    write_chain(forge_dir)
    return done


def verify_after_repair(forge_dir: Path) -> bool:
    """Confirm the chain is whole again (decision 022, step 4)."""
    return not fi.untrusted(forge_dir)


# --------------------------------------------------------------------------
# the chain file, decision 023
# --------------------------------------------------------------------------


def write_chain(forge_dir: Path) -> Path:
    """Write the visible chain and mark it read-only where the OS allows.

    The read-only flag is a guard against accidents and a statement of intent.
    It is **not** a security control: file permissions do not survive a
    `git clone`, so it protects only the machine that set it. The real
    protection is the fingerprint chain, repair from git, and the commit
    history. This is recorded in decision 023 so it is never mistaken for more
    than it is.
    """
    path = forge_dir / CHAIN_FILE
    lines = [
        "# Forge decision chain, generated, do not edit",
        "# Each line: <id> <status> <fingerprint> <links-to>",
        "",
    ]
    for checked in fi.check_all(forge_dir):
        signatures = fi._read_signatures(forge_dir).get(checked.decision.id, {})
        lines.append(
            f"{checked.decision.id:03d} "
            f"{checked.decision.status:<8} "
            f"{signatures.get(fi.CONTENT_SHA, '-')[:16]} "
            f"→ {signatures.get(fi.PREV_SHA, '-')[:16]}"
        )

    _make_writable(path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _make_read_only(path)
    return path


def _make_read_only(path: Path) -> None:
    try:
        path.chmod(path.stat().st_mode & ~stat.S_IWRITE & ~stat.S_IWGRP & ~stat.S_IWOTH)
    except OSError:
        pass  # best effort by design, never fail because of a permission flag


def _make_writable(path: Path) -> None:
    try:
        if path.exists():
            path.chmod(path.stat().st_mode | stat.S_IWRITE)
    except OSError:
        pass
