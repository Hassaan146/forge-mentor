"""Forge Mentor — reading review findings.

Decision 005 puts review in the loop: every step is pushed, reviewed, and
fixed before it counts as done. This module is the "read the review" half.

**Two reviewers, because they do not find the same things** (decision 025).
CodeRabbit pulls on security, bug risk and data integrity; Sourcery was built
as a Python refactoring engine and pulls on complexity, duplication and test
quality. On pull request #1 Sourcery was the one that caught the governor
comparing path substrings — a bug in the product's core guarantee. Both are
read into one file, each finding tagged with who raised it, so "is this step
clean?" stays a single question with a single answer (decision 009).

**Both halves of a review are read, not just the inline comments.** A reviewer
posts findings in two places: pinned to a line, and in the body of the review
itself. Sourcery puts most of its work in the body. Reading only inline
comments returned an almost empty file and looked like approval.

**Why there is no second login.** Both reviewers post to GitHub, and Forge
already holds GitHub access from `/forge:start` (decision 014). So findings are
fetched with the credentials Forge already has — the user is never asked to
sign in to a review service, now or later. One login covers all of it.

The one thing that cannot be automated is the initial app install: GitHub
requires a human to authorise it. So Forge *detects* which reviewers are
installed and *guides* the user through the missing ones once.

**Findings land in a file, not an inbox.** Reviews are written to
`.forge/reviews/pr-<n>.md` — committed with the code, readable months later,
and available to a session on another machine (decision 011). An email would
be none of those things. A workflow in the repository keeps that file current
without anyone having to ask (decision 026).
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

import forge_state as fs
import safety

API = "https://api.github.com"
REVIEWS_DIR = "reviews"

# The reviewers Forge reads, and how to recognise their accounts. Decision 025.
#
# **Anchored, and that is the point.** These patterns decide whose comments
# become findings and whether a step is allowed to close. A substring match
# meant any public account containing the word — `coderabbit-fan` — could post
# a comment that Forge would file as a reviewer finding, and could satisfy the
# "has this repository been reviewed?" check on its own. The repository is
# public (decision 007), so registering such an account is trivial. Only the
# real bot logins, with the optional suffix GitHub adds to app accounts.
REVIEWERS: dict[str, re.Pattern[str]] = {
    "coderabbit": re.compile(r"^coderabbitai(\[bot\])?$", re.IGNORECASE),
    "sourcery": re.compile(r"^sourcery-ai(\[bot\])?$", re.IGNORECASE),
}

# Kept as a name so callers reading "any reviewer at all?" stay readable. Each
# alternative carries its own anchors, so the union is anchored too.
REVIEWER_PATTERN = re.compile(
    "|".join(f"(?:{p.pattern})" for p in REVIEWERS.values()), re.IGNORECASE
)

# A reviewer marks a finding it has confirmed as fixed. Worth separating so a
# user reading the file is not handed work that is already done.
RESOLVED_MARKER = re.compile(r"(✅\s*Addressed in|marked as resolved|已解决)", re.IGNORECASE)


def reviewer_of(login: str) -> str | None:
    """Which reviewer this GitHub account is, if it is one of ours."""
    for name, pattern in REVIEWERS.items():
        if pattern.search(login or ""):
            return name
    return None

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
    reviewer: str = "coderabbit"

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
    reviewers: list[str] = field(default_factory=list)

    @property
    def open_findings(self) -> list[Finding]:
        return [f for f in self.findings if not f.resolved]

    def open_by_reviewer(self, name: str) -> list[Finding]:
        return [f for f in self.open_findings if f.reviewer == name]

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


def _get_all(path: str, token: str | None, pages: int = 10) -> list:
    """Every page of a list endpoint, not just the first.

    GitHub caps a page at 100. A phase with more than a hundred comments would
    otherwise report a short count and could read as clean when it is not —
    which is exactly the number decision 009 gates a step on. Pull request #4
    reached 43 in one pass, so the cap is nearer than it looks.
    """
    out: list = []
    separator = "&" if "?" in path else "?"
    for page in range(1, pages + 1):
        chunk = _get(f"{path}{separator}per_page=100&page={page}", token)
        if not isinstance(chunk, list) or not chunk:
            break
        out.extend(chunk)
        if len(chunk) < 100:
            break
    return out


def valid_pr(pr: object) -> int:
    """A pull request number, proven to be one.

    It reaches a URL path and a filename, so a value that is not a plain
    positive integer is both a request-forgery and a path-traversal shape.
    The type annotation does not enforce this: the number arrives from an MCP
    tool call, where the caller is a model.
    """
    try:
        number = int(str(pr).strip())
    except (TypeError, ValueError):
        raise ReviewError(f"Not a pull request number: {pr!r}") from None
    if number <= 0:
        raise ReviewError(f"Not a pull request number: {pr!r}")
    return number


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

    # The trailing ".git" is stripped explicitly rather than by excluding dots
    # from the name, which truncated any repository with a dot in it —
    # "forge.dev" became "forge".
    match = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?/?$", result.stdout.strip())
    return match.group(1) if match else None


# --------------------------------------------------------------------------
# is the reviewer set up? — detect and guide, never nag
# --------------------------------------------------------------------------

# Where each reviewer is installed from, and how to make it look at work that
# is already open. Both are free on public repositories (decision 007).
INSTALL: dict[str, tuple[str, str]] = {
    "coderabbit": ("https://github.com/apps/coderabbitai", "@coderabbitai full review"),
    "sourcery": ("https://github.com/apps/sourcery-ai", "@sourcery-ai review"),
}

SETUP_GUIDE = """\
The review step needs {names}, and {verb} not on this repository yet.

{steps}
Both are free on public repositories.

You will not be asked to sign in again — Forge reads the findings through the
GitHub access it already has.

To review the pull requests that are already open, comment on each one:

{commands}
"""


def _setup_guide(missing: list[str], repo: str) -> str:
    steps = []
    commands = []
    for index, name in enumerate(missing, start=1):
        url, command = INSTALL[name]
        steps.append(
            f"  {index}. Open  {url}\n"
            f'     Choose "Only select repositories", pick {repo}, and authorise.\n'
        )
        commands.append(f"  {command}")
    return SETUP_GUIDE.format(
        names=" and ".join(missing),
        verb="is" if len(missing) == 1 else "are",
        steps="\n".join(steps),
        commands="\n".join(commands),
    )


def check_setup(project: Path) -> dict[str, object]:
    """Which reviewers have ever spoken on this repository?

    Asked by looking for their comments rather than by querying the app
    installation, because that endpoint needs app-level credentials a user
    token does not have.

    Ready means *both* reviewers have been seen (decision 025). One reviewer
    working is not the bar, because the two look at different things.
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

    seen: set[str] = set()
    for pull in pulls if isinstance(pulls, list) else []:
        for endpoint in (
            f"repos/{repo}/issues/{pull['number']}/comments",
            f"repos/{repo}/pulls/{pull['number']}/reviews",
        ):
            try:
                entries = _get_all(endpoint, token)
            except ReviewError:
                continue  # one unreadable pull request must not hide the rest
            for entry in entries if isinstance(entries, list) else []:
                who = reviewer_of(entry.get("user", {}).get("login", ""))
                if who:
                    seen.add(who)
        if seen >= set(REVIEWERS):
            break

    missing = sorted(set(REVIEWERS) - seen)
    if not missing:
        return {"ready": True, "repo": repo, "reviewers": sorted(seen)}

    return {
        "ready": False,
        "repo": repo,
        "reviewers": sorted(seen),
        "missing": missing,
        "reason": (
            f"{' and '.join(missing)} "
            f"{'has' if len(missing) == 1 else 'have'} not reviewed anything here."
        ),
        "guide": _setup_guide(missing, repo),
    }


# --------------------------------------------------------------------------
# fetching the findings
# --------------------------------------------------------------------------


# Sourcery opens a comment with its own label, as seen on pull request #1:
# "**issue (bug_risk):**", "**suggestion (testing):**", "**nitpick (typo):**".
# The leading asterisks are markdown bold and are part of the literal text, so
# they have to be allowed for. Note the ordering is the reverse of CodeRabbit's
# badge: here the severity comes first and the category sits in brackets.
_SOURCERY_PREFIX = re.compile(
    r"^[\s*_]*(issue|suggestion|nitpick)\s*\(([a-z0-9_ -]+)\)\s*:",
    re.IGNORECASE | re.MULTILINE,
)


def classify(body: str, reviewer: str = "coderabbit") -> str:
    """How serious the finding is, read from the reviewer's own labelling.

    The two reviewers label differently, so the reviewer has to be known. Both
    carry a category and a severity, and confusing the two is the trap: reading
    the category as the severity marked every security-flavoured note critical,
    which buries the ones that really are.

    Most Sourcery labels come out the same under the generic rules below, but
    only by coincidence — its severity words happen to be in `SEVERITY_ORDER`,
    so a substring check lands on the right answer for the wrong reason. Parsed
    properly here so that a category Sourcery has not used yet does not quietly
    fall through to "suggestion". The one case where the two readings differ
    today is a `(security)` category, which outranks whatever word precedes it.
    """
    head = body.lower()[:400]

    if reviewer == "sourcery":
        match = _SOURCERY_PREFIX.search(body)
        if match:
            kind, category = match.group(1).lower(), match.group(2).lower()
            if "security" in category:
                return "critical"
            if kind == "nitpick":
                return "nitpick"
            if kind == "issue":
                # Sourcery reserves "issue" for something it believes is wrong,
                # as against a style preference.
                return "bug_risk" if ("bug" in category or "risk" in category) else "issue"
            return "suggestion"

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


# Sourcery's review body opens with high-level feedback and then repeats every
# inline comment under this heading. Everything from here down is a duplicate.
_INDIVIDUAL_COMMENTS = re.compile(r"^#+\s*Individual Comments", re.IGNORECASE | re.MULTILINE)


def overall_feedback(body: str) -> str:
    """The part of a review body that is not a copy of the inline comments.

    Sourcery's body duplicates all of its inline findings; only the text above
    the "Individual Comments" heading is unique to it. Keeping the whole body
    would show every Sourcery finding twice — once as a finding to fix and once
    buried in a wall of quoted text.
    """
    text = clean_body(body)
    split = _INDIVIDUAL_COMMENTS.split(text, maxsplit=1)
    return split[0].strip()


def fetch(repo: str, pr: int, token: str | None = None) -> Review:
    """Every finding on one pull request, from every reviewer Forge reads.

    **Findings come from inline comments only** (decision 025). Review bodies
    are kept as summaries: CodeRabbit's is a walkthrough with no findings in it,
    and Sourcery's repeats each of its inline comments verbatim. Counting the
    bodies as findings double-counted every Sourcery item, and a doubled count
    feeding decision 009's "is it clean" bar is worse than no count.
    """
    pr = valid_pr(pr)
    token = token or github_token()

    details = _get(f"repos/{repo}/pulls/{pr}", token)
    review = Review(pr=pr, title=details.get("title", "") if isinstance(details, dict) else "")

    inline = _get_all(f"repos/{repo}/pulls/{pr}/comments", token)
    for comment in inline if isinstance(inline, list) else []:
        who = reviewer_of(comment.get("user", {}).get("login", ""))
        if who is None:
            continue
        body = comment.get("body", "")
        review.findings.append(
            Finding(
                path=comment.get("path", "?"),
                line=comment.get("line") or comment.get("original_line") or "?",
                body=body,
                severity=classify(body, who),
                resolved=bool(RESOLVED_MARKER.search(body)),
                url=comment.get("html_url", ""),
                reviewer=who,
            )
        )

    # The bodies — read for the high-level feedback that appears nowhere else,
    # and to know which reviewers actually looked at this pull request.
    summaries: list[str] = []
    bodies = _get_all(f"repos/{repo}/pulls/{pr}/reviews", token)
    for entry in bodies if isinstance(bodies, list) else []:
        who = reviewer_of(entry.get("user", {}).get("login", ""))
        if who is None:
            continue
        if who not in review.reviewers:
            review.reviewers.append(who)
        overall = overall_feedback(entry.get("body", ""))
        if overall:
            summaries.append(f"**{who}** — {overall}")

    for finding in review.findings:
        if finding.reviewer not in review.reviewers:
            review.reviewers.append(finding.reviewer)

    review.reviewers.sort()
    review.summary = "\n\n".join(summaries)

    review.findings.sort(
        key=lambda f: (
            f.resolved,
            SEVERITY_ORDER.index(f.severity) if f.severity in SEVERITY_ORDER else 99,
            f.path,
            f.reviewer,
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
    reviewers = review.reviewers or sorted({f.reviewer for f in review.findings})
    lines = [
        "---",
        "type: review",
        f"pr: {review.pr}",
        f"reviewers: [{', '.join(reviewers)}]",
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
        split = " · ".join(
            f"{len(review.open_by_reviewer(name))} {name}"
            for name in reviewers
            if review.open_by_reviewer(name)
        )
        lines += [
            f"**{len(review.open_findings)} open** ({split}) "
            f"· {len(review.resolved_findings)} already addressed",
            "",
            "Decision 009: a step is not finished until the review is clean.",
            "",
        ]

    if len(reviewers) < len(REVIEWERS):
        missing = sorted(set(REVIEWERS) - set(reviewers))
        lines += [
            f"> Not reviewed by: {', '.join(missing)}. "
            "This pull request has only been seen by some of the reviewers.",
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
                f"- `{finding.path}:{finding.line}` — {finding.title} _({finding.reviewer})_"
            )
        lines.append("")

    if review.summary:
        # Kept apart from the findings on purpose: this is the reviewer's
        # high-level read, not a list of things to tick off.
        lines += ["## High-level feedback", ""]
        lines.append(
            safety.wrap_untrusted(f"review:summary:pr-{review.pr}", review.summary)
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
    body = safety.wrap_untrusted(
        f"review:{finding.reviewer}:{finding.path}", clean_body(finding.body)
    )
    return [
        f"### `{finding.path}:{finding.line}` — {finding.severity} _({finding.reviewer})_",
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
    pr = valid_pr(pr)
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
        "reviewers": review.reviewers,
        "open_by_reviewer": {
            name: len(review.open_by_reviewer(name)) for name in review.reviewers
        },
        "titles": [f"{f.title} ({f.reviewer})" for f in review.open_findings],
    }


def _main(argv: list[str]) -> int:  # pragma: no cover - CLI surface
    """Fetch one pull request's review into the project's notes.

    Used by the workflow in decision 026, which runs this on GitHub's side when
    a review is posted, so the file stays current without anyone asking.

        python scripts/forge_review.py <pr> [project-root]
    """
    if not argv:
        print("usage: forge_review.py <pr-number> [project-root]")
        return 2

    try:
        pr = int(argv[0])
    except ValueError:
        print(f"Not a pull request number: {argv[0]!r}")
        return 2

    project = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd()
    forge_dir = project / fs.FORGE_DIR

    try:
        result = fetch_and_save(project, forge_dir, pr)
    except ReviewError as exc:
        print(f"Could not read the review: {exc}")
        return 1

    split = ", ".join(
        f"{count} {name}" for name, count in result["open_by_reviewer"].items()
    )
    print(f"{result['file']}: {result['open']} open ({split or 'none'})")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI surface
    import sys

    raise SystemExit(_main(sys.argv[1:]))
