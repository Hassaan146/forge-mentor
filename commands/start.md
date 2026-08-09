---
description: Start Forge Mentor in this project — connect accounts, agree permissions, and begin the foundation interrogation
---

# /forge:start

Turn this project into a Forge project. Run the setup interview, then begin the
foundation interrogation.

Forge only acts in projects where this command has been run. Every other project
stays plain Claude Code.

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
report a version, show it before the readiness check: setting up a project with a
plugin that is about to be replaced wastes the setup.

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

Create `.claude/forge/` in the project with:

- `progress.md` — the labelled header must include `open_question:` and
  `override_active:`, because the governor reads them on every write
- `decisions/` — one file per decision
- `settings.md` — which AI does which job, with the defaults from decision 002

Commit and push it (decision 016 — `.claude/forge/` is committed, never ignored).

## Step 6 — Begin the foundation interrogation

Ask about the blast-radius decisions only: what is being built, the stack, how
data is stored, how people log in, and the phase breakdown.

Follow these rules for every question:

- **Teach first.** Concept, then a short example, then why it matters here.
- **Plain language** (R1). Users may be non-technical. No jargon unless their
  answers show they want it.
- **Name real specifics** (R2). "Fable 5 teaches, Opus 4.8 writes" — never
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


## Never write the question yourself

Every question, every follow-up, and every "type yes to continue" goes through a
render tool. Not because hand-written prose is untidy, but because an unframed
paragraph is indistinguishable from ordinary assistant text — the user cannot
tell which of the two is bound by Forge's rules (decision 035).

| What you are doing | Tool | What the user sees |
|---|---|---|
| Asking a decision | `render_decision` | the block, then a double-ruled **YOUR TURN** frame |
| A short follow-up | `render_note` | the frame, capped at three lines |
| Asking yes/no, or A/B/C on its own | `render_action` | the double-ruled frame alone |
| A detail they must not skim | `important_lines` on either render tool | a yellow bar beside it |
| Explaining the colours | `color_legend` | the key, at setup |

Two rules that are not negotiable:

- **The ask is never the last line of a paragraph.** It goes in its own frame.
  The double rule is the only one on the screen, so a user scrolling back finds
  the place they have to act before reading a word of it.
- **Anything with a cost the user cannot undo goes in `important_lines`.** "This
  makes the repository public", "every account will have to sign up again". As
  sentence four of a paragraph it is read past; on its own bar it is not.

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
8. Build that step, and only that step.
9. `step_built` — tick it off. This is what moves the loop on; skip it and nothing new is
   ever asked.
10. Back to 3.

Two things that are not negotiable:

- **A phase is never built in one pass.** It has happened — four files and an entire
  application in one turn, nothing asked after question six, every write permitted. The
  governor now blocks a phase with no step list and a step with no decision, so attempting it
  produces a block message instead of an app. Do not make the user read that block: follow
  the loop.
- **One step is one question.** Not "here are the five decisions for this phase". The user is
  learning by making these choices one at a time, and five at once is a form.

