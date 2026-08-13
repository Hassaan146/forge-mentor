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

## The three things this file grew after a user watched it run

**Options were thin, so now there is a floor.** Only the stack question carried
any. The rest were improvised, and improvisation with no rule produced "Docker,
or run it locally": two options where there are six, one of them already ruled
out by an earlier answer. Every question now carries a real menu, and
`forge_options` refuses one that is too short or has no consequences.

**The menu narrows itself against what is recorded.** A project that runs only
on the user's machine is never offered a container, and is offered SQLite and a
plain file, because those are what the answer left standing. The excluded ones
are shown struck out with the reason, since the exclusion is the teaching.

**Answers open questions.** Choosing to deploy is not one decision, it is five,
and they only exist for a project that deploys. A question that does not apply
was never in the sequence rather than being skipped in front of the user.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import forge_options as fo
import forge_state as fs
from forge_options import Option


@dataclass(frozen=True)
class Question:
    """One foundation question, and enough to teach it."""

    key: str
    question: str
    subtitle: str
    means: tuple[str, ...]
    # The idea underneath, named. A question is about a concept the project
    # actually contains ("where the data lives when nothing is running"), not
    # about a menu, and saying which concept is what makes the answer portable
    # to the next project rather than trivia about this one.
    concept: str = ""
    # What goes wrong if this is answered badly, in one line, and it goes on
    # screen with a bar down the side. Not decoration: a question the user
    # cannot see the weight of is a question they answer at random, and the
    # ones with the worst consequences are usually the ones that sound
    # administrative. "Where does configuration live" reads like paperwork
    # until the day the key is in the repository.
    matters: str = ""
    options: tuple[Option, ...] = ()
    # Menus that only make sense once something else is known. First matching
    # fact wins, in the order written, and `options` is the fallback. This is
    # how the storage question offers SQLite to a local project and IndexedDB
    # to a browser one without either list being guessed.
    options_when: tuple[tuple[str, tuple[Option, ...]], ...] = ()
    # Stages that make this question pointless. A single-file script has no
    # delivery question worth asking, and Forge should not invent one to fill
    # the sequence.
    skip_when: tuple[str, ...] = field(default=())

    def menu(self, facts: set[str] | None = None) -> tuple[tuple[Option, ...], str]:
        """The option list this question has, given what the project has decided."""
        known = set(facts or ())
        for fact, options in self.options_when:
            if fact in known:
                return options, fact
        return self.options, ""


INTENT = Question(
    key="intent",
    question="What's the idea?",
    subtitle="in your own words, the questions after this all follow from it",
    matters="Every question after this is asked inside your answer, so a vague one costs six.",
    concept="the thing you are making, before anything about how it is made",
    # Two lines, per rule R10. This shipped as three paragraphs of advice on how
    # to describe an idea, in front of someone who only wanted to describe
    # theirs. The reasoning behind the question belongs in this comment and in
    # the decision record, not on the screen.
    means=(
        "Say it the way you would to a friend, not the way you would write a spec.",
        '"A to-do app for myself" is a complete answer.',
    ),
    # No options, deliberately. It is the only genuinely open question, and the
    # one the other five are asked inside: a recommendation about storage or
    # hosting is not answerable until Forge knows what the thing is.
)

NAME = Question(
    key="name",
    question="What is this called, and where will the code live?",
    subtitle="the name and the repository, which everything after this is written into",
    matters="Renaming a repository later breaks every link, clone and pipeline pointing at it.",
    concept="a repository is the one place the code and its history live together",
    means=(
        "The name goes in the folder, the repository, and every link anyone sends you.",
        "Forge needs the repository to push, to open a pull request, and to read reviews.",
    ),
    # Deliberately open. A menu here would be Forge naming somebody's project
    # for them, and the answer is two facts it cannot guess: what they call it
    # and whose account it goes under.
)

STACK = Question(
    key="stack",
    question="What are you building this with?",
    subtitle="the first decision, everything below is built on top of it",
    matters="Changing shape later is not a refactor, it is starting again with opinions.",
    concept="the shape of the project: screens, a server, or both",
    means=(
        "You are choosing the shape: screens, a server, or both.",
        "Language and framework follow from that, so they are settled together.",
    ),
    # Named by shape, not by technology. "Browser + small API" and "Python
    # service" described what you would type rather than what you would have,
    # so the option a user actually wanted, build the API first and add screens
    # later, was on the list and unrecognisable. A menu that hides an answer is
    # the same failure as not offering it.
    #
    # One line each, per rule R10.
    options=(
        Option(
            "Front end only",
            "screens in the browser. No server; data stays on this machine",
            gives=("no-server", "screens"),
        ),
        Option(
            "Back end only",
            "an API and a database now, screens added later or by someone else",
            needs=("server",),
            gives=("no-screens", "server"),
        ),
        Option(
            "Both together",
            "screens plus your own API and database. Most parts, and the data is yours",
            needs=("server",),
            gives=("screens", "server"),
        ),
        Option(
            "Command line",
            "you type commands and it answers. Nothing to host, no screens at all",
            gives=("no-screens", "cli", "cli-single-user"),
        ),
        Option(
            "A phone app",
            "screens on a phone, and anything shared between phones needs a server",
            gives=("screens", "mobile"),
        ),
    ),
)

# The storage menus, one per shape. This is the question that produced the
# original defect: asked before the stack, its options assumed a browser nobody
# had chosen. Asked after it, the shape decides the list, and the list is real.
BROWSER_STORAGE = (
    Option(
        "The browser's own storage",
        "simplest possible. Survives a refresh, dies with the browser profile",
        gives=("browser-storage",),
    ),
    Option(
        "IndexedDB",
        "still the browser, but built for real amounts of data and searching it",
        gives=("browser-storage",),
    ),
    Option(
        "A file the user saves and loads",
        "their data is a file they own. Nothing is lost when the browser is",
    ),
    Option(
        "Nothing is kept",
        "it starts empty every time, which is a real answer for a tool you use once",
    ),
)

LOCAL_STORAGE = (
    Option(
        "SQLite, one file",
        "a real database in a single file. No server to run, and it is copyable",
        gives=("sqlite",),
    ),
    Option(
        "Plain files you can read",
        "JSON or CSV on disk. Easy to inspect and to fix by hand when it breaks",
    ),
    Option(
        "Postgres running on this machine",
        "the full thing locally, if you know it is going to grow into a service",
        needs=("server",),
    ),
    Option(
        "Nothing is kept",
        "it starts empty every time, which is a real answer for a tool you use once",
    ),
)

SERVED_STORAGE = (
    Option(
        "SQLite, one file",
        "a real database in a single file. Fine until several people write at once",
        gives=("sqlite",),
    ),
    Option(
        "Postgres",
        "the usual answer for a service. More to run, and it will not surprise you",
        needs=("server",),
    ),
    Option(
        "MySQL",
        "the other usual answer. Pick it if it is what you or your host already run",
        needs=("server",),
    ),
    Option(
        "A hosted database someone else runs",
        "you get backups and uptime, and you pay for them monthly",
        needs=("hosting",),
    ),
    Option(
        "Plain files you can read",
        "JSON or CSV on disk. Honest for small data, painful once two things write",
    ),
)

DATA = Question(
    key="data",
    question="What is stored, and what happens if it is lost?",
    subtitle="decides the data model, backups, and how much a mistake costs",
    matters="What you cannot rebuild is the only part of this that cannot be written twice.",
    concept="where the information lives when the program is not running",
    means=(
        "Where the data lives decides how it is written and read.",
        "What losing it would cost decides how hard you work to prevent that.",
    ),
    # Conditional, never fixed. A fixed list here is exactly what put
    # browser-only storage in front of a project that had not chosen a browser.
    options_when=(
        ("no-server", BROWSER_STORAGE),
        ("browser-storage", BROWSER_STORAGE),
        ("local-only", LOCAL_STORAGE),
        ("cli", LOCAL_STORAGE),
        ("server", SERVED_STORAGE),
    ),
)

PEOPLE = Question(
    key="people",
    question="Is there more than one person using this?",
    subtitle="decides accounts, sign-in, and who can see what",
    matters="Building accounts you do not need is weeks. Adding them later touches every screen.",
    concept="whether the program has to know who is using it",
    means=(
        "Only ever you? Then there is nothing to build here, and Forge will not invent it.",
        "A second person means proving who they are, and deciding what they may see.",
    ),
    options=(
        Option(
            "Only me",
            "no accounts, no sign-in, nothing to get wrong. The cheapest answer",
            gives=("single-user",),
        ),
        Option(
            "A few people I know",
            "they need to sign in, but not to be kept apart from each other",
            needs=("accounts",),
            gives=("accounts", "multi-user"),
        ),
        Option(
            "Anyone who signs up",
            "sign-up, password resets, and one person never seeing another's data",
            needs=("accounts", "multi-user"),
            gives=("accounts", "multi-user", "permissions"),
        ),
        Option(
            "Everyone in one organisation",
            "they sign in with the account they already have at work",
            needs=("accounts", "multi-user"),
            gives=("accounts", "multi-user", "permissions"),
        ),
    ),
    skip_when=("cli-single-user",),
)

DELIVERY = Question(
    key="delivery",
    question="Where does this run when you are not running it?",
    subtitle="decides hosting, configuration, and how a change reaches people",
    matters="This decides what deployment means for you, and whether it exists at all.",
    concept="where the program lives when your own machine is off",
    means=(
        "Only on your own machine is a legitimate answer.",
        "If other people use it, something has to hold it up when your laptop shuts.",
    ),
    options=(
        Option(
            "Only on my machine",
            "nothing to host and nothing to pay for. Nobody else can reach it",
            gives=("local-only",),
        ),
        Option(
            "A service that runs it for me",
            "you push, it deploys. Least to operate, and you live inside their rules",
            needs=("hosting",),
            gives=("deployed", "always-on"),
        ),
        Option(
            "A small server I rent",
            "yours to configure and yours to patch. Cheap, and it is now your job",
            needs=("hosting", "always-on"),
            gives=("deployed", "always-on"),
        ),
        Option(
            "An image anyone can run",
            "the same everywhere, at the cost of learning containers first",
            needs=("container",),
            gives=("deployed", "container"),
        ),
        Option(
            "Files on a static host",
            "no server at all, so it is cheap and it cannot keep a secret",
            needs=("hosting",),
            gives=("deployed",),
        ),
    ),
    skip_when=("cli-single-user",),
)

DONE = Question(
    key="done",
    question="What does 'finished' mean for a step in this project?",
    subtitle="decides the gate, what has to be true before work moves on",
    matters="Set the bar too low and you carry the difference for the rest of the project.",
    concept="the bar a piece of work clears before the next one starts",
    means=(
        "Passing tests and a clean review are already required (decision 009).",
        "What varies is the bar: a weekend tool and a payments service are not the same.",
    ),
    options=(
        Option(
            "The floor: tests pass and the review is clean",
            "the minimum Forge enforces anyway. Fast, and it trusts the tests",
        ),
        Option(
            "The floor, and you have run it yourself",
            "you see it work once before it counts. Slower, and it catches the obvious",
        ),
        Option(
            "The floor, and you can explain it back",
            "the teaching bar. It is the slowest, and it is the one you remember",
        ),
        Option(
            "The floor, and someone else has looked",
            "a second person signs off. Right for work other people depend on",
            needs=("multi-user",),
        ),
    ),
)

# Fixed, not chosen per project. A planner picking the order will sometimes
# pick badly, and a question that was skipped is invisible — unlike a wrong
# answer, which the user can see and argue with.
FOUNDATION: tuple[Question, ...] = (INTENT, NAME, STACK, DATA, PEOPLE, DELIVERY, DONE)


# --------------------------------------------------------------------------
# questions an answer opens
# --------------------------------------------------------------------------

# Deciding to deploy is not one decision. It is where it runs, how a change
# gets there, what happens when it falls over, and where the secrets live, and
# every one of those is load-bearing. They are asked only of a project that
# deploys, which is why they are here rather than in FOUNDATION: a question that
# does not apply should never have been in the sequence, not skipped in front of
# the user with an apology.
RELEASE = Question(
    key="release",
    question="How does a change get from your machine to the running copy?",
    subtitle="decides what a mistake costs and how quickly it is undone",
    matters="The cost of a bad release is measured from here, not from when you notice.",
    concept="the path a change takes to reach the people using it",
    means=(
        "The question underneath is how you undo a bad one, not how you ship a good one.",
        "Automatic is faster to use and slower to build. Both are real answers.",
    ),
    options=(
        Option(
            "By hand, when you decide",
            "you copy it up yourself. Nothing to build, and nothing stops a bad one",
        ),
        Option(
            "Automatically, whenever you push",
            "every push goes live. Fast, and a mistake is live before you see it",
            needs=("hosting",),
        ),
        Option(
            "Automatically, but only after the tests pass",
            "the usual answer. A broken build never reaches anyone",
            needs=("hosting",),
        ),
        Option(
            "You push a button once the tests pass",
            "the machine prepares it, you decide when. Slowest, and the safest",
            needs=("hosting",),
        ),
    ),
)

FAILURE = Question(
    key="failure",
    question="What happens when it falls over at three in the morning?",
    subtitle="decides logging, alerting, and how long it is broken for",
    matters="The gap between it breaking and you knowing is the outage your users see.",
    concept="how you find out something is wrong, and what you look at",
    means=(
        "Everything falls over. What differs is whether you hear about it from a user.",
        "The cheap version is one alert and readable logs, and it is worth having.",
    ),
    options=(
        Option(
            "You find out when someone tells you",
            "nothing to build. Right for a tool with three users who know you",
        ),
        Option(
            "It writes logs you can read afterwards",
            "you can answer what happened, but only once you go looking",
        ),
        Option(
            "It emails you when it breaks",
            "one alert, cheap to add, and it is the difference between hours and days",
            needs=("hosting",),
        ),
        Option(
            "It restarts itself and tells you",
            "most outages fix themselves. More to set up, and it hides slow rot",
            needs=("hosting", "always-on"),
        ),
    ),
)

SECRETS = Question(
    key="secrets",
    question="Where do the keys and passwords live once this is deployed?",
    subtitle="decides how a leak happens, and it is the one that ends up on GitHub",
    matters="A key in the repository is a key in the history, and history is forever.",
    concept="how the running program gets a secret without it being in the code",
    means=(
        "The security floor already forbids a secret in the code. This is what replaces it.",
        "The answer is about who can read it, not about where it is easiest to put.",
    ),
    options=(
        Option(
            "Environment variables where it runs",
            "the usual answer. Simple, and anyone with the machine can read them",
            needs=("hosting",),
        ),
        Option(
            "A file that is never committed",
            "easy to hold in your head, and easy to commit by accident one day",
        ),
        Option(
            "Your host's own secret store",
            "encrypted, audited, and it ties you a little more tightly to them",
            needs=("hosting",),
        ),
        Option(
            "A dedicated secret manager",
            "rotation and history. Real work to set up, and it pays back at a team",
            needs=("hosting",),
        ),
    ),
)

BACKUP = Question(
    key="backup",
    question="If this machine died tonight, what would you want back?",
    subtitle="decides what is copied, how often, and how much you would retype",
    matters="A backup nobody has restored from is a folder, not a backup.",
    concept="the difference between the data you can rebuild and the data you cannot",
    means=(
        "A local project is one disk away from losing everything, and it is easy to fix.",
        "The honest answer is sometimes 'nothing', and that is worth saying out loud.",
    ),
    options=(
        Option(
            "Nothing, it can all be made again",
            "no work at all, and it is true more often than people admit",
        ),
        Option(
            "The data file, copied somewhere else",
            "one command. Covers the case that actually happens, which is a dead disk",
        ),
        Option(
            "The data, on a schedule, without you remembering",
            "a scheduled copy. It is the version that still works in six months",
        ),
        Option(
            "Everything, versioned, so you can go back a week",
            "you can undo a bad change, not just a dead disk. More to keep and to test",
        ),
    ),
)

IDENTITY = Question(
    key="identity",
    question="How does someone prove they are who they say they are?",
    subtitle="decides what you store, what you can leak, and how much you build",
    matters="Getting this wrong is the failure that ends up in the news with your name on it.",
    concept="proving identity, which is separate from deciding what someone may do",
    means=(
        "Every option here is one you can get wrong in a way that ends up in the news.",
        "The floor stands whatever you pick: passwords are hashed, never stored as typed.",
    ),
    options=(
        Option(
            "Email and password, yours to hold",
            "no dependency on anyone. Resets, hashing and lockouts are now yours too",
            needs=("accounts",),
        ),
        Option(
            "Sign in with an account they already have",
            "Google or GitHub do the hard part. You depend on them staying up",
            needs=("accounts",),
        ),
        Option(
            "A link emailed to them each time",
            "no password to leak or reset. Every sign-in waits on an email arriving",
            needs=("accounts",),
        ),
        Option(
            "A login service you pay for",
            "the fastest to a safe answer, and it is a monthly bill and a lock-in",
            needs=("accounts", "hosting"),
        ),
    ),
    # A project with one person has nobody to identify. Asked anyway, it is the
    # product inventing work, which is the other half of the failure it exists
    # to prevent.
    skip_when=("single-user", "cli-single-user"),
)

PERMISSIONS = Question(
    key="permissions",
    question="Once they are in, what is each person allowed to see?",
    subtitle="decides the checks in every query, and the one bug class that leaks data",
    matters="The common leak is not a broken login, it is a page that forgot to check.",
    concept="authorisation: what someone may do, once you know who they are",
    means=(
        "The common leak is not a broken login. It is a page that forgot to check.",
        "Simplest is 'you see only your own', and it is enough for most projects.",
    ),
    options=(
        Option(
            "Everyone sees their own things only",
            "one rule, checked everywhere. The simplest thing that is not wrong",
            needs=("multi-user",),
        ),
        Option(
            "Everyone sees everything",
            "no checks to write. Honest for a tool used by people who trust each other",
            needs=("multi-user",),
        ),
        Option(
            "Two kinds of person: normal and admin",
            "one extra check. Covers most of what a small product ever needs",
            needs=("multi-user", "permissions"),
        ),
        Option(
            "Roles you can change without a deploy",
            "flexible, and it is a whole feature with its own screens and its own bugs",
            needs=("multi-user", "permissions"),
        ),
    ),
    skip_when=("single-user", "cli-single-user"),
)

# What a recorded answer opens up. The key is a fact; the value is the questions
# that only exist once it is true.
FOLLOW_UPS: dict[str, tuple[Question, ...]] = {
    "deployed": (RELEASE, FAILURE, SECRETS),
    "container": (SECRETS,),
    "local-only": (BACKUP,),
    "accounts": (IDENTITY,),
    "multi-user": (PERMISSIONS,),
}

# Where each follow-up is inserted: straight after the question whose answer
# opened it, so the sequence still reads in one direction.
AFTER: dict[str, str] = {
    "release": "delivery",
    "failure": "delivery",
    "secrets": "delivery",
    "backup": "delivery",
    "identity": "people",
    "permissions": "people",
}

ALL_QUESTIONS: tuple[Question, ...] = FOUNDATION + (
    RELEASE,
    FAILURE,
    SECRETS,
    BACKUP,
    IDENTITY,
    PERMISSIONS,
)

BY_KEY = {q.key: q for q in ALL_QUESTIONS}


# --------------------------------------------------------------------------
# reading what the project has already settled
# --------------------------------------------------------------------------

# For an answer that matched no option, because the user typed their own. The
# words are deliberately few: a fact guessed from prose is a fact that will one
# day rule out an option the user wanted, so only the unmistakable ones count.
FACT_WORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("local-only", ("only on my machine", "my own machine", "just locally", "my laptop")),
    ("single-user", ("only me", "just me", "only ever me", "nobody else")),
    ("no-server", ("no server", "without a server", "no backend", "no back end")),
    ("deployed", ("deploy", "hosted", "hosting", "online", "on the internet")),
)


def match_in(text: str, pool: tuple[Question, ...]) -> Question | None:
    """Which of these questions a recorded question text belongs to, if any.

    Matched on the text rather than an id, because a project may record other
    decisions in between and the numbering is shared across branches (decision
    018). Kept in one function because two copies of a matching rule are two
    rules: a caller that spells it slightly differently will disagree about
    whether something is answered, and nothing in the run would say so.
    """
    haystack = (text or "").lower()
    for question in pool:
        if question.question.lower() in haystack:
            return question
    return None


def match(text: str) -> Question | None:
    """The foundation and its follow-ups. Topics use `match_in` with their own."""
    return match_in(text, ALL_QUESTIONS)


def answered_from(forge_dir: Path, pool: tuple[Question, ...]) -> set[str]:
    """Which of these questions already have a decided record."""
    found: set[str] = set()
    for decision in fs.list_decisions(forge_dir):
        if decision.status.strip().lower() != fs.STATUS_DECIDED:
            continue
        question = match_in(decision.question, pool)
        if question is not None:
            found.add(question.key)
    return found


def chosen(decision: fs.Decision) -> str:
    """What the user actually picked, read back out of the record.

    The body's first heading is the choice, because that is how `record_answer`
    writes it. Read from the record rather than remembered in a field, for the
    same reason everything else is (decision 019): a value held anywhere else
    is a value that disagrees with the file after an account switch.
    """
    for line in (decision.body or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if stripped:
            return stripped
    return ""


def _facts_from(question: Question, choice: str, known: set[str]) -> set[str]:
    """What one answer settles, whether it came from the menu or from prose."""
    said = (choice or "").strip().lower()
    if not said:
        return set()

    first = said.split()[0] if said.split() else ""
    marked = first.rstrip(").:,-")

    options, _ = question.menu(known)
    # **No facts from prose that was never a menu.** The keyword fallback below
    # exists for one case: a user who typed their own answer instead of picking
    # a letter. Applied to an open question it reads facts out of a
    # description, and "a to-do app I can use from my phone and my laptop" was
    # recorded as local-only, which struck Supabase and Neon off the database
    # menu of a project that had just chosen a hosted service.
    if not options:
        return set()
    for index, option in enumerate(options):
        letter = fo.LETTERS[index].lower()
        label = option.label.lower()
        # The length floor is not fussiness. Without it "no" matches "nothing
        # is kept" as a substring, and a project acquires a fact from a word
        # that happened to be inside another word.
        by_text = len(said) >= 4 and (label in said or said in label)
        # **"A" the letter, never "a" the article.** Accepting a leading
        # "a " read the answer "A small server I rent" as option A, "Only on my
        # machine", so a project that had just chosen to rent a server was
        # recorded as local-only and never asked how a change would reach it.
        # The whole answer has to be the letter, or the letter has to be marked
        # as one: "A)", "A.", "A:".
        by_letter = said.rstrip(").:,-") == letter or (
            marked == letter and marked != first
        )
        if by_letter or by_text:
            return set(option.gives)

    found: set[str] = set()
    for fact, words in FACT_WORDS:
        if any(word in said for word in words):
            found.add(fact)
    return found


def facts(forge_dir: Path) -> set[str]:
    """Everything this project has settled, as tags later questions narrow on.

    This is what makes a menu belong to a project rather than to a topic. A run
    that has said "only on my machine" never sees a container offered again,
    and the storage question offers a file and SQLite rather than a hosted
    database, because those are what the earlier answer left standing.
    """
    found: set[str] = set()
    for decision in fs.list_decisions(forge_dir):
        if decision.status.strip().lower() != fs.STATUS_DECIDED:
            continue
        question = match(decision.question)
        if question is None:
            continue
        found |= _facts_from(question, chosen(decision), found)
    return found


def source_of(forge_dir: Path, fact: str) -> fs.Decision | None:
    """Which recorded answer put this fact on the table.

    Needed wherever a fact is used against the user: "a container is ruled out"
    is an assertion, and "a container is ruled out by decision 011, where you
    said this runs only on your machine" is one they can argue with. The second
    is the only version that belongs in a product about decisions.
    """
    known: set[str] = set()
    for decision in fs.list_decisions(forge_dir):
        if decision.status.strip().lower() != fs.STATUS_DECIDED:
            continue
        question = match(decision.question)
        if question is None:
            continue
        gained = _facts_from(question, chosen(decision), known)
        if fact in gained:
            return decision
        known |= gained
    return None


def answered_keys(forge_dir: Path) -> set[str]:
    """Which questions already have a recorded decision."""
    answered: set[str] = set()
    for decision in fs.list_decisions(forge_dir):
        if decision.status.strip().lower() != fs.STATUS_DECIDED:
            continue
        question = match(decision.question)
        if question is not None:
            answered.add(question.key)
    return answered


def sequence(forge_dir: Path, skip: set[str] | None = None) -> tuple[Question, ...]:
    """The questions this project is actually being asked, in order.

    Not a constant. The six are always there; the rest are opened by answers,
    which is why the count moves as the interrogation runs. Rule R4 requires the
    progress to be shown, and a total that grows honestly is better than one
    that was a guess and stayed one.
    """
    known = facts(forge_dir) | set(skip or ())

    unlocked: list[Question] = []
    for fact, questions in FOLLOW_UPS.items():
        if fact in known:
            unlocked += [q for q in questions if q not in unlocked]

    out: list[Question] = []
    for question in FOUNDATION:
        if known & set(question.skip_when):
            continue
        out.append(question)
        for follow in unlocked:
            if AFTER.get(follow.key) == question.key and follow not in out:
                out.append(follow)

    # A follow-up whose parent was skipped still gets asked, at the end, rather
    # than silently lost. Losing one would be the failure decision 033 exists to
    # prevent, arriving through the back door.
    for follow in unlocked:
        if follow not in out:
            out.append(follow)

    return tuple(out)


def next_question(forge_dir: Path, skip: set[str] | None = None) -> Question | None:
    """The next question, or None when there is nothing left to ask."""
    done = answered_keys(forge_dir)
    for question in sequence(forge_dir, skip):
        if question.key not in done:
            return question
    return None


def position(forge_dir: Path, skip: set[str] | None = None) -> tuple[int, int]:
    """How far through the interrogation this project is, for the progress line."""
    live = sequence(forge_dir, skip)
    keys = {q.key for q in live}
    return len(answered_keys(forge_dir) & keys), len(live)


def menu_for(
    question: Question, forge_dir: Path | None = None, facts_known: set[str] | None = None
) -> fo.Menu:
    """This question's options, narrowed by what the project has already decided.

    Returns the rows a renderer wants **and** what was removed, because an
    option struck out with its reason teaches more than one that was never
    mentioned. A user who is told a container is ruled out because they said
    the thing runs on their laptop has learned what a container is for.
    """
    known = set(facts_known if facts_known is not None else set())
    if forge_dir is not None and facts_known is None:
        known = facts(forge_dir)

    options, _ = question.menu(known)
    if not options:
        return fo.Menu(rows=[], removed=[])

    # A question is never narrowed by the answers it is offering. The delivery
    # question settles whether this project is local-only, so applying
    # local-only to its own menu strikes out four of its five options and leaves
    # the one that produced the fact: the question would answer itself and then
    # present the result as a choice.
    own = {fact for option in options for fact in option.gives}

    try:
        rows, removed = fo.offer(list(options), known - own, question.question)
    except fo.OptionError:
        # Narrowed past the floor. The question is still worth asking, so it is
        # asked openly rather than with a menu of one, and the exclusions are
        # shown so the user can see why the usual answers are not on offer.
        # Raising here would take the tool down and hand the model a traceback
        # in place of a question.
        _kept, removed = fo.rule_out(list(options), known - own)
        return fo.Menu(rows=[], removed=removed)

    return fo.Menu(rows=rows, removed=removed)
