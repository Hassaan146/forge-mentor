---
id: 010
question: Does Forge need a second AI company, or is Anthropic-only correct?
status: decided
date: 2026-07-31
decided_by: user
overrides: challenge-001 finding C1
affects: [phase-5, phase-10, submission]
risk: open
---

# Anthropic-only for the pipeline — user decision, with one requirement still unmet

**Challenge C1 said:** every model chosen is Anthropic, so the project uses one provider,
while the program requires two or more with a live same-query comparison.

**User's position:** Forge is a Claude Code plugin. It runs inside Claude Code, which is
Anthropic. Adding another company's model to the working pipeline adds complexity for no
product benefit.

**Decision:** the pipeline stays Anthropic-only. Fable 5 teaches, Opus 4.8 writes, Haiku 4.5
tidies.

## This is architecturally sound

The main loop lives inside Claude Code, so its models are Anthropic by definition. Forcing a
different company's model into the teaching or building path would be complexity chasing a
checkbox, not a better product.

## The requirement it does not satisfy — still open

The program's non-negotiable is **two or more LLM providers with a live same-query
comparison**. Three Anthropic models is one provider. That requirement is currently unmet.

**Cheapest path to compliance, if wanted later:** the comparison is a *single feature*, not
a pipeline change. The MCP server is ordinary Python and can call any provider. One
second-opinion command sends the same question to Claude and to one non-Anthropic model and
shows both answers side by side. It touches nothing else, and it demonstrates the
requirement live in the presentation.

**Status:** left open deliberately. The user will address this in the presentation. Revisit
before submission — see the checklist in `PROJECT_PLAN.md` §8.
