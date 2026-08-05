"""Forge Mentor — generating prompts.md.

The programme asks every project to keep a log of the prompts behind the work.
Most projects write it by hand at the end, which makes it a reconstruction:
whatever the author remembers, tidied.

Forge does not have to. Every question it asked and every answer it was given
is already on disk as a decision record, written at the moment it happened. So
this assembles the log from those, and the result is a record rather than a
recollection — including the questions whose answers turned out to be wrong,
which are the ones a hand-written version quietly loses.

**What goes in.** The question Forge put to the user, the options it offered,
what was chosen, and the reasoning in the user's own words. Also which model
handled the step, because decision 002 routes different work to different
models and a log that hides that misrepresents how the project was built.

**What stays out.** File contents, tool output, and anything from outside the
conversation. A prompt log is about what was asked, not about everything that
travelled — and the repository is public (decision 007), so the smaller this
file's blast radius the better.

**Anything that looks like a credential is redacted.** The reasoning is the
user's own free text, typed into a terminal, and people paste keys into free
text — a connection string with a password in it is the ordinary way someone
explains why they chose a database. This file lands in the project root of a
repository that may be public, so it is the last place that should carry one
through verbatim. The redaction is deliberately blunt: it would rather blank
something harmless than publish a live key, and it says when it has acted.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import forge_explain as fe
import forge_skills as sk
import forge_state as fs

PROMPTS_FILE = "prompts.md"

REDACTED = "[redacted by Forge]"

# Shapes that carry a live secret often enough to be worth blanking on sight.
# Tuned to over-redact: a blanked sentence is an inconvenience, a published key
# is an incident.
_SECRET_SHAPES: tuple[re.Pattern[str], ...] = (
    # A URL with credentials in it — the usual way a database choice gets explained.
    re.compile(r"\b[a-z+]{2,12}://[^\s:/@]+:[^\s/@]+@\S+", re.IGNORECASE),
    # Provider key prefixes.
    re.compile(r"\b(?:sk|pk|rk|api|ghp|gho|ghs|ghu|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    # `SOMETHING_KEY=value`, `password: value`, and friends.
    re.compile(
        r"\b(?:[A-Za-z0-9_]*(?:secret|token|password|passwd|api[_-]?key|access[_-]?key)"
        r"[A-Za-z0-9_]*)\s*[:=]\s*\S{6,}",
        re.IGNORECASE,
    ),
)


def redact(text: str) -> tuple[str, int]:
    """Blank anything credential-shaped. Returns the text and how much was hit."""
    if not text:
        return text, 0
    hits = 0
    for pattern in _SECRET_SHAPES:
        text, count = pattern.subn(REDACTED, text)
        hits += count
    return text, hits

# Which model handled which kind of step, from decision 002. Stated once here
# rather than guessed per entry, and taken from the same table the subagents
# and the server use so a change reaches all three (decision 029).
_STAGE_MODEL = {
    "the question": sk.AGENTS_BY_NAME["planner"].model,
    "the record": sk.AGENTS_BY_NAME["structurer"].model,
    "the code": sk.AGENTS_BY_NAME["builder"].model,
    "the review fixes": sk.AGENTS_BY_NAME["review-fixer"].model,
}


def render(entries: list[fe.Explained], project: str = "") -> str:
    """The log."""
    lines = [
        fs.render_header(
            {
                "type": "prompts",
                "project": project or "this project",
                "entries": str(len(entries)),
                "generated": date.today().isoformat(),
            }
        ).rstrip("\n"),
        "",
        f"# Prompts — {project or 'this project'}",
        "",
        "Generated from the decision records, not written afterwards. Each entry is what "
        "Forge actually asked and what was actually answered, recorded at the time.",
        "",
        "Anything credential-shaped is blanked before it is written here — this file sits "
        "in the project root and the repository may be public. The full text is always in "
        "`.forge/decisions/`.",
        "",
        "## Which model did what",
        "",
        "Decision 002 sends different work to different models, so a single-model log would "
        "misrepresent how this was built.",
        "",
    ]
    lines += [f"| {what} | `{model}` |" for what, model in _STAGE_MODEL.items()]
    lines.insert(len(lines) - len(_STAGE_MODEL), "|---|---|")
    lines.insert(len(lines) - len(_STAGE_MODEL) - 1, "| step | model |")
    lines += ["", "---", ""]

    if not entries:
        lines += ["No decisions recorded yet, so there are no prompts to log.", ""]
        return "\n".join(lines)

    redactions = 0
    for entry in entries:
        question, hit = redact(entry.question)
        redactions += hit
        lines += [
            f"## {entry.id:03d} · {question}",
            "",
            "**Asked:**",
            "",
            f"> {question}",
            "",
        ]

        if entry.options:
            lines += ["**Options put to the user:**", ""]
            for option in entry.options:
                safe, hit = redact(option)
                redactions += hit
                lines.append(f"- {safe}")
            lines.append("")

        if entry.choice:
            who = "Forge (recorded, not chosen by the user)" if entry.was_automatic else "the user"
            choice, hit = redact(entry.choice)
            redactions += hit
            lines += [f"**Answered by {who}:** {choice}", ""]

        if entry.why:
            why, hit = redact(entry.why.strip())
            redactions += hit
            lines += ["**Reasoning given:**", "", f"> {why}", ""]

        lines += ["---", ""]

    if redactions:
        # Said out loud. A silently doctored record would leave the reader
        # trusting a log that is not the whole account, which is worse than a
        # log that is upfront about what it withheld and where to find it.
        lines += [
            f"_{redactions} value(s) looked like credentials and were blanked. "
            "If one was harmless, the original is in its decision record._",
            "",
        ]

    return "\n".join(lines)


def write(project_root: Path, forge_dir: Path, name: str = "") -> Path:
    """Write `prompts.md` at the top of the repository, where a marker looks.

    Not inside `.forge/`. The programme asks for it as a deliverable of the
    project, so it goes where a reader expects a project file — the decision
    records it is built from stay where they are.
    """
    path = project_root / PROMPTS_FILE
    entries = fe.collect(forge_dir)
    path.write_text(render(entries, name or project_root.name), encoding="utf-8")
    return path


def report(project_root: Path, forge_dir: Path, name: str = "") -> dict[str, object]:
    path = write(project_root, forge_dir, name)
    entries = fe.collect(forge_dir)
    return {
        "file": str(path),
        "entries": len(entries),
        "chosen_by_you": sum(1 for e in entries if not e.was_automatic),
    }
