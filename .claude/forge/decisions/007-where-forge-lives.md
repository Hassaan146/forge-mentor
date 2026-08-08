---
id: 007
question: Where do people get Forge from?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-2, phase-10]
content_sha: da7ef82ff34524b5891c58d49be7bb17a81f2947008a3a6bd4ad50206fc5b189
prev_sha: 52fb989a9342981a51eabf5dc82d8c965f4f0c2ef9808d54d1b2b6ee4a9c00f3
---
# Public from the first commit

**Options considered**

- **A** — public from the start
- **B** — private, invite only
- **C** — private while building, public at release

**Recommended:** A · **Decided:** A

## Why

**It is consistent with decision 005.** The user chose to push on every step precisely
because visible commit history is proof of work. That reasoning applies more strongly to
Forge itself: a public repository from the first commit makes the whole build timestamped,
visible evidence for the internship submission.

**It avoids the trap written into decision 006.** A repository that is public from the
first commit never has a private history to expose later. There is no "flip to public"
moment, so the history-exposure guard never has to run on Forge's own repo.

**Nothing in it is secret.** Forge is a teaching tool. Its value is the design and the
protocol, not concealment.

**The demo gets easier.** The mentor and other students can install it themselves during
the presentation, with the same two commands any user would run.

## Consequence accepted

Work in progress is visible to anyone at any time, including before it is ready. Accepted
deliberately: an unfinished public build is normal, and the history is the evidence.

## Rule that follows

Because the repository is public from commit one, **no secret may ever be committed** —
there is no private window in which a mistake could be quietly cleaned up. Secret scanning
runs from the first commit, not just before a release.
