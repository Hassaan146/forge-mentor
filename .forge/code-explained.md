---
type: code-explained
decisions: 30
chosen_by_you: 30
updated: 2026-08-05
---

# Why Forge Mentor is built the way it is

30 decisions shape this project. You made 30 of them.

Read in the order they were decided, because each one was made knowing the
ones above it — which is not the order the files are listed in.

---

## 001 · How does Forge save project notes?

**A, refined — both files are readable documents with a strict labelled**

Also considered: **B** — both in a strict computer format; **C** — mixed: strict progress note, readable decision notes

The user must be able to read either file himself. And when usage runs out on one
account and he switches to another, a brand-new session with no memory of the project
must be able to read these files and carry on. Nothing hidden, nothing tied to one
session or one account.

Full record: [`001`](decisions/)

## 002 · Which AI does which job?

**C**

Also considered: **A** — one AI for all four jobs; **B** — two AIs: a strong one for thinking/coding, a cheap one for small jobs

The best-thinking AI is slower and costs more. Putting it on the tidy-up job — which
runs hundreds of times in a build — is exactly what makes running costs explode. Putting
a cheap fast AI on teaching produces shallow lessons, which defeats the product. Keeping
the jobs separate protects both quality and cost.

Full record: [`002`](decisions/)

## 003 · Can the user change which AI does which job?

**C, refined with three added rules.**

Also considered: **A** — fixed inside Forge, user cannot change it; **B** — a settings file the user edits freely

Defaults protect the beginner, who is the main user. The override solves the real problem
that a cheaper plan may not include Fable 5. Warning instead of blocking respects that it
is the user's project — the same principle as the rest of Forge: teach the consequence,
then let the human decide.

Full record: [`003`](decisions/)

## 004 · What happens if Forge's safety check breaks — or the user demands code anyway?

**C, refined.**

Also considered: **A** — stop everything, no way through; **B** — warn and carry on

The guarantee is the product. If it can disappear quietly, it was never a guarantee. But
locking someone out of their own project because of a bug in Forge is not acceptable
either. An explicit command plus a specific confirmation keeps the promise real while
leaving the human in charge.

Full record: [`004`](decisions/)

## 005 · How does your code get a second opinion?

**A — overruled, with reasons the recommendation missed.**

Also considered: **B** — review locally, never push; **C** — local checks always, CodeRabbit only if the user pushes

Full record: [`005`](decisions/)

## 006 · Who creates the project repository, and is it public or private?

**C, refined.**

Also considered: **A** — Forge creates it, public by default; **B** — Forge creates it, private by default

Full record: [`006`](decisions/)

## 007 · Where do people get Forge from?

**A**

Also considered: **B** — private, invite only; **C** — private while building, public at release

**It is consistent with decision 005.** The user chose to push on every step precisely
because visible commit history is proof of work. That reasoning applies more strongly to
Forge itself: a public repository from the first commit makes the whole build timestamped,
visible evidence for the internship submission.

**It avoids the trap written into decision 006.** A repository that is public from the
first commit never has a private history to expose later. There is no "flip to public"
moment, so the history-exposure guard never has to run on Forge's own repo.

**Nothing in it is secret.** Forge is a teaching tool. Its value is the design and the
protocol, not concealment.

**The demo gets easier.** The mentor and other students can install it themselves during
the presentation, with the same two commands any user would run.

Full record: [`007`](decisions/)

## 008 · How much should it cost to run?

**B now, C later.**

Also considered: **A** — show usage, never interfere

Full record: [`008`](decisions/)

## 009 · What counts as "finished" for each step?

**C**

Also considered: **A** — the tests pass; **B** — tests pass and the review is clean

The project's thesis is *the decision is the lesson*. If a step can be marked finished
while the person still does not understand it, the product has failed at its one job.
The two conditions keep the bar real while keeping it light in feel — consistent with the
live pace (R7) and warn-don't-block (decision 004).

Full record: [`009`](decisions/)

## 010 · Does Forge need a second AI company, or is Anthropic-only correct?

**Anthropic-only for the pipeline — user decision, with one requirement still unmet**

Full record: [`010`](decisions/)

## 011 · How is history preserved when the user switches to another account?

**The repository is the memory — the chat is not**

Full record: [`011`](decisions/)

## 013 · What does "live session" mean in practice, and what is actually achievable?

**One answer triggers a continuous stream, not a round trip**

Full record: [`013`](decisions/)

## 014 · What does /forge:start actually do?

**Connect accounts, explain the workflow, request permissions — all mandatory**

Full record: [`014`](decisions/)

## 015 · What is the plugin called, and how is it versioned?

**Forge Mentor, starting at v0.1.0**

Full record: [`015`](decisions/)

## 016 · Is the .forge/ folder committed or ignored?

**Committed to the project repository and pushed to GitHub**

Full record: [`016`](decisions/)

## 017 · Does Forge work without all permissions granted? (resolves 006 vs 014)

**A**

Also considered: **B** — 006 wins: core works, review optional; **C** — split: file access mandatory, review optional with warnings

Full record: [`017`](decisions/)

## 018 · How do we stop the notes from causing git conflicts?

**a question becomes a decision file the moment it is *asked*, carrying**

Full record: [`018`](decisions/)

## 019 · What holds the project's state across account switches?

**Local files, one writer, re-read every session**

Full record: [`019`](decisions/)

## 020 · How does Forge know a decision record is genuine?

**B**

Also considered: **A** — trust any record; **C** — sign and reject anything unsigned

Full record: [`020`](decisions/)

## 021 · Tamper-evident records, or true signing?

**A**

Also considered: **B** — secret-key signing; **C** — both, with two trust levels

Full record: [`021`](decisions/)

## 022 · What happens when the chain is broken or a record is hand-written?

**Warn, stop, and restore the record from its committed version**

Full record: [`022`](decisions/)

## 023 · How is the chain stored?

**the chain is written to `.forge/chain.log` and marked read-only on disk**

Full record: [`023`](decisions/)

## 024 · Where do the usage numbers come from?

**A**

Also considered: **A** — read Claude Code's session transcripts; **B** — estimate from the text Forge sends; **C** — count only when Forge calls a model directly; **D** — drop the meter from v1

Full record: [`024`](decisions/)

## 025 · How do two reviewers share one set of notes?

**A**

Also considered: **B** — one file per reviewer per pull request; **C** — merged, but only CodeRabbit's findings count toward "done"

Full record: [`025`](decisions/)

## 026 · Who writes the review file into the repository?

**A**

Also considered: **B** — Forge commits and pushes it from the user's machine after fetching; **C** — Forge writes it locally; it rides along in the next ordinary commit

Full record: [`026`](decisions/)

## 027 · Does the second-provider requirement change the pipeline?

**A**

Also considered: **A** — Anthropic only; **B** — OpenRouter as an API-key fallback tier; **C** — a direct second-party API key; **D** — drive the local Codex CLI as a second subscription path

Full record: [`027`](decisions/)

## 028 · Where do Forge's skills come from?

**A**

Also considered: **B** — install only the ~40 skills Forge's routing map actually names; **C** — ship the routed subset, offer the full library as an opt-in

Full record: [`028`](decisions/)

## 029 · Which model actually runs a job — who decides at dispatch?

**A**

Also considered: **B** — the MCP server owns dispatch and configures the subagents; **C** — subagent files only; drop `choose_model`

Full record: [`029`](decisions/)

## 030 · What actually differs between the three modes?

**A**

Also considered: **A** — the modes differ only in how many decisions Forge makes on its own; **B** — as A, and Auto also skips the explain-back gate; **C** — two modes; drop Auto

Full record: [`030`](decisions/)

## 031 · What does "clean" mean when a finding is about code that has changed?

**A and B together**

Also considered: **C** — count only findings raised against the current head commit

Full record: [`031`](decisions/)
