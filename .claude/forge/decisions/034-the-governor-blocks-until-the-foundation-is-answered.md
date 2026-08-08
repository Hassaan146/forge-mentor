---
id: 034
question: When exactly does the governor block a write?
status: decided
date: 2026-08-08
decided_by: user
implements: 004
affects: [phase-3, phase-8]
content_sha: d9a595cfd775e2fcfd2e3a67f84678120cb95bab721cb1fc6d39d610e2174f09
prev_sha: 551a147cb497ac227105eb5a6488a75bbe4db2e95f645ba5e9c2b162d90f18f7
---
# Until the foundation is answered, not merely between asking and answering

**Options considered**

- **A** — block whenever a foundation question is unanswered
- **B** — block only while a question is open, as before
- **C** — block on the first write and let the user opt out

**Recommended:** A · **Decided:** A

## The hole

The rule was "is a question open" — the state between Forge asking and the user answering. On
a brand-new project nothing has been asked, so nothing is open, so writes were allowed.

Which means: install Forge, say "put it in this file", and it writes the file. No decision
exists, none is required, and the plugin reports itself as working the entire time. The
product's one guarantee was only ever enforced in the narrow window after it had already
started doing its job.

That is not a missing feature. It is the guarantee being absent in exactly the case it was
sold for — the first thing a new user does.

## The rule now

A write is allowed when **every foundation question has a recorded decision** and none is
open. Before that, the governor denies and names the question it is waiting on, so the block
explains itself rather than looking like a fault.

Reads are never blocked, and Forge can always write its own notes — both unchanged, and both
still necessary, or answering a question would be impossible while blocked.

## What this costs

Six questions before the first line of code, on every project. That is the product working,
not a delay — but it is a real cost and it is chosen deliberately rather than stumbled into.
The override from decision 004 still exists for someone who genuinely needs through, and it is
still recorded when used.

Option C was declined for the same reason the original hole existed: a guarantee that asks
permission to apply is a default, and a default is not a guarantee.

Related: [[004-when-the-safety-check-fails]] · [[033-the-stack-is-the-first-question]]
