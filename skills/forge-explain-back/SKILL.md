---
name: forge-explain-back
description: The gate at the end of a step — the user explains back what was built and why, before the step counts as finished. Use at the teach-back stage, after tests pass and the review is clean.
---

# Explaining it back

Decision 009: a step is finished when the tests pass, the review is clean, **and** the user can
say what was built and why. This skill is the third one.

It is reflective, not graded. Nobody fails. The point is to surface the gap while it is still
cheap to close, not to score anyone.

## When it fires

After the tests pass and the review is clean — never before. Asking someone to explain code
that is still broken teaches them the broken version.

## Scale it to the step

A one-line change gets one question. A phase that introduced authentication gets three or four.
A gate heavier than the work it guards trains the user to rush it.

## Ask about the decision, not the syntax

Wrong: "what does this function return?" — that is reading, and they can see it.

Right, in roughly this order:

1. **What did we choose, and what did we turn down?** ("We used a login service instead of
   building password handling ourselves.")
2. **Why, for this project?** This is the one that matters. A right answer for the wrong reason
   is the gap.
3. **What would have to change for the other option to win?** This is what separates a
   remembered answer from an understood one.

## Reading the answer

- **Solid** — say so in one line and move on. Do not congratulate at length.
- **Thin but right** — fill the gap in two sentences, no quiz.
- **Wrong or blank** — re-teach the concept from a different angle, then ask once more. Never
  the same words again; if they did not land the first time they will not land the second.

Three attempts, then stop and escalate: record what did not land in the decision record and
carry on. Decision 009's three-strike rule exists so a stuck user is not trapped by the gate
meant to help them.

## Never

- Never withhold working code as leverage. The code is already written and already theirs.
- Never make the user feel tested. "Say it back in your own words" beats "explain to me why".
- Never accept your own summary as their answer.
