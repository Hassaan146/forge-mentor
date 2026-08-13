---
id: 061
question: How does someone installing Forge end up with ponytail as well?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: 37fd72c52eba0db1869621994edff7cf59b6d4ad35feec80152e7154ca51fa83
prev_sha: d3d77a9c55b6e934a29d3ff31c376147c7fa4b98b780ab82807ca6bc34a1dcd3
---

# ponytail is listed in Forge's marketplace, installed by the user, never installed silently

**Options considered**

- They find it themselves from the README
- Forge's own marketplace lists it, so it is one command from the same place
- Forge installs it silently during setup
- Vendor its rules into Forge's skills

**Recommended:** Forge's marketplace lists it · **Decided:** ponytail is listed in Forge's marketplace, installed by the user, never installed silently

## Why

A marketplace can carry more than one plugin, so adding Forge's marketplace now offers both and installing ponytail is one command from the same place rather than a link in a README. It points at Dietrich Gebert's repository, so it stays his: his updates, his licence, his name on it, and no fork of a fast-moving repository for anybody to maintain. Silent installation was rejected. Installing somebody else's software onto a user's account while they are reading about permissions answers a question nobody asked, and Claude Code installs plugins on the user's word rather than a plugin's. The offer is made at setup, in one line, and the session hook from decision 059 makes it once per project after that.

## In their words

In the Forge project, whenever this plugin is completed and someone uses this plugin, it should be installed directly when Forge is, because ponytail is for coding.
