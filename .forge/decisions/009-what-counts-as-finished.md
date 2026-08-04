---
id: 009
question: What counts as "finished" for each step?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-4, phase-8]
content_sha: d4f607887290e879e1650cf079a420d11eb2d2f64ee566fa5fc5be13727d323c
prev_sha: 259aec07eee04ba15288d44d56e19da1fb1a9afe8d33c6c81f9e57b25e3cd5dc
---
# Tests pass, review clean, and you can explain it back

**Options considered**

- **A** — the tests pass
- **B** — tests pass and the review is clean
- **C** — tests pass, review clean, and the user explains it back

**Recommended:** C with two conditions · **Decided:** C

## The three gates

1. **Tests pass.**
2. **Review is clean** — CodeRabbit findings resolved (decision 005).
3. **Explain-back** — the user says in their own words why it was built this way.

## Condition 1 — the explain-back is reflective, never graded

No pass, no fail, no wrong answers. The user says what they understood; if something
important is missing, Forge fills the gap and moves on. The moment it becomes a test that
can be failed, people resent it and type nonsense to get past it — which destroys the
only thing it was there to measure.

## Condition 2 — the bar scales with the size of the step

| Step type | Gates applied |
|---|---|
| Routine / small (a rename, a tidy-up) | tests only |
| Load-bearing — came from a real decision | all three |

Without this, the user would be explaining back a renamed variable, and the ceremony
would destroy the live pace required by rule R7.

## Loop protection

If a step fails its checks **three times**, Forge stops looping and escalates to the user
instead of grinding. This prevents a stubborn review finding from trapping a learner in an
endless fix–push–fail cycle. Carried forward from the original proposal.

## Why

The project's thesis is *the decision is the lesson*. If a step can be marked finished
while the person still does not understand it, the product has failed at its one job.
The two conditions keep the bar real while keeping it light in feel — consistent with the
live pace (R7) and warn-don't-block (decision 004).

## Consequence accepted

Three gates on every load-bearing step is real ceremony and the slowest of the three
options. Accepted because understanding is the product; the scaling rule keeps it from
applying where it would only add friction.
