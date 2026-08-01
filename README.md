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
| `mcp/` | The engine — model routing, cost control, review |
| `.forge/` | Your project's notes: the plan and every decision |

## Status

v0.1.0 — early. Built in the open as an Arbisoft Internship 2026 Phase 3 project.

## License

MIT
