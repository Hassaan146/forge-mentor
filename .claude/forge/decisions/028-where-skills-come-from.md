---
id: 028
question: Where do Forge's skills come from?
status: decided
date: 2026-08-04
decided_by: user
affects: [phase-7]
content_sha: 27d3f060bc54e9e98355109b9095e9e177c3d3fa6e3569df36803da6502dbf1b
prev_sha: a529e5eda682d7cff297720a0e9aeef3276da4746332bd368c33313bf7afca18
---
# The whole library is installed at setup; Forge ships only its own four

**Options considered**

- **A** — install the full 438-skill library on the user's machine at setup
- **B** — install only the ~40 skills Forge's routing map actually names
- **C** — ship the routed subset, offer the full library as an opt-in

**Recommended:** B · **Decided:** A

## The two layers

They are different things and the decision only concerns the second:

**Forge's own skills — bundled in the plugin.** Four, written for Forge, versioned with it:
the teaching voice, the coding-standards layer, the security floor, and the explain-back gate.
These are the product. They are not drawn from any library because Forge's behaviour cannot
depend on what a user happens to have installed.

**The library — installed at setup.** The user's curated collection at
`github.com/Hassaan146/claude-skills`, which the router draws on for stage-specific work.
Installed in full, so every machine running Forge has the same set available and a routed
skill is never missing.

## Consequences accepted

Measured before deciding, not estimated:

| | |
|---|---|
| Install size | 46 MB, 438 folders |
| Context per session | ~44,500 tokens of skill names and descriptions, loaded before any work starts |

Claude Code puts every installed skill's name and description in front of the model so it can
choose between them. With 438 installed that is a fixed ~44.5k tokens at the start of every
session, whether or not a single one is used.

**On cost, this is the cheap kind of large.** That block never changes between calls, so it
sits in the frozen tier of the request and is served from cache — measured at 94% reuse on a
real session. What it genuinely costs is context window, not money.

**On licensing, it is a real change of act.** Forge's marketplace is public from the first
commit (decision 007). Installing 438 skills from many different authors on a user's machine
makes Forge's installer a redistributor, which is a different thing from the author having
them on his own laptop. Not resolved here; recorded so it is not discovered later. Before the
marketplace is advertised, the library repository needs a licence position.

Option B was recommended on both counts — the routed subset is roughly 4k of context and a far
smaller licensing surface, with identical behaviour. The user chose the full library so that
nothing the router might reach for is ever absent.

Related: [[007-where-forge-lives]] · [[029-which-model-runs-a-job]] · [[014-setup-flow]]
