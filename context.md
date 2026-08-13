# Context

Everything you need to pick this project up cold. Written for a new session, a
new machine, or someone who is not me.

The short version: **Forge Mentor is a Claude Code plugin that refuses to write
load-bearing code until you have made — and understood — the decision behind
it.** The decision is the lesson. A user who cannot say why their app is built
a certain way does not own it, however well it runs.

---

## Where things are

| | |
|---|---|
| **Default branch** | `merge` — not `main`. All ten phases live here. |
| `main` | Phase 2 only, frozen. Kept as history; nothing targets it. |
| `phase-3` … `phase-10` | Eight branches, all fast-forwarded to `merge`. Their pull requests (#1–#8) are now historical — the per-phase split has been superseded and they show near-identical diffs. |
| **Marketplace** | `Hassaan146/forge-marketplace` follows this repo's default branch, so an install gets `merge`. |
| **Project notes** | `.claude/forge/` — decisions, chain, reviews, phases (decision 032). |
| `prompts.md` | Project root, generated. A programme deliverable, so it stays where a reader looks. |

Working copy: `H:\Skills\Project\forge-mentor`.
Planning documents (proposal, plan, mockups) sit one level up in `H:\Skills\Project`.

---

## How it works

Four moving parts, and the split between them matters.

**Hooks** (`scripts/governor.py`, `safety.py`, `gates.py`) are the guarantees.
They run as subprocesses, are **standard-library only**, and never depend on
anything being installed. The governor blocks writes; safety blocks secret reads
and quotes outside text as data; gates hold the commit until tests pass. Three
more are not guarantees and never block: `forge_update.py` (are you on the
current build), `presenter.py` (was that said in a frame), `companion.py`
(bring ponytail in with Forge).

**The MCP server** (`server/forge_server.py`) is the engine — 47 tools for
recording decisions, reading reviews, metering usage, planning the pipeline,
and asking a subject what it owes before it is built.
Registered tools must be defined *above* `server.run()`, which blocks; anything
below it is silently never registered.

**Skills** (`skills/`) are four instruction files bundled in the plugin: the
teaching voice, the coding standards, the security floor, the explain-back gate.
They are the product. The wider library is installed separately at setup.

**Subagents** (`agents/`) split the work across models — planner on Fable 5,
builder on Opus 5, structurer on Haiku 4.5, review-fixer on Opus 5. The
subagent file is authoritative, because Claude Code reads it at dispatch.

---

## The rules that are actually enforced

Not aspirations. Each is code, with a test.

1. **No write past an unanswered question.** Including the six foundation
   questions — a fresh project blocks until all of them are recorded. This was
   broken for most of the build: the rule only covered the window between asking
   and answering, so a brand-new project allowed everything.
1b. **A note the builder writes about its own work is not permission.** Build
   choices are recorded as they are made (decision 051), marked in the header,
   and `decided_markers` refuses to count them. Without that line the builder
   opens its own gate by describing what it decided to do.
2. **Secret files are never read**, by any spelling. `cat`, `sed`, `python -c`,
   a symlink with a harmless name.
3. **Outside text is data.** Review findings arrive wrapped, and the wrapper
   cannot be closed from inside.
4. **Nothing is pushed without asking**, per push, every time.
5. **Nothing is destroyed.** Repair quarantines before it overwrites.

---

## The question order, and why it is fixed

`scripts/forge_foundation.py`, decision 033.

1. **What's the idea?** — open, no options
2. **What are you building this with?** — the stack, in detail
3. **What is stored, and what happens if it is lost?**
4. **Is there more than one person using this?**
5. **Where does this run when you are not running it?**
6. **What does 'finished' mean for a step?**

Six is where it starts, not where it ends. **Answers open further questions** (decision 049):
deploying opens how a change gets there, what happens when it falls over, and where the secrets
live; staying local opens what you would want back if the machine died; a second person opens
identity and permissions. A question that does not apply was never in the sequence, rather than
skipped in front of the user. `sequence()` computes the live list and `position()` counts against
it, so the total moves as the interrogation runs.

## The order of a step, and it does not vary

`scripts/forge_lean.py`, decision 060. Forge's question was always *which* decision. The one
before it, does this need writing and how much of it, was never asked.

1. `lean_check` runs the ladder: does it need to exist, does the project already do it, does the
   standard library do it, what is the smallest version worth having, what the extra size costs.
   The model answers all five (ponytail's job), then puts the findings to the user as a size
   question. `record_lean` writes it, and it is refused with a rung missing.
2. `step_questions`, if this step is the first to touch a subject.
3. The step's own question.
4. `lean_review` on the approach the answer implies, **before a line of it is written**.
   Unchanged is one line. **Smaller is the user's decision**, not the reviewer's. Reviewing
   after the code exists means arguing to delete something that already works, which is an
   argument the code usually wins.
5. The builder writes what they settled on.

The gate is `next_gap` returning `unchallenged`. Nothing here judges whether code is minimal:
the model reasons, the gate remembers. Note the marker trap this hit on the way in: `lean:` plus
the step marker *contains* the step marker, so recording the pass counted as deciding the step
and skipped the question the pass exists to precede.

## The plan is drafted in plan mode

Decision 067. The planner enters Claude Code's plan mode before drafting the phases and stays
in it until the user accepts, running ponytail's ladder over the plan while there: a phase that
exists because plans usually have one, or one whose deliverable the project already has, is the
cheapest deletion in the build and the most expensive to notice in week three.

**This one is an instruction, not a gate.** Nothing in Forge can put the client into plan mode,
so unlike everything else in this file it depends on the planner following it, and instructions
in this project have a history of being skipped.

## What the owner asked for

`.claude/forge/asked-for.md`, decision 068, written by `what_did_i_ask_for`. Every "In their
words" section from every record, in one list, with what each became.

It exists because sixty records is not a list anybody scans: a small thing asked for in March is
a small thing nobody can find in June. It is a **view**, regenerated on every call, so deleting
a record removes its line and the index can never claim a requirement that is not recorded.
Reconstructing one from the conversation is the answer that is never acceptable, because that is
memory presented as a record.

## Coming back after a gap

`catch_up`, decision 066, and the first thing `/forge:status` calls. Two blocks: **where you
left off**, then the question or step you were on, so the session continues rather than
restarts. The box carries the idea in the user's own words, questions answered against the
estimate, decisions recorded, phases finished, steps built, what is open now, and the last three
decisions with what was chosen.

Assembled from the records on every call, never from a session log. A log would be a second
version of a history the records already hold, and two records of the same thing is one record
that is wrong. Deleting a decision changes the summary, which is the property that keeps it
honest. The second block is `resume`'s, reused rather than rebuilt.

## Adding to something that already works

`scripts/forge_feature.py` and `/forge:add`, decisions 056 and 057. Every gate reads the phase
list, so once the last phase was built `next_gap` found no unbuilt step and **opened**. Someone
coming back a month later to add one feature got no questions at all.

- `plan_feature` returns three things: the recorded decisions the feature lives inside (ids and
  one-line choices, capped at eight), anything it wants that the project has ruled out with the
  decision that would have to be reopened, and the subject questions it still owes.
- **The foundation is never asked again.** It is on disk and still true. Re-asking it spends a
  new project's tokens to learn what was already written down.
- `add_phase` appends. `compile_phases` rewrites the whole list, which puts finished work
  through a new pen and can mark built steps unbuilt.
- Changing a recorded decision is a **new record naming the old one** with `supersedes`, never
  an edit. The old record stays readable and stays in the chain.

## Three reviewers, one list

Decision 064. CodeRabbit and Sourcery are GitHub apps: they post to the pull request and the
workflow reads them into `.claude/forge/reviews/pr-<n>.md` (decisions 025, 026). ponytail is a
plugin in the session with no account to post from.

- Its findings are filed with `record_review_findings` into **`pr-<n>.local.md`**, committed like
  everything else in the notes.
- `fetch_and_save` merges them into `pr-<n>.md` on **every** fetch, so the combined file is
  rebuilt from both rather than one overwriting the other. Writing straight into `pr-<n>.md`
  would have them wiped by the next fetch with nobody seeing it happen.
- `is_clean` counts all three, so a step is not finished while any of them is open.
- `resolve_finding` routes on the id: `ponytail-N` is marked handled in its own file, anything
  else closes a GitHub thread.
- **ponytail is deliberately not in `REVIEWERS`.** That table is anchored to two bot logins
  because the repository is public and any account containing the right word could otherwise
  raise findings and satisfy the reviewed check on its own.

**What makes it run (decision 065).** Not the model remembering. `pr-<n>.md` carries a
fingerprint, `pr-<n>.local.md` records the version it was written against, and anything else is
*owed*. `scripts/reviewed.py` checks it after the fetch tool, after Bash, and at the start of a
session, so a review pulled in another window is noticed at the top of the next turn.

Hooking the moment the file is written was the obvious design and the wrong one: the usual
arrival is the workflow committing it and the user pulling in a terminal, which nothing in the
session sees. **`clean` now means all three have looked**, not merely that no finding is open,
and filing nothing counts as looking: "found nothing" and "has not run" are different states.

## Code that refers to things which do not exist

`scripts/forge_grounding.py` and the `grounded.py` PostToolUse hook, decision 063. Every import
is checked against the project's manifests, the standard library and the files actually there;
every "as decided in decision 014" against the records.

- **After the write, not before.** A reference cannot be checked until it exists, and a hook
  that stops work on suspicion is one people turn off.
- **It never fixes anything.** Each finding is a dependency to add and record, a file about to
  be written, or something invented, and which of the three belongs to the user. A silent
  correction is a second guess stacked on the first.
- Read from the manifests, never from the environment: a package installed by accident is why
  this class of bug survives review.

`FORGE_NO_GROUNDING=1` turns it off.

## Companions: other people's plugins

`COMPANIONS` in `forge_skills.py`. **ponytail** (github.com/DietrichGebert/ponytail, MIT) loads
at the building stage and `ponytail-review` at the fix stage. It teaches an agent to write the
least code that works, which is the same argument as the incremental path from the other end:
Forge governs which decisions get made, ponytail governs how much code the answer turns into.

**It is required (decision 062, superseding 058).** Setup stops without it and the readiness
check is fatal, on the owner's argument that the output of this product is somebody else's
codebase, so the thing keeping that code small is not a nice-to-have. The cost is written down
rather than argued away: Forge now breaks if a third-party plugin changes name, layout or
availability, and detection is a filesystem guess about a directory layout Claude Code owns.
There is one way through, per decision 004's shape: `record_override`, explicit, recorded.

Still kept out of `ROUTE`, which stays the deterministic table of things that ship with Forge or
the pinned library. And **where they disagree Forge wins**: the security floor is not
overridable, and a recorded decision is not optimised away because a shorter version exists.

Install: `/plugin marketplace add DietrichGebert/ponytail` then `/plugin install ponytail@ponytail`.

`scripts/companion.py` is the hook that brings it in with Forge (decision 059), on SessionStart:
one line when it is installed, the install command once per project when it is not, silence
outside a Forge project and on every error. The routing table alone was not enough, because a
table is read by whatever asks it, and four rules in this repository have shipped in code that
nothing called. `FORGE_NO_COMPANION=1` turns it off.

## What a subject owes before it is built

`scripts/forge_topics.py`, decisions 053 to 055. The foundation asks its questions and stops.
Everything after it used to be whatever the planner thought of in the moment, so a step called
"store the todos" could be asked one question, or none worth the name, and the database was
chosen by whichever model was writing that turn.

Eight subjects now carry the questions they owe, twenty in all:

| Subject | Owes |
|---|---|
| database | which one (Postgres, Supabase, Neon, SQLite, MySQL, Mongo), where it runs, how the shape changes once there is real data, how the code talks to it, what a test opens |
| deploy | how many pieces run, what starts and restarts them (nothing, systemd, Compose, a platform, Kubernetes), rollback, how a change gets there, how you hear it broke |
| config | where settings live, what happens when one is missing, where the secrets are |
| auth | how someone proves who they are, what each may see |
| api | its shape, and what a caller gets when it fails |
| jobs, uploads, payments | one question each, same shape |

Asked **once per project**, by whichever step needs them first, and `next_gap` returns an
`unasked` gap until they are recorded, so the write is refused rather than discouraged. A step
that touches none of them is not held up: a gate that fires on everything is one people learn to
type past. Each question also carries one line on **what a bad answer costs**, shown with a bar,
because the questions with the worst consequences sound the most administrative.

## What a menu has to be

`scripts/forge_options.py`, decisions 047 and 048. This was reported as "it is giving very
limited options", and underneath it **nothing generated options at all**: one question carried a
menu and the rest were improvised against no rule, which is how "Docker, or run it locally"
reached a project that runs on one laptop.

- **Three at least, six at most, each carrying its consequence.** `render_decision` refuses to
  draw a block that breaks it. Two is a false binary; a real one passes `binary_because` and the
  sentence goes on screen.
- **The menu narrows against the recorded facts**, and what it removes is shown struck out with
  the reason, because the exclusion teaches. A question is never narrowed by the fact its own
  answer produces.
- **Each question names its concept.** A user who remembers picking B has learned nothing.

The idea comes first because every later question is asked *inside* it. The
stack comes next because "where is the data kept" means different things for a
browser app and a Django service — and asking storage first is how a real run
ended up offering `localStorage` to a project that had never chosen a browser.

The order is fixed in code rather than chosen by the planner, because a planner
that picks its own order will sometimes pick badly and **nobody will notice** —
a skipped question is invisible in a way a wrong answer is not.

---

## Recurring failure, worth internalising

The same bug happened four times in different clothes: **the rule was in the
code, and the code was not in the path.**

- `server.run()` sat above the review tools, so they never registered — while
  tests passed, because a test imports the module rather than running it.
- The governor only blocked between asking and answering, so a fresh project
  allowed everything.
- The fixed question sequence existed and was tested, but `start.md` never
  called it, so the planner improvised its own questions.
- `EXCLUDED_FROM_HASH` was defined and never read.

When adding a guarantee, the question is not "is it implemented" but "what
calls it, and would I notice if nothing did".

Two more from the visual layer, same shape:

- **`isatty()` answers "am I a terminal", not "will this be seen".** The MCP
  server writes down a pipe, so every colour constant was the empty string
  inside it: the palette, the legend and the tests were all correct and none of
  them ran anywhere that could emit an escape byte. Then, forced back on, the
  codes were stripped by the client's markdown renderer anyway. Find which
  process emits the output and what it believes about its own stdout before
  changing anything about how it is drawn.
- **Never document a command you have not watched run.** `/plugin update
  forge@forge-marketplace` was written on the assumption that the slash commands
  mirror the CLI. Claude Code reads `/plugin` as the plugin browser and opens
  it, arguments and all, so the user landed in a list of 284 plugins. It did not
  fail; it did something else quietly.

Two related traps:

- **Tests that cannot fail.** Several shipped: a trailing `or True`, a colour
  test that asserted nothing on a real terminal, an encoding test that never
  handed its stream to the code under test. If a test passes with the feature
  deleted, it is decoration.
- **Escapes through shell heredocs.** Writing Python via `<<'PY'` repeatedly
  turned `\n` into real newlines and `\b` into a literal backspace byte — the
  latter silently disabled every redaction pattern while looking correct in
  every editor and diff. Use the Write tool for code containing escapes.

---

## Running it

```bash
pip install "mcp>=2.0.0,<3"
```

```
/plugin marketplace add Hassaan146/forge-marketplace
/plugin install forge@forge-marketplace
```

Then per project: `/forge:start`, and afterwards `/forge:status`, `/forge:mode`,
`/forge:update`, `/forge:stop`. `/forge:add` is the path for adding a feature to
a project that already works.

Recommended alongside it, not required:

```
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```

Check a machine before installing anything:

```bash
python scripts/forge_preflight.py
```

Tests:

```bash
python -m pytest
```

876 tests, ~88% coverage, no model calls anywhere in the suite.

---

## State, honestly

**Built:** all ten phases. 876 tests. The governor, safety hooks, gates, state
layer with a verified hash chain (68 records, ids 1 to 68; 12 was answered by 021 to 023 and never written), MCP engine, skills, subagents,
the pipeline with three modes, usage metering, two-reviewer integration,
opt-in push, `prompts.md` and Code Explained generation.

**Changed most recently (2026-08-13, decisions 047 to 055):** the option rules,
the branching interrogation, the recorded reason in the user's own words, build
notes, a wider block that names its concept, and the per-subject interrogation
above. `resume` is the tool `/forge:start` now calls first in a project that
already has notes; `step_questions` is the one the planner calls before writing
any code for a step.

**Not done:**

- **The ≥2-provider requirement is unmet.** Decision 027 chose Anthropic-only
  because Forge drives Claude Code and a second provider has nowhere to attach.
  The Phase 10 live-comparison deliverable is therefore also unmet. Recorded,
  not discovered late — but a mentor may push back, and the cheapest answer is a
  standalone benchmark script that touches no part of the pipeline.
- **The live file-by-file build ticker.** `forge_build.py` is designed —
  skeleton-first ordering per stack, one file at a time, each announced as it is
  written — and was interrupted mid-write. Not committed.
- **Presentation, demo video, reflection document.**

**Known friction, now handled:** the installed plugin lagged the working copy for
four sessions running, and every one of them opened by debugging the wrong build.
Decision 040 makes the plugin say so itself — a once-a-day version check that
prints one frame with the command to run. Still restart Claude Code rather than
reloading it: hooks and the engine register at startup.

---

## Reading order for the records

`.claude/forge/decisions/` holds 45, oldest first. The load-bearing ones:

| | |
|---|---|
| 002 | which model does which job |
| 004 | fail closed, and how an override is recorded |
| 009 | what "finished" means |
| 011 | the repository is the memory |
| 027 | Anthropic only, and the gap that leaves |
| 031 | what "clean" means when a finding is out of date |
| 032 | where the notes live in someone's project |
| 033 | the question order |
| 034 | when the governor blocks |
| 035 | one symbol per meaning |
| 036 | six colours with a key the user is taught, and a frame of its own for the ask |
| 037 | the governor gates on the build step, not the phase |
| 038 | the whole plan is shown, and accepted, before any of it is built |
| 039 | speech is gated like writing, and the colour never left the process |
| 041 | the stack options name the shape, not the technology |
| 042 | Opus 5 writes the code, and 002 is amended rather than edited |
| 043 | one file switches Forge off in a project, and deletes nothing |
| 044 | eight ways to get a block on screen, and why seven fail |
| 045 | the fenced box ships, and it is monochrome, and that is final |
| 040 | the plugin tells you when it is out of date |

`.claude/forge/code-explained.md` is the generated version of all of them, and
`prompts.md` is every question and answer, assembled from the records rather
than remembered.
