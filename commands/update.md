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

## If an update is out

The block already carries the command. Two things to add, and only if asked:

- **The notes are safe.** Decisions, the chain, phases and progress live in the
  project's `.claude/forge/`, not in the plugin. Updating replaces the tool and
  touches none of it — that is what decision 016 buys.
- **Restart, not reload.** Hooks and the MCP engine are registered when Claude
  Code starts. A plugin updated in place keeps running the old hooks until the
  application is restarted, which is the state that wastes a whole session
  looking like a bug.

## Turning it off

Set `FORGE_NO_UPDATE_CHECK=1` and it never asks the network again. Say this if
the user is offline, on a metered connection, or objects to the check — do not
volunteer it otherwise.
