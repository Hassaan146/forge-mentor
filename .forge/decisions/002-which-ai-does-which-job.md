---
id: 002
question: Which AI does which job?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-1, phase-5, phase-7]
content_sha: eb0e0e40f193f451c5c0ba978c978054c2c681eb53dec861a4760aa8c3c3a7f8
prev_sha: 21d34fa2c45c792b363a0f767fdb5e4eea9ef1fe3c4bc2133917a7db1fbe5f85
---
# Best-fit AI per job, with a fallback

**Options considered**

- **A** — one AI for all four jobs
- **B** — two AIs: a strong one for thinking/coding, a cheap one for small jobs
- **C** — best-fit AI for each job

**Recommended:** C · **Decided:** C

## The mapping

| Job | AI | Why this one |
|---|---|---|
| Teaching, asking questions, planning | **Claude Fable 5** | Best reasoning available. Teaching quality is the product, so this job gets the strongest model. |
| Writing the code | **Claude Opus 4.8** | Strongest coding model in the Opus tier. |
| Tidying a typed answer into a neat note | **Claude Haiku 4.5** | Small job that runs constantly. Fast and cheapest — this is where cost is won or lost. |
| Fixing review comments | **Claude Opus 4.8** | It is real code editing, so it belongs with the coding model. Claude Sonnet 5 is the cheaper alternative if cost becomes a problem. |

## Why

The best-thinking AI is slower and costs more. Putting it on the tidy-up job — which
runs hundreds of times in a build — is exactly what makes running costs explode. Putting
a cheap fast AI on teaching produces shallow lessons, which defeats the product. Keeping
the jobs separate protects both quality and cost.

## The fallback (safety net)

Available AIs depend on the user's subscription plan. Each job has a **preferred** AI; if
the user's plan does not include it, that job falls back to the next best one they do
have. Nobody is blocked because of their plan.

## Consequence accepted

Four AI roles means more to configure, test, and explain in the presentation than a
single-AI setup would need.
