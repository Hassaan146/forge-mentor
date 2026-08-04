---
id: 013
question: What does "live session" mean in practice, and what is actually achievable?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-2, phase-5, phase-8]
supersedes_detail_in: R7
content_sha: 580e06589ca9ed66fcb1744dafa487b7628d8ff8d783d00f0b6ec5495a664ac1
prev_sha: ecb78913b881e15eb9e6c97872131c8b34b5343030c30db71131c9af2f699626
---
# One answer triggers a continuous stream, not a round trip

**The user's point:** the interrogation as practised so far is static — a question is asked,
an answer is given, the exchange ends, and the next question is a fresh start. Forge must
feel live: Claude working in the background, communication running continuously.

## What "live" means here

**One user input opens a continuous sequence.** The user answers, presses Enter, and without
any further input from them the session visibly:

1. reacts to the answer — agreeing, or disagreeing and saying why (R8)
2. writes the decision record to disk
3. updates the progress file
4. commits and pushes (decision 005)
5. runs whatever checks apply
6. streams the next question into view

All of it visible as it happens, in one unbroken flow. The user never submits and waits for
a wall of text to appear at the end.

## Honest limit

Claude Code is turn-based underneath: a session acts when the user sends something. Forge
cannot push new activity into an idle terminal with no user input at all.

**What this does not prevent:** everything above happens inside a single turn, streamed. The
long-running MCP server persists between turns and holds work in progress. Hooks fire on
their own without being asked. So the *experience* is continuous even though the protocol is
turn-based.

**The design consequence:** never split what should feel like one moment across several user
turns. One answer → one continuous streamed sequence ending at the next question. Asking the
user to press Enter again just to advance the pipeline is a design failure.

## What must be built for this

- Streamed output rather than a single block at the end of the turn.
- Visible state changes as they happen — file written, pushed, check passed — not summarised
  afterwards.
- A live indicator of which AI is working (already in the visual design).
- The next question composed and shown in the same turn as the previous answer's processing.

## Consequence accepted

A single turn does more work and takes longer. Mitigation: because it is streamed, the user
sees continuous progress rather than a frozen screen — which is the entire point.
