---
id: 023
question: How is the chain stored?
status: decided
date: 2026-08-03
decided_by: user
affects: [phase-4]
content_sha: 5f9af41beda5ca915217fdb4c886e9f6b37ecd2afe9a9e460bcc334d633425e3
prev_sha: 1439b2cfdbbc7bc3409133cc4471e6455fa6dc663b39c40971036c55acdc6e29
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
