---
description: Start Forge Mentor in this project — connect accounts, agree permissions, and begin the foundation interrogation
---

# /forge:start

Turn this project into a Forge project. Run the setup interview, then begin the
foundation interrogation.

Forge only acts in projects where this command has been run. Every other project
stays plain Claude Code.

## Before anything else

Print the banner:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/forge_ui.py" banner
```

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


## Before anything else

Run the readiness check and show its output:

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/forge_preflight.py"
```

If anything is marked MISSING, stop and show the user the fix line for it. Do not begin the
interrogation — Forge's hooks would block writes while the engine could not record a decision,
so it would stop a write and then be unable to record the decision that unblocks it. That is
the worst state the product has, and it is worth one command to avoid.

If only "GitHub sign-in" is unset, carry on and mention that reading reviews will need
`gh auth login` later.

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
3. `render_decision` — show it. Pass `means`, `choices` and the progress straight through.
   Where there are no options, ask it open and take the user's own words.
4. Wait. Do not answer it yourself, do not guess, do not move on.
5. `record_answer` — their words, their reasoning, the options they were shown.

If a question does not apply, say why in one line and record that as the answer. Never drop it
silently: "not asked" and "asked and found irrelevant" look identical afterwards, and only one
of them is a decision.

## When the foundation is done, start — do not wait to be asked again

The user has answered six questions. Asking "shall I begin?" spends their turn on a question
whose answer is obviously yes.

1. `next_step` — the stage, the subagent, the model.
2. `plan_build` if the phases are compiled — the ordered file list for this stack.
3. `render_note` with the first step: what is being built, which file is first, and why that
   file. Three lines.
4. Then build it. Announce each file as you reach it, not in a batch at the end.

