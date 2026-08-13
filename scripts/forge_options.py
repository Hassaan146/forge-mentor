"""Forge Mentor — what a set of options has to be before a user sees it.

**Why this module exists.** Nothing generated options. One question in the
foundation carried them (the stack, four of them), every other question carried
none, and every per-step question in the build loop carried none either. So the
options a user saw were improvised in the moment against no rule at all: no
floor on how many, no requirement that each carry its cost, and nothing
whatsoever tying them to what the project had already decided.

That is not a small gap. A real run offered a project "Docker, or run it
locally", which is two options where there are six, and one of them had already
been ruled out three questions earlier when the user said the thing only ever
runs on their own laptop. The model was not being careless. It was being asked
to invent a menu with no constraints, and a menu invented under no constraints
comes out as the two most familiar words on the subject.

Two rules, then, and both are checked in code rather than asked for in a brief:

**A menu is at least three real options.** Two is a false binary, and a false
binary is how a decision gets made by whoever wrote the pair. Every option
carries what it costs, because an option list without consequences is a list of
words.

**An option that contradicts a recorded decision is not offered.** It is shown
struck out, naming the decision that removed it, because a user who never sees
Docker mentioned learns less than one who sees it ruled out and why. The
teaching is in the exclusion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Three, not two. The floor is the whole point of the module: a question that
# arrives with two options has usually had its answer chosen already by whoever
# picked the pair, and the user is left ratifying it.
MIN_OPTIONS = 3

# Six, because a list nobody finishes reading is a list nobody chooses from.
# Above this the extra options are not width, they are noise.
MAX_OPTIONS = 6

LETTERS = "ABCDEFGH"


@dataclass(frozen=True)
class Option:
    """One thing the user could pick, and what picking it would mean.

    `needs` is what this option requires of the project: a server, a machine
    that stays up, more than one person. `gives` is what choosing it settles,
    so later questions can narrow themselves against it. Both are plain tags
    rather than prose, because a rule that reads prose is a rule that guesses.
    """

    label: str
    note: str
    needs: tuple[str, ...] = ()
    gives: tuple[str, ...] = ()

    def as_row(self, letter: str) -> list[str]:
        """The `[letter, label, note]` shape the renderers expect."""
        return [letter, self.label, self.note]


@dataclass(frozen=True)
class RuledOut:
    """An option that was considered and removed, and what removed it."""

    option: Option
    fact: str
    because: str

    def line(self) -> str:
        return f"Ruled out, {self.option.label}: {self.because}"


# What a recorded answer takes off the table. Read as: a project that is
# `local-only` cannot be offered anything needing `hosting`, `container` or
# `always-on`.
#
# Keyed by fact rather than by question, because the facts outlive the question
# that produced them. "This runs on my laptop only" constrains the storage
# question, the deployment questions and every per-step question after them,
# and a rule attached to the delivery question alone would constrain none of
# those.
CONTRADICTS: dict[str, tuple[str, ...]] = {
    "local-only": ("hosting", "container", "always-on", "domain"),
    # Not "hosting". A browser app with no server of its own is still put
    # somewhere for other people to open, and static hosting is exactly the
    # answer for it. Ruling hosting out here struck four of the five delivery
    # options off a front-end project and left it with one, which is how a rule
    # meant to widen the menu nearly emptied it.
    "no-server": ("server", "background-job"),
    "no-screens": ("screens",),
    "single-user": ("accounts", "multi-user", "permissions"),
    "offline": ("network",),
}

WHY: dict[str, str] = {
    "local-only": "this project runs only on your own machine",
    "no-server": "this project has no server of its own",
    "no-screens": "this project has no screens",
    "single-user": "only one person uses this",
    "offline": "this project works without a network",
}


# The same rule, applied to options that arrive as plain text rather than as
# `Option` objects. Every per-step question in the build loop is written by the
# planner in the moment, so its options have no tags to check, and those are
# exactly the questions where a container was offered to a laptop project.
#
# Words are matched inside the label and its consequence line. The list is
# short on purpose: a word here wrongly removes an option the user wanted, so
# it holds only the ones that cannot mean anything else. "image" is not here,
# because an image upload is not a container.
NEED_WORDS: dict[str, tuple[str, ...]] = {
    "container": ("docker", "container", "kubernetes", "podman"),
    "hosting": (
        "deploy",
        "hosted",
        "the cloud",
        "aws",
        "azure",
        "heroku",
        "vercel",
        "netlify",
        "a vps",
        "railway",
    ),
    "always-on": ("always on", "always-on", "24/7", "uptime"),
    "server": ("a server", "the server", "backend", "back end"),
    "accounts": ("sign up", "sign-up", "sign in", "sign-in", "log in", "login", "oauth"),
    "multi-user": ("multi-user", "other users", "each user", "per user"),
    "domain": ("a domain", "dns record"),
}


def needs_in(text: str) -> set[str]:
    """What a written-out option appears to require, read from its words."""
    haystack = f" {(text or '').lower()} "
    return {
        need for need, words in NEED_WORDS.items() if any(w in haystack for w in words)
    }


def contradicted(text: str, facts: set[str]) -> tuple[str, str]:
    """The fact this option contradicts, and why, or two empty strings.

    Generous on purpose, in the same direction as `is_load_bearing`: flagging
    an option that was fine costs one re-render, and letting one through costs
    a user being offered something they ruled out three questions ago and never
    being told the two are connected.
    """
    needs = needs_in(text)
    for fact in sorted(facts or ()):
        if needs & set(CONTRADICTS.get(fact, ())):
            return fact, WHY.get(fact, f"of {fact}")
    return "", ""


class OptionError(Exception):
    """An option set that must not reach a user."""


def _clean(options: list[Option]) -> list[Option]:
    return [o for o in options if str(o.label).strip()]


def rule_out(
    options: list[Option], facts: set[str]
) -> tuple[list[Option], list[RuledOut]]:
    """Split a menu into what may be offered and what the project has excluded.

    The excluded ones are returned rather than dropped. Silently removing an
    option teaches nothing, and the user cannot tell the difference between an
    option Forge decided against and one it never thought of.
    """
    offered: list[Option] = []
    removed: list[RuledOut] = []

    for option in _clean(options):
        blocking = ""
        for fact in sorted(facts):
            if set(option.needs) & set(CONTRADICTS.get(fact, ())):
                blocking = fact
                break
        if blocking:
            removed.append(
                RuledOut(option, blocking, WHY.get(blocking, f"of {blocking}"))
            )
        else:
            offered.append(option)

    return offered[:MAX_OPTIONS], removed


def problems(options: list[Option], question: str = "") -> list[str]:
    """Everything wrong with this menu, in the words the model needs to fix it.

    Returned rather than raised so a caller can decide whether a thin menu is
    worth refusing. `check` is the refusing version, and the tools use that.
    """
    found: list[str] = []
    clean = _clean(options)

    if len(clean) < MIN_OPTIONS:
        found.append(
            f"Only {len(clean)} option{'' if len(clean) == 1 else 's'}. "
            f"A question needs at least {MIN_OPTIONS}: two is a false binary, and "
            "the user ends up ratifying whichever pair you happened to think of. "
            "Name the ones a competent engineer would actually weigh here."
        )

    if len(clean) > MAX_OPTIONS:
        found.append(
            f"{len(clean)} options is more than anyone reads. Keep the "
            f"{MAX_OPTIONS} that are genuinely different and fold the rest in."
        )

    for option in clean:
        if not str(option.note).strip():
            found.append(
                f"{option.label!r} has no consequence line. Every option says what "
                "it costs you, or it is a word rather than a choice."
            )

    labels = [str(o.label).strip().lower() for o in clean]
    for label in sorted(set(labels)):
        if labels.count(label) > 1:
            found.append(f"{label!r} is listed twice.")

    stem = re.sub(r"[^a-z0-9 ]", "", (question or "").lower()).strip()
    if stem:
        for option in clean:
            if str(option.label).strip().lower() == stem:
                found.append(
                    f"{option.label!r} repeats the question back rather than "
                    "answering it."
                )

    return found


def check(options: list[Option], question: str = "") -> None:
    """Raise unless this menu is fit to put in front of someone.

    Fail closed, like every other rule in Forge (decision 004). A thin menu
    drawn anyway is the defect this module exists for, and a warning printed
    next to it would be read by nobody, because the block is what the user is
    looking at.
    """
    found = problems(options, question)
    if found:
        raise OptionError(" ".join(found))


def offer(
    options: list[Option], facts: set[str] | None = None, question: str = ""
) -> tuple[list[list[str]], list[RuledOut]]:
    """The menu as the renderers want it, having applied both rules.

    Checked **after** the project's facts are applied, not before: a menu of
    four that loses two to a recorded decision is a menu of two, and it is the
    one the user actually sees.
    """
    offered, removed = rule_out(list(options), set(facts or ()))
    check(offered, question)
    return [o.as_row(LETTERS[i]) for i, o in enumerate(offered)], removed


def from_rows(rows: list[list[str]] | None) -> list[Option]:
    """Read back the `[letter, label, note]` shape a tool is handed.

    The letter is dropped rather than kept. It is a position in a list, and
    positions change the moment a recorded decision rules one of them out.
    """
    out: list[Option] = []
    for row in rows or []:
        cells = [str(cell) for cell in (list(row) + ["", "", ""])[:3]]
        label, note = (cells[1], cells[2]) if len(row) > 2 else (cells[0], cells[1])
        out.append(Option(label=label.strip(), note=note.strip()))
    return out


@dataclass
class Menu:
    """A question's options, with the ones the project has already excluded."""

    rows: list[list[str]] = field(default_factory=list)
    removed: list[RuledOut] = field(default_factory=list)

    def ruled_out_lines(self) -> list[str]:
        return [item.line() for item in self.removed]
