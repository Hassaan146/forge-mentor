---
id: 079
question: What happens to a tool the product promises and no brief calls?
status: decided
date: 2026-08-15
decided_by: user
affects: phase-5, phase-8
content_sha: d0103679c8b46b28d1d191ecc47baffce1b89863785af9255bc95971677437e4
prev_sha: e903a148609550cbfc45e715a76fa9badba062c4e13985a99fe5b837e87ce45e
---

# They are wired into the briefs that should have called them, and a test now fails when a tool has no caller

**Options considered**

- Delete the unreachable tools: the tree gets smaller and the promises get quieter
- Wire the eight the product promises, keep six as deliberately uncalled, and guard the list with a test
- Leave them: they are tested and harmless

**Recommended:** Wire and guard - **Decided:** Wire and guard

## Why

A repo-wide ponytail audit found fifteen of forty-nine registered tools reachable from no command, agent brief or skill. Eight of them were not surplus at all: they were capabilities the README and the command files tell users they have. Setup never called install_skill_library, so the 46 MB library README lists as step 2 was never installed. explain_code and write_prompts_log generate the two documents the README promises and stop.md describes, and nothing generated them. preview_push and push_work implement the consent step and the secret scan behind "Forge asks before every push", while the loop pushed with plain git through Bash and went around both. status.md told a user their notes were damaged and never offered repair_history, which quarantines before it writes. mode.md documents auto as settling small things "and records them", and settle_small_decision, the thing that records them, was called by nothing. what_did_i_ask_for is the whole of decision 068.

Every one of them had passing tests. That is the point worth keeping: a test calls a tool directly, and a brief is the only thing that does not, so the suite was green on a surface a third larger than the behaviour. The guard reads commands, agents and skills, and fails naming any registered tool nothing calls. Six are listed as uncalled on purpose with the reason each needs no caller, so the exemption is a sentence somebody has to write rather than a silence.

## In their words

tell me what are the unwired things. ok so wire the unwired things
