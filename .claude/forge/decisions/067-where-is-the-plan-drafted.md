---
id: 067
question: Where is the plan drafted?
status: decided
date: 2026-08-14
decided_by: user
affects: 
content_sha: d96d783ff798927f2e5f012315583d1c74533dd7caca539d0a82261ce43c4e19
prev_sha: b59bcbd7efacd1d2647315bc23162c6e8035f1af402627df451369d918d503d7
---

# The planner enters Claude Code's plan mode before drafting the phases and stays in it until the user accepts, running ponytail's ladder over the plan while there

**Options considered**

- In the ordinary conversation, as it is now
- In Claude Code's plan mode, from the first draft until the user accepts
- In plan mode only for the first plan, not for added features
- In a file the user edits directly

**Recommended:** In plan mode, until they accept · **Decided:** The planner enters Claude Code's plan mode before drafting the phases and stays in it until the user accepts, running ponytail's ladder over the plan while there

## Why

Plan mode is the one state where the client itself refuses to let anything be written, so the plan is drafted somewhere the code cannot start early. Forge's governor already blocks the write, and this means the question never arises. Running the ladder over the phases while in it is the cheapest deletion in the whole build: a phase that exists because plans usually have one, or one whose deliverable the project already has, costs nothing to remove now and a great deal to notice in week three. Recorded with its limit stated: nothing in Forge can put the client into plan mode, so unlike the gates this one depends on the planner following it. It is an instruction, and instructions in this project have a history of being skipped.

## In their words

Whenever I propose my plan to my plugin, it should use the Claude plan mode specifically to make the plan. If there is any requirement of ponytail there to ask questions in the plans, I'll review the plan.
