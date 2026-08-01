---
id: 001
question: How does Forge save project notes?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-3, phase-4, phase-5]
---

# Both notes readable by people and by Claude

**Options considered**

- **A** — both as readable documents
- **B** — both in a strict computer format
- **C** — mixed: strict progress note, readable decision notes

**Recommended:** C
**Decided:** A, refined — both files are readable documents with a strict labelled
section at the top (this file is an example of the format).

## Why

The user must be able to read either file himself. And when usage runs out on one
account and he switches to another, a brand-new session with no memory of the project
must be able to read these files and carry on. Nothing hidden, nothing tied to one
session or one account.

## Consequence accepted

A hand-edit can introduce a mistake that confuses the tool.

**Mitigation:** the labelled top section is checked whenever a file is read. If it does
not match what is expected, Forge says exactly what is wrong and how to fix it, instead
of guessing or silently continuing.

## Requirement this surfaced

**Account portability.** The notes must be complete enough that a fresh session on a
different account can continue without asking the user to repeat anything. This also
answers the "ran out of usage mid-build" risk: switch accounts, keep going.
