---
name: rulectl-checker-cli
description: Wraps rulectl's tasklist command and the taskctl commands needed to work a Rule-derived tasklist (annotate, info-review, set-status, show) for the checking workflow. Use whenever a rulectl-checker run refreshes a tasklist, picks up its work-set snapshot, and records compliant/violation/can't-check outcomes. Not for authoring Rules (that's rulectl-author-cli) and not for reading/searching the codebase being checked (that's the Subagent's own job).
---

Full spec: `architecture/docs/skills/design-rulectl-checker-cli.md`.

You operate `rulectl` (only `tasklist`) and `taskctl` via Bash for the
rule-checking workflow. This is a reference, not a wrapper script — call
the CLIs yourself, following the recipes below. `rulectl`/`taskctl` are
on `PATH`, provided by the `architecture-tools` plugin's `bin/`.

## Scope

**`rulectl`**: only `tasklist` — refreshing the tasklist *and* capturing
this run's work-set snapshot in the same call (see "Recipes").

**`taskctl`**: only these —
- `annotate <id> --message <text>` — record what was examined, for every
  task regardless of outcome.
- `info-review <id> user` — run immediately before escalating a task to
  `R`.
- `set-status <id> <code> --message <text>` — `~` (start checking),
  `X`/`R`/`B`.
- `show <id>` — re-read a task's actual persisted state, for every ID in
  the snapshot, at the end of a run.

Never call `taskctl list` in any form, `taskctl next`, any other `rulectl`
command, or any other `taskctl` command (`add`, `add-phase`,
`set-description`, `delete`, `reorder`, `group-phase`, ...) — none are
needed here. `next` re-returns tasks you've already moved to `R`/`B`
instead of advancing (`taskctl.py`, `_handle_next`: it selects the first
task whose status is anything other than `X`). `list` would pull in every
open task in the whole store, not just this run's scope — `tasklist`'s own
output is already the exact work set (see "Recipes"). Reading/searching
the codebase being checked is not this Skill's job either — use
Read/Glob/Grep/Bash directly for that.

## Conventions

- **`--root <path>`**: one shared path for *both* `rulectl tasklist` and
  every `taskctl` call — use exactly what you were given, never a
  different path for each tool. `rulectl tasklist` writes into the
  `taskctl` store sharing that same `--root`.
- **`--json`**: pass it only on calls whose output you actually parse —
  the `tasklist` refresh and the final `show`. Omit it on `set-status`/
  `annotate`/`info-review`: pure write calls, their outcome is the exit
  code, nothing in their output ever gets read (the recipes below already
  reflect this — don't add `--json` where they don't show it). **Where
  used, always before the subcommand**: `rulectl --root <root> --json
  tasklist`, `taskctl --root <root> --json show <id>`. It's declared on
  each CLI's top-level parser, not on the subcommand's own parser, so
  `rulectl tasklist --json` is a different (and invalid) command line —
  the `tasklist` subparser doesn't know `--json` and rejects it.
- **Exit codes**: `0` ok, `1` error.

## Recipes

**Refresh the tasklist and capture the work-set snapshot — one call, at
the start of a run:**

```
rulectl --root <root> --json tasklist [--language <path> | --context <path> | --category <path>]
```

At most one scope flag; omit to process the whole Rule store. Parse the
printed JSON array — one object per Task this refresh just created or
updated, each with an `id`. **These IDs are the fixed snapshot** this run
processes: iterate them directly. Never re-derive or widen this set with a
separate `taskctl list` call, and never call `next` mid-run. If this call
fails or its output doesn't parse as a JSON array, there is no snapshot —
stop before touching any task; don't treat it like a single task's
check failing (see "Error handling").

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

*Can't check* (tool not on the allow-list, insufficient evidence for an
`llm`-checked Rule, or an error running/interpreting a tool):
```
taskctl --root <root> annotate <id> --message "<what was attempted>"
taskctl --root <root> set-status <id> B --message "<reason>"
```
No `info-review` needed — `[~]→[B]` is reachable regardless of `review`,
as long as `--message` is given.

**Verify, then build the final report**, after processing the whole
snapshot — for every ID in the step-1 snapshot:
```
taskctl --root <root> --json show <id>
```
Re-reads the actual persisted state; don't rely on your own bookkeeping of
what you believe you set. Bucket by the result: `status == "X"` →
compliant, `status == "R"` → escalated-for-review, `status == "B"` →
blocked, anything else (still `"~"`, or the `show` call itself failing) →
not successfully finalized.

## Status transitions, summarized

- Tasks arrive from `rulectl tasklist` with `review` reset to `none` —
  even a Task re-exported after a previous escalation to `R` — so every
  task in a fresh snapshot starts on the same clean path: `[ ]→[~]→[X]`.
- Every task is moved `[ ]→[~]` first, before any outcome.
- Compliant: `[~]→[X]` directly. Violation: `info-review` then `[~]→[R]`,
  on-path. Can't check: `[~]→[B]` any time.

## Error handling

- A single task's check failing never stops the run — record it as
  "can't check" (`B`) and continue to the next task in the snapshot.
- Reaching the end of the snapshot ends the run normally.
- Any other non-zero exit *after* the snapshot was captured: surface the
  stderr text for that one task in the report; keep going. A failed or
  unparseable `tasklist` refresh itself is different — no task exists yet
  to "continue" from, so stop the run and report that failure directly,
  before any `set-status` call.
