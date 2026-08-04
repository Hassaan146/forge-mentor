---
id: 019
question: What holds the project's state across account switches?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-3, phase-5]
content_sha: 2768fa5f37f20fbadd9644695053d8b707d2b44b65988de99104b97d790c6726
prev_sha: f096def71c72bc694716395747279c11556f219d0c67acecb823b324caf4009f
---
# Local files, one writer, re-read every session

**The mental model:** state was never in the Claude account. It lives in the project
folder on the user's machine. The account is only who pays for the AI. Two accounts do
not share state — there is one copy of the notes on disk, and whoever logs in reads it.

**Rejected:** a hosted server. It breaks the project's own non-goals (no external
database or backend), sends private decisions off the machine, costs money to run, and
fails offline — to solve a problem `git pull` already solves.

## The eight measures

1. **Nothing is stored against an account** — no login, no account id, no session key.
   Nothing can mismatch on a switch.
2. **Read fresh at every session start** — never trust remembered state. Stale memory is
   impossible because there is no memory.
3. **Write the instant a decision is made** — not at the end of a phase. A token running
   out mid-sentence loses nothing.
4. **Save unfinished work too** — the question asked, its options, and the fact that no
   answer has been given yet. Resume mid-question, not at the start of it.
5. **Commit and push after every write** — disk survives an account switch; the repo
   survives a lost laptop.
6. **Prove continuity on every start** — open with what is recorded, what is open, and
   what the last step was, so the user sees it rather than hoping.
7. **Warn when the notes are behind** — on another machine, offer to pull before
   continuing. This is the only case where staleness is real.
8. **One writer** — all reads and writes go through the plugin's helper, so two parts of
   Forge can never write different things at once.
