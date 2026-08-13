---
id: 056
question: What happens when someone adds a feature to a project Forge has already built?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: b4783aaf728c6206d95523ee270b6e26f9ba04ede15b6c1abdca004012f8bd52
prev_sha: 6d0cf71283cff9fff88de6ed4f2af9868cec395e37afb63bd7388a13b3e6228d
---

# A feature reads the recorded decisions it lives inside, is asked only what it owes that is not already answered, and is appended as a new phase

**Options considered**

- Nothing. The gates open once the last phase is built (what shipped)
- Run the whole interrogation again for the new feature
- Read what is recorded, ask only what the feature owes, and append a phase
- Treat it as a new project in the same repository

**Recommended:** Read what is recorded, ask only what the feature owes · **Decided:** A feature reads the recorded decisions it lives inside, is asked only what it owes that is not already answered, and is appended as a new phase

## Why

Every gate reads the phase list, so once the last phase was built `next_gap` found no unbuilt step and opened. Someone coming back a month later to add one thing got no questions at all, which is the worst moment to have no rules: a new feature is written against a codebase full of decisions nobody is re-reading. `plan_feature` returns three things and nothing else, the decisions the feature is built inside as ids and one-line choices, anything it wants that the project has ruled out, and the subject questions it still owes. The foundation is never asked again: it is on disk and still true, and re-asking it spends a new project's tokens to learn what was already written down. Phases are appended by `add_phase` rather than recompiled, because rewriting the list puts finished work through a new pen and can mark built steps unbuilt.

## In their words

I want you to have an incremental approach. If, after the first version, you want to add a feature, there are fewer tokens and the product is token-efficient. By adding one feature we are not disturbing the other feature.
