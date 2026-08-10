---
description: Switch Forge off in this project, keeping every decision it recorded
---

# /forge:stop

Stop Forge acting in this project. The gates stop blocking, the questions stop
coming, and Claude Code goes back to being ordinary Claude Code here.

**Nothing is deleted.** Every decision, the chain, the phases and the progress
file stay exactly where they are. They are the project's own history and they
outlive the tool that produced them, which is the whole point of keeping them in
the repository rather than in a session (decision 016).

## How

Write `.claude/forge/paused.md` with the date and, if the user gave one, the
reason. That file existing is the whole mechanism: every hook checks for it
first and stands down.

A file rather than a setting, deliberately. Each hook has to answer "am I on"
before it does anything, and a file either exists or it does not: nothing to
parse, nothing that can be malformed, and no way for a damaged note to leave
somebody locked out of their own repository. It can also be created or deleted
by hand, and its presence is obvious in a directory listing.

Then say, in one framed block:

- Forge is off here, and what that means: no gates, no questions, no blocked
  writes.
- The records are untouched and still committed with the code.
- `/forge:start` turns it back on and picks up where it left off, because the
  state was never in the session.

## If they want it gone entirely

Deleting the notes is theirs to do, not yours. Say the command and let them run
it:

```bash
git rm -r --cached .claude/forge && rm -rf .claude/forge
```

Before you show that, say plainly what it costs: every recorded decision, the
reasoning behind it, the options that were turned down and the chain that proves
none of it was edited afterwards. That is the record that answers "why is this
built this way" in six months, and `prompts.md` and Code Explained are generated
from it. Removing the plugin does not require removing the record.

Never run it yourself, however clearly they ask. This is the one action in Forge
that destroys work, and the rule everywhere else in the product is that nothing
is destroyed: repair quarantines before it overwrites, and blocked writes are
refused rather than discarded.
