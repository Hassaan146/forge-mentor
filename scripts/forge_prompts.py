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
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import forge_explain as fe
import forge_skills as sk
import forge_state as fs

PROMPTS_FILE = "prompts.md"

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

    for entry in entries:
        lines += [
            f"## {entry.id:03d} · {entry.question}",
            "",
            "**Asked:**",
            "",
            f"> {entry.question}",
            "",
        ]

        if entry.options:
            lines += ["**Options put to the user:**", ""]
            lines += [f"- {option}" for option in entry.options]
            lines.append("")

        if entry.choice:
            who = "Forge (recorded, not chosen by the user)" if entry.was_automatic else "the user"
            lines += [f"**Answered by {who}:** {entry.choice}", ""]

        if entry.why:
            lines += ["**Reasoning given:**", "", f"> {entry.why.strip()}", ""]

        lines += ["---", ""]

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
