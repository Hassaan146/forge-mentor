# Forge Mentor

**Decide-then-code.** A Claude Code plugin that refuses to write load-bearing code
until you have made — and understood — the decision behind it.

Normally AI writes your code and quietly makes the architectural choices for you, so
you end up with something you can run but cannot explain. Forge Mentor inverts that:
for every load-bearing decision it teaches the concept, offers options with a
recommendation, waits for your call, records it, and only then writes the code.

A rule enforced in code — not a prompt — stops any write from moving past a decision
you have not made.

## Requirements

Nothing to deploy — Forge is a plugin, with no server and no hosted anything. But it does need
three things on each machine, and Claude Code does not install a plugin's Python dependencies
for you:

| | |
|---|---|
| **Python 3.12+** | the hooks and the engine are Python |
| **the `mcp` package** | `pip install "mcp>=2.0.0,<3"` — without it the engine cannot start |
| **git** | the decision history lives in your repository |

`gh auth login` is optional; it is only needed to read review findings.

**Terminal, desktop app, or IDE — same plugin.** Forge is a Claude Code plugin, so it runs
wherever Claude Code does. One thing differs outside a terminal: the hooks invoke a bare
`python`, and an app launched from a dock or Start menu does not always inherit the PATH your
shell has. The readiness check tests that exact command rather than the interpreter you happen
to have typed with, because those two can disagree and only the first one matters.

Forge uses six colours, one meaning each — amber is Forge talking, blue is teaching, green
means it worked, yellow means your turn, red means it stopped, purple names the AI doing the
work. `/forge:start` prints the key before it asks you anything, because a colour scheme
nobody was told about is one nobody can read.

Colour switches itself off when the output is not a terminal, or when `NO_COLOR` is set.
Nothing is lost — no state is ever signalled by colour alone, and the one thing you have to
answer sits in its own double-ruled frame, which reads the same in black and white.

`/forge:start` checks all of this first and prints the exact command for anything missing. You
can also run the check yourself at any time:

```
python "$CLAUDE_PLUGIN_ROOT/scripts/forge_preflight.py"
```

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
| **Records why** | Every decision becomes a file in `.claude/forge/`, committed with the code |
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
| `.claude/forge/` | Your project's notes: the plan, every decision, and the reviews |

Your project also gets two generated documents, both assembled from the decision records
rather than written afterwards:

- **`.claude/forge/code-explained.md`** — why the project is built the way it is, including the
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
using itself: every decision behind it is recorded in `.claude/forge/decisions/`, which is the
same format your project gets.

Known gap, stated plainly: Forge drives Claude Code, so it runs on Anthropic models only
(decision 027).

## License

MIT
