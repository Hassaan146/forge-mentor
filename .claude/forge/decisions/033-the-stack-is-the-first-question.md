---
id: 033
question: What does Forge ask first, and in what order?
status: decided
date: 2026-08-08
decided_by: user
affects: [phase-8]
content_sha: 551a147cb497ac227105eb5a6488a75bbe4db2e95f645ba5e9c2b162d90f18f7
prev_sha: 1773fc2094f2df602e5c61c0ca06b70c526cc095f8bba39ac38a26528922ffef
---
# The stack, in detail, before anything else

**Options considered**

- **A** — a fixed foundation sequence, the stack first
- **B** — let the planner choose an order per project
- **C** — the stack first, the rest chosen per project

**Recommended:** A · **Decided:** A

## Why the stack goes first

Every other foundation question is asked *inside* an answer to this one. "Where is the data
kept" means different things for a browser app, a Django service and a CLI. Asking storage
before the stack means asking a question whose options are not knowable yet — and the user
answers it anyway, because they are being asked.

Running it on a real project showed this: the second question put was "where are the todos
stored", offering `localStorage`, `IndexedDB` and a file. Reasonable options — but every one of
them assumes a browser, which nobody had established. The stack had been assumed rather than
decided, which is the precise failure Forge exists to prevent, occurring in Forge's own
opening move.

## Why it is one detailed question rather than three

Language, framework and runtime are not independent. Picking Python does not settle Django
against FastAPI, and picking a browser front end does not settle whether there is a server at
all — but asking them separately invites an answer to one that quietly rules out most answers
to the next. They are put together, with the combinations named as whole options, so what is
being chosen is a shape of project rather than three words.

It is the longest question Forge asks, and that is proportionate. Everything downstream is
built on top of it.

## The order after it

Fixed rather than chosen per project (option B declined), because a planner that picks the
order will sometimes pick badly and nobody will notice — a question skipped is invisible,
unlike a wrong answer.

1. **Stack** — language, framework, runtime
2. **Data** — what is stored, where it lives, what happens when it is lost
3. **People** — whether there are accounts, and how someone proves who they are
4. **Delivery** — where it runs and how it gets there
5. **Done** — what "finished" means for a step in this project

Each is skipped when the stack already answers it: a single-file script has no delivery
question worth asking, and Forge should not manufacture one to fill the sequence.

Related: [[009-what-counts-as-finished]] · [[030-the-three-modes]]
