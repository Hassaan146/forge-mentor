---
type: prompts
project: Forge Mentor
entries: 32
generated: 2026-08-08
---

# Prompts — Forge Mentor

Generated from the decision records, not written afterwards. Each entry is what Forge actually asked and what was actually answered, recorded at the time.

Anything credential-shaped is blanked before it is written here — this file sits in the project root and the repository may be public. The full text is always in `.claude/forge/decisions/`.

## Which model did what

Decision 002 sends different work to different models, so a single-model log would misrepresent how this was built.

| step | model |
|---|---|
| the question | `claude-fable-5` |
| the record | `claude-haiku-4-5` |
| the code | `claude-opus-4-8` |
| the review fixes | `claude-opus-4-8` |

---

## 001 · How does Forge save project notes?

**Asked:**

> How does Forge save project notes?

**Options put to the user:**

- **A** — both as readable documents
- **B** — both in a strict computer format
- **C** — mixed: strict progress note, readable decision notes

**Answered by the user:** A, refined — both files are readable documents with a strict labelled

**Reasoning given:**

> The user must be able to read either file himself. And when usage runs out on one
account and he switches to another, a brand-new session with no memory of the project
must be able to read these files and carry on. Nothing hidden, nothing tied to one
session or one account.

---

## 002 · Which AI does which job?

**Asked:**

> Which AI does which job?

**Options put to the user:**

- **A** — one AI for all four jobs
- **B** — two AIs: a strong one for thinking/coding, a cheap one for small jobs
- **C** — best-fit AI for each job

**Answered by the user:** C

**Reasoning given:**

> The best-thinking AI is slower and costs more. Putting it on the tidy-up job — which
runs hundreds of times in a build — is exactly what makes running costs explode. Putting
a cheap fast AI on teaching produces shallow lessons, which defeats the product. Keeping
the jobs separate protects both quality and cost.

---

## 003 · Can the user change which AI does which job?

**Asked:**

> Can the user change which AI does which job?

**Options put to the user:**

- **A** — fixed inside Forge, user cannot change it
- **B** — a settings file the user edits freely
- **C** — defaults ship with Forge; a settings file overrides them

**Answered by the user:** C, refined with three added rules.

**Reasoning given:**

> Defaults protect the beginner, who is the main user. The override solves the real problem
that a cheaper plan may not include Fable 5. Warning instead of blocking respects that it
is the user's project — the same principle as the rest of Forge: teach the consequence,
then let the human decide.

---

## 004 · What happens if Forge's safety check breaks — or the user demands code anyway?

**Asked:**

> What happens if Forge's safety check breaks — or the user demands code anyway?

**Options put to the user:**

- **A** — stop everything, no way through
- **B** — warn and carry on
- **C** — stop by default, with a deliberate recorded way out

**Answered by the user:** C, refined.

**Reasoning given:**

> The guarantee is the product. If it can disappear quietly, it was never a guarantee. But
locking someone out of their own project because of a bug in Forge is not acceptable
either. An explicit command plus a specific confirmation keeps the promise real while
leaving the human in charge.

---

## 005 · How does your code get a second opinion?

**Asked:**

> How does your code get a second opinion?

**Options put to the user:**

- **A** — push first, always; CodeRabbit reviews the pull request
- **B** — review locally, never push
- **C** — local checks always, CodeRabbit only if the user pushes

**Answered by the user:** A — overruled, with reasons the recommendation missed.

---

## 006 · Who creates the project repository, and is it public or private?

**Asked:**

> Who creates the project repository, and is it public or private?

**Options put to the user:**

- **A** — Forge creates it, public by default
- **B** — Forge creates it, private by default
- **C** — the user connects their own repository

**Answered by the user:** C, refined.

---

## 007 · Where do people get Forge from?

**Asked:**

> Where do people get Forge from?

**Options put to the user:**

- **A** — public from the start
- **B** — private, invite only
- **C** — private while building, public at release

**Answered by the user:** A

**Reasoning given:**

> **It is consistent with decision 005.** The user chose to push on every step precisely
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

---

## 008 · How much should it cost to run?

**Asked:**

> How much should it cost to run?

**Options put to the user:**

- **A** — show usage, never interfere
- **B** — show usage and warn at points along the way
- **C** — warn, plus a spending limit the user sets

**Answered by the user:** B now, C later.

---

## 009 · What counts as "finished" for each step?

**Asked:**

> What counts as "finished" for each step?

**Options put to the user:**

- **A** — the tests pass
- **B** — tests pass and the review is clean
- **C** — tests pass, review clean, and the user explains it back

**Answered by the user:** C

**Reasoning given:**

> The project's thesis is *the decision is the lesson*. If a step can be marked finished
while the person still does not understand it, the product has failed at its one job.
The two conditions keep the bar real while keeping it light in feel — consistent with the
live pace (R7) and warn-don't-block (decision 004).

---

## 010 · Does Forge need a second AI company, or is Anthropic-only correct?

**Asked:**

> Does Forge need a second AI company, or is Anthropic-only correct?

**Answered by the user:** Anthropic-only for the pipeline — user decision, with one requirement still unmet

---

## 011 · How is history preserved when the user switches to another account?

**Asked:**

> How is history preserved when the user switches to another account?

**Answered by the user:** The repository is the memory — the chat is not

---

## 013 · What does "live session" mean in practice, and what is actually achievable?

**Asked:**

> What does "live session" mean in practice, and what is actually achievable?

**Answered by the user:** One answer triggers a continuous stream, not a round trip

---

## 014 · What does /forge:start actually do?

**Asked:**

> What does /forge:start actually do?

**Answered by the user:** Connect accounts, explain the workflow, request permissions — all mandatory

---

## 015 · What is the plugin called, and how is it versioned?

**Asked:**

> What is the plugin called, and how is it versioned?

**Answered by the user:** Forge Mentor, starting at v0.1.0

---

## 016 · Is the .forge/ folder committed or ignored?

**Asked:**

> Is the .forge/ folder committed or ignored?

**Answered by the user:** Committed to the project repository and pushed to GitHub

---

## 017 · Does Forge work without all permissions granted? (resolves 006 vs 014)

**Asked:**

> Does Forge work without all permissions granted? (resolves 006 vs 014)

**Options put to the user:**

- **A** — 014 wins: every permission mandatory, no partial mode
- **B** — 006 wins: core works, review optional
- **C** — split: file access mandatory, review optional with warnings

**Answered by the user:** A

---

## 018 · How do we stop the notes from causing git conflicts?

**Asked:**

> How do we stop the notes from causing git conflicts?

**Answered by the user:** a question becomes a decision file the moment it is *asked*, carrying

---

## 019 · What holds the project's state across account switches?

**Asked:**

> What holds the project's state across account switches?

**Answered by the user:** Local files, one writer, re-read every session

---

## 020 · How does Forge know a decision record is genuine?

**Asked:**

> How does Forge know a decision record is genuine?

**Options put to the user:**

- **A** — trust any record
- **B** — sign what Forge writes; unsigned records show as unverified
- **C** — sign and reject anything unsigned

**Answered by the user:** B

---

## 021 · Tamper-evident records, or true signing?

**Asked:**

> Tamper-evident records, or true signing?

**Options put to the user:**

- **A** — fingerprint + chain, no secret
- **B** — secret-key signing
- **C** — both, with two trust levels

**Answered by the user:** A

---

## 022 · What happens when the chain is broken or a record is hand-written?

**Asked:**

> What happens when the chain is broken or a record is hand-written?

**Answered by the user:** Warn, stop, and restore the record from its committed version

---

## 023 · How is the chain stored?

**Asked:**

> How is the chain stored?

**Answered by the user:** the chain is written to `.forge/chain.log` and marked read-only on disk

---

## 024 · Where do the usage numbers come from?

**Asked:**

> Where do the usage numbers come from?

**Options put to the user:**

- **A** — read Claude Code's session transcripts
- **B** — estimate from the text Forge sends
- **C** — count only when Forge calls a model directly
- **D** — drop the meter from v1

**Answered by the user:** A

---

## 025 · How do two reviewers share one set of notes?

**Asked:**

> How do two reviewers share one set of notes?

**Options put to the user:**

- **A** — one file per pull request, both reviewers merged, each finding tagged
- **B** — one file per reviewer per pull request
- **C** — merged, but only CodeRabbit's findings count toward "done"

**Answered by the user:** A

---

## 026 · Who writes the review file into the repository?

**Asked:**

> Who writes the review file into the repository?

**Options put to the user:**

- **A** — a GitHub workflow fetches the review and commits the file
- **B** — Forge commits and pushes it from the user's machine after fetching
- **C** — Forge writes it locally; it rides along in the next ordinary commit

**Answered by the user:** A

---

## 027 · Does the second-provider requirement change the pipeline?

**Asked:**

> Does the second-provider requirement change the pipeline?

**Options put to the user:**

- **A** — Anthropic only
- **B** — OpenRouter as an API-key fallback tier
- **C** — a direct second-party API key
- **D** — drive the local Codex CLI as a second subscription path

**Answered by the user:** A

---

## 028 · Where do Forge's skills come from?

**Asked:**

> Where do Forge's skills come from?

**Options put to the user:**

- **A** — install the full 438-skill library on the user's machine at setup
- **B** — install only the ~40 skills Forge's routing map actually names
- **C** — ship the routed subset, offer the full library as an opt-in

**Answered by the user:** A

---

## 029 · Which model actually runs a job — who decides at dispatch?

**Asked:**

> Which model actually runs a job — who decides at dispatch?

**Options put to the user:**

- **A** — the subagent's own file declares the model; `choose_model` advises and logs
- **B** — the MCP server owns dispatch and configures the subagents
- **C** — subagent files only; drop `choose_model`

**Answered by the user:** A

---

## 030 · What actually differs between the three modes?

**Asked:**

> What actually differs between the three modes?

**Options put to the user:**

- **A** — the modes differ only in how many decisions Forge makes on its own
- **B** — as A, and Auto also skips the explain-back gate
- **C** — two modes; drop Auto

**Answered by the user:** A

---

## 031 · What does "clean" mean when a finding is about code that has changed?

**Asked:**

> What does "clean" mean when a finding is about code that has changed?

**Options put to the user:**

- **A** — resolve the thread on GitHub as part of the fix loop
- **B** — judge each finding against the current file and mark superseded ones
- **C** — count only findings raised against the current head commit

**Answered by the user:** A and B together

---

## 032 · Where do Forge's notes live inside someone's project?

**Asked:**

> Where do Forge's notes live inside someone's project?

**Options put to the user:**

- **A** — `.claude/forge/` for everything Forge keeps
- **B** — stay at `.forge/` in the project root
- **C** — `.claude/forge/` for state, and `prompts.md` at the root as well

**Answered by the user:** C

---

## 033 · What does Forge ask first, and in what order?

**Asked:**

> What does Forge ask first, and in what order?

**Options put to the user:**

- **A** — a fixed foundation sequence, the stack first
- **B** — let the planner choose an order per project
- **C** — the stack first, the rest chosen per project

**Answered by the user:** A

---
