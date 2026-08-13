---
id: 059
question: How does the companion plugin actually reach a build, rather than sitting in a table?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: 925da36ffbc5542b46dfb12aaf435ae75b091db776aba95533419a594906abe9
prev_sha: d87a49d9f37cd6eeb682794e5a3c38e3613aba9996e649c3afe037e1191aa489
---

# A SessionStart hook brings it in with Forge: one line when it is installed, the install command once per project when it is not, and silence on every error

**Options considered**

- The routing table only. The builder reads it when it asks
- A session hook that names it once, and offers it once per project when absent
- Copy its rules into Forge's own coding-standards skill
- Require it, and refuse to build without it

**Recommended:** A session hook · **Decided:** A SessionStart hook brings it in with Forge: one line when it is installed, the install command once per project when it is not, and silence on every error

## Why

The routing table alone puts it somewhere that is read by whatever asks the table, and if the builder does not ask, nothing happens and nothing says so. That is the failure this repository has repeated more than any other: the rule was in the code and the code was not in the path. A hook is the path. It is deliberately the quietest one Forge has: it never blocks, it says nothing outside a Forge project or where Forge is paused, it swallows every error, and the offer is written to a marker file so it is made once per project rather than every session, because a suggestion repeated is an advertisement. Copying the rules in was rejected for the same reason as vendoring the plugin: a copy of a repository moving that fast is a fork nobody volunteered to maintain. Requiring it was rejected because it is somebody else's plugin and Forge's guarantees cannot depend on a thing Forge does not ship. FORGE_NO_COMPANION=1 turns it off.

## In their words

Whenever in our plugin we use Forge, I also want to use that same hook that triggers this repository and this ponytail thing.
