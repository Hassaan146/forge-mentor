---
id: 030
question: What actually differs between the three modes?
status: decided
date: 2026-08-04
decided_by: user
affects: [phase-8]
---

# How much gets decided for you — and nothing else

**Options considered**

- **A** — the modes differ only in how many decisions Forge makes on its own
- **B** — as A, and Auto also skips the explain-back gate
- **C** — two modes; drop Auto

**Recommended:** A · **Decided:** A

## The three

| Mode | Asks | Writes |
|---|---|---|
| **Pipeline** (default) | every load-bearing decision | after each decision is recorded, confirming each file |
| **Accept Edits** | every load-bearing decision | without stopping to confirm each file |
| **Auto** | only blast-radius decisions | furniture-level choices made by Forge and recorded as decision records |

"Furniture" is a choice that can be changed later without touching anything else — a helper's
name, where a small function lives. "Blast radius" is a choice other work will be built on top
of: the stack, the schema, how people log in, how errors surface. Auto never decides one of
those; it decides the furniture and writes down what it decided.

## What does not change between modes

**The governor rule.** In all three, code cannot move past a decision that has not been
recorded. Auto changes *who answers* a question, never *whether it was answered*. A mode that
turned the rule off would not be a faster Forge, it would be plain Claude Code with a banner.

**The explain-back gate**, which is why option B was declined. Decision 009 makes explaining it
back part of what finishing means, and that gate is the entire teaching claim. Skipping it to
save time makes Auto a different product rather than a quicker one. A user who does not want to
be taught does not need Forge at all.

## Why Auto stays

Option C would have made Phase 8 smaller. Rejected: Auto is in the approved proposal, and
cutting it is a conversation with the supervisor rather than a quiet simplification.

## Consequence accepted

Auto produces decision records nobody chose, which dilutes the record as evidence of what the
*user* understands. Mitigation: records written by Auto say so in their `decided_by` field, so
the two are never confused when reading back — and the explain-back gate still applies to the
code that results.

Related: [[009-what-counts-as-finished]] · [[004-when-the-safety-check-fails]]
