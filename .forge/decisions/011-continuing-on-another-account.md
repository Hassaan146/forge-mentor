---
id: 011
question: How is history preserved when the user switches to another account?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-3, phase-8]
content_sha: 9335778c21510f4a2afdf76dd8a6c0d0ac34ed27cadec83229000a33b9a810fc
prev_sha: 9ddd447bf38296e5ab7d5606fa6fa1d7b3e49eca899448279dd1ac6754722421
---
# The repository is the memory — the chat is not

**The user's question:** *"I have Forge on one account, then I go to another account and want
to continue. How do I continue from there?"*

## What is lost, and what is kept

| Lost when you switch account | Kept |
|---|---|
| The Claude Code conversation transcript | Every decision record |
| Anything said only in chat | The plan and phase graph |
| Session-only context | Progress — what is done, what is next |
| | All code and commit history |

**The key point:** Forge does not need the conversation. It needs the *decisions*, and those
are files in the repository (decision 001), pushed on every step (decision 005).

## How continuing actually works

1. On the old account, work is committed and pushed as it happens — no separate "save".
2. On the new account, the user clones or pulls the repository.
3. They run `claude` and Forge reads `.forge/`.
4. Forge reports where things stand — *"Decision 7 of 12 done. Next: how people log in.
   Last step: rate limiting, tests passing, review clean."* — and continues.

Nothing is retyped. Nothing is re-explained.

## What this requires of the notes

For this to work, the notes must capture **in-flight state**, not only finished decisions.
If the user stops in the middle of question 7, the new session must know that question 7 was
asked, what options were on the table, and that no answer was given yet. Finished decisions
alone are not enough.

**Therefore the progress file must always hold:**

- the question currently open, with its options and the recommendation already given
- the step currently in progress and which gates it has passed
- anything Forge said it would do next

## Why this matters beyond convenience

This is what makes hitting a usage limit a non-event: switch account, pull, carry on. It also
makes Forge survivable — a lost machine, a crashed session, or a different computer are all
the same situation, and all recover the same way.

## Consequence accepted

Conversational nuance is lost across a switch. If something mattered, it belonged in a
decision record — which is the discipline Forge is teaching anyway.
