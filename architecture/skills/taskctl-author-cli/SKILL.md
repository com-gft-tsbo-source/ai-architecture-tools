---
name: taskctl-author-cli
description: Wraps the taskctl CLI for the task-authoring workflow — creating Phase metagroups and Tasks, and browsing/correcting them while extending a task list. Use whenever a task list is being created or extended (add-phase, add, list, show, show-metagroups, set-description, group-phase, reorder, delete, info-review, info-assignee-type, info-assignee-name). Not for recording execution progress or changing a Task's status based on work done (annotate, next, set-status) — that is a separate, later workflow (taskctl-worker-cli).
---

Full spec: `architecture/docs/skills/design-taskctl-author-cli.md`.

You operate the `taskctl` CLI (on `PATH`, provided by the
`architecture-tools` plugin's `bin/`) via Bash for the
task-authoring workflow: creating and extending a Task list. This is a
reference, not a wrapper script — call `taskctl` yourself, following the
recipes below.

## Scope

Only these operations, because only these are needed to author Tasks:

- `add-phase` — create a Phase metagroup path (optional; a store is either
  Phase-using or phase-less, decided once by whatever comes first).
- `add` — create a Task, with inline `--phase`/`--description`/`--review`/
  `--assignee-type`/`--assignee-name`/`--source`, and optionally
  `--set-status`.
- `list` — browse existing Tasks before adding more, to avoid duplicating
  or overlapping already-covered work.
- `show`, `show-metagroups` — inspect one Task or the declared Phase tree;
  re-read a just-created Task to confirm it actually persisted.
- `set-description` — correct a just-created Task's Description.
- `info-review`, `info-assignee-type`, `info-assignee-name`,
  `info-source` — set or correct a Task's review requirement, assignment,
  and source traceability.
- `group-phase`, `reorder`, `delete` — restructure an existing Task.

Never call `annotate`, `next`, or standalone `set-status` from this
Skill — recording progress and changing Status based on actual work
belongs to `taskctl-worker-cli`. Also never `reindex`/`history` —
maintenance/reporting, out of scope here.

## Conventions

- **`--root <path>`**: use exactly the path you were given by whoever
  invoked you. Never hardcode or guess one. A not-yet-existing path is
  fine — `taskctl` creates the store on first use.
- **`--json`**: always pass it when you're going to parse the output
  (`list`, `show`, `show-metagroups`). Parse the JSON; never scrape the
  human-readable format.
- **Exit codes**: `0` = ok, `1` = error, error text on stderr.
- Each `taskctl` call is independent — there's no transaction. If a
  multi-step change fails partway, whatever was created before the failure
  stays created.

## Recipes

**Establish (or extend) the Phase structure**, if this store uses Phases:

```
taskctl --root <root> add-phase <name>
```

A segment may be a bare name (auto-numbered) or an explicit `<nr>-<name>`.
Skip this entirely for a flat, phase-less list.

**Create a Task**:

```
taskctl --root <root> add --name "<short name>" --description "<description text>" \
  [--phase <name>] \
  [--review none|user|subagent] \
  [--assignee-type <value>] [--assignee-name <value>] \
  [--source <value>] \
  [--set-status <code>]
```

`--phase` is required in a Phase-using store, omitted in a phase-less one —
never mix within the same store. `--source` traces the Task back to the
document it was derived from — set it whenever there is one. `--set-status`
is rare: it sets the Task's *initial* status (even one a normal transition
couldn't reach) — useful when importing a Task that's already done or
already in progress.

**Browse before extending**, to avoid duplicating or overlapping an
existing Task:

```
taskctl --root <root> --json list [--phase <path>] [--status <value>]
```

**Inspect one Task, or the Phase tree**:

```
taskctl --root <root> --json show <id> [--history]
taskctl --root <root> --json show-metagroups
```

**Correct a just-created Task's fields**:

```
taskctl --root <root> set-description <id> "<new description>"
taskctl --root <root> info-review <id> none|user|subagent
taskctl --root <root> info-assignee-type <id> <value>
taskctl --root <root> info-assignee-name <id> <value>
taskctl --root <root> info-source <id> <value>
```

**Restructure an existing Task**:

```
taskctl --root <root> group-phase <id> <phase-path>
taskctl --root <root> reorder <id> --after <sibling-number>
taskctl --root <root> delete <id>
```

## Error handling

- **Unknown Phase path**: create it first (`add-phase`), then retry. This
  is a missed prerequisite, not a reason to abort the whole run.
- **Object ID collision** on `add`: retry once — `taskctl` regenerates the
  ID from content each time.
- **Any other failure**: report the stderr text as-is for that one item,
  and move on to the next Task/Phase rather than stopping the run.

## Producer provenance

Ordinary authored Tasks leave `origin` unset, including Tasks assigned to
`agent` or `tool`. `origin=rulectl:<rule-id>` is reserved for `rulectl tasklist`
exports and routes those Tasks to `rulectl-checker`. Never fabricate this
marker while authoring or infer it from an assignment or source document.
