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
`.claude/forge/reviews/pr-<n>.md`, committed with the code, readable months later,
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
# meant any public account containing the word — `coderabbit-fan`, could post
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


def _count(number: int, noun: str) -> str:
    """`1 finding` / `3 findings`.

    A small thing, but this text is the first line a user reads about their own
    work, and "1 finding(s) point at" reads as machine output rather than as
    something written for them (rule R1).
    """
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def reviewer_of(login: str) -> str | None:
    """Which reviewer this GitHub account is, if it is one of ours."""
    for name, pattern in REVIEWERS.items():
        if pattern.search(login or ""):
            return name
    return None


# --------------------------------------------------------------------------
# the third reviewer, which is not on GitHub
# --------------------------------------------------------------------------

# **Why ponytail is not in REVIEWERS above.** That table decides which GitHub
# account may raise a finding, and it is anchored precisely so no other account
# can. ponytail is not an account at all: it is a plugin running in the user's
# own session, reviewing the same diff from the same machine that wrote it.
#
# So its findings arrive by a different road and are kept in their own file,
# `pr-<n>.local.md`, which is committed like everything else in the notes. The
# combined `pr-<n>.md` is regenerated from both every time the workflow runs,
# which keeps decision 026 true (the workflow writes the review file) without
# the local findings being wiped by the next fetch, and keeps the anchored
# login check exactly as strict as it was.
LOCAL_REVIEWERS: tuple[str, ...] = ("ponytail",)

LOCAL_SUFFIX = ".local.md"

_LOCAL_HEADING = re.compile(
    r"^##\s+(?P<id>[\w.-]+)\s+·\s+(?P<state>open|fixed)\s+·\s+(?P<where>.*?)$"
)


def local_path(forge_dir: Path, pr: int) -> Path:
    return forge_dir / REVIEWS_DIR / f"pr-{valid_pr(pr)}{LOCAL_SUFFIX}"


def read_local(forge_dir: Path, pr: int) -> list[Finding]:
    """The local reviewer's findings, read back off disk.

    Read rather than remembered, like everything else (decision 019). A session
    that files three findings and ends still has them, and the fix loop in the
    next session sees the same three.
    """
    path = local_path(forge_dir, pr)
    if not path.is_file():
        return []

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    findings: list[Finding] = []
    current: Finding | None = None
    body: list[str] = []

    def close() -> None:
        if current is not None:
            current.body = "\n".join(body).strip()
            findings.append(current)

    for line in text.splitlines():
        match = _LOCAL_HEADING.match(line.strip())
        if match:
            close()
            body = []
            where = match.group("where").strip()
            file_part, _, line_part = where.rpartition(":")
            current = Finding(
                path=file_part or where,
                line=line_part if line_part.isdigit() else "",
                body="",
                severity="suggestion",
                resolved=match.group("state") == "fixed",
                reviewer="ponytail",
                thread_id=match.group("id"),
            )
            continue
        if current is not None:
            body.append(line)

    close()
    return findings


def save_local(forge_dir: Path, pr: int, findings: list[Finding]) -> Path:
    """Write the local reviewer's findings where the fix loop will find them."""
    pr = valid_pr(pr)
    path = local_path(forge_dir, pr)
    path.parent.mkdir(parents=True, exist_ok=True)

    out = [
        fs.render_header(
            {
                "type": "local-review",
                "pr": str(pr),
                "reviewer": ", ".join(sorted({f.reviewer for f in findings})) or "ponytail",
                "open": str(sum(1 for f in findings if not f.resolved)),
            }
        ),
        "",
        "# Reviewed here, not on GitHub",
        "",
        "Findings from a reviewer that runs in the session rather than as a GitHub app.",
        "They are merged into `pr-%d.md` and count towards the same gate." % pr,
        "",
    ]
    for finding in findings:
        where = f"{finding.path}:{finding.line}" if finding.line else finding.path
        out += [
            f"## {finding.thread_id} · {'fixed' if finding.resolved else 'open'} · {where}",
            "",
            finding.body.strip(),
            "",
        ]

    path.write_text("\n".join(out), encoding="utf-8")
    return path


def next_local_id(existing: list[Finding], reviewer: str = "ponytail") -> str:
    used = [f.thread_id for f in existing if f.thread_id.startswith(f"{reviewer}-")]
    numbers = [int(i.rsplit("-", 1)[-1]) for i in used if i.rsplit("-", 1)[-1].isdigit()]
    return f"{reviewer}-{(max(numbers) if numbers else 0) + 1}"


def add_local(
    forge_dir: Path, pr: int, raised: list[tuple[str, str, str]], reviewer: str = "ponytail"
) -> list[Finding]:
    """Add findings, keeping the ones already on file and their state.

    Appended rather than replaced, and this is not a detail: a second review
    pass that overwrote the file would take three findings the user had already
    answered and present them again as new.
    """
    existing = read_local(forge_dir, pr)
    seen = {(f.path, str(f.line), f.body.strip()) for f in existing}

    for path_name, line, note in raised:
        key = (path_name, str(line), note.strip())
        if key in seen:
            continue
        existing.append(
            Finding(
                path=path_name,
                line=line,
                body=note.strip(),
                reviewer=reviewer,
                thread_id=next_local_id(existing, reviewer),
            )
        )
        seen.add(key)

    save_local(forge_dir, pr, existing)
    return existing


def resolve_local(forge_dir: Path, pr: int, finding_id: str) -> bool:
    """Mark one local finding handled. Nothing is deleted."""
    findings = read_local(forge_dir, pr)
    hit = False
    for finding in findings:
        if finding.thread_id == finding_id:
            finding.resolved = True
            hit = True
    if hit:
        save_local(forge_dir, pr, findings)
    return hit

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
    raised_against: str = ""  # the commit this was written about
    thread_id: str = ""  # for resolving it on GitHub once it is handled
    stale: bool = False  # the file has moved since; needs a look, not dismissal

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
        """Findings raised against code that has not moved since.

        These apply exactly as written — nothing about them is in doubt.
        Decision 031 keeps them apart from the stale ones so that "is this
        step clean?" stays answerable.
        """
        return [f for f in self.findings if not f.resolved and not f.stale]

    @property
    def stale_findings(self) -> list[Finding]:
        """Findings whose file changed underneath them.

        **Stale means "needs a look", never "resolved".** A changed file does
        not say the finding was addressed; it says nobody can tell from
        metadata alone. Most of this project's real bugs were reported against
        an earlier commit and were entirely valid.
        """
        return [f for f in self.findings if not f.resolved and f.stale]

    def open_by_reviewer(self, name: str) -> list[Finding]:
        return [f for f in self.open_findings if f.reviewer == name]

    @property
    def resolved_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.resolved]

    @property
    def is_clean(self) -> bool:
        """Decision 009: a step is not finished until the review is clean.

        Only the findings that certainly still apply. A stale one is reported
        separately and judged, because counting it here made "clean" a state
        that fixing things could never reach (decision 031).
        """
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
            # shell=False stated rather than left to the default: the audit
            # rule that flags this cannot tell a fixed argument list from an
            # interpolated string, and saying so is cheaper than explaining it
            # on every review. There is no user input in `command`.
            result = subprocess.run(  # noqa: S603
                command, capture_output=True, text=True, timeout=10, shell=False
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
            return out
        out.extend(chunk)
        if len(chunk) < 100:
            return out

    # Every page was full, so there is probably another one. Stopping quietly
    # here would write `clean: true` from findings that were never read, and a
    # step would close on a review nobody finished — the one failure this file
    # exists to prevent. Refuse instead.
    raise ReviewError(
        f"More than {pages * 100} entries on {path}. Forge stopped rather than "
        "write a review it knows is incomplete. Raise the page limit and re-run."
    )


def _post_graphql(query: str, variables: dict, token: str | None) -> dict:
    """GraphQL, needed for the two things REST cannot do here.

    REST exposes review *comments* but not the review *threads* they belong to,
    and resolving is a thread-level act. So thread ids and the resolve mutation
    both come from here.
    """
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "forge-mentor",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ReviewError(f"GitHub returned {exc.code} for a GraphQL request.") from exc
    except urllib.error.URLError as exc:
        raise ReviewError(f"Could not reach GitHub: {exc.reason}") from exc

    if body.get("errors"):
        raise ReviewError(str(body["errors"])[:300])
    return body.get("data") or {}


_THREADS_QUERY = """
query($owner:String!, $name:String!, $pr:Int!, $after:String) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$pr) {
      reviewThreads(first:100, after:$after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          comments(first:100) { nodes { databaseId } }
        }
      }
    }
  }
}
"""


def review_threads(repo: str, pr: int, token: str | None = None) -> dict[int, str]:
    """Map each finding's comment id to the thread it lives in.

    Only unresolved threads. A resolved one needs no id, because nothing is
    going to be done to it.
    """
    owner, _, name = repo.partition("/")
    token = token or github_token()
    out: dict[int, str] = {}
    after = None

    # Both connections are paginated. A hundred threads is not a lot on a busy
    # pull request, and a comment past the cap simply had no thread id — so it
    # could never be resolved, and the count it fed never came down.
    for _ in range(20):
        try:
            data = _post_graphql(
                _THREADS_QUERY,
                {"owner": owner, "name": name, "pr": pr, "after": after},
                token,
            )
        except ReviewError:
            return out  # thread ids are a convenience; losing them must not lose the review

        threads = (
            data.get("repository", {}).get("pullRequest", {}).get("reviewThreads", {}) or {}
        )
        for thread in threads.get("nodes") or []:
            if thread.get("isResolved"):
                continue
            for comment in thread.get("comments", {}).get("nodes") or []:
                if comment.get("databaseId"):
                    out[int(comment["databaseId"])] = thread["id"]

        page = threads.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        after = page.get("endCursor")

    return out


_RESOLVE = """
mutation($id:ID!) {
  resolveReviewThread(input:{threadId:$id}) { thread { isResolved } }
}
"""


def known_threads(forge_dir: Path, pr: int) -> set[str]:
    """The thread ids that appear in this project's own review notes.

    A resolve request is only honoured for one of these. Without it the tool
    took any id at all, so a thread id from another repository — or one simply
    guessed — could be closed through the user's credentials, and neither the
    server nor the notes would have any record that a finding was handled.
    """
    path = forge_dir / REVIEWS_DIR / f"pr-{valid_pr(pr)}.md"
    if not path.is_file():
        return set()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    return set(re.findall(r"thread:\s*(\S+)", text))


def resolve_thread(
    thread_id: str,
    token: str | None = None,
    *,
    allowed: set[str] | None = None,
) -> bool:
    """Close a review thread, the same act a reviewer performs by hand.

    Decision 031: only ever called once a finding has been fixed or declined
    with a reason. A thread closed without either is a finding silently
    dropped, which is worse than a count that reads too high.

    `allowed` is the set of threads this project actually recorded. Callers
    that can supply it must, so the id is checked against something Forge
    wrote rather than taken on trust from whoever asked.
    """
    if not thread_id:
        return False
    if allowed is not None and thread_id not in allowed:
        raise ReviewError(
            "That thread is not one of this project's recorded findings, so "
            "Forge will not close it."
        )
    data = _post_graphql(_RESOLVE, {"id": thread_id}, token or github_token())
    return bool(
        data.get("resolveReviewThread", {}).get("thread", {}).get("isResolved")
    )


def changed_files(repo: str, base: str, head: str, token: str | None = None) -> set[str] | None:
    """Which files differ between two commits.

    Returns None when the comparison cannot be made, and the caller then treats
    nothing as stale — an unknown answer must never be read as "the finding
    went away".
    """
    if not base or not head or base == head:
        return set()
    try:
        data = _get(f"repos/{repo}/compare/{base}...{head}", token)
    except ReviewError:
        return None
    if not isinstance(data, dict):
        return None

    files = data.get("files") or []
    # The compare endpoint stops at 300 files and does not paginate them. A
    # file past that cap would come back "not changed", which reads as "the
    # finding still applies" — the safe direction, but the count is then a
    # guess. Report unknown instead, so nothing is marked stale on a partial
    # answer either.
    if data.get("total_commits") is not None and len(files) >= 300:
        return None
    return {entry.get("filename", "") for entry in files}


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

You will not be asked to sign in again, Forge reads the findings through the
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
            "guide": "Connect a repository first, run /forge:start.",
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
    details = details if isinstance(details, dict) else {}
    review = Review(pr=pr, title=details.get("title", ""))
    head = (details.get("head") or {}).get("sha", "")

    threads = review_threads(repo, pr, token)
    # One comparison per commit findings were raised against, not one per
    # finding — a busy pull request has dozens of comments across two or three
    # commits, and the answer is the same for all of them.
    since: dict[str, set[str] | None] = {}

    inline = _get_all(f"repos/{repo}/pulls/{pr}/comments", token)
    for comment in inline if isinstance(inline, list) else []:
        who = reviewer_of(comment.get("user", {}).get("login", ""))
        if who is None:
            continue
        body = comment.get("body", "")
        path = comment.get("path", "?")
        raised = comment.get("original_commit_id") or comment.get("commit_id") or ""

        if raised and raised not in since:
            since[raised] = changed_files(repo, raised, head, token)
        moved = since.get(raised)

        review.findings.append(
            Finding(
                path=path,
                line=comment.get("line") or comment.get("original_line") or "?",
                body=body,
                severity=classify(body, who),
                resolved=bool(RESOLVED_MARKER.search(body)),
                url=comment.get("html_url", ""),
                reviewer=who,
                raised_against=raised,
                thread_id=threads.get(comment.get("id", 0), ""),
                # Only when the comparison actually succeeded. An unknown
                # answer stays "still applies" — the safe direction, because
                # stale findings are the ones a person has to re-read.
                stale=bool(moved) and path in moved,
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
            summaries.append(f"**{who}**, {overall}")

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
        f"stale: {len(review.stale_findings)}",
        f"resolved: {len(review.resolved_findings)}",
        f"clean: {'true' if review.is_clean else 'false'}",
        f"fetched: {datetime.now().isoformat(timespec='seconds')}",
        "---",
        "",
        f"# Review, pull request #{review.pr}",
        "",
    ]
    if review.title:
        lines += [f"**{review.title}**", ""]

    if review.is_clean:
        lines += [
            "No findings that still apply as written.",
            "",
        ]
        if review.stale_findings:
            lines += [
                f"{_count(len(review.stale_findings), 'finding')} "
                f"{'sits' if len(review.stale_findings) == 1 else 'sit'} against code "
                "that has changed since. "
                "read them below before calling this step done (decision 031).",
                "",
            ]
        else:
            lines += ["By decision 009, the review bar for this step is met.", ""]
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

    if review.stale_findings:
        lines += [
            "## Raised against code that has since changed",
            "",
            f"{_count(len(review.stale_findings), 'finding')} "
            f"{'points' if len(review.stale_findings) == 1 else 'point'} at files "
            "edited after they were "
            "written. **That does not mean they are fixed**, it means nobody can tell from "
            "the pull request alone, so each needs reading against the file as it is now "
            "(decision 031). Most of this project's real bugs were reported against an "
            "earlier commit and were entirely valid.",
            "",
        ]
        for finding in review.stale_findings:
            lines += _finding_block(finding)

    if review.resolved_findings:
        lines += ["## Already addressed", ""]
        for finding in review.resolved_findings:
            lines.append(
                f"- `{finding.path}:{finding.line}`, {finding.title} _({finding.reviewer})_"
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
        f"### `{finding.path}:{finding.line}`, {finding.severity} _({finding.reviewer})_",
        "",
        *([f"thread: {finding.thread_id}", ""] if finding.thread_id else []),
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

    # The local reviewer's findings are merged in on every fetch, so the
    # combined file is rebuilt from both sources rather than one overwriting the
    # other. The workflow still owns `pr-<n>.md` (decision 026); what changed is
    # that it now assembles it from what GitHub says *and* what was raised here.
    local = read_local(forge_dir, pr)
    if local:
        review.findings.extend(local)
        for name in sorted({f.reviewer for f in local}):
            if name not in review.reviewers:
                review.reviewers.append(name)

    path = save(forge_dir, review, repo)
    return {
        "pr": pr,
        "file": str(path),
        "open": len(review.open_findings),
        "stale": len(review.stale_findings),
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
    print(
        f"{result['file']}: {result['open']} open ({split or 'none'}), "
        f"{result['stale']} against changed code"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI surface
    import sys

    raise SystemExit(_main(sys.argv[1:]))
