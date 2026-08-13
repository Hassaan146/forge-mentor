---
description: Add a feature to a project Forge has already built, without re-asking what is already decided
---

# /forge:add

For a project that already works. The user says what they want to add, in their own words,
and this is the path that gets it built without disturbing what is there.

If this project has no `.claude/forge/` yet, stop and tell them to run `/forge:start`. There
is nothing to add to.

## Step 1: read before asking

Call `plan_feature` with their description. It returns three things:

- **`built_on`**: the recorded decisions this feature has to live inside, as ids and
  one-line choices.
- **`clashes`**: anything the feature wants that the project has already ruled out, each
  naming the decision that would have to be reopened.
- **`still_to_ask`**: the subject questions this feature owes that are not answered yet.

**The foundation is not asked again.** It is on disk, it is still true, and asking a user a
question they have already answered is the fastest way to lose their trust in the record. It
is also most of the cost: re-running an interrogation to add one feature spends the tokens of
a new project to learn what was already written down.

Say what it is being built on in **one line**, not a recital. "This lands on top of decision
016, SQLite in one file, and 019, migrations in the repository." They wrote those answers;
they need reminding, not re-teaching.

## Step 2: put the clashes first

A clash is not a detail to work around. It means the feature, as described, contradicts
something the user decided, and there are exactly two honest ways forward:

- **Change the feature** so it fits what is recorded.
- **Change the decision**, which is a *new* decision naming the old one with `supersedes`,
  and a new record saying what changed and why. Never an edit of the old one: the earlier
  record stays readable and stays in the chain, because the history is what makes any of this
  auditable.

Put both to the user with `render_decision` and let them choose. Do not pick for them, and do
not build around a clash quietly, which is the one outcome that leaves a project nobody can
explain.

## Step 3: ask what the feature owes

Work through `still_to_ask` the same way as any other question: paste the block, wait, record
the answer with the user's own reason. A feature that adds uploads owes the upload question
even though the project answered its database questions a month ago.

## Step 4: append the phase

Call `add_phase`, then `plan_steps`. **Never `compile_phases` here.** That rewrites the whole
plan, which puts finished work through a new pen and can mark built steps unbuilt. Appending
is what keeps August's phases exactly as they were.

Then the build loop is the ordinary one: `step_questions`, the step's own decision, the code,
the gate, the explain-back.

## What this command is for

Adding one thing to a working project should cost one feature's worth of questions, not a
project's worth. And the feature that goes in should not be able to break the one that is
already there without somebody deciding that out loud.
