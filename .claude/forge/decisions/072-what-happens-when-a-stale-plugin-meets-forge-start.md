---
id: 072
question: What happens when a stale plugin meets /forge:start?
status: decided
date: 2026-08-14
decided_by: user
affects: phase-2, phase-10
content_sha: 6b26810176aa121b50e3361499b0128cce6e0b15233b16ac4b540f8336470251
prev_sha: c26bc0fef0ec5d6f6ed35af4b4589fb6c7d8040a40730e4606c22339f00a7034
---

# Nothing. The UserPromptSubmit gate is deleted, the notice rides along, and the project starts

**Options considered**

- Keep the block and fix the command it names, so a fresh project is sent to /forge:start rather than /forge:status
- Delete the gate: print the notice, start the project, and let the restart keep until it suits
- Block only when the project already has notes

**Recommended:** Delete the gate - **Decided:** Delete the gate

## Why

The gate held /forge:start back whenever a newer version sat downloaded and unloaded, because starting on an old build writes a notes layout and a question sequence shaped by the wrong version. Its way out was /forge:status, which in an empty directory answers "not a Forge project, run /forge:start" - and the gate blocked that in turn. A user ran the pair four times before reporting it, and the earlier fix, naming the right command in the message, would have left the same door locked with a better sign on it. The check was never the problem; refusing to start was. start.md prints the notice before Step 1 and carries straight on, so the update command and the project arrive in the same turn. Both notices lost their YOUR TURN frames for the same reason: a question on an update block is a question the user has to answer before the command they actually ran can happen. Nothing replaced the hook, because its one remaining job, saying the version is behind, is already done twice - at SessionStart and in start.md.

## In their words

multiple times, I accepted Claude and then again implemented Forge Start Forge. This is a bug. I want you to clear the bug. When there are no questions, no everything, the user from Forge Start should directly start from the Forge. If there is a new update available, provide the command that this is the command to update to the latest Forge, and then you have to start Forge.
