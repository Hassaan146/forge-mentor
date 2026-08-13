"""Forge Mentor, the build loop's unit of work.

**The hole this closes.** The governor's rule was "is a question open", and
decision 034 added "is the foundation answered". Both are true exactly once, at
the start. After the sixth foundation answer, `writes_allowed` returned True
and stayed True, so Forge asked six questions, compiled the phases, and then
wrote an entire application without asking anything again. On a real run it
produced `app.js`, `db.js`, `index.html` and `style.css` in one turn. Every
line of it was allowed, and the product looked like it was working.

The interactive loop was never enforced. It was described in the planner's
instructions, which makes it a suggestion.

**A phase is not something you build.** It is something you break into steps,
and each step is a question before it is code. That is the difference between
this and plain Claude Code with a banner, and it has to be a fact about the
files rather than a paragraph in a prompt.

So: a phase file carries its own step list, a step is decided when a decision
record names it, and the write gate reads both. Nothing here trusts a model to
remember the rule.

**What this cannot do.** The governor sees a file path, not an intention. Once
the current step is decided, writes are allowed until it is ticked off, so a
builder that ignores its brief can still write more than the step asked for.
What it cannot do is build a phase nobody has been asked about, which is the
failure that actually happened.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import forge_state as fs

PHASES = "phases"
STEPS_HEADING = "## Steps"

# `1. text`, `- text`, `- [ ] text`, `- [x] text`, a step list written by a
# planner, a user, or by hand, and all four shapes read the same. The tick box
# is what "built" means; a list without one is a list of steps nobody has
# started.
_STEP_LINE = re.compile(
    r"^\s*(?:[-*]|\d+[.)])\s*(?:\[(?P<tick>[ xX])\]\s*)?(?P<text>\S.*?)\s*$"
)

_DONE_STATUS = {"complete", "done", "shipped", "merged"}


@dataclass(frozen=True)
class Step:
    """One step of one phase: a question first, then the code that answers it."""

    phase: int
    number: int
    text: str
    built: bool = False

    @property
    def marker(self) -> str:
        """What a decision record writes in `affects` to claim this step.

        A marker rather than a decision id, because ids are shared across
        branches (decision 018) and a step has to stay identifiable when two
        branches both wrote a decision 014.
        """
        return f"phase-{self.phase}.step-{self.number}"

    @property
    def question(self) -> str:
        return f"Phase {self.phase}, step {self.number}: {self.text}"


@dataclass(frozen=True)
class Phase:
    """One phase of the plan, as the user will see it on the roadmap."""

    number: int
    title: str
    delivers: str
    status: str
    steps: tuple[Step, ...] = ()

    @property
    def done(self) -> bool:
        return self.status.strip().lower() in _DONE_STATUS

    @property
    def built(self) -> int:
        return len([s for s in self.steps if s.built])

    @property
    def started(self) -> bool:
        return self.done or self.built > 0

    def state(self) -> str:
        """`done`, `now`, or `later`, the word that carries it without colour."""
        if self.done:
            return "done"
        if self.built or self.steps:
            return "now"
        return "later"


@dataclass(frozen=True)
class Gap:
    """Why code cannot be written yet, and what would close it."""

    # "unplanned":     no phases at all, or this phase has no step list
    # "unapproved":    the plan exists but the user has not seen it whole
    # "unasked":       this step touches a subject whose questions are unanswered
    # "unchallenged":  nobody has asked whether this step should be built at all
    # "undecided":     this step has no recorded decision
    kind: str
    phase: int
    reason: str
    step: Step | None = None
    # Set on "unasked": the key of the question that is owed, so a caller can
    # fetch and draw it rather than inventing one from the reason text.
    question: str = ""


# What a decision writes in `affects` to say the user has seen the whole plan.
# A marker rather than a phase number, because it is a decision about all of
# them at once, and the point of it is that no phase is built before the user
# knows what the other four are.
PLAN_MARKER = "plan-accepted"


# --------------------------------------------------------------------------
# reading the phases
# --------------------------------------------------------------------------


def phase_files(forge_dir: Path) -> list[tuple[int, Path, dict[str, str]]]:
    """Every phase file, in phase order, with its header.

    Sorted by the `phase:` number rather than by filename, because `10-` sorts
    before `2-` as text and a build loop that runs phase 10 second is not a
    build loop.
    """
    folder = forge_dir / PHASES
    if not folder.is_dir():
        return []

    out: list[tuple[int, Path, dict[str, str]]] = []
    for path in sorted(folder.glob("*.md")):
        try:
            header, _ = fs.parse_header(path.read_text(encoding="utf-8"), path)
        except (fs.StateError, OSError):
            # A phase file Forge cannot read is not a phase it can silently
            # skip: skipping it would build the next phase in its place. It is
            # surfaced by `next_gap` instead, where it stops the loop.
            header = {"unreadable": "yes"}
        try:
            number = int(str(header.get("phase", "")).strip())
        except ValueError:
            number = 0
        out.append((number, path, header))

    return sorted(out, key=lambda row: (row[0] or 10**6, row[1].name))


def read_steps(path: Path, phase: int) -> list[Step]:
    """The step list from one phase file, in the order it is written.

    Only the lines under `## Steps` count. A phase file has other lists in it —
    deliverables, done-when, and treating those as steps would ask the user to
    decide a heading.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []

    steps: list[Step] = []
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(STEPS_HEADING.lower()):
            inside = True
            continue
        if inside and stripped.startswith("#"):
            break  # the next heading ends the list
        if not inside or not stripped:
            continue

        match = _STEP_LINE.match(line)
        if match is None:
            continue
        steps.append(
            Step(
                phase=phase,
                number=len(steps) + 1,
                text=match.group("text"),
                built=(match.group("tick") or "").lower() == "x",
            )
        )
    return steps


def decided_markers(forge_dir: Path) -> set[str]:
    """Every step marker that already has a decided record against it.

    Read from `affects`, which is part of the record's fingerprint, so a step
    cannot be marked decided by editing a file the chain would then reject.
    """
    found: set[str] = set()
    for decision in fs.list_decisions(forge_dir):
        if decision.status.strip().lower() != fs.STATUS_DECIDED:
            continue
        # A note the builder wrote about its own work is not permission to do
        # that work. Both are decided records against the same step, and
        # without this line the builder could open its own gate by writing down
        # what it had decided to do, which is the governor rule inverted.
        if decision.extra.get("kind", "").strip().lower() == fs.BUILD_NOTE:
            continue

        # Nor is deciding that a step is worth building a decision about how it
        # works. The lean marker *contains* the step marker (`lean:phase-1.step-1`)
        # so the pattern below matched it and the pass opened the gate it was
        # written to come before. Same shape as the line above, found the same
        # way: by a test that expected the next question and got permission.
        import forge_lean as ln

        if (decision.affects or "").strip().startswith(f"{ln.PREFIX}:"):
            continue
        for token in re.findall(r"phase-\d+\.step-\d+", decision.affects or ""):
            found.add(token)
    return found


def plan_accepted(forge_dir: Path) -> bool:
    """Has the user seen the whole plan and said yes to it?

    Not "do phase files exist". Files can be written without anybody reading
    them, and that is what happened: five phases were compiled into a progress
    file as prose, and the first one was built before the user knew there were
    five. A plan revealed one phase at a time is not a plan, it is a surprise
    delivered in instalments.
    """
    for decision in fs.list_decisions(forge_dir):
        if decision.status.strip().lower() != fs.STATUS_DECIDED:
            continue
        if PLAN_MARKER in (decision.affects or ""):
            return True
    return False


def roadmap(forge_dir: Path) -> list[Phase]:
    """The whole plan, in order, every phase, not just the current one."""
    out: list[Phase] = []
    for number, path, header in phase_files(forge_dir):
        if header.get("unreadable"):
            out.append(
                Phase(
                    number=number,
                    title=f"{path.name}, unreadable",
                    delivers="",
                    status="broken",
                )
            )
            continue
        out.append(
            Phase(
                number=number,
                title=str(header.get("title", "")).strip() or f"Phase {number}",
                delivers=str(header.get("delivers", "")).strip(),
                status=str(header.get("status", "")).strip() or "planned",
                steps=tuple(read_steps(path, number)),
            )
        )
    return out


# --------------------------------------------------------------------------
# where the loop is
# --------------------------------------------------------------------------


def _is_done(header: dict[str, str]) -> bool:
    return str(header.get("status", "")).strip().lower() in _DONE_STATUS


def current(forge_dir: Path) -> Step | None:
    """The step being worked on: the first unbuilt step of the first open phase.

    None means every phase is either finished or has nothing left in it, which
    is the only state where there is no next step to ask about.
    """
    for number, path, header in phase_files(forge_dir):
        if _is_done(header) or header.get("unreadable"):
            continue
        for step in read_steps(path, number):
            if not step.built:
                return step
    return None


def next_gap(forge_dir: Path) -> Gap | None:
    """What is standing between this project and its next line of code.

    Returns None only when the current step has been decided, which is the
    single condition under which the builder is allowed to run.
    """
    files = phase_files(forge_dir)
    if not files:
        # No phases at all, which is the state the real failure ran in: the
        # project that wrote a whole application unasked had six decisions, a
        # progress file describing five phases in prose, and no `phases/`
        # directory. `planned()` was False and the pipeline said so, but the
        # write gate never asked, so the builder ran anyway.
        return Gap(
            kind="unplanned",
            phase=0,
            reason=(
                "The phases have not been compiled yet. There is nothing to build "
                "until the decisions become an ordered list of phases, and each "
                "phase a list of steps."
            ),
        )

    # A phase file that cannot be read comes first, ahead of everything below.
    # There is no showing the user a plan Forge cannot read, and no skipping
    # the broken one, skipping it would silently build the phase after it in
    # its place.
    for number, path, header in files:
        if header.get("unreadable"):
            return Gap(
                kind="unplanned",
                phase=number,
                reason=(
                    f"Forge cannot read the phase file {path.name}, so it cannot tell "
                    "which step comes next."
                ),
            )

    # The whole plan is shown before any of it is built. This gate is here
    # rather than in the planner's brief for the same reason as every other
    # one: a run compiled five phases, built the first, and asked the user
    # about the second only once the first was finished, so the shape of the
    # project arrived in instalments, and the decision that set it was made
    # before the user could see what it committed them to.
    if not plan_accepted(forge_dir):
        count = len(files)
        return Gap(
            kind="unapproved",
            phase=0,
            reason=(
                f"You have not seen the whole plan yet. There "
                f"{'is' if count == 1 else 'are'} {count} "
                f"phase{'' if count == 1 else 's'}; Forge shows all of them, and you "
                "accept or change the shape, before any one of them is built."
            ),
        )

    for number, path, header in files:
        if _is_done(header):
            continue

        steps = read_steps(path, number)
        if not steps:
            title = str(header.get("title", "")).strip() or f"phase {number}"
            return Gap(
                kind="unplanned",
                phase=number,
                reason=(
                    f"{title} has not been broken into steps yet. A phase is not "
                    "something to build in one go, it is a list of steps, and each "
                    "one is a decision before it is code."
                ),
            )

        decided = decided_markers(forge_dir)
        title = str(header.get("title", "")).strip()
        for step in steps:
            if step.built:
                continue

            # What the subject owes, before what the step owes. A step that
            # stores something is asked which database, where it runs and how
            # its shape changes, once per project, and those are answered before
            # the step's own question is worth asking: the step decision is made
            # inside them. Without this the whole interrogation after the
            # foundation was whatever the planner thought of in the moment,
            # which for a database step was usually nothing.
            import forge_topics as tp

            owed = tp.next_owed(forge_dir, f"{title} {step.text}")
            if owed is not None:
                return Gap(
                    kind="unasked",
                    phase=number,
                    reason=(
                        f"This step touches something that has not been decided "
                        f"yet: {owed.question}"
                    ),
                    step=step,
                    question=owed.key,
                )

            # Whether it should be built at all, before what it should look
            # like. Asked in this order deliberately: put the size question
            # after the design question and the design has already settled the
            # size, which is how a step that needed twenty lines arrives as
            # four files that everybody has already agreed to.
            import forge_lean as ln

            if not ln.passed(forge_dir, step.marker):
                return Gap(
                    kind="unchallenged",
                    phase=number,
                    reason=(
                        "This step has not been through the lean pass yet: "
                        f"nobody has asked whether {step.text!r} needs building, "
                        "or how small it could be."
                    ),
                    step=step,
                )

            if step.marker in decided:
                return None  # the current step is decided; the builder may run
            return Gap(
                kind="undecided",
                phase=number,
                reason=f"No decision recorded yet for: {step.question}",
                step=step,
            )

    return None


def position(forge_dir: Path) -> tuple[int, int]:
    """Steps built against steps known, for the progress line.

    Counted across open phases only. A finished phase's steps are history, and
    a progress bar that includes them never appears to move.
    """
    built = total = 0
    for number, path, header in phase_files(forge_dir):
        if _is_done(header) or header.get("unreadable"):
            continue
        for step in read_steps(path, number):
            total += 1
            built += 1 if step.built else 0
    return built, total


# --------------------------------------------------------------------------
# writing the phases
# --------------------------------------------------------------------------


class StepError(Exception):
    """The step list could not be read or written."""


def _phase_path(forge_dir: Path, phase: int) -> tuple[Path, dict[str, str]]:
    for number, path, header in phase_files(forge_dir):
        if number == phase:
            return path, header
    raise StepError(
        f"There is no phase {phase} in {forge_dir / PHASES}. "
        "Compile the phases before breaking one into steps."
    )


def compile_phases(forge_dir: Path, phases: list[tuple[str, str]]) -> list[Phase]:
    """Write the whole plan at once: every phase, before any of them is built.

    **All of them, deliberately.** Compiling one phase at a time is how a plan
    becomes a surprise delivered in instalments, the user answers a question
    about testing in phase two having never been told there was a phase four,
    and the answer to the first question quietly set the shape of all of them.

    Refuses to rewrite a plan whose phases have started, for the same reason
    `write_steps` does: the decisions are recorded against phase numbers, and
    renumbering leaves signed records pointing at work that no longer exists.
    """
    kept = [(t.strip(), d.strip()) for t, d in phases if t and t.strip()]
    if not kept:
        raise StepError("A plan needs at least one phase.")

    started = [p for p in roadmap(forge_dir) if p.started]
    if started:
        raise StepError(
            f"{len(started)} phase(s) are already under way. Rewriting the plan would "
            "renumber them, and their decisions are recorded against those numbers. "
            "Add a phase at the end, or edit the phase files by hand."
        )

    folder = forge_dir / PHASES
    folder.mkdir(parents=True, exist_ok=True)
    for existing in folder.glob("*.md"):
        existing.unlink()

    for number, (title, delivers) in enumerate(kept, start=1):
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50] or "phase"
        body = fs.render_header(
            {
                "phase": str(number),
                "title": title,
                "delivers": delivers,
                "status": "planned",
            }
        )
        body += f"\n# Phase {number}, {title}\n\n{delivers}\n"
        (folder / f"{number}-{slug}.md").write_text(body, encoding="utf-8")

    return roadmap(forge_dir)


def write_steps(forge_dir: Path, phase: int, texts: list[str]) -> list[Step]:
    """Give a phase its step list, or replace one that has not been started.

    **Refuses to overwrite work.** Once any step of a phase is built or decided,
    rewriting the list would silently detach those records from the steps they
    were recorded against, the decision would still exist and nothing would
    point at it. Add to the end instead, or edit the file by hand and repair
    the chain.
    """
    kept = [text.strip() for text in texts if text and text.strip()]
    if not kept:
        raise StepError("A phase needs at least one step.")

    path, _ = _phase_path(forge_dir, phase)
    existing = read_steps(path, phase)
    decided = decided_markers(forge_dir)
    started = [s for s in existing if s.built or s.marker in decided]
    if started:
        raise StepError(
            f"Phase {phase} already has {len(started)} step(s) under way, and their "
            "decisions are recorded against their numbers. Rewriting the list would "
            "leave those records pointing at nothing."
        )

    body = path.read_text(encoding="utf-8")
    block = "\n".join(f"{n}. [ ] {text}" for n, text in enumerate(kept, start=1))
    section = f"{STEPS_HEADING}\n\n{block}\n"

    if STEPS_HEADING.lower() in body.lower():
        body = _replace_section(body, section)
    else:
        body = body.rstrip("\n") + "\n\n" + section

    path.write_text(body, encoding="utf-8")
    return read_steps(path, phase)


def _replace_section(body: str, section: str) -> str:
    """Swap the `## Steps` block, leaving everything around it alone."""
    lines = body.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.strip().lower().startswith(STEPS_HEADING.lower())),
        None,
    )
    if start is None:
        return body.rstrip("\n") + "\n\n" + section

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].strip().startswith("#"):
            end = i
            break
    return "\n".join(lines[:start] + section.splitlines() + [""] + lines[end:]).rstrip("\n") + "\n"


def mark_built(forge_dir: Path, phase: int, number: int) -> Step:
    """Tick a step off, once its code is written and its gate has passed.

    This is what moves the loop on. Until it is called the current step stays
    the current step, so the next question is never asked, which is a stall,
    and a stall is the right failure here. The alternative is a loop that
    advances on nothing but a model's say-so, which is the behaviour this whole
    module exists to remove.
    """
    path, _ = _phase_path(forge_dir, phase)
    steps = read_steps(path, phase)
    if not 1 <= number <= len(steps):
        raise StepError(
            f"Phase {phase} has {len(steps)} step(s); there is no step {number}."
        )

    seen = 0
    out: list[str] = []
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(STEPS_HEADING.lower()):
            inside = True
            out.append(line)
            continue
        if inside and stripped.startswith("#"):
            inside = False
        if inside and stripped and _STEP_LINE.match(line):
            seen += 1
            if seen == number:
                match = _STEP_LINE.match(line)
                assert match is not None  # matched on the line above
                text = match.group("text")
                indent = line[: len(line) - len(line.lstrip())]
                out.append(f"{indent}{number}. [x] {text}")
                continue
        out.append(line)

    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return read_steps(path, phase)[number - 1]
