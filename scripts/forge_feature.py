"""Forge Mentor: adding to something that already works.

**The gap.** Forge could take a project from nothing to ten phases and then had
nothing to say. Every gate reads the phase list, so once the last phase is
built, `next_gap` finds no unbuilt step and opens. A user coming back a month
later to add one feature got no questions at all, and the builder wrote whatever
it thought the sentence meant.

That is the worst moment to have no rules, because it is the moment with the
most to break. A new feature is written against a codebase full of decisions
nobody is re-reading, and the cheapest way to ruin a working project is to add
something that quietly contradicts one of them.

**Two things this file does, and they are the two things that were asked for.**

*Fewer tokens.* The foundation is not asked again. It is on disk, it is still
true, and re-asking it would be the product committing the failure it exists to
prevent. What comes back is a short list: the recorded decisions that bear on
this feature, and the questions the feature owes that are not already answered.
Ids and one-line choices, not bodies, because the model only needs to know what
it is building inside.

*Nothing disturbed.* A new feature that contradicts a recorded decision is not
quietly built. The clash is named, along with the decision that would have to be
reopened, and reopening one is a recorded supersede rather than an edit. Phases
are appended: nothing that exists is rewritten, so a feature added in September
cannot mark August's work unbuilt.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import forge_foundation as ff
import forge_options as fo
import forge_state as fs
import forge_steps as stp
import forge_topics as tp

# How many recorded decisions come back as context. A new feature lives inside
# a handful of them, and a list long enough to need scrolling is a list that
# gets skimmed. The ones that matter are the ones its own subjects settled.
MAX_CONSTRAINTS = 8


@dataclass(frozen=True)
class Constraint:
    """A decision already recorded that this feature has to live inside."""

    id: int
    question: str
    choice: str

    def line(self) -> str:
        return f"{self.id:03d}  {self.question}  ->  {self.choice}"


@dataclass(frozen=True)
class Clash:
    """Something the feature needs that a recorded decision has ruled out."""

    needs: str
    fact: str
    because: str
    decision: Constraint | None = None

    def line(self) -> str:
        where = f" (decision {self.decision.id:03d})" if self.decision else ""
        return f"This wants {self.needs}, and {self.because}{where}."


def _choice_of(decision: fs.Decision) -> str:
    """The one line at the top of a record: what was chosen."""
    return ff.chosen(decision)


def constraints(forge_dir: Path, description: str) -> list[Constraint]:
    """The recorded decisions this feature is being built inside.

    Not every decision. The ones its own subjects settled, plus the shape of the
    project, because those are what a new feature can contradict without
    anybody noticing. Returned as ids and one-line choices: the model needs to
    know what it is building inside, not to re-read the reasoning behind it.
    """
    wanted = {q.key for topic in tp.topics_in(description) for q in topic.questions}
    wanted |= {"stack", "data", "delivery", "people"}

    pool = ff.ALL_QUESTIONS + tp.ALL_QUESTIONS
    out: list[Constraint] = []
    for decision in fs.list_decisions(forge_dir):
        if decision.status.strip().lower() != fs.STATUS_DECIDED:
            continue
        question = ff.match_in(decision.question, pool)
        if question is None or question.key not in wanted:
            continue
        out.append(Constraint(decision.id, question.question, _choice_of(decision)))

    # Newest last, and the tail is what is kept: a decision that superseded an
    # earlier one is the one in force.
    return out[-MAX_CONSTRAINTS:]


def clashes(forge_dir: Path, description: str) -> list[Clash]:
    """What this feature wants that the project has already ruled out.

    Read the same way a menu is narrowed, and deliberately generous in the same
    direction: naming a clash that turns out to be fine costs one sentence,
    while missing one costs a feature built on top of a decision it broke.
    """
    known = ff.facts(forge_dir)
    if not known:
        return []

    found: list[Clash] = []
    for need in sorted(fo.needs_in(description)):
        for fact in sorted(known):
            if need not in fo.CONTRADICTS.get(fact, ()):
                continue
            # Named, not asserted. "A container is ruled out" is something the
            # user has to take on faith; "ruled out by decision 011, where you
            # said this runs only on your machine" is something they can argue
            # with, and being able to argue with it is the product.
            record = ff.source_of(forge_dir, fact)
            found.append(
                Clash(
                    needs=need,
                    fact=fact,
                    because=fo.WHY.get(fact, f"this project is {fact}"),
                    decision=(
                        Constraint(record.id, record.question, ff.chosen(record))
                        if record is not None
                        else None
                    ),
                )
            )
            break
    return found


def owed(forge_dir: Path, description: str) -> list[ff.Question]:
    """The subject questions this feature owes and the project has not answered."""
    return tp.owed(forge_dir, description)


def next_phase_number(forge_dir: Path) -> int:
    existing = [number for number, _path, _header in stp.phase_files(forge_dir)]
    return (max(existing) if existing else 0) + 1


def add_phase(forge_dir: Path, title: str, delivers: str) -> Path:
    """Append one phase. Never rewrite one.

    `compile_phases` writes the whole plan at once, which is right the first
    time and wrong every time after it: rewriting the file list to add a
    feature would put an August phase through a September pen, and the steps
    already marked built are the record of what happened.
    """
    if not title.strip():
        raise stp.StepError("A phase needs a title.")

    number = next_phase_number(forge_dir)
    folder = forge_dir / stp.PHASES
    folder.mkdir(parents=True, exist_ok=True)

    slug = "-".join(
        part for part in title.lower().replace("/", " ").split() if part.isalnum()
    )[:40]
    path = folder / f"{number}-{slug or 'feature'}.md"
    if path.exists():
        raise stp.StepError(f"{path.name} already exists, so this would overwrite it.")

    path.write_text(
        f"---\nphase: {number}\ntitle: {title.strip()}\nadded: later\n---\n\n"
        f"{delivers.strip()}\n\n## Steps\n\n_Not broken into steps yet._\n",
        encoding="utf-8",
    )
    return path
