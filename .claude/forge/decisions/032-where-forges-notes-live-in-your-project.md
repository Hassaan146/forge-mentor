---
id: 032
question: Where do Forge's notes live inside someone's project?
status: decided
date: 2026-08-08
decided_by: user
amends: 016
affects: [phase-3, phase-10]
content_sha: 1773fc2094f2df602e5c61c0ca06b70c526cc095f8bba39ac38a26528922ffef
prev_sha: 7222fdf6183c39818931c576d517790e4253a19d6e0e653cf552bb482988d9ae
---
# Under `.claude/`, with one exception and one guard

**Options considered**

- **A** — `.claude/forge/` for everything Forge keeps
- **B** — stay at `.forge/` in the project root
- **C** — `.claude/forge/` for state, and `prompts.md` at the root as well

**Recommended:** C · **Decided:** C

## What changes

Someone installs Forge and runs `/forge:start`. Until now that put a `.forge/` folder at the
top of their repository. It now goes to `.claude/forge/` — the same place Claude Code already
keeps what belongs to it, so a project picks up one new folder rather than two unrelated ones.

Everything Forge maintains moves together: the progress file, the decision records, the chain,
the reviews, the phases, settings, and Code Explained.

## The exception

`prompts.md` stays at the project root. It is not Forge's working state — it is an artifact of
the user's project, and something a reader looks for at the top of a repository. Filing a
deliverable inside a tool's folder makes it a folder deeper than anyone will look.

## The guard, which is the real reason this decision has a body

**`.claude/` is very commonly ignored by git.** It usually holds `settings.local.json` and
other machine-local config, so "ignore the whole folder" is an ordinary thing for a project to
do — and entirely reasonable, until Forge's memory is inside it.

If that happens, the decision records stop being committed. Nothing announces it. The user
carries on, switches machine or account, and finds an empty project — which is precisely the
failure decision 011 exists to prevent, arriving through the fix for a tidiness problem.

**Forge cannot repair this from inside its own folder.** Git will not re-include a file whose
parent directory is excluded, so a `.gitignore` shipped inside `.claude/forge/` is worthless if
`.claude/` itself is ignored.

So Forge asks git directly, at setup and before it records anything: is this path ignored? If
it is, Forge says so and stops, naming the line to change. Refusing is right here — a tool
whose whole promise is "the repository is the memory" must not write notes it knows will never
be committed.

## Consequence accepted

An existing project has to move its folder. `git mv .forge .claude/forge` is the whole
migration, and Forge's own repository is the first to do it — its 30 signed records are
re-signed afterwards, so the migration path is proven on real records before anyone else meets
it (decision 021's chain covers content, not location, so the records survive the move).

Related: [[016-forge-folder-committed]] · [[011-continuing-on-another-account]] · [[001-state-file-format]]
