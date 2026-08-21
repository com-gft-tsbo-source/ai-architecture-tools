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
before checking starts. No other `rulectl` command; authoring Rules is
`rulectl-author-cli`'s job.

**`taskctl`**:
- `list --status " "` — capture the set of currently-open tasks **once**,
  at the start of a run (see "Why not `next`" below).
- `annotate <id> --message <text>` — record what was actually examined,
  for every task regardless of outcome.
- `info-review <id> user` — switch a task's review mode immediately before
  escalating it to `R` (see "Status transitions" below).
- `set-status <id> <code> --message <text>` — `~` (start checking), `X`
  (compliant), `R` (after `info-review`, violation), `B` (can't check).
- `list --review user` / `list --status B` — for building the final
  report.

Not in scope: any `rulectl` command besides `tasklist`, `taskctl next`
(see "Why not `next`" below), and any `taskctl` command besides the ones
above (`add`, `add-phase`, `set-description`, `delete`, `reorder`,
`group-phase`, etc. — none of these are needed to check a tasklist).
Reading or searching the codebase being checked is also out of scope for
this Skill — that's the Subagent's own job via Read/Glob/Grep/Bash, not a
`rulectl`/`taskctl` operation.

### Why not `next`

`taskctl next` (`taskctl.py`, `_handle_next`) selects the first task whose
status is **anything other than `X`** — not the first task whose status is
specifically `open`. A task this workflow has already moved to `R` or `B`
still satisfies that condition, so looping `next` after processing such a
task returns the *same* task again instead of advancing — it never
reaches the tasks that are still genuinely untouched. Use a `list
--status " "` snapshot instead (see "Recipes"), which is unaffected by
status changes made while processing it.

## Conventions

- **`--root <path>`**: one shared path for *both* `rulectl tasklist` and
  every `taskctl` call in a run — always given explicitly by the caller.
  `rulectl tasklist` writes into "the taskctl store sharing this
  invocation's `--root`" (design-rulectl.md), so a single `--root` value
  drives everything; never pass different roots to the two tools.
- **`--json`**: always pass it when parsing `list` output.
- **Exit codes**: `0` = ok, `1` = error.

## Recipes

**Refresh the tasklist** (once, at the start of a run):

```
rulectl --root <root> tasklist [--language <path> | --context <path> | --category <path>]
```

At most one scope flag; omit it to process the whole Rule store.

**Capture the work set once, before processing anything:**

```
taskctl --root <root> --json list --status " "
```

This is the fixed list of tasks this run will process — iterate it
directly by ID; do not re-query it (and never call `next`) mid-run, since
statuses change as you go.

**For each task in that captured list, first mark it in progress** — every
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

*Can't check* (tool not on the Subagent's allow-list, or an error running
or interpreting it):
```
taskctl --root <root> annotate <id> --message "<what was attempted>"
taskctl --root <root> set-status <id> B --message "<reason>"
```
`B` needs no `info-review` step first — it's reachable from `[~]`
regardless of the task's current `review` value, as long as a `--message`
is given.

**Building the final report** (after the loop ends):

```
taskctl --root <root> --json list --review user
taskctl --root <root> --json list --status B
```

These list every task the store currently has in each state — filter the
results down to the task IDs captured in the initial work-set snapshot so
the report covers only what *this* run did, not the store's full history.

## Status transitions, summarized

- Tasks arrive from `rulectl tasklist` with `review` unset (defaults to
  `none`): normal forward path `[ ]→[~]→[X]`.
- Every task is first moved `[ ]→[~]` ("checking") — `open`'s only forward
  step — before any outcome is set.
- Compliant: stays on that path, `[~]→[X]` directly.
- Violation: `info-review <id> user` first, then `[~]→[R]` is on-path (no
  `--force`).
- Can't check: `[~]→[B]` any time, `review` value irrelevant.

## Error handling

- A single task's check failing (tool error, ambiguous judgment) never
  stops the loop — record it as "can't check" (`B`) and continue to the
  next task in the captured work-set.
- Reaching the end of the captured work-set ends the run normally.
- Any other non-zero exit from a `taskctl`/`rulectl` call: surface the
  stderr text for that one task in the report; still don't stop the loop.

## Out of scope

- Any `rulectl` command besides `tasklist`.
- Any `taskctl` command not listed above.
- Reading or writing the codebase being checked.
