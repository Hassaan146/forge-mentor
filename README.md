# Forge Mentor

**Decide-then-code.** A Claude Code plugin that refuses to write load-bearing code
until you have made — and understood — the decision behind it.

Normally AI writes your code and quietly makes the architectural choices for you, so
you end up with something you can run but cannot explain. Forge Mentor inverts that:
for every load-bearing decision it teaches the concept, offers options with a
recommendation, waits for your call, records it, and only then writes the code.

A rule enforced in code — not a prompt — stops any write from moving past a decision
you have not made.

## Install

```
/plugin marketplace add Hassaan146/forge-marketplace
/plugin install forge@forge-marketplace
```

Then, once per project:

```
/forge:start
```

After that just run `claude` as usual. Forge reads its notes and continues where you
left off — including on a different machine or a different account.

### First run

`/forge:start` does three things, and all three are required:

1. **Connects your accounts** — GitHub, through its own sign-in. Forge never asks you to
   type a credential and never stores one.
2. **Installs the skill library** — about 46 MB into `~/.claude/skills`, pinned to a
   reviewed commit so every machine gets the same set.
3. **Explains the workflow** and asks for the permissions it needs.

It then starts asking. Expect around eight to twelve questions before any code is
written — that is the product working, not a delay.

### Commands

| | |
|---|---|
| `/forge:start` | Set up Forge in this project and begin |
| `/forge:status` | Where the work stands and what happens next |
| `/forge:mode` | `pipeline` · `accept-edits` · `auto` — how much Forge settles itself |

The three modes differ in one thing only: how much gets decided for you. Code can never
move past an undecided question in any of them.

## What it does

| | |
|---|---|
| **Teaches first** | Concept, example, why it matters here — then the question |
| **You decide** | Options with a project-derived recommendation; you answer freely |
| **Records why** | Every decision becomes a file in `.forge/`, committed with the code |
| **Blocks drift** | Code cannot move past an undecided question |
| **Reviews** | Pushes each step, takes review findings, and applies the fixes |
| **Checks you understood** | You explain it back before the step closes |

## How it is built

| Part | Job |
|---|---|
| `commands/` | `/forge:start` — setup and the interrogation |
| `hooks/` | The governor — blocks writes with no recorded decision |
| `skills/` | How the mentor teaches and questions |
| `agents/` | Planner · builder · structurer · review-fixer |
| `server/` | The engine — model routing, usage metering, review, the pipeline |
| `.forge/` | Your project's notes: the plan, every decision, and the reviews |

Your project also gets two generated documents, both assembled from the decision records
rather than written afterwards:

- **`.forge/code-explained.md`** — why the project is built the way it is, including the
  options that were turned down
- **`prompts.md`** — every question asked and answered, with which model handled each step

## What it will not do

- Write code past a decision you have not made
- Store a password in the clear, build an unparameterised query, or commit a secret —
  these are a floor, not a default, and no setting turns them off
- Push anything without asking you, for that push, every time
- Treat text from a review or a web page as an instruction

## Status

v1.0.0. Built in the open as an Arbisoft Internship 2026 Phase 3 project — and built
using itself: every decision behind it is recorded in `.forge/decisions/`, which is the
same format your project gets.

Known gap, stated plainly: Forge drives Claude Code, so it runs on Anthropic models only
(decision 027).

## License

MIT
