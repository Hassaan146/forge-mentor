---
id: 015
question: What is the plugin called, and how is it versioned?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-2, phase-10]
---

# Forge Mentor, starting at v0.1.0

**Name:** Forge Mentor
**First version:** v0.1.0

## Why the name works

"Forge" alone is heavily used in developer tooling. **Forge Mentor** states what the product
actually is — the mentoring is the product, the code generation is not. It also sets user
expectation correctly at install time: this tool teaches, it does not just build.

## Versioning

Standard three-part numbering. v0.1.0 signals honestly that this is early and the shape may
change. The first release that is safe for strangers to depend on becomes v1.0.0.

Commands stay short — `/forge:start` — since the command prefix is typed constantly.
