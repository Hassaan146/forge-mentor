"""Forge Mentor — the state layer.

Everything Forge knows lives in `.forge/` inside the user's own repository,
committed with the code. There is no database and no hidden state.

Design constraints this module exists to satisfy:

  decision 001  both files are readable documents with a strict labelled
                header. A hand edit may break them, so a broken file must
                say exactly what is wrong — never guess.
  decision 011  a fresh session on another account must be able to read
                these files and carry on. That requires in-flight state,
                not only finished decisions.
  decision 016  `.forge/` is committed, never ignored.
  decision 004  the governor reads `open_question` here to decide whether
                code may be written.

The header is the machine contract; the body is for the human. Both live in
the same file so neither can drift from the other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

FORGE_DIR = ".forge"
PROGRESS = "progress.md"
DECISIONS = "decisions"
SETTINGS = "settings.md"

# Fields the governor depends on. Missing any of these is a broken file, not
# a default — guessing here would silently disable the product's guarantee.
REQUIRED_PROGRESS_FIELDS = ("stage", "open_question", "override_active")

_TRUE = {"true", "yes", "1", "on"}
_NONE = {"", "none", "null", "-"}


class StateError(Exception):
    """A state file could not be trusted.

    Carries a repair instruction. Decision 001 requires Forge to say what is
    wrong and how to fix it; challenge finding H1 requires that a user can
    always recover, because a broken file plus fail-closed would otherwise
    strand them in their own project.
    """

    def __init__(self, problem: str, path: Path, repair: str | None = None) -> None:
        rel = _repo_relative(path)
        fix = repair or f"git checkout -- {rel}"
        super().__init__(f"{problem}\n  file: {rel}\n  fix:  {fix}")
        self.problem = problem
        self.path = path
        self.repair = fix


def _repo_relative(path: Path) -> str:
    """Show a short path — absolute paths in error text are noise."""
    parts = path.as_posix().split(f"/{FORGE_DIR}/")
    return f"{FORGE_DIR}/{parts[-1]}" if len(parts) > 1 else path.name


# --------------------------------------------------------------------------
# the labelled header
# --------------------------------------------------------------------------


def parse_header(text: str, path: Path) -> tuple[dict[str, str], str]:
    """Split a Forge file into its labelled header and its body.

    Deliberately small: `key: value` per line, no nesting, no types. A format
    a person can repair by hand is worth more here than an expressive one,
    because these files are edited by humans and read by a machine that must
    fail loudly rather than interpret creatively.
    """
    if not text.startswith("---"):
        raise StateError("The labelled section at the top is missing.", path)

    end = text.find("\n---", 3)
    if end == -1:
        raise StateError("The labelled section at the top is not closed.", path)

    header: dict[str, str] = {}
    for raw in text[3:end].splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise StateError(
                f"Line {line!r} in the labelled section is missing a colon.", path
            )
        key, _, value = line.partition(":")
        header[key.strip()] = value.strip()

    body = text[end + 4 :].lstrip("\n")
    return header, body


def render_header(fields: dict[str, str]) -> str:
    lines = "\n".join(f"{k}: {v}" for k, v in fields.items())
    return f"---\n{lines}\n---\n"


# --------------------------------------------------------------------------
# progress — the live state
# --------------------------------------------------------------------------


@dataclass
class Progress:
    """Where the project is right now.

    `open_question` is the field the governor reads. When it names a question,
    code is blocked. When it is `none`, code may be written.
    """

    stage: str = "foundation-interrogation"
    open_question: str = "none"
    override_active: bool = False
    questions_answered: int = 0
    questions_total_estimate: int = 0
    current_step: str = ""
    next_action: str = ""
    updated: str = field(default_factory=lambda: date.today().isoformat())
    body: str = ""

    # -- derived ----------------------------------------------------------

    @property
    def has_open_question(self) -> bool:
        return self.open_question.strip().lower() not in _NONE

    @property
    def writes_allowed(self) -> bool:
        """The governor's rule, in one place so it cannot be restated wrongly."""
        return self.override_active or not self.has_open_question

    def resume_line(self, open_question: str | None = None) -> str:
        """What a brand-new session on another account says first.

        Decision 011: nothing is retyped, nothing is re-explained.

        The open question is passed in rather than read from this file. Since
        decision 018 the records are the authority, and reading the summary
        field here would show a stale question on exactly the account-switch
        path decision 011 exists to protect.
        """
        if open_question:
            return f"Open question: {open_question}"
        if self.current_step:
            return f"In progress: {self.current_step}"
        if self.next_action:
            return f"Next: {self.next_action}"
        return f"Stage: {self.stage}"

    # -- io ---------------------------------------------------------------

    @classmethod
    def read(cls, forge_dir: Path) -> "Progress":
        path = forge_dir / PROGRESS
        if not path.exists():
            raise StateError(
                "No progress file. This project has no Forge notes yet.",
                path,
                repair="run /forge:start",
            )

        header, body = parse_header(
            path.read_text(encoding="utf-8", errors="replace"), path
        )

        missing = [f for f in REQUIRED_PROGRESS_FIELDS if f not in header]
        if missing:
            raise StateError(
                f"The labelled section is missing: {', '.join(missing)}.", path
            )

        return cls(
            stage=header.get("stage", ""),
            open_question=header.get("open_question", "none"),
            override_active=header.get("override_active", "").lower() in _TRUE,
            questions_answered=_int(header.get("questions_answered")),
            questions_total_estimate=_int(header.get("questions_total_estimate")),
            current_step=header.get("current_step", ""),
            next_action=header.get("next_action", ""),
            updated=header.get("updated", ""),
            body=body,
        )

    def write(self, forge_dir: Path) -> Path:
        path = forge_dir / PROGRESS
        path.parent.mkdir(parents=True, exist_ok=True)
        header = render_header(
            {
                "type": "progress",
                "stage": self.stage,
                "open_question": self.open_question or "none",
                "override_active": "true" if self.override_active else "false",
                "questions_answered": str(self.questions_answered),
                "questions_total_estimate": str(self.questions_total_estimate),
                "current_step": self.current_step,
                "next_action": self.next_action,
                "updated": date.today().isoformat(),
            }
        )
        path.write_text(header + "\n" + (self.body or "# Where we are\n"), encoding="utf-8")
        return path


def _known_status(value: str, path: Path) -> str:
    """A status Forge understands, or a named failure.

    Anything else was accepted and stored as-is. Since `open_question` only
    treats "open" as pending, a record reading `status: pending` counted as
    settled — and the governor then allowed code past a decision nobody had
    made. A typo in a hand-edited file was enough to switch the product's one
    guarantee off, silently.
    """
    status = (value or "").strip().lower()
    if status in {STATUS_OPEN, STATUS_DECIDED}:
        return status
    raise StateError(
        f"This record's status is {value!r}, which Forge does not recognise. "
        f"It has to be {STATUS_OPEN!r} or {STATUS_DECIDED!r}.",
        path,
    )


def _strict_int(value: str | None, path: Path) -> int:
    """An id, or a named failure. Never a guess.

    `_int` below is right for the progress summary, where a missing count is a
    cosmetic gap. It is wrong for a decision id, which orders the chain and
    identifies the record the governor is waiting on.
    """
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise StateError(
            f"This record's id is not a number: {value!r}. "
            "Every decision needs an id, because the id is what orders them.",
            path,
        ) from None


def _int(value: str | None) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


# --------------------------------------------------------------------------
# decisions — the permanent record
# --------------------------------------------------------------------------


@dataclass
class Decision:
    """One recorded decision. Written once, read by people afterwards."""

    id: int
    question: str
    status: str = "decided"
    decided_by: str = "user"
    date: str = field(default_factory=lambda: date.today().isoformat())
    affects: str = ""
    body: str = ""

    _SLUG = re.compile(r"[^a-z0-9]+")

    def slug(self) -> str:
        base = self._SLUG.sub("-", self.question.lower()).strip("-")
        return f"{self.id:03d}-{base[:60].rstrip('-')}"

    def filename(self) -> str:
        return f"{self.slug()}.md"

    def write(self, forge_dir: Path) -> Path:
        path = forge_dir / DECISIONS / self.filename()
        path.parent.mkdir(parents=True, exist_ok=True)
        header = render_header(
            {
                "id": f"{self.id:03d}",
                "question": self.question,
                "status": self.status,
                "date": self.date,
                "decided_by": self.decided_by,
                "affects": self.affects,
            }
        )
        path.write_text(header + "\n" + self.body, encoding="utf-8")
        return path

    @classmethod
    def read(cls, path: Path) -> "Decision":
        header, body = parse_header(
            path.read_text(encoding="utf-8", errors="replace"), path
        )
        return cls(
            # Strict, unlike the other fields. A record whose id cannot be read
            # is not a record with a missing id — it is a file nobody can place
            # in the chain, and guessing 0 invents one that collides with the
            # default `next_decision_id` returns. This module's whole stance is
            # to fail loudly on a broken file rather than interpret it.
            id=_strict_int(header.get("id"), path),
            question=header.get("question", ""),
            status=_known_status(header.get("status", ""), path),
            decided_by=header.get("decided_by", ""),
            date=header.get("date", ""),
            affects=header.get("affects", ""),
            body=body,
        )


def list_decisions(forge_dir: Path) -> list[Decision]:
    """Every decision, oldest first. A broken record names itself and stops.

    Paths are sorted before the ids are, and that is not redundant: decision
    018 accepts that two branches can both take the same id, and Python's sort
    is stable. Sorting by filename first means two records sharing an id keep a
    deterministic order rather than depending on directory iteration.
    """
    folder = forge_dir / DECISIONS
    if not folder.is_dir():
        return []
    out = [Decision.read(p) for p in sorted(folder.glob("*.md"))]
    return sorted(out, key=lambda d: d.id)


def next_decision_id(forge_dir: Path) -> int:
    existing = list_decisions(forge_dir)
    return (max((d.id for d in existing), default=0)) + 1


# --------------------------------------------------------------------------
# the open question — computed, never stored (decision 018)
# --------------------------------------------------------------------------

STATUS_OPEN = "open"
STATUS_DECIDED = "decided"


def open_question(forge_dir: Path) -> Decision | None:
    """The question currently awaiting an answer, or None.

    Decision 018: a question becomes a file the moment it is asked, carrying
    `status: open`, and the same file flips to `decided` once answered. So the
    open question is *derived* from the folder rather than stored in a mutable
    field that two branches would fight over.

    If several are open — which merging two branches can produce — the lowest
    id wins, so the older question is settled first.
    """
    openers = [d for d in list_decisions(forge_dir) if d.status.strip().lower() == STATUS_OPEN]
    return openers[0] if openers else None


def ask(forge_dir: Path, question: str, body: str = "", affects: str = "") -> Decision:
    """Record that a question has been asked. Blocks writes until answered."""
    decision = Decision(
        id=next_decision_id(forge_dir),
        question=question,
        status=STATUS_OPEN,
        decided_by="",
        affects=affects,
        body=body or f"# {question}\n\n_Awaiting the user's decision._\n",
    )
    decision.write(forge_dir)
    return decision


def answer(forge_dir: Path, decision_id: int, body: str, decided_by: str = "user") -> Decision:
    """Flip an open question to decided, in the same file it was asked in.

    Decision 018 accepts that two branches can both take the same id, so an id
    is not a unique handle. Answering the first match meant the wrong record
    could be filled in — and then the second one could never be answered at
    all, because the first was no longer open. Where an id is ambiguous the
    open one is the only sensible target; where more than one is open, Forge
    stops rather than guessing which the user meant.
    """
    matches = [d for d in list_decisions(forge_dir) if d.id == decision_id]
    still_open = [d for d in matches if d.status.strip().lower() == STATUS_OPEN]

    if len(still_open) > 1:
        raise StateError(
            f"Two records share id {decision_id:03d} and both are open, so Forge "
            "cannot tell which one you answered. Renumber one of them.",
            forge_dir / DECISIONS,
            repair="give one of the duplicate records a new id",
        )

    for decision in still_open or matches:
        if decision.status.strip().lower() != STATUS_OPEN:
            raise StateError(
                f"Decision {decision_id:03d} is not open — it is {decision.status!r}.",
                forge_dir / DECISIONS / decision.filename(),
                repair="answer the open question instead",
            )
        decision.status = STATUS_DECIDED
        decision.decided_by = decided_by
        decision.date = date.today().isoformat()
        decision.body = body
        decision.write(forge_dir)
        return decision

    raise StateError(
        f"No decision {decision_id:03d} to answer.",
        forge_dir / DECISIONS,
        repair="check .forge/decisions/ for the right id",
    )


def writes_allowed(forge_dir: Path) -> tuple[bool, str]:
    """The governor's rule, in one place. Returns (allowed, reason_if_not).

    **Unreadable state blocks.** This used to swallow the error and carry on,
    so a damaged or missing progress file with no decision open came out as
    "writes allowed" — Forge could not tell whether a question was open and
    said yes anyway. Decision 004 is explicit that the safety path fails
    closed, and this is the safety path.
    """
    try:
        progress = Progress.read(forge_dir)
    except StateError as exc:
        return False, f"Forge cannot read its own notes, so it will not write: {exc}"

    if progress.override_active:
        return True, ""

    try:
        pending = open_question(forge_dir)
    except StateError as exc:
        return False, f"Forge cannot read a decision record, so it will not write: {exc}"

    if pending is None:
        return True, ""

    return False, pending.question


# --------------------------------------------------------------------------
# locating and creating the project's notes
# --------------------------------------------------------------------------


def find_forge_dir(start: Path) -> Path | None:
    """Find this project's `.forge/`, so Forge works from any subdirectory.

    The walk upward is **bounded**, and that bound is the point. An unbounded
    search finds a stray `.forge/` in a home directory and silently activates
    Forge in every project on the machine — the opposite of decision 014,
    which says Forge acts only where it was invited.

    The boundary is the repository root, because decision 016 puts `.forge/`
    inside the project repository. The search also never rises above the
    user's home directory, for machines where the work is not in a repo.
    """
    try:
        current = start.resolve()
    except OSError:
        return None

    try:
        home = Path.home().resolve()
    except (OSError, RuntimeError):
        home = None

    for candidate in (current, *current.parents):
        # Checked before looking for notes: the home directory is never a
        # project root, so a stray ~/.forge must not adopt everything below it.
        if home is not None and candidate == home:
            return None

        forge = candidate / FORGE_DIR
        if forge.is_dir():
            return forge

        # Stop at the repository root — a project does not extend past it.
        if (candidate / ".git").exists():
            return None
    return None


def is_forge_project(start: Path) -> bool:
    return find_forge_dir(start) is not None


def init(project_root: Path, total_questions: int = 0) -> Path:
    """Create `.forge/` for a new project. Refuses to overwrite existing notes."""
    forge = project_root / FORGE_DIR
    if forge.exists():
        raise StateError(
            "This project already has Forge notes.",
            forge / PROGRESS,
            repair="run /forge:start only once per project",
        )

    (forge / DECISIONS).mkdir(parents=True)
    Progress(
        stage="foundation-interrogation",
        questions_total_estimate=total_questions,
        next_action="begin the foundation interrogation",
        body=(
            "# Where we are\n\n"
            "Forge writes this file. You can read it, and you can fix it by hand if\n"
            "it breaks — the labelled section at the top is what the tool relies on.\n"
        ),
    ).write(forge)
    return forge
