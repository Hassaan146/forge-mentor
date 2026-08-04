---
id: 020
question: How does Forge know a decision record is genuine?
status: decided
date: 2026-08-03
decided_by: user
resolves: challenge-001 finding C2
affects: [phase-4]
---

# Sign what Forge writes; forged records show as unverified

**Options considered**

- **A** — trust any record
- **B** — sign what Forge writes; unsigned records show as unverified
- **C** — sign and reject anything unsigned

**Recommended:** B · **Decided:** B

## Why not C

Decision 001 deliberately allows a user to hand-edit their notes, and challenge finding
H1 requires that a user can repair a broken file by hand. Rejecting unsigned records
outright removes that and can strand someone in their own project.

## Why not A

The governor's whole job is to check whether a decision was recorded. If any file that
looks like a record is trusted, insecure code can be walked past the block carrying a
document that makes it look reviewed.

## What B means in practice

The governor trusts only what Forge itself wrote. A hand-written or altered record still
exists, still reads normally, and can still be repaired by hand — it simply does not
count as an approval.
