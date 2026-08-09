---
id: 037
question: What is the unit of work the governor gates on, once the foundation is answered?
status: decided
date: 2026-08-09
decided_by: user
affects: phase-8, phase-9
content_sha: 04d45bc7f7059403484a9c24458ae50570e6c5960259e395ba32bde28de906b2
prev_sha: 7d4ab2884cd547fccb1b260b7f6f653be69a0ec75bbf9110aeabfb6ed5c39beb
---

# The step, not the phase — and a phase with no step list cannot be built

**Options considered**

- **A** - leave the gate where decision 034 put it: the foundation is answered, so code may be
  written
- **B** - gate on the current build step: a phase must be broken into steps, and each step must
  have its own recorded decision before its code
- **C** - tell the planner in its instructions to ask before each step, and leave the gate alone

## Why

**C is what was already there, and it is what failed.** The interactive loop was described in
the planner's brief and in `start.md`. A description is a suggestion. On a real run against a
to-do app, Forge asked its foundation questions, wrote a progress file describing five phases
in prose, compiled no phase files at all, and then produced `index.html`, `style.css`, `db.js`
and `app.js` in one turn. Nothing was asked after the last foundation question. Every write was
permitted, and the product looked like it was working the whole time.

**A is the bug, stated as a rule.** Decision 034 closed a real hole - a fresh project allowed
writes because no question was open - by adding "and the foundation must be answered". Both
conditions are true exactly once, at the start. After the sixth answer `writes_allowed` returned
True and had nothing left to check, ever. The foundation says what is being built. It does not
say what the next file is, and nobody had been asked.

**B puts the loop in the files.** A phase is not a unit of work; it is a list of them. A phase
file carries its own step list, a step is decided when a decision record names it in `affects`,
and the write gate reads both. Three refusals follow, in order: no phases compiled, a phase with
no step list, a current step with no decision. The gate opens for exactly one step at a time and
closes again when it is ticked off.

## What one step is

One thing the user could see or test working, small enough that there is a real choice inside it
and large enough to be worth teaching. "Save a typed todo to the browser's storage" is a step.
"Write db.js" is a file, and a file is not a decision. Three to seven per phase.

## What this deliberately does not do

The governor sees a file path, not an intention. Once the current step is decided, writes stay
allowed until it is ticked - so a builder that ignores its brief can still write more than the
step asked for. What it cannot do is build a phase nobody was asked about, which is the failure
that actually happened. Perfect per-write attribution is not available to a hook that only knows
a filename, and pretending otherwise would be the same mistake as trusting the prompt.

The loop stalls if `step_built` is never called: the current step stays current and no new
question is asked. That is the right failure. The alternative is a loop that advances on a
model's say-so, which is the thing being removed.

Recorded as rule R13 in `design-rules.md`.

Related: [[034-the-governor-blocks-until-the-foundation-is-answered]] - [[033-the-stack-is-the-first-question]] - [[030-the-three-modes]]
