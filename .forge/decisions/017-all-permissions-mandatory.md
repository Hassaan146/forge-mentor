---
id: 017
question: Does Forge work without all permissions granted? (resolves 006 vs 014)
status: decided
date: 2026-07-31
decided_by: user
resolves: conflict between 006 and 014
amends: 006
affects: [phase-2, phase-8]
content_sha: abc2a0c4cf80bd6c4d7f89bff4f096a93db363c164529a82e46269d633aebb69
prev_sha: fcc1c1d158f63018f0dca309a8c6c7c6dc8870523006719c9a77ba460401864e
---
# All-or-nothing — decision 014 stands, 006 is amended

**Options considered**

- **A** — 014 wins: every permission mandatory, no partial mode
- **B** — 006 wins: core works, review optional
- **C** — split: file access mandatory, review optional with warnings

**Recommended:** A · **Decided:** A

**User's reasoning:** the review service is free, so requiring it is not a real burden.

## What changes

Decision 006's clause — *"a user who does not connect a repository still gets Forge, with
review and history unavailable"* — is **removed**. There is no reduced mode. Forge either has
what it needs, or it does not run.

## ⚠ Consequence the reasoning depends on — must be stated at setup

The review service is free **on public repositories**. On private repositories it needs a
paid plan.

Decision 006 set repositories to **private first**. Combined with mandatory review, that
means:

| User's situation | What actually happens |
|---|---|
| Wants free review | The repository must be **public** |
| Wants the repository private | A **paid review plan** is required |

So "private first" now holds only until the first review runs. For a user on the free path,
the repository becomes public almost immediately.

**This is not a defect — it is a fork the user must meet knowingly.** Required at setup,
before any permission is granted:

> *"Reviews are free on public repositories. If you want your code private, you will need a
> paid plan for the review service. Which do you want?"*

The choice is then recorded, and the full-history secret scan from decision 006 still runs
before anything becomes public.

## Why A is right despite the wall it creates

Forge's product is a guarantee. A half-connected Forge leaves the user unsure which promises
still hold — worse than a clear "not yet". One clear contract is easier to trust, easier to
explain, and easier to build.

## Consequence accepted

A hard wall at the first screen, which raises challenge risk **P10 (setup drop-off)**.
Mitigations already decided: the workflow is explained before permissions are requested
(014), and the public/private cost fork is surfaced at setup rather than discovered later.

**Pricing note:** review-service pricing should be re-checked before release; a change to
their free tier would invalidate the reasoning behind this decision.
