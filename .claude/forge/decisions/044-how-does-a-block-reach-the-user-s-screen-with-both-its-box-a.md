---
id: 044
question: How does a block reach the user's screen with both its box and its colour?
status: decided
date: 2026-08-11
decided_by: user
affects: phase-2
content_sha: 0805dea0c4cc9b045dbc0b57cc8142272f7d8832edde6b9875855dda7e8404c3
prev_sha: 4da213ea3d1209ee61cae5026901040e42cb8cf0d704721d29d909b73976c4d4
---

# A table, so the client draws the border and colours the contents

**Options considered, and every one was tried against a real screen**

| | what was tried | box | colour |
|---|---|---|---|
| 1 | ANSI codes retyped into the reply | yes | stripped by the markdown renderer |
| 2 | ANSI codes printed by a shell command | yes | stripped, same reason |
| 3 | a drawn block printed by a shell command | yes | never shown; tool output collapses |
| 4 | loose markdown headings and quotes | lost | arrives |
| 5 | a plain ``` fence | yes | lost |
| 6 | an ```ansi fence | yes | codes printed raw |
| 7 | **a one-column markdown table** | **drawn by the client** | **arrives** |

## Why the first six failed

Attempts 1, 2 and 5 all end the same way: the client renders markdown, and markdown has no
concept of an escape sequence. Where the codes went did not matter.

Attempt 3 failed differently and was the worst of them, because it looked like it worked.
Claude Code collapses tool output into "ran 2 shell commands", so the block was rendered and
never seen. The guardrail had been taught to accept "the render command ran" as proof the
question was framed, so it certified a screen the user was not looking at.

Attempt 4 bought the colour by giving up the boundary, which was the thing asked for first and
asked for most. A decision has to arrive as one object or it reads as the assistant talking,
which is decision 035.

Attempt 6 was the closest reasoned guess and still wrong: this client prints the escape codes
rather than acting on them.

## Why the seventh works

A table is markdown the client both colours *and* draws a border around. Every other
arrangement made the box and the colour fight, because one came from characters Forge drew and
the other from styling the client applied. Here they come from the same place.

`FORGE_PLAIN_FENCE=1` gives the drawn box with no colour, and `FORGE_ANSI_FENCE=1` restores
attempt 6, because these failures are per-client rather than universal and someone else's
terminal may do better.

## The lesson, which cost seven rounds

Every one of these was a guess about what a renderer would do, and every one could have been
settled by looking. The ones that took longest were not the wrong guesses but the wrong
*checks*: a guardrail that certified a collapsed tool result, and a frame test that looked for
box characters in a presentation that has none. **When output looks wrong, verify what the
destination actually renders before changing how it is drawn, and verify that the check
recognises what the code now produces.**

The second half of that is new and is the expensive one. Both the presenter fixes in this
sequence were the check disagreeing with the code, not the code being wrong.

Related: [[035-one-symbol-per-meaning]] - [[036-does-every-forge-response-carry-a-taught-colour-system-and-d]] - [[039-what-stops-forge-from-asking-a-question-as-plain-prose]]
