# rulectl-checker-cli

Skill that wraps both `rulectl` (only its `tasklist` command) and `taskctl`
(the handful of commands needed to work a Rule-derived tasklist) for the
`rulectl-checker` Subagent (`architecture/docs/subagents/design-rulectl-checker.md`).
Purely an instructional reference — a `SKILL.md`, no executable wrapper
code. The invoking agent calls `rulectl`/`taskctl` itself via Bash; this
Skill only teaches it how to do that correctly for the checking workflow.
Named `rulectl-...` (like its sibling `rulectl-author-cli`) to keep the
family relationship visible, even though its command surface spans both
CLIs.

## Scope

**`rulectl`**: only `tasklist` — refreshing the Rule-derived tasklist
*and* capturing this run's work-set snapshot in the same call (see
"Recipes" below). No other `rulectl` command; authoring Rules is
`rulectl-author-cli`'s job.

**`taskctl`**:
- `annotate <id> --message <text>` — record what was actually examined,
  for every task regardless of outcome.
- `info-review <id> user` — switch a task's review mode immediately before
  escalating it to `R` (see "Status transitions" below).
- `set-status <id> <code> --message <text>` — `~` (start checking), `X`
  (compliant), `R` (after `info-review`, violation), `B` (can't check).
- `show <id>` — re-read a task's actual persisted state, at the end of a
  run, for every ID in the snapshot (see "Recipes").

Not in scope: any `rulectl` command besides `tasklist`, `taskctl next`
(see "Why not `next`" below), `taskctl list` in any form (superseded by
capturing the snapshot straight from `tasklist`'s own output — see below),
and any `taskctl` command besides the ones above (`add`, `add-phase`,
`set-description`, `delete`, `reorder`, `group-phase`, etc. — none of these
are needed to check a tasklist). Reading or searching the codebase being
checked is also out of scope for this Skill — that's the Subagent's own
job via Read/Glob/Grep/Bash, not a `rulectl`/`taskctl` operation.

### Why not `next`

`taskctl next` (`taskctl.py`, `_handle_next`) selects the first task whose
status is **anything other than `X`** — not the first task whose status is
specifically `open`. A task this workflow has already moved to `R` or `B`
still satisfies that condition, so looping `next` after processing such a
task returns the *same* task again instead of advancing — it never
reaches the tasks that are still genuinely untouched.

### Why not a separate `taskctl list`

`rulectl tasklist` already returns, in one call, exactly the Tasks it just
created or updated — the precise work set this run should process, scoped
by whatever `[--language|--context|--category <path>]` filter was given. A
follow-up `taskctl list --status " "` would instead return *every* open
task in the whole store, including ones this run's `tasklist` scope never
touched (leftover open tasks from unrelated `taskctl` activity, or ones
outside the rule-scope filter) — silently widening the run past what the
caller asked to check. Take the snapshot directly from `tasklist`'s own
output instead (see "Recipes"); never issue a separate `list` call to
(re-)derive it.

## Conventions

- **`--root <path>`**: one shared path for *both* `rulectl tasklist` and
  every `taskctl` call in a run — always given explicitly by the caller.
  `rulectl tasklist` writes into "the taskctl store sharing this
  invocation's `--root`" (design-rulectl.md), so a single `--root` value
  drives everything; never pass different roots to the two tools.
- **`--json`**: pass it on calls whose output you actually parse — the
  `tasklist` refresh (its returned IDs are the snapshot) and `show` (the
  final re-read). Omit it on `set-status`/`annotate`/`info-review`: those
  are pure write calls whose outcome is the exit code, nothing in their
  output is ever read, so `--json` would just be noise there — the
  Recipes below reflect this split; don't add `--json` to a recipe that
  doesn't already show it. **Where it is used, it is a global option, not
  a subcommand option** — both CLIs declare it on their top-level parser,
  before the subcommand is dispatched (`lib/cliapp.py`), so it must appear
  *before* the subcommand name: `rulectl --root <root> --json tasklist
  [scope]`, `taskctl --root <root> --json show <id>`. Placing it after the
  subcommand (`rulectl tasklist --json`) is a different, invalid command
  line — the subcommand's own parser doesn't declare `--json` and rejects
  it as an unrecognized argument.
- **Exit codes**: `0` = ok, `1` = error.

## Recipes

**Refresh the tasklist and capture the work-set snapshot — one call, at
the start of a run:**

```
rulectl --root <root> --json tasklist [--language <path> | --context <path> | --category <path>]
```

At most one scope flag; omit it to process the whole Rule store. Parse the
JSON array this prints — one object per Task the refresh just created or
updated, each with its `id`. **This array's IDs are the immutable snapshot**
for the rest of the run: iterate them directly; never re-derive or widen
this set with a separate `taskctl list` call, and never call `next` (see
"Why not `next`"/"Why not a separate `taskctl list`" above). If this call
fails (non-zero exit) or its output doesn't parse as a JSON array, there is
no snapshot — stop before touching any task (see the Subagent's own
"Workflow", which distinguishes this run-initialization failure from a
single task's check failing later).

**For each task in that snapshot, first mark it in progress** — every
task starts `open` (` `), and `open` has exactly one forward step, to
`in-progress` (`~`); jumping straight to `X`/`R`/`B` from `open` is
off-path and fails without `--force`:
```
taskctl --root <root> set-status <id> "~" --message "checking"
```

**Then, after determining the outcome:**

*Compliant:*
```
taskctl --root <root> annotate <id> --message "<scope examined>"
taskctl --root <root> set-status <id> X --message "compliant"
```

*Violation found:*
```
taskctl --root <root> annotate <id> --message "<scope examined>"
taskctl --root <root> info-review <id> user
taskctl --root <root> set-status <id> R --message "<violation detail>"
```
`info-review` must run *before* `set-status ... R` — it switches the
task's forward path so `[~]→[R]` becomes a normal step, no `--force`
needed. (Verified against `lib/taskctl_spec.py`'s `validate_transition`:
it reads the task's *current* `review` metainfo at the moment of the
transition, not a value fixed at creation.)

*Can't check* (tool not on the Subagent's allow-list, ambiguous/insufficient
evidence for an `llm`-checked Rule, or an error running or interpreting a
tool):
```
taskctl --root <root> annotate <id> --message "<what was attempted>"
taskctl --root <root> set-status <id> B --message "<reason>"
```
`B` needs no `info-review` step first — it's reachable from `[~]`
regardless of the task's current `review` value, as long as a `--message`
is given.

**Verify, then build the final report** (after the snapshot loop ends): for
every ID in the step-1 snapshot, re-read its actual persisted state —
don't trust this run's own bookkeeping of what it believes it set:
```
taskctl --root <root> --json show <id>
```
Bucket each snapshot ID by what this returns: `status == "X"` → compliant;
`status == "R"` → escalated-for-review; `status == "B"` → blocked; anything
else (still `"~"`, or the `show` call itself failing) → not successfully
finalized. This replaces querying `taskctl list --review user`/`list
--status B` after the fact — those would return the store's *entire*
current state for that filter, not just this run's snapshot, and would
still only reflect this run's own belief rather than a fresh read.

## Status transitions, summarized

- Tasks arrive from `rulectl tasklist` with `review` reset to `none` —
  including a re-exported Task that had been escalated to `R` on a
  previous run (design-rulectl.md, "Operations": "Review reset") — so
  every task in a fresh snapshot starts on the same clean forward path:
  `[ ]→[~]→[X]`.
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

## Error handling

- A single task's check failing (tool error, ambiguous judgment) never
  stops the loop — record it as "can't check" (`B`) and continue to the
  next task in the captured work-set.
- Reaching the end of the captured work-set ends the run normally.
- Any other non-zero exit from a `taskctl`/`rulectl` call *after* the
  snapshot was captured: surface the stderr text for that one task in the
  report; still don't stop the loop. A non-zero exit or unparseable output
  from the `tasklist` refresh itself (before any task exists to work) is
  categorically different — no task has been touched yet, so there is
  nothing to "continue" into; stop the run before any `set-status` call
  and report the refresh failure directly.

## Out of scope

- Any `rulectl` command besides `tasklist`.
- Any `taskctl` command not listed above — in particular, `list` in any
  form (see "Why not a separate `taskctl list`").
- Reading or writing the codebase being checked.
