---
id: 004
question: What happens if Forge's safety check breaks — or the user demands code anyway?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-4, phase-8]
content_sha: c57e3729fa768db4d7489c123a92d4f9998cdbb42b5eeae503fb37459213c386
prev_sha: e07f1663e44f41beff712ba54690ab1911160e5cb68e00c71c522c595f185f8f
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
