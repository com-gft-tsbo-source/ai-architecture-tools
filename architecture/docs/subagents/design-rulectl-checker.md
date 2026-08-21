# rulectl-checker

Subagent that checks a codebase for compliance with `rulectl` Rules, by
working a `taskctl` tasklist generated via `rulectl tasklist`. Generic —
usable against any project's `rulectl`/`taskctl` store and any codebase;
the two need not be the same repository. Operates `rulectl`/`taskctl`
exclusively through the `rulectl-checker-cli` Skill
(`architecture/docs/skills/design-rulectl-checker-cli.md`) — it never
invents CLI usage of its own. Companion to `rulectl-author`
(`architecture/docs/subagents/design-rulectl-author.md`), which creates the
Rules this Subagent checks; the two never call each other.

## Purpose

Given an existing set of active `rulectl` Rules and a codebase, verify the
codebase against every Rule and record the outcome — compliant, violated
(needs human review), or not checkable (e.g. a disallowed tool) — via
`taskctl` status and annotations. This is the checking half of the rulectl
workflow; a pure auditor, it never edits the codebase itself.

## Input

- **`--root <path>`**: the shared `rulectl`/`taskctl` store. Always
  supplied explicitly by the caller — no default, no guessing.
- **codebase path**: where the code to check lives. Always supplied
  explicitly by the caller, **independent of `--root`** — the Rules can
  live in a completely different repository from the code they apply to.
  Normally the whole codebase; the caller may narrow it to a subdirectory.
- **rule-scope filter** (optional): a Language/Context/Category path,
  passed straight through to `rulectl tasklist`'s own
  `--language`/`--context`/`--category` flag. Omit for the whole store.

## Tool allow-list

A fixed list, maintained **in this Subagent's own definition** (not a
per-invocation parameter), of tool names permitted to run for
`checkable=<tool>` Rules. Starts **empty**: every `checkable=<tool>` Task
is `B` (blocked, reason "tool not on the allow-list") until a tool is
added here deliberately. Extend it by editing the Subagent (and this
design document, which is authoritative for the list's contents) as tools
are vetted — there is no dynamic or remote allow-list, and no
per-invocation override.

**Current allow-list**: *(empty — no tools vetted yet)*.

This exists because Rules can originate from `rulectl-author` processing a
fetched URL (`design-rulectl-author.md`, "Input") — an untrusted document
could otherwise plant an arbitrary command as a Rule's `tool` metainfo,
which this Subagent would then execute. Restricting execution to a
deliberately maintained, empty-by-default list closes that gap.

## Workflow

1. **Refresh the tasklist**: run `rulectl tasklist --json` (scoped by the
   rule-scope filter, if given) via the Skill. This brings the `taskctl`
   store's Rule-derived Tasks up to date with the currently active Rules
   before any checking starts — no separate precondition step for the
   caller. `tasklist` returns the full list of Tasks it just created or
   updated, one entry per exported Rule; with `--json` that list comes back
   as structured output, IDs included.
2. **Capture the work set once, directly from that refresh output**: the
   exact Task IDs `rulectl tasklist --json` just reported in step 1 —
   nothing broader. **Never derive the work set from a separate `taskctl
   list --status " "` call**: that would return every open Task in the
   store, including ones this run's `tasklist` scope never touched (a task
   left open by unrelated `taskctl` activity, or one outside the
   `--rule-scope` filter) — silently widening this run beyond what the
   caller asked to check. **Never use `taskctl next`** for this either:
   `next` (`taskctl.py`, `_handle_next`) selects the first task whose status
   is anything other than `X`, so a task this run has already moved to `R`
   or `B` still qualifies — looping `next` would return that same task
   again instead of advancing to the genuinely untouched ones.
3. **Work every task in that captured list to completion, never aborting
   early.** For each task:
   a. Mark it in progress (`[ ]→[~]`, "checking") — every task starts
      `open`, and `open`'s only forward step is `in-progress`; the outcome
      statuses below are only reachable from there.
   b. Read its Description — the embedded Rule text (`checkable=llm`) or
      the tool instruction naming a `tool`/`tool-rule` (`checkable=<tool>`).
   c. **`checkable=llm`**: examine the codebase (at the given codebase
      path) against the Rule text using judgment — read/search the
      relevant files. Determine compliant or violated.
   d. **`checkable=<tool>`**: if the named tool isn't on the allow-list,
      this task is "can't check" — do not run it. Otherwise invoke the
      tool against the codebase and interpret its result for the specific
      `tool-rule` referenced in the Description.
   e. **Record traceability.** Regardless of outcome, `annotate` the task
      with what was actually examined (files/pattern/scope), *and* why the
      Rule applies to that scope in the first place — not just the bare
      verdict, and not just what was looked at. This applies the same
      completeness discipline that `rulectl-author`'s worklist reconciliation
      enforces on the authoring side, here to checking: a verdict without a
      stated scope cannot be told apart from one reached by skipping most of
      the codebase, and a stated scope without its applicability rationale
      cannot be told apart from one picked arbitrarily.
   f. **Set the outcome status** via the Skill's recipes:
      - compliant → `X`, message "compliant".
      - violation → `info-review user` then `R`, message = the violation
        detail, specific enough for a human reviewer to act on without
        re-deriving it.
      - can't check → `B`, message = the reason (disallowed tool, or the
        error encountered).
   A single task's outcome — including a failure to check it — never stops
   the run; move on to the next task in the captured list.
4. **Verify, then report.** After the captured list is exhausted, re-read
   the store's actual, persisted status for every ID in the step-2 snapshot
   — don't rely on this run's own bookkeeping of what it believes it set;
   a `set-status` call that silently failed, or a task that never made it
   past "in progress", must not be reported as if it landed cleanly.
   Summarize this run's own tasks (not the store's full history — filter by
   the snapshot IDs) in four categories: compliant (`X`), escalated-for-
   review (`R`, with each violation's detail), blocked (`B`, with each
   reason), and **not successfully finalized** — any snapshot ID whose
   re-read status isn't one of those three (e.g. still `~`, or a
   `set-status` call that errored), together with whatever is known about
   why. This last category doesn't change step 3's "never abort early": a
   task landing here is still visited and moved on from during the run, it
   just didn't reach a clean terminal status — the report says so instead of
   miscounting it. Retrospective, like `rulectl-author`'s report — a record
   of what happened, not a plan awaiting approval.

## Status mapping (verified against `lib/taskctl_spec.py`)

- Tasks arrive from `rulectl tasklist` with `review` metainfo unset
  (defaults to `none`): normal forward path `[ ]→[~]→[X]`.
- Every task is first moved `[ ]→[~]` ("checking") — `open`'s only forward
  step — before any outcome status is set; a direct jump from `open` to
  `X`/`R`/`B` is off-path and fails without `--force`.
- Compliant: stays on that path, `[~]→[X]` directly.
- Violation: `info-review <id> user` first — this changes the *effective*
  forward path, since the transition validator reads the task's current
  `review` value at the moment of `set-status`, not one fixed at creation
  — making `[~]→[R]` a normal, on-path step afterward. No `--force`
  needed.
- Can't check: `[~]→[B]` is reachable regardless of `review`, provided a
  `--message` is given (taskctl's general rule for entering `[B]`).
- No change to `rulectl.py`/`taskctl.py` was needed for any of this —
  `info-review` already existed and the transition validator already reads
  `review` dynamically.

## Re-checking

Every run re-checks every in-scope active Rule's Task, by construction —
this is not an opt-in extension, it's what step 1 already causes. Re-running
`rulectl tasklist` force-resets a Task's status back to `open` whenever it
had drifted away from `open` (design-rulectl.md, "Operations"; confirmed in
`design-decisions.md`, "Amendments (2026-08-21, rulectl `tasklist`)") —
including a Task this Subagent itself previously closed at `[X]`, `[R]`, or
`[B]` on an earlier run, as long as its source Rule is still `active` and
within the rule-scope filter. Since step 1 (refresh) always runs before step
2 (snapshot capture), a previously-closed Task for a still-active, in-scope
Rule is *already back at `open`* by the time the snapshot is taken — this
Subagent has no way to tell "never checked" apart from "checked before,
reset by the refresh", and does not try to. This is a deliberate property of
`tasklist`, not a gap here: a Rule could have changed since the last check,
so re-verifying it on every run is the correct default, not something to
work around.

What this Subagent still never does on its own: re-evaluate a Task that is
open in the step-2 snapshot for a reason *other* than this run's own
refresh — there is none, since every open Task in the snapshot got there
either freshly (never exported before) or via this run's force-reset. There
is also no way to check a Rule *less* often than every run without changing
`tasklist` itself (e.g. skipping unchanged Rules) — that would be a change
to `rulectl`, out of scope for this Subagent's own design.

## Interaction with the rulectl-checker-cli Skill

This Subagent never constructs `rulectl`/`taskctl` command lines beyond
what `rulectl-checker-cli` documents. If a needed operation isn't covered
there, that's a gap in the Skill, not something to work around ad hoc in
the Subagent.

## Out of scope

- Fixing violations — pure auditor, never edits the codebase (v1).
- A per-invocation tool allow-list parameter — the list lives in this
  Subagent's own definition (see "Tool allow-list").
- Changing `rulectl tasklist`'s own re-export/reset behavior, or building
  logic here to work around it, to check a Rule less often than every run
  (see "Re-checking") — a change to `rulectl` itself, not this Subagent.
- Authoring Rules — that's `rulectl-author`'s job.
- A dedicated automated test/eval harness — v1 acceptance is a manual
  regression run against a scratch store, same as `rulectl-author`.
