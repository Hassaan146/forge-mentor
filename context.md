# Context

Everything you need to pick this project up cold. Written for a new session, a
new machine, or someone who is not me.

The short version: **Forge Mentor is a Claude Code plugin that refuses to write
load-bearing code until you have made — and understood — the decision behind
it.** The decision is the lesson. A user who cannot say why their app is built
a certain way does not own it, however well it runs.

---

## Where things are

| | |
|---|---|
| **Default branch** | `merge` — not `main`. All ten phases live here. |
| `main` | Phase 2 only, frozen. Kept as history; nothing targets it. |
| `phase-3` … `phase-10` | Eight branches, all fast-forwarded to `merge`. Their pull requests (#1–#8) are now historical — the per-phase split has been superseded and they show near-identical diffs. |
| **Marketplace** | `Hassaan146/forge-marketplace` follows this repo's default branch, so an install gets `merge`. |
| **Project notes** | `.claude/forge/` — decisions, chain, reviews, phases (decision 032). |
| `prompts.md` | Project root, generated. A programme deliverable, so it stays where a reader looks. |

Working copy: `H:\Skills\Project\forge-mentor`.
Planning documents (proposal, plan, mockups) sit one level up in `H:\Skills\Project`.

---

## How it works

Four moving parts, and the split between them matters.

**Hooks** (`scripts/governor.py`, `safety.py`, `gates.py`) are the guarantees.
They run as subprocesses, are **standard-library only**, and never depend on
anything being installed. The governor blocks writes; safety blocks secret reads
and quotes outside text as data; gates hold the commit until tests pass.

**The MCP server** (`server/forge_server.py`) is the engine — 26 tools for
recording decisions, reading reviews, metering usage, planning the pipeline.
Registered tools must be defined *above* `server.run()`, which blocks; anything
below it is silently never registered.

**Skills** (`skills/`) are four instruction files bundled in the plugin: the
teaching voice, the coding standards, the security floor, the explain-back gate.
They are the product. The wider library is installed separately at setup.

**Subagents** (`agents/`) split the work across models — planner on Fable 5,
builder on Opus 4.8, structurer on Haiku 4.5, review-fixer on Opus 4.8. The
subagent file is authoritative, because Claude Code reads it at dispatch.

---

## The rules that are actually enforced

Not aspirations. Each is code, with a test.

1. **No write past an unanswered question.** Including the six foundation
   questions — a fresh project blocks until all of them are recorded. This was
   broken for most of the build: the rule only covered the window between asking
   and answering, so a brand-new project allowed everything.
2. **Secret files are never read**, by any spelling. `cat`, `sed`, `python -c`,
   a symlink with a harmless name.
3. **Outside text is data.** Review findings arrive wrapped, and the wrapper
   cannot be closed from inside.
4. **Nothing is pushed without asking**, per push, every time.
5. **Nothing is destroyed.** Repair quarantines before it overwrites.

---

## The question order, and why it is fixed

`scripts/forge_foundation.py`, decision 033.

1. **What's the idea?** — open, no options
2. **What are you building this with?** — the stack, in detail
3. **What is stored, and what happens if it is lost?**
4. **Is there more than one person using this?**
5. **Where does this run when you are not running it?**
6. **What does 'finished' mean for a step?**

The idea comes first because every later question is asked *inside* it. The
stack comes next because "where is the data kept" means different things for a
browser app and a Django service — and asking storage first is how a real run
ended up offering `localStorage` to a project that had never chosen a browser.

The order is fixed in code rather than chosen by the planner, because a planner
that picks its own order will sometimes pick badly and **nobody will notice** —
a skipped question is invisible in a way a wrong answer is not.

---

## Recurring failure, worth internalising

The same bug happened four times in different clothes: **the rule was in the
code, and the code was not in the path.**

- `server.run()` sat above the review tools, so they never registered — while
  tests passed, because a test imports the module rather than running it.
- The governor only blocked between asking and answering, so a fresh project
  allowed everything.
- The fixed question sequence existed and was tested, but `start.md` never
  called it, so the planner improvised its own questions.
- `EXCLUDED_FROM_HASH` was defined and never read.

When adding a guarantee, the question is not "is it implemented" but "what
calls it, and would I notice if nothing did".

Two related traps:

- **Tests that cannot fail.** Several shipped: a trailing `or True`, a colour
  test that asserted nothing on a real terminal, an encoding test that never
  handed its stream to the code under test. If a test passes with the feature
  deleted, it is decoration.
- **Escapes through shell heredocs.** Writing Python via `<<'PY'` repeatedly
  turned `\n` into real newlines and `\b` into a literal backspace byte — the
  latter silently disabled every redaction pattern while looking correct in
  every editor and diff. Use the Write tool for code containing escapes.

---

## Running it

```bash
pip install "mcp>=2.0.0,<3"
```

```
/plugin marketplace add Hassaan146/forge-marketplace
/plugin install forge@forge-marketplace
```

Then per project: `/forge:start`, and afterwards `/forge:status`, `/forge:mode`.

Check a machine before installing anything:

```bash
python scripts/forge_preflight.py
```

Tests:

```bash
python -m pytest
```

534 tests, ~88% coverage, no model calls anywhere in the suite.

---

## State, honestly

**Built:** all ten phases. 534 tests. The governor, safety hooks, gates, state
layer with a verified hash chain (34 records), MCP engine, skills, subagents,
the pipeline with three modes, usage metering, two-reviewer integration,
opt-in push, `prompts.md` and Code Explained generation.

**Not done:**

- **The ≥2-provider requirement is unmet.** Decision 027 chose Anthropic-only
  because Forge drives Claude Code and a second provider has nowhere to attach.
  The Phase 10 live-comparison deliverable is therefore also unmet. Recorded,
  not discovered late — but a mentor may push back, and the cheapest answer is a
  standalone benchmark script that touches no part of the pipeline.
- **The live file-by-file build ticker.** `forge_build.py` is designed —
  skeleton-first ordering per stack, one file at a time, each announced as it is
  written — and was interrupted mid-write. Not committed.
- **Presentation, demo video, reflection document.**

**Known friction:** the installed plugin on the author's machine has lagged the
working copy repeatedly, which produces confusing sessions — old hooks blocking
work that the current code allows. Update the marketplace before testing.

---

## Reading order for the records

`.claude/forge/decisions/` holds 34, oldest first. The load-bearing ones:

| | |
|---|---|
| 002 | which model does which job |
| 004 | fail closed, and how an override is recorded |
| 009 | what "finished" means |
| 011 | the repository is the memory |
| 027 | Anthropic only, and the gap that leaves |
| 031 | what "clean" means when a finding is out of date |
| 032 | where the notes live in someone's project |
| 033 | the question order |
| 034 | when the governor blocks |
| 035 | one symbol per meaning |
| 036 | six colours with a key the user is taught, and a frame of its own for the ask |
| 037 | the governor gates on the build step, not the phase |
| 038 | the whole plan is shown, and accepted, before any of it is built |

`.claude/forge/code-explained.md` is the generated version of all of them, and
`prompts.md` is every question and answer, assembled from the records rather
than remembered.
