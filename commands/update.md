---
description: Check whether a newer Forge is available, and show how to get it
---

# /forge:update

Ask whether this copy of Forge is current, and say what to run if it is not.

Forge checks this once a day on its own and tells you when something is out. This
command is for when you want to ask now — usually right after someone has pushed
a fix you are waiting on.

## Run it

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/forge_update.py" --force
```

`--force` skips the once-a-day cache. Without it you would get this morning's
answer to a question you are asking because something changed this afternoon.

Print whatever it returns, exactly as it comes. **Silence means you are current** —
say so in one line rather than inventing a block, and do not describe the check
itself. Nobody asked how it works.

## Two different answers, and they are not interchangeable

**"An update is out."** A newer version exists on GitHub and is not on this
machine. Two commands, in this order, because the second one checks the local
catalogue and the first is what refreshes it:

```bash
claude plugin marketplace update forge-marketplace
```

```bash
claude plugin update forge@forge-marketplace
```

**"It is downloaded, this session is running the old one."** The update already
worked. Nothing needs downloading again, and running the update command a second
time will report success and change nothing, which is the loop that wastes an
afternoon. What is left is one restart.

Forge tells these two apart on its own and prints the right one, so show what
the command returns and do not improvise a third answer.

## Guiding the restart

Say these three things, in this order, and nothing else:

1. **Quit Claude Code completely and open it again.** Not `/clear`, not a new
   tab. Hooks, the MCP engine and the `/forge:*` commands are read once at
   startup, so a session keeps whatever it loaded however many times the plugin
   is updated underneath it.
2. **Nothing is lost.** Decisions, the chain, the phases and the open question
   all live in the project's `.claude/forge/`, committed with the code
   (decision 016). The plugin is the tool, not the work.
3. **How to pick it back up:** `/forge:status` after reopening. It reads the
   files and says which question is open and what happens next, so the thread is
   never held in the conversation.

If the user would rather finish what they are doing first, that is a reasonable
answer and the notice says so. Do not press it. An update that interrupts is an
update people learn to dismiss.

## Turning it off

Set `FORGE_NO_UPDATE_CHECK=1` and it never asks the network again. Say this if
the user is offline, on a metered connection, or objects to the check — do not
volunteer it otherwise.
