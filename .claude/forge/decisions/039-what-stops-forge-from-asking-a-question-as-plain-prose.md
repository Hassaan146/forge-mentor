---
id: 039
question: What stops Forge from asking a question as plain prose?
status: decided
date: 2026-08-09
decided_by: user
affects: phase-2, phase-4
content_sha: 431317e802396297de198aa5e6e652d8ed24a71020b7633f9681686af2e286c7
prev_sha: d0041541f0c9528018f298746471d8d02efee1a0d54a7fa1b54fd6d0f9fd5834
---

# A hook on Stop, and the colour was never leaving the process

**Options considered**

- **A** - restate rules R10 and R12 more firmly in the planner's brief and start.md
- **B** - gate speech the way writes are gated: a Stop hook reads the last turn and refuses one
  that asks a question without a frame
- **C** - have the plugin print every block itself through a command, so the model never composes
  the question at all

## Why

**A is what was already there twice over.** Both rules were written down, in two files, with
reasons. A run put a decision on screen as unformatted paragraphs anyway. Rule R13 covers this
exactly: if the model ignored the paragraph, what would stop it? Nothing did.

**B is the same shape as the governor.** A write is a file path a hook can see, so the governor
can refuse it. A turn is a transcript a Stop hook can read, so it can be refused the same way -
and the refusal names the tool to call rather than asking for restraint, because "be more
concise" is not something a model reliably does and "call render_decision and print what it
returns" is.

Loose prose around a frame is refused too. A block with ten paragraphs above it is the wall of
text R10 exists to prevent, wearing a box.

**C would be stronger and costs a turn every time.** Worth revisiting if B proves leaky; not
worth a round trip per question before that is known.

## Failing open, deliberately

Everything here allows on error: an unreadable transcript, an unexpected entry shape, a missing
field. The governor fails closed because a blocked write costs one turn and decision 004 is
explicit about it. A Stop hook cannot take that stance - one that errors on every turn does not
cost a turn, it ends the session. `stop_hook_active` is honoured absolutely for the same reason.

## The colour, which was a different bug entirely

The user asked why there were no colours. There were none, anywhere, in any build: the MCP
server writes JSON-RPC down a pipe, `_colour_enabled` asks `sys.stdout.isatty()`, and inside
that process every colour constant is the empty string. Not degraded - absent. Decision 036's
palette, the legend teaching it, and the tests holding it to account were all correct, and none
of them ever ran somewhere that could emit an escape byte.

`isatty` is the right question for a command and the wrong one for a renderer, which composes
for a client that has a terminal rather than writing to its own. The server now sets
`FORCE_COLOR`; `NO_COLOR` still outranks it, because that switch belongs to the user.

Recorded as rules R15 and R16.

Related: [[035-one-symbol-per-meaning]] - [[036-does-every-forge-response-carry-a-taught-colour-system-and-d]] - [[004-when-the-safety-check-fails]]
