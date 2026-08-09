---
id: 040
question: How does someone find out their copy of Forge is out of date?
status: decided
date: 2026-08-10
decided_by: user
affects: phase-2, phase-10
content_sha: 99ca02c4a7e549a3ed6d6cfddb8d72181d47890be5b2b0f20f4ae7ecdd8bc126
prev_sha: 431317e802396297de198aa5e6e652d8ed24a71020b7633f9681686af2e286c7
---

# The plugin says so itself, once a day, in a frame

**Options considered**

- **A** - leave it: the user notices when something behaves oddly and reinstalls
- **B** - the plugin checks its own version against the repository and says so, once a day
- **C** - check on every session start, every time

## Why

**A is what shipped, and it cost four sessions.** Every one of them opened by debugging the
wrong build: rules that had been fixed still firing, a question order that had been changed
still coming out old, colours that had shipped still absent. Nothing on screen ever said the
copy on disk was two weeks behind, so the first hour of each session went into re-diagnosing
work that was already done. The user's words: *"after every update, the plugin should show
'Update your current plugin', like we have on the Play Store."*

**C is A with a different failure.** A check on every session start adds latency to every
session and a notice people learn to skip. Once a day catches a stale copy the next morning
and is never in the way.

**B, with the boring parts done properly.** The version comes from the plugin's own manifest
and the repository from its `repository` field, so a fork checks itself rather than reporting
that it is behind the original. Versions compare as numbers, because `"1.10.0" < "1.9.0"` as
text is the release where everybody's update notice silently stops appearing. The answer is
cached in the user's home directory rather than inside the plugin - inside, the record of
"I checked today" would be deleted by the very reinstall this exists to make unnecessary.

## What crosses the boundary

A version string, and only after it matches `^\d+(\.\d+){0,3}$`. Nothing else the remote
sends is displayed, stored or acted on. Remote text on a user's screen is remote text in a
model's context - challenge finding C3 - and a release note is not worth that door. This is
the security floor applied to the plugin's own supply chain rather than to generated code.

## Silence is the normal answer

Any failure is nothing at all: no network, a proxy, a rate limit, junk in the response, a home
directory that cannot be written. `FORGE_NO_UPDATE_CHECK=1` turns it off entirely. An update
check is the least important thing in a session and must never be why one fails to start -
the same stance the presenter hook takes, and for the same reason.

## What it tells them to do

The command, and two facts: their decisions are untouched because those live in the project's
`.claude/forge/` and not in the plugin (decision 016), and Claude Code has to be **restarted**
rather than reloaded, because hooks and the engine are registered at startup. A plugin updated
in place keeps running its old hooks, which is precisely the state that looks like a bug and
wastes the session.

Also fixed here: the banner read its version from a default argument saying "0.1.0" while the
manifest said 1.0.0. It is the first thing anyone looks at to check whether an update landed,
and it had been wrong for months. A number that is wrong is worse than no number, because it
is believed.

Recorded as rule R17.

Related: [[016-forge-folder-committed]] - [[039-what-stops-forge-from-asking-a-question-as-plain-prose]]
