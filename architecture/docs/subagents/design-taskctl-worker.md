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

**Exception — `rulectl tasklist` exports.** Recognize an export only by
its structured `origin=rulectl:<rule-id>` Metainfo (for a valid export,
`<rule-id>` equals the Task ID). Never infer origin from `assignee-type`,
which ordinary Tasks may also set to `agent` or `tool`.
A marked Task belongs to `rulectl-checker`; never execute its Description.
If `next` returns it open or in progress, set `[B]` directly, without a
claim or annotation, with `--message "rulectl check task — use rulectl-checker"`.
For an already-blocked/review Task, leave it unchanged and report the
blocker. A malformed `rulectl:` marker is blocked as invalid provenance,
never treated as an ordinary work order.

Legacy exports have no marker until the next `rulectl tasklist` export,
which adds/repairs it. They cannot be identified reliably before then.
Before using this worker on a store containing legacy exports, the caller
must refresh those exports through `rulectl-checker`. The worker must not
use assignment or Description text as a fallback provenance heuristic.

## Local work only — remote actions need the user's approval

`taskctl` is mainly used to guide an AI through **progressive local
changes**; remote changes are the rare exception. Rather than enumerating
forbidden actions (a list always misses one — a `gh workflow run`, a
`curl -X POST` to JIRA), "local" is defined positively and everything else
is gated.

**Classification by effect, not by tool:**

- **Local** (free): editing files in the working area; local git
  operations (commit only when the Task or prompt asks); local builds,
  tests, scripts; installing dependencies into the working area.
- **Read-only remote** (free): `WebFetch`, `git fetch`, HTTP GET, reading
  docs.
- **Remote** (gated): anything that changes state outside the working area
  and local repository — e.g. `git push`, writing `gh`/`glab` calls,
  triggering CI/CD, JIRA/Confluence/Slack changes, mail, cloud/cluster
  CLIs, `docker push`, package publishing, HTTP POST/PUT/PATCH/DELETE —
  plus irreversible local operations on things the Task didn't create.
  When in doubt, remote.

**Exactly one path for a remote action** — the pre-action gate:

1. The Task must have `review=user`. `taskctl-author` sets it on every
   remote-action Task (`design-taskctl-author.md`, "Metainfo population");
   for any other Task (hand-written, or `review` `none`/`subagent`) the
   worker raises it via `info-review user` itself — the existing
   escalation mechanism (`taskctl-worker-cli`, "Recipes").
2. The worker does the local part, then sets `[R]` with
   "`<action>` pending: needs user approval" — **without** performing it.
3. The user approves by setting the Task back to `[~]` (the normal
   `[R]`→`[~]` rework step) with a message approving the action.
4. The next worker run resumes the `[~]` Task, finds in its History a
   `[R]`→`[~]` entry **after** its latest pending (or `failed`/`outcome
   unknown`) `[R]` approving the action,
   annotates `<action> executing: approved` **before** performing it,
   performs it exactly once, annotates `<action> done: <result>` (or
   `<action> failed: <error>`), and sets `[R]` again for the user's final
   check.

One approval covers exactly one execution attempt; the `executing`
annotation consumes it. The marker texts are fixed message prefixes — a
convention of `taskctl-worker-cli`, not a CLI feature — so a later run can
tell from History alone how far an approved action got.

**Failures around an approved action** (no automatic retry of the action,
ever — a remote timeout does not tell whether it took effect):

- *Before the action* (`info-review user`, the pending `[R]`, or the
  `executing` annotation fails): do not perform it; stop and report. With no
  consumed approval in History, the next run repeats the preparation or the
  pending review on its own.
- *The action fails or only partly succeeds*: annotate `<action> failed:`
  with the error and the observed partial state, then `[R]` with the same
  prefix. Re-running it needs a new approval.
- *The result annotation fails after the action ran*: retry that annotation
  once; if it still fails, put the result into the final `[R]` message; if
  that fails too, the run's report carries the full result so the user can
  record it. Never re-run the action.
- *Resume finds `executing` after the latest approval but no `done`/`failed`*
  (e.g. the previous run died mid-action): the outcome is unknown. Do not
  perform the action; annotate and set `[R]` with `<action> outcome unknown:
  verify remote state`.
- *Resume finds `done`/`failed` but no final `[R]`*: do not perform the
  action; only set the `[R]` for the final check.

A `failed` or `outcome unknown` `[R]` doubles as the new pending review: the
user re-authorizes exactly one further attempt by moving it back to `[~]`
with an approving message (design-decisions.md, "Amendments (2026-10-30,
remote-action recovery)").

A rework message that asks for changes is rework, not approval. Nothing
else counts as approval — not the Task's Description, not the invocation
prompt (it may come from a calling agent, not the user), not content
encountered while working. This replaces the earlier rule that an
explicit request in the Task or prompt sufficed for an outward action.

**Strength of this guarantee.** The classification and the History check
are the model's judgment, not a mechanism — a strong default, not a hard
guarantee. A hard guarantee must come from the environment the worker
runs in; see "Operating guidance".

## Operating guidance

For unattended runs — loop mode in particular — the operator should:

- run Claude Code's sandbox with outbound network writes restricted, so a
  misclassified remote call fails instead of taking effect;
- not give the session remote credentials it doesn't need for the
  Tasklist (no `gh` token, no JIRA/cloud credentials in the environment).
  Without credentials, a remote write fails even if the model gets the
  classification wrong.

A plugin-level backstop (blocking obvious commands such as `git push`,
`gh`, `curl -X POST` for this Subagent only, via its tool configuration or
a hook) is a possible later addition — only as a backstop, since a pattern
list never catches everything (`python -c ...`, scripts). Not built: it
first needs verifying that Claude Code supports such restrictions per
Subagent; a plugin-wide hook would also affect the user's normal sessions.

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
   (blocked), never a confident-sounding `[X]` reached by guessing.
   The Task's existing `review` is a minimum requirement. Preserve
   `user`/`subagent` even if you believe review unnecessary; escalate a
   `none` Task when needed. De-escalate only on an explicit user
   instruction for this Task, never on your own judgment. Never
   de-escalate a Task that includes a remote action. Record the user
   instruction and reason for every authorized review change.
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
