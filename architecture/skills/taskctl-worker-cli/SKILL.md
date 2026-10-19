---
name: taskctl-worker-cli
description: Wraps the taskctl CLI for working a task list — picking the next Task via next, claiming it, and recording progress/outcome (annotate, set-status, info-review, show) as work actually happens. Use whenever a run works through taskctl Tasks: one Task per invocation by default, or looping until drained/blocked when explicitly instructed. Not for creating or restructuring Tasks (add, add-phase, set-description, group-phase, reorder, delete, info-assignee-type, info-assignee-name) — that is taskctl-author-cli's job — and not for deciding how to actually perform a Task's described work.
---

Full spec: `architecture/docs/skills/design-taskctl-worker-cli.md`.

You operate the `taskctl` CLI (on `PATH`, provided by the
`architecture-tools` plugin's `bin/`) via Bash to work a task
list: picking the next Task, doing its described work (outside this Skill
entirely — Read/Grep/Bash/whatever it calls for), and recording progress
and outcome. This is a reference, not a wrapper script — call `taskctl`
yourself, following the recipes below.

## Scope

Only these operations:

- `next` — find the Task to work.
- `set-status` — claim it (`[~]`) and set its outcome (`[X]`/`[R]`/`[C]`/
  `[B]`).
- `annotate` — log progress, on every Task regardless of outcome.
- `show` — read a Task's real state: resume context for an already-`[~]`
  Task, and end-of-run verification.
- `info-review` — **only** immediately before an escalating/de-escalating
  `set-status` call (see "Recipes"), never to reassign a Task.

Never call `add`, `add-phase`, `set-description`, `group-phase`,
`reorder`, `delete`, `info-assignee-type`, or `info-assignee-name` — those
are `taskctl-author-cli`'s job. Also never `list`/`show-metagroups` (no
browsing need — `next` already returns the exact Task) or
`reindex`/`history` (maintenance/reporting).

## Conventions

- **`--root <path>`**: use exactly what you were given, never a different
  path than the caller supplied.
- **`--json`**: pass it on `next`/`show`, whose output you parse. Omit it
  on `set-status`/`annotate`/`info-review` — pure write calls, only the
  exit code matters.
- **Exit codes**: `0` ok, `1` error.
- **Never use `--force`** — every transition below is already on a Task's
  normal forward path (or, for `[B]`, reachable from any non-terminal
  status with `--message`).

## Iteration model

Whoever invokes you decides which mode applies — it's not a `taskctl` flag:

- **Default: one Task per invocation.** Call `next` once, work that Task
  to its resting point (`[X]`, or an escalation `[R]`/`[C]`/`[B]`), stop.
- **Loop mode, only if explicitly instructed.** Repeat: call `next`; stop
  if it reports `NoWorkAvailable`/`all_done` (drained) or returns a Task
  already sitting in `[B]`/`[R]`/`[C]` (this run's blocker — `next` would
  just keep re-returning it); otherwise work it and loop.

**Invariant**: never call `set-status`/`annotate`/`info-review` on any
Task ID other than the one `next` most recently returned.

## Recipes

**Pick the Task to work:**

```
taskctl --root <root> --json next
```

Check the returned `status`:

- **`" "` (open)** — fresh Task. Claim it:
  ```
  taskctl --root <root> set-status <id> "~" --message "starting"
  ```
- **`"~"` (in progress)** — **resume**, not a fresh start. Don't
  re-claim; read History for context:
  ```
  taskctl --root <root> --json show <id> --history
  ```
- **`"B"`/`"R"`/`"C"`** — this run's blocker; nothing to do (single-Task
  mode) or stop the loop (loop mode).

If `next` itself fails: under `--json`, parse
`{"reason": "all_done", "message": "no open tasks"}` — drained, stop
cleanly. Any other failure is a genuine error, not "drained."

**Do the described work** — outside `taskctl` and this Skill entirely.

**Log what happened, regardless of outcome:**

```
taskctl --root <root> annotate <id> --message "<what was actually done>"
```

**Then set the outcome:**

*Done:*
```
taskctl --root <root> set-status <id> X --message "<summary>"
```

*Needs review* — only call `info-review` if the Task's current `review`
(check via `show <id>`) doesn't already cover the target:
```
taskctl --root <root> info-review <id> user      # or: subagent
taskctl --root <root> set-status <id> R --message "<why review is needed>"   # or: C
```
`info-review` must run *before* `set-status` — it changes the Task's
effective forward path, making the escalating step normal (no `--force`).

*De-escalation* (a pre-flagged Task turns out not to need review):
```
taskctl --root <root> info-review <id> none
taskctl --root <root> set-status <id> X --message "<why no review was needed after all>"
```

*Blocked:*
```
taskctl --root <root> set-status <id> B --message "<reason>"
```
No `info-review` needed first.

**End-of-run verification** — re-read every Task ID this run touched:
```
taskctl --root <root> --json show <id>
```
Don't trust your own bookkeeping — the store is the source of truth.

## Error handling

- **A claim (`[ ]→[~]`) that itself fails**: this Task was never actually
  claimed — do not proceed to `annotate`/an outcome for it, and do not
  move to a different Task (violates the invariant above). Its true state
  surfaces on the next `next` call.
- **`NoWorkAvailable`/`all_done`** is the normal "nothing left" signal,
  never a failure.
- **Any other non-zero exit** after a successful claim: surface the
  stderr text for that Task in the report; don't let it corrupt Tasks
  already finalized.

## Out of scope

- `add`/`add-phase`/`set-description`/`group-phase`/`reorder`/`delete` —
  `taskctl-author-cli`'s job.
- `info-assignee-type`/`info-assignee-name` — reassignment, never touched
  here.
- `list`/`show-metagroups`/`reindex`/`history`.
- Deciding *how* to perform a Task's described work, or when evidence is
  sufficient for done/blocked/needs-review — judgment for whoever invokes
  this Skill, not prescribed here.
