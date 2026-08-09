"""Forge Mentor — Code Explained.

The document at the end of the loop. Not API documentation and not a summary of
what the code does — the code already says that, and a generated restatement of
it is the least useful page in any repository.

This answers the question the user will actually be asked: **why is it like
this?** Every load-bearing choice, what else was considered, what was given up,
and who decided. It is assembled from the decision records rather than written,
because the records are the only account of the reasoning that existed at the
time — a summary written afterwards is a reconstruction, and reconstructions
quietly become tidier than the truth.

Ordered by decision, not by file. A reader following the argument wants the
order the project was thought through in, which is rarely the order the
directory lists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import forge_state as fs

EXPLAINED_FILE = "code-explained.md"

# Pulled out of a record body. Written by `record_answer`, so the shape is
# known — but parsed forgivingly, because the Phase 1 records were hand-written
# before the writer existed and they have to keep working.
_HEADING = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_OPTIONS = re.compile(r"\*\*Options considered\*\*\s*(.+?)(?=\n\s*\n|\Z)", re.DOTALL)
_DECIDED = re.compile(r"\*\*Decided:\*\*\s*(.+?)(?:\s*·|$)", re.MULTILINE)
_WHY = re.compile(r"##\s+Why\s*\n+(.+?)(?=\n##\s|\Z)", re.DOTALL)


@dataclass
class Explained:
    """One decision, as a reader meets it."""

    id: int
    question: str
    choice: str
    options: list[str]
    why: str
    decided_by: str

    @property
    def was_automatic(self) -> bool:
        """Did Forge settle this one itself?

        Kept visible on purpose. Decision 030 accepts that Auto produces
        records nobody chose, and the mitigation was that the two are never
        confused when read back — which only works if this says so.
        """
        return self.decided_by.strip().lower() not in {"user", ""}


def _first(pattern: re.Pattern[str], text: str, default: str = "") -> str:
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def read(decision: fs.Decision) -> Explained:
    """Turn a stored record back into the argument it holds.

    Reads the record already in hand rather than reopening it by name. The
    first draft rebuilt the filename from the question, which broke on the
    Phase 1 records — those were named by hand and do not match the slug the
    writer would generate.
    """
    body = decision.body

    options = [
        re.sub(r"^[-*]\s*", "", line).strip()
        for line in _first(_OPTIONS, body).splitlines()
        if line.strip().startswith(("-", "*"))
    ]

    return Explained(
        id=decision.id,
        question=decision.question,
        choice=_first(_DECIDED, body) or _first(_HEADING, body),
        options=options,
        why=_first(_WHY, body),
        decided_by=decision.decided_by,
    )


def collect(forge_dir: Path) -> list[Explained]:
    """Every decided record, in the order it was decided.

    Walks the folder rather than calling `fs.list_decisions`, because the two
    want opposite things from a damaged file. The state layer stops and names
    it, which is right when the file is about to gate a write. Here it would
    cost the reader every other explanation in the document to report one bad
    record, so this skips it — `check_history` is what reports the damage.
    """
    folder = forge_dir / fs.DECISIONS
    if not folder.is_dir():
        return []

    out: list[Explained] = []
    for path in sorted(folder.glob("*.md")):
        try:
            decision = fs.Decision.read(path)
        except (fs.StateError, OSError):
            continue
        # Compared loosely on purpose. The Phase 1 records were hand-written,
        # and one reading "Decided" or carrying a trailing space would have
        # been skipped silently — taking its choice, its rejected options and
        # its reasoning out of the document with no sign anything was missing.
        if decision.status.strip().lower() != fs.STATUS_DECIDED:
            continue  # an open question is not yet part of the account
        out.append(read(decision))
    return sorted(out, key=lambda entry: entry.id)


def render(entries: list[Explained], project: str = "") -> str:
    """The document."""
    chosen_by_user = sum(1 for e in entries if not e.was_automatic)

    lines = [
        fs.render_header(
            {
                "type": "code-explained",
                "decisions": str(len(entries)),
                "chosen_by_you": str(chosen_by_user),
                "updated": date.today().isoformat(),
            }
        ).rstrip("\n"),
        "",
        f"# Why {project or 'this project'} is built the way it is",
        "",
    ]

    if not entries:
        lines += [
            "No decisions have been recorded yet, so there is nothing to explain.",
            "",
            "This file fills itself in as you answer questions — it is assembled from",
            "your decision records, never written separately.",
            "",
        ]
        return "\n".join(lines)

    lines += [
        f"{len(entries)} decisions shape this project. "
        f"You made {chosen_by_user} of them"
        + (
            f"; Forge settled the other {len(entries) - chosen_by_user} and recorded them.\n"
            if chosen_by_user != len(entries)
            else ".\n"
        ),
        "Read in the order they were decided, because each one was made knowing the",
        "ones above it — which is not the order the files are listed in.",
        "",
        "---",
        "",
    ]

    for entry in entries:
        lines += [f"## {entry.id:03d} · {entry.question}", ""]

        if entry.choice:
            mark = "" if not entry.was_automatic else "  *(settled by Forge)*"
            lines += [f"**{entry.choice}**{mark}", ""]

        if entry.options and entry.choice:
            # Only when the choice was actually identified. With no choice to
            # compare against, `_is_chosen` matches nothing and every option
            # would be listed as rejected — telling the reader the project
            # turned down the thing it actually built.
            rejected = rejected_options(entry.options, entry.choice)
            if rejected:
                lines += ["Also considered: " + "; ".join(rejected), ""]
        elif entry.options:
            lines += [
                "Options put forward: " + "; ".join(entry.options),
                "",
                "_The record does not say which of these was taken._",
                "",
            ]

        if entry.why:
            lines += [entry.why.strip(), ""]

        lines += [
            f"Full record: [`{entry.id:03d}`](decisions/)",
            "",
        ]

    return "\n".join(lines)


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def rejected_options(options: list[str], choice: str) -> list[str]:
    """The options that were not taken.

    Matching is done across the whole set rather than one option at a time,
    because what identifies a choice is the word that tells the options apart
    — not how much of it the choice happens to repeat. "use hosted PostgreSQL"
    and "use hosted MySQL" share two words in three, so a plain overlap ratio
    called both of them chosen and dropped the rejected one from the document
    entirely.

    The comparison stays loose because the user answers in their own words,
    which is the point of asking that way.
    """
    if not choice or not options:
        return []

    shared: set[str] = set()
    for index, option in enumerate(options):
        for other in options[index + 1 :]:
            shared |= _words(option) & _words(other)

    chosen_words = _words(choice)
    out: list[str] = []
    for option in options:
        distinguishing = _words(option) - shared
        if distinguishing:
            taken = bool(distinguishing & chosen_words)
        else:
            overlap = _words(option) & chosen_words
            taken = bool(_words(option)) and len(overlap) / len(_words(option)) > 0.6
        if not taken:
            out.append(option)
    return out


def _is_chosen(option: str, choice: str) -> bool:
    """Was this single option the one taken? Kept for callers with no set."""
    return bool(choice) and option not in rejected_options([option], choice)

def write(forge_dir: Path, project: str = "") -> Path:
    """Assemble the document and put it where it is committed with the code."""
    path = forge_dir / EXPLAINED_FILE
    forge_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(render(collect(forge_dir), project), encoding="utf-8")
    return path


def report(forge_dir: Path, project: str = "") -> dict[str, object]:
    entries = collect(forge_dir)
    path = write(forge_dir, project)
    return {
        "file": str(path),
        "decisions": len(entries),
        "chosen_by_you": sum(1 for e in entries if not e.was_automatic),
        "settled_by_forge": sum(1 for e in entries if e.was_automatic),
    }
