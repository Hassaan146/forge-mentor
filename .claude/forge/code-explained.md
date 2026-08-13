---
type: code-explained
decisions: 60
chosen_by_you: 60
updated: 2026-08-13
---

# Why forge-mentor is built the way it is

60 decisions shape this project. You made 60 of them.

Read in the order they were decided, because each one was made knowing the
ones above it, which is not the order the files are listed in.

---

## 001 · How does Forge save project notes?

**A, refined — both files are readable documents with a strict labelled**

Also considered: **B** — both in a strict computer format; **C** — mixed: strict progress note, readable decision notes

The user must be able to read either file himself. And when usage runs out on one
account and he switches to another, a brand-new session with no memory of the project
must be able to read these files and carry on. Nothing hidden, nothing tied to one
session or one account.

Full record: [`001`](decisions/)

## 002 · Which AI does which job?

**C**

Also considered: **A** — one AI for all four jobs; **B** — two AIs: a strong one for thinking/coding, a cheap one for small jobs

The best-thinking AI is slower and costs more. Putting it on the tidy-up job — which
runs hundreds of times in a build — is exactly what makes running costs explode. Putting
a cheap fast AI on teaching produces shallow lessons, which defeats the product. Keeping
the jobs separate protects both quality and cost.

Full record: [`002`](decisions/)

## 003 · Can the user change which AI does which job?

**C, refined with three added rules.**

Also considered: **A** — fixed inside Forge, user cannot change it; **B** — a settings file the user edits freely

Defaults protect the beginner, who is the main user. The override solves the real problem
that a cheaper plan may not include Fable 5. Warning instead of blocking respects that it
is the user's project — the same principle as the rest of Forge: teach the consequence,
then let the human decide.

Full record: [`003`](decisions/)

## 004 · What happens if Forge's safety check breaks — or the user demands code anyway?

**C, refined.**

Also considered: **A** — stop everything, no way through; **B** — warn and carry on

The guarantee is the product. If it can disappear quietly, it was never a guarantee. But
locking someone out of their own project because of a bug in Forge is not acceptable
either. An explicit command plus a specific confirmation keeps the promise real while
leaving the human in charge.

Full record: [`004`](decisions/)

## 005 · How does your code get a second opinion?

**A — overruled, with reasons the recommendation missed.**

Also considered: **B** — review locally, never push; **C** — local checks always, CodeRabbit only if the user pushes

Full record: [`005`](decisions/)

## 006 · Who creates the project repository, and is it public or private?

**C, refined.**

Also considered: **A** — Forge creates it, public by default; **B** — Forge creates it, private by default

Full record: [`006`](decisions/)

## 007 · Where do people get Forge from?

**A**

Also considered: **B** — private, invite only; **C** — private while building, public at release

**It is consistent with decision 005.** The user chose to push on every step precisely
because visible commit history is proof of work. That reasoning applies more strongly to
Forge itself: a public repository from the first commit makes the whole build timestamped,
visible evidence for the internship submission.

**It avoids the trap written into decision 006.** A repository that is public from the
first commit never has a private history to expose later. There is no "flip to public"
moment, so the history-exposure guard never has to run on Forge's own repo.

**Nothing in it is secret.** Forge is a teaching tool. Its value is the design and the
protocol, not concealment.

**The demo gets easier.** The mentor and other students can install it themselves during
the presentation, with the same two commands any user would run.

Full record: [`007`](decisions/)

## 008 · How much should it cost to run?

**B now, C later.**

Also considered: **A** — show usage, never interfere

Full record: [`008`](decisions/)

## 009 · What counts as "finished" for each step?

**C**

Also considered: **A** — the tests pass; **B** — tests pass and the review is clean

The project's thesis is *the decision is the lesson*. If a step can be marked finished
while the person still does not understand it, the product has failed at its one job.
The two conditions keep the bar real while keeping it light in feel — consistent with the
live pace (R7) and warn-don't-block (decision 004).

Full record: [`009`](decisions/)

## 010 · Does Forge need a second AI company, or is Anthropic-only correct?

**Anthropic-only for the pipeline — user decision, with one requirement still unmet**

Full record: [`010`](decisions/)

## 011 · How is history preserved when the user switches to another account?

**The repository is the memory — the chat is not**

Full record: [`011`](decisions/)

## 013 · What does "live session" mean in practice, and what is actually achievable?

**One answer triggers a continuous stream, not a round trip**

Full record: [`013`](decisions/)

## 014 · What does /forge:start actually do?

**Connect accounts, explain the workflow, request permissions — all mandatory**

Full record: [`014`](decisions/)

## 015 · What is the plugin called, and how is it versioned?

**Forge Mentor, starting at v0.1.0**

Full record: [`015`](decisions/)

## 016 · Is the .forge/ folder committed or ignored?

**Committed to the project repository and pushed to GitHub**

Full record: [`016`](decisions/)

## 017 · Does Forge work without all permissions granted? (resolves 006 vs 014)

**A**

Also considered: **B** — 006 wins: core works, review optional; **C** — split: file access mandatory, review optional with warnings

Full record: [`017`](decisions/)

## 018 · How do we stop the notes from causing git conflicts?

**a question becomes a decision file the moment it is *asked*, carrying**

Full record: [`018`](decisions/)

## 019 · What holds the project's state across account switches?

**Local files, one writer, re-read every session**

Full record: [`019`](decisions/)

## 020 · How does Forge know a decision record is genuine?

**B**

Also considered: **A** — trust any record; **C** — sign and reject anything unsigned

Full record: [`020`](decisions/)

## 021 · Tamper-evident records, or true signing?

**A**

Also considered: **B** — secret-key signing; **C** — both, with two trust levels

Full record: [`021`](decisions/)

## 022 · What happens when the chain is broken or a record is hand-written?

**Warn, stop, and restore the record from its committed version**

Full record: [`022`](decisions/)

## 023 · How is the chain stored?

**the chain is written to `.forge/chain.log` and marked read-only on disk**

Full record: [`023`](decisions/)

## 024 · Where do the usage numbers come from?

**A**

Also considered: **A** — read Claude Code's session transcripts; **B** — estimate from the text Forge sends; **C** — count only when Forge calls a model directly; **D** — drop the meter from v1

Full record: [`024`](decisions/)

## 025 · How do two reviewers share one set of notes?

**A**

Also considered: **B** — one file per reviewer per pull request; **C** — merged, but only CodeRabbit's findings count toward "done"

Full record: [`025`](decisions/)

## 026 · Who writes the review file into the repository?

**A**

Also considered: **B** — Forge commits and pushes it from the user's machine after fetching; **C** — Forge writes it locally; it rides along in the next ordinary commit

Full record: [`026`](decisions/)

## 027 · Does the second-provider requirement change the pipeline?

**A**

Also considered: **A** — Anthropic only; **B** — OpenRouter as an API-key fallback tier; **C** — a direct second-party API key; **D** — drive the local Codex CLI as a second subscription path

Full record: [`027`](decisions/)

## 028 · Where do Forge's skills come from?

**A**

Also considered: **B** — install only the ~40 skills Forge's routing map actually names; **C** — ship the routed subset, offer the full library as an opt-in

Full record: [`028`](decisions/)

## 029 · Which model actually runs a job — who decides at dispatch?

**A**

Also considered: **B** — the MCP server owns dispatch and configures the subagents; **C** — subagent files only; drop `choose_model`

Full record: [`029`](decisions/)

## 030 · What actually differs between the three modes?

**A**

Also considered: **A** — the modes differ only in how many decisions Forge makes on its own; **B** — as A, and Auto also skips the explain-back gate; **C** — two modes; drop Auto

Full record: [`030`](decisions/)

## 031 · What does "clean" mean when a finding is about code that has changed?

**A and B together**

Also considered: **C** — count only findings raised against the current head commit

Full record: [`031`](decisions/)

## 032 · Where do Forge's notes live inside someone's project?

**C**

Also considered: **A** — `.claude/forge/` for everything Forge keeps; **B** — stay at `.forge/` in the project root

Full record: [`032`](decisions/)

## 033 · What does Forge ask first, and in what order?

**A**

Also considered: **B** — let the planner choose an order per project; **C** — the stack first, the rest chosen per project

Full record: [`033`](decisions/)

## 034 · When exactly does the governor block a write?

**A**

Also considered: **A** — block whenever a foundation question is unanswered; **B** — block only while a question is open, as before; **C** — block on the first write and let the user opt out

Full record: [`034`](decisions/)

## 035 · How many symbols does Forge use, and what governs them?

**B**

Also considered: **A** — keep the four symbols of rule R9 unchanged; **C** — emoji freely wherever they help

Full record: [`035`](decisions/)

## 036 · Does every Forge response carry a taught colour system, and does the thing the user must do next get its own frame?

**B**

Also considered: **A** — keep the palette as it is; the ask stays the last tinted line of the block; **C** — colour freely wherever it helps, with no fixed scheme

Two separate faults, reported together.

**The colours had meanings and nobody was told them.** Six were already in use and each already meant one thing, but the meanings lived in a comment in `forge_ui.py`. Forge asks the user to *act* on colour — red means it stopped, yellow means the turn is theirs — and a scheme nobody was told about is a scheme nobody can read. The key is now printed at setup, beside the permissions, which is the one moment the user is reading carefully. Blue replaces cyan for information and yellow is added for "your turn, or a cost"; every span closes with the reset, because an unclosed one runs past the end of Forge's output and recolours the user's own shell prompt.

**The ask was the last line of the block it belonged to.** "Type yes to continue" and "A, B, or C?" carried the same weight as the option above them, and they were the first thing lost when a block scrolled — reading back through a session there was no way to find the place you were being asked something without reading everything. The ask now has the only double-ruled frame on the screen, in yellow, marked with the eighth symbol. It names the letters that were actually offered rather than a fixed A/B/C, and says what shape of answer is wanted.

The same reasoning covers details with a cost that cannot be undone — *this makes the repository public*, *every account will have to sign up again*. As sentence four of a paragraph they are read straight past, and those are the sentences the user most needs to have read. They get a yellow bar and their own vertical, inside the block rather than after it.

Full record: [`036`](decisions/)

## 037 · What is the unit of work the governor gates on, once the foundation is answered?

**The step, not the phase — and a phase with no step list cannot be built**

Also considered: **A** - leave the gate where decision 034 put it: the foundation is answered, so code may be; **C** - tell the planner in its instructions to ask before each step, and leave the gate alone

**C is what was already there, and it is what failed.** The interactive loop was described in
the planner's brief and in `start.md`. A description is a suggestion. On a real run against a
to-do app, Forge asked its foundation questions, wrote a progress file describing five phases
in prose, compiled no phase files at all, and then produced `index.html`, `style.css`, `db.js`
and `app.js` in one turn. Nothing was asked after the last foundation question. Every write was
permitted, and the product looked like it was working the whole time.

**A is the bug, stated as a rule.** Decision 034 closed a real hole - a fresh project allowed
writes because no question was open - by adding "and the foundation must be answered". Both
conditions are true exactly once, at the start. After the sixth answer `writes_allowed` returned
True and had nothing left to check, ever. The foundation says what is being built. It does not
say what the next file is, and nobody had been asked.

**B puts the loop in the files.** A phase is not a unit of work; it is a list of them. A phase
file carries its own step list, a step is decided when a decision record names it in `affects`,
and the write gate reads both. Three refusals follow, in order: no phases compiled, a phase with
no step list, a current step with no decision. The gate opens for exactly one step at a time and
closes again when it is ticked off.

Full record: [`037`](decisions/)

## 038 · When does the user see the shape of the whole project?

**All the phases, before any of them - and the plan is a gate, not a document**

**A is what shipped, and the user caught it.** Watching a real run, they were asked "how is
this project tested?" - a question whose answer applies to every phase - at a point where they
had been told about phase one only. Phase one had already been built. Their words: *"Why are we
moving with a phase-by-phase approach? First, you will make all the phase plans."*

The cost is not that the plan was wrong. It is that a decision with project-wide reach was made
without the project being visible. A user who could see four more phases coming would answer the
testing question differently, and would have said so about phase three before phase one was
written rather than after.

**C is A with better filing.** A plan that exists only in files nobody was shown is the state
`todo-test` was actually in: five phases described in prose in the progress file, no `phases/`
directory at all, and the first phase built. Being on disk is not being seen.

**B makes it a gate.** `compile_phases` writes all of them in one call. `show_roadmap` renders
the whole plan - the spine, every phase, what each delivers, which steps are built - and
regenerates a self-contained `roadmap.html` that opens from disk with no network and can be
sent to a mentor. Acceptance is recorded as a decision carrying `plan-accepted`, and
`writes_allowed` refuses everything until it exists.

Rule R13 applies to this the same as to the step gate: it is a fact about `.claude/forge/`, not
a paragraph in the planner's brief. The brief already said to show the plan.

Full record: [`038`](decisions/)

## 039 · What stops Forge from asking a question as plain prose?

**A hook on Stop, and the colour was never leaving the process**

Also considered: **A** - restate rules R10 and R12 more firmly in the planner's brief and start.md

**A is what was already there twice over.** Both rules were written down, in two files, with
reasons. A run put a decision on screen as unformatted paragraphs anyway. Rule R13 covers this
exactly: if the model ignored the paragraph, what would stop it? Nothing did.

**B is the same shape as the governor.** A write is a file path a hook can see, so the governor
can refuse it. A turn is a transcript a Stop hook can read, so it can be refused the same way -
and the refusal names the tool to call rather than asking for restraint, because "be more
concise" is not something a model reliably does and "call render_decision and print what it
returns" is.

Loose prose around a frame is refused too. A block with ten paragraphs above it is the wall of
text R10 exists to prevent, wearing a box.

**C would be stronger and costs a turn every time.** Worth revisiting if B proves leaky; not
worth a round trip per question before that is known.

Full record: [`039`](decisions/)

## 040 · How does someone find out their copy of Forge is out of date?

**The plugin says so itself, once a day, in a frame**

Also considered: **A** - leave it: the user notices when something behaves oddly and reinstalls; **C** - check on every session start, every time

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

Full record: [`040`](decisions/)

## 041 · How are the stack options named?

**By the shape you end up with, not the technology you would type**

Also considered: **A** - keep the technology names: "Browser only", "Browser + small API", "Python service"; **C** - ask the shape first, then a second question for the technology

**A hid an answer in plain sight.** A user reading the list said the options were missing the
case where you build the API and database first and add the screens later. It was there. It was
option B, called "Browser + small API", and the name described what they would type rather than
what they would have, so they could not see it.

That is the same failure as leaving it out. A menu is read for what it appears to offer, and
nobody audits a menu against the thing they were about to ask for.

**C is the split that decision 033 already refused**, one question up. Language, framework and
runtime do not separate cleanly, and asking the shape and then the technology lets an answer to
the first quietly rule out most answers to the second without anyone noticing.

**B keeps them together and names the outcome.** "Back end only, an API and a database now,
screens added later" is a sentence someone can recognise their own plan in. Rule R2 still holds:
the consequence line names the real thing, so the label can be plain without the option being
vague.

Full record: [`041`](decisions/)

## 042 · Which Opus writes the code?

**Opus 5, and decision 002 is amended rather than edited**

Also considered: **A** - leave `claude-opus-4-8` in place

Decision 002 chose "the strongest coding model" and then wrote down the name of the model that
was strongest when it was written. The name aged; the reasoning did not. Opus 5 is the current
one, so B is what 002 actually asked for.

The user caught it in the demo output, where the live line read "Opus 4.8 is now writing it".
That line exists to make the multi-model design visible, which means it is also the line that
shows when the routing is wrong.

Full record: [`042`](decisions/)

## 043 · What does a user do when they want to stop using Forge in a project?

**One file switches it off, and nothing is deleted**

Also considered: **C** - a setting in `settings.md`

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

Full record: [`043`](decisions/)

## 044 · How does a block reach the user's screen with both its box and its colour?

**A table, so the client draws the border and colours the contents**

Full record: [`044`](decisions/)

## 045 · Which presentation does a block use where colour cannot arrive?

**The fenced box. Eight tried, and this is the one, and it is monochrome**

Full record: [`045`](decisions/)

## 046 · How does colour reach the screen in a client that strips escape codes?

**The client colours it. Forge stops trying to carry it there.**

Full record: [`046`](decisions/)

## 047 · How many options does a question put in front of the user?

**At least three and at most six, each carrying its cost, refused at the renderer**

Also considered: Whatever the model thinks of at the time (what shipped); Two to four, as the teaching skill asked for in prose; A fixed number for every question

Nothing generated options. One question in the product carried a menu and every other one was improvised against no rule, so the floor could not be held by asking for it. `render_decision` now refuses a block with two options or with an option that has no consequence line, and the foundation menus are checked at the source. Three is the floor because two is a false binary: the answer has usually been chosen by whoever picked the pair. Six is the ceiling because a list nobody finishes is a list nobody chooses from. A question that genuinely has two sides passes `binary_because`, and that sentence goes on screen, so claiming a binary costs the same as arguing for one.

Full record: [`047`](decisions/)

## 048 · Does the menu narrow against what the project has already decided?

**The menu narrows against the recorded facts, and what it removes is shown with the reason**

Also considered: No, the same options everywhere, and the user ignores the ones that do not apply; Yes, and the excluded ones are dropped silently; Ask the user each time whether an option still applies

A project that has said it runs only on the user's machine is never offered a container again; one with a single user is never offered a second reviewer. The facts are read back out of the decision records every time, never remembered, which is decision 019 applied to menus. Shown rather than dropped, because the exclusion is the cheapest teaching in the whole interrogation: a user who reads that a container is ruled out because this runs on their laptop has learned what a container is for, at no cost in questions. Silently removing it leaves them unable to tell the difference between an option Forge weighed and one it never thought of. A question is never narrowed by the fact its own answer produces, or it would answer itself and present the result as a choice.

Full record: [`048`](decisions/)

## 049 · What happens to the questions an answer implies but the fixed list does not contain?

**An answer opens the questions it implies, and they are inserted where they belong**

Choosing to deploy is not one decision. It is where it runs, how a change gets there, what happens when it falls over, and where the secrets live, and every one of those is load-bearing. Choosing to stay local opens a different one: what you would want back if the machine died. A project with more than one person is asked how someone proves who they are and what each may see. None of those are asked of a project they do not apply to, and a question that does not apply was never in the sequence rather than being skipped in front of the user with an apology. The count moves as the interrogation runs, and rule R4 already required showing it, so a total that grows honestly beats one that was a guess and stayed one.

Full record: [`049`](decisions/)

## 050 · Is the user's own reason for a choice part of the record?

**The user's own words are recorded, and a load-bearing question is not written without them**

Also considered: Yes, asked afterwards as a separate turn; Yes, but optional, and Forge notes when it is missing

The thesis of this product is that a user who cannot say why their app is built a certain way does not own it. The record is where that is either true or not, and a record saying only 'B' is evidence of nothing. It is kept in its own section, apart from Forge's account of the tradeoff, because merged into one the second quietly becomes the first. The question ends with the choice and the reason together, so it costs no extra turn and decision 013 is not broken. Furniture is not held up for it: a gate that fires on everything is one people learn to type past.

Full record: [`050`](decisions/)

## 051 · What happens to the choices made while the code is being written?

**Every choice made while building is recorded as it is made, and it cannot open a gate**

Also considered: Nothing, they are implementation detail; The builder mentions them in its reply; Stop and ask the user about each one

A recorded step decision does not settle everything inside it. What a module is called, whether a failure raises or returns, where a helper lives, which library gets pulled in: all invisible, and invisible is how a project ends up with conventions nobody chose and the user cannot explain when asked. They are marked in the header, inside the fingerprint, and the step gate refuses to count them. Without that the builder could clear its own gate by writing down what it had decided to do, which is the governor rule inverted. A choice that would change what the project is, is refused as a build note and sent back to be asked properly.

Full record: [`051`](decisions/)

## 052 · Is the block wide enough, and does it say what the question is about?

**The box is 92 columns, narrowable by setting, and every question names its concept**

Also considered: Widen it only when the terminal is wide; Drop the consequence lines so the options fit

At 74 columns an option and the consequence that makes it a choice did not fit on one line, so a menu of four read as eight and the part that wrapped was the part that mattered. The width cannot be measured, because the block is drawn into a chat panel rather than a terminal, so it is a setting with a sensible default and `FORGE_BOX_WIDTH` for a split pane. The concept line is the other half: a user who remembers that they picked B has learned nothing, and the idea underneath is the only part of this that outlives the project being built.

Full record: [`052`](decisions/)

## 053 · What does a subject owe the user before code touching it is written?

**Each subject carries the questions it owes, they are asked the first time a step touches it, and the step is blocked until they are recorded**

Also considered: Every question up front, before any code at all

The foundation asked twelve questions and then stopped. Everything after it was written by the planner in the moment, so a step called 'store the todos' could be asked one question or none worth the name, and the database was chosen by whichever model was writing that turn. `scripts/forge_topics.py` now holds eight subjects and the twenty questions they owe: the database owes which one, where it runs, how the shape changes once there is real data in it, how the code talks to it, and what a test opens; deployment owes how many pieces have to run, what starts and restarts them, and what happens in the five minutes after a bad release. Asked once per project by whichever step needs them first, because 'which database' is a project question that a step is merely the first to need, and asking it again at step nine would be the failure this product exists to prevent, performed by the product. The gate is in `next_gap`, not in a brief: every rule this repository put in a brief was eventually skipped by a model in a hurry, and a skipped question is invisible in a way a wrong answer is not.

Full record: [`053`](decisions/)

## 054 · Do the options past the foundation name real products?

**The stack question keeps naming shapes; every question after it names the actual products, with what each one costs**

Also considered: No. Shapes only, everywhere, as decision 041 has it for the stack; Yes, from the first question onwards; Let the planner decide per question

Decision 041 made the stack options name shapes rather than technologies, and that was right for the first question: naming a product there assumes the shape nobody has chosen yet. It is wrong for everything after it. By the time a step is storing something the shape is decided, and 'a relational database' is no help to anyone. So the database question offers Postgres you run yourself, Supabase, Neon, SQLite, MySQL and MongoDB, each with the thing that is actually wrong with it, and the orchestration question offers nothing, a service manager, Docker Compose, a platform and Kubernetes, and says out loud that Kubernetes is the answer at a scale you are not at. This amends 041 rather than editing it, in the shape decision 042 used.

Full record: [`054`](decisions/)

## 055 · Does a question say what goes wrong if it is answered badly?

**Every question carries one line on what a bad answer costs, and it is shown with a bar**

Also considered: Yes, but only in the decision record afterwards; Only where the consequence cannot be undone

The options say what each choice costs. They do not say what the question is worth, and the questions with the worst consequences are the ones that sound the most administrative: 'where does configuration live' reads like paperwork until the day the key is in the repository. A question whose weight the user cannot see is a question they answer at random. It uses the bar that already exists for a cost that cannot be undone, so nothing new was invented to carry it.

Full record: [`055`](decisions/)

## 056 · What happens when someone adds a feature to a project Forge has already built?

**A feature reads the recorded decisions it lives inside, is asked only what it owes that is not already answered, and is appended as a new phase**

Also considered: Nothing. The gates open once the last phase is built (what shipped); Run the whole interrogation again for the new feature

Every gate reads the phase list, so once the last phase was built `next_gap` found no unbuilt step and opened. Someone coming back a month later to add one thing got no questions at all, which is the worst moment to have no rules: a new feature is written against a codebase full of decisions nobody is re-reading. `plan_feature` returns three things and nothing else, the decisions the feature is built inside as ids and one-line choices, anything it wants that the project has ruled out, and the subject questions it still owes. The foundation is never asked again: it is on disk and still true, and re-asking it spends a new project's tokens to learn what was already written down. Phases are appended by `add_phase` rather than recompiled, because rewriting the list puts finished work through a new pen and can mark built steps unbuilt.

Full record: [`056`](decisions/)

## 057 · How does a decision get changed once it has been recorded?

**A new record that names the old one with `supersedes`, and the old one stays readable**

Also considered: Edit the record; Delete the old record and write a new one; Keep a separate list of what is no longer true

This is the shape decision 042 already used when Opus 5 replaced Opus 4.8 in 002, now enforced by the tool rather than done by hand. An edit destroys the only thing the record was for: what was believed, when, and why it changed. It also breaks the chain, since the fingerprint covers the body. It matters most on the incremental path, where a new feature meets a decision made months earlier: the clash is named, the user chooses between changing the feature and changing the decision, and changing the decision leaves a trace either way.

Full record: [`057`](decisions/)

## 058 · Should Forge use other people's plugins where they are better than its own?

**ponytail is wired in as an optional companion at the building and review stages, used in addition to Forge's own skills and never instead of them**

Also considered: Yes, copy the useful ones into the plugin

ponytail (github.com/DietrichGebert/ponytail, MIT) teaches an agent to write the least code that works: check whether it needs writing, whether the project already does it, whether the standard library does it, before adding anything. It is aimed at the same target as Forge from the other end. Forge governs which decisions get made; ponytail governs how much code the answer turns into, which is the same token argument that produced the incremental path. It is kept out of ROUTE on purpose. ROUTE is deterministic because its skills ship with Forge or with the pinned library, and folding in a plugin installed separately and updated on someone else's schedule would turn 'the same skills every time' into 'unless the user happened to install something'. So COMPANIONS is a separate table, absence is a suggestion rather than a failure, and where the two disagree Forge wins: the security floor is not overridable, and a recorded decision is not optimised away because a shorter version exists. Copying it in was rejected despite the licence allowing it, because a vendored copy of a repository moving that fast is a fork nobody volunteered to maintain.

Full record: [`058`](decisions/)

## 059 · How does the companion plugin actually reach a build, rather than sitting in a table?

**A SessionStart hook brings it in with Forge: one line when it is installed, the install command once per project when it is not, and silence on every error**

Also considered: Require it, and refuse to build without it

The routing table alone puts it somewhere that is read by whatever asks the table, and if the builder does not ask, nothing happens and nothing says so. That is the failure this repository has repeated more than any other: the rule was in the code and the code was not in the path. A hook is the path. It is deliberately the quietest one Forge has: it never blocks, it says nothing outside a Forge project or where Forge is paused, it swallows every error, and the offer is written to a marker file so it is made once per project rather than every session, because a suggestion repeated is an advertisement. Copying the rules in was rejected for the same reason as vendoring the plugin: a copy of a repository moving that fast is a fork nobody volunteered to maintain. Requiring it was rejected because it is somebody else's plugin and Forge's guarantees cannot depend on a thing Forge does not ship. FORGE_NO_COMPANION=1 turns it off.

Full record: [`059`](decisions/)

## 060 · What has to happen between a step appearing on the plan and its code being written?

**Two extra gates around the step: the ladder before anybody is asked anything, and the same ladder against the approach before it is built**

Also considered: A review after the code, in the fix loop, where the reviewers already are; Trust the builder to keep it small

Forge's question has always been which decision. The one before it, does this need writing and how much of it, was never asked, so a step that arrived on a plan got built at whatever size the model first imagined. The first gate runs the ladder (does it need to exist, does the project already do it, does the standard library do it, what is the smallest useful version, what the extra size costs) and puts the findings to the user as a size question with at least three answers. The second runs the same ladder against the approach once it is settled: unchanged means one line and carry on, and smaller means the user decides, because a change to what gets built is theirs and not the reviewer's. The second gate is the one that pays, because the approach is where over-building happens and by then everybody has agreed on the goal and stopped looking. Nothing in Forge judges whether code is minimal: that is the model's job with ponytail loaded, and Forge's job is to refuse to move until the answer is on disk. Reviewing after the code was rejected because by then it is written and deleting it is a second argument.

Full record: [`060`](decisions/)

## 061 · How does someone installing Forge end up with ponytail as well?

**ponytail is listed in Forge's marketplace, installed by the user, never installed silently**

Also considered: They find it themselves from the README; Vendor its rules into Forge's skills

A marketplace can carry more than one plugin, so adding Forge's marketplace now offers both and installing ponytail is one command from the same place rather than a link in a README. It points at Dietrich Gebert's repository, so it stays his: his updates, his licence, his name on it, and no fork of a fast-moving repository for anybody to maintain. Silent installation was rejected. Installing somebody else's software onto a user's account while they are reading about permissions answers a question nobody asked, and Claude Code installs plugins on the user's word rather than a plugin's. The offer is made at setup, in one line, and the session hook from decision 059 makes it once per project after that.

Full record: [`061`](decisions/)
