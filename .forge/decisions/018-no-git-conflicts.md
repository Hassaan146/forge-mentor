---
id: 018
question: How do we stop the notes from causing git conflicts?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-3, phase-4]
---

# Questions become files when asked, not when answered

**Problem.** `progress.md` was rewritten on every step, so two branches always
collided on the same lines. Decision files, written once each, almost never collide.

**Decided:** a question becomes a decision file the moment it is *asked*, carrying
`status: open`. When answered, the same file flips to `status: decided`.

**Therefore `open_question` is no longer stored — it is computed.** Any decision file
with `status: open` is the open question. The governor looks for one instead of reading
a mutable field two branches fight over.

| Situation | Result |
|---|---|
| Two branches ask different questions | Different files — no conflict |
| Two branches answer the same question | Same file — conflicts, and should |
| `progress.md` conflicts | Delete and regenerate; never hand-merged |
| Duplicate ID taken on two branches | The later one renumbers at merge |

`progress.md` becomes a generated summary for humans, not a source of truth.
