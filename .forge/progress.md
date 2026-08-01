---
type: progress
project: forge
stage: phase-2-complete
questions_total_estimate: 12
questions_answered: 16
next_question: none — Phase 3 next
open_question: none
override_active: false
updated: 2026-07-31
---

# Where we are

**Stage:** Foundation interrogation **complete** — all 9 questions decided (Phase 1, dogfood stage 1).
No code written yet, by design.

**Challenge stage: complete** — see [challenge-001.md](challenge-001.md). Premortem + redteam
found **3 critical** issues (C1 second provider, C2 state-file trust, C3 review injection)
and 7 high-priority ones. C1 and C2 must be resolved before Phase 2 begins.

**Phase 2: complete.** Plugin scaffolded, validated against the official spec, published,
and installed from GitHub end to end. The governor is proven to block writes (7/7 tests).

**Next:** Phase 3 — the state layer.

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
| 12 | How signed decision records work (challenge C2) | ⏳ open | deferred to Phase 4 (governor) — not needed for Phase 2 |
| 13 | What "live session" means in practice | ✅ decided | One answer → one continuous streamed sequence; never split a moment across turns → [013](decisions/013-live-session-not-turn-based.md) |
| 14 | What `/forge:start` does | ✅ decided | Connect accounts (delegated sign-in, never typed credentials), explain workflow, request permissions — **all mandatory** → [014](decisions/014-setup-flow.md) |
| 15 | Name and version | ✅ decided | **Forge Mentor**, v0.1.0 → [015](decisions/015-name-and-version.md) |
| 16 | Is `.forge/` committed | ✅ decided | Committed in the project repo and pushed to GitHub → [016](decisions/016-forge-folder-committed.md) |
| 17 | Does Forge work without all permissions | ✅ decided | No — all mandatory; 006 amended; public/private cost fork shown at setup → [017](decisions/017-all-permissions-mandatory.md) |

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
