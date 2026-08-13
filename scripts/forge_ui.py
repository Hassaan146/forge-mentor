"""Forge Mentor — shared visual identity.

Every piece of Forge output goes through here so the plugin looks and feels
distinct from plain Claude Code (design rules R5, R9, R10, R11).

Rules this module enforces:
  R9  restraint — one symbol per meaning, and no symbol without one
  R9  colour and weight carry meaning; colour is never the only signal
  R10 questions are compact and boxed, never prose
  R11 six colours, each with exactly one meaning, taught to the user at setup

Colour degrades safely: if the terminal cannot do colour, or NO_COLOR is set,
every code becomes an empty string and the symbols still carry the meaning.
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata

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
    """True when it is safe to emit ANSI colour.

    **`isatty` is the right question for a command and the wrong one for a
    renderer**, and getting that backwards is why Forge shipped with no colour
    at all. The MCP server writes JSON-RPC down a pipe, so `isatty()` is false
    inside it — and every block it returned came out with every colour code
    replaced by an empty string. Not dimmed, not degraded: absent, in every
    build, always. The palette, the legend teaching it, and the tests holding
    it to account were all correct, and none of them ran in a process that
    could emit a single escape byte.

    The server sets `FORCE_COLOR` for exactly this reason (see `.mcp.json`):
    it is not writing to its own terminal, it is composing a block for a client
    that has one. `NO_COLOR` still wins over it, because that is the user's
    switch and it outranks ours.
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORGE_NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False

    # CI systems usually render colour fine; honour an explicit opt-in too.
    # Checked before the Claude Code test so a user who sets it anyway gets
    # what they asked for.
    if os.environ.get("FORCE_COLOR"):
        return True

    # **Inside Claude Code, colour does not arrive.** Everything Forge prints
    # reaches the user through the client, which renders it as markdown, and
    # markdown drops escape sequences. Emitting them anyway is not a harmless
    # extra: the legend's colour swatches come out as blank grey blocks, and
    # any codes that do survive are noise in the middle of a question.
    #
    # So the escape codes are for a real terminal, where Forge's own commands
    # are run directly and they work. In the client, the symbols, the frames
    # and the words carry every meaning on their own, which rule R11 has
    # required from the beginning precisely so this case would not be a loss.
    if os.environ.get("CLAUDECODE"):
        return False

    return sys.stdout.isatty()


_ON = _colour_enabled()


def _c(code: str) -> str:
    return code if _ON else ""


# Every colour, whether or not this process is emitting them. Kept so a block
# can be drawn in colour for a destination that wants the codes even though the
# process itself would not print them: see the `ansi` fence in `render_from`.
_CODES = {
    "AMBER": "\033[38;5;215m",
    "BLUE": "\033[38;5;75m",
    "GREEN": "\033[38;5;114m",
    "YELLOW": "\033[38;5;221m",
    "RED": "\033[38;5;203m",
    "PURPLE": "\033[38;5;177m",
    "DIM": "\033[38;5;245m",
    "FAINT": "\033[38;5;240m",
    "BOLD": "\033[1m",
    "RESET": "\033[0m",
}


def _apply_colour(on: bool) -> None:
    """Turn the palette on or off for the whole module.

    The builders read these as module constants, so switching the palette means
    rebinding them rather than threading a flag through fifteen functions. Used
    only by `render_from`, and always put back.
    """
    globals()["_ON"] = on
    for name, code in _CODES.items():
        globals()[name] = code if on else ""
    globals()["CYAN"] = globals()["BLUE"]
    globals()["NC"] = globals()["RESET"]


# --------------------------------------------------------------------------
# the palette — six meanings, one colour each (rule R11)
# --------------------------------------------------------------------------
#
# A colour with no fixed meaning is decoration, and decoration on a screen that
# is asking someone to make a decision competes with the decision. So each of
# these carries exactly one thing, the same thing everywhere in the product,
# and `legend()` teaches the set to the user at setup — a colour system nobody
# was told about is a colour system nobody can read.
#
# RESET is aliased to NC ("no colour") because that is what shell scripts call
# it, and every span in this module closes with it. An unclosed span does not
# stop at the end of Forge's output — it bleeds into whatever the terminal
# prints next, which is usually the user's own shell prompt.

AMBER = _c("\033[38;5;215m")  # Forge itself — the mark, headings, chrome
BLUE = _c("\033[38;5;75m")  # information — teaching, file paths, detail
GREEN = _c("\033[38;5;114m")  # it worked — recorded, passed, recommended
YELLOW = _c("\033[38;5;221m")  # your turn, or take care — actions, warnings, costs
RED = _c("\033[38;5;203m")  # it stopped — blocked, errors, findings
PURPLE = _c("\033[38;5;177m")  # which AI is working
DIM = _c("\033[38;5;245m")  # quiet detail; no meaning of its own
FAINT = _c("\033[38;5;240m")  # borders; no meaning of its own

# Kept because callers outside this module import it. Teaching text is blue.
CYAN = BLUE

BOLD = _c("\033[1m")
RESET = _c("\033[0m")
NC = RESET  # no colour — the reset, under the name shell scripts give it


def paint(colour: str, text: str, *, bold: bool = False) -> str:
    """Colour `text` and always close it.

    Every coloured span in Forge goes through here or ends in `NC` by hand.
    The failure this prevents is not cosmetic: a span left open runs past the
    end of Forge's output and recolours the user's shell prompt, which looks
    like Forge broke their terminal.
    """
    if not colour and not bold:
        return text
    return f"{BOLD if bold else ''}{colour}{text}{NC}"


# What each colour means, in the words the user is shown. The single source
# for `legend()`, for the setup explanation, and for the MCP `color_legend`
# tool — so the product cannot describe its own colours two different ways.
MEANINGS: tuple[tuple[str, str, str], ...] = (
    ("Forge", "AMBER", "Forge itself, if it is this colour, the plugin is talking"),
    ("Information", "BLUE", "teaching, explanations, file paths"),
    ("Good", "GREEN", "it worked, decided, recorded, passed, recommended"),
    ("Your turn", "YELLOW", "you have to act, or there is a cost to weigh"),
    ("Stopped", "RED", "something is wrong and Forge stopped, errors, blocks"),
    ("Working", "PURPLE", "which AI is doing the current job"),
)

_PALETTE = {
    "AMBER": AMBER,
    "BLUE": BLUE,
    "GREEN": GREEN,
    "YELLOW": YELLOW,
    "RED": RED,
    "PURPLE": PURPLE,
}

# One symbol per meaning, and no symbol without one (decision 035). Eight,
# fixed. Rule R9 said four and was right about restraint but wrong about the
# number — headings had no marker at all, so "What this means" and "Options"
# were told apart by position and nothing else.
#
# Adding a ninth requires a meaning none of these carries. That is the same
# restraint R9 wanted, stated as a test rather than as a count.
MARK = "⚒"        # Forge itself
TEACH = "💡"       # what this means
WEIGH = "⚖️"       # the options, weighed
STAR = "★"        # the recommendation
COST = "⚠️"        # what the recommendation costs
RECORDED = "✅"    # recorded
BLOCKED = "⛔"     # blocked
ACTION = "→"      # your turn — Forge has stopped and is waiting for you

# `→` is the eighth, and it earns its place by the test decision 035 set: no
# other symbol means "nothing moves until you answer". ✅ is the opposite, ⛔ is
# Forge refusing rather than Forge waiting, and ⚠️ is a cost inside a block the
# user is still reading. The moment the turn passes back to the user had no
# marker at all, which is exactly the gap that made four symbols too few.

# Every one of these renders wider than its Unicode class claims, so the frame
# has to be told. `⚖️` and `⚠️` carry a variation selector, which is zero-width
# and must not be counted twice.
BAR = "▌"        # a detail you cannot undo, on its own vertical

SYMBOLS = (MARK, TEACH, WEIGH, STAR, COST, RECORDED, BLOCKED, ACTION)

def _width() -> int:
    """How wide to draw, from the terminal rather than from a guess.

    This was a fixed 62, which wrapped an option's consequence onto a second
    line on a terminal with room for it — the text looked cramped for no
    reason. Clamped at both ends: narrow enough to stay readable in a split
    pane, and never so wide that a line of prose becomes hard to track back to
    the next one.
    """
    import shutil

    try:
        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
    except (OSError, ValueError):
        columns = 80
    return max(56, min(columns - 4, 96))


WIDTH = _width()


def _box_inner() -> int:
    """How wide the drawn box is, in the client where it actually ships.

    Not `_width()`. That measures a terminal, and the box is drawn inside a
    fenced block in a chat panel, which is a different surface with a different
    size that this process cannot ask about.

    Widened from 74 after a user said it plainly: a question with four options,
    each carrying its consequence, was wrapping every one of them onto a second
    line, so a menu that is four things read as eight. The consequence lines are
    the part that makes an option a choice rather than a word, and they are the
    first thing a narrow box breaks.

    `FORGE_BOX_WIDTH` narrows it again for a split pane. Clamped so neither end
    can produce a box that cannot hold an option.
    """
    raw = os.environ.get("FORGE_BOX_WIDTH", "").strip()
    try:
        wanted = int(raw) if raw else 92
    except ValueError:
        wanted = 92
    return max(56, min(wanted, 120))


BOX_INNER = _box_inner()


# --------------------------------------------------------------------------
# building blocks
# --------------------------------------------------------------------------


def plugin_version() -> str:
    """The version this copy actually is, read from the manifest.

    It was a default argument reading "0.1.0" while the manifest said 1.0.0 —
    so the banner reported a version that had not been true for months, and it
    is the first thing anybody looks at to check whether an update landed. A
    number that is wrong is worse than no number, because it is believed.
    """
    import json
    import pathlib

    try:
        here = pathlib.Path(__file__).resolve().parent.parent
        manifest = here / ".claude-plugin" / "plugin.json"
        return str(json.loads(manifest.read_text(encoding="utf-8")).get("version", "")) or "unknown"
    except (OSError, ValueError, TypeError, AttributeError):
        return "unknown"


def banner(project: str | None = None, version: str | None = None) -> str:
    """The start-up banner. Printed once when a session begins."""
    version = version or plugin_version()
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


# What each symbol means, in the words the user is shown. Used when colour is
# not arriving, which inside Claude Code is always.
SYMBOL_MEANINGS: tuple[tuple[str, str], ...] = (
    (MARK, "Forge itself. If a block carries this, the plugin is talking"),
    (TEACH, "what the decision means, before the options"),
    (WEIGH, "the options, weighed against each other"),
    (STAR, "what Forge recommends, and why"),
    (COST, "what that recommendation costs you"),
    (BAR, "a detail you cannot undo later"),
    (ACTION, "your turn. Forge has stopped and is waiting"),
    (RECORDED, "decided and written down"),
    (BLOCKED, "Forge stopped this, and says what would unblock it"),
)


def _symbol_legend() -> str:
    """The key, for a screen that gets no colour.

    Not a fallback with something missing. Inside Claude Code the colour never
    arrives, so teaching six colours there would be teaching a scheme the user
    cannot use, and printing swatches would put nine grey blocks on the screen.

    The symbols were always the ones carrying the meaning, because rule R11
    required that colour never be the only signal. This is that rule collecting
    on its promise.
    """
    rows = ["", f"  {DIM}Every block Forge prints is marked. Here is the set:{RESET}", ""]

    width = max(visible_width(symbol) for symbol, _ in SYMBOL_MEANINGS)
    lead = 4 + width + 2
    room = max(20, WIDTH - lead - 4)

    for symbol, meaning in SYMBOL_MEANINGS:
        pad = " " * (width - visible_width(symbol))
        wrapped = _wrap(meaning, room, "") or [""]
        rows.append(f"    {symbol}{pad}  {DIM}{wrapped[0]}{RESET}")
        for extra in wrapped[1:]:
            rows.append(f"{' ' * lead}{DIM}{extra}{RESET}")

    rows.append("")
    for line in _wrap(
        "A single-ruled frame is Forge talking. A double-ruled one means it has "
        "stopped and the next move is yours.",
        WIDTH - 10,
        "",
    ):
        rows.append(f"    {FAINT}{line}{RESET}")
    rows.append("")

    return "\n" + box(rows, title=f"{AMBER}{BOLD}{MARK} How to read Forge{RESET}") + "\n"


def legend() -> str:
    """The colour key, shown once at setup (rule R11).

    Forge asks the user to read six colours and act on them — a red line means
    stop, a yellow frame means it is their turn. None of that is legible to
    someone who was never told the scheme, and a user who cannot tell "Forge
    stopped this" from "Forge is thinking" learns to ignore both.

    So the key is taught at setup, beside the permissions, while the user is
    already reading carefully. It is also the reason every colour here is
    printed *in* its own colour: the sample is the explanation.
    """
    if not _ON:
        return _symbol_legend()

    rows = ["", f"  {DIM}Forge uses six colours. Each one means one thing:{RESET}", ""]

    # Sized from the terminal, not from a guess. A description longer than the
    # frame does not overflow tidily — the row runs past the right rail and the
    # box goes ragged, which on a narrow pane is every row at once.
    label_width = max(len(name) for name, _, _ in MEANINGS)
    swatch_width = 3 if _ON else max(len(key) for _, key, _ in MEANINGS) + 2
    lead = 4 + swatch_width + 2 + label_width + 2
    room = max(20, WIDTH - lead - 4)

    for name, key, means in MEANINGS:
        ink = _PALETTE[key]
        swatch = f"{ink}███{RESET}" if _ON else f"[{key.lower()}]".ljust(swatch_width)
        wrapped = _wrap(means, room, "") or [""]
        rows.append(
            f"    {swatch}  {ink}{BOLD}{name:<{label_width}}{RESET}  {DIM}{wrapped[0]}{RESET}"
        )
        for extra in wrapped[1:]:
            rows.append(f"{' ' * lead}{DIM}{extra}{RESET}")

    rows.append("")
    wrapped = _wrap(
        "A double-ruled frame means Forge has stopped and is waiting for you.",
        WIDTH - 12,
        "",
    )
    rows.append(f"    {YELLOW}{ACTION}  {wrapped[0]}{RESET}")
    for extra in wrapped[1:]:
        rows.append(f"       {YELLOW}{extra}{RESET}")

    rows.append("")
    for line in _wrap(
        "Colour is never the only signal. Every line reads the same without it. "
        "Set NO_COLOR=1 to turn it off.",
        WIDTH - 10,
        "",
    ):
        rows.append(f"    {FAINT}{line}{RESET}")
    rows.append("")

    return "\n" + box(rows, title=f"{AMBER}{BOLD}{MARK} How to read Forge{RESET}") + "\n"


# --------------------------------------------------------------------------
# measuring a line, which is the whole reason the box works
# --------------------------------------------------------------------------

_ANSI = re.compile(r"\[[0-9;]*m")

# Characters that render wider than their Unicode width class claims.
#
# `⚒` is the reason the frame used to come out crooked. Its East Asian width is
# "Neutral", so every rule says one column and `len()` agrees — but terminals
# give it emoji presentation and draw it in two. `⛔` and `✅` are properly
# classed Wide and need no help. Listed explicitly rather than inferred,
# because "does this terminal draw this symbol as an emoji" is not a question
# Python can answer.
_RENDERS_WIDE = frozenset("⚒💡⚖⚠")

# U+FE0F asks for emoji presentation and occupies no column of its own.
_VARIATION_SELECTOR = "️"


def visible_width(text: str) -> int:
    """How many columns this will actually occupy.

    Colour codes are stripped first — they are bytes the terminal consumes and
    never draws, so counting them is how padding silently goes wrong.
    """
    plain_text = _ANSI.sub("", text)
    width = 0
    for char in plain_text:
        if char == _VARIATION_SELECTOR:
            continue  # asks the terminal for emoji presentation; draws nothing
        if unicodedata.combining(char):
            continue  # an accent sits on the character before it
        if char in _RENDERS_WIDE or unicodedata.east_asian_width(char) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


# Two frames, and the difference between them is load-bearing. The single rule
# is Forge talking; the double rule is Forge waiting. A user scrolling back
# through a session finds the place they have to act by its border, before
# reading a word of it.
_SINGLE = ("┌", "─", "┐", "│", "└", "┘")
_DOUBLE = ("╔", "═", "╗", "║", "╚", "╝")


def box(lines: list[str], title: str = "", *, style: str = "single", edge: str = "") -> str:
    """Frame content so every row closes at the same column.

    The frame is drawn from `visible_width`, never from `len`. That difference
    is the entire bug this replaced: one emoji in the heading made the top rail
    a column longer than the bottom, and the box looked broken in a way that
    read as sloppiness rather than as an off-by-one.

    `style="double"` draws the heavier rule reserved for the action frame, and
    `edge` colours the border — the frame that asks for an answer is yellow,
    every other frame is faint, so the two never read as the same thing.
    """
    tl, bar, tr, side, bl, br = _DOUBLE if style == "double" else _SINGLE
    ink = edge or FAINT
    inner = WIDTH - 2
    out = []

    if title:
        pad = inner - visible_width(title) - 3
        out.append(f"  {ink}{tl}{bar}{RESET} {title} {ink}{bar * max(0, pad)}{tr}{RESET}")
    else:
        out.append(f"  {ink}{tl}{bar * inner}{tr}{RESET}")

    for line in lines:
        gap = max(0, inner - visible_width(line))
        out.append(f"  {ink}{side}{RESET}{line}{' ' * gap}{ink}{side}{RESET}")

    out.append(f"  {ink}{bl}{bar * inner}{br}{RESET}")
    return "\n".join(out)


def _wrap(text: str, width: int, indent: str) -> list[str]:
    """Wrap to the terminal, keeping a hanging indent.

    Long reasoning used to run past the edge and wrap wherever the terminal
    happened to break it, which put the second half of a sentence under the
    left margin and made the block look broken.
    """
    import textwrap

    if not text:
        return []
    return textwrap.wrap(text, width=width, initial_indent=indent, subsequent_indent=indent)


def rule(char: str = "─") -> str:
    return f"  {FAINT}{char * WIDTH}{RESET}"


# --------------------------------------------------------------------------
# the thing the user has to do next
# --------------------------------------------------------------------------

# What kind of answer is wanted, in one line, under the ask itself. The user
# knowing *that* an answer is wanted is not the same as knowing what shape it
# takes, and "A, B, or C" and "yes" and "a sentence in your own words" are
# three different questions wearing the same frame.
ASK_KINDS = {
    "choose": "one letter, or say it in your own words",
    "confirm": "type yes to go ahead, or no to stop",
    "answer": "in your own words, there is no wrong wording",
    "fix": "run the line above, then say done",
}

def _spoken_letters(letters: list[str]) -> str:
    """"A, B, or C" — the options named the way the user will say them back.

    Built from the options that were actually shown rather than hard-coded, so
    a two-option question does not ask for a C that was never offered.
    """
    if not letters:
        return ""
    if len(letters) == 1:
        return letters[0]
    return f"{', '.join(letters[:-1])}, or {letters[-1]}"


def action(ask: str, hint: str = "", *, kind: str = "answer") -> str:
    """The double-ruled frame that says the turn is the user's now.

    This is the one block on the screen the user has to *do* something with,
    and it used to be a single tinted line trailing the decision — the same
    weight as the option it sat under, and the first thing lost when a block
    scrolled. Reading back through a session, there was no way to find the
    place you were being asked something without reading everything.

    Three signals, so no one of them has to carry it alone: its own frame,
    drawn in double rule where every other frame is single; yellow, which
    means "your turn" everywhere in Forge; and `→`, which means it in a
    terminal with no colour at all.
    """
    # Wrapped, both of them. A hint long enough to reach the right rail does
    # not overflow tidily — the row runs past the border and the frame goes
    # ragged, which on a narrow pane is every row at once.
    body = [""]
    body += [f"  {YELLOW}{BOLD}{line}{RESET}" for line in _wrap(ask, WIDTH - 6, "")]

    tail = hint or ASK_KINDS.get(kind, "")
    if tail:
        body += [f"  {DIM}{line}{RESET}" for line in _wrap(tail, WIDTH - 6, "")]
    body.append("")

    title = f"{YELLOW}{BOLD}{ACTION} YOUR TURN{RESET}"
    return "\n" + box(body, title=title, style="double", edge=YELLOW) + "\n"


def confirm(what: str) -> str:
    """A yes/no gate — the "type yes to continue" moment, in its own frame."""
    return action(what, kind="confirm")


def choose(letters: str = "A, B, or C", question: str = "") -> str:
    """A pick-one gate. `letters` is whatever the options actually were."""
    return action(question or f"Your call: {letters}?", kind="choose")


# --------------------------------------------------------------------------
# details that must not be skimmed past
# --------------------------------------------------------------------------


def _important_lines(lines: list[str]) -> list[str]:
    """Bar-marked rows, for a detail the user cannot afford to miss.

    Bold alone does not survive being one line among ten. The bar puts the line
    on its own vertical, so it separates from the prose beside it whether or
    not the terminal is drawing colour.
    """
    out: list[str] = []
    for line in [ln for ln in lines if ln.strip()]:
        wrapped = _wrap(line, WIDTH - 10, "") or [""]
        out.append(f"    {YELLOW}{BOLD}{BAR}{RESET}  {BOLD}{wrapped[0]}{RESET}")
        for extra in wrapped[1:]:
            out.append(f"    {YELLOW}{BAR}{RESET}  {BOLD}{extra}{RESET}")
    return out


def roadmap(phases: list[dict], title: str = "THE PLAN") -> str:
    """The whole plan on one screen, before any of it is built.

    A plan revealed one phase at a time is not a plan. The user answered a
    question about how the project is tested without having been told there
    were three more phases after the one being tested — and that answer set
    the shape of all of them.

    Drawn as a spine rather than a table. A table of five rows says these are
    five things; a spine says they are one thing in five parts, which is what
    a phase plan actually is, and it makes "you are here" a position rather
    than a highlighted row.

    Each phase is a dict: number, title, delivers, state (`done`/`now`/
    `later`), steps, built.
    """
    if not phases:
        return note("The plan", ["No phases have been compiled yet."])

    width_number = max(len(str(p.get("number", ""))) for p in phases)
    body: list[str] = [""]

    for index, phase in enumerate(phases):
        state = str(phase.get("state", "later"))
        number = str(phase.get("number", index + 1)).rjust(width_number)
        steps = list(phase.get("steps") or [])
        built = int(phase.get("built") or 0)

        if state == "done":
            ink, badge, mark = GREEN, "done", RECORDED
        elif state == "now":
            ink, badge, mark = AMBER, "now", MARK
        else:
            ink, badge, mark = DIM, "later", " "

        right = f"{built}/{len(steps)} steps" if steps else "not broken into steps yet"
        head = f"  {ink}{mark}{RESET} {ink}{BOLD}{number}{RESET}  {BOLD}{phase.get('title', '')}{RESET}"
        gap = max(2, WIDTH - visible_width(head) - len(badge) - len(right) - 5)
        body.append(f"{head}{' ' * gap}{DIM}{right}{RESET}  {ink}{badge}{RESET}")

        # The spine. Two columns of it, so the phases read as one thing in
        # parts rather than as five unrelated rows.
        spine = f"  {FAINT}│{RESET}  " + " " * width_number
        for line in _wrap(str(phase.get("delivers", "")), WIDTH - 12, ""):
            body.append(f"{spine} {DIM}{line}{RESET}")

        if state == "now" and steps:
            for position, step in enumerate(steps, start=1):
                tick = f"{GREEN}{RECORDED}{RESET}" if step.get("built") else f"{FAINT}·{RESET}"
                text = step.get("text", "")
                shade = DIM if step.get("built") else ""
                body.append(f"{spine} {tick} {shade}{position}. {text}{RESET}")

        if index < len(phases) - 1:
            body.append(f"  {FAINT}│{RESET}")

    body.append("")
    return "\n" + box(body, title=f"{AMBER}{BOLD}{MARK} {title}{RESET}") + "\n"


def important(lines: list[str], heading: str = "Worth stopping on") -> str:
    """A standalone framed block for the details that change what a choice costs.

    Kept out of the ordinary prose deliberately. The things a user most needs
    to have read — this makes the repository public, this cannot be undone —
    were sentences four and five of a paragraph, which is where a reader who
    already decided they understood the block stops looking.
    """
    body = [""] + _important_lines(lines) + [""]
    return "\n" + box(body, title=f"{YELLOW}{BOLD}{COST} {heading}{RESET}", edge=YELLOW) + "\n"


def question_box(
    title: str,
    subtitle: str = "",
    number: int | None = None,
    done: int = 0,
    total: int = 0,
    stage: str = "",
) -> str:
    """The heading for a decision.

    **No box.** The frame this used to draw could not be relied on: `⚒` is an
    emoji-presentation character and renders two columns wide in most
    terminals, while `len()` counts it as one — so the top rail came out a
    column longer than the bottom one and the whole frame looked broken. A
    rule needs no width arithmetic, so it cannot disagree with itself.

    The progress moves up here too. It was a lone bar at the bottom of the
    screen, furthest from the thing it described; rule R4 asks for it to be
    visible, not for it to be last.
    """
    right = ""
    if total:
        right = f"{done} of ~{total}" + (f" · {stage}" if stage else "")

    left = f"{MARK} FORGE" + (f" · DECISION {number:03d}" if number else "")
    # Padding is computed from the plain text, and the two-column symbol is the
    # only thing that lies about its length — so it is counted as two.
    used = len(left) + 1 + len(right)
    gap = " " * max(2, WIDTH - used)

    out = [
        "",
        f"  {AMBER}{BOLD}{MARK} FORGE{RESET}"
        + (f"{FAINT} · {RESET}{AMBER}DECISION {number:03d}{RESET}" if number else "")
        + f"{gap}{DIM}{right}{RESET}",
        rule(),
        "",
        f"  {BOLD}{title}{RESET}",
    ]
    if subtitle:
        out.append(f"  {DIM}{subtitle}{RESET}")
    return "\n".join(out)


def _option_lines(items: list[tuple[str, str, str]]) -> list[str]:
    """Option rows, sized to the longest label so nothing floats in whitespace.

    The letters are yellow, not amber: they are the thing the user types back,
    and yellow means "yours to act on" everywhere else in Forge. Amber stays
    on Forge's own chrome, so the two never have to be told apart by hue.
    """
    label_width = max(len(label) for _, label, _ in items)
    room = WIDTH - label_width - 12
    out: list[str] = []
    for letter, label, note in items:
        pad = " " * (label_width - len(label) + 2)
        wrapped = _wrap(note, room, "") or [""]
        out.append(f"    {YELLOW}{BOLD}{letter}{RESET}  {BOLD}{label}{RESET}{pad}{DIM}{wrapped[0]}{RESET}")
        for extra in wrapped[1:]:
            out.append(f"{' ' * (label_width + 9)}{DIM}{extra}{RESET}")
    return out


MAX_NOTE_LINES = 3

# Rule R10 says two lines of explanation. It was a sentence in a document, so
# the first foundation question shipped with eleven: three paragraphs about how
# to describe an idea, in front of someone who only wanted to describe theirs.
# Long teaching is not more teaching. It is the thing people skip, and skipping
# it is how they arrive at the options without the concept.
#
# Three rather than two, because a concept plus its consequence is sometimes
# genuinely two sentences and the third catches the overflow. Anything past it
# belongs in the decision record, which is where someone looks in a month.
MAX_MEANS_LINES = 3


def _teaching_lines(means: list[str]) -> list[str]:
    """Take at most three sentences, then wrap each of them whole.

    **The cap counts sentences, not rows on the screen.** Counting rows meant a
    sentence could be cut wherever the wrap happened to fall, and one of them
    came out as "Changing it in week three is" with the "not." gone. That does
    not shorten the teaching, it reverses it. A cap that can invert a sentence
    is worse than no cap.

    Wrapped as well, because these arrive as hand-broken strings: a line longer
    than the frame ran straight through the right border and took the box with
    it, and nothing outside this module was measuring them.
    """
    out: list[str] = []
    for line in [line for line in means if line.strip()][:MAX_MEANS_LINES]:
        out += _wrap(line, WIDTH - 8, "    ")
    return out


def note(
    heading: str,
    lines: list[str],
    *,
    symbol: str = "",
    ask: str = "",
    important_lines: list[str] | None = None,
) -> str:
    """A short framed answer — the follow-up, not the decision.

    Everything Forge says goes inside a frame (decision 035). An unframed
    paragraph is indistinguishable from the assistant talking, so a session
    looked like Forge while a question was on screen and like ordinary chat
    for everything in between — and the user could not tell which of the two
    was bound by the rules.

    **Capped at three lines, and the cap is the feature.** The follow-up
    sprawled because it had nowhere to be short: given a lid, each cost fits on
    one line and the full argument stays in the decision record, which is where
    someone will actually look for it in a month.
    """
    kept = [line for line in lines if line.strip()][:MAX_NOTE_LINES]
    dropped = len([line for line in lines if line.strip()]) - len(kept)

    body: list[str] = [""]
    for line in kept:
        body += [f"{DIM}{wrapped}{RESET}" for wrapped in _wrap(line, WIDTH - 8, "    ")]

    if dropped:
        body += [
            "",
            f"    {FAINT}{dropped} more in the decision record{RESET}",
        ]

    if important_lines:
        body += [""] + _important_lines(important_lines)

    body.append("")

    title = f"{AMBER}{BOLD}{symbol or MARK} {heading}{RESET}"
    out = "\n" + box(body, title=title) + "\n"

    # The ask leaves the box and gets its own. Inside, it was the last line of
    # a block the user had already started skimming; outside, it is the only
    # double-ruled thing on the screen.
    if ask:
        out += action(ask, kind="answer")
    return out


def decision(
    title: str,
    *,
    number: int | None = None,
    subtitle: str = "",
    concept: str = "",
    means: list[str] | None = None,
    choices: list[tuple[str, str, str]] | None = None,
    recommend: tuple[str, str] | None = None,
    against: str = "",
    important_lines: list[str] | None = None,
    done: int = 0,
    total: int = 0,
    stage: str = "",
    ask: str = "",
) -> str:
    """A whole decision, framed, as one block.

    Composed here rather than by the caller printing pieces in order. The parts
    have to appear in a fixed sequence to read properly — teach, then options,
    then the recommendation, then the question — and leaving that order to
    whoever is calling meant it drifted between stages.

    The frame is measured with `visible_width`, so the emoji in the heading no
    longer pushes the top rail a column past the bottom one.
    """
    label = f"{AMBER}{BOLD}{MARK} FORGE{RESET}"
    if number:
        label += f"{FAINT} · {RESET}{AMBER}DECISION {number:03d}{RESET}"

    body: list[str] = ["", f"  {BOLD}{title}{RESET}"]
    if subtitle:
        body.append(f"  {DIM}{subtitle}{RESET}")
    if concept:
        body.append(f"  {DIM}Concept: {concept}{RESET}")

    if means:
        body += ["", f"  {BLUE}{BOLD}{TEACH} What this means{RESET}"]
        body += _teaching_lines(means)

    if choices:
        body += ["", f"  {AMBER}{BOLD}{WEIGH} Options{RESET}"]
        body += _option_lines(choices)

    if recommend:
        body += ["", f"  {GREEN}{BOLD}{STAR} Recommended{RESET}  {BOLD}{recommend[0]}{RESET}"]
        body += [f"{DIM}{line}{RESET}" for line in _wrap(recommend[1], WIDTH - 8, "    ")]
        if against:
            body.append("")
            body += [
                f"{YELLOW}{line}{RESET}"
                for line in _wrap(f"{COST} Against it: {against}", WIDTH - 8, "    ")
            ]

    # What the user cannot afford to skim. Yellow, barred, and on its own
    # vertical — not sentence four of the teaching, which is where a reader
    # who has already decided they understand the block stops looking.
    if important_lines:
        body += [""] + _important_lines(important_lines)

    if total:
        body += ["", f"  {DIM}{done} of ~{total}" + (f" · {stage}" if stage else "") + RESET]
    body.append("")

    # The question leaves the block. It is the only thing here the user has to
    # act on, and as the last tinted line inside the frame it carried the same
    # weight as the option above it.
    letters = _spoken_letters([letter for letter, _, _ in choices]) if choices else ""
    if not ask:
        ask = f"Your call: {letters}?" if letters else "Your call"
    return "\n" + box(body, title=label) + "\n" + action(
        ask, kind="choose" if choices else "answer"
    )


def options(items: list[tuple[str, str, str]]) -> str:
    """Options as a tight list: (letter, label, one-line consequence).

    The label column is sized to the longest label rather than a fixed 28, so
    short options do not sit in a lake of whitespace and a long one is not
    pushed off the edge. The consequence is what the user is really comparing,
    so it gets the room that is left.
    """
    if not items:
        return ""

    label_width = max(len(label) for _, label, _ in items)
    room = WIDTH - label_width - 8

    out = ["", f"  {AMBER}{BOLD}{WEIGH} Options{RESET}"]
    for letter, label, note in items:
        head = f"    {YELLOW}{BOLD}{letter}{RESET}  {BOLD}{label}{RESET}"
        pad = " " * (label_width - len(label) + 2)
        wrapped = _wrap(note, room, "")
        out.append(f"{head}{pad}{DIM}{wrapped[0] if wrapped else ''}{RESET}")
        # A consequence too long for one line continues under itself, not
        # under the letter — so the columns stay readable.
        for extra in wrapped[1:]:
            out.append(f"{' ' * (label_width + 9)}{DIM}{extra}{RESET}")
    return "\n".join(out)


def recommendation(choice: str, reason: str, against: str = "") -> str:
    """Forge's own view, and what is wrong with it.

    The reason wraps under the recommendation rather than trailing off the
    right edge — it is usually the longest line on the screen, and it used to
    break wherever the terminal happened to run out.
    """
    out = ["", f"  {GREEN}{BOLD}{STAR} Recommended{RESET}  {BOLD}{choice}{RESET}"]
    out += [f"{DIM}{line}{RESET}" for line in _wrap(reason, WIDTH - 5, "     ")]
    if against:
        # Always shown, and in yellow — it is a cost, and cost is what yellow
        # means. A recommendation with no cost is advertising, and the user is
        # being asked to weigh it, not to accept it.
        out.append("")
        out += [
            f"{YELLOW}{line}{RESET}"
            for line in _wrap(f"{COST} Against it: {against}", WIDTH - 5, "     ")
        ]
    return "\n".join(out)


def progress(done: int, total: int, label: str = "") -> str:
    """Progress bar. Required on every question by rule R4."""
    slots = 12
    filled = 0 if total <= 0 else min(slots, round(slots * done / total))
    bar = f"{GREEN}{'█' * filled}{FAINT}{'░' * (slots - filled)}{RESET}"
    tail = f" {DIM}· {label}{RESET}" if label else ""
    return f"\n  {DIM}[{RESET}{bar}{DIM}]  {done} of ~{total}{RESET}{tail}"


def prompt(text: str = "Your call") -> str:
    """The one-line inline prompt.

    Kept for callers that want a bare line. Anything asking the user to decide
    should use `action()` instead — a tinted line is the same weight as the
    text above it, which is how the question got lost.
    """
    return f"\n  {YELLOW}{BOLD}{text}{RESET} {FAINT}›{RESET} "


def blocked(what: str, why: str, ways_out: list[str]) -> str:
    """The governor stopping a write.

    Red and ⛔ and the words, so no one signal is load-bearing — and framed
    like everything else (decision 035), because an unframed block is
    indistinguishable from ordinary assistant text, and this is the one
    message the user most needs to know came from Forge's rules.

    The ways out go in the action frame under it. They are the only part of
    this the user can do anything with.
    """
    body = [""]
    body += [f"  {DIM}{line}{RESET}" for line in _wrap(why, WIDTH - 6, "")]

    # The undecided thing gets the bar. It is the single detail that tells the
    # user which question to go and answer, and as the tail of a sentence it
    # was the easiest part of the message to read past.
    body += _important_lines([what])
    body += [
        "",
        f"  {DIM}Code cannot be written until you decide this.{RESET}",
        "",
    ]
    title = f"{RED}{BOLD}{BLOCKED} FORGE STOPPED THIS{RESET}"
    out = "\n" + box(body, title=title, edge=RED) + "\n"

    if ways_out:
        ways = [""] + [f"  {YELLOW}{ACTION}{RESET} {BOLD}{w}{RESET}" for w in ways_out] + [""]
        out += "\n" + box(
            ways,
            title=f"{YELLOW}{BOLD}{ACTION} YOUR TURN{RESET}",
            style="double",
            edge=YELLOW,
        ) + "\n"
    return out


def recorded(decision: str, path: str) -> str:
    return (
        f"\n  {GREEN}{BOLD}{RECORDED}  DECIDED{RESET}  {BOLD}{decision}{RESET}\n"
        f"     {DIM}written to{RESET} {BLUE}{path}{RESET}\n"
    )


def working(model: str, doing: str) -> str:
    """Live 'which AI is working' line — makes the multi-model design visible."""
    return f"  {PURPLE}{model}{RESET} {DIM}{doing}{RESET}"


def teaching(heading: str, body_lines: list[str]) -> str:
    out = ["", f"  {BLUE}{BOLD}{TEACH} {heading}{RESET}"]
    out += [f"     {line}" for line in body_lines]
    return "\n".join(out)


def _demo() -> None:
    print(banner("teamtasks"))
    print(legend())
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
    print(
        important([
            "A login service means your users' passwords are held by someone else.",
            "Moving off it later means every account has to sign up again.",
        ])
    )
    print(choose("A, B, or C"))
    print(confirm("This will make the repository public. Continue?"))
    print(blocked("rate limiting", "No decision recorded yet for:", [
        "answer the open question, or",
        "tell me to write it anyway (you will be asked to confirm)",
    ]))
    print(recorded("B, a login service", ".claude/forge/decisions/007-how-people-log-in.md"))
    print(working("Opus 5", "is now writing it…"))
    print()


# --------------------------------------------------------------------------
# the same block, for a client that renders markdown instead of escape codes
# --------------------------------------------------------------------------
#
# **Why a second renderer rather than a fallback.** Inside Claude Code the
# escape codes never arrive: everything Forge prints reaches the user through a
# markdown renderer, which drops them. The ASCII box survives that trip, but it
# arrives entirely monochrome, and after six requests for colour the honest
# answer stopped being "it cannot be done" and became "not that way".
#
# Markdown is the one thing that surface *does* colour. Headings, bold, code
# spans and rules are all styled by the client, so the block can carry the same
# information and come out in colour, drawn by the thing that is doing the
# drawing. Same content, two presentations, chosen by where it is going. The
# legend already worked this way for symbols against colours; this is the same
# principle applied to the whole block.


def _md_decision(payload: dict) -> str:
    """A decision, as markdown the client will colour."""
    number = payload.get("number")
    done, total = int(payload.get("done") or 0), int(payload.get("total") or 0)

    head = f"{MARK} FORGE"
    if number:
        head += f" · DECISION {int(number):03d}"

    out = [f"### {head}", "", f"**{payload.get('title', '')}**"]
    if payload.get("subtitle"):
        out.append(f"*{payload['subtitle']}*")

    means = [line for line in (payload.get("means") or []) if str(line).strip()]
    if means:
        out += ["", f"{TEACH} **What this means**", ""]
        out += [f"> {line}" for line in means]

    choices = payload.get("choices") or []
    if choices:
        out += ["", f"{WEIGH} **Options**", "", "| | | |", "|---|---|---|"]
        for choice in choices:
            letter, label, note = (list(choice) + ["", "", ""])[:3]
            out.append(f"| `{letter}` | **{label}** | {note} |")

    recommend = payload.get("recommend")
    if recommend:
        pick, why = (list(recommend) + ["", ""])[:2]
        out += ["", f"{STAR} **Recommended: {pick}** · {why}"]
    if payload.get("against"):
        out.append(f"{COST} **Against it:** {payload['against']}")

    for line in payload.get("important_lines") or []:
        out += ["", f"> {BAR} **{line}**"]

    if total:
        stage = f" · {payload['stage']}" if payload.get("stage") else ""
        out += ["", f"`{done} of ~{total}{stage}`"]

    letters = _spoken_letters([str(c[0]) for c in choices]) if choices else ""
    ask = str(payload.get("ask") or "") or (
        f"Your call: {letters}?" if letters else "Your call"
    )
    hint = ASK_KINDS["choose" if choices else "answer"]

    out += ["", "---", "", f"### {ACTION} YOUR TURN", "", f"**{ask}**", "", f"*{hint}*"]
    return "\n".join(out)


def _md_note(payload: dict) -> str:
    lines = [line for line in (payload.get("lines") or []) if str(line).strip()]
    out = [f"### {payload.get('symbol') or MARK} {payload.get('heading', '')}", ""]
    out += [f"> {line}" for line in lines[:MAX_NOTE_LINES]]
    for line in payload.get("important_lines") or []:
        out += ["", f"> {BAR} **{line}**"]
    if payload.get("ask"):
        out += ["", "---", "", f"### {ACTION} YOUR TURN", "", f"**{payload['ask']}**"]
    return "\n".join(out)


def _md_action(payload: dict) -> str:
    hint = str(payload.get("hint") or "") or ASK_KINDS.get(
        str(payload.get("ask_kind", "answer")), ""
    )
    out = [f"### {ACTION} YOUR TURN", "", f"**{payload.get('ask', '')}**"]
    if hint:
        out += ["", f"*{hint}*"]
    return "\n".join(out)


def _md_legend() -> str:
    out = [f"### {MARK} How to read Forge", "", "| | |", "|---|---|"]
    out += [f"| {symbol} | {meaning} |" for symbol, meaning in SYMBOL_MEANINGS]
    out += [
        "",
        "*A `### → YOUR TURN` heading means Forge has stopped and is waiting for you.*",
    ]
    return "\n".join(out)


def _md_roadmap(phases: list[dict], title: str) -> str:
    out = [f"### {MARK} {title}", "", "| | | | |", "|---|---|---|---|"]
    for phase in phases:
        steps = list(phase.get("steps") or [])
        built = int(phase.get("built") or 0)
        count = f"{built}/{len(steps)} steps" if steps else "not broken into steps yet"
        state = str(phase.get("state", "later"))
        mark = {"done": RECORDED, "now": MARK}.get(state, "·")
        out.append(
            f"| {mark} | `{phase.get('number', '')}` | **{phase.get('title', '')}** "
            f"<br>{phase.get('delivers', '')} | {count} · {state} |"
        )
        if state == "now":
            for position, step in enumerate(steps, start=1):
                tick = RECORDED if step.get("built") else "·"
                out.append(f"| | | {tick} {position}. {step.get('text', '')} | |")
    return "\n".join(out)


def _plain_block(payload: dict) -> str:
    """The drawn block, whatever the colour setting says.

    `render_from` sends everything here when escape codes cannot arrive, so it
    has to build the frame directly rather than going back through the branch
    that chose this route.
    """
    kind = str(payload.get("kind", "")).strip().lower()

    if kind == "legend":
        return legend()
    if kind == "roadmap":
        return roadmap(list(payload.get("phases") or []), payload.get("title", "THE PLAN"))
    if kind == "action":
        return action(
            str(payload.get("ask", "")),
            str(payload.get("hint", "")),
            kind=str(payload.get("ask_kind", "answer")),
        )
    if kind == "note":
        return note(
            str(payload.get("heading", "")),
            list(payload.get("lines") or []),
            symbol=str(payload.get("symbol", "")),
            ask=str(payload.get("ask", "")),
            important_lines=list(payload.get("important_lines") or []) or None,
        )
    if kind == "decision":
        recommend = payload.get("recommend")
        return decision(
            str(payload.get("title", "")),
            number=payload.get("number") or None,
            subtitle=str(payload.get("subtitle", "")),
            concept=str(payload.get("concept", "")),
            means=list(payload.get("means") or []) or None,
            choices=[tuple(c) for c in (payload.get("choices") or [])] or None,
            recommend=(tuple(recommend) if recommend else None),
            against=str(payload.get("against", "")),
            important_lines=list(payload.get("important_lines") or []) or None,
            done=int(payload.get("done") or 0),
            total=int(payload.get("total") or 0),
            stage=str(payload.get("stage", "")),
            ask=str(payload.get("ask", "")),
        )

    raise ValueError(
        f"Unknown block kind {kind!r}. "
        "Use one of: decision, note, action, legend, roadmap, banner."
    )


def _coloured_box(payload: dict) -> str:
    """A drawn box whose left border is also the thing that colours the line.

    **Both, finally, and the trick is that only column zero is anchored.**
    highlight.js decides a diff line from its first character, and says nothing
    about the rest. So the right border, the padding and every box rule after
    column zero are free. What has to give is the left border character: it
    becomes the marker.

      `+`  green: the frame itself, and an option, a thing you can pick
      `-`  red: what it costs, the line rule R11 paints yellow
      `|`  default: ordinary content, no claim on the eye

    That is why the earlier attempt lost the box. It put `+` where the border
    should be *instead of* a border, rather than making the border do both jobs.
    """
    kind = str(payload.get("kind", "")).strip().lower()
    inner = BOX_INNER

    def rule(title: str = "") -> str:
        if not title:
            return "+" + "-" * inner + "+"
        return "+-- " + title + " " + "-" * max(3, inner - len(title) - 4) + "+"

    def row(text: str = "", mark: str = "|") -> str:
        return f"{mark}  {text.ljust(inner - 3)}|"

    def wrapped(text: str, mark: str = "|", indent: str = "") -> list[str]:
        return [row(indent + line, mark) for line in _wrap(text, inner - 6 - len(indent), "")]

    out: list[str] = []

    if kind in {"action", "note", "legend", "roadmap", "decision"}:
        pass
    else:
        raise ValueError(
            f"Unknown block kind {kind!r}. "
            "Use one of: decision, note, action, legend, roadmap, banner."
        )

    if kind == "action":
        hint = str(payload.get("hint") or "") or ASK_KINDS.get(
            str(payload.get("ask_kind", "answer")), ""
        )
        out = [rule(f"{ACTION} YOUR TURN"), row()]
        out += wrapped(str(payload.get("ask", "")))
        if hint:
            out += wrapped(hint)
        out += [row(), rule()]
        return "```diff\n" + "\n".join(out) + "\n```"

    if kind == "note":
        out = [rule(f"{payload.get('symbol') or MARK} {payload.get('heading', '')}"), row()]
        for line in [ln for ln in (payload.get("lines") or []) if str(ln).strip()][
            :MAX_NOTE_LINES
        ]:
            out += wrapped(str(line))
        for line in payload.get("important_lines") or []:
            out += wrapped(f"{BAR} {line}", "-")
        out += [row(), rule()]
        if payload.get("ask"):
            out += ["", *_coloured_box(
                {"kind": "action", "ask": payload["ask"], "ask_kind": "answer"}
            ).split("\n")[1:-1]]
        return "```diff\n" + "\n".join(out) + "\n```"

    if kind == "legend":
        out = [rule(f"{MARK} How to read Forge"), row()]
        for symbol, meaning in SYMBOL_MEANINGS:
            out += wrapped(f"{symbol}  {meaning}")
        out += [row(), rule()]
        return "```diff\n" + "\n".join(out) + "\n```"

    if kind == "roadmap":
        out = [rule(f"{MARK} {payload.get('title', 'THE PLAN')}"), row()]
        for phase in payload.get("phases") or []:
            steps = list(phase.get("steps") or [])
            built = int(phase.get("built") or 0)
            state = str(phase.get("state", "later"))
            count = f"{built}/{len(steps)} steps" if steps else "no steps yet"
            mark = "+" if state in {"done", "now"} else "|"
            out += wrapped(
                f"{phase.get('number', '')}  {phase.get('title', '')}   {count} · {state}", mark
            )
            out += wrapped(str(phase.get("delivers", "")), "|", "   ")
            if state == "now":
                for position, step in enumerate(steps, start=1):
                    tick = RECORDED if step.get("built") else "·"
                    out += wrapped(f"{tick} {position}. {step.get('text', '')}", "|", "   ")
            out.append(row())
        out.append(rule())
        return "```diff\n" + "\n".join(out) + "\n```"

    number = payload.get("number")
    title = f"{MARK} FORGE" + (f" · DECISION {int(number):03d}" if number else "")
    out = [rule(title), row()]
    out += wrapped(str(payload.get("title", "")))
    if payload.get("subtitle"):
        out += wrapped(str(payload["subtitle"]))
    # The concept, named. A question is about something the project contains,
    # and saying which thing is what makes the answer worth anything on the
    # next project. Without it the user learns that they picked B.
    if payload.get("concept"):
        out += wrapped(f"Concept: {payload['concept']}")

    means = [line for line in (payload.get("means") or []) if str(line).strip()]
    if means:
        out.append(row())
        out += wrapped(f"{TEACH} What this means")
        for line in means[:MAX_MEANS_LINES]:
            out += wrapped(str(line), "|", "  ")

    choices = payload.get("choices") or []
    if choices:
        out.append(row())
        out += wrapped(f"{WEIGH} Options")
        width = max(len(str(c[1])) for c in choices)
        for choice in choices:
            letter, label, note_text = (list(choice) + ["", "", ""])[:3]
            # Hanging indent, so a consequence that runs on lines up under
            # itself rather than under the next letter. Without it a wrapped
            # option reads as another option: the continuation carries the same
            # `+` in column zero, which is what marks a line as choosable.
            lead = f"  {letter}  {str(label).ljust(width)}   "
            room = max(20, inner - 6 - len(lead))
            first, *rest = _wrap(str(note_text), room, "") or [""]
            out.append(row(f"{lead}{first}", "+"))
            out += [row(" " * len(lead) + line, "+") for line in rest]

    recommend = payload.get("recommend")
    if recommend:
        pick, why = (list(recommend) + ["", ""])[:2]
        out.append(row())
        out += wrapped(f"{STAR} Recommended  {pick}", "+")
        out += wrapped(str(why), "+", "  ")
    if payload.get("against"):
        out += wrapped(f"{COST} Against it: {payload['against']}", "-", "  ")
    for line in payload.get("important_lines") or []:
        out += wrapped(f"{BAR} {line}", "-", "  ")

    total = int(payload.get("total") or 0)
    if total:
        stage = f" · {payload['stage']}" if payload.get("stage") else ""
        out += [row(), row(f"{int(payload.get('done') or 0)} of ~{total}{stage}")]

    out += [row(), rule()]

    letters = _spoken_letters([str(c[0]) for c in choices]) if choices else ""
    ask = str(payload.get("ask") or "") or (
        f"Your call: {letters}?" if letters else "Your call"
    )
    turn = _coloured_box(
        {"kind": "action", "ask": ask, "ask_kind": "choose" if choices else "answer"}
    ).split("\n")[1:-1]

    return "```diff\n" + "\n".join(out) + "\n\n" + "\n".join(turn) + "\n```"


def _diff_block(payload: dict) -> str:
    """The block as a `diff` fence, which the client's highlighter colours.

    **Why this works where five other things did not.** Claude Code bundles
    highlight.js: `hljs-addition`, `hljs-deletion`, `hljs-meta` and
    `hljs-comment` are all in the binary. A fenced block with a language it
    knows gets tokenised and coloured by the client itself, so the colour is
    applied at the far end rather than carried there. `ansi` failed because
    highlight.js has no such language, not because fences cannot be coloured.

    **The markers carry the meanings.** They are not decoration borrowed from
    version control:

      `@@ … @@`   Forge's own chrome, the heading and the turn marker
      `+`         an option, a thing you can pick
      `-`         what it costs you, the line R11 paints yellow
      `#`         quiet detail, the subtitle and the progress

    Every one of them has to sit in column zero, because highlight.js anchors
    them with `^`. That is why the left border is gone: a `│` in front of a
    `+` makes it an ordinary line. The fence draws the container instead, and
    the rules above and below close it.
    """
    kind = str(payload.get("kind", "")).strip().lower()
    rule = "─" * 58

    def head(text: str) -> str:
        return f"@@ {text} {rule[: max(4, 62 - len(text))]}@@"

    if kind == "action":
        hint = str(payload.get("hint") or "") or ASK_KINDS.get(
            str(payload.get("ask_kind", "answer")), ""
        )
        out = [head(f"{ACTION} YOUR TURN"), "", f"  {payload.get('ask', '')}"]
        if hint:
            out.append(f"# {hint}")
        return "```diff\n" + "\n".join(out) + "\n```"

    if kind == "note":
        out = [head(f"{payload.get('symbol') or MARK} {payload.get('heading', '')}"), ""]
        out += [
            f"  {line}"
            for line in (payload.get("lines") or [])
            if str(line).strip()
        ][:MAX_NOTE_LINES]
        out += [f"- {BAR} {line}" for line in payload.get("important_lines") or []]
        if payload.get("ask"):
            out += ["", head(f"{ACTION} YOUR TURN"), "", f"  {payload['ask']}"]
        return "```diff\n" + "\n".join(out) + "\n```"

    if kind == "legend":
        out = [head(f"{MARK} How to read Forge"), ""]
        out += [f"  {symbol}  {meaning}" for symbol, meaning in SYMBOL_MEANINGS]
        out += ["", "# A `→ YOUR TURN` rule means Forge has stopped and is waiting."]
        return "```diff\n" + "\n".join(out) + "\n```"

    if kind == "roadmap":
        out = [head(f"{MARK} {payload.get('title', 'THE PLAN')}"), ""]
        for phase in payload.get("phases") or []:
            steps = list(phase.get("steps") or [])
            built = int(phase.get("built") or 0)
            state = str(phase.get("state", "later"))
            count = f"{built}/{len(steps)} steps" if steps else "no steps yet"
            marker = "+" if state == "done" else (" " if state == "now" else "#")
            out.append(
                f"{marker} {phase.get('number', '')}  {phase.get('title', '')}"
                f"   {count} · {state}"
            )
            out.append(f"#     {phase.get('delivers', '')}")
            if state == "now":
                for position, step in enumerate(steps, start=1):
                    tick = RECORDED if step.get("built") else "·"
                    out.append(f"    {tick} {position}. {step.get('text', '')}")
        return "```diff\n" + "\n".join(out) + "\n```"

    if kind != "decision":
        raise ValueError(
            f"Unknown block kind {kind!r}. "
            "Use one of: decision, note, action, legend, roadmap, banner."
        )

    number = payload.get("number")
    title = f"{MARK} FORGE" + (f" · DECISION {int(number):03d}" if number else "")

    out = [head(title), "", f"  {payload.get('title', '')}"]
    if payload.get("subtitle"):
        out.append(f"# {payload['subtitle']}")

    means = [line for line in (payload.get("means") or []) if str(line).strip()]
    if means:
        out += ["", f"  {TEACH} What this means"]
        for line in means[:MAX_MEANS_LINES]:
            out += [f"    {wrapped}" for wrapped in _wrap(line, 62, "")]

    choices = payload.get("choices") or []
    if choices:
        out += ["", f"  {WEIGH} Options"]
        width = max(len(str(c[1])) for c in choices)
        for choice in choices:
            letter, label, note_text = (list(choice) + ["", "", ""])[:3]
            out.append(f"+   {letter}  {str(label).ljust(width)}   {note_text}")

    recommend = payload.get("recommend")
    if recommend:
        pick, why = (list(recommend) + ["", ""])[:2]
        out += ["", f"  {STAR} Recommended  {pick}"]
        out += [f"      {wrapped}" for wrapped in _wrap(str(why), 60, "")]
    if payload.get("against"):
        out += [f"- {COST} Against it: {line}" for line in _wrap(str(payload["against"]), 60, "")]

    for line in payload.get("important_lines") or []:
        out += [f"- {BAR} {wrapped}" for wrapped in _wrap(str(line), 60, "")]

    total = int(payload.get("total") or 0)
    if total:
        stage = f" · {payload['stage']}" if payload.get("stage") else ""
        out += ["", f"# {int(payload.get('done') or 0)} of ~{total}{stage}"]

    letters = _spoken_letters([str(c[0]) for c in choices]) if choices else ""
    ask = str(payload.get("ask") or "") or (
        f"Your call: {letters}?" if letters else "Your call"
    )
    hint = ASK_KINDS["choose" if choices else "answer"]
    # A closing rule, so the block reads as shut rather than as trailing off.
    # The opening one alone left it looking like the start of something.
    out += ["", head(f"{ACTION} YOUR TURN"), "", f"  {ask}", f"# {hint}", "", f"@@{rule}@@"]

    return "```diff\n" + "\n".join(out) + "\n```"


def _boxed_markdown(payload: dict) -> str:
    """The block as a one-column table, so the client draws the box.

    **The last untried shape, and the only one that can give both.** A fence
    keeps the drawing and kills the colour. Loose markdown keeps the colour and
    loses the boundary. A table is markdown the client both colours *and* draws
    a border around, so the box comes from the renderer instead of from
    characters it refuses to leave alone.

    One line per row, and no `<br>`: raw HTML inside a cell is not something
    every markdown renderer honours, and this has already cost enough round
    trips to guesses about what a renderer will do.
    """
    kind = str(payload.get("kind", "")).strip().lower()

    def table(title: str, rows: list[str]) -> str:
        out = [f"| {title} |", "| :--- |"]
        out += [f"| {row} |" for row in rows]
        return "\n".join(out)

    if kind == "action":
        hint = str(payload.get("hint") or "") or ASK_KINDS.get(
            str(payload.get("ask_kind", "answer")), ""
        )
        rows = [f"**{payload.get('ask', '')}**"] + ([f"*{hint}*"] if hint else [])
        return table(f"{ACTION} **YOUR TURN**", rows)

    if kind == "note":
        rows = [str(line) for line in (payload.get("lines") or []) if str(line).strip()]
        rows = rows[:MAX_NOTE_LINES]
        rows += [f"{BAR} **{line}**" for line in payload.get("important_lines") or []]
        block = table(
            f"{payload.get('symbol') or MARK} **{payload.get('heading', '')}**", rows
        )
        if payload.get("ask"):
            block += "\n\n" + _boxed_markdown(
                {"kind": "action", "ask": payload["ask"], "ask_kind": "answer"}
            )
        return block

    if kind == "legend":
        return table(
            f"{MARK} **How to read Forge**",
            [f"{symbol}  {meaning}" for symbol, meaning in SYMBOL_MEANINGS],
        )

    if kind == "roadmap":
        rows = []
        for phase in payload.get("phases") or []:
            steps = list(phase.get("steps") or [])
            built = int(phase.get("built") or 0)
            state = str(phase.get("state", "later"))
            mark = {"done": RECORDED, "now": MARK}.get(state, "·")
            count = f"{built}/{len(steps)} steps" if steps else "no steps yet"
            rows.append(
                f"{mark} `{phase.get('number', '')}` **{phase.get('title', '')}** "
                f"· {count} · {state}"
            )
            rows.append(f"{phase.get('delivers', '')}")
            if state == "now":
                for position, step in enumerate(steps, start=1):
                    tick = RECORDED if step.get("built") else "·"
                    rows.append(f"{tick} {position}. {step.get('text', '')}")
        return table(f"{MARK} **{payload.get('title', 'THE PLAN')}**", rows)

    if kind != "decision":
        raise ValueError(
            f"Unknown block kind {kind!r}. "
            "Use one of: decision, note, action, legend, roadmap, banner."
        )

    number = payload.get("number")
    head = f"{MARK} **FORGE**"
    if number:
        head += f" · **DECISION {int(number):03d}**"

    rows = [f"**{payload.get('title', '')}**"]
    if payload.get("subtitle"):
        rows.append(f"*{payload['subtitle']}*")

    means = [line for line in (payload.get("means") or []) if str(line).strip()]
    if means:
        rows.append(f"{TEACH} **What this means**")
        rows += [f"{line}" for line in means]

    choices = payload.get("choices") or []
    if choices:
        rows.append(f"{WEIGH} **Options**")
        for choice in choices:
            letter, label, note_text = (list(choice) + ["", "", ""])[:3]
            rows.append(f"`{letter}`  **{label}**  {note_text}")

    recommend = payload.get("recommend")
    if recommend:
        pick, why = (list(recommend) + ["", ""])[:2]
        rows.append(f"{STAR} **Recommended: {pick}**  {why}")
    if payload.get("against"):
        rows.append(f"{COST} **Against it:** {payload['against']}")

    for line in payload.get("important_lines") or []:
        rows.append(f"{BAR} **{line}**")

    total = int(payload.get("total") or 0)
    if total:
        stage = f" · {payload['stage']}" if payload.get("stage") else ""
        rows.append(f"`{int(payload.get('done') or 0)} of ~{total}{stage}`")

    letters = _spoken_letters([str(c[0]) for c in choices]) if choices else ""
    ask = str(payload.get("ask") or "") or (
        f"Your call: {letters}?" if letters else "Your call"
    )
    return table(head, rows) + "\n\n" + _boxed_markdown(
        {
            "kind": "action",
            "ask": ask,
            "ask_kind": "choose" if choices else "answer",
        }
    )


def as_markdown(payload: dict) -> str:
    """The block as markdown, for a client that colours markdown and not ANSI."""
    kind = str(payload.get("kind", "")).strip().lower()
    if kind == "decision":
        return _md_decision(payload)
    if kind == "note":
        return _md_note(payload)
    if kind == "action":
        return _md_action(payload)
    if kind == "legend":
        return _md_legend()
    if kind == "roadmap":
        return _md_roadmap(list(payload.get("phases") or []), payload.get("title", "THE PLAN"))
    raise ValueError(
        f"Unknown block kind {kind!r}. "
        "Use one of: decision, note, action, legend, roadmap, banner."
    )


def render_from(payload: dict) -> str:
    """Build a block from a plain dict, so it can be printed by a command.

    **Why this exists.** Every render tool returned its block to the model,
    which retyped it into its reply. That reply is rendered as markdown, and
    markdown has no idea what an escape code is, so the colours were stripped
    on the last hop. They were correct at the source and invisible at the
    destination, which is the worst kind of wrong: every test passed.

    Printing through a command puts the block on the same channel as the
    banner, which is the one channel already known to reach a terminal intact.
    """
    kind = str(payload.get("kind", "")).strip().lower()

    # Where escape codes cannot arrive, the block goes inside a fence.
    #
    # **Loose markdown was the wrong trade.** It bought colour from the client's
    # renderer and lost the box, and the box is the thing: a decision has to
    # arrive as one object with a boundary, or it reads as the assistant
    # chatting (decision 035). Rendered as headings and quotes it sprawled down
    # the screen with nothing holding it together, which is worse than
    # monochrome.
    #
    # A fence keeps every column exactly where it was drawn: no reflow, no
    # markdown interpreting `---` as a rule or `*` as emphasis, and the client
    # draws its own container around it. The symbols and the frame carry the
    # meaning, which is what rule R11 has required from the start.
    if not _ON and kind != "banner":
        # **A plain fence. This is settled, and here is the whole search.**
        #
        # Six ways to put a coloured block on screen in Claude Code, each
        # verified against a real screenshot rather than reasoned about:
        #
        #   1. ANSI retyped into the reply     colour stripped by the renderer
        #   2. ANSI printed by a command       colour stripped, same reason
        #   3. a block printed by a command    never shown; tool output collapses
        #   4. loose markdown                  colour arrives, the box is lost
        #   5. an ```ansi fence                escape codes shown raw, unusable
        #   6. a plain fence                   the box, exactly as drawn
        #
        # Five of the six trade away either the box or the message. The box is
        # the one that was asked for first and asked for most, and rule R11 has
        # required from the beginning that colour is never the only signal
        # precisely so this case would cost nothing. The symbols and the frame
        # carry every meaning.
        #
        # `FORGE_ANSI_FENCE=1` restores attempt 5 for a client that interprets
        # those fences. Left in because the failure is per-client, not
        # universal, and someone else's terminal may do better than this one.
        if os.environ.get("FORGE_ANSI_FENCE"):
            was_on = _ON
            try:
                _apply_colour(True)
                drawn = _plain_block(payload).strip("\n")
            finally:
                _apply_colour(was_on)
            return "```ansi\n" + drawn + "\n```"

        # `FORGE_TABLE=1` renders it as a one-column table instead. That was
        # tried as the default and was worse in two ways this renderer decides
        # rather than the author: it draws a border after **every row**, so one
        # block arrives as a stack of boxes, and it prints `&nbsp;` literally,
        # so indentation came out as the entity itself. Kept because another
        # client may do both properly.
        if os.environ.get("FORGE_TABLE"):
            return _boxed_markdown(payload)

        # `FORGE_DIFF=1` gives the coloured version: a `diff` fence the client's
        # own highlight.js paints. It costs the drawn border and shows `@@`,
        # `+`, `-` and `#` in the text, because highlight.js anchors its line
        # tokens at column zero. A `│` in front of a marker makes it an ordinary
        # character, so the box and the colour cannot both be had. The markers
        # are the colour.
        if os.environ.get("FORGE_DIFF"):
            return _diff_block(payload)

        # `FORGE_NO_COLOUR=1` gives the drawn box with no markers at all, for a
        # client whose highlighter does not know `diff`.
        if os.environ.get("FORGE_NO_COLOUR"):
            return "```\n" + _plain_block(payload).strip("\n") + "\n```"

        # **Both, and the trick is that only column zero is anchored.** The
        # left border character is also the token that colours the line, so the
        # box is drawn and the client paints it. Nine earlier attempts each gave
        # up one of the two because they treated the marker and the border as
        # competing for the same column instead of as the same thing.
        return _coloured_box(payload)

    if kind == "legend":
        return legend()

    if kind == "banner":
        return banner(payload.get("project"), payload.get("version"))

    if kind == "roadmap":
        return roadmap(list(payload.get("phases") or []), payload.get("title", "THE PLAN"))

    if kind == "action":
        return action(
            str(payload.get("ask", "")),
            str(payload.get("hint", "")),
            kind=str(payload.get("ask_kind", "answer")),
        )

    if kind == "note":
        return note(
            str(payload.get("heading", "")),
            list(payload.get("lines") or []),
            symbol=str(payload.get("symbol", "")),
            ask=str(payload.get("ask", "")),
            important_lines=list(payload.get("important_lines") or []) or None,
        )

    if kind == "decision":
        recommend = payload.get("recommend")
        return decision(
            str(payload.get("title", "")),
            number=payload.get("number") or None,
            subtitle=str(payload.get("subtitle", "")),
            concept=str(payload.get("concept", "")),
            means=list(payload.get("means") or []) or None,
            choices=[tuple(c) for c in (payload.get("choices") or [])] or None,
            recommend=(tuple(recommend) if recommend else None),
            against=str(payload.get("against", "")),
            important_lines=list(payload.get("important_lines") or []) or None,
            done=int(payload.get("done") or 0),
            total=int(payload.get("total") or 0),
            stage=str(payload.get("stage", "")),
            ask=str(payload.get("ask", "")),
        )

    raise ValueError(
        f"Unknown block kind {kind!r}. "
        "Use one of: decision, note, action, legend, roadmap, banner."
    )


if __name__ == "__main__":  # pragma: no cover - CLI surface
    arg = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if arg == "banner":
        print(banner(sys.argv[2] if len(sys.argv) > 2 else None))
    elif arg == "legend":
        print(legend())
    elif arg == "render":
        # JSON on stdin, a coloured block on stdout. The whole point is that
        # the model never retypes it.
        import json as _json

        try:
            print(render_from(_json.loads(sys.stdin.read() or "{}")))
        except (ValueError, TypeError) as exc:
            print(note("That block could not be drawn", [str(exc)], symbol=BLOCKED))
            sys.exit(1)
    else:
        _demo()
