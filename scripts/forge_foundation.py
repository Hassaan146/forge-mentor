"""Forge Mentor — the foundation questions, in order (decision 033).

The order is fixed rather than chosen per project, and the stack comes first.

**What comes before the stack.** One open question: what do you want to
make? It has no options, because every option Forge could offer would already
assume an answer to it — a menu narrows what the user was about to say. It is
also what makes the stack question answerable, since a recommendation needs to
know what is being built.

**Why the stack is next.** Every other foundation question is asked *inside* an
answer to this one. "Where is the data kept" means something different for a
browser app, a Django service and a command-line tool. Ask storage before the
stack and you are asking a question whose options are not knowable yet — and
the user answers anyway, because they were asked.

That is not hypothetical. On a real run Forge's second question was "where are
the todos stored", offering localStorage, IndexedDB and a file. Every option
assumed a browser, which nobody had decided. The stack had been assumed instead
of chosen, which is the exact failure the product exists to prevent, happening
in its own opening move.

**Why the stack is one question and not three.** Language, framework and
runtime are not independent. Choosing Python does not settle Django against
FastAPI; choosing a browser front end does not settle whether a server exists.
Asked separately, an answer to one quietly rules out most answers to the next
without anyone noticing. So they are put together and the combinations are
named as whole options — what is being chosen is a shape of project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import forge_state as fs


@dataclass(frozen=True)
class Question:
    """One foundation question, and enough to teach it."""

    key: str
    question: str
    subtitle: str
    means: tuple[str, ...]
    options: tuple[tuple[str, str, str], ...] = ()
    # Stages that make this question pointless. A single-file script has no
    # delivery question worth asking, and Forge should not invent one to fill
    # the sequence.
    skip_when: tuple[str, ...] = field(default=())


INTENT = Question(
    key="intent",
    question="What's the idea?",
    subtitle="in your own words — the five questions after this all follow from it",
    means=(
        "Describe it the way you would to a friend, not the way you would write",
        'a specification. "A to-do app for myself" is a complete answer. So is',
        "a paragraph about a business you are trying to start.",
        "",
        "Useful if you have it: who it is for, and what it should do on the",
        "first day it works. Leave out anything you have not settled — that is",
        "what the next five questions are for.",
        "",
        "Nothing is chosen yet, and there is nothing to pick from. Every option",
        "Forge could offer here would already assume something about your idea,",
        "and a menu narrows what you were about to say.",
    ),
    # No options, deliberately. It is the only genuinely open question, and the
    # one the other five are asked inside: a recommendation about storage or
    # hosting is not answerable until Forge knows what the thing is.
)

STACK = Question(
    key="stack",
    question="What are you building this with?",
    subtitle="the first decision — everything below is built on top of it",
    means=(
        "This settles three things at once, because they do not separate cleanly:",
        "the language, the framework, and where the code actually runs.",
        "Picking one narrows the others, so they are chosen together as a shape",
        "rather than as three words.",
    ),
    options=(
        (
            "A",
            "Browser only",
            "HTML, CSS and JavaScript in the page. No server, nothing to deploy, "
            "and the data lives in the browser",
        ),
        (
            "B",
            "Browser + small API",
            "a front end plus a thin server you own. Data lives in a database; "
            "more moving parts, but the data is yours",
        ),
        (
            "C",
            "Python service",
            "FastAPI or Django with a database behind it. No front end unless you "
            "add one; strongest for logic and data",
        ),
        (
            "D",
            "Command line tool",
            "a script or CLI on your own machine. Fastest to build, nothing to "
            "host, no users but you",
        ),
    ),
)

DATA = Question(
    key="data",
    question="What is stored, and what happens if it is lost?",
    subtitle="decides the data model, backups, and how much a mistake costs",
    means=(
        "Two questions that are really one. Where data lives decides how it is",
        "written and read; what its loss would cost decides how hard you work to",
        "prevent that. Answer the second honestly and the first often settles",
        "itself.",
    ),
    # No options: they depend entirely on the stack, and offering a fixed list
    # here is what put browser-only storage in front of a project that had not
    # chosen a browser.
)

PEOPLE = Question(
    key="people",
    question="Is there more than one person using this?",
    subtitle="decides accounts, sign-in, and who can see what",
    means=(
        "If it is only ever you, there is nothing to build here and Forge will",
        "not invent it. The moment a second person exists, two things follow:",
        "proving who someone is, and deciding what they are allowed to see.",
    ),
    skip_when=("cli-single-user",),
)

DELIVERY = Question(
    key="delivery",
    question="Where does this run when you are not running it?",
    subtitle="decides hosting, configuration, and how a change reaches people",
    means=(
        "A project that only ever runs on your machine has no answer here, and",
        "that is a legitimate answer. If other people use it, something has to",
        "hold it up when your laptop is shut.",
    ),
    skip_when=("cli-single-user",),
)

DONE = Question(
    key="done",
    question="What does 'finished' mean for a step in this project?",
    subtitle="decides the gate — what has to be true before work moves on",
    means=(
        "Forge already requires tests to pass and a clean review (decision 009).",
        "What varies by project is how much of that is proportionate: a weekend",
        "tool and a service handling other people's money do not deserve the same",
        "bar, and pretending otherwise makes the gate theatre.",
    ),
)

# Fixed, not chosen per project. A planner picking the order will sometimes
# pick badly, and a question that was skipped is invisible — unlike a wrong
# answer, which the user can see and argue with.
FOUNDATION: tuple[Question, ...] = (INTENT, STACK, DATA, PEOPLE, DELIVERY, DONE)

BY_KEY = {q.key: q for q in FOUNDATION}


def answered_keys(forge_dir: Path) -> set[str]:
    """Which foundation questions already have a recorded decision."""
    answered: set[str] = set()
    for decision in fs.list_decisions(forge_dir):
        if decision.status.strip().lower() != fs.STATUS_DECIDED:
            continue
        # Matched on the question text rather than an id, because a project may
        # record other decisions in between and the numbering is shared.
        for question in FOUNDATION:
            if question.question.lower() in decision.question.lower():
                answered.add(question.key)
    return answered


def next_question(forge_dir: Path, skip: set[str] | None = None) -> Question | None:
    """The next foundation question, or None when the foundation is done."""
    done = answered_keys(forge_dir)
    skipped = skip or set()
    for question in FOUNDATION:
        if question.key in done:
            continue
        if skipped & set(question.skip_when):
            continue
        return question
    return None


def position(forge_dir: Path) -> tuple[int, int]:
    """How far through the foundation this project is, for the progress line."""
    return len(answered_keys(forge_dir)), len(FOUNDATION)

