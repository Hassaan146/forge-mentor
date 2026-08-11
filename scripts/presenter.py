"""Forge Mentor — the hook that will not let a question be asked as prose.

**Why this exists.** Rules R10 and R12 say a question is framed and short, and
both lived in `start.md` and the planner's brief. Rule R13 says that makes them
advice. It was right: a real run put a decision on screen as three paragraphs
of plain text with no frame around it, and nothing anywhere could tell.

The governor gates *writes*, which is a file path a hook can see. Nothing gated
*speech*, and speech is most of what Forge does. This closes that.

**How.** `Stop` fires when the assistant has finished its turn, and it carries
the transcript. So the last thing said can be read back and checked against the
one rule that matters: if a question is open, the user must be looking at a
frame. If they are not, the turn is refused and the assistant is told to render
it properly — the same shape of refusal the governor gives a bad write.

**It fails open, everywhere.** A governor that blocks a write costs a turn; a
presenter that wedges the session costs the session. Any unreadable transcript,
any unexpected shape, any error at all, and this allows. `stop_hook_active` is
honoured absolutely, so it can never ask twice in a row.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from forge_state import find_forge_dir, open_question, paused  # noqa: E402

# The frame characters. Any one of them means a block was rendered — the single
# rule and the double one both count, since a note, a decision and an action
# frame are all Forge speaking in its own shape.
FRAMES = frozenset("┌│└╔║╚")

# Unframed prose allowed alongside a question. Two lines is a lead-in; ten is
# the wall of text rule R10 exists to prevent, wearing a box at the bottom.
MAX_LOOSE_LINES = 6


def allow() -> None:
    print(json.dumps({}))
    sys.exit(0)


def block(reason: str) -> None:
    """Refuse the turn and say what to do instead.

    The reason is written to be acted on rather than apologised for: it names
    the tool, because "be more concise" is not a thing a model can reliably do
    and "call render_decision and print what it returns" is.
    """
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


# How a block reaches the terminal with its colour intact. A block returned to
# the model and retyped into its reply is rendered as markdown, and markdown
# does not know what an escape code is, so the colour died on the last hop.
# Printing it through this command puts it on the same channel as the banner.
RENDER_COMMAND = "forge_ui.py"

# Named once, in the shortest form that is still runnable. `start.md` carries
# the full payload shape and the assistant has already read it.
RENDER_HINT = 'python "$CLAUDE_PLUGIN_ROOT/scripts/forge_ui.py" render'


def rendered_by_command(transcript: Path) -> bool:
    """Did this turn print a block through the render command?

    A turn that did is framed, whatever its text says: the frame is on the
    user's screen, in colour, above whatever the assistant then wrote. Judging
    only the reply text would refuse the very path that fixed the colours.
    """
    try:
        lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False

    for line in reversed(lines[-200:]):
        try:
            entry = json.loads(line)
        except ValueError:
            continue

        content = (entry.get("message") or {}).get("content")

        # **A tool result is written as a `user` entry**, which is why this
        # found nothing. Breaking on `type == "user"` was meant to stop at the
        # turn boundary; it stopped at the result of the last tool call
        # instead, one line in, so the render command sitting just above it was
        # never seen. The user's own message is the one carrying no tool result.
        if entry.get("type") == "user" and not _is_tool_result(content):
            break

        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "tool_use":
                continue
            command = str((part.get("input") or {}).get("command", ""))
            if RENDER_COMMAND in command and " render" in command:
                return True
    return False


def _is_tool_result(content: object) -> bool:
    """Is this `user` entry a tool result rather than something a person typed?"""
    if not isinstance(content, list):
        return False
    return any(
        isinstance(part, dict) and part.get("type") == "tool_result" for part in content
    )


def last_assistant_text(transcript: Path) -> str:
    """The text of the most recent assistant turn, or "" if it cannot be read.

    The transcript is JSONL and its shape is the client's business, not ours —
    so every field is reached defensively and any surprise yields "", which
    allows the turn.
    """
    try:
        lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""

    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") != "assistant":
            continue

        content = (entry.get("message") or {}).get("content")
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return ""

        parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        text = "\n".join(p for p in parts if p)
        if text.strip():
            return text
        # An assistant entry carrying only tool calls is not the turn's speech;
        # keep looking back for the one that actually said something.
    return ""


# Forge speaking in markdown rather than in a box. Where escape codes cannot
# arrive, the block is handed to the client as markdown so the client colours
# it, and none of those lines carry a frame character. Looking only for the box
# would refuse the presentation that exists because the box could not be
# coloured.
#
# The eight symbols of decision 035, plus the bar. Matched on a heading rather
# than anywhere in the text, so a reply that merely mentions ⚒ in a sentence is
# not mistaken for a block. Listing specific headings was tried first and missed
# `render_note`, whose heading is whatever the note is called.
MARKS = "⚒💡⚖★⚠✅⛔→▌"


def _starts_the_block(line: str) -> bool:
    if any(char in FRAMES for char in line):
        return True
    return line.lstrip().startswith("#") and any(mark in line for mark in MARKS)


def is_framed(text: str) -> bool:
    return any(_starts_the_block(line) for line in text.splitlines())


def loose_lines(text: str) -> int:
    """Prose *before* the block, which is the lead-in rule R10 is about.

    Counted up to the block rather than across the whole reply. Everything
    after it is the block's own body, and in the markdown presentation that
    body is ordinary lines with no frame character in them, so counting the
    whole reply refused every question it was given.
    """
    lines = text.splitlines()
    for position, line in enumerate(lines):
        if _starts_the_block(line):
            return len([earlier for earlier in lines[:position] if earlier.strip()])
    return len([line for line in lines if line.strip()])


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        allow()

    if payload.get("hook_event_name") != "Stop":
        allow()

    # Absolute. This is what stops the hook asking twice for the same turn, and
    # a presenter that can loop is a presenter that ends the session.
    if payload.get("stop_hook_active"):
        allow()

    try:
        forge_dir = find_forge_dir(Path(payload.get("cwd") or "."))
        if forge_dir is None:
            allow()  # not a Forge project
        if paused(forge_dir):
            allow()  # switched off here; Forge has no opinion about the answer

        pending = open_question(forge_dir)
        if pending is None:
            allow()  # nothing is being asked, so nothing has to be framed

        transcript = payload.get("transcript_path")
        if not transcript:
            allow()

        # **Running the render command is no longer proof of anything.** Claude
        # Code collapses tool output into "ran 2 shell commands", so a block
        # printed that way never reaches the screen. Accepting it here let a
        # bare prose line through as question 3 of a real run while the block
        # sat invisible behind a summary line.
        #
        # The block has to be in the reply itself, which is also the only place
        # the client will colour it.

        said = last_assistant_text(Path(transcript))
        if not said.strip():
            allow()

        # Short, because the user reads this too. It is addressed to the
        # assistant, but Claude Code shows a Stop hook's reason on screen, so a
        # fourteen-line correction with a JSON example in it arrives looking
        # like the plugin has crashed. The detail belongs in `start.md`, which
        # the assistant has already read; this only has to name the fix.
        if not is_framed(said):
            block(
                "Put the block in your reply, not in a shell command. Tool output "
                "is collapsed to 'ran N shell commands' and the user never sees "
                "it. Call foundation_question or render_decision and paste the "
                "`block` it returns, verbatim, as your whole answer."
            )

        if loose_lines(said) > MAX_LOOSE_LINES:
            block(
                f"{loose_lines(said)} lines of prose around the block "
                f"(rule R10 allows {MAX_LOOSE_LINES}). Move the rest into the "
                "block or the decision record."
            )
    except Exception:
        # Never wedge a session over presentation. The governor can afford to
        # fail closed because a blocked write costs one turn; this cannot,
        # because a Stop hook that errors on every turn ends the conversation.
        allow()

    allow()


if __name__ == "__main__":
    main()
