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

1. **Refresh the tasklist**: run `rulectl tasklist` (scoped by the
   rule-scope filter, if given) via the Skill. This brings the `taskctl`
   store's Rule-derived Tasks up to date with the currently active Rules
   before any checking starts — no separate precondition step for the
   caller.
2. **Capture the work set once**: `taskctl list --status " "` (open) —
   the fixed list of tasks this run processes. **Never use `taskctl
   next`** for this: `next` (`taskctl.py`, `_handle_next`) selects the
   first task whose status is anything other than `X`, so a task this run
   has already moved to `R` or `B` still qualifies — looping `next` would
   return that same task again instead of advancing to the genuinely
   untouched ones.
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
      with what was actually examined (files/pattern/scope) — never just
      the bare verdict. This applies the same completeness discipline that
      `rulectl-author`'s worklist reconciliation enforces on the authoring
      side, here to checking: a verdict without a stated scope cannot be
      told apart from one reached by skipping most of the codebase.
   f. **Set the outcome status** via the Skill's recipes:
      - compliant → `X`, message "compliant".
      - violation → `info-review user` then `R`, message = the violation
        detail, specific enough for a human reviewer to act on without
        re-deriving it.
      - can't check → `B`, message = the reason (disallowed tool, or the
        error encountered).
   A single task's outcome — including a failure to check it — never stops
   the run; move on to the next task in the captured list.
4. **Report.** After the captured list is exhausted, summarize this run's
   own tasks (not the store's full history — filter by the task IDs from
   the step-2 snapshot) in three categories: compliant (`X`),
   escalated-for-review (`R`, with each violation's detail), and blocked
   (`B`, with each reason). Retrospective, like `rulectl-author`'s report —
   a record of
   what happened, not a plan awaiting approval.

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

Out of scope for v1: this Subagent only ever works the tasks captured as
*open* at the start of a single run; it never re-evaluates a task already
at `[X]`, `[R]`, or `[B]`. Re-checking a previously-flagged task (e.g. after a
fix) is a possible later extension — for now, resetting such a task's
status so this Subagent picks it up again is a manual step outside this
Subagent's scope.

## Interaction with the rulectl-checker-cli Skill

This Subagent never constructs `rulectl`/`taskctl` command lines beyond
what `rulectl-checker-cli` documents. If a needed operation isn't covered
there, that's a gap in the Skill, not something to work around ad hoc in
the Subagent.

## Out of scope

- Fixing violations — pure auditor, never edits the codebase (v1).
- A per-invocation tool allow-list parameter — the list lives in this
  Subagent's own definition (see "Tool allow-list").
- Re-checking already-closed/escalated/blocked tasks (see "Re-checking").
- Authoring Rules — that's `rulectl-author`'s job.
- A dedicated automated test/eval harness — v1 acceptance is a manual
  regression run against a scratch store, same as `rulectl-author`.
