---
id: 029
question: Which model actually runs a job — who decides at dispatch?
status: decided
date: 2026-08-04
decided_by: user
implements: 002
closes_open_half_of: 003
affects: [phase-7]
content_sha: 31daa09cba1a03123aa4344e1ccbaeb89b007b5fe6c0591d0c5ed5eb10807bc4
prev_sha: 27d3f060bc54e9e98355109b9095e9e177c3d3fa6e3569df36803da6502dbf1b
---
# The subagent declares it; the server answers what it should be

**Options considered**

- **A** — the subagent's own file declares the model; `choose_model` advises and logs
- **B** — the MCP server owns dispatch and configures the subagents
- **C** — subagent files only; drop `choose_model`

**Recommended:** A · **Decided:** A

## What was actually open

Decision 002 settled *which* model does *which* job — Fable 5 teaches and plans, Opus 4.8
writes and fixes, Haiku 4.5 structures. What it left open was where that assignment lives once
there is code, and by Phase 5 there were two candidates: `choose_model` in the MCP server, and
the `model:` field in each subagent's own file.

Two places holding the same fact is the problem, not either place.

## Why the subagent file wins

Claude Code reads the subagent's file when it dispatches. Whatever that file says is the model
that runs, regardless of what any server thinks. So if the two ever disagree, the server is the
one that is wrong — and it would be wrong *silently*, reporting one model in the "which AI is
working" indicator (F1) while another did the work. An indicator that can lie is worse than no
indicator.

So the declaration lives where dispatch reads it.

## What `choose_model` is for, then

Not dead — its job changes from deciding to answering:

- the ordered fallback list from decision 003, for when a plan does not include the first choice
- the reason a job maps to a model, which is what the teaching layer shows the user
- the source for the "which AI is working" line

A test asserts the two agree, so a change to one that is not made to the other fails rather than
drifts.

## The division of labour this settles

| | Owns |
|---|---|
| Subagents | which model runs a job |
| MCP server | review — merging both reviewers, writing the notes, reporting what is open |

The server is the engine for the things that must happen identically every time. Model dispatch
is not one of them, because Claude Code already does it.

Related: [[002-which-ai-does-which-job]] · [[003-changing-the-ai-mapping]] · [[025-two-reviewers-one-file]]
