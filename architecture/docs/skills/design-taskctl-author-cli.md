# taskctl-author-cli

Skill that wraps the `taskctl` CLI for the `taskctl-author` Subagent
(`architecture/docs/subagents/design-taskctl-author.md`). Purely an
instructional reference — a `SKILL.md`, no executable wrapper code. The invoking agent
calls the `taskctl` binary itself via Bash; this Skill only teaches it how
to do that correctly for the task-authoring workflow: creating and
extending a Task list. Companion to `taskctl-worker-cli`, which works the
Tasks this Skill creates and changes their Status accordingly — the two
Skills' command surfaces are disjoint by design (see "Out of scope"), and
their future Subagents never call each other's `taskctl` commands.

## Scope

Covers only the `taskctl` operations the authoring workflow needs —
creating and restructuring Tasks, never working them:

- `add-phase` — create a Phase metagroup path.
- `add` (with inline `--phase`, `--description`, `--review`,
  `--assignee-type`, `--assignee-name`, `--source`, and optionally
  `--set-status`) — create a Task.
- `list` — browse existing Tasks (by `--phase`/`--status`/metainfo) before
  adding more, e.g. to avoid duplicating or overlapping an already-covered
  piece of work.
- `show`, `show-metagroups` — inspect one Task or the declared Phase tree,
  and re-read a just-created Task to confirm it actually persisted.
- `set-description` — correct a just-created Task's Description.
- `info-review`, `info-assignee-type`, `info-assignee-name`,
  `info-source` — set or correct a Task's review requirement, assignment,
  and traceability back to its source document. (`info-review` is also
  usable by `taskctl-worker-cli`, for a different purpose — see that
  Skill's own scope.)
- `group-phase` — move a Task to a different Phase.
- `reorder` — reposition a Task among its Phase siblings.
- `delete` — remove a Task.

Not in scope (belongs to a different workflow, so not documented here):
`annotate`, `next`, standalone `set-status` — these are how a Task's
progress and outcome are recorded once work on it actually starts, which
is `taskctl-worker-cli`'s job, never this Skill's. Also not in scope:
`reindex`, `history` — maintenance/reporting operations that belong to
neither authoring nor working a Task list.

## Invocation conventions

- **`--root <path>`**: always supplied by the caller (the `taskctl-author`
  Subagent receives it from whoever invoked it — user or orchestrating
  Skill). Never hardcode or guess a root; `taskctl` auto-creates the store
  on first use if it doesn't exist yet.
- **`--json`**: always pass this flag when the output needs to be parsed
  programmatically (`list`, `show`, `show-metagroups`) — do not scrape the
  human-readable format.
- **Exit codes**: `0` = ok, `1` = error. Error text goes to stderr.
- Every operation is a single, independent `taskctl` invocation — there is
  no batch/transaction mode. A multi-step change (e.g. "create a Phase,
  then add several Tasks under it") is several sequential CLI calls; if one
  fails partway, whatever was already created before the failure remains.

## Operation recipes

**Establishing (or extending) the Phase structure** — optional; a store is
either Phase-using (depth 1) or phase-less (depth 0), decided once by
whatever comes first (design-taskctl.md, "Metagroups"):

```
taskctl --root <root> add-phase <name>
```

A segment may be given as a bare name (an auto-assigned `<nr>-` prefix is
added) or as an explicit `<nr>-<name>`. Skip this entirely for a flat,
phase-less Task list — the first successful `add` without `--phase` then
locks the store at depth 0 instead.

**Creating a Task**:

```
taskctl --root <root> add --name "<short name>" --description "<description text>" \
  [--phase <name>] \
  [--review none|user|subagent] \
  [--assignee-type <value>] [--assignee-name <value>] \
  [--source <value>] \
  [--set-status <code>]
```

`--phase` is required in a Phase-using store, omitted entirely in a
phase-less one — never both within the same store (design-taskctl.md,
"Metagroups": depth is a whole-store property). Omitting `--review`
leaves it unset, which `taskctl`'s status machine treats the same as
`none` (design-taskctl.md, "Status"). `--source` traces the Task back to
the document (and section/passage, where identifiable) it was derived
from — set it whenever the Task actually came from a source document;
leave it unset for a Task with no such origin. `--set-status` is rarely
needed — it sets the Task's *initial* Status to any value, even one a
normal transition couldn't reach (e.g. importing a Task that's already
done or already in progress); this is an initial-value choice, not a
transition, so it never needs `--force` (design.md, "Object Status").

**Browsing before extending**, to see what already exists — e.g. to avoid
adding a Task that duplicates or overlaps one already on the list:

```
taskctl --root <root> --json list [--phase <path>] [--status <value>]
```

**Inspecting one Task, or the declared Phase tree**:

```
taskctl --root <root> --json show <id> [--history]
taskctl --root <root> --json show-metagroups
```

`show <id>` right after `add` is how you confirm a just-created Task
actually persisted — a run's own belief about what it created is not
itself evidence.

**Correcting a just-created Task's fields**:

```
taskctl --root <root> set-description <id> "<new description>"
taskctl --root <root> info-review <id> none|user|subagent
taskctl --root <root> info-assignee-type <id> <value>
taskctl --root <root> info-assignee-name <id> <value>
taskctl --root <root> info-source <id> <value>
```

**Restructuring an existing Task**:

```
taskctl --root <root> group-phase <id> <phase-path>
taskctl --root <root> reorder <id> --after <sibling-number>
taskctl --root <root> delete <id>
```

`group-phase` rejects reassigning a Task to its current Phase (no-op — use
`reorder` instead). `reorder --after 0` inserts before all siblings.

## Error handling

- **Unknown Phase path** (`add --phase <path>` naming a path not yet
  created): create it first (`add-phase`), then retry the original
  operation. Never treat this as a fatal error for the overall run — it
  means a prerequisite step was skipped, not that the operation itself is
  invalid.
- **Object ID collision** on `add`: astronomically unlikely with generated
  IDs; if it happens anyway, retry once — `taskctl` regenerates the ID from
  content on each attempt.
- Any other non-zero exit: surface the stderr text as-is in the Subagent's
  final report for that one Task/Phase; do not retry blindly, and do not
  let one failed item abort the whole run — continue with the remaining
  Tasks to create or extend.

## Out of scope

- Recording execution progress or changing a Task's Status based on work
  actually done (`annotate`, `next`, standalone `set-status`) —
  `taskctl-worker-cli`'s job entirely.
- `reindex`, `history` — maintenance/reporting, neither authoring nor
  working a Task list.
- Judging whether a candidate Task duplicates or overlaps an existing one,
  how to break a larger goal into Tasks, or how to structure a Phase
  breakdown — workflow judgment for the future `taskctl-author` Subagent,
  not something this Skill prescribes (mirrors `rulectl-author-cli`'s own
  "purely a CLI-contract reference" stance).
- Working the Task list itself (deciding what "done" means for a given
  Task's described work) — `taskctl-worker-cli`'s job.
