"""Forge Mentor — reading review findings.

Decision 005 puts review in the loop: every step is pushed, reviewed, and
fixed before it counts as done. This module is the "read the review" half.

**Why there is no second login.** CodeRabbit posts its findings to GitHub.
Forge already holds GitHub access from `/forge:start` (decision 014). So the
findings are fetched with the credentials Forge already has — the user is never
asked to sign in to a review service, now or later. One login covers both.

The one thing that cannot be automated is the initial app install: GitHub
requires a human to authorise it. So Forge *detects* whether it is installed
and *guides* the user through it once, rather than asking repeatedly.

**Findings land in a file, not an inbox.** Reviews are written to
`.forge/reviews/pr-<n>.md` — committed with the code, readable months later,
and available to a session on another machine (decision 011). An email would
be none of those things.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import safety

API = "https://api.github.com"
REVIEWS_DIR = "reviews"

# CodeRabbit's bot account. Matched loosely because the exact login has varied
# ("coderabbitai", "coderabbitai[bot]").
REVIEWER_PATTERN = re.compile(r"coderabbit", re.IGNORECASE)

# CodeRabbit marks a finding it has confirmed as fixed. Worth separating so a
# user reading the file is not handed work that is already done.
RESOLVED_MARKER = re.compile(r"✅\s*Addressed in", re.IGNORECASE)

SEVERITY_ORDER = ("critical", "security", "bug_risk", "issue", "suggestion", "nitpick")

# The reviewer prefixes each comment with a badge line such as
# "Security & Privacy | Critical | Heavy lift". It is decoration, not the
# finding — treating it as the description made every finding look the same.
_IS_BADGE = re.compile(r"^[^\w]*\w[\w &/]*\|.*\|", re.UNICODE)


class ReviewError(Exception):
    """Something went wrong reaching the review. Carries what to do about it."""


@dataclass
class Finding:
    """One review comment, as it will be read by a person."""

    path: str
    line: int | str
    body: str
    severity: str = "suggestion"
    resolved: bool = False
    url: str = ""

    @property
    def title(self) -> str:
        """What this finding is, in one phrase.

        Skips the reviewer's severity badge line, which is decoration rather
        than a description — reading it as the title made every finding look
        identical in the summary.
        """
        for raw in clean_body(self.body).splitlines():
            line = re.sub(r"[*_`#]", "", raw).strip()
            if not line or _IS_BADGE.match(line):
                continue
            return line[:120]
        return "(no description)"


@dataclass
class Review:
    """Every finding on one pull request."""

    pr: int
    title: str = ""
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""

    @property
    def open_findings(self) -> list[Finding]:
        return [f for f in self.findings if not f.resolved]

    @property
    def resolved_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.resolved]

    @property
    def is_clean(self) -> bool:
        """Decision 009: a step is not finished until the review is clean."""
        return not self.open_findings


# --------------------------------------------------------------------------
# talking to GitHub with the credentials Forge already has
# --------------------------------------------------------------------------


def github_token() -> str | None:
    """The GitHub credential, from the places it normally lives.

    Never asks the user to type one. Decision 014: delegated sign-in, never a
    typed secret.
    """
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        token = os.environ.get(name)
        if token:
            return token

    # The GitHub CLI keeps a token once the user has signed in with it.
    for command in (["gh", "auth", "token"], ["gh.exe", "auth", "token"]):
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
    return None


def _get(path: str, token: str | None) -> list | dict:
    request = urllib.request.Request(
        f"{API}/{path.lstrip('/')}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "forge-mentor",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise ReviewError(
                "GitHub refused the request.\n"
                "  → run: gh auth login\n"
                "  Forge uses the sign-in you already have; it never asks for a token."
            ) from exc
        if exc.code == 404:
            raise ReviewError(f"Not found on GitHub: {path}") from exc
        raise ReviewError(f"GitHub returned {exc.code} for {path}") from exc
    except urllib.error.URLError as exc:
        raise ReviewError(f"Could not reach GitHub: {exc.reason}") from exc


def detect_repo(project: Path) -> str | None:
    """The owner/repo this project pushes to, read from git."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None

    match = re.search(r"github\.com[:/]([^/]+/[^/\s.]+)", result.stdout.strip())
    return match.group(1) if match else None


# --------------------------------------------------------------------------
# is the reviewer set up? — detect and guide, never nag
# --------------------------------------------------------------------------

SETUP_GUIDE = """\
The review step needs CodeRabbit, and it is not on this repository yet.

  1. Open  https://github.com/apps/coderabbitai
  2. Choose "Only select repositories" and pick {repo}
  3. Authorise

It is free on public repositories.

You will not be asked to sign in to it again — Forge reads the findings
through the GitHub access it already has.

To review the pull requests that are already open, comment on each one:

  @coderabbitai full review
"""


def check_setup(project: Path) -> dict[str, object]:
    """Has the reviewer ever spoken on this repository?

    Asked by looking for its comments rather than by querying the app
    installation, because that endpoint needs app-level credentials a user
    token does not have.
    """
    repo = detect_repo(project)
    if repo is None:
        return {
            "ready": False,
            "reason": "This project has no GitHub remote yet.",
            "guide": "Connect a repository first — run /forge:start.",
        }

    token = github_token()
    if token is None:
        return {
            "ready": False,
            "repo": repo,
            "reason": "Forge has no GitHub access yet.",
            "guide": "Run: gh auth login",
        }

    try:
        pulls = _get(f"repos/{repo}/pulls?state=all&per_page=10", token)
    except ReviewError as exc:
        return {"ready": False, "repo": repo, "reason": str(exc), "guide": str(exc)}

    for pull in pulls if isinstance(pulls, list) else []:
        comments = _get(f"repos/{repo}/issues/{pull['number']}/comments", token)
        if any(
            REVIEWER_PATTERN.search(c.get("user", {}).get("login", ""))
            for c in (comments if isinstance(comments, list) else [])
        ):
            return {"ready": True, "repo": repo}

    return {
        "ready": False,
        "repo": repo,
        "reason": "CodeRabbit has not reviewed anything on this repository.",
        "guide": SETUP_GUIDE.format(repo=repo),
    }


# --------------------------------------------------------------------------
# fetching the findings
# --------------------------------------------------------------------------


def classify(body: str) -> str:
    """How serious the finding is, read from the reviewer's own badge.

    The badge carries two different things — a category ("Security & Privacy")
    and a severity ("Critical", "Major"). Only the severity says how urgent this
    is. Reading the category as the severity marked every security-flavoured
    note critical, which would bury the ones that really are.
    """
    head = body.lower()[:400]

    for word, level in (
        ("critical", "critical"),
        ("major", "bug_risk"),
        ("minor", "suggestion"),
        ("trivial", "nitpick"),
    ):
        if word in head:
            return level

    # Older comment styles label themselves inline instead.
    for level in SEVERITY_ORDER:
        if f"**{level}" in head or f"({level})" in head or f"{level}:" in head:
            return level
    return "suggestion"


def fetch(repo: str, pr: int, token: str | None = None) -> Review:
    """Every review comment on one pull request."""
    token = token or github_token()

    details = _get(f"repos/{repo}/pulls/{pr}", token)
    review = Review(pr=pr, title=details.get("title", "") if isinstance(details, dict) else "")

    inline = _get(f"repos/{repo}/pulls/{pr}/comments?per_page=100", token)
    for comment in inline if isinstance(inline, list) else []:
        if not REVIEWER_PATTERN.search(comment.get("user", {}).get("login", "")):
            continue
        body = comment.get("body", "")
        review.findings.append(
            Finding(
                path=comment.get("path", "?"),
                line=comment.get("line") or comment.get("original_line") or "?",
                body=body,
                severity=classify(body),
                resolved=bool(RESOLVED_MARKER.search(body)),
                url=comment.get("html_url", ""),
            )
        )

    review.findings.sort(
        key=lambda f: (
            f.resolved,
            SEVERITY_ORDER.index(f.severity) if f.severity in SEVERITY_ORDER else 99,
            f.path,
        )
    )
    return review


# --------------------------------------------------------------------------
# writing it where a person will actually read it
# --------------------------------------------------------------------------


def to_markdown(review: Review, repo: str = "") -> str:
    """The findings as a document, not a notification.

    Committed with the code so it can be read months later, and by a session on
    another machine (decision 011).
    """
    lines = [
        "---",
        "type: review",
        f"pr: {review.pr}",
        f"reviewer: coderabbit",
        f"open: {len(review.open_findings)}",
        f"resolved: {len(review.resolved_findings)}",
        f"clean: {'true' if review.is_clean else 'false'}",
        f"fetched: {datetime.now().isoformat(timespec='seconds')}",
        "---",
        "",
        f"# Review — pull request #{review.pr}",
        "",
    ]
    if review.title:
        lines += [f"**{review.title}**", ""]

    if review.is_clean:
        lines += [
            "No open findings. By decision 009, the review bar for this step is met.",
            "",
        ]
    else:
        lines += [
            f"**{len(review.open_findings)} open** · {len(review.resolved_findings)} already addressed",
            "",
            "Decision 009: a step is not finished until the review is clean.",
            "",
        ]

    if review.open_findings:
        lines += ["## Open", ""]
        for finding in review.open_findings:
            lines += _finding_block(finding)

    if review.resolved_findings:
        lines += ["## Already addressed", ""]
        for finding in review.resolved_findings:
            lines.append(
                f"- `{finding.path}:{finding.line}` — {finding.title}"
            )
        lines.append("")

    if repo:
        lines += [
            "---",
            "",
            f"Source: https://github.com/{repo}/pull/{review.pr}",
            "",
        ]
    return "\n".join(lines)


def clean_body(body: str) -> str:
    """The finding itself, without the reviewer's working notes.

    Review comments carry collapsed `<details>` blocks holding the shell
    commands the reviewer ran. Useful to it, noise to a person reading the
    file — and they buried the actual findings when this was first written.
    """
    text = re.sub(r"<details>.*?</details>", "", body, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"</details>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _finding_block(finding: Finding) -> list[str]:
    # Wrapped as untrusted: this text comes from outside, the repository is
    # public (decision 007), and it is read by the model that applies the fix.
    # Challenge finding C3 — data, never instructions.
    body = safety.wrap_untrusted(f"review:pr-comment:{finding.path}", clean_body(finding.body))
    return [
        f"### `{finding.path}:{finding.line}` — {finding.severity}",
        "",
        body,
        "",
        *([f"[view on github]({finding.url})", ""] if finding.url else []),
    ]


def save(forge_dir: Path, review: Review, repo: str = "") -> Path:
    """Write the review into the project's own notes."""
    folder = forge_dir / REVIEWS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"pr-{review.pr}.md"
    path.write_text(to_markdown(review, repo), encoding="utf-8")
    return path


def fetch_and_save(project: Path, forge_dir: Path, pr: int) -> dict[str, object]:
    """The whole loop: read the review, write it down, say what is left."""
    repo = detect_repo(project)
    if repo is None:
        raise ReviewError("This project has no GitHub remote.")

    review = fetch(repo, pr)
    path = save(forge_dir, review, repo)
    return {
        "pr": pr,
        "file": str(path),
        "open": len(review.open_findings),
        "resolved": len(review.resolved_findings),
        "clean": review.is_clean,
        "titles": [f.title for f in review.open_findings],
    }
