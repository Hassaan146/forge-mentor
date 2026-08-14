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


def _building(forge_dir: Path) -> bool:
    """Is there a step being worked on right now?

    Imported here rather than at the top: the step layer reads the state layer,
    and this hook has to survive a project whose phases are unreadable. Any
    trouble at all is False, which allows the turn, because presentation is
    never worth a wedged session.
    """
    try:
        import forge_steps as stp

        return stp.current(forge_dir) is not None
    except Exception:
        return False


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


def _is_tool_result(content: object) -> bool:
    """Is this `user` entry a tool result rather than something a person typed?"""
    if not isinstance(content, list):
        return False
    return any(
        isinstance(part, dict) and part.get("type") == "tool_result" for part in content
    )


def last_assistant_text(transcript: Path) -> str:
    """Everything the assistant said this turn, or "" if it cannot be read.

    **Everything, not the last thing.** A build is one turn with a dozen tool
    calls in it, and the assistant speaks between them: a box, then a
    paragraph, then another box, then six lines about a port. Reading only the
    final text part saw the last of those and judged the turn on it, which is
    how a screen full of prose passed a hook whose whole job is prose.

    The transcript is JSONL and its shape is the client's business, not ours —
    so every field is reached defensively and any surprise yields "", which
    allows the turn.
    """
    try:
        lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""

    said: list[str] = []
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue

        # A real user message ends the turn. Tool results arrive as `user`
        # entries too, and stopping at those would cut the turn at its first
        # tool call, which is where the speech starts.
        if entry.get("type") == "user":
            if _is_tool_result((entry.get("message") or {}).get("content")):
                continue
            break

        if entry.get("type") != "assistant":
            continue

        content = (entry.get("message") or {}).get("content")
        if isinstance(content, str):
            said.append(content)
            continue
        if not isinstance(content, list):
            continue

        parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        text = "\n".join(p for p in parts if p)
        if text.strip():
            said.append(text)
        # An assistant entry carrying only tool calls said nothing; keep going.

    return "\n".join(reversed(said))


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
    """Is this the line where Forge's own block begins?

    Four shapes, because the block is drawn to suit the destination and the
    hook has to recognise every one of them:

      * a frame character, in a terminal that takes escape codes
      * `@@ … @@`, the rule of a `diff` fence, which is what the client's own
        highlighter colours
      * a symbol on a markdown heading
      * a symbol in a table row

    Each new presentation has had to be added here, and twice it was forgotten
    and refused every question the render tools produced. The check has to be
    updated in the same breath as the drawing, which is the lesson of decision
    045 and the reason this list is spelled out rather than inferred.
    """
    if any(char in FRAMES for char in line):
        return True

    stripped = line.lstrip()
    if stripped.startswith("@@") and any(mark in line for mark in MARKS):
        return True

    # `+`, `-` and `|` are the ASCII border of the coloured box, where the left
    # edge doubles as the token that colours the line. Missing them refused
    # `render_note` and `render_action` outright, because their only framed
    # lines start with `+`. Caught by cross-checking against the real output of
    # every tool, which is the third time that check has earned its place.
    return stripped[:1] in {"#", "|", "+", "-"} and any(mark in line for mark in MARKS)


def is_framed(text: str) -> bool:
    return any(_starts_the_block(line) for line in text.splitlines())


# A fenced block is how a block reaches a client that cannot take escape codes,
# and it is what the user is looking at today. Where fences are present they
# draw an exact line: inside is Forge's block, outside is the assistant talking.
FENCE = "```"


def loose_lines(text: str) -> int:
    """Prose around the blocks, counted the way this reply is actually drawn.

    **Fenced**, which is every reply the current renderer produces: everything
    outside a fence is the assistant. That covers the lead-in *and* the wall
    after the last box, which is what a build put on screen with two perfectly
    good frames sitting in the middle of it.

    **Unfenced**, the older markdown presentation: the block's own body is
    ordinary lines with nothing to mark them, so only the lead-in can be
    counted. Counting the rest refused every question drawn that way, twice,
    both times by tightening this check without asking what the other
    presentation looks like.
    """
    lines = text.splitlines()
    if any(line.lstrip().startswith(FENCE) for line in lines):
        inside = False
        loose = 0
        for line in lines:
            if line.lstrip().startswith(FENCE):
                inside = not inside
            elif line.strip() and not inside and not _starts_the_block(line):
                loose += 1
        return loose

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

        # **A question is not the only thing that has to be framed, and
        # believing it was is how a build reached a user as a wall of prose.**
        # This allowed every turn where nothing was open, which is the whole of
        # a build: three paragraphs of file explanation, six lines of narration
        # about ports, and the two boxes lost somewhere inside it. Their words:
        # "only the box info should be displayed". So a step in progress counts
        # as Forge speaking, exactly like a question does.
        pending = open_question(forge_dir)
        if pending is None and not _building(forge_dir):
            allow()

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

        loose = loose_lines(said)
        if loose > MAX_LOOSE_LINES:
            block(
                f"{loose} lines of prose around the blocks (rule R10 allows "
                f"{MAX_LOOSE_LINES}). Forge speaks in blocks: put it in the one "
                "the tool returned, or in the record, and say nothing between "
                "them about what you are doing."
            )
    except Exception:
        # Never wedge a session over presentation. The governor can afford to
        # fail closed because a blocked write costs one turn; this cannot,
        # because a Stop hook that errors on every turn ends the conversation.
        allow()

    allow()


if __name__ == "__main__":
    main()
