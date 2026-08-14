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

**Colour, honestly.** Forge has six, one meaning each: amber is Forge talking, blue is
teaching, green means it worked, yellow means your turn, red means it stopped, purple names
the AI doing the work. You will see them running Forge's own commands in a terminal.

**You will not see them inside Claude Code**, and that is not a bug in Forge. Everything the
plugin prints reaches you through the client, which renders it as markdown, and markdown has
no concept of an escape sequence. Forge detects this and stops emitting the codes rather than
sending colour that is stripped on arrival, because the leftovers made the legend print as
grey blocks.

Nothing is lost, because nothing was ever signalled by colour alone. Every block carries a
symbol and the words that say the same thing, and the one thing you have to answer sits in its
own double-ruled frame, which reads identically in black and white. `/forge:start` prints the
key for whichever set applies: the six colours where they render, the nine symbols where they
do not.

`NO_COLOR=1` turns it off anywhere. `FORCE_COLOR=1` turns it back on if you want to see for
yourself what your setup does with it.

`/forge:start` checks all of this first and prints the exact command for anything missing. You
can also run the check yourself at any time — and here too the command depends on where you
are typing.

Inside a Claude Code session, `$CLAUDE_PLUGIN_ROOT` is set for you:

```bash
python "$CLAUDE_PLUGIN_ROOT/scripts/forge_preflight.py"
```

In a normal terminal it is not set, so point at the installed copy directly:

```bash
python ~/.claude/plugins/cache/forge-marketplace/forge/*/scripts/forge_preflight.py
```

On Windows, that path is `%USERPROFILE%\.claude\plugins\cache\forge-marketplace\forge\`, with
a folder per installed version. If two versions are listed, the newest is the one running.

## Install

There are two sets of commands and they are not interchangeable. Which one you want
depends on where you are typing.

### Inside Claude Code — slash commands

If you are already in a Claude Code session and see a `>` prompt, use these:

```
/plugin marketplace add Hassaan146/forge-marketplace
```

```
/plugin install forge@forge-marketplace
```

Bare `/plugin` opens the panel, which is also where you **enable or disable** an
installed plugin. Worth knowing where that switch is: a disabled plugin is still
installed and still the right version, and it loads nothing at all, no hooks, no
engine, no `/forge:*` commands. It looks exactly like a plugin that is not working.

**Updating from a session is one command, not two:**

```
/plugin marketplace update forge-marketplace
```

Refreshing the marketplace downloads the new plugin with it. It reports
"1 plugin bumped", and the bump *is* the download.

**There is no `/plugin update <name>`.** Claude Code reads `/plugin` as the plugin
browser and opens it, arguments and all, so running it looks like nothing happened
while you stare at a list of every plugin in the catalogue. The slash commands do
not mirror the CLI one for one.

### In a normal terminal — the `claude` CLI

If you are at a shell prompt, outside any Claude Code session, the same operations are
subcommands of `claude`:

```bash
claude plugin marketplace add Hassaan146/forge-marketplace
```

```bash
claude plugin install forge@forge-marketplace
```

Updating here **is** two commands, in this order, because the second reads the
catalogue that the first refreshes:

```bash
claude plugin marketplace update forge-marketplace
```

```bash
claude plugin update forge@forge-marketplace
```

The CLI can do a few things the slash commands cannot, and these are the ones worth
having to hand:

| | |
|---|---|
| `claude plugin list` | every plugin, its version, and whether it is enabled |
| `claude plugin enable forge@forge-marketplace` | switch it on |
| `claude plugin disable forge@forge-marketplace` | switch it off without uninstalling |
| `claude plugin update forge@forge-marketplace` | fetch the newest version |
| `claude plugin uninstall forge@forge-marketplace` | remove it |

### Restart, don't reload

Hooks and the MCP engine are registered when Claude Code starts. A plugin installed,
updated or enabled mid-session keeps running the old configuration until you quit and
start again — which is the state that looks like a bug and costs a whole session. The
CLI says so itself: `claude plugin update --help` reads *"restart required to apply"*.

Check it took:

```bash
claude plugin list
```

You want `forge@forge-marketplace` showing the version you expect and `Status: ✔ loaded`.

### Updating

Forge tells you. It checks its own version against this repository once a day and prints
one frame with the command when there is something newer. The frame never stops what you
were doing: `/forge:start` shows it and then starts the project in the same turn, and the
restart keeps until it suits you. Ask on demand with `/forge:update`, and turn the whole
thing off with `FORGE_NO_UPDATE_CHECK=1`.

Your decisions are never at risk in an update — they live in your project's
`.claude/forge/`, not in the plugin.

### Then, once per project

```
/forge:start
```

After that just run `claude` as usual. Forge reads its notes and continues where you
left off — including on a different machine or a different account.

Coming back after a gap, `/forge:status` gives you the story so far and then carries straight
on: what the project is, how far in it is, what was decided lately, and either the question you
were on or the next piece of work. It does not stop at a report. If nothing is waiting on you,
the next move is Forge's and it takes it.

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
| `/forge:add` | Add a feature to a project that already works |
| `/forge:status` | Where the work stands and what happens next |
| `/forge:mode` | `pipeline` · `accept-edits` · `auto` — how much Forge settles itself |
| `/forge:update` | Check now whether a newer Forge is out, and how to get it |
| `/forge:stop` | Switch Forge off in this project, keeping every record |

The three modes differ in one thing only: how much gets decided for you. Code can never
move past an undecided question in any of them.

### Adding to something that already works

`/forge:add` is the path for the second version. It reads what is already recorded rather
than asking again: the foundation is on disk and still true, so what comes back is the
handful of decisions the new feature has to live inside, anything it wants that the project
already ruled out, and only the questions the feature itself owes. The phase is appended, so
nothing already built is rewritten.

If the feature contradicts a recorded decision, that is put to you rather than worked around.
Changing your mind is a new record naming the old one, never an edit of it.

### ponytail, which Forge requires

[ponytail](https://github.com/DietrichGebert/ponytail) (MIT, by Dietrich Gebert) gets an agent
to write the least code that works: check whether the thing needs writing, whether the project
already does it, whether the standard library does it, before adding anything.

```
/plugin install ponytail@forge-marketplace
```

It is listed in Forge's own marketplace, so there is no second marketplace to add. Forge routes
to it at the building and review steps, and **setup will not finish without it**: the output of
this tool is your codebase, and the thing keeping that code small is not an optional extra.

**Every step climbs the ladder before you are asked anything about it.** Does this need to exist
at all, does the project already do it, does the standard library do it, what is the smallest
version worth having, what the extra size costs. All five, and the answers are shown to you with
the question, so you are choosing a size rather than approving a plan. This one is enforced the
same way decisions are: the step stays shut until the pass is recorded, and a pass with a rung
missing is refused, because three plausible sentences with two rungs quietly absent reads as a
completed pass in every summary anybody will ever look at.

Where the two disagree Forge wins. The security floor is not overridable, and a recorded
decision is not optimised away because a shorter version exists.

If it is genuinely unavailable, `record_override` is the one way past, and it writes down that
the build ran without the check that keeps it small.

### When the code names something that is not there

Every import Forge writes is checked against your manifests, the standard library, and the
files that actually exist. Every "as decided in decision 014" is checked against the records.

Anything unaccounted for stops and asks you, because it is one of three things and only you
know which: a dependency that has to be added, a file about to be written, or something the
model invented. Forge does not quietly fix it, and it does not install a package to make the
guess true. `FORGE_NO_GROUNDING=1` turns the check off.

## Switching it off

`/forge:stop` stops Forge acting in a project: no gates, no questions, no blocked
writes. It writes one file, `.claude/forge/paused.md`, and every hook stands down
when it sees it.

Nothing is deleted. The decisions, the chain and the phases are the project's own
history and stay committed with the code, so `/forge:start` resumes rather than
restarts. Deleting the record is a separate, manual choice, and Forge will not
make it for you.

## What it does

| | |
|---|---|
| **Teaches first** | Concept, example, why it matters here — then the question |
| **You decide** | Options with a project-derived recommendation; you answer freely |
| **Records why** | Every decision becomes a file in `.claude/forge/`, committed with the code |
| **Blocks drift** | Code cannot move past an undecided question |
| **Announces itself** | Every step says what it writes before it writes it |
| **Leaves it running** | The step ends with the thing started and an address you can open |
| **Reviews** | Pushes each step, takes review findings, and applies the fixes |
| **Checks you understood** | You explain it back before the step closes |

## What a step looks like

A phase is never built in one pass. It is a list of steps, and each step is one question, one
piece of code, and exactly two blocks on your screen.

**First the plan.** Before a single file is written, Forge says in plain words what the step
does and names every file it will touch, in the order it will write them. Skeleton first: the
file that is the shape of the thing before the file that fills it in. This is a gate, not a
courtesy. The governor refuses every write until it has happened, so there is no version of a
step where code appears and the explanation follows.

**Then silence.** The files are written one at a time, and each one is recorded with what it
is, why it exists and how it works before the next is allowed. That goes to the record, not to
your screen. A paragraph a file turns a three-file step into a wall of prose with the blocks
lost inside it.

**Then the result.** One block: every file on one line, what was run to prove it works, and
the address it is already serving on. Forge starts it for you and hands you a live URL rather
than instructions to produce one, and it says what the command means part by part, because a
command nobody explained is the first thing you need on the day Forge is not in the room.

Every load-bearing idea in the code is named in plain words as it is written. Forge writes the
code; the concepts are yours to keep.

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

v1.26.1. Built in the open as an Arbisoft Internship 2026 Phase 3 project, and built using
itself: the 75 decisions behind it are recorded in `.claude/forge/decisions/`, in the same
format your project gets, each one fingerprinted against the one before it.

Known gap, stated plainly: Forge drives Claude Code, so it runs on Anthropic models only
(decision 027).

## License

MIT
