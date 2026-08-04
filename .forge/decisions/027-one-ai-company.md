---
id: 027
question: Does the second-provider requirement change the pipeline?
status: decided
date: 2026-08-04
decided_by: user
supersedes_open_half_of: 010
affects: [phase-6, phase-10]
---

# No. Forge is a Claude Code plugin, and it stays one

**Options considered**

- **A** — Anthropic only
- **B** — OpenRouter as an API-key fallback tier
- **C** — a direct second-party API key
- **D** — drive the local Codex CLI as a second subscription path

**Recommended:** B (previously) · **Decided:** A

## The reasoning that settled it

Forge is a Claude Code plugin. Its hooks are Claude Code hooks, its commands are Claude Code
commands, its subagents are Claude Code subagents, and the thing it governs is the Claude Code
runtime. A second model provider cannot be plugged into that — it has nowhere to attach. Adding
one would not make Forge multi-provider; it would bolt a second, unused pipeline onto a plugin
that can only drive the first.

Decision 010 left this open, to be revisited before submission. It is now closed: Anthropic
only, and the two-provider question does not reopen it.

## What this leaves unmet, stated plainly

The program asks for at least two providers and a live comparison in Phase 10. Under this
decision, neither is delivered by the product. That is a known, accepted gap, recorded here
rather than discovered at submission.

**If it has to be answered**, the cheapest route is a standalone benchmark script that sends one
prompt to a non-Anthropic model and prints the two answers side by side — enough to produce the
comparison artifact, touching no part of the pipeline. It is not built, and it is not planned.
It is written down so the option is one afternoon away rather than a redesign.

## Consequence accepted

Ranked extension goals that assumed other agent runtimes (Codex, Cursor) now depend on Forge
becoming runtime-agnostic first. That is a larger change than it looked when they were ranked,
and they should be read as post-v1 in the fullest sense.

Related: [[010-single-provider]] · [[002-which-ai-does-which-job]]
