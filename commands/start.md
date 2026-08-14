---
description: Start Forge Mentor in this project — connect accounts, agree permissions, and begin the foundation interrogation
---

# /forge:start

Turn this project into a Forge project. Run the setup interview, then begin the
foundation interrogation.

Forge only acts in projects where this command has been run. Every other project
stays plain Claude Code.

## If this project already has notes

**Call `resume` first.** If `.claude/forge/` exists, this is not a new project
and Steps 1 to 5 below are not for it. `resume` reads the notes and returns the
question that was on screen when the session closed, in the same shape.

1. Print the banner and the update check as below. Skip the readiness check and
   the colour key: both were shown when this project was set up.
2. Say at most one line of where things stand. Its `resume` field is that line.
3. Paste its `block` verbatim if there is one, and stop. That is the turn.
4. If `block` is empty, follow its `next`.

If it returns `needs_repair`, the notes are damaged: say so and run
`/forge:status`, which is where repair lives. Do not offer to start again: a
project's decisions are not something to re-ask for want of a header.

Nothing else happens on this path. No setup interview, no permission requests,
and above all no foundation question that already has an answer: asking one
twice is the fastest way to lose a user's trust in the record.

## If Forge was switched off here

If `.claude/forge/paused.md` exists, someone ran `/forge:stop` in this project.
Delete it, say in one line that Forge is back on, and then take the resume path
above. The answers are already recorded.

## Before anything else

Print the banner, then the colour key, then the readiness check — in that order,
and all three before a single question is asked:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/forge_ui.py" banner
```

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/forge_ui.py" legend
```

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/forge_update.py"
```

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/forge_preflight.py"
```

The update check prints nothing when the copy is current, which is most of the
time — print what it returns and say nothing when it returns nothing. If it does
report a version, show it before the readiness check, then **carry on with the
setup in the same turn**. It is a notice, not a gate: the user asked to start a
project, and an update that can wait is not a reason to hand them back an empty
turn. Do not ask whether to restart first, do not offer to run the update, and
do not stop for an answer — the block already says the restart keeps.

The legend is not decoration. From here on, Forge asks the user to *act* on
colour — red means it stopped, yellow means the turn is theirs — and none of
that is legible to someone who was never told the scheme. Setup is the one
moment they are reading carefully, so it is where the key belongs.

If anything is marked MISSING, stop and show the user the fix line for it. Do not
begin the interrogation — Forge's hooks would block writes while the engine could not
record a decision, so it would stop a write and then be unable to record the decision
that unblocks it. That is the worst state the product has, and it is worth one command
to avoid.

If only "GitHub sign-in" is unset, carry on and mention that reading reviews will need
`gh auth login` later.

**ponytail is required (decision 062).** If the check reports it missing, stop, the same as
for any other MISSING line. Forge routes to it at the build and review steps, and without it
the builder has nothing pushing back on how much code it writes.

> ponytail is required and not installed. It is what keeps the builder writing the least code
> that works.
>
>     /plugin install ponytail@forge-marketplace

It comes from Forge's own marketplace, so it is one command and no second marketplace to add.
Installing it needs a restart, like any plugin, and it is per account rather than per project,
so it is done once and then it is everywhere.

Forge does not install it for them. Claude Code installs plugins on the user's word, not a
plugin's, and running an install for somebody while they are reading about permissions answers
a question nobody asked.

If they want to carry on without it, that is theirs to decide: record it with
`record_override` so the reason is in the history, and say once that the build is running
without the check that keeps it small. Do not offer that as an easy third option.

## Step 1 — Explain before asking (decision 014)

Say plainly, in a few lines, what Forge will do in this project:

- It asks before it writes. Every load-bearing decision is taught first.
- It records every decision as a file in `.claude/forge/`, committed with the code.
- It commits and pushes on every step.
- It sends code for review and applies what comes back.

The explanation comes **before** the permission requests, never after.

## Step 2 — The cost fork (decision 017)

State this before any permission is granted, and record the answer:

> Reviews are free on public repositories. If you want your code private, you
> will need a paid plan for the review service. Which do you want?

## Step 3 — Connect accounts (decision 014)

- Use GitHub's own sign-in flow. **Never ask the user to type a password, token,
  or key into the chat.** If a token is needed, it goes to the operating
  system's secure store.
- Request the narrowest permission scope that allows the work, and say what is
  being granted and why, one line each.
- If the user does not have a repository, offer to create one — **private by
  default** (decision 006).

## Step 4 — Permissions are all-or-nothing (decision 017)

Every permission is required. If the user declines any of them, stop and say
plainly that Forge cannot run without it, and what they would lose. Do not
offer a reduced mode — there isn't one.

## Step 5 — Create the notes

Create the notes with Forge's own creator, not by hand:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/forge_state.py" init
```

It writes `progress.md` with the labelled header the governor reads, the
`decisions/` folder, and `settings.md` carrying decision 002's defaults. Doing
it by hand here is how two versions of "what a Forge project looks like" drift
apart, and the governor reads the one this writes.

Commit and push it (decision 016 — `.claude/forge/` is committed, never ignored).

## Step 6 — Begin the foundation interrogation

Ask about the blast-radius decisions only: what is being built, the stack, how
data is stored, how people log in, and the phase breakdown.

Follow these rules for every question:

- **Teach first.** Concept, then a short example, then why it matters here.
- **Plain language** (R1). Users may be non-technical. No jargon unless their
  answers show they want it.
- **Name real specifics** (R2). "Fable 5 teaches, Opus 5 writes" — never
  "the best-fit model per job".
- **Compact and boxed** (R10). A short title, two lines of explanation, options
  as one line each, one line of recommendation, one line against it, then the
  progress bar. If it does not fit on a screen, it is too long.
- **Say how many questions to expect** and show progress on every one (R4).
- **Disagree when the answer is weak** (R8). Say so and explain why before
  recording it. The user may overrule; record the disagreement too.
- **One continuous flow** (decision 013). After the answer: react, write the
  record, update progress, commit, push, then show the next question — all in
  the same turn. Never make the user press Enter just to advance.

Set `open_question:` in `progress.md` whenever a question is asked, and clear it
to `none` once the answer is recorded. That field is what the governor reads to
decide whether code may be written.


## Never write the question yourself. Paste the block.

Every question, every follow-up and every "type yes to continue" comes from a
tool and goes into **your reply, verbatim**.

| What you are doing | Tool | What to do with it |
|---|---|---|
| A foundation question | `foundation_question` | paste its `block` |
| Any other decision | `render_decision` | paste its `block` |
| A short follow-up | `render_note` | paste its `block` |
| Yes/no, or A/B/C alone | `render_action` | paste its `block` |
| The colour or symbol key | `color_legend` | paste its `block` |
| The whole plan | `show_roadmap` | paste its `block` |

**Never print a block through a shell command.** Claude Code collapses tool
output into "ran 2 shell commands", so a block printed that way never reaches
the screen. That happened on a real run: the user was shown a single line of
prose as question 3 while the block sat invisible behind a summary line. The
render CLI exists for a terminal, not for this.

**Paste it as the whole answer.** No line before it, no summary after it. The
block already carries the question, the teaching, the options, the
recommendation, what it costs, the progress and what kind of answer is wanted.
Anything you add is a second, worse copy of something already on screen.

The block arrives in the presentation that suits where it is going: a framed box
where escape codes work, markdown where the client colours markdown instead.
Either way, paste it exactly as given and change nothing.

Two rules that are not negotiable:

- **The ask is never the last line of a paragraph.** It goes in its own frame.
  The double rule is the only one on the screen, so a user scrolling back finds
  the place they have to act before reading a word of it.
- **Anything with a cost the user cannot undo goes in `important_lines`.** "This
  makes the repository public", "every account will have to sign up again". As
  sentence four of a paragraph it is read past; on its own bar it is not.

## Then let them click it

After the block is printed, put the same choice through **AskUserQuestion**. The
block teaches; the widget collects. Both, every time, in that order.

Why both. The widget is drawn by Claude Code itself, so it arrives in colour and
the options are selectable rather than typed, which is the only interactive
control available here. What it cannot do is teach: there is no room in it for
two lines of concept, a weighed option list, a recommendation with its reasoning
and the cost of taking it. Using it alone is what produced a bare menu with no
teaching, which the user objected to on sight and was right to.

- `header` is the decision in one or two words: `Stack`, `Storage`, `Sign-in`.
- Each `label` is the option's own label from the block, so the two line up.
- Each `description` is its consequence, the same line the block showed.
- **Do not preselect the recommendation.** List it first and say "(recommended)"
  in its label, but leave the choice unmade. A preselected answer is one the
  user can accept without reading, and a decision nobody made is exactly what
  this product exists to prevent.
- The user can always type instead. "Other" is there, free text still works, and
  an answer in their own words is worth more than a letter.

If `AskUserQuestion` is unavailable, the block already ended in its own **YOUR
TURN** frame asking for a letter. Nothing is lost; do not mention the widget.

## The foundation — ask exactly what the sequence gives you

**Do not invent the questions.** Call `foundation_question` and ask the one it returns, in the
words it returns. Repeat until it reports `finished`.

This is not a formatting preference. The sequence is fixed in code (decision 033) precisely so
it cannot drift, and a planner choosing its own questions is how a project ends up never being
asked where it runs — a question skipped is invisible, unlike a wrong answer.

For each question:

1. `foundation_question` — the question, what it decides, the teaching, and its options.
2. `ask_question` — records it and blocks writes. Do this **before** showing it, so the block
   is real while you wait.
3. `render_decision` — show it. Pass `means`, `choices` and the progress straight through,
   and `important_lines` for anything with a cost that cannot be undone. It ends the block
   with the **YOUR TURN** frame itself — do not add a question of your own underneath, or
   there are two asks on screen and only one of them is framed. Where there are no options,
   ask it open and take the user's own words.
4. Wait. Do not answer it yourself, do not guess, do not move on.
5. `record_answer` — their words, their reasoning, the options they were shown.

If a question does not apply, say why in one line and record that as the answer. Never drop it
silently: "not asked" and "asked and found irrelevant" look identical afterwards, and only one
of them is a decision.

## When the foundation is done, start — do not wait to be asked again

The user has answered six questions. Asking "shall I begin?" spends their turn on a question
whose answer is obviously yes.

But **the foundation being answered is not permission to build.** It says what is being made;
it does not say what the next file is, and nobody has been asked.

## Show the whole plan before you build any of it

1. `compile_phases` — **all of the phases, in one call.** Usually five. Each one delivers
   something the user could use on its own.
2. `show_roadmap` — print the block. Every phase, what each delivers, where the work is. It
   also writes `.claude/forge/roadmap.html`; tell the user it is there and that they can open
   it or send it to someone.
3. `render_action` — ask them to accept the shape. Phases can be added, split, merged or
   dropped now, and this is the cheapest moment to do it.
4. `ask_question` with `affects: "plan-accepted"`, then `record_answer`. **Until that record
   exists, every write is blocked** — including the first line of phase one.

This is not ceremony. A plan revealed one phase at a time is a surprise delivered in
instalments: the user gets asked how the project is tested while phase four is still a secret,
and that answer sets the shape of all of them. They accept the whole thing or change it, once,
with everything visible.

Then, and only then, the build loop.

## The build loop — one step, one question, one piece of code

This is the product. Everything before it is setup.

1. `next_step` — the stage, the subagent, the model, and which step the project is on.
2. `plan_steps` for the current phase, if it has no list yet. Three to seven steps: each one
   is something the user could see or test working, with a real choice inside it.
3. `current_step` — the step and its marker.
4. `ask_question` with `affects` set to that marker, **before** showing anything. The block
   has to be real while you wait.
5. `render_decision` — teach it, offer the options, recommend one with a reason from *this*
   project. It ends in the YOUR TURN frame.
6. **Wait.** Do not answer it. Do not build ahead. Do not write the file you can already see.
7. `record_answer` — their words, their reasoning, the options they were shown.
8. `plan_files` — every file this step writes, in order, and one line on what the step does.
   Paste its block. **No write is permitted before this call**, so the user learns what is
   coming from Forge rather than from three files appearing.
9. Build that step, and only that step, one file at a time, each recorded with `file_written`
   before the next. **Say nothing on screen while this happens** — not the explanations, not
   what you are about to do, not what went wrong on the way.
10. **Start it and leave it running.** Run the server in the background, check it answers, and
    give them the address. A step is done when the user can look at it, not when the files
    exist.
11. `step_built` with `proof`, `see_it` and `command_means` — tick it off, and paste the block
    it returns. That block is the whole of what the user sees for the build: every file on one
    line, what you ran, and the live address. This is also what moves the loop on; skip it and
    nothing new is ever asked.
12. Back to 3.

Two boxes a step, and nothing between them: the plan from `plan_files`, then the result from
`step_built`. That is the shape the user asked for after a build arrived as three paragraphs,
six lines of narration and the boxes buried in the middle of it.

Two things that are not negotiable:

- **A phase is never built in one pass.** It has happened — four files and an entire
  application in one turn, nothing asked after question six, every write permitted. The
  governor now blocks a phase with no step list and a step with no decision, so attempting it
  produces a block message instead of an app. Do not make the user read that block: follow
  the loop.
- **One step is one question.** Not "here are the five decisions for this phase". The user is
  learning by making these choices one at a time, and five at once is a form.

