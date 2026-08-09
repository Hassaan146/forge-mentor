---
id: 031
question: What does "clean" mean when a finding is about code that has changed?
status: decided
date: 2026-08-04
decided_by: user
implements: 009
affects: [phase-9]
content_sha: 7222fdf6183c39818931c576d517790e4253a19d6e0e653cf552bb482988d9ae
prev_sha: ca96e31a19bc8a5f1805db0058c1f3377d4cdb7a2a239673649221049b87dde8
---
# Separate what is stale from what is open, and close threads deliberately

**Options considered**

- **A** — resolve the thread on GitHub as part of the fix loop
- **B** — judge each finding against the current file and mark superseded ones
- **C** — count only findings raised against the current head commit

**Recommended:** A and B together · **Decided:** A and B together

> Drafted by Forge because Phase 9 could not proceed without an answer, then **put to the
> user and confirmed** — it changes what decision 009 gates on, which is load-bearing and
> not Forge's to settle alone.

## The problem, found by running the loop rather than by thinking about it

Decision 009 says a step is finished when the review is clean, and `is_clean` was computed
from unresolved review comments. Both pull requests reached the state where **every finding was
fixed in code or declined with reasoning, and both still reported open findings.**

A reviewer does not retract a comment when the code beneath it changes. So the count measures
"comments nobody has clicked resolve on", not "problems that remain" — and a phase gated on it
can never close by fixing things.

## Why not C

Tempting and wrong. A finding raised two commits ago is not stale *because* it is old — most of
this project's real bugs were reported against an earlier commit and were still entirely valid.
Dropping them on age alone would discard exactly the findings the review exists to surface.

## What is actually knowable

GitHub gives `original_commit_id` — the commit a finding was raised against. It does **not**
give a reliable "outdated" flag: `commit_id` is rewritten to follow the pull request head, and
`position` stays set. So the honest signal is narrow, and stated as narrowly as it is true:

> If the file has not changed between the commit the finding was raised against and the current
> head, the finding still applies exactly as written.

The converse is not true. A changed file does **not** mean the finding is addressed — it means
nobody can tell from metadata alone. So a finding whose file has moved is marked **stale**,
which means *needs a look*, never *resolved*.

## The two counts

| | Meaning |
|---|---|
| `open` | raised against code that has not moved since — applies as written |
| `stale` | the file changed underneath it — a person or the review-fixer must judge it |

Decision 009's bar becomes: no open findings, and every stale one either fixed or declined with
a reason. `clean` stays a single answer, which was the point of decision 025.

## Closing the loop for real

Marking is not enough on its own, or the file fills with stale entries forever and the pull
request still shows unresolved threads to a human. So the fix loop also **resolves the thread on
GitHub** once a finding is handled — the same act a reviewer performs by hand, through
`resolveReviewThread`.

Resolving is deliberate and never automatic on a guess. Forge resolves a thread only when it
has applied a fix or recorded a decline, because a thread closed without either is a finding
silently dropped — which is worse than a count that reads too high.

## Consequence accepted

Forge now writes to the pull request conversation, not only to files. That is a new kind of
outward action and it needs the same consent rule as pushing (decision 005): it happens on the
user's say-so, per fix, and never as a background tidy-up.

Related: [[009-what-counts-as-finished]] · [[025-two-reviewers-one-file]] · [[005-review-and-push]]
