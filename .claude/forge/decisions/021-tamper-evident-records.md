---
id: 021
question: Tamper-evident records, or true signing?
status: decided
date: 2026-08-03
decided_by: user
implements: 020
affects: [phase-4]
content_sha: 986e05c49120d48fd8ae4dc9276eea557b6fbc7aa41b0bf164176aad77bccebc
prev_sha: 0e03330b402f289d6962edd0571f2fa91a8f910c293d584d52e91c2a4c699918
---
# Fingerprint and chain — no secret, works everywhere

**Options considered**

- **A** — fingerprint + chain, no secret
- **B** — secret-key signing
- **C** — both, with two trust levels

**Recommended:** A · **Decided:** A

## The constraint that decided it

Signing needs a secret. A secret kept in the repository can be used by anyone who clones
it, so it proves nothing. A secret kept in the machine's keychain does work — until the
user switches accounts or machines, at which point every record stops verifying. That
breaks decision 011, the promise the user cared most about.

Portability wins. Git history already answers "who".

## The mechanism

Every record carries two extra header fields:

| Field | Meaning |
|---|---|
| `content_sha` | Fingerprint of this record's own text |
| `prev_sha` | Fingerprint of the record before it — forming a chain |

Verification is arithmetic. It needs no secret and runs anywhere:

| Check | Catches |
|---|---|
| Recompute the text and compare to `content_sha` | An approved decision edited after the fact |
| Walk `prev_sha` back through the chain | A record inserted, deleted, or reordered |

## The three states

- **verified** — fingerprint matches and the chain is intact
- **modified** — the text changed after it was written
- **chain broken** — a record was inserted, removed, or reordered

## What this does not stop, stated plainly

Someone who knows the format can append a *new* record with a correct fingerprint and
chain link, because the fingerprints are computed openly.

**Why it is still worth building:** it turns the attack from invisible into visible. A
forged record can no longer be slipped quietly into history — it has to arrive as a new
commit, from a named author, in a reviewable pull request, which is exactly where the
review step already looks.
