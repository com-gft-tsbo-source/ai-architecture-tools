---
name: rulectl-checker-cli
description: Wraps rulectl's tasklist command and the taskctl commands needed to work a Rule-derived tasklist (list, annotate, info-review, set-status) for the checking workflow. Use whenever a rulectl-checker run refreshes a tasklist, picks up open tasks, and records compliant/violation/can't-check outcomes. Not for authoring Rules (that's rulectl-author-cli) and not for reading/searching the codebase being checked (that's the Subagent's own job).
---

Full spec: `architecture/docs/skills/design-rulectl-checker-cli.md`.

You operate `rulectl` (only `tasklist`) and `taskctl` via Bash for the
rule-checking workflow. This is a reference, not a wrapper script — call
the CLIs yourself, following the recipes below. `rulectl`/`taskctl` are
already on `PATH`, or run as `python3 <repo>/architecture/scripts/rulectl.py`
/ `taskctl.py`.

## Scope

**`rulectl`**: only `tasklist` — refreshing the tasklist before checking.
No other `rulectl` command belongs here.

**`taskctl`**: only these —
- `list --status " "` — capture the set of currently-open tasks **once**,
  at the start of a run. Never call `next` for this: `next` picks the
  first task whose status is anything other than `X` (`taskctl.py`,
  `_handle_next`), so once you've moved a task to `R` or `B` it still
  qualifies — looping `next` returns that same task forever instead of
  advancing to the genuinely untouched ones.
- `annotate <id> --message <text>` — record what was examined, for every
  task regardless of outcome.
- `info-review <id> user` — run immediately before escalating a task to
  `R`.
- `set-status <id> <code> --message <text>` — `~` (start checking),
  `X`/`R`/`B`.
- `list --review user` / `list --status B` — for the final report.

Never call any other `rulectl` command, `taskctl next`, or any other
`taskctl` command (`add`, `add-phase`, `set-description`, `delete`,
`reorder`, `group-phase`, ...) — none are needed here. Reading/searching
the codebase being checked is not this Skill's job either — use
Read/Glob/Grep/Bash directly for that.

## Conventions

- **`--root <path>`**: one shared path for *both* `rulectl tasklist` and
  every `taskctl` call — use exactly what you were given, never a
  different path for each tool. `rulectl tasklist` writes into the
  `taskctl` store sharing that same `--root`.
- **`--json`**: always pass it when parsing `list` output.
- **Exit codes**: `0` ok, `1` error.

## Recipes

**Refresh the tasklist** (once, at the start of a run):

```
rulectl --root <root> tasklist [--language <path> | --context <path> | --category <path>]
```

At most one scope flag; omit to process the whole Rule store.

**Capture the work set once, before processing anything:**

```
taskctl --root <root> --json list --status " "
```

This is the fixed list this run processes — iterate it directly by ID.
Do not re-query it mid-run; statuses change as you go, and re-querying (or
using `next`) would pick up your own already-processed tasks again.

**Per task, first mark it in progress** — every task starts `open` (` `),
whose only forward step is `in-progress` (`~`); jumping straight to
`X`/`R`/`B` from `open` is off-path and fails without `--force`:
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
`info-review` must run before `set-status ... R` — it makes `[~]→[R]` a
normal forward step (no `--force`), since the transition check reads the
task's *current* `review` value, not one fixed at creation.

*Can't check* (tool not on the allow-list, or an error running/interpreting
it):
```
taskctl --root <root> annotate <id> --message "<what was attempted>"
taskctl --root <root> set-status <id> B --message "<reason>"
```
No `info-review` needed — `[~]→[B]` is reachable regardless of `review`,
as long as `--message` is given.

**Final report**, after processing the whole captured list:
```
taskctl --root <root> --json list --review user
taskctl --root <root> --json list --status B
```
Filter to the task IDs in your initial snapshot — these `list` calls
return the store's *entire* current state, not just this run.

## Status transitions, summarized

- Tasks arrive with `review` unset: normal path `[ ]→[~]→[X]`.
- Every task is moved `[ ]→[~]` first, before any outcome.
- Compliant: `[~]→[X]` directly. Violation: `info-review` then `[~]→[R]`,
  on-path. Can't check: `[~]→[B]` any time.

## Error handling

- A single task's check failing never stops the run — record it as
  "can't check" (`B`) and continue to the next task in the snapshot.
- Reaching the end of the snapshot ends the run normally.
- Any other non-zero exit: surface the stderr text for that one task in
  the report; keep going.
