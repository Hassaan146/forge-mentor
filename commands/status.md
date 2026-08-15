---
description: Where this project stands, and what happens next
---

Show where the work is, and carry on from it.

**Start with `catch_up`.** It returns two blocks: the story so far, and whatever comes next.
Paste them in that order and stop. That is the whole reply on the common path, which is
somebody reopening after a gap and needing to know where they were.

**Unless there is no second block.** An empty `next_block` does not mean there is nothing to do,
it means nothing is waiting on the *user* — the step is decided and the next move is Forge's. Do
not stop there. Carry straight on in the same turn: `current_step`, then `plan_files`, then
build it. This ended a real session on the line "No question is open; nothing is blocking you",
which reads as a finished report and is actually a loop that forgot to take its turn. Follow the
`next` field that `catch_up` returns; it says which of the two endings applies.

The summary is assembled from the records every time rather than kept in a log, so there is no
second version of the history to drift from the first (decision 011: the repository is the
memory). It carries the idea in the user's own words, how many questions are answered against
the estimate, how many decisions are recorded, phases finished, steps built, which step is open
now, and the last three decisions with what was chosen.

If it reports `needs_repair`, call `check_history`, show what is damaged, and **offer
`repair_history`**, which is the tool that fixes it: it quarantines the damaged records before
it writes anything, so nothing is destroyed and the original is still on disk afterwards. Say
that, then ask, then run it if they say yes. Telling somebody their notes are broken and
naming no repair is the shape of an error message, not of a product. Nothing else on this
screen is worth reading until the notes are sound.

**If the user asks whether they ever asked for something** — "did I say I wanted dark mode",
"what did I ask about the database" — call `what_did_i_ask_for` with their words. It searches
the records and returns what they asked, when, and what was decided. Answering from memory
here is guessing about the one thing this product exists to have written down.

Everything below is the longer report, for when the user asks for more than a glance.

Steps:

1. Call `next_step` for the stage, the subagent, the model, and whether the next step needs the
   user.
2. Call `current_state` for what is decided and what is open.
3. Call `usage_report` for tokens used so far. If it reports `available: false`, say usage is
   unavailable in one line and carry on — nothing else depends on it.
4. Call `check_history` to confirm the decision records are intact.

Then check the version — a status report from a plugin that is two weeks behind
describes a project state that may already have moved:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/forge_update.py"
```

It prints nothing when the copy is current. Print what it returns, add nothing.

Then print, using the Forge visual identity:

- the banner, then the progress bar with the count of questions answered against the estimate
  (rule R4 — always show how many remain)
- the current stage in plain words, and what happens next
- the open question, if there is one, and that code is blocked until it is answered — put the
  question itself through `render_action`, because it is the one thing on this screen the user
  can do something about, and everything around it is a report
- which model does the next step and why (rule R2 — name it: "Fable 5", not "the teaching model")
- usage, and any threshold warning
- anything the review still has open

Keep it short. This is a glance, not a report.
