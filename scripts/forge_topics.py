"""Forge Mentor: the questions a subject owes you before it is built.

**The gap this closes.** The foundation asks twelve questions and then stops.
After that every question was written by the planner in the moment, which means
a project could reach a step called "store the todos" and be asked one question
about it, or none worth the name, and a database would be chosen by whichever
model was writing that turn. The user's report was exact: *"you have to ask me
about the database, then how I want to configure it, then whether I want to
deploy, whether I want it orchestrated. I want to figure out whether I have to
use Supabase or something else."*

None of that could be asked, because none of it existed. The stack question
names a shape by design (decision 041), and nothing after it ever named a
product.

**What a topic is.** A subject a project can contain, with the questions that
subject owes the user before code touching it is written. Database is a topic.
So are deployment, configuration, the API surface, background work, uploads and
payments. Each carries real named options: Supabase and Neon and Postgres, not
"a relational database".

**When they are asked.** The first time a step touches the topic, and once per
project. "Which database" is not a per-step question, it is a project question
that some step is the first to need, and asking it again at step nine would be
the thing the product exists to prevent, done by the product. The step still
gets its own decision on top (decision 037); the topic questions are what has to
be true before that step is buildable at all.

**Why they are here and not in a brief.** Every rule in this repository that
lived in a brief was eventually skipped by a model in a hurry, and nobody
noticed, because a skipped question is invisible in a way a wrong answer is not.
So the gate reads this file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import forge_foundation as ff
from forge_foundation import Question
from forge_options import Option

# --------------------------------------------------------------------------
# the database
# --------------------------------------------------------------------------

DB_CHOICE = Question(
    key="db-choice",
    question="Which database is this project going to use?",
    subtitle="the one answer the most other answers are built on top of",
    concept="a database is a program that keeps your data safe while yours is not running",
    matters="Moving between these later means rewriting every query you have written by then.",
    means=(
        "They differ in what you run yourself, what you pay for, and what you can undo.",
        "The honest question is who you want operating it at two in the morning.",
    ),
    options=(
        Option(
            "Postgres you run yourself",
            "the standard answer. Nothing it cannot do, and it is yours to keep alive",
            needs=("server",),
            gives=("postgres", "sql"),
        ),
        Option(
            "Supabase",
            "hosted Postgres with sign-in and file storage included. Fast to start, and their shape",
            needs=("hosting",),
            gives=("postgres", "sql", "hosted-db", "auth-included"),
        ),
        Option(
            "Neon",
            "Postgres that sleeps when idle and branches like git. Cheap, and it wakes slowly",
            needs=("hosting",),
            gives=("postgres", "sql", "hosted-db"),
        ),
        Option(
            "SQLite, one file",
            "no server, no bill, no network. One writer at a time, and that is the whole catch",
            gives=("sqlite", "sql"),
        ),
        Option(
            "MySQL or MariaDB",
            "as capable in practice. Pick it if it is what your host or your team already runs",
            needs=("server",),
            gives=("sql",),
        ),
        Option(
            "MongoDB",
            "no fixed shape, so early changes are free and late mistakes are expensive",
            needs=("server",),
            gives=("nosql",),
        ),
    ),
)

DB_WHERE = Question(
    key="db-where",
    question="Where does the database actually run?",
    subtitle="decides the bill, the backups, and who is on call for it",
    concept="the difference between a database you operate and one you rent",
    matters="Whoever runs it is responsible for it staying up and for its backups working.",
    means=(
        "On your machine it is free and it is gone when the machine is.",
        "Rented, someone else patches it and you pay monthly and inherit their limits.",
    ),
    options=(
        Option(
            "On this machine, next to the code",
            "nothing to pay and nothing to configure. It exists only here",
        ),
        Option(
            "In a container beside the app",
            "the same setup everywhere, at the cost of learning containers first",
            needs=("container",),
            gives=("container",),
        ),
        Option(
            "A managed service you rent",
            "backups, patching and uptime are theirs. A monthly bill and their limits",
            needs=("hosting",),
            gives=("hosted-db",),
        ),
        Option(
            "A server you already have",
            "no new bill and no new vendor. It is now one more thing you maintain",
            needs=("server",),
        ),
    ),
)

DB_SHAPE = Question(
    key="db-shape",
    question="How does the shape of the data change after it has real data in it?",
    subtitle="decides whether a change to a table is routine or frightening",
    concept="migrations: a recorded, repeatable change to the shape of stored data",
    matters="Without a plan here, the first shape change after launch risks the data.",
    means=(
        "The shape will change. The question is whether the change is repeatable.",
        "A migration is a file that turns yesterday's shape into today's, in order.",
    ),
    options=(
        Option(
            "A migration tool, files kept in the repository",
            "the usual answer. Every change is reviewable and runs the same everywhere",
        ),
        Option(
            "The framework does it from the models",
            "least to write. It decides what your change meant, and sometimes it is wrong",
        ),
        Option(
            "SQL you write and run yourself",
            "complete control, and nothing stops two machines being different",
        ),
        Option(
            "Rebuild it from nothing each time",
            "honest while there is no real data. It stops being an option on launch day",
        ),
    ),
)

DB_ACCESS = Question(
    key="db-access",
    question="How does your code talk to the database?",
    subtitle="decides how much SQL you write and how much magic sits in between",
    concept="an ORM maps rows to objects, so you write your language instead of SQL",
    matters="This is in every file that touches data, so changing it later is a rewrite.",
    means=(
        "An ORM is faster to write and hides the query that is actually run.",
        "Plain SQL is more to write and there is nothing between you and the mistake.",
    ),
    options=(
        Option(
            "A full ORM",
            "objects and relations, migrations included. Slow queries hide until they hurt",
        ),
        Option(
            "A query builder",
            "SQL in your language, no hidden loading. You still design the queries",
        ),
        Option(
            "Plain SQL in one place",
            "exactly what runs, nothing more. Every query is yours to write and test",
        ),
        Option(
            "Whatever the framework ships with",
            "no decision to defend, and no escape when it is the wrong tool",
        ),
    ),
)

DB_TESTDATA = Question(
    key="db-testdata",
    question="What is in the database when you or a test opens it fresh?",
    subtitle="decides whether tests are trustworthy and whether a demo is repeatable",
    concept="seed data: a known starting state, written down rather than typed in",
    matters="Tests that share one database pass alone and fail together, or the reverse.",
    means=(
        "Empty is a real answer, and it means every test builds what it needs.",
        "A seed file makes a demo repeatable, which matters the week you present it.",
    ),
    options=(
        Option(
            "Empty, and each test makes what it needs",
            "slowest to write and the only version that cannot leak between tests",
        ),
        Option(
            "A seed file, committed",
            "one command to a working demo. It goes stale unless something checks it",
        ),
        Option(
            "A copy of real data, anonymised",
            "realistic, and anonymising it properly is a project of its own",
        ),
        Option(
            "Whatever is in there",
            "no work now. Nothing is reproducible, including the bug you are chasing",
        ),
    ),
)

# --------------------------------------------------------------------------
# getting it out of your machine
# --------------------------------------------------------------------------

DEPLOY_PARTS = Question(
    key="deploy-parts",
    question="How many separate things have to be running for this to work?",
    subtitle="decides everything about deployment, and it is usually undercounted",
    concept="the deployable unit: what you start, and what has to be started with it",
    matters="Each additional running piece is one more thing that can be down alone.",
    means=(
        "One process is one thing to start, one log to read, one thing to restart.",
        "Count the database, the queue and the scheduled job. They are pieces too.",
    ),
    options=(
        Option(
            "One process, and that is all",
            "the simplest thing that works. Everything scales together or not at all",
        ),
        Option(
            "An app and a database",
            "two pieces, one of which holds the data. The common shape, and enough",
            gives=("has-db",),
        ),
        Option(
            "An app, a database, and background work",
            "the queue is a third thing to run and the first to be forgotten",
            gives=("has-db", "jobs"),
        ),
        Option(
            "Several services that talk to each other",
            "independent pieces, and now you own the network between them",
            gives=("multi-service",),
        ),
    ),
)

DEPLOY_ORCHESTRATION = Question(
    key="deploy-orchestration",
    question="What starts those pieces, in order, and restarts them when they die?",
    subtitle="the orchestration question, and it is a real fork in the project",
    concept="orchestration: something whose job is keeping the right things running",
    matters="Picking Kubernetes for two containers costs weeks and buys nothing.",
    means=(
        "Something has to start them in order and notice when one is gone.",
        "The honest range is from a one-line service file to a cluster you operate.",
    ),
    options=(
        Option(
            "You start it by hand",
            "nothing to learn. Nothing restarts it when the machine reboots",
        ),
        Option(
            "The operating system's own service manager",
            "systemd or a scheduled task. Free, dull, and it survives a reboot",
        ),
        Option(
            "Docker Compose, one file",
            "the pieces and their order in one readable file. One machine, no failover",
            needs=("container",),
            gives=("container", "compose"),
        ),
        Option(
            "A platform that runs containers for you",
            "you hand it an image. It handles restarts, and you live in their model",
            needs=("hosting", "container"),
            gives=("container",),
        ),
        Option(
            "Kubernetes",
            "the answer at a scale you are not at. Real power, and a full-time job",
            needs=("container", "hosting", "always-on"),
            gives=("container", "kubernetes"),
        ),
    ),
)

DEPLOY_ROLLBACK = Question(
    key="deploy-rollback",
    question="A change goes out and it is wrong. What do you do in the next five minutes?",
    subtitle="decides how frightening it is to release, and therefore how often you do",
    concept="rollback: getting back to the last version that worked, on purpose",
    matters="Without an answer, the fix for a bad release is a panicked second release.",
    means=(
        "Every project has an answer here. Most of them are 'push another change and hope'.",
        "The database is the hard half: code goes back, data does not.",
    ),
    options=(
        Option(
            "Put the previous version back",
            "the old build is kept and one command returns to it. Fastest and safest",
        ),
        Option(
            "Fix forward and release again",
            "nothing to build now, and your worst outage is as long as your slowest fix",
        ),
        Option(
            "Turn the feature off without releasing",
            "a switch in the running copy. Most control, and every switch is a branch to keep",
        ),
        Option(
            "Restore from the last backup",
            "the honest answer for a small project. Everything since the backup is gone",
        ),
    ),
)

# --------------------------------------------------------------------------
# configuration, which is where the secret ends up
# --------------------------------------------------------------------------

CONFIG_WHERE = Question(
    key="config-where",
    question="Where does the running copy read its settings from?",
    subtitle="decides how a machine differs from yours without the code differing",
    concept="configuration: the values that change per machine while the code does not",
    matters="A setting in the code is a setting somebody edits in production one day.",
    means=(
        "Same code, different database address, different keys, different machine.",
        "The moment those live in the code, one of them is a key in your repository.",
    ),
    options=(
        Option(
            "Environment variables",
            "the standard answer. Nothing to parse, and anyone on the box can read them",
        ),
        Option(
            "A file that is never committed",
            "readable and reviewable, and it is committed by accident sooner or later",
        ),
        Option(
            "A settings file per environment, secrets kept out",
            "the whole shape in one reviewable place, and two files to keep in step",
        ),
        Option(
            "Your host's configuration store",
            "encrypted and audited, and one more thing tying you to that host",
            needs=("hosting",),
        ),
    ),
)

CONFIG_MISSING = Question(
    key="config-missing",
    question="What happens when a setting is missing or wrong?",
    subtitle="decides whether you find out at start-up or from a user",
    concept="failing fast: refusing to start rather than running half configured",
    matters="A missing key found at request time is an outage found by a customer.",
    means=(
        "Checked at start-up, a missing key is a clear message before anyone is served.",
        "Checked when first used, it is an error at midnight in one code path.",
    ),
    options=(
        Option(
            "Refuse to start, and say which one",
            "the loudest and the kindest. One list of what is missing, at boot",
        ),
        Option(
            "Start with sensible defaults, and log loudly",
            "it keeps running, and a default in production is its own kind of outage",
        ),
        Option(
            "Fail when the setting is first used",
            "nothing to write. The failure arrives far from the cause",
        ),
    ),
)

# --------------------------------------------------------------------------
# the smaller topics, still asked properly
# --------------------------------------------------------------------------

API_SHAPE = Question(
    key="api-shape",
    question="What shape is the interface between the screens and the server?",
    subtitle="decides what every later endpoint looks like",
    concept="an API contract: what a caller may ask for and what comes back",
    matters="Changing this later breaks every caller you have by then, including yours.",
    means=(
        "The shape decides how a change reaches callers without breaking them.",
        "There is no wrong answer here, only one you have to keep.",
    ),
    options=(
        Option(
            "REST, one address per thing",
            "the boring answer everyone can read. Chatty when a screen needs six things",
        ),
        Option(
            "One endpoint per action",
            "each is exactly what a screen needs. The list grows with the screens",
        ),
        Option(
            "GraphQL",
            "the caller asks for what it needs. A server that is harder to make fast",
        ),
        Option(
            "The framework's own server functions",
            "least to write and no contract to keep. The client and server are married",
        ),
    ),
)

API_ERRORS = Question(
    key="api-errors",
    question="What does a caller get back when something goes wrong?",
    subtitle="decides whether the screens can say anything useful to a person",
    concept="an error contract: failures with a shape, rather than whatever fell out",
    matters="Without one, every screen invents its own guess at what went wrong.",
    means=(
        "A failure a caller can read is a failure a screen can explain.",
        "The other half is what you never send back: stack traces and internals.",
    ),
    options=(
        Option(
            "A status code and a message meant for a person",
            "enough for most projects and readable in a log",
        ),
        Option(
            "A status code, a machine-readable code, and a message",
            "screens can branch on the code. One more thing to keep consistent",
        ),
        Option(
            "Whatever the framework produces",
            "nothing to write, and internals leak in the wording",
        ),
    ),
)

JOBS_WHEN = Question(
    key="jobs-when",
    question="What work happens without somebody waiting for it?",
    subtitle="decides whether a slow thing blocks a screen",
    concept="background work: started now, finished later, nobody watching",
    matters="Work done inside a request makes the user wait for something they did not ask for.",
    means=(
        "Sending mail, resizing an image, a nightly tidy-up. None of it needs a person.",
        "Doing it in the request is simplest, until the request takes nine seconds.",
    ),
    options=(
        Option(
            "Nothing, it all happens in the request",
            "no machinery. The user waits for whatever you added",
        ),
        Option(
            "A queue and a worker",
            "the standard answer. A second thing to run and to watch",
            gives=("jobs",),
        ),
        Option(
            "A scheduled task on a timer",
            "enough for tidying up. It is not enough for anything a user is waiting on",
            gives=("jobs",),
        ),
        Option(
            "Your host's own background jobs",
            "nothing to run yourself, and it works only where they run",
            needs=("hosting",),
            gives=("jobs",),
        ),
    ),
)

UPLOAD_WHERE = Question(
    key="upload-where",
    question="Where do the files people upload actually go?",
    subtitle="decides your backups, your bill, and one of the classic security holes",
    concept="object storage: files kept somewhere that is not your database or your disk",
    matters="Files on the app's own disk vanish the first time it is redeployed.",
    means=(
        "The disk your code runs on is usually temporary, and files on it are too.",
        "The second half is what you accept: type, size, and what you do with the name.",
    ),
    options=(
        Option(
            "A folder on this machine",
            "simplest, and it is gone on the next deploy unless the disk is kept",
        ),
        Option(
            "Object storage, S3 or the equivalent",
            "the usual answer. Cheap, durable, and one more account to configure",
            needs=("hosting",),
        ),
        Option(
            "Inside the database",
            "one thing to back up and one thing to restore. It makes the database big and slow",
        ),
        Option(
            "Somewhere else entirely, by link",
            "no storage to own. You depend on wherever the file lives",
        ),
    ),
)

PAY_WHO = Question(
    key="pay-who",
    question="Who holds the card details?",
    subtitle="decides the compliance you inherit, and this one is not negotiable",
    concept="handling payments means the card number is never yours to store",
    matters="Storing card numbers yourself is a compliance obligation you do not want.",
    means=(
        "Every reasonable answer keeps the number away from your servers.",
        "What differs is how much of the checkout you draw yourself.",
    ),
    options=(
        Option(
            "Their hosted checkout page",
            "you send people there and they come back paid. Least work and least control",
            needs=("hosting",),
        ),
        Option(
            "Their fields, embedded in your page",
            "your design, their iframe holding the number. The usual answer",
            needs=("hosting",),
        ),
        Option(
            "A payment link per item",
            "no integration at all. Fine for a handful of things, painful for a catalogue",
        ),
        Option(
            "An invoice you send by hand",
            "no code. Right more often than people expect, early on",
        ),
    ),
)


@dataclass(frozen=True)
class Topic:
    """A subject, the words that mean it, and what it owes the user."""

    key: str
    title: str
    words: tuple[str, ...]
    questions: tuple[Question, ...]


TOPICS: tuple[Topic, ...] = (
    Topic(
        key="database",
        title="the database",
        words=(
            "database", "db", "schema", "table", "migration", "query", "sql",
            "store", "stored", "storing", "persist", "record", "model", "orm",
            "repository layer", "data layer", "supabase", "postgres", "sqlite",
            "mongo", "mysql",
        ),
        questions=(DB_CHOICE, DB_WHERE, DB_SHAPE, DB_ACCESS, DB_TESTDATA),
    ),
    Topic(
        key="deploy",
        title="getting it out of your machine",
        words=(
            "deploy", "deployment", "release", "ship", "publish", "production",
            "hosting", "host", "server setup", "docker", "container", "compose",
            "kubernetes", "orchestrat", "infrastructure", "provision", "ci/cd",
            "pipeline",
        ),
        questions=(DEPLOY_PARTS, DEPLOY_ORCHESTRATION, DEPLOY_ROLLBACK, ff.RELEASE, ff.FAILURE),
    ),
    Topic(
        key="config",
        title="configuration and secrets",
        words=(
            "config", "configuration", "settings", "environment variable", "env var",
            ".env", "secret", "api key", "credential", "connection string",
        ),
        questions=(CONFIG_WHERE, CONFIG_MISSING, ff.SECRETS),
    ),
    Topic(
        key="auth",
        title="who someone is, and what they may do",
        words=(
            "auth", "authentication", "authorisation", "authorization", "login",
            "log in", "sign in", "sign up", "signup", "session", "password",
            "token", "jwt", "oauth", "permission", "role", "account",
        ),
        questions=(ff.IDENTITY, ff.PERMISSIONS),
    ),
    Topic(
        key="api",
        title="the interface between the parts",
        words=("api", "endpoint", "route", "handler", "controller", "rest", "graphql", "contract"),
        questions=(API_SHAPE, API_ERRORS),
    ),
    Topic(
        key="jobs",
        title="work nobody is waiting for",
        words=("background", "queue", "worker", "cron", "scheduled", "job", "async task", "celery"),
        questions=(JOBS_WHEN,),
    ),
    Topic(
        key="uploads",
        title="files people give you",
        words=("upload", "file storage", "attachment", "image upload", "avatar", "s3", "bucket"),
        questions=(UPLOAD_WHERE,),
    ),
    Topic(
        key="payments",
        title="taking money",
        words=("payment", "billing", "checkout", "stripe", "subscription", "invoice", "card"),
        questions=(PAY_WHO,),
    ),
)

BY_KEY = {topic.key: topic for topic in TOPICS}

ALL_QUESTIONS: tuple[Question, ...] = tuple(
    dict.fromkeys(question for topic in TOPICS for question in topic.questions)
)


def _words(text: str) -> str:
    return f" {re.sub(r'[^a-z0-9]+', ' ', (text or '').lower())} "


def topics_in(text: str) -> list[Topic]:
    """Which subjects a piece of work touches, read from how it is written.

    Matched on whole words. A substring match reads "storing" out of "restoring"
    and, worse, finds "db" inside a hundred ordinary words, so a step about
    wording would demand five database decisions.
    """
    haystack = _words(text)
    found = []
    for topic in TOPICS:
        if any(f" {word} " in haystack for word in topic.words):
            found.append(topic)
    return found


def owed(forge_dir: Path, text: str) -> list[Question]:
    """The questions this work owes the user, not yet recorded, in order.

    Asked once per project rather than once per step. "Which database" is a
    project question that some step is merely the first to need, and asking it
    again at step nine is the failure this product exists to prevent, performed
    by the product.
    """
    wanted: list[Question] = []
    for topic in topics_in(text):
        for question in topic.questions:
            if question not in wanted:
                wanted.append(question)

    if not wanted:
        return []

    done = ff.answered_from(forge_dir, tuple(wanted))
    known = ff.facts(forge_dir)
    out = []
    for question in wanted:
        if question.key in done:
            continue
        # A question the project has already ruled out is not owed. A single
        # user is not asked how one person is kept from another's data.
        if known & set(question.skip_when):
            continue
        out.append(question)
    return out


def next_owed(forge_dir: Path, text: str) -> Question | None:
    pending = owed(forge_dir, text)
    return pending[0] if pending else None
