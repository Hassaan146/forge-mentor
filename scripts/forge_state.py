"""Forge Mentor, the state layer.

Everything Forge knows lives in `.claude/forge/` inside the user's own
repository, committed with the code. There is no database and no hidden state.

Design constraints this module exists to satisfy:

  decision 001  both files are readable documents with a strict labelled
                header. A hand edit may break them, so a broken file must
                say exactly what is wrong, never guess.
  decision 011  a fresh session on another account must be able to read
                these files and carry on. That requires in-flight state,
                not only finished decisions.
  decision 016  the notes are committed, never ignored.
  decision 032  they live in `.claude/forge/`, and Forge refuses to write
                there if git is ignoring it.
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

# Under `.claude/`, alongside what Claude Code already keeps for a project, so
# turning Forge on adds one folder rather than a second unrelated one
# (decision 032). A posix-style string on purpose: `Path / "a/b"` handles the
# separator on every platform, and the literal is used in messages.
FORGE_DIR = ".claude/forge"
PROGRESS = "progress.md"
DECISIONS = "decisions"
SETTINGS = "settings.md"

# Forge is switched off in this project while this file exists.
#
# **Why a file and not a header field.** Every hook has to answer "am I on"
# before it does anything, and a file either exists or it does not: no parsing,
# nothing to be malformed, and nothing that can fail closed and lock someone
# out of their own repository. A user can create or delete it by hand and the
# answer is obvious from a directory listing.
#
# It never deletes anything. The decisions, the chain and the phases are the
# project's own history and stay exactly where they are, so switching Forge
# back on resumes rather than restarts.
PAUSED = "paused.md"


def paused(forge_dir: Path) -> bool:
    """Has the user told Forge to stop acting in this project?"""
    try:
        return (forge_dir / PAUSED).is_file()
    except OSError:
        return False

# Fields the governor depends on. Missing any of these is a broken file, not
# a default — guessing here would silently disable the product's guarantee.
REQUIRED_PROGRESS_FIELDS = ("stage", "open_question", "override_active")

_TRUE = {"true", "yes", "1", "on"}
_NONE = {"", "none", "null", "-"}

# Header keys `Decision` models as its own attributes. Anything else a record
# carries is kept in `extra` rather than discarded, so the fingerprint covers
# it — a header added later would otherwise carry meaning from outside the
# hash and be changeable without detection.
#
# The two fingerprint fields are listed here too. They are not modelled either,
# but they are the hash — a fingerprint that covered itself could never verify.
_MODELLED_HEADER_KEYS = frozenset(
    {
        "id",
        "question",
        "status",
        "decided_by",
        "date",
        "affects",
        "content_sha",
        "prev_sha",
    }
)


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
    """Show a short path, absolute paths in error text are noise."""
    text = path.as_posix()
    marker = f"/{FORGE_DIR}/"
    if marker in text:
        return f"{FORGE_DIR}/{text.split(marker)[-1]}"
    # The notes directory itself, not a file inside it. Falling through to
    # `path.name` printed a bare "forge", which names nothing a user can act on.
    if text.endswith(f"/{FORGE_DIR}"):
        return FORGE_DIR
    return path.name


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

    Note on `open_question`: decision 018 moved the authority for this out of
    the progress file and into the decision records themselves, a question is
    a record with `status: open`. The field is kept only as a readable summary
    for a person opening this file, and is written from the computed value. The
    governor and `resume_line` both take the real answer as an argument, so a
    stale field here can never decide anything.
    """

    stage: str = "foundation-interrogation"
    open_question: str = "none"
    override_active: bool = False
    questions_answered: int = 0
    questions_total_estimate: int = 0
    current_step: str = ""
    next_action: str = ""
    # Decision 009: after three failed attempts at a step, stop looping and
    # escalate to the user. Kept here so the count survives a crash, a new
    # session, or a switch to another account (decision 011).
    gate_attempts: int = 0
    updated: str = field(default_factory=lambda: date.today().isoformat())
    body: str = ""

    # -- derived ----------------------------------------------------------

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
            gate_attempts=_int(header.get("gate_attempts")),
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
                "gate_attempts": str(self.gate_attempts),
                "updated": date.today().isoformat(),
            }
        )
        path.write_text(header + "\n" + (self.body or "# Where we are\n"), encoding="utf-8")
        return path


def _known_status(value: str, path: Path) -> str:
    """A status Forge understands, or a named failure.

    Anything else was accepted and stored as-is. Since `open_question` only
    treats "open" as pending, a record reading `status: pending` counted as
    settled, and the governor then allowed code past a decision nobody had
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
    # Header keys this class does not model. Kept so the fingerprint can cover
    # them: `Decision.read` used to discard anything unrecognised, so a header
    # someone added later carried meaning and sat outside the hash entirely —
    # changeable without the fingerprint moving.
    extra: dict[str, str] = field(default_factory=dict)

    _SLUG = re.compile(r"[^a-z0-9]+")

    def slug(self) -> str:
        base = self._SLUG.sub("-", self.question.lower()).strip("-")
        return f"{self.id:03d}-{base[:60].rstrip('-')}"

    def filename(self) -> str:
        return f"{self.slug()}.md"

    def write(self, forge_dir: Path, signature: dict[str, str] | None = None) -> Path:
        """Write the record, optionally carrying its tamper-evident fields.

        Signing lives in `forge_integrity` rather than here so the state layer
        stays readable on its own; callers use `ask()` and `answer()`, which
        apply it automatically.
        """
        path = forge_dir / DECISIONS / self.filename()
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = {
            "id": f"{self.id:03d}",
            "question": self.question,
            "status": self.status,
            "date": self.date,
            "decided_by": self.decided_by,
            "affects": self.affects,
        }
        if signature:
            fields.update(signature)
        path.write_text(render_header(fields) + "\n" + self.body, encoding="utf-8")
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
            extra={
                key: value
                for key, value in header.items()
                if key not in _MODELLED_HEADER_KEYS
            },
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

    If several are open, which merging two branches can produce, the lowest
    id wins, so the older question is settled first.
    """
    openers = [d for d in list_decisions(forge_dir) if d.status.strip().lower() == STATUS_OPEN]
    return openers[0] if openers else None


def _sign_for(forge_dir: Path, decision: "Decision") -> dict[str, str]:
    """Fingerprint a record against the one before it (decisions 020, 021).

    Imported here rather than at module scope: the integrity module imports
    this one, so a top-level import would be circular.
    """
    import forge_integrity

    earlier = [d for d in list_decisions(forge_dir) if d.id < decision.id]
    return forge_integrity.sign(decision, earlier[-1] if earlier else None)


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
    decision.write(forge_dir, signature=_sign_for(forge_dir, decision))
    return decision


def answer(forge_dir: Path, decision_id: int, body: str, decided_by: str = "user") -> Decision:
    """Flip an open question to decided, in the same file it was asked in.

    Decision 018 accepts that two branches can both take the same id, so an id
    is not a unique handle. Answering the first match meant the wrong record
    could be filled in, and then the second one could never be answered at
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
                f"Decision {decision_id:03d} is not open, it is {decision.status!r}.",
                forge_dir / DECISIONS / decision.filename(),
                repair="answer the open question instead",
            )
        decision.status = STATUS_DECIDED
        decision.decided_by = decided_by
        decision.date = date.today().isoformat()
        decision.body = body
        # Re-signed: the content changed, so the old fingerprint no longer holds.
        decision.write(forge_dir, signature=_sign_for(forge_dir, decision))
        return decision

    raise StateError(
        f"No decision {decision_id:03d} to answer.",
        forge_dir / DECISIONS,
        repair="check .claude/forge/decisions/ for the right id",
    )


def writes_allowed(forge_dir: Path) -> tuple[bool, str]:
    """The governor's rule, in one place. Returns (allowed, reason_if_not).

    **Unreadable state blocks.** This used to swallow the error and carry on,
    so a damaged or missing progress file with no decision open came out as
    "writes allowed", Forge could not tell whether a question was open and
    said yes anyway. Decision 004 is explicit that the safety path fails
    closed, and this is the safety path.
    """
    # Switched off in this project, so every write is somebody else's business.
    # Checked before the state is even read: a paused project must not be able
    # to lock its owner out because a note file is malformed, and asking Forge
    # to stop should stop it completely rather than mostly.
    if paused(forge_dir):
        return True, ""

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

    # Every reason this function returns is a complete sentence, because the
    # governor prints it as one. It used to return a bare question and let the
    # governor prefix "No decision recorded yet for:" — which read correctly
    # for a question and absurdly for anything else: "No decision recorded yet
    # for: Forge cannot read its own notes."
    if pending is not None:
        return False, f"No decision recorded yet for: {pending.question}"

    # An unanswered foundation blocks too, and this is the hole that made the
    # product not work.
    #
    # The rule was only ever "is a question open" — the state between asking
    # and answering. On a brand-new project nothing has been asked, so nothing
    # was open, so writes were allowed and Forge would happily write a whole
    # file before a single decision existed. Which is exactly what it exists to
    # prevent, and it looked like it was working the entire time.
    #
    # Imported here rather than at the top: the foundation module reads the
    # state layer, so a module-level import would be a cycle.
    import forge_foundation as ff

    unanswered = ff.next_question(forge_dir)
    if unanswered is not None:
        return False, f"No decision recorded yet for: {unanswered.question}"

    # And the current build step blocks, which is the hole that made the
    # product stop working after the sixth question.
    #
    # Both rules above are true exactly once, at the start. After the last
    # foundation answer this function returned True and never returned anything
    # else — so Forge asked six questions, compiled the phases, and then wrote a
    # whole application in one turn without asking again. The interactive loop
    # existed only in the planner's instructions, which makes it advice.
    #
    # A phase is not buildable. Its steps are, one at a time, each after its own
    # decision. Imported here for the same reason as the foundation module: the
    # step layer reads this one.
    import forge_steps as st

    gap = st.next_gap(forge_dir)
    if gap is not None:
        return False, gap.reason

    return True, ""


# --------------------------------------------------------------------------
# locating and creating the project's notes
# --------------------------------------------------------------------------


def find_forge_dir(start: Path) -> Path | None:
    """Find this project's `.claude/forge/`, so Forge works from any subdirectory.

    The walk upward is **bounded**, and that bound is the point. An unbounded
    search finds a stray notes folder in a home directory and silently activates
    Forge in every project on the machine, the opposite of decision 014,
    which says Forge acts only where it was invited.

    The boundary is the repository root, because decision 016 puts `.claude/forge/`
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


def is_ignored_by_git(path: Path) -> bool:
    """Would git refuse to track this path?

    Asked of git itself rather than by reading `.gitignore`, because the rules
    compose across files, the global config and the exclude file, and a
    reimplementation would be wrong in exactly the cases that matter.

    This exists because `.claude/` is commonly ignored, it usually holds
    machine-local settings, so excluding the whole folder is an ordinary thing
    for a project to do. Harmless until Forge's memory is inside it.
    """
    import subprocess

    # Asked from the nearest directory that exists. The path being checked is
    # usually the folder about to be created, and neither it nor its parent is
    # there yet — running from a directory that does not exist made git answer
    # about whatever the process happened to be sitting in, which was a
    # different repository entirely and always said "not ignored".
    anchor = path
    while not anchor.exists() and anchor != anchor.parent:
        anchor = anchor.parent
    if not anchor.is_dir():
        anchor = anchor.parent

    try:
        done = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=str(anchor),
            capture_output=True,
            timeout=15,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False  # cannot ask, so do not accuse

    # 0 = ignored, 1 = not ignored, 128 = not a repository.
    return done.returncode == 0


def refuse_if_ignored(forge: Path) -> None:
    """Stop before writing notes that would never be committed.

    Refusing is the right call rather than warning and carrying on. Forge's
    whole promise is that the repository is the memory (decision 011); notes it
    knows git will discard are not memory, and the user would not find out
    until they switched machine and found an empty project.

    Forge cannot fix this from inside its own folder either, git will not
    re-include a file whose parent directory is excluded, so the only thing it
    can usefully do is say which line to change.
    """
    if not is_ignored_by_git(forge):
        return
    raise StateError(
        f"git is ignoring {FORGE_DIR}, so Forge's notes would never be committed.\n"
        "  Your decisions are meant to travel with the code, without that, a new\n"
        "  machine or account opens an empty project.",
        forge,
        repair=(
            f"remove the line that ignores `.claude/` (or add `!{FORGE_DIR}/` "
            "after it) in .gitignore, then run /forge:start again"
        ),
    )


def init(project_root: Path, total_questions: int = 0) -> Path:
    """Create the notes for a new project. Refuses to overwrite existing ones."""
    forge = project_root / FORGE_DIR
    refuse_if_ignored(forge)
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
            "it breaks, the labelled section at the top is what the tool relies on.\n"
        ),
    ).write(forge)
    return forge
