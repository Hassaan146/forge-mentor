---
id: 038
question: When does the user see the shape of the whole project?
status: decided
date: 2026-08-09
decided_by: user
affects: phase-8, plan-accepted
content_sha: d0041541f0c9528018f298746471d8d02efee1a0d54a7fa1b54fd6d0f9fd5834
prev_sha: 04d45bc7f7059403484a9c24458ae50570e6c5960259e395ba32bde28de906b2
---

# All the phases, before any of them - and the plan is a gate, not a document

**Options considered**

- **A** - compile and reveal one phase at a time, as each becomes current
- **B** - compile every phase up front, show the whole plan, and block all writing until the
  user has accepted its shape
- **C** - compile all of them up front but show only the current one, keeping the rest in the
  files for whoever goes looking

## Why

**A is what shipped, and the user caught it.** Watching a real run, they were asked "how is
this project tested?" - a question whose answer applies to every phase - at a point where they
had been told about phase one only. Phase one had already been built. Their words: *"Why are we
moving with a phase-by-phase approach? First, you will make all the phase plans."*

The cost is not that the plan was wrong. It is that a decision with project-wide reach was made
without the project being visible. A user who could see four more phases coming would answer the
testing question differently, and would have said so about phase three before phase one was
written rather than after.

**C is A with better filing.** A plan that exists only in files nobody was shown is the state
`todo-test` was actually in: five phases described in prose in the progress file, no `phases/`
directory at all, and the first phase built. Being on disk is not being seen.

**B makes it a gate.** `compile_phases` writes all of them in one call. `show_roadmap` renders
the whole plan - the spine, every phase, what each delivers, which steps are built - and
regenerates a self-contained `roadmap.html` that opens from disk with no network and can be
sent to a mentor. Acceptance is recorded as a decision carrying `plan-accepted`, and
`writes_allowed` refuses everything until it exists.

Rule R13 applies to this the same as to the step gate: it is a fact about `.claude/forge/`, not
a paragraph in the planner's brief. The brief already said to show the plan.

## The order the gates now run in

1. an unreadable phase file - there is no showing a plan Forge cannot read
2. no phases compiled at all
3. the plan not yet accepted by the user
4. a phase with no step list
5. the current step with no recorded decision

Each one names itself in the block message, so a user who hits it is told which of the five it
is rather than "blocked".

## What a phase is

Something the user could use on its own. "Tick a todo off and delete it" is a phase; "the data
layer" is not, because nobody can use a data layer. Five is the usual number, and the roadmap is
the artefact that makes that judgement checkable by the person it is for.

Recorded as rule R14 in `design-rules.md`.

Related: [[037-what-is-the-unit-of-work-the-governor-gates-on-once-the-foun]] - [[036-does-every-forge-response-carry-a-taught-colour-system-and-d]]
