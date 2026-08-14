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
**Amended by [035](decisions/035-one-symbol-per-meaning.md) and R11:** the count was
replaced by a test — one symbol per meaning, and no symbol without one. Eight now.

## R11 — Every colour means one thing, and the user is told which

**Came from:** user feedback — *"each response must have colours… red is error, green is
this, yellow is this, blue is this. For each colour there should be some notations."*
**Rule:** six colours, one meaning each, the same meaning everywhere in the product:

| | |
|---|---|
| amber | Forge itself — if it is this colour, the plugin is talking |
| blue | information — teaching, explanations, file paths |
| green | it worked — decided, recorded, passed, recommended |
| yellow | your turn, or a cost to weigh |
| red | it stopped — errors, blocked writes, findings |
| purple | which AI is doing the current job |

Two things follow from it. **The key is taught at setup**, beside the permissions, because
Forge asks the user to *act* on colour and a scheme nobody was told about is a scheme
nobody can read. And **colour is never the only signal** — every line carries a symbol and
words that say the same thing, so the whole system survives `NO_COLOR`, a monochrome
terminal, or a user who cannot distinguish the hues.

Every coloured span closes with the reset. An unclosed one does not stop at the end of
Forge's output; it recolours the user's own shell prompt.
**Applies to:** the visual layer (Phase 2), the readiness check, every question and every
block Forge prints.

## R12 — What the user must do next has its own frame

**Came from:** user feedback — *"'press type yes' or something like this, encapsulate it in
a special frame so that it gets separated."*
**Rule:** the ask is never the last line of a block. "Type yes to continue", "A, B, or C?",
"run this and tell me when it is done" — each goes in the double-ruled **YOUR TURN** frame,
the only one of its kind on the screen, so a user scrolling back finds the place they have
to act before reading a word of it. The frame states what shape of answer is wanted, and
names the letters that were actually offered rather than a fixed A/B/C.

The same applies to details with a cost that cannot be undone — *this makes the repository
public*, *every account will have to sign up again*. They get a yellow bar and their own
vertical. As sentence four of a paragraph they are read straight past, and those are the
sentences the user most needs to have read.
**Applies to:** every question (Phase 8), the governor's block message, the readiness
check, and the visual layer (Phase 2).

## R10 — Questions are compact and boxed, never prose

**Came from:** user feedback after the challenge stage.
**Rule:** a question is never a wall of text. It is framed in a box with a short title, then
at most two lines of explanation, options as a tight list of one line each, one line of
recommendation, one line against it, and the progress bar. If it does not fit on a screen,
it is too long.
**Applies to:** every question Forge asks (Phase 8), and the visual layer (Phase 2).

## R13 — The loop is enforced by the files, never by the instructions

**Came from:** a dogfood run, and the user watching it — *"it didn't ask me about anything and
directly started building. I want it to be an interactive process."*
**Rule:** every rule about how Forge behaves has to be a fact about `.claude/forge/`, checkable
by the governor. Anything living only in a prompt is advice, and advice is what produced an
entire application in one turn with nothing asked after the sixth question.

Concretely: a phase cannot be built, only its steps. A phase with no step list is blocked; a
step with no recorded decision is blocked; the gate opens for one step and closes when that
step is ticked off. The planner's brief still describes the rhythm — teach, offer, recommend,
wait — but the brief is now the explanation of a gate rather than the gate itself.

The test for any future rule is the same: *if the model ignored this paragraph, what would stop
it?* If the answer is nothing, it is not a rule yet.
**Applies to:** the write gate (Phase 4), the pipeline (Phase 8), every agent brief.

## R14 — The user sees the whole shape before any of it is built

**Came from:** the user watching a run — *"Why are we moving with a phase-by-phase approach?
First, you will make all the phase plans… we have to show all the phases to the user."*
**Rule:** every phase is compiled in one pass, the whole plan is shown, and the user accepts or
changes its shape before a line is written. A plan revealed one phase at a time is a surprise
delivered in instalments: a question with project-wide reach — how is this tested, where does it
run — gets answered while three phases are still invisible, and that answer silently sets the
shape of all of them.

Shown twice over, because the two do different jobs. The terminal roadmap is what is in front of
the user at the moment they accept it, and it needs nothing but a terminal. `roadmap.html` is
self-contained, opens from disk with no network, survives the scrollback, and can be sent to a
mentor or read in week six when nobody remembers what phase four was for. It is generated from
the files every time — a roadmap maintained by hand disagrees with the project inside a week,
and the copy someone is reading is always the wrong one.

Acceptance is a recorded decision, not a flag, so it rides on the chain like everything else.
**Applies to:** the pipeline (Phase 8), the write gate (Phase 4), `/forge:start`.

## R15 — Speech is gated the same as writing

**Came from:** the user, on seeing a decision arrive as unframed prose —
*"I asked you that this must be short and encapsulated in a box, there should be a guardrail
which enforces this thing."*
**Rule:** the governor gates writes because a write is a file path a hook can see. Most of what
Forge does is talk, and talk was gated by nothing — so R10 and R12 held exactly as long as a
model felt like following them. A `Stop` hook now reads the last thing said: if a question is
open and there is no frame around it, the turn is refused and the assistant is told which tool
to call. Loose prose around a frame is refused too, because a block with ten paragraphs above it
is the same wall of text wearing a box.

It fails open on everything — an unreadable transcript, an unexpected shape, any error at all.
The governor can afford to fail closed, because a blocked write costs one turn. A `Stop` hook
that errors costs the session.

**Applies to:** every turn in a Forge project where a question is open.

## R16 — Check which process the output is actually leaving

**Came from:** the same report — *"and also no colors, why?"*
**Rule:** `isatty()` answers "am I writing to a terminal", which is the right question for a
command and the wrong one for a renderer. The MCP server writes JSON-RPC down a pipe, so inside
it every colour code was replaced by an empty string — not dimmed, *absent*, in every build,
always. The palette, the legend teaching it, and the tests holding it to account were all
correct, and none of them ran in a process that could emit one escape byte.

A renderer composes for a client that has a terminal; it is not writing to its own. The server
sets `FORCE_COLOR` for that reason. `NO_COLOR` still outranks it — that switch is the user's.

The general form: when output looks wrong, find which process emits it and what that process
believes about its own stdout, before changing anything about how it is drawn.
**Applies to:** every render tool, the readiness check, the hooks.

## R17 — A tool that is out of date has to say so itself

**Came from:** the user, after four sessions spent debugging a build that had already been
fixed — *"after every update, the plugin should show 'Update your current plugin', like we
have on the Play Store, so that we don't have to uninstall and reinstall from scratch."*
**Rule:** the plugin checks its own version against its repository once a day and says so in
one frame, with the command to run. Nothing else about the remote is displayed — only a
version string, and only after it matches a strict numeric pattern, because remote text on a
screen is remote text in a model's context.

Silence is the normal answer and the answer to every failure: no network, a proxy, a rate
limit, junk in the response. `FORGE_NO_UPDATE_CHECK=1` turns it off. An update check is the
least important thing in a session and must never be why one fails to start.

The notice says two things beyond the command, because they are what stops people delaying:
the user's decisions are untouched — they live in the project, not the plugin — and Claude Code
must be **restarted**, not reloaded, since hooks and the engine register at startup.

The general form: any version a user reads must come from the artefact itself. The banner
printed "0.1.0" from a default argument while the manifest said 1.0.0, and it is the first
thing anybody checks to see whether an update landed. A number that is wrong is worse than no
number, because it is believed.

**And the notice never stops the command it appears on.** A `UserPromptSubmit` hook used to
hold `/forge:start` back while a newer version sat downloaded and unloaded, on the reasoning
that starting on an old build writes a notes layout and a question sequence shaped by the wrong
version. It named `/forge:status` as the way out; in an empty directory that command answers
"not a Forge project, run `/forge:start`", which the hook then blocked as well. A user ran the
pair four times before reporting it, and the hook is gone. The check stayed: `start.md` prints
it before Step 1 and carries straight on, so the update command and the project both arrive in
the same turn. A stale build is worth a sentence, not a locked door — and a way out that leads
back to the door is worse than no gate at all.

The command it hands over is one that exists: `claude plugin update forge@forge-marketplace`,
taken from `claude plugin update --help`, whose own text supplies the restart line. An earlier
draft invented a slash command. A fix instruction that does not work is worse than none, because
the user now believes they have tried.
**Applies to:** the plugin shell (Phase 2), release (Phase 10), `/forge:update`.

## R6 — Keep a written record, not a conversational one

**Came from:** user asking whether responses were being recorded.
**Rule:** decisions and learned rules are written to files as they happen, not held in the
conversation. If it is not in `.forge/`, it did not happen.
**Applies to:** Forge's own build, and the product's behaviour.
