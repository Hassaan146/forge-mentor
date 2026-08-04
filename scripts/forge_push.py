"""Forge Mentor — pushing, only when asked.

Decision 005 puts review in the loop, which means work has to reach GitHub. It
also means Forge is a program that can publish a user's code, and that is not a
thing to do quietly.

**Consent is per push and never inferred.** Not from the mode, not from having
pushed before, not from the user having connected a repository at setup. Every
one of those is a reason it would be *convenient* to assume, which is exactly
why none of them count. `confirmed` has to arrive from the person, for this
push, after they have been shown what goes out.

**What goes out is shown first.** `preview` lists the files, the branch, and
the remote before anything moves, because a user consenting to "push" is
consenting to something specific and cannot consent to a set they have not
seen. The public/private fork from decision 006 matters here: on a public
repository the preview is also the last moment before the code is readable by
anyone.

The secret scan is not advice. A push carrying a credential to a public
repository cannot be undone by deleting the commit — it has to be treated as
leaked and rotated. So a suspected secret stops the push outright rather than
warning, and the security floor is not overridable by a mode or a flag.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import safety


class PushError(Exception):
    """The push did not happen, and this says why."""


@dataclass
class Plan:
    """What a push would do, shown before it is allowed to happen."""

    branch: str = ""
    remote: str = ""
    files: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    ahead: int = 0

    @property
    def safe(self) -> bool:
        return not self.secrets

    def as_dict(self) -> dict[str, object]:
        return {
            "branch": self.branch,
            "remote": self.remote,
            "files": self.files,
            "commits_ahead": self.ahead,
            "blocked_by_secrets": self.secrets,
            "safe": self.safe,
        }


def _git(repo: Path, *args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except FileNotFoundError:
        raise PushError("git is not installed, so nothing can be pushed.") from None
    except subprocess.TimeoutExpired:
        raise PushError("git stopped responding.") from None


def preview(repo: Path, branch: str = "") -> Plan:
    """What would go out, without anything going out.

    Read-only by construction: every git call here reports, none of them
    publish. The user is shown this and then asked.
    """
    plan = Plan()

    # Asked separately from HEAD. A repository initialised but not yet
    # committed to has no HEAD, and reading that as "not a repository" sent the
    # user to fix something that was not wrong.
    if _git(repo, "rev-parse", "--git-dir").returncode != 0:
        raise PushError("This is not a git repository yet.")

    head = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    plan.branch = branch or (head.stdout.strip() if head.returncode == 0 else "")

    remote = _git(repo, "remote", "get-url", "origin")
    if remote.returncode != 0:
        raise PushError("There is no remote to push to. Connect one first.")
    plan.remote = remote.stdout.strip()

    # What this branch has that the remote does not. A branch never pushed has
    # no upstream, so fall back to everything on it.
    counted = _git(repo, "rev-list", "--count", f"origin/{plan.branch}..HEAD")
    if counted.returncode == 0 and counted.stdout.strip().isdigit():
        plan.ahead = int(counted.stdout.strip())
        listed = _git(repo, "diff", "--name-only", f"origin/{plan.branch}..HEAD")
    else:
        listed = _git(repo, "ls-files")
        plan.ahead = -1  # unknown: this branch is not on the remote yet

    plan.files = [line.strip() for line in listed.stdout.splitlines() if line.strip()]

    # The security floor, and it does not bend. A credential pushed to a public
    # repository is leaked the moment it lands — deleting the commit afterwards
    # does not unpublish it, it only hides it from the default view.
    plan.secrets = [path for path in plan.files if safety.is_secret_file(path, repo)]
    return plan


def push(
    repo: Path,
    *,
    confirmed: bool = False,
    branch: str = "",
) -> dict[str, object]:
    """Push, if and only if the user said so for this push.

    `confirmed` defaults to False and is never derived. A caller that wants to
    push has to pass it explicitly, which makes an accidental publish a thing
    somebody had to write on purpose.
    """
    plan = preview(repo, branch)

    if plan.secrets:
        raise PushError(
            "Stopped: these look like credential files and would be published — "
            + ", ".join(plan.secrets)
            + ".\nThis is the one rule no setting turns off. Remove them from the "
            "commit, and treat any that already left as leaked."
        )

    if not confirmed:
        return {
            "pushed": False,
            "needs_confirmation": True,
            "plan": plan.as_dict(),
            "ask": (
                f"Push {plan.ahead if plan.ahead >= 0 else len(plan.files)} "
                f"change(s) on {plan.branch} to {plan.remote}?"
            ),
        }

    result = _git(repo, "push", "origin", f"HEAD:{plan.branch}", timeout=300)
    if result.returncode != 0:
        raise PushError(f"The push was refused: {result.stderr.strip()[:300]}")

    return {"pushed": True, "branch": plan.branch, "remote": plan.remote}
