"""Forge Mentor: the pass that asks whether a thing should be built at all.

Forge's question has always been *which* decision. This is the one before it:
does this need writing, and if it does, how much of it. The two are different
questions and the second one was never asked, so a step that arrived on the
plan got built at whatever size the model first imagined it.

**What Forge can and cannot do here, stated plainly.** Nothing in this file can
judge whether code is minimal. That judgement is the model's, and it is better
at it with ponytail's ladder loaded (decisions 058 and 059). What Forge can do
is refuse to move until the question has been asked and the answer is on disk,
which is the same division of labour as everywhere else in this product: the
model reasons, the gate remembers.

**The two moments, and why there are two.**

*Before the user is asked* the proposal goes through the ladder: does the
project already do this, does the standard library do it, what is the smallest
version that is still worth having. The findings are shown to the user with the
question, so the user is choosing a size and not just approving a plan.

*After the approach is settled and before it is built* the same ladder is put
to the approach itself. If it comes back unchanged, one line says so and the
build proceeds. **If it comes back smaller, the smaller version goes to the user
as its own decision**, because a change to what is being built is a change the
user makes, not one the reviewer makes on their behalf.

The second moment is the one that is easy to skip and the one that pays: the
approach is where over-building actually happens, and by then everybody has
agreed on the goal and stopped looking.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import forge_state as fs

# The marker a lean record carries in `affects`. A marker rather than a decision
# id, for the reason decision 018 gives: ids are shared across branches, and a
# step has to stay identifiable when two branches both wrote a decision 014.
PREFIX = "lean"


def marker_for(step_marker: str) -> str:
    return f"{PREFIX}:{step_marker}"


# The rungs, in order, cheapest first. Written as questions because the point is
# that they are asked rather than assumed, and the order matters: "does this
# need to exist" has to be answered before "which library does it", or the
# library question quietly settles the first one.
LADDER: tuple[tuple[str, str], ...] = (
    ("needed", "Does this need to exist at all, or is it here because it was on a list?"),
    ("already", "Does something in this project already do it, or nearly do it?"),
    ("stdlib", "Does the standard library or the framework already do it?"),
    ("smallest", "What is the smallest version that is still worth having?"),
    ("cost", "What does the extra size cost: to read, to test, to change later?"),
)

LADDER_KEYS = tuple(key for key, _ in LADDER)


@dataclass(frozen=True)
class Finding:
    """What the ladder turned up, before the user is asked anything."""

    rung: str
    answer: str

    def line(self) -> str:
        return f"{self.rung}: {self.answer}"


def passed(forge_dir: Path, step_marker: str) -> bool:
    """Has this step been through the pass and had the answer recorded?"""
    wanted = marker_for(step_marker)
    for decision in fs.list_decisions(forge_dir):
        if decision.status.strip().lower() != fs.STATUS_DECIDED:
            continue
        if wanted in (decision.affects or ""):
            return True
    return False


def body(
    keep: str,
    findings: list[Finding],
    reasoning: str,
    their_reason: str = "",
    instead_of: str = "",
) -> str:
    """The record, written so the ladder is readable a year later.

    The findings are kept even when the answer is "build it as proposed". A pass
    that only leaves a trace when it changes something looks, in the history,
    exactly like a pass that never ran.
    """
    out = [f"# {keep}", ""]
    if instead_of.strip():
        out += [f"**Instead of:** {instead_of.strip()}", ""]
    if findings:
        out += ["**Before writing it, the ladder said**", ""]
        out += [f"- {finding.line()}" for finding in findings]
        out.append("")
    out += ["## Why", "", reasoning.strip(), ""]
    if their_reason.strip():
        out += ["## In their words", "", their_reason.strip(), ""]
    return "\n".join(out)


def missing_rungs(findings: list[Finding]) -> list[str]:
    """Which rungs were skipped. A ladder with a gap is a ladder nobody climbed.

    Checked because the failure mode here is not a wrong answer, it is three
    plausible sentences and two rungs quietly missing, which reads as a
    completed pass in every summary anybody will ever look at.
    """
    answered = {f.rung for f in findings if str(f.answer).strip()}
    return [key for key in LADDER_KEYS if key not in answered]
