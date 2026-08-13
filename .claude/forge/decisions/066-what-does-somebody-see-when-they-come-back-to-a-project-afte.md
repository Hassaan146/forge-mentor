---
id: 066
question: What does somebody see when they come back to a project after a gap?
status: decided
date: 2026-08-14
decided_by: user
affects: 
content_sha: b59bcbd7efacd1d2647315bc23162c6e8035f1af402627df451369d918d503d7
prev_sha: a410e08d990600e889729bdf87c26c0dc97f0d151c838f5a1f62b853dee72917
---

# `catch_up` returns two blocks: where you left off, assembled from the records, and then the open question or next step

**Options considered**

- The open question on its own, as resume already gives
- A summary box assembled from the records, then the thing they were on
- A session log written at the end of each session and replayed
- The full status report every time

**Recommended:** A summary box, then the thing they were on · **Decided:** `catch_up` returns two blocks: where you left off, assembled from the records, and then the open question or next step

## Why

Reopening after a gap was answered with the open question and nothing around it, which tells somebody what to do and not what they were doing. The box carries the idea in their own words, questions answered against the estimate, decisions recorded, phases finished, steps built, which step is open, and the last three decisions with what was chosen. A session log was rejected: it would be a second version of a history the records already hold, and two records of the same thing is one record that is wrong. Assembling it on every call means deleting a decision changes the summary, which is the property that keeps it honest. The next block is `resume`'s, reused rather than rebuilt, because two ways of drawing the same open question is two ways for them to differ.

## In their words

When we exit Claude Code it should have something so that when we hit forge status again it continues to the next question or phase, and gives a brief summary of all of the previous work, in a box.
