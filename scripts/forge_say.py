"""Forge Mentor, the shape of a message that leaves through a hook.

**Why this is separate from `forge_ui`.** A hook does not print to a terminal.
It returns a string in JSON, which Claude Code then renders itself, so nothing
here can rely on colour surviving and nothing here may cost a dependency: these
run on a machine where the engine may not be installed at all.

What it can rely on is the frame. Box-drawing characters are plain text, they
survive any renderer that uses a monospace font, and decision 035 is explicit
that everything Forge says goes inside one. A refusal arriving as bare prose is
indistinguishable from the client's own error text, which is exactly what it
looked like: "UserPromptSubmit operation blocked by hook" followed by four
paragraphs with nothing marking them as Forge speaking.

**Every message here carries its way out.** A block that only says no is a
dead end; the user is left to guess whether they broke something. So the shape
is fixed: what stopped, why in one line, and then the moves that end it. If a
message cannot name a way out, it is not ready to be shown.
"""

from __future__ import annotations

import shutil
import textwrap

MARK = "⚒"
BLOCKED = "⛔"
ACTION = "→"


def _width() -> int:
    """Sized to the terminal, clamped so a long line stays readable."""
    try:
        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
    except (OSError, ValueError):
        columns = 80
    return max(56, min(columns - 4, 92))


def _wrap(text: str, width: int) -> list[str]:
    out: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            out.append("")
            continue
        out.extend(textwrap.wrap(paragraph, width=width) or [""])
    return out


def framed(title: str, body: str, ways_out: list[str] | None = None) -> str:
    """A hook message in Forge's own shape, with its exits.

    `ways_out` is not decoration and not optional in practice. Every refusal
    Forge makes has at least one: answer the question, run the command, say
    "anyway". A user who cannot see the exit reads the block as a fault.
    """
    width = _width()
    inner = width - 2
    lines = [f"┌─ {BLOCKED} {title} " + "─" * max(0, inner - len(title) - 5) + "┐"]
    lines.append("│" + " " * inner + "│")

    for line in _wrap(body, inner - 4):
        lines.append("│  " + line.ljust(inner - 4) + "  │")

    if ways_out:
        lines.append("│" + " " * inner + "│")
        for way in ways_out:
            wrapped = _wrap(way, inner - 8) or [""]
            lines.append("│  " + f"{ACTION} {wrapped[0]}".ljust(inner - 4) + "  │")
            for extra in wrapped[1:]:
                lines.append("│  " + f"  {extra}".ljust(inner - 4) + "  │")

    lines.append("│" + " " * inner + "│")
    lines.append("└" + "─" * inner + "┘")
    return "\n".join(lines)
