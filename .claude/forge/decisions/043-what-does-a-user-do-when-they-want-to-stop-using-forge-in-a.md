---
id: 043
question: What does a user do when they want to stop using Forge in a project?
status: decided
date: 2026-08-10
decided_by: user
affects: phase-2, phase-4
content_sha: 4da213ea3d1209ee61cae5026901040e42cb8cf0d704721d29d909b73976c4d4
prev_sha: bc10f99a79b923a7675f0d0e5d24a9003287b7949e4163a0b3be6e904caf5adf
---

# One file switches it off, and nothing is deleted

**Options considered**

- **A** - no way off. Delete `.claude/forge/` if you want Forge to stop
- **B** - a pause file every hook checks, leaving every record where it is
- **C** - a setting in `settings.md`

## Why

**A was the state, and it is a trap.** The only exit from a configured project was to delete
the notes, which is the one action in the product that destroys work. Everything else here
refuses rather than discards: repair quarantines before it overwrites, and a blocked write is
refused rather than thrown away. Making "I do not want the gates today" cost the decision
history contradicts all of it.

**C is a setting, and a setting has to be parsed.** Every hook answers "am I on" before it does
anything, and parsing can fail. A malformed header would leave someone locked out of their own
repository by a tool they had already asked to stop, which is the worst possible time to fail
closed.

**B is a file.** It exists or it does not. Nothing to parse, nothing to be malformed, obvious
in a directory listing, and a user can create or delete it by hand without knowing anything
about Forge.

## Where the check sits

Before the notes are read, not after. Everywhere else the safety path fails closed and should,
per decision 004. Here it must not: the user has said stop, and a damaged progress file is not
a reason to keep refusing their writes.

## Deleting is separate, manual, and theirs

`/forge:stop` never removes anything. The decisions, the chain and the phases are the project's
own history and outlive the tool that produced them, which is what decision 016 bought by
committing them with the code. `prompts.md` and Code Explained are generated from them, and
they are what answers "why is this built this way" in six months.

The command to delete them is documented in `/forge:stop`, with what it costs, and Forge will
not run it however clearly it is asked. Removing the tool does not require removing the record.

Related: [[016-forge-folder-committed]] - [[004-when-the-safety-check-fails]] - [[014-setup-flow]]
