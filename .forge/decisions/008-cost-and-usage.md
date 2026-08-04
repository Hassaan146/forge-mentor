---
id: 008
question: How much should it cost to run?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-2, phase-6]
content_sha: 259aec07eee04ba15288d44d56e19da1fb1a9afe8d33c6c81f9e57b25e3cd5dc
prev_sha: 87ab9ad681055310ee60d8b166359e3a833344238389f191cf84be88ec0d9210
---
# Show usage and warn along the way; a spending limit comes later

**Options considered**

- **A** — show usage, never interfere
- **B** — show usage and warn at points along the way
- **C** — warn, plus a spending limit the user sets

**Recommended:** B now, C later · **Decided:** B now, C later.

## Now (v1)

- The banner shows usage continuously.
- Forge warns plainly at roughly half, three-quarters, and nearly-full.
- Each warning reminds the user that the notes are portable — they can switch accounts and
  carry on without losing anything (decision 001).
- Warnings are stated once at each threshold, not repeated, so they inform rather than nag.

## Later (deferred, ranked extension)

A user-set spending limit that halts work when reached. Deferred because the main users are
on subscriptions, where the risk is hitting a wall mid-build rather than an unexpected bill.
The warning path plus account switching already solves that.

## Already handled elsewhere

Three earlier choices do most of the cost work and are not repeated here:

- Haiku 4.5 handles the job that runs constantly (decision 002).
- Fable 5 is reserved for teaching only, not for routine work (decision 002).
- Repeated parts of each request are reused rather than re-sent.

## Consequence accepted

A pay-as-you-go user has no hard cap in v1. Mitigation: the warnings are visible and
frequent enough to notice, and the spending limit is first in the deferred list — not a
vague "someday".
