"""Forge Mentor — the loop itself.

Phases 3 to 7 built the parts: state, the governor, the engine, the skills and
the subagents. This is what puts them in order, and it is the product.

**Two loops.** The foundation loop runs once at the start — interrogate the
blast-radius decisions, then challenge the resulting plan with a premortem and
a redteam, then compile the phases. The build loop then runs per step, over and
over: teach, decide, write, gate, explain back.

**Where a stage comes from.** Never from a model deciding what feels next. The
stage is a function of what is on disk — is a question open, has the plan been
challenged, did the tests pass — so two sessions reading the same `.claude/forge/`
reach the same answer, and a session that resumes on another machine lands
exactly where the last one stopped (decision 011).

**The three modes** (decision 030) change one thing: how much Forge decides on
its own. Auto answers furniture-level questions itself and records them like
any other decision. It never answers a blast-radius one, and the governor rule
holds in all three — a mode that turned that off would not be a faster Forge,
it would be plain Claude Code with a banner.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import forge_foundation as ff
import forge_skills as sk
import forge_state as fs
import forge_steps as st


class Mode(str, Enum):
    """How much Forge decides without asking (decision 030)."""

    PIPELINE = "pipeline"  # asks every load-bearing decision, confirms each write
    ACCEPT_EDITS = "accept-edits"  # asks the same, stops confirming each write
    AUTO = "auto"  # decides the furniture itself, asks only blast-radius

    @property
    def explains(self) -> str:
        return {
            Mode.PIPELINE: "asks about every decision that matters, and confirms each file",
            Mode.ACCEPT_EDITS: "asks about every decision that matters, and writes without confirming",
            Mode.AUTO: "decides small things itself and records them; still asks about the big ones",
        }[self]


class Stage(str, Enum):
    """Where the work is. Ordered, and derived from disk rather than declared."""

    INTERROGATION = "interrogation"
    CHALLENGE = "challenge"
    PLANNING = "planning"
    # The step's own question, asked inside a phase. Separate from
    # INTERROGATION because the foundation runs once and this runs before every
    # step — reporting both as "interrogation" made a live build look like it
    # had gone back to the beginning.
    STEP_DECISION = "step-decision"
    BUILDING = "building"
    REVIEW_FIX = "review-fix"
    TEACH_BACK = "teach-back"
    STRUCTURING = "structuring"


# The foundation loop, in order. Runs once, before any code exists.
FOUNDATION = (Stage.INTERROGATION, Stage.CHALLENGE, Stage.PLANNING)

# The build loop, in order. Runs per step, repeatedly — and it opens with a
# question, which is the whole point of it. A loop starting at BUILDING is a
# loop that writes code nobody was asked about.
BUILD = (Stage.STEP_DECISION, Stage.BUILDING, Stage.REVIEW_FIX, Stage.TEACH_BACK)

DEFAULT_MODE = Mode.PIPELINE


class PipelineError(Exception):
    """The pipeline could not work out what to do next."""


# --------------------------------------------------------------------------
# blast radius — the only thing Auto is allowed to decide for you
# --------------------------------------------------------------------------

# A decision other work gets built on top of. Auto never answers one of these:
# getting it wrong is not a thing you fix later, it is a thing you rewrite
# around. The list is deliberately about *consequence*, not about topic.
# Each ends in \w* so a plural or a participle still matches. Written the long
# way after "payments", "secrets" and "log in" all slipped through a first
# draft that assumed the singular and one word — the failure mode being that
# Auto silently answers a question about payments, which is precisely the class
# this list exists to protect.
LOAD_BEARING = (
    r"\b(stack|framework|language|runtime)\w*",
    r"\b(database|schema|migration|storage|persistence|persist)\w*",
    r"\b(log[\s-]?in|logging[\s-]?in|sign[\s-]?in|signing[\s-]?in|sign[\s-]?up"
    r"|oauth|openid|saml|sso|auth|authentication|authoris|authoriz"
    r"|password|session|token|credential|permission|access control)\w*",
    r"\b(api|endpoint|contract|protocol|interface)\w*",
    r"\b(deploy|hosting|infrastructure|environment)\w*",
    r"\b(secret|encrypt|privacy|personal data|gdpr)\w*",
    r"\b(test\w*\s+strateg|error handling|logging strateg)\w*",
    r"\b(payment|billing|money|charge|invoice|subscription|pricing)\w*",
    r"\b(architecture|module boundar|data model|state management)\w*",
)

_LOAD_BEARING = tuple(re.compile(p, re.IGNORECASE) for p in LOAD_BEARING)


def is_load_bearing(question: str) -> bool:
    """Would other work be built on top of this answer?

    Auto stops for these and answers the rest. The test is intentionally
    generous: a furniture question wrongly treated as load-bearing costs one
    unnecessary question, while a load-bearing question wrongly treated as
    furniture costs a decision the user never made and cannot defend. Those two
    errors are not the same size, so this leans towards asking.
    """
    return any(pattern.search(question or "") for pattern in _LOAD_BEARING)


def should_ask(question: str, mode: Mode) -> bool:
    """Does this question go to the user, or does Forge answer it?

    A blank question always goes to the user. There is nothing in it to
    classify, and "I cannot tell" must never resolve to "Forge decides" — that
    is the one direction where being wrong costs a decision the user never
    made. The first version returned False, and the test asserting it was
    named for the safe behaviour while asserting the unsafe one.
    """
    if mode is Mode.AUTO:
        return not question.strip() or is_load_bearing(question)
    return True  # pipeline and accept-edits ask about everything that is asked


# --------------------------------------------------------------------------
# the mode, kept where it survives a restart
# --------------------------------------------------------------------------


def mode(forge_dir: Path) -> Mode:
    """The mode this project is in. Pipeline unless told otherwise.

    Read from disk every time rather than cached, for the same reason the
    governor re-reads state every time (decision 019): a value held in memory
    is a value that disagrees with the file after an account switch.
    """
    path = forge_dir / fs.SETTINGS
    if not path.is_file():
        return DEFAULT_MODE
    try:
        header, _ = fs.parse_header(path.read_text(encoding="utf-8"), path)
    except (fs.StateError, OSError):
        return DEFAULT_MODE
    try:
        return Mode(str(header.get("mode", "")).strip().lower())
    except ValueError:
        return DEFAULT_MODE  # an unreadable mode is the safest mode


def set_mode(forge_dir: Path, wanted: str | Mode) -> Mode:
    """Change the mode, and say so on disk."""
    try:
        chosen = Mode(str(wanted).strip().lower())
    except ValueError:
        raise PipelineError(
            f"Unknown mode {wanted!r}. Use: {', '.join(m.value for m in Mode)}."
        ) from None

    path = forge_dir / fs.SETTINGS
    header: dict[str, str] = {}
    body = ""
    if path.is_file():
        try:
            header, body = fs.parse_header(path.read_text(encoding="utf-8"), path)
        except (fs.StateError, OSError) as exc:
            # Report the damage; never write over it. Discarding a header that
            # failed to parse and rewriting the same file would destroy every
            # unrelated setting in it just to record a mode change.
            raise PipelineError(
                "The settings file could not be read, so Forge will not "
                f"overwrite it: {exc}"
            ) from None

    header["type"] = "settings"
    header["mode"] = chosen.value
    if not body.strip():
        body = (
            "# Settings\n\n"
            "`mode` decides how much Forge settles on its own (decision 030). The rule that "
            "code cannot move past an undecided question holds in every mode.\n"
        )

    forge_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(fs.render_header(header) + body, encoding="utf-8")
    return chosen


# --------------------------------------------------------------------------
# what happens next — read from disk, never decided by a model
# --------------------------------------------------------------------------


@dataclass
class Step:
    """The next thing to do, and everything needed to do it."""

    stage: Stage
    agent: str
    model: str
    skills: tuple[str, ...]
    why: str
    asks_user: bool
    blocked: bool = False
    question: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage.value,
            "agent": self.agent,
            "model": self.model,
            "skills": list(self.skills),
            "why": self.why,
            "asks_user": self.asks_user,
            "writes_blocked": self.blocked,
            "question": self.question,
        }


CHALLENGED_MARKER = "challenge-001.md"


def challenge_done(forge_dir: Path) -> bool:
    """Has the plan been through the premortem and the redteam?

    A file on disk, not a flag in the progress header. The challenge produces a
    document; if the document is not there the challenge did not happen,
    whatever a header claims.
    """
    return (forge_dir / CHALLENGED_MARKER).is_file()


def planned(forge_dir: Path) -> bool:
    """Have the phases been compiled?"""
    folder = forge_dir / "phases"
    return folder.is_dir() and any(folder.glob("*.md"))


def next_step(forge_dir: Path) -> Step:
    """What happens next, worked out from what is on disk.

    The order is fixed and the inputs are files, so this is the same answer in
    any session on any machine — which is what makes resuming work at all.
    """
    current = mode(forge_dir)

    pending = fs.open_question(forge_dir)
    if pending is not None:
        # A question is open, so nothing else can happen. This is the governor
        # rule expressed as a plan rather than as a refusal.
        asks = should_ask(pending.question, current)
        return _step(
            Stage.INTERROGATION if not planned(forge_dir) else Stage.BUILDING,
            skills_stage=Stage.INTERROGATION,
            why=(
                f"{pending.question} — waiting for your answer"
                if asks
                else f"{pending.question} — small enough for Forge to settle and record"
            ),
            asks_user=asks,
            blocked=True,
            question=pending.question,
        )

    # A project with no decisions at all has not started, so the first step is
    # to ask — not to challenge a plan that does not exist yet. The first
    # version fell straight to CHALLENGE on a fresh directory and INTERROGATION
    # was only ever reached once a question was already open, which meant the
    # stage that opens the first question could never be the one suggested.
    pending_foundation = ff.next_question(forge_dir)
    if pending_foundation is not None:
        done, total = ff.position(forge_dir)
        return _step(
            Stage.INTERROGATION,
            why=f"{pending_foundation.question} — {done + 1} of {total}",
            asks_user=True,
            question=pending_foundation.question,
        )

    if not challenge_done(forge_dir):
        return _step(
            Stage.CHALLENGE,
            why="the plan has not been challenged yet — premortem and redteam before any code",
            asks_user=False,
        )

    if not planned(forge_dir):
        return _step(
            Stage.PLANNING,
            why="decisions are made and challenged; compile them into phases",
            asks_user=False,
        )

    try:
        progress = fs.Progress.read(forge_dir)
    except fs.StateError as exc:
        raise PipelineError(f"The notes need repair before work can continue: {exc}") from None

    if progress.gate_attempts:
        return _step(
            Stage.REVIEW_FIX,
            why=f"the gate has failed {progress.gate_attempts} time(s) — fix before building on",
            asks_user=False,
        )

    # A step whose code is written and whose gate has passed is not finished:
    # decision 009 needs the user to say it back. Without this the loop
    # returned to BUILDING and the teaching gate — the product's whole claim —
    # was never reached by the state machine at all.
    if progress.current_step and not progress.next_action:
        return _step(
            Stage.TEACH_BACK,
            why=f"{progress.current_step} is built and green — say it back before it closes",
            asks_user=True,
        )

    # The phase in front of the user, one step at a time. This is where the
    # loop was missing entirely: it fell straight to BUILDING and stayed there,
    # so the whole of a phase came out in a single turn with nothing asked.
    gap = st.next_gap(forge_dir)

    if gap is not None and gap.kind == "unplanned":
        return _step(
            Stage.PLANNING,
            why=gap.reason,
            asks_user=False,
            blocked=True,
        )

    # The plan is shown whole before any of it is built. Separate from
    # PLANNING because the phases already exist here — what is missing is the
    # user having seen them, which is a question rather than a compile.
    if gap is not None and gap.kind == "unapproved":
        return _step(
            Stage.PLANNING,
            why=gap.reason,
            asks_user=True,
            blocked=True,
            question=gap.reason,
        )

    if gap is not None:
        asks = should_ask(gap.reason, current)
        return _step(
            Stage.STEP_DECISION,
            why=(
                f"{gap.reason} — waiting for your answer"
                if asks
                else f"{gap.reason} — small enough for Forge to settle and record"
            ),
            asks_user=asks,
            blocked=True,
            question=gap.reason,
        )

    step = st.current(forge_dir)
    if step is None:
        return _step(
            Stage.BUILDING,
            why="every phase is finished — nothing is left to build",
            asks_user=False,
        )

    return _step(
        Stage.BUILDING,
        why=(
            f"step {step.number} of phase {step.phase} is decided — build that, and "
            "only that"
        ),
        asks_user=False,
        question=step.question,
    )


def _step(
    stage: Stage,
    *,
    why: str,
    asks_user: bool,
    skills_stage: Stage | None = None,
    blocked: bool = False,
    question: str = "",
) -> Step:
    agent = sk.agent_for((skills_stage or stage).value)
    return Step(
        stage=stage,
        agent=agent.name,
        model=agent.model,
        skills=sk.skills_for((skills_stage or stage).value),
        why=why,
        asks_user=asks_user,
        blocked=blocked,
        question=question,
    )


def status(forge_dir: Path) -> dict[str, object]:
    """Everything a session needs to pick up where the last one stopped."""
    current = mode(forge_dir)
    try:
        step = next_step(forge_dir)
    except PipelineError as exc:
        return {"error": str(exc), "needs_repair": True}

    allowed, reason = fs.writes_allowed(forge_dir)
    built, total = st.position(forge_dir)
    here = st.current(forge_dir)

    out = step.as_dict()
    out.update(
        {
            "mode": current.value,
            "mode_means": current.explains,
            "challenged": challenge_done(forge_dir),
            "planned": planned(forge_dir),
            "writes_allowed": allowed,
            "writes_reason": reason,
            # Where the loop actually is. Without this a session could see
            # "stage: building" and no indication of which step that meant, so
            # the only sane thing left to do was build the phase.
            "step": (
                {
                    "phase": here.phase,
                    "number": here.number,
                    "text": here.text,
                    "marker": here.marker,
                }
                if here
                else None
            ),
            "steps_built": built,
            "steps_total": total,
        }
    )
    return out
