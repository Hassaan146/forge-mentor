---
type: progress
project: forge
stage: built-and-in-use
questions_total_estimate: 59
questions_answered: 58
next_question: none
open_question: none
override_active: false
updated: 2026-08-13
---

# Where we are

All ten phases are built. 822 tests, 88% coverage, 60 decision records, chain verified.

## Adding without disturbing, and a companion plugin (2026-08-13)

Decisions [056](decisions/056-what-happens-when-someone-adds-a-feature-to-a-project-forge.md)
to [059](decisions/059-how-does-the-companion-plugin-actually-reach-a-build-rather.md).

**The incremental path did not exist.** Every gate reads the phase list, so once the last phase
was built `next_gap` found no unbuilt step and opened: a user coming back to add one feature got
no questions at all. `/forge:add` and `plan_feature` read the recorded decisions the feature
lives inside, name anything it contradicts along with the decision that would have to be
reopened, and ask only what the feature owes. `add_phase` appends rather than recompiling.
Changing a recorded decision is a new record with `supersedes`, never an edit.

**ponytail is wired in as a companion**, not a dependency: additive at the building and review
stages, detected rather than assumed, reported by the preflight, and Forge wins where they
disagree. `scripts/companion.py` is the SessionStart hook that brings it in with Forge, because
a routing table is only read by whatever asks it, and this repository has shipped four rules
that lived in code nothing called. Kept out of `ROUTE`
because ROUTE is the deterministic table and a separately installed plugin cannot be part of a
guarantee.

## The final check: a subject is not one question (2026-08-13)

Decisions [053](decisions/053-what-does-a-subject-owe-the-user-before-code-touching-it-is.md)
to [055](decisions/055-does-a-question-say-what-goes-wrong-if-it-is-answered-badly.md).

Asked for as a last pass: *"you have to ask me about the database, then how I want to configure
it, then whether I want to deploy, whether I want it orchestrated. I want to figure out whether
I have to use Supabase or something else."* None of it could happen. **The whole product held
twelve questions**, all of them in the foundation, and everything after it was written by the
planner in the moment.

`scripts/forge_topics.py` holds eight subjects and the twenty questions they owe, asked once per
project by whichever step touches them first, gated in `next_gap` rather than asked for in a
brief. The options name products: Postgres, Supabase, Neon, SQLite, MySQL, Mongo, and for
orchestration nothing, systemd, Compose, a platform, Kubernetes. Every question carries what a
bad answer costs.

Two bugs found by running it rather than by testing it: the keyword fallback read facts out of
the open idea question, so "a to-do app I can use from my phone and my laptop" was recorded as
local-only and struck Supabase off a hosted project's menu; and the progress line counted a
database step against every question in the file instead of against the five it owed.
**Read `context.md` at the repository root first**: it is the cold-start brief and it is
kept current. This file is the log.

## The interrogation was rewritten after a user watched it run (2026-08-13)

Decisions [047](decisions/047-how-many-options-does-a-question-put-in-front-of-the-user.md)
to [052](decisions/052-is-the-block-wide-enough-and-does-it-say-what-the-question-i.md).

The report was one sentence: "it is giving very limited options". Underneath it, **nothing
generated options at all.** One question in the product carried a menu (the stack, four
options); every other foundation question carried none, and every per-step question in the
build loop carried none either. So the options a user saw were improvised in the moment
against no rule: no floor on how many, no requirement that each carry its cost, and nothing
tying them to what the project had already decided. "Docker, or run it locally" was the
result, offered to a project that had said three questions earlier that it runs on one laptop.

What changed:

- `scripts/forge_options.py` holds the rule. Three options minimum, six maximum, each with its
  consequence. `render_decision` refuses to draw a block that breaks it, so a per-step question
  cannot be improvised thin. A genuine two-sided question passes `binary_because`, and that
  sentence goes on screen.
- Menus narrow against the recorded facts, and what they remove is **shown struck out with the
  reason**. The exclusion is the cheapest teaching in the interrogation.
- Answers open further questions. Deploying opens four; staying local opens the backup question
  instead; a second person opens identity and permissions. The total moves, and R4 already
  required showing it.
- Every question names the **concept** it teaches, and the block is 92 columns rather than 74,
  because an option and its consequence did not fit on one line.
- The user's own reason is recorded in its own section, and a load-bearing answer is refused
  without it.
- The builder records the choices it makes while writing code, and those records **cannot open a
  step's gate**.

Two bugs the new tests found immediately, both in the fact-reading: a leading "a " was read as
option A, so "A small server I rent" was recorded as "Only on my machine"; and a question was
being narrowed by the fact its own answer produces, so the delivery question struck out four of
its own five options.

**Stage before this:** foundation interrogation complete, all 9 original questions decided
(Phase 1, dogfood stage 1).

**Challenge stage: complete** — see [challenge-001.md](challenge-001.md). Premortem + redteam
found **3 critical** issues (C1 second provider, C2 state-file trust, C3 review injection)
and 7 high-priority ones. C2 and C3 are resolved in code; **C1 is closed by decision
[027](decisions/027-one-ai-company.md) — accepted, not solved.**

| Phase | State |
|---|---|
| 2 — Plugin foundation | complete, **merged to `main`** |
| 3 — State layer | code complete · [PR #1](https://github.com/Hassaan146/forge-mentor/pull/1) open |
| 4 — Hooks & enforcement | code complete · [PR #2](https://github.com/Hassaan146/forge-mentor/pull/2) open |
| 5 — MCP server core | code complete · [PR #3](https://github.com/Hassaan146/forge-mentor/pull/3) open |
| 6 — MCP server extended | code complete · [PR #4](https://github.com/Hassaan146/forge-mentor/pull/4) open |
| 7 — Skills & subagents | code complete · [PR #5](https://github.com/Hassaan146/forge-mentor/pull/5) open |
| 8–10 | branches and draft pull requests opened; no code yet |

**Phase 6 delivered:** the usage meter (decision 024), cache-stable request assembly with
drift detection, the second reviewer (decision 025), and the workflow that keeps review notes
current on its own (decision 026).

**Phase 7 delivered:** Forge's own four skills, the stage→skill table, the library install
pinned to a reviewed commit (decision 028), and four subagents whose declared models are
proven to agree with the server's routing (decision 029).

339 tests, 87% coverage.

**The review loop is running for real.** The workflow fetches both reviewers into
`.forge/reviews/pr-<n>.md` and commits it without anyone asking — first proved on this
repository's own pull request #4.

### The dogfood run that found the real one (2026-08-09)

Forge was run against a fresh to-do app in `H:\Skills\todo-test`. It asked its foundation
questions, then wrote `index.html`, `style.css`, `db.js` and `app.js` in a single turn —
**nothing was asked after the last foundation question**, and every write was permitted.

The cause was in `writes_allowed`, not in any prompt. Its two conditions — "is a question open"
and, after decision 034, "is the foundation answered" — are both true exactly once, at the
start. After the last foundation answer it returned True and had nothing left to check, ever.
The interactive per-step loop existed only in the planner's brief, which makes it advice.

Closed by [037](decisions/037-what-is-the-unit-of-work-the-governor-gates-on-once-the-foun.md)
and rule R13: a phase is not buildable, only its steps, and the gate opens for one step at a
time. `scripts/forge_steps.py` holds the ledger; `plan_steps`, `current_step` and `step_built`
drive it.

**Second finding, same run.** Watching it continue, the user was asked *"How is this project
tested?"* — a question whose answer applies to every phase — having been shown phase one only,
which was already built. Their objection: the plan should be made and shown whole, up front.

Closed by [038](decisions/038-when-does-the-user-see-the-shape-of-the-whole-project.md) and
rule R14. `compile_phases` writes every phase in one call; `show_roadmap` renders the spine and
regenerates a self-contained `roadmap.html`; acceptance is a recorded decision carrying
`plan-accepted`, and nothing is written until it exists. Five gates now run in order, each
naming itself: unreadable phase file → no phases → plan not accepted → phase not broken into
steps → current step undecided.

Two things this did **not** fix, both worth knowing:

- The installed plugin is **v0.1.0**, which predates the `.claude/forge/` move (decision 032)
  and the foundation gate (034). `todo-test` has a `.forge/` directory, so the current code
  cannot even see it. **The plugin has to be reinstalled from source before any of this
  applies.**
- `todo-test` itself is still in the old layout and has no `phases/`. It needs migrating or
  restarting before it can be used as a dogfood target again.

### Bugs the tests did not catch, found this phase

| Where | What |
|---|---|
| `forge_server.py` | `server.run()` sat *above* the review tools. It blocks, so those tools never registered in a real session — while tests passed, because a test imports the module rather than running it. |
| `forge_meter.py` | Counted one model reply three times. Claude Code writes a reply with several tool calls as several records, each carrying an identical copy of the same usage. |
| `safety.py` | `</UNTRUSTED>` escaped the wrapper — matched case-insensitively, neutralised case-sensitively. The one regression test covered lowercase only, so it could not fail. |
| `safety.py` | Secret-path resolution failed *open*, reporting "could not check" as "it is fine", while the docstring directly above claimed the opposite. |
| `forge-review.yml` | Ran the branch's own review script with a write-scoped token, and interpolated a branch name straight into a shell command. |
| `forge_skills.py` | The structurer had no tool to record with, and no stage routed to it — an agent that could never run. |
| `forge_ui.py` | Crashed a cp1252 Windows console. Printing the banner raised `UnicodeEncodeError`, which would have taken a hook down with it. |

**Next:** Phase 8 — pipeline integration.

## Open problem — "clean" counts the wrong thing

Decision 009 gates a step on the review being clean, and `is_clean` is computed from
unresolved review comments on the pull request. Running the loop for real showed the flaw:
**a reviewer does not retract a comment when the code beneath it changes.** Every finding on
pull requests #4 and #5 is now either fixed in the code or declined with reasoning, and both
still report open findings — every one of them pointing at a line that no longer says what the
comment describes.

So a phase gated on `is_clean` can never close by fixing things. Superseded comments only
disappear when a human resolves them in the GitHub interface.

Three ways out, none chosen yet:

1. Resolve threads through the API as part of the fix loop, so the count means what it says.
2. Judge a finding against the current file and mark it superseded when the line has moved.
3. Change the bar: count only findings raised against the current head commit.

This needs a decision before any phase can be *merged*, and it is the first thing Phase 9
should settle — it is exactly the kind of defect the dogfood run exists to find.

## Known gaps, carried deliberately

- **Two-provider requirement unmet** — decision 027. Accepted with the consequence written down.
- **Forge's own decision records are unsigned.** Phase 4 built the fingerprint-and-chain
  machinery but it was never applied to the 22 records written before it existed, and
  `.forge/chain.log` does not exist here. Bulk-signing belongs in Phase 9, where Forge is
  turned on itself.

## Questions

| # | Question | Status | Decision |
|---|---|---|---|
| 1 | How Forge saves your project notes | ✅ decided | Both readable, with a strict labelled top section → [001](decisions/001-state-file-format.md) |
| 2 | Which AI does which job | ✅ decided | Best-fit per job: Fable 5 teaches, Opus 4.8 writes, Haiku 4.5 tidies → [002](decisions/002-which-ai-does-which-job.md) |
| 3 | Can the user change which AI does which job | ✅ decided | Yes, via settings — warn, never block; ordered fallback list → [003](decisions/003-changing-the-ai-mapping.md) |
| 4 | What happens if Forge's own safety check breaks | ✅ decided | Blocked by default; explicit command + specific confirmation is the only way through → [004](decisions/004-when-the-safety-check-fails.md) |
| 5 | How your code gets a second opinion | ✅ decided | Push to GitHub instantly → pipeline → CodeRabbit → Opus 4.8 fixes → [005](decisions/005-review-and-push.md) |
| 6 | Your project repository — who creates it, public or private | ✅ decided | User creates it; Forge only with GitHub sign-in; private first; public only if reviews require it → [006](decisions/006-project-repository.md) |
| 7 | Where people download Forge from | ✅ decided | Public from the first commit → [007](decisions/007-where-forge-lives.md) |
| 8 | How much it should cost to run | ✅ decided | Show usage + warn at thresholds now; user-set spending limit deferred → [008](decisions/008-cost-and-usage.md) |
| 9 | What counts as "finished" for each step | ✅ decided | Tests + clean review + explain-back; reflective not graded; scales with step size; 3-strike escalation → [009](decisions/009-what-counts-as-finished.md) |

| 10 | Does Forge need a second AI company | ✅ decided | Anthropic-only pipeline — user override of challenge C1; two-provider requirement **still unmet**, revisit before submission → [010](decisions/010-single-provider.md) |
| 11 | Continuing on another account | ✅ decided | Repository is the memory; progress file must hold in-flight state → [011](decisions/011-continuing-on-another-account.md) |
| 12 | How signed decision records work (challenge C2) | ✅ decided | Fingerprint + chain, no secret — answered in Phase 4 by [021](decisions/021-tamper-evident-records.md), [022](decisions/022-chain-enforcement-and-repair.md), [023](decisions/023-chain-file-storage.md) |
| 13 | What "live session" means in practice | ✅ decided | One answer → one continuous streamed sequence; never split a moment across turns → [013](decisions/013-live-session-not-turn-based.md) |
| 14 | What `/forge:start` does | ✅ decided | Connect accounts (delegated sign-in, never typed credentials), explain workflow, request permissions — **all mandatory** → [014](decisions/014-setup-flow.md) |
| 15 | Name and version | ✅ decided | **Forge Mentor**, v0.1.0 → [015](decisions/015-name-and-version.md) |
| 16 | Is `.forge/` committed | ✅ decided | Committed in the project repo and pushed to GitHub → [016](decisions/016-forge-folder-committed.md) |
| 17 | Does Forge work without all permissions | ✅ decided | No — all mandatory; 006 amended; public/private cost fork shown at setup → [017](decisions/017-all-permissions-mandatory.md) |
| 18 | Duplicate decision ids across branches | ✅ decided | Accepted; ordering stays deterministic → [018](decisions/018-no-git-conflicts.md) |
| 19 | What must survive an account switch | ✅ decided | State re-read from disk every time; nothing cached → [019](decisions/019-state-survives-account-switch.md) |
| 20 | Can a record be trusted | ✅ decided | Records must be tamper-evident → [020](decisions/020-record-authenticity.md) |
| 21 | Tamper-evident, or true signing | ✅ decided | Fingerprint + chain, no secret — a secret cannot travel between machines → [021](decisions/021-tamper-evident-records.md) |
| 22 | What happens when the chain breaks | ✅ decided | Warn, stop, and repair from the committed version; never delete → [022](decisions/022-chain-enforcement-and-repair.md) |
| 23 | Where the chain is stored | ✅ decided | `.forge/chain.log`, read-only where the filesystem allows → [023](decisions/023-chain-file-storage.md) |
| 24 | Where usage numbers come from | ✅ decided | Claude Code's own session logs — measured, never estimated → [024](decisions/024-where-usage-numbers-come-from.md) |
| 25 | How two reviewers share one set of notes | ✅ decided | Both in one file per pull request, each finding tagged → [025](decisions/025-two-reviewers-one-file.md) |
| 26 | Who writes the review file to GitHub | ✅ decided | A workflow in the repository, not Forge on the user's machine → [026](decisions/026-who-writes-the-review-file.md) |
| 27 | Does the two-provider rule change the pipeline | ✅ decided | No — Anthropic only; the gap is accepted and written down → [027](decisions/027-one-ai-company.md) |
| 28 | Where Forge's skills come from | ✅ decided | Four bundled in the plugin; the library installed whole at setup, pinned to a reviewed commit → [028](decisions/028-where-skills-come-from.md) |
| 29 | Which model actually runs a job | ✅ decided | The subagent's own file, because Claude Code reads it at dispatch; `choose_model` advises → [029](decisions/029-which-model-runs-a-job.md) |
| 30 | What differs between the three modes | ✅ decided | Only how much gets decided for you; the governor rule and the explain-back gate hold in all three → [030](decisions/030-the-three-modes.md) |

*The number of questions can move — some answers close two at once, others open a new one.*

## Conflicts — resolved

**006 vs 014 — resolved by [017](decisions/017-all-permissions-mandatory.md).** All
permissions mandatory; 006's reduced-mode clause removed. Downstream consequence recorded:
free review requires a public repository, so the public/private cost fork must be presented
at setup.

## Feature requests raised during interrogation

| # | Request | Where it lands |
|---|---|---|
| F1 | Distinct visual identity — coloured banner, six-colour meaning system, emoji state markers (⚒ ⛔ ✅ ⚠️ 💡 ★ 🎓), framed question blocks, progress bar, live "which AI is working" indicator, usage meter. Mockup: `forge-visual-identity.html` | Phase 2 (plugin shell), applied throughout |

## Design rules learned

See [design-rules.md](design-rules.md) — 10 rules so far, all from user feedback.
