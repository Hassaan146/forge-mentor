---
id: 023
question: How is the chain stored?
status: decided
date: 2026-08-03
decided_by: user
affects: [phase-4]
---

# A chain file, marked read-only where possible — never relied upon

**Decided:** the chain is written to `.forge/chain.log` and marked read-only on disk
where the filesystem allows it.

## The honest limit, recorded so it is not discovered later

**File permissions do not survive `git clone`.** This was proved in practice on
2026-08-03: the project moved from one machine to another and came back entirely through
git. A fresh clone writes files with default permissions, so a read-only flag protects
only the machine that set it.

Therefore the read-only flag is:

- a **guard against accidents** — an editor will refuse the write without a deliberate act
- a **statement of intent** — the file announces that it is not meant to be edited

and it is **not** a security control. The real protection is the fingerprint chain
(decision 021), automatic repair from git (decision 022), and the commit history, which
records who changed what.
