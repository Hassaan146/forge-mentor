---
description: Where this project stands, and what happens next
---

Show where the work is, without changing anything.

Steps:

1. Call `next_step` for the stage, the subagent, the model, and whether the next step needs the
   user. If it reports `needs_repair`, call `check_history` and show what is damaged and how to
   repair it — then stop; nothing else is worth reading until the notes are sound.
2. Call `current_state` for what is decided and what is open.
3. Call `usage_report` for tokens used so far. If it reports `available: false`, say usage is
   unavailable in one line and carry on — nothing else depends on it.
4. Call `check_history` to confirm the decision records are intact.

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
