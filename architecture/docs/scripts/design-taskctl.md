# taskctl

Objects are tasks.

## Store

Store name `tasks` (design.md, "File and Directory Parameters"): resolves to `<shared-dir>/tasks.md` or `<shared-dir>/tasks`. Default mode when neither exists yet: **directory** — a task list's Phase-level structure reads more naturally as nested directories than as one growing file.

## Metagroups

`Phase=<nr>-<name>` (single level; the 3-digit, zero-padded `<nr>` prefix is the metagroup's sort key, as for all tools — see design.md). Example: `002-Implementation`.

Like questctl (design-questctl.md, "Metagroups"), taskctl declares an **allowed depth range** rather than one fixed number — here, 0 or 1: a store either uses Phases for every Task, or uses no Phases at all (a flat task list). The depth is a whole-store property, not a per-Task one: it is not persisted as an explicit marker but inferred from what already exists, exactly as design.md, "Metagroups", describes generally. Unlike questctl's `add-group` (which by itself decides nothing — Group is not questctl's deepest level, Subgroup is), **`add-phase` locks depth 1 immediately, the moment the first Phase is created**, even before any Task exists: Phase is taskctl's *only* declared level, so it is simultaneously its shallowest and its deepest — creating one is exactly as unambiguous a signal as questctl's `add-subgroup` is for *its* deepest level, not the ambiguous-either-way signal `add-group` is for questctl. Failing that (no Phase created yet either), depth is fixed by the first successful `add` (with or without `--phase`). `add-phase` is rejected once a store is locked at depth 0 (there is nothing for a Phase to attach to); every `add` after the first must match the established depth. A depth-0 store's Task files sit directly in the store root (directory mode), which is then the only metagroup-path directory that ever exists, with its own `.index.md`/`.index.json` pair.

## Metainfo

- `origin`: optional producer reference, separate from document `source` and assignment. `rulectl tasklist` sets `rulectl:<rule-id>`; ordinary authored Tasks leave it unset. Exposed through `add --origin`, `info-origin`, `list --origin`, and JSON output like other Metainfo fields. This is provenance, not authentication.

- `review`: `none` | `user` | `subagent`
- `assignee-type`: free text
- `assignee-name`: free text
- `source`: free text — traceability back to the document a Task was derived
  from, same convention as rulectl's own `source` field (design-decisions.md,
  "Amendments (2026-08-25, taskctl-author/taskctl-worker Subagent design)").
  Left unset for a Task with no such origin (e.g. a hand-created Task, or one
  authored directly through `taskctl-author-cli` without a source document).

## Status

| Status | Meaning |
|---|---|
| `[ ]` | open |
| `[~]` | in progress |
| `[R]` | review by user |
| `[C]` | review by subagent |
| `[B]` | blocked |
| `[X]` | done |

Depending on the task's `review` value, the normal forward path is:
- `none`:     `[ ]` → `[~]` → `[X]`
- `user`:     `[ ]` → `[~]` → `[R]` → `[X]`
- `subagent`: `[ ]` → `[~]` → `[C]` → `[X]`

`[B]` is reachable from any non-terminal status, and from there back into any non-terminal status of the path (unblocking) — a reason **must** be supplied via `--message` when transitioning to `[B]`; it is recorded in the History. From `[R]` or `[C]`, a step back to `[~]` is allowed (rework). All other transitions require `--force`.

As described in design.md, `--set-status` at `add` time may set any initial status, including one unreachable as a transition (e.g. creating a task directly in `[~]`) — no `--force` needed for that case, since it is not a transition.

## Sequential Processing

Task processing is sequential: the tool assumes at most one Task is actively worked at a time, in priority order (see Prioritization). `[B]`, `[R]`, and `[C]` **block** this sequential progression — a Task in any of these statuses must be resolved (moved onward, or unblocked and then moved onward) before work proceeds to a later Task.

This is what `next` (see Operations) actually returns: not "the next `[ ]` Task," but **the earliest Task, in priority order, that is not `[X]`** — whatever its status. A Task already `[~]` is reported as the one currently active; a Task in `[B]`/`[R]`/`[C]` is reported as the one currently blocking further progress; only when the earliest non-`[X]` Task is `[ ]` does `next` hand back a genuinely new Task to start. `next` therefore never skips past an unresolved Task to reach a later `[ ]` one, however far down the list that later Task is.

(Contrast questctl, design-questctl.md, "Status": there, `[B]`/`[R]`/`[C]` on one Question never blocks work on any other Question — several Questions may be worked in parallel — precisely because questctl's processing model is not sequential in this sense.)

## Object Type

Exception to the general rule in design.md: **when Phases are in use** (depth 1, see Metagroups), the Object Type equals the Phase number, **not** padded to 6 characters — this exists purely to make tasks more easily identifiable, not as a true classification. **In a phase-less (depth 0) store**, there is no Phase number to derive from, so the general 0-level derivation applies instead (design.md, "Object Type"; design-questctl.md, "Object Type", for the same fallback in questctl): every Task derives to `______`.

## History

In addition to the general `M` (management) entries from design.md, taskctl uses `T` to log execution progress via `annotate`. `T` entries **always** show the `[<old>] -> [<new>]` transition, even when unchanged (e.g. `[~] -> [~]`) — unlike `M`, which shows a transition only when the status actually changed.

## Operations

In addition to the general operations from design.md, taskctl supports:

- `annotate`: append a History entry (`T`) documenting task execution progress.
- `next`: find and display the earliest Task, in priority order, that is not `[X]` (see Sequential Processing) — including its History. This may be the next new `[ ]` Task, or an already-`[~]`/`[B]`/`[R]`/`[C]` Task blocking further progress. If no such Task exists (every Task is `[X]`, or the store is empty), `next` raises `NoWorkAvailable` with reason `all_done` — exit 1, plain stderr text, or with `--json` a machine-readable `{"reason": "all_done", "message": ...}` (design-decisions.md, "Amendments (2026-08-25, taskctl `NoWorkAvailable` + taskctl-author-cli/taskctl-worker-cli design)"; the same mechanism questctl's `next`/`next-all` already use, design-questctl.md, "CLI Contract additions" — taskctl only ever has this one "nothing to hand out" case, never questctl's other two).

Phases and Tasks may also originate from `rulectl tasklist` (design-rulectl.md, "Operations") rather than being created directly through taskctl's own `add-phase`/`add` — such a Task's Object ID is shared with its source Rule, and `annotate`-style `T` History entries record every re-export. No taskctl-side behavior differs for these Tasks; this is purely informational.

## Prioritization

Tasks are ordered by sorted Phase, then by task number within that Phase — this order drives `next` and default listings.

## User Content

- `Description`

Each block may contain Markdown and is stored with a `> ` prefix per line.
