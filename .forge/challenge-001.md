---
type: challenge
stage: post-foundation-interrogation
method: premortem + redteam
date: 2026-07-31
decisions_challenged: 001-009
status: findings-open
---

# Challenge — attacking the nine foundation decisions

Run before any code is written. Premortem asks *"it is Week 8 and this failed — what
killed it?"*. Redteam asks *"I want to break this — how?"*.

---

## PART 1 — PREMORTEM

**The scene.** It is Week 8. Forge was not submitted, or was submitted broken. Looking back:

| # | What went wrong | How it played out |
|---|---|---|
| P1 | **Only one AI company was ever used** | Every job was given to an Anthropic model. The program required two or more providers with a live comparison. Nobody noticed until the submission checklist was read properly in Week 8. |
| P2 | **A user locked themselves out of their own project** | Someone hand-edited a note file (allowed by decision 001), broke the labelled header, the check failed, and fail-closed (decision 004) blocked everything. They could not work and could not fix it. |
| P3 | **The live feel died waiting for reviews** | Push on every step (005) meant a review ran on every step. Reviews take minutes. The "live session" promised in rule R7 became a series of waits. |
| P4 | **Fable 5 ran out in the first hour** | Teaching happens constantly and Fable 5 is the most limited model. Users burned their allowance during the interrogation, before writing a single line. |
| P5 | **The explain-back became theatre** | Ungraded meant no consequence. Users typed "ok" to move on. The gate that justified the whole product measured nothing. |
| P6 | **The plugin could not actually block a write** | The core promise assumed a capability the platform did not offer in the form needed. Discovered in Week 6, too late to redesign. |
| P7 | **Ten phases did not fit 3.5 weeks** | Three phases were sized L. Alongside the internship's other work, Phases 8–10 were rushed and the dogfood run never happened. |
| P8 | **No dogfood run meant no demo** | Phase 9 depended on Phase 8 finishing. Phase 8 slipped, so there was no real footage, no authentic records, and the demo was staged. |
| P9 | **Commit history became unreadable** | Pushing every micro-step produced hundreds of commits. What was meant to be evidence of work looked like noise. |
| P10 | **Setup was too confusing to reach the good part** | Repository connection, GitHub sign-in, public/private, CodeRabbit plan — users quit at setup and never saw the teaching. |

### Priority

| Failure | Likelihood | Impact | Priority |
|---|---|---|---|
| P1 — one provider only | **High** | **Critical** | **1** |
| P6 — cannot block a write | Medium | Critical | 2 |
| P7 — scope vs time | High | High | 3 |
| P2 — self-lockout | Medium | High | 4 |
| P3 — review latency kills live feel | High | Medium | 5 |
| P4 — Fable allowance | Medium | High | 6 |
| P10 — setup drop-off | Medium | Medium | 7 |
| P5 — explain-back theatre | High | Low | 8 |

---

## PART 2 — REDTEAM

**Objective:** make Forge write bad code, leak something, or lock a user out.

### Attack surface

| Vector | How it is exploited | Severity |
|---|---|---|
| **Review findings re-enter the session** | Decision 005 sends CodeRabbit findings back in, and Opus 4.8 acts on them. Any text that reaches a review comment is text the model reads. On a public repo (007) anyone can comment. | **Critical** |
| **Public repo from commit one** | Strangers can open issues and pull requests on Forge itself. If any automated flow reads them, that is an injection path into the maintainer's own session. | High |
| **The override phrase** | "Write it anyway" is a trained habit. A user conditioned to type it will type it when prompted by content they did not write. | High |
| **Editable settings file** | `.forge/settings` lives in the repo. A merged pull request can change which AI teaches — silently degrading a victim's teaching quality, or pointing a job somewhere unintended. | High |
| **Editable state files** | Same path: a modified decision record can make Forge believe a decision was made that never was, letting code through the governor. | **Critical** |
| **Secret scan before going public** | Pattern matching misses secrets that do not look like secrets. A clean result creates false confidence at the exact moment history becomes permanent. | Medium |
| **GitHub sign-in scope** | If repository creation asks for broad account permissions, the plugin holds more access than the task needs. | Medium |

### The attack I would actually run

**Forged decision record.** Open a pull request on a Forge-using project that adds a
plausible-looking decision record approving something insecure — plaintext passwords, a
disabled check. The governor reads state files to decide whether code may be written. If
the record exists, the governor is satisfied and the code goes in "legitimately", with a
decision file that makes it look reviewed and intentional.

**Why it works:** the governor trusts the state files completely, and those files are
ordinary editable text committed in the repo. Trust was placed in a file anyone with merge
rights can write.

---

## PART 3 — WHAT MUST CHANGE

### Critical — fix before building

**C1. Assign a second provider a real job.** *(kills P1)*
Every model chosen so far is Anthropic. Three Anthropic models is one provider. The
program requires two or more, with a live same-query comparison. Fix at the decision level:
give a non-Anthropic model a named job in the mapping — the natural fit is the
**comparison/second-opinion role**, where two providers answer the same question and the
user sees both. That satisfies the requirement *and* becomes a demo moment.

**C2. Authenticate state files.** *(kills the forged-record attack)*
The governor must not trust a decision record simply because it exists. Records written by
Forge carry a signature derived from their content; the governor rejects any record whose
content does not match its signature. A hand-written or modified record is visible as
unverified — usable by a human, never trusted by the governor.

**C3. Treat review findings as data, never instructions.** *(kills the injection path)*
Findings entering the session are wrapped and labelled as untrusted quoted text. The fixing
model is instructed that they describe problems and never issue commands. Any finding
containing instruction-like content is surfaced to the user rather than acted on.

### High — resolve during Phase 1–2

**H1. Recovery from a broken state file.** Decision 001 permits hand edits; decision 004
blocks everything on failure. Together they can strand a user. Add a repair path: when a
header fails, Forge explains exactly what is wrong, offers to restore the file from its last
committed version, and — because history is in git — that restore always exists.

**H2. Decouple the live loop from review latency.** Push on every step, but do **not** wait
for the review before continuing. Findings arrive asynchronously and are applied at the next
natural pause. Rule R7's live pace survives.

**H3. Protect the Fable allowance.** Reserve Fable 5 for the teaching itself, not for
routine turns inside a session. Warn earlier than planned for this model specifically,
because it is the scarcest and it powers the part users notice first.

**H4. Cut scope honestly now.** Three phases are sized L against 3.5 weeks. Decide now
which phase is sacrificed if time runs short — before pressure decides for you.

**H5. Make the explain-back matter without grading it.** Keep it ungraded, but have Forge
*respond* to the answer — name what was missed and add it. A gate that answers back is not
theatre; a gate that only records is.

**H6. Squash commits per decision.** Keep pushing constantly, but present history as one
meaningful commit per decision so it reads as evidence rather than noise.

**H7. Minimum GitHub permission.** Request the narrowest scope that allows the work, and
say plainly what is being granted.

---

## Blind spots this exercise exposed

1. **The two-provider requirement was assumed satisfied by the plan and was not implemented
   by any decision.** The plan said "API-key fallback"; no decision ever gave a second
   provider a job. A requirement mentioned in a document but absent from the decisions is
   not implemented.
2. **The governor's trust was never examined.** Nine decisions were made about *when* it
   blocks; none about *what it believes*. It reads a file and trusts it absolutely.
3. **Two safe decisions combined into an unsafe one.** Editable files (001) and fail-closed
   (004) are each defensible; together they can strand a user. Decisions were challenged
   individually, never in pairs.

## Confidence

**Before this exercise:** high — the decisions were coherent and well reasoned.
**After:** moderate, and higher once C1–C3 are resolved. C1 is a submission-failing gap and
C2 undermines the product's central promise. Both are cheap to fix now and expensive later —
which is the entire argument for running this before writing code.
