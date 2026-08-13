---
id: 053
question: What does a subject owe the user before code touching it is written?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: ad219a2be2e753527be84699e0a72b9cc4d4743e455c5318d096e4392db39c29
prev_sha: b55001ec7e6fa454b4f95ddf22ccb2235054864fad85b8e6b030ee1ba5e74fb4
---

# Each subject carries the questions it owes, they are asked the first time a step touches it, and the step is blocked until they are recorded

**Options considered**

- Nothing fixed. The planner asks what it thinks of at the time (what shipped)
- One question per step, whatever the step is about
- A written list per subject, asked once per project, held by the governor
- Every question up front, before any code at all

**Recommended:** A written list per subject, held by the governor · **Decided:** Each subject carries the questions it owes, they are asked the first time a step touches it, and the step is blocked until they are recorded

## Why

The foundation asked twelve questions and then stopped. Everything after it was written by the planner in the moment, so a step called 'store the todos' could be asked one question or none worth the name, and the database was chosen by whichever model was writing that turn. `scripts/forge_topics.py` now holds eight subjects and the twenty questions they owe: the database owes which one, where it runs, how the shape changes once there is real data in it, how the code talks to it, and what a test opens; deployment owes how many pieces have to run, what starts and restarts them, and what happens in the five minutes after a bad release. Asked once per project by whichever step needs them first, because 'which database' is a project question that a step is merely the first to need, and asking it again at step nine would be the failure this product exists to prevent, performed by the product. The gate is in `next_gap`, not in a brief: every rule this repository put in a brief was eventually skipped by a model in a hurry, and a skipped question is invisible in a way a wrong answer is not.

## In their words

You have to ask the user questions at each step of what we are integrating so that the user's mind does not move towards a slop. He doesn't only rely on giving prompts.
