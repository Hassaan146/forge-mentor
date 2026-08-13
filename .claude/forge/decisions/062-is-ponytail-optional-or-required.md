---
id: 062
question: Is ponytail optional or required?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: d5f2369adca711820bc052f010e04a1efc28b4b606a3a938711b0d07958e7fe5
prev_sha: 37fd72c52eba0db1869621994edff7cf59b6d4ad35feec80152e7154ca51fa83
---

# Required. Setup stops without it, the readiness check is fatal, and the user installs it

**Supersedes decision 058** (Should Forge use other people's plugins where they are better than its own?)

**Options considered**

- Optional. Forge routes to it when present and runs without it (decision 058)
- Required. Setup will not finish without it, and the readiness check is fatal
- Required, and Forge installs it during setup
- Bundled: copy its rules into Forge's own skills

**Recommended:** Required, and the user installs it · **Decided:** Required. Setup stops without it, the readiness check is fatal, and the user installs it

## Why

This supersedes decision 058, which made it optional on the argument that Forge's guarantees cannot depend on something Forge does not ship. The owner overruled that twice, and the reasoning stands on its own: the output of this product is somebody else's codebase, so the thing that keeps that code small is not a nice-to-have. It is the same argument decision 017 makes about permissions, and it carries the same cost, which is written down rather than argued away: Forge now breaks when a third-party plugin changes name, layout or availability, and the detection is a filesystem guess about a directory layout Claude Code owns. Mitigated the way decision 004 mitigates every hard rule: there is exactly one way through, it is explicit, and it is recorded. Forge still does not install it, because Claude Code installs plugins on the user's word rather than a plugin's.

## In their words

Keep in mind that Ponytail is compulsory. The code quality is improved by Ponytail.
