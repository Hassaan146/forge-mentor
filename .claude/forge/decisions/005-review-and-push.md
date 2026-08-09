---
id: 005
question: How does your code get a second opinion?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-6, phase-8, phase-9]
content_sha: c2c648732e2e97d802ad953387c5a8f0b61d13022796053cea5ce396d40f4ccf
prev_sha: 99a3fa353414864e26dc3fca586165ae53afd8ad410b4152ad5ddec396172181
---
# Push to GitHub immediately, then the pipeline reviews it

**Options considered**

- **A** — push first, always; CodeRabbit reviews the pull request
- **B** — review locally, never push
- **C** — local checks always, CodeRabbit only if the user pushes

**Recommended:** C · **Decided:** A — overruled, with reasons the recommendation missed.

## The flow

1. A decision is made and the code for it is written.
2. The code is **committed and pushed to GitHub immediately** — small step, small commit.
3. The pipeline fires on the push.
4. **CodeRabbit** reviews the repository code and returns findings on every check.
5. The findings come back into the session.
6. **Opus 4.8** makes the fixes, keeping the original decision in mind.
7. Fixed code is pushed again; the loop closes when the review is clean.

## Why the user chose A over the recommendation

Two reasons the recommendation did not weigh properly:

**It enforces real engineering discipline.** Pushing at every step forces the habit that
professional teams actually have — small, frequent, meaningful commits — instead of one
giant commit at the end. The tool teaches the workflow, not just the code.

**It builds visible commit history.** A steady stream of commits is the evidence of work.
For a learner, it is proof of progress; for this project, it is proof for the internship
submission.

## Contradiction that must be resolved

Earlier project documents state that pushing to GitHub is **opt-in and requires the
user's consent** each time. That cannot coexist with pushing instantly on every step.

**Resolution:** consent moves to **setup, once**. When the user runs `/forge:start`, they
connect a repository and agree that Forge will commit and push automatically from then on.
After that, no per-push prompt — it happens instantly, as decided here. A user who does
not want this does not connect a repository, and Forge tells them plainly that review and
history are then unavailable.

## Consequence accepted

- A GitHub account and a connected repository become **required** for the full experience.
- Many small commits produce a long history. Mitigation: each commit message is generated
  from the decision it implements, so the history reads as a decision log rather than noise.
