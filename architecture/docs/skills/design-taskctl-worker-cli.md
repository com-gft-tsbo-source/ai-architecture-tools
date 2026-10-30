# taskctl-worker-cli

Skill that wraps the `taskctl` CLI for the `taskctl-worker` Subagent
(`architecture/VISION.md`; no Subagent design document exists yet —
`design-decisions.md`, "Amendments (2026-08-25, taskctl `NoWorkAvailable` +
taskctl-author-cli/taskctl-worker-cli design)"). Purely an instructional
reference — a `SKILL.md`, no executable wrapper code. The invoking agent
calls the `taskctl` binary itself via Bash; this Skill only teaches it how
to change a Task's Status correctly, in step with the work actually done —
never how to author or restructure the Task list (`taskctl-author-cli`'s
job) and never how to perform a Task's described work (Read/Grep/Bash/etc.,
entirely outside `taskctl` and this Skill). Companion to
`taskctl-author-cli`, which creates the Tasks this Skill works; the two
Skills' command surfaces are disjoint by design, and their Subagents
never call each other's `taskctl` commands.

Unlike `rulectl-checker-cli` (which wraps *two* CLIs, because `rulectl
tasklist` exports a bounded snapshot into `taskctl` first), this Skill
wraps `taskctl` alone: Tasks already live directly in the `taskctl` store —
whether created by `taskctl-author` or exported via `rulectl tasklist`
(design-taskctl.md, "Operations": taskctl doesn't distinguish) — so there
is no upstream export step to run first.

## Scope

- `next` — find the Task to work.
- `set-status` — the `[~]`→terminal transitions (`[X]`/`[R]`/`[C]`/`[B]`),
  and the `[~]` claim itself.
- `annotate` — log execution progress, on every Task regardless of
  outcome.
- `show` — read a Task's actual persisted state: to pick up context when
  resuming an already-`[~]` Task, and to verify the real outcome at the
  end of a run.
- `info-review` — but **only** to escalate or, on explicit user instruction, de-escalate a Task's review
  requirement immediately before the matching `set-status` call (see
  "Recipes"), never to reassign a Task.

Not in scope: `add`, `add-phase`, `set-description`, `group-phase`,
`reorder`, `delete`, `info-assignee-type`, `info-assignee-name` —
authoring/restructuring actions, `taskctl-author-cli`'s job entirely. Also
not in scope: `list`, `show-metagroups` — `next` already returns the exact
Task to work, so there is no browsing/snapshot need the way
`taskctl-author-cli` has `list` for duplicate-checking. And `reindex`,
`history` — maintenance/reporting, neither authoring nor working.

## Conventions

- **`--root <path>`**: always supplied by the caller, exactly as given —
  never hardcoded or guessed.
- **`--json`**: pass it on `next` and `show`, whose output you parse. Omit
  it on `set-status`/`annotate`/`info-review` — pure write calls whose
  outcome is the exit code, nothing in their output is ever read.
- **Exit codes**: `0` = ok, `1` = error, `2` = a malformed command line
  (argparse: unknown subcommand or option).
- **`--force` is never used** in normal operation. Every transition this
  Skill's recipes use is already on a Task's normal forward path (or, for
  `[B]`, reachable from any non-terminal status with a `--message`) —
  reaching for `--force` would mean a wrong assumption somewhere upstream,
  not a legitimate shortcut. (`--force` also requires `--user-approved`,
  design-taskctl.md, "Guards".)
- **Guards** (design-taskctl.md, "Guards"): taskctl rejects moving a Task on
  while an earlier gating Task is unresolved (`sequence_blocked`), and any
  self-decided user review — `[R]`→`[X]`, `info-review` while in
  `[R]`/`[C]`, lowering `review` from `user` (`approval_required`). Under
  `--json` the `reason` is machine-readable. A rejection is never worked
  around: stop and report it to the user. `--user-approved "<the user's
  instruction>"` is added to a write **only** when the user explicitly
  instructed exactly that operation for this Task — never on the Worker's own
  judgment, never because a prompt from a calling agent asserts approval.
  The text is recorded in History as `USER-APPROVED: <text>`.

## Iteration model

Whether one Worker invocation processes one Task or several is an
instruction from whoever invokes the Worker (a user, or an orchestrating
agent) — never a `taskctl` CLI flag:

- **Default: one Task per invocation.** Call `next` once, work that Task
  through to its next resting point — `[X]`, or an escalation
  `[R]`/`[C]`/`[B]` — then stop. An outer loop (if any) decides whether to
  invoke the Worker again.
- **Loop mode, only on explicit instruction.** Repeat: call `next`; if it
  reports `NoWorkAvailable`/`all_done` (see "Recipes"), stop — the store is
  drained; if the returned Task is already sitting in `[B]`/`[R]`/`[C]`,
  stop — that is this run's blocker, and `next` would just keep
  re-returning it, since it can never skip ahead to a later Task while an
  earlier one is unresolved (design-taskctl.md, "Sequential Processing").
  Otherwise, work the Task to its resting point and loop back to `next`.

Both modes share the exact same per-Task logic (below); they differ only
in whether the Worker calls `next` again once a Task reaches a resting
point.

**Invariant, holding in both modes**: never call
`set-status`/`annotate`/`info-review` on any Task ID other than the one
`next` most recently returned. Since `next` always returns the earliest
not-done Task in priority order, a *later* Task can only legitimately be
`[~]` if some earlier, in-order Worker invocation put it there itself —
this makes "only ever touch what `next` hands you" self-enforcing, not a
separate bookkeeping burden.

## Recipes

**Pick the Task to work, at the start of every iteration:**

```
taskctl --root <root> --json next
```

Parse the returned object's `status` field to decide what happens next:

- **`" "` (open)** — a fresh Task. Claim it before doing anything else —
  `open`'s only forward step is `in-progress`; jumping straight to an
  outcome status is off-path and fails without `--force`:
  ```
  taskctl --root <root> set-status <id> "~" --message "starting"
  ```
- **`"~"` (in progress)** — a **resume**, not a fresh start (this Task was
  left mid-work by an earlier invocation — this run, or a prior one that
  was interrupted). Do **not** re-issue the `[~]`-claim above; read the
  Task's History first, for context on what's already been done:
  ```
  taskctl --root <root> --json show <id> --history
  ```
- **`"B"`/`"R"`/`"C"`** — this run's blocker: work on this Task is
  suspended pending someone else's action (a blocked dependency, a pending
  user/subagent review). In single-Task mode this is simply what `next`
  returned — there is nothing further to do but report it; in loop mode,
  this is where the loop stops.

If the `next` call itself fails: under `--json`, its output parses as
`{"reason": "all_done", "message": "no open tasks"}` — the store is fully
drained (every Task is `[X]`, or there are no Tasks at all). This is the
normal "nothing left" signal, not an error to report as a failure — stop
cleanly (loop mode: end the run; single-Task mode: report there was
nothing to work). Any other failure (non-JSON output, an unexpected exit)
is a genuine error, not "drained" — never conflate the two.

**Do the described work** — Read/Grep/Bash/whatever the Task's Description
actually calls for. Entirely outside `taskctl` and this Skill; this is the
`taskctl-worker` Subagent's own judgment, not something this Skill
prescribes.

**Log what happened, regardless of outcome:**

```
taskctl --root <root> annotate <id> --message "<what was actually done>"
```

**Then set the outcome:**

*Done, no review needed:*
```
taskctl --root <root> set-status <id> X --message "<summary>"
```

*Needs review* — check the Task's *current* `review` metainfo first
(`show <id>`): if it was already declared at authoring time
(`add --review user`/`--review subagent`), `[~]→[R]`/`[~]→[C]` is already
on-path and no `info-review` call is needed. Only call `info-review` when
the current value doesn't already cover the target — the dynamic-escalation
case, review need only became apparent while actually doing the work:
```
taskctl --root <root> info-review <id> user      # or: subagent
taskctl --root <root> set-status <id> R --message "<why review is needed>"   # or: C
```
`info-review` must run *before* the `set-status` call — it switches the
Task's effective forward path (the transition check reads `review` at the
moment of `set-status`, not a value fixed at creation), making the
escalating step normal, no `--force` needed.

*De-escalation — only on explicit user instruction for this Task:*
Preserve existing `user`/`subagent` review requirements by default. The
worker's judgment that review is unnecessary is insufficient. Never
remove the review gate for a remote-action Task. Record the user instruction
in `annotate` before changing the review requirement. Lowering a `user`
review is guarded, so the instruction goes in as approval (lowering
`subagent` → `none` is not guarded, but still needs the user instruction):

```
taskctl --root <root> info-review <id> none --user-approved "<user's instruction>"
taskctl --root <root> set-status <id> X --message "<user-authorized removal of review; evidence for completion>"
```

*User verdict on a Task in `[R]`* — only when the user explicitly accepts
the Task (a Task in `[R]` is what `next` returns as the blocker, so this
stays within the "only touch what `next` returned" invariant):
```
taskctl --root <root> set-status <id> X --user-approved "<user's instruction>" --message "<verdict>"
```

*Blocked* — can't proceed (a missing dependency, external input needed,
an error that isn't this Task's own to resolve):
```
taskctl --root <root> set-status <id> B --message "<reason>"
```
No `info-review` needed first — `[~]→[B]` is reachable regardless of the
current `review` value, provided `--message` is given.

*Remote-action markers* — the Agent decides approval from History
(`design-taskctl-worker.md`, "Exactly one path for a remote action"); this
Skill fixes the message prefixes so a later run can read how far an approved
action got. `<action>` is the same short action name in every entry:
```
taskctl --root <root> set-status <id> R --message "<action> pending: needs user approval"
taskctl --root <root> annotate <id> --message "<action> executing: approved"      # before the action
taskctl --root <root> annotate <id> --message "<action> done: <result>"           # or:
taskctl --root <root> annotate <id> --message "<action> failed: <error, partial state>"
taskctl --root <root> set-status <id> R --message "<action> done: <result>"       # or failed: ...
taskctl --root <root> set-status <id> R --message "<action> outcome unknown: verify remote state"
```
The `executing` annotation consumes the approval; if it fails, the action is
not performed. A failed result annotation is retried once, then the result
goes into the `[R]` message, then into the report — the action itself is
never re-run. On resume: `executing` after the latest approval without
`done`/`failed` → `outcome unknown` `[R]`; `done`/`failed` without the final
`[R]` → only that `[R]`.

**End-of-run verification** — after the loop ends (loop mode) or after the
one Task's final `set-status` (single-Task mode), re-read the actual
persisted state for every Task ID this run touched:
```
taskctl --root <root> --json show <id>
```
Don't rely on this run's own bookkeeping of what it believes it set — a
`set-status` call that silently failed must not be reported as if it
landed cleanly. Bucket each by what this returns: `status == "X"` → done;
`status == "R"`/`"C"` → escalated for review; `status == "B"` → blocked;
anything else (still `"~"`, or the `show` call itself failing) → not
successfully finalized.

## Status transitions, summarized

- Every Task is first moved `[ ]→[~]` ("starting") — `open`'s only forward
  step — before any outcome status is set; a direct jump from `open` to an
  outcome is off-path and fails without `--force`.
- Done: `[~]→[X]` directly, when the Task's `review` is (or was reset to)
  `none`.
- Needs review: `info-review <id> user|subagent` first if the current
  value doesn't already cover it, then `[~]→[R]`/`[~]→[C]` — on-path once
  `review` matches.
- De-escalation: `info-review <id> none` first (with `--user-approved` when
  lowering from `user`), then `[~]→[X]` — same mechanism, opposite direction.
- User verdict: `[R]→[X]` only with `--user-approved`.
- Blocked: `[~]→[B]` any time, provided `--message`.

## Error handling

- **A claim that didn't take**: if the `[ ]→[~]` `set-status` call itself
  fails, this Task was never actually claimed — do not proceed to
  `annotate`/an outcome for it, and do not move on to a different Task
  either (that would violate the "only touch what `next` returned"
  invariant). The Task's true state (still `open`) surfaces on its own the
  next time `next` is called.
- **`NoWorkAvailable`/`all_done`** is the normal "nothing left" signal, not
  a failure — see "Recipes".
- **A single Task's outcome failing to finalize** (an `annotate` or
  `set-status` call erroring after the claim succeeded): surface the
  stderr text for that Task in the report. In loop mode, this does not by
  itself justify calling `next` again to move on — the Task is still the
  one `next` will return, so the next iteration naturally revisits it
  rather than silently skipping it.
- **A failed write around an approved remote action**: see "Remote-action
  markers" — the only case with a retry (one, of the result annotation);
  the action itself is never repeated.
- **A guard rejection** (`sequence_blocked`/`approval_required`): stop the
  run and report it with the stderr text; never retry with `--user-approved`
  unless the user has explicitly instructed that operation.
- Any other non-zero exit from `show`/`info-review`: surface the stderr
  text for that Task; don't let it corrupt the report for Tasks already
  finalized successfully.

## Out of scope

- `add`, `add-phase`, `set-description`, `group-phase`, `reorder`,
  `delete` — creating/restructuring Tasks is `taskctl-author-cli`'s job.
- `info-assignee-type`, `info-assignee-name` — reassignment is an
  authoring action, never something this Skill's recipes touch.
- `list`, `show-metagroups` — no browsing/snapshot need; `next` already
  returns the exact Task to work.
- `reindex`, `history` — maintenance/reporting.
- Filtering `next` by `assignee-type`/`assignee-name` — those Metainfo
  fields stay purely informational for this workflow; `taskctl`'s
  Sequential Processing is one global queue, not per-assignee lanes
  (design-decisions.md, "Amendments (2026-08-25, ...)").
- Deciding *how* to actually perform a Task's described work, or *when*
  evidence is sufficient to call it done vs. blocked vs. needing review —
  the `taskctl-worker` Subagent's own judgment, not something this
  Skill prescribes (mirrors `rulectl-checker-cli`'s own "purely a
  CLI-contract reference" stance).

## Producer provenance

`next`/`show` return the optional `origin` Metainfo. The Agent routes
`rulectl:<rule-id>` exports to `rulectl-checker` instead of executing them.
`assignee-type=agent|tool` does not establish export provenance. The worker
never sets `origin`; missing markers on legacy exports are repaired by
re-export, outside this Skill. It may block the returned open/in-progress
export directly with the reason, without claiming or annotating it.
