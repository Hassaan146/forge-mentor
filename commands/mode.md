---
description: Change how much Forge settles on its own — pipeline, accept-edits, or auto
argument-hint: "[pipeline|accept-edits|auto]"
---

Change the working mode for this project, or show the current one if no mode was given.

The three differ in exactly one thing — how much gets decided for you (decision 030):

- **pipeline** — asks about every decision that matters, and confirms each file before writing it
- **accept-edits** — asks the same questions, and writes without stopping to confirm
- **auto** — settles small things itself and records them; still asks about anything the rest of
  the work gets built on

What does *not* change: code can never move past a question that has not been answered, and the
explain-back gate still runs. A mode that turned those off would not be a faster Forge — it
would be plain Claude Code with a banner.

Requested mode: $1

Steps:

1. Call `next_step` to read where the project currently stands.
2. If `$1` is empty, print the current mode and what it means, and stop.
3. Otherwise call `set_mode` with it.
4. Confirm the change in one line, using the plain-language meaning rather than the mode's name
   (rule R1 — the name tells a non-technical user nothing).
5. If the new mode is `auto`, say plainly what Forge will now settle without asking, and what it
   will still stop for.
