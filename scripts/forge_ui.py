"""Forge Mentor — shared visual identity.

Every piece of Forge output goes through here so the plugin looks and feels
distinct from plain Claude Code (design rules R5, R9, R10).

Rules this module enforces:
  R9  restraint — four symbols only: the mark, blocked, recorded, recommended
  R9  colour and weight carry meaning; colour is never the only signal
  R10 questions are compact and boxed, never prose

Colour degrades safely: if the terminal cannot do colour, or NO_COLOR is set,
every code becomes an empty string and the symbols still carry the meaning.
"""

from __future__ import annotations

import os
import sys

# --------------------------------------------------------------------------
# making the symbols printable at all
# --------------------------------------------------------------------------


def _make_output_utf8_safe() -> None:
    """Stop a Windows console from crashing on the four symbols.

    On Windows, Python writes to the console in the system code page, which is
    usually cp1252 — and none of ⚒ ⛔ ✅ ★ exist in it. Printing a banner
    raised UnicodeEncodeError and took the whole hook down with it, which for
    the governor would mean a blocked write never explaining itself.

    UTF-8 is asked for first. Where it cannot be had, `errors="replace"` makes
    an unprintable symbol come out as a placeholder instead of an exception —
    degraded, but rule R9 already requires that colour and symbols are never
    the only signal, so the words still carry the meaning.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            try:
                reconfigure(errors="replace")
            except (OSError, ValueError):
                pass


_make_output_utf8_safe()


# --------------------------------------------------------------------------
# colour support
# --------------------------------------------------------------------------


def _colour_enabled() -> bool:
    """True when it is safe to emit ANSI colour."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORGE_NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    # CI systems usually render colour fine; honour an explicit opt-in too.
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


_ON = _colour_enabled()


def _c(code: str) -> str:
    return code if _ON else ""


# Six meanings, one colour each. See decision F1 / rule R9.
AMBER = _c("\033[38;5;215m")  # Forge itself
CYAN = _c("\033[38;5;80m")  # teaching, file paths
GREEN = _c("\033[38;5;114m")  # recommended, recorded, passed
RED = _c("\033[38;5;203m")  # blocked, override, findings
PURPLE = _c("\033[38;5;177m")  # which AI is working
DIM = _c("\033[38;5;245m")  # progress, quiet detail
FAINT = _c("\033[38;5;240m")  # borders

BOLD = _c("\033[1m")
RESET = _c("\033[0m")

# The only four symbols. Restraint is deliberate (R9).
MARK = "⚒"
BLOCKED = "⛔"
RECORDED = "✅"
STAR = "★"

WIDTH = 62


# --------------------------------------------------------------------------
# building blocks
# --------------------------------------------------------------------------


def banner(project: str | None = None, version: str = "0.1.0") -> str:
    """The start-up banner. Printed once when a session begins."""
    lines = [
        "",
        f"  {AMBER}{BOLD}   ▄▄▄▄▄  ▄▄▄▄  ▄▄▄▄▄   ▄▄▄▄  ▄▄▄▄▄{RESET}",
        f"  {AMBER}{BOLD}   █▄▄    █  █  █▄▄▄█  █  ▄▄  █▄▄{RESET}",
        f"  {AMBER}{BOLD}   █      █▄▄█  █   █  █▄▄█▌ █▄▄▄{RESET}   {FAINT}Mentor v{version}{RESET}",
        "",
        f"  {FAINT}{'─' * WIDTH}{RESET}",
        f"  {BOLD}decide-then-code{RESET}  {FAINT}·{RESET}  {DIM}no code before you decide{RESET}",
        f"  {FAINT}{'─' * WIDTH}{RESET}",
    ]
    if project:
        lines.append(f"  {GREEN}{RECORDED} active in this project{RESET}   {DIM}{project}{RESET}")
    lines.append("")
    return "\n".join(lines)


def question_box(title: str, subtitle: str = "", number: int | None = None) -> str:
    """A framed decision question. Compact by rule R10 — never prose.

    Border width is computed from the *visible* text so the top and bottom
    rails always line up, whatever the heading says.
    """
    inner = WIDTH - 2
    label = f"{MARK} FORGE" + (f" · DECISION {number:03d}" if number else "")
    # visible top-rail prefix is "┌─ " + label + " "
    used = 3 + len(label) + 1
    fill = max(0, inner - used + 1)

    tag = f" {FAINT}·{RESET} {AMBER}DECISION {number:03d}{RESET}" if number else ""
    out = [
        "",
        f"  {FAINT}┌─{RESET} {AMBER}{BOLD}{MARK} FORGE{RESET}{tag} {FAINT}{'─' * fill}┐{RESET}",
        f"  {FAINT}│{RESET}  {BOLD}{title}{RESET}",
    ]
    if subtitle:
        out.append(f"  {FAINT}│{RESET}  {DIM}{subtitle}{RESET}")
    out.append(f"  {FAINT}└{'─' * inner}┘{RESET}")
    return "\n".join(out)


def options(items: list[tuple[str, str, str]]) -> str:
    """Options as a tight list: (letter, label, one-line consequence)."""
    out = ["", f"  {AMBER}{BOLD}Options{RESET}"]
    for letter, label, note in items:
        out.append(
            f"    {AMBER}{BOLD}{letter}{RESET}  {label:<28} {DIM}{note}{RESET}"
        )
    return "\n".join(out)


def recommendation(choice: str, reason: str, against: str = "") -> str:
    out = ["", f"  {GREEN}{STAR} Recommended{RESET}  {BOLD}{choice}{RESET} {DIM}— {reason}{RESET}"]
    if against:
        out.append(f"  {DIM}Against it: {against}{RESET}")
    return "\n".join(out)


def progress(done: int, total: int, label: str = "") -> str:
    """Progress bar. Required on every question by rule R4."""
    slots = 12
    filled = 0 if total <= 0 else min(slots, round(slots * done / total))
    bar = f"{GREEN}{'█' * filled}{FAINT}{'░' * (slots - filled)}{RESET}"
    tail = f" {DIM}· {label}{RESET}" if label else ""
    return f"\n  {DIM}[{RESET}{bar}{DIM}]  {done} of ~{total}{RESET}{tail}"


def prompt(text: str = "Your call") -> str:
    return f"\n  {AMBER}{BOLD}{text}{RESET} {FAINT}›{RESET} "


def blocked(what: str, why: str, ways_out: list[str]) -> str:
    """The governor stopping a write. Red plus the ⛔ symbol — never colour alone."""
    out = [
        "",
        f"  {RED}{BOLD}{BLOCKED}  FORGE STOPPED THIS{RESET}",
        "",
        f"     {BOLD}{why}{RESET} {AMBER}{what}{RESET}",
        f"     {DIM}Code cannot be written until you decide this.{RESET}",
        "",
    ]
    out += [f"     {DIM}→ {w}{RESET}" for w in ways_out]
    out.append("")
    return "\n".join(out)


def recorded(decision: str, path: str) -> str:
    return (
        f"\n  {GREEN}{BOLD}{RECORDED}  DECIDED{RESET}  {BOLD}{decision}{RESET}\n"
        f"     {DIM}written to{RESET} {CYAN}{path}{RESET}\n"
    )


def working(model: str, doing: str) -> str:
    """Live 'which AI is working' line — makes the multi-model design visible."""
    return f"  {PURPLE}{model}{RESET} {DIM}{doing}{RESET}"


def teaching(heading: str, body_lines: list[str]) -> str:
    out = ["", f"  {CYAN}{BOLD}{heading}{RESET}"]
    out += [f"     {line}" for line in body_lines]
    return "\n".join(out)


def _demo() -> None:
    print(banner("teamtasks"))
    print(question_box("How should people log in?", "phase 2 of 5 · backend", 7))
    print(
        teaching(
            "What this means",
            [
                "Logging in proves someone is who they say they are.",
                "Where that check lives decides how much you build yourself.",
            ],
        )
    )
    print(
        options(
            [
                ("A", "Email + password, by us", "full control, most work"),
                ("B", "A login service", "fast, less control"),
                ("C", "Sign in with Google", "no passwords to keep safe"),
            ]
        )
    )
    print(
        recommendation(
            "B",
            "small team app, and password safety comes free",
            "you depend on someone else's service.",
        )
    )
    print(progress(3, 8, "foundation"))
    print(prompt())
    print()
    print(blocked("rate limiting", "No decision recorded yet for:", [
        "answer the open question, or",
        "tell me to write it anyway (you will be asked to confirm)",
    ]))
    print(recorded("B — a login service", ".claude/forge/decisions/007-how-people-log-in.md"))
    print(working("Opus 4.8", "is now writing it…"))
    print()


if __name__ == "__main__":  # pragma: no cover - CLI surface
    arg = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if arg == "banner":
        print(banner(sys.argv[2] if len(sys.argv) > 2 else None))
    else:
        _demo()
