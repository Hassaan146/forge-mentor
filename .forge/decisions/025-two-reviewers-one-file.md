---
id: 025
question: How do two reviewers share one set of notes?
status: decided
date: 2026-08-04
decided_by: user
implements: 005
affects: [phase-6]
---

# Both reviewers, one file per pull request

**Options considered**

- **A** — one file per pull request, both reviewers merged, each finding tagged
- **B** — one file per reviewer per pull request
- **C** — merged, but only CodeRabbit's findings count toward "done"

**Recommended:** A · **Decided:** A

## Why a second reviewer at all

They do not find the same things. On pull request #1 Sourcery caught the governor comparing
path *substrings* — `"/.forge/"` did not match a relative `.forge/decisions/001.md`, so Forge
could have been blocked from recording the very decision that unblocks the user. CodeRabbit's
three findings on the same pull request were different ones.

The split is consistent with what each tool is:

| | CodeRabbit | Sourcery |
|---|---|---|
| Built as | an AI pull-request reviewer | a Python refactoring engine that later added review |
| Pulls on | security, bug risk, data integrity, config and docs drift | complexity, duplication, simplification, test quality |
| Steerable | yes — per-path instructions | mostly not |

This codebase is two thousand lines of Python. Sourcery's lens is the one that gets sharper
the more Python there is, and it is not the lens CodeRabbit brings.

## Why one file and not two

Decision 009 says a step is not finished until the review is clean. That has to stay a single
question with a single answer. Option B makes "is this clean?" require reading two files and
reconciling them, and the reconciliation has no home — it would end up in the model's head,
differently each time.

So: `.forge/reviews/pr-<n>.md` holds both. Every finding carries the name of the reviewer that
raised it, and the header lists which reviewers were read. Findings sort by severity across
both, not grouped by tool, because urgency matters more than authorship when deciding what to
fix first.

## Why not option C

C would have let phases close faster by treating Sourcery as advisory. Rejected on the
evidence above: the advisory reviewer is the one that found the bug in the product's core
guarantee. A bar that excludes it is not a bar.

## What this changes in the code

The reviewer name stops being a constant and becomes a table, and severity is read per
reviewer — CodeRabbit writes a badge (`Security & Privacy | Critical`), Sourcery writes a
prefix (`**issue (bug_risk):**`), and the category and the severity sit in opposite positions
in the two formats.

**Where findings actually live, checked rather than assumed.** The first draft of this record
said Sourcery posts most of its findings in the review body, and planned to read both the body
and the inline comments. Pull request #1 says otherwise:

| | inline comments | review body |
|---|---|---|
| CodeRabbit | 3 — the findings | 4.8k walkthrough, no findings |
| Sourcery | 7 — the findings | 14.4k, **repeating all 7** plus overall feedback |

Sourcery's body duplicates every inline comment under an "Individual Comments" heading. Reading
both would have counted every Sourcery finding twice, and a doubled count feeding decision 009's
"is it clean" bar is worse than a missing one.

So: **findings come from inline comments only.** The body is kept as a summary, not as findings,
and the one thing it holds that the inline comments do not — Sourcery's "Overall Comments" — is
extracted and shown as high-level feedback rather than as items to tick off.

## Consequence accepted

Two reviewers means more findings, and phases close more slowly. That is the point of the bar,
not a side effect of it. If the volume becomes unmanageable, the answer is per-path instructions
narrowing where each reviewer looks — not dropping one.

Related: [[005-review-and-push]] · [[009-what-counts-as-finished]] · [[026-who-writes-the-review-file]]
