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

## Object Type

Exception to the general rule in design.md: the Object Type equals the Phase number, **not** padded to 6 characters. This exists purely to make tasks more easily identifiable, not as a true classification.

## History

In addition to the general `M` (management) entries from design.md, taskctl uses `T` to log execution progress via `annotate`. `T` entries **always** show the `[<old>] -> [<new>]` transition, even when unchanged (e.g. `[~] -> [~]`) — unlike `M`, which shows a transition only when the status actually changed.

## Operations

In addition to the general operations from design.md, taskctl supports:

- `annotate`: append a History entry (`T`) documenting task execution progress.
- `next`: find and display the next open task, including its History.

## Prioritization

Tasks are ordered by sorted Phase, then by task number within that Phase — this order drives `next` and default listings.

## User Content

- `Description`

Each block may contain Markdown and is stored with a `> ` prefix per line.
