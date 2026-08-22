# taskctl

Objects are tasks.

## Store

Store name `tasks` (design.md, "File and Directory Parameters"): resolves to `<shared-dir>/tasks.md` or `<shared-dir>/tasks`. Default mode when neither exists yet: **directory** — a task list's Phase-level structure reads more naturally as nested directories than as one growing file.

## Metagroups

`Phase=<nr>-<name>` (single level; the 3-digit, zero-padded `<nr>` prefix is the metagroup's sort key, as for all tools — see design.md). Example: `002-Implementation`.

## Metainfo

- `review`: `none` | `user` | `subagent`
- `assignee-type`: free text
- `assignee-name`: free text

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

Exception to the general rule in design.md: the Object Type equals the Phase number, **not** padded to 6 characters. This exists purely to make tasks more easily identifiable, not as a true classification.

## History

In addition to the general `M` (management) entries from design.md, taskctl uses `T` to log execution progress via `annotate`. `T` entries **always** show the `[<old>] -> [<new>]` transition, even when unchanged (e.g. `[~] -> [~]`) — unlike `M`, which shows a transition only when the status actually changed.

## Operations

In addition to the general operations from design.md, taskctl supports:

- `annotate`: append a History entry (`T`) documenting task execution progress.
- `next`: find and display the earliest Task, in priority order, that is not `[X]` (see Sequential Processing) — including its History. This may be the next new `[ ]` Task, or an already-`[~]`/`[B]`/`[R]`/`[C]` Task blocking further progress.

Phases and Tasks may also originate from `rulectl tasklist` (design-rulectl.md, "Operations") rather than being created directly through taskctl's own `add-phase`/`add` — such a Task's Object ID is shared with its source Rule, and `annotate`-style `T` History entries record every re-export. No taskctl-side behavior differs for these Tasks; this is purely informational.

## Prioritization

Tasks are ordered by sorted Phase, then by task number within that Phase — this order drives `next` and default listings.

## User Content

- `Description`

Each block may contain Markdown and is stored with a `> ` prefix per line.
