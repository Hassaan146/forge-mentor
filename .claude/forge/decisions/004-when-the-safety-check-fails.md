---
id: 004
question: What happens if Forge's safety check breaks — or the user demands code anyway?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-4, phase-8]
content_sha: 99a3fa353414864e26dc3fca586165ae53afd8ad410b4152ad5ddec396172181
prev_sha: bb86fc9d6da1a5f180209d327afa04e7c61a9f3ee5e07d2f7797e68ed730b519
---
# Blocked by default; an explicit command plus confirmation is the only way through

**Options considered**

- **A** — stop everything, no way through
- **B** — warn and carry on
- **C** — stop by default, with a deliberate recorded way out

**Recommended:** C · **Decided:** C, refined.

## How it behaves

**Default:** code cannot be written until the current decision is recorded. This holds
both in normal use and when Forge's own safety check fails.

**The only way through** is an explicit instruction from the user — the user must
directly command that the code be written anyway. Chatting around it does not work; the
request has to be deliberate.

**Then Forge asks for confirmation:** *"Are you really sure? No decision has been recorded
for this yet, so you will not have a record of why this was built this way."* The user
confirms, the code is written, and the override is written into the notes.

## The point of the confirmation

The confirmation is **not a rubber stamp**. Its purpose is not to have shown a warning —
it is to make the user stop and actually decide. If it becomes a reflex people click
through, it has failed. It must state the specific thing being lost, not a generic
caution.

## Why

The guarantee is the product. If it can disappear quietly, it was never a guarantee. But
locking someone out of their own project because of a bug in Forge is not acceptable
either. An explicit command plus a specific confirmation keeps the promise real while
leaving the human in charge.

## Consequence accepted

A way out can become a habit. Mitigation: every override is recorded in the notes and
counted, so a user who is bypassing constantly can see it — and so can the teach-back
step.
