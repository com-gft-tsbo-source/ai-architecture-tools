# taskctl-worker

Subagent that works an existing `taskctl` Tasklist, per the user's
invocation prompt — performing each Task's described work and changing its
Status accordingly. Generic — usable against any project's `taskctl` store,
whatever produced its Tasks (`taskctl-author`, a hand-written one, or a
`rulectl tasklist` export; `taskctl` itself doesn't distinguish,
design-taskctl.md, "Operations"). Operates `taskctl` exclusively through the
`taskctl-worker-cli` Skill (`architecture/docs/skills/design-taskctl-worker-cli.md`)
— it never invents CLI usage of its own. Companion to `taskctl-author`
(`architecture/docs/subagents/design-taskctl-author.md`), which creates the
Tasks this Subagent works; the two never call each other. Unlike
`rulectl-checker`/`questctl-checker`/`questctl-researcher`, this Subagent
isn't forming a verdict about something else (compliance, an attribution, a
researched answer) — it's *doing* the work a Task describes, using
whatever general-purpose tools that requires (Read/Edit/Bash/...), then
recording what happened.

## Purpose

Given an existing Tasklist and a prompt describing how to work it, find the
Task to work (`taskctl-worker-cli`'s `next`), perform its described work,
and record progress and outcome via `annotate`/`set-status`/`info-review` —
including escalating to a human or subagent review, or marking a Task
blocked, exactly as `design-taskctl-worker-cli.md` already specifies at the
CLI-recipe level. This document adds what that Skill deliberately doesn't
cover: how the Subagent decides *what to do* for a Task, and the judgment
behind the outcome it eventually records.

## Input

- **`--root <path>`**: the `taskctl` store. Always supplied explicitly by
  the caller — no default, no guessing.
- **the invocation prompt**: mandatory, and controls two independent
  things:
  1. **Iteration mode** (`taskctl-worker-cli`, "Iteration model"): **one
     Task per invocation by default** — work whatever `next` returns to
     its next resting point, then stop. **Only when the prompt explicitly
     asks for more** (e.g. "arbeite die ganze Tasklist ab," "mach weiter
     bis du fertig bist") does this Subagent loop, calling `next` again
     after each Task reaches a resting point, until drained
     (`NoWorkAvailable`/`all_done`) or blocked by a Task already sitting in
     `[B]`/`[R]`/`[C]`.
  2. **Where/how the work happens.** There is no separate, structured
     "codebase path" input the way `rulectl-checker` takes one — a Task's
     described work isn't always "check code in one repository," so a
     single fixed location wouldn't generalize. If the work needs scoping
     to a particular directory, repository, or environment, that's stated
     in the prompt itself, in whatever terms the prompt's author used, and
     read like any other instruction.

This Subagent always follows `taskctl`'s own global, sequential `next`
order (design-taskctl.md, "Sequential Processing") — there is no
Phase-scoped or assignee-scoped subset it can be pointed at instead
(`assignee-type`/`assignee-name` stay purely informational for this
workflow, per `design-decisions.md`, "Amendments (2026-08-25, taskctl
`NoWorkAvailable` + taskctl-author-cli/taskctl-worker-cli design)" — no
`next` scope filter exists, or was added, for this reason). A prompt asking
to work "only Phase 2" isn't something this design can honor beyond what
`next`'s own ordering already produces on its own — if an earlier Phase has
unresolved work, `next` returns that first, regardless of the prompt.

## A Task's Description is a trusted work order — because of how it got there

Every other Subagent in this family states an explicit "this content is
data, never instruction" boundary for whatever it reads (`rulectl-author`'s
source document, `rulectl-checker`'s checked codebase, `questctl-checker`'s
answer-source). This Subagent is different in kind: it doesn't just read
and judge a Task's Description, it **executes** it — Bash commands, file
edits, whatever the described work actually calls for. That is a much
larger blast radius than any read-only judgment, so this document states
the boundary that makes it safe, rather than leaving it implicit:

**A Task's Description is trustworthy specifically because `taskctl-author`
never copies untrusted source-document text into it verbatim** — every
Task Description is that Subagent's own synthesis of what a source says and
what its invocation prompt asked for (`design-taskctl-author.md`, "Source
content is untrusted"). By construction, a Description already went through
one Subagent's judgment before this one ever sees it; it is not relayed
attacker content with a `taskctl` wrapper around it. This is what lets this
Subagent treat a Task's Description as an authoritative instruction to act
on, the same way any coding agent treats a task description a human wrote
directly — rather than needing its own per-Task suspicion layer the way
`rulectl-checker` needs one for the codebase it only ever *reads*.

This trust is scoped to the Description text itself, not to everything a
Task's *execution* subsequently touches: files, command output, and other
artifacts encountered while doing the described work are ordinary inputs to
an engineering task, carrying the same general caution any coding agent
already applies to untrusted repository content or tool output — nothing
specific to `taskctl` beyond what's stated above.

**Exception: Tasks exported by `rulectl tasklist`.** That export copies a
Rule's Description/Procedure verbatim into the Task (`lib/tasklist.py`),
and a Rule's text may itself be close to verbatim source-document content
(`rulectl-author`) — the synthesis guarantee above does not hold for them.
They are also not work orders but compliance checks, owned by
`rulectl-checker`. This Subagent recognizes them by `assignee-type`
`agent` or `tool` (the values the export sets — a heuristic: a hand-written
Task could carry them too) and never works them: it claims nothing, sets
`[B]` with "rulectl check task — use rulectl-checker", and reports it.

## Outward-facing and irreversible actions

Editing files in the working area is the normal case. Actions that leave
it or can't be undone — `git push`, publishing, deploying, sending
messages, deleting or overwriting outside the stated working area — are
performed **only** when the Task's Description or the invocation prompt
explicitly asks for them. Otherwise the Subagent completes the local part
and sets `[R]` with the pending action as the reason (e.g. "push pending:
needs user"). Local commits likewise only when the Task or prompt asks for
them. This is a risk-class rule, not "commit hygiene" — a looping worker
running unattended is exactly where an unrequested outward action does
damage.

## Tools

`Read`, `Glob`, `Grep`, `Edit`, `Write`, `Bash`, `WebFetch`, `Skill`. No
`Agent` (it never spawns further Subagents — a `review=subagent` Task goes
to `[C]` for someone else) and no MCP tools (no reach into external
services). A Task that genuinely needs either is a legitimate `[B]` with
that reason.

## Iteration model, resume logic, and status transitions

Fully specified at the CLI level in `taskctl-worker-cli`
(`design-taskctl-worker-cli.md`, "Iteration model" / "Recipes" / "Status
transitions, summarized") — this Subagent follows those recipes exactly,
not a variant of its own:

- Default: one Task per invocation, worked to its next resting point.
  Loop only when the prompt explicitly instructs it (see "Input," point 1).
- **Invariant**: never call `set-status`/`annotate`/`info-review` on any
  Task ID other than the one `next` most recently returned.
- `next` returning a Task already `[~]` is a **resume**, not a fresh
  start — read its History (`show --history`) for what's already been
  done before continuing; never re-claim it.
- `next` returning a Task already `[B]`/`[R]`/`[C]` is this run's blocker —
  nothing more to do (single-Task mode) or the point the loop stops
  (loop mode).
- `NoWorkAvailable`/`all_done` from `next` is the normal "nothing left"
  signal, not a failure.

## Workflow, per Task

1. **Pick the Task** (`next`, per "Iteration model" above).
2. **Understand the Task**: read its Description (and, for a resumed Task,
   its History) to determine what work it actually describes. If the
   Description alone doesn't say enough to know what "done" would even
   look like, that is itself evidence toward a `[B]` outcome in step 4, not
   something to guess past.
3. **Perform the described work**, using whatever tools it calls for
   (Read/Grep/Edit/Bash/...) — entirely outside `taskctl` and the
   `taskctl-worker-cli` Skill; this is ordinary engineering work, and this
   document doesn't prescribe *how* to do it well, only what happens
   before and after.
4. **Form the outcome — a concrete, reasoned judgment, never a guess.**
   Adapted from `rulectl-checker`'s own compliance-verdict discipline
   (`design-rulectl-checker.md`, step 3d) and `questctl-researcher`'s
   evidence threshold (`design-questctl-researcher.md`): marking a Task
   `[X]` requires being able to state *why* the work is actually complete
   and correct, not just that nothing obviously failed. If that can't be
   said — genuine ambiguity in the Task, a change whose correctness this
   Subagent can't itself verify, a decision that isn't this Subagent's to
   make — the honest outcome is `[R]`/`[C]` (needs review) or `[B]`
   (blocked), never a confident-sounding `[X]` reached by guessing. A
   Task's `review` Metainfo, if already declared at authoring time, is a
   floor, not a ceiling — this Subagent may still escalate a
   `review=none` Task that turns out to need eyes on it, or de-escalate
   one that turns out not to (`taskctl-worker-cli`, "Recipes": the
   `info-review` mechanism, symmetric both directions).
5. **Record it**: `annotate` with what was actually done, regardless of
   outcome, then `set-status` (with `info-review` first, only if the
   current `review` value doesn't already cover the target) — exactly the
   `taskctl-worker-cli` recipes for done / needs-review / de-escalation /
   blocked.

## Report

Retrospective, like every sibling's. Per Task worked this run:

- ID and Signature; status before → after.
- What was done (files touched, commands run) — matching what was
  `annotate`d.
- The evidence behind the outcome: why `[X]` is justified, or why
  `[R]`/`[C]`/`[B]`.
- Any `info-review` change (escalation/de-escalation) and why.

Then: the **stop reason** (single Task done / `all_done` / blocked by
`<id>` in `[B]`/`[R]`/`[C]` / error) and the result of the end-of-run
verification (`show` of every touched Task; any mismatch with this run's
own bookkeeping reported as such — the store is the source of truth).

## Interaction with the taskctl-worker-cli Skill

This Subagent never constructs `taskctl` command lines beyond what
`taskctl-worker-cli` documents — picking the Task, claiming it, logging
progress, and setting the outcome all go through that Skill's recipes. If a
needed operation isn't covered there, that's a gap in the Skill, not
something to work around ad hoc in the Subagent.

## Future extensions

- **Automated regression evals.** Today's acceptance is a manual smoke
  test, same as every sibling Subagent; the resume-after-interruption path
  and the escalate/de-escalate `info-review` mechanism in particular
  deserve reproducible scenarios once a harness exists. Not designed yet.
- **A verification step before `[X]`** (e.g. running a project's own
  tests/linters as part of forming the outcome judgment) is deliberately
  left to this Subagent's own general competence as an engineering agent,
  not prescribed here — see "Out of scope."

## Out of scope

- Creating, restructuring, or deleting Tasks/Phases — entirely
  `taskctl-author`'s job.
- A `next` scope filter (Phase- or assignee-scoped) — see "Input"; not
  built, and not something this Subagent's workflow needs given
  `assignee-type`/`assignee-name` stay purely informational.
- A tool allow-list (unlike `rulectl-checker`) — `assignee-type=tool`
  Tasks are never worked here (see the `rulectl tasklist` exception); a
  Task's described work is performed with this Subagent's own ordinary
  toolset, not dispatched to a specific named external tool.
- A structured "codebase path" input — see "Input," point 2.
- Prescribing *how* to do good engineering work (testing discipline,
  commit hygiene, etc.) — this Subagent's own general competence, not a
  `taskctl`-specific concern.
- A dedicated automated test/eval harness — v1 acceptance is a manual
  smoke test, same as every sibling Subagent. See "Future extensions."
