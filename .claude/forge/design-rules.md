---
type: design-rules
source: user feedback during foundation interrogation
status: living
updated: 2026-07-31
---

# Design rules learned from the user

Rules discovered while running Forge's own interrogation. Each came from real feedback,
not from planning. These become part of Forge's shipped behaviour.

## R1 — Speak plain language by default

**Came from:** user feedback after Question 1.
**Rule:** users may be technical or non-technical. Teaching text avoids jargon
("blast radius", "hooks", "server", "sub-agents", "state", "resume"). Explain in ordinary
words, use everyday comparisons, and only use a technical term after the user's own
answers show they want that level.
**Applies to:** the teaching skill bundled in Phase 7; every question Forge asks.

## R2 — Elaborate; name real specifics, not categories

**Came from:** user feedback after Question 2 — *"in C you have to tell Fable for
thinking, Opus for writing."*
**Rule:** an option is not explained until it is concrete. Never say "best-fit AI per
job" — say which AI, for which job, and why. The same applies to any recommendation:
name the actual thing being chosen.
**Applies to:** every option list Forge presents.

## R3 — State must survive an account switch

**Came from:** user's answer to Question 1.
**Rule:** the notes must be complete enough that a fresh session, on a different account,
with no memory of the project, can read them and carry on. No hidden state, nothing tied
to one session or account.
**Applies to:** the note format (Phase 3) and the safety checks (Phase 4). Also answers
the "ran out of usage mid-build" risk.

## R4 — Show progress through the questions

**Came from:** user feedback — *"tell the user how many questions there will be."*
**Rule:** before the first question, tell the user roughly how many to expect and list
what is coming. Show progress as it goes ("2 of about 8"). Say clearly that the number
can move depending on their answers.
**Applies to:** the interrogation loop (Phase 8).

## R5 — Forge must look and feel different from plain Claude Code

**Came from:** user feature request during Question 2.
**Rule:** when the plugin is active, the user should see it. A distinct visual identity —
a banner when a project starts, coloured output, a consistent prefix on Forge's messages,
clearly framed questions, and a visible progress indicator — so it is obvious a plugin is
running and not ordinary Claude Code.
**Applies to:** the plugin shell (Phase 2), applied across every phase after it.

## R7 — It must feel like a live session, not a form

**Came from:** user feedback during Question 5.
**Rule:** the loop is continuous and interactive. The user answers, presses Enter, and
Forge visibly *thinks*, responds, and moves to the next question in the same beat — while
updating its memory, its files and its record at the same time. It never feels like
submitting a form and waiting. The session is always alive and always current.
**Applies to:** the pipeline (Phase 8) and the visual layer (Phase 2).

## R8 — Forge is allowed to disagree with the user

**Came from:** user feedback — *"Claude thinks again and then tells me, no, it shouldn't be
like this."*
**Rule:** an answer is not automatically accepted. If the user's choice is weak or
contradicts an earlier decision, Forge says so and explains why before recording it. The
user can still overrule — and the disagreement is recorded alongside the decision. This is
the difference between a teacher and a form field.
**Applies to:** the interrogation loop (Phase 8), the teaching skill (Phase 7).

## R9 — Restraint in the interface

**Came from:** user feedback — *"don't ask for too many emojis."*
**Rule:** colour and weight carry most meaning. Only four symbols are kept: ⚒ (Forge),
⛔ (blocked), ✅ (recorded), ★ (recommended), plus `!` for a review finding. The screen
stays clean; decoration never competes with the decision.
**Applies to:** the visual layer (Phase 2).

## R10 — Questions are compact and boxed, never prose

**Came from:** user feedback after the challenge stage.
**Rule:** a question is never a wall of text. It is framed in a box with a short title, then
at most two lines of explanation, options as a tight list of one line each, one line of
recommendation, one line against it, and the progress bar. If it does not fit on a screen,
it is too long.
**Applies to:** every question Forge asks (Phase 8), and the visual layer (Phase 2).

## R6 — Keep a written record, not a conversational one

**Came from:** user asking whether responses were being recorded.
**Rule:** decisions and learned rules are written to files as they happen, not held in the
conversation. If it is not in `.forge/`, it did not happen.
**Applies to:** Forge's own build, and the product's behaviour.
