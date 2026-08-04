---
type: progress
project: forge
stage: phase-6-complete
questions_total_estimate: 27
questions_answered: 26
next_question: none — Phase 7 next
open_question: none
override_active: false
updated: 2026-08-04
---

# Where we are

**Stage:** Foundation interrogation **complete** — all 9 questions decided (Phase 1, dogfood stage 1).

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
current on its own (decision 026). 299 tests, 87% coverage.

**Two bugs found while building it**, both invisible to the tests that existed:

- `server.run()` sat *above* the review tool definitions. Because it blocks, `fetch_review`
  and `check_review_setup` were never registered in a real session — while the tests passed,
  because a test imports the module rather than running it.
- The usage meter counted one model reply three times. Claude Code writes a reply with
  several tool calls as several records, each carrying an identical copy of the same usage.

**Next:** Phase 7 — skills and subagents.

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
