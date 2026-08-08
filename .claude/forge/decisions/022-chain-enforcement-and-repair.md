---
id: 022
question: What happens when the chain is broken or a record is hand-written?
status: decided
date: 2026-08-03
decided_by: user
strengthens: 021
affects: [phase-4]
content_sha: 1439b2cfdbbc7bc3409133cc4471e6455fa6dc663b39c40971036c55acdc6e29
prev_sha: 986e05c49120d48fd8ae4dc9276eea557b6fbc7aa41b0bf164176aad77bccebc
---
# Warn, stop, and restore the record from its committed version

**User's answer:** Forge should warn, stop, and rewrite the hand-written content with
its own version.

## Why this is stronger than either option offered

Decision 021 chose *detect, do not prevent*, because refusing outright could strand a
user behind one damaged old record (challenge finding H1). Repair removes that
objection: enforcement is safe when the fix is automatic.

## Where the "correct version" comes from

Git. Decision 005 commits and pushes on **every step**, so a committed good version of
every record always exists. A fingerprint cannot be reversed into text — git history is
the only real source, and it is already there.

## Behaviour

1. **Warn** — name the record, and state plainly what changed.
2. **Stop** — the session does not continue past a broken chain.
3. **Restore** — replace the altered file with its last committed version.
4. **Re-verify** — confirm the chain is whole again before continuing.

## Two safeguards this needs

**Confirm before overwriting.** Decision 001 deliberately allows hand-editing, and a
silent overwrite would destroy a user's work without asking — which contradicts the
principle the whole product rests on: no important decision made for you. So Forge shows
what changed and asks before restoring. One keystroke, but the user's choice.

**Quarantine what cannot be restored.** A forged record that was never committed has no
earlier version to return to. It is moved to `.forge/quarantine/` rather than deleted —
nothing is destroyed, the chain becomes whole, and the evidence survives for review.

## Consequence accepted

A user who deliberately hand-edits a decided record will be asked to accept a restore.
That is the intended trade: decided records are approvals the governor trusts, so they
are held to the chain. Notes, prose, and everything outside `.forge/decisions/` stay
freely editable.
