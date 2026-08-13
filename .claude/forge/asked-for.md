---
type: asked-for
project: forge-mentor
entries: 22
generated: yes, from the decision records; do not edit
---


# What you asked for

Your own words, from every decision that carries them, newest last. This is a
view of `decisions/`, not a second copy: nothing is written here that is not
already recorded, and deleting a record removes its line.

### 047 · How many options does a question put in front of the user?

> It is giving very limited options. It should not give limited options in the code. For example it is only giving an option for a docker setup or data. There should be multiple options.

**What it became:** At least three and at most six, each carrying its cost, refused at the renderer

### 048 · Does the menu narrow against what the project has already decided?

> Only once if the person wants to make the app locally then only SQLite. There should be no docker.

**What it became:** The menu narrows against the recorded facts, and what it removes is shown with the reason

### 049 · What happens to the questions an answer implies but the fixed list does not contain?

> If you want to do deployment there should be multiple questions related to the project.

**What it became:** An answer opens the questions it implies, and they are inserted where they belong

### 050 · Is the user's own reason for a choice part of the record?

> It should ask why it made their choice on the next decision, and everything should be recorded.

**What it became:** The user's own words are recorded, and a load-bearing question is not written without them

### 051 · What happens to the choices made while the code is being written?

> If you are coding, you have to record all of your decisions.

**What it became:** Every choice made while building is recorded as it is made, and it cannot open a gate

### 052 · Is the block wide enough, and does it say what the question is about?

> The question should be related to a concept, and it should be wide.

**What it became:** The box is 92 columns, narrowable by setting, and every question names its concept

### 053 · What does a subject owe the user before code touching it is written?

> You have to ask the user questions at each step of what we are integrating so that the user's mind does not move towards a slop. He doesn't only rely on giving prompts.

**What it became:** Each subject carries the questions it owes, they are asked the first time a step touches it, and the step is blocked until they are recorded

### 054 · Do the options past the foundation name real products?

> I want to figure out whether I have to use Supabase or other databases or something else.

**What it became:** The stack question keeps naming shapes; every question after it names the actual products, with what each one costs

### 055 · Does a question say what goes wrong if it is answered badly?

> You have to explain the question as well and why it matters, why that thing matters, what happens.

**What it became:** Every question carries one line on what a bad answer costs, and it is shown with a bar

### 056 · What happens when someone adds a feature to a project Forge has already built?

> I want you to have an incremental approach. If, after the first version, you want to add a feature, there are fewer tokens and the product is token-efficient. By adding one feature we are not disturbing the other feature.

**What it became:** A feature reads the recorded decisions it lives inside, is asked only what it owes that is not already answered, and is appended as a new phase

### 057 · How does a decision get changed once it has been recorded?

> By adding one feature we are not disturbing the other feature.

**What it became:** A new record that names the old one with `supersedes`, and the old one stays readable

### 058 · Should Forge use other people's plugins where they are better than its own?

> I want you to also see if we can integrate or work with the ponytail plugin, which is a very good plugin for coding of AI. If we can integrate that into this plugin, our code quality is good enough.

**What it became:** ponytail is wired in as an optional companion at the building and review stages, used in addition to Forge's own skills and never instead of them

### 059 · How does the companion plugin actually reach a build, rather than sitting in a table?

> Whenever in our plugin we use Forge, I also want to use that same hook that triggers this repository and this ponytail thing.

**What it became:** A SessionStart hook brings it in with Forge: one line when it is installed, the install command once per project when it is not, and silence on every error

### 060 · What has to happen between a step appearing on the plan and its code being written?

> Ponytail will ask: is this thing important or not, will this give a benefit. Claude re-evaluates his approach, asks the user, gives the concept. Then ponytail evaluates Claude's approach and the modified approach is asked from the user.

**What it became:** Two extra gates around the step: the ladder before anybody is asked anything, and the same ladder against the approach before it is built

### 061 · How does someone installing Forge end up with ponytail as well?

> In the Forge project, whenever this plugin is completed and someone uses this plugin, it should be installed directly when Forge is, because ponytail is for coding.

**What it became:** ponytail is listed in Forge's marketplace, installed by the user, never installed silently

### 062 · Is ponytail optional or required?

> Keep in mind that Ponytail is compulsory. The code quality is improved by Ponytail.

**What it became:** Required. Setup stops without it, the readiness check is fatal, and the user installs it

### 063 · What happens when the code refers to something that does not exist?

> I want that if the AI hallucinates, Ponytail unhallucinates, or asks questions from me to improve the code, and then they ask questions from me.

**What it became:** Every import is checked against the project's own manifests and files, every citation of a decision against the records, and anything unaccounted for goes to the user as a question

### 064 · How does a reviewer that runs in the session join the two that run on GitHub?

> After each PR I want the code reviews of Sourcery and CodeRabbit to come, combine with the ponytail reviews, and then Claude fixes all of those problems.

**What it became:** ponytail's findings are filed in pr-<n>.local.md, merged into pr-<n>.md on every fetch, and gated exactly like CodeRabbit's and Sourcery's

### 065 · What makes the local review run once the hosted ones have landed?

> Whenever the two apps' md files for the PRs are downloaded locally, then the ponytail review runs. When it runs we have all of the reviews and all of the improvements, and after that everything runs.

**What it became:** Every pull request's review carries a fingerprint, the local review file records which version it was written against, and anything else is owed until they match

### 066 · What does somebody see when they come back to a project after a gap?

> When we exit Claude Code it should have something so that when we hit forge status again it continues to the next question or phase, and gives a brief summary of all of the previous work, in a box.

**What it became:** `catch_up` returns two blocks: where you left off, assembled from the records, and then the open question or next step

### 067 · Where is the plan drafted?

> Whenever I propose my plan to my plugin, it should use the Claude plan mode specifically to make the plan. If there is any requirement of ponytail there to ask questions in the plans, I'll review the plan.

**What it became:** The planner enters Claude Code's plan mode before drafting the phases and stays in it until the user accepts, running ponytail's ladder over the plan while there

### 068 · How does the owner find a small thing they asked for months ago?

> I have told you a lot of these smaller things, a lot of them. Is there any fact check you are keeping, because I may forget.

**What it became:** `asked-for.md`, generated from the 'In their words' section of every record
