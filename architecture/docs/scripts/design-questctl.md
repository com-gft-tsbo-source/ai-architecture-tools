# questctl

Objects are Questions to be answered — open items requiring investigation, decision, or clarification, typically tracked during requirements or architecture work. questctl is almost identical to taskctl (design-taskctl.md); this document states only where it differs, and otherwise defers to design.md/design-taskctl.md.

## Store

Store name `questions` (design.md, "File and Directory Parameters"): resolves to `<shared-dir>/questions.md` or `<shared-dir>/questions`. Default mode when neither exists yet: **directory** — same reasoning as taskctl (design-taskctl.md, "Store"): the hierarchical structure reads more naturally as nested directories, and directory mode gives each Group/Subgroup its own independently lockable, independently listable location.

## Metagroups

- `Group=<nr>-<name>` (level 1)
- `Subgroup=<Group>/<nr>-<name>` (level 2, requires an existing Group)

As a *tree shape*, this is identical to adrctl's Domain/Component (design-adrctl.md, "Metagroups"): a regular, ≤2-level hierarchy. **The deviation from design.md's general model is not the tree shape but where an object may attach to it.** Every other tool's objects always sit at that tool's one fixed, deepest declared level (design.md, "Every object belongs to exactly one metagroup"). A Question, instead, may attach at **any** level of its ≤2-level tree: no Group at all (depth 0, "ungrouped"), a Group only (depth 1), or a Group/Subgroup (depth 2) — a per-object choice, not a tool-wide constant.

- `add-group <name> [--abbrev <code>]` and `add-subgroup <Group>/<name> [--abbrev <code>]` create metagroup-path nodes exactly as design.md describes: only the last segment is newly created, every ancestor segment must already exist.
- A Question is assigned via **either** `--group <path>` (depth 1) **or** `--subgroup <path>` (depth 2) — inline on `add`, or via `group-group <id> <path>` / `group-subgroup <id> <path>` afterwards — never both at once. Omitting both on `add` leaves the Question ungrouped (depth 0).
- `ungroup <id>` (new operation — no other tool needs an equivalent, since their objects can never be "un-metagrouped") moves an already-grouped Question back to depth 0. Logged as a plain `M` entry, the same way `group-<metagroup-type>` is.
- **Directory mode:** a Group is a subdirectory of the store root; a Subgroup is a subdirectory of its Group's directory — identical to adrctl. An **ungrouped** Question's file lives directly in the store root, which therefore doubles as the depth-0 metagroup-path directory: it gets its own `.index.md`/`.index.json` pair (see Index Files), alongside the Group subdirectories the same root also contains. The two kinds of entries never collide: Group directories are always named `<nr>-<name>`, Question files are always named `<nr>-<type>-<id>-<name>.md`.
- **Single-file mode:** an ungrouped Question simply carries no metagroup-type entry in its `## Meta` section — the empty case of the general rule that `## Meta` lists every ancestor level of the object's path.

## Object Type

The general derivation table (design.md, "Object Type") is extended with a 0-level row:

| Metagroup levels | Letters taken per level |
|---|---|
| 0 | (none) |
| 1 | 6 |
| 2 | 3 + 3 |

An ungrouped Question therefore always derives to `______` — 0 letters taken, then right-padded to 6 by the existing rule; no new mechanism, just that rule applied to the empty case. Since a real Group/Subgroup Name can never be empty, `______` can never collide with a derived code and needs no collision handling of its own.

## Metainfo

Same as taskctl (design-taskctl.md, "Metainfo"): `review` (`none` | `user` | `subagent`), `assignee-type`, `assignee-name`.

## Status

| Status | Meaning |
|---|---|
| `[ ]` | open, not yet worked |
| `[~]` | in progress |
| `[X]` | successfully answered |
| `[R]` | needs review by user |
| `[C]` | needs review by subagent |
| `[B]` | cannot be answered (blocked) |

The *per-object* state machine is unchanged from taskctl (design-taskctl.md, "Status"):
- `none`:     `[ ]` → `[~]` → `[X]`
- `user`:     `[ ]` → `[~]` → `[R]` → `[X]`
- `subagent`: `[ ]` → `[~]` → `[C]` → `[X]`

`[B]` is reachable from, and back into, any non-terminal status (a reason via `--message` is required going in). From `[R]`/`[C]`, a step back to `[~]` is allowed (rework). All other transitions require `--force`.

**Deviation from taskctl:** `[B]`, `[R]`, and `[C]` on one Question never block work on any *other* Question — this is the point of contrast against taskctl's now-explicit sequential-blocking rule (design-taskctl.md, "Sequential Processing"). Several Questions may be `[~]` at once — a whole Subgroup, a whole Group, or any combination of Groups/Subgroups — the tool imposes no restriction on which Questions may be concurrently active. Only `next-all`'s own precondition (see Operations) cares about `[~]` at all, and only tool-wide, not per-branch.

## History

In addition to `M`, questctl uses two prefixes (taskctl has only one, `T`):
- `T`: a plain progress-log entry, written by `annotate` — free-form notes on work in progress, exactly as taskctl's `T`.
- `A`: an answer entry, written by `answer`. Multiple `A` entries may exist (an answer may be revised); only the **last** `A` entry in a Question's History counts as *the* answer. There is no separate "answer" field kept in sync elsewhere — it is always derived by reading History backward for the most recent `A` entry.

Both `T` and `A` always show the `[<old>] -> [<new>]` transition, even when unchanged (e.g. `[~] -> [~]`) — same as taskctl's `T`.

## Operations

In addition to the general operations from design.md, questctl supports:

- `annotate`: append a `T` History entry documenting progress. Does not affect what counts as "the answer".
- `answer`: append an `A` History entry — this *is* how a Question's answer is recorded or revised. Identical in shape to `annotate` (same arguments, same `[<old>]->[<new>]` display), differing only in the History prefix it writes.
- `ungroup <id>`: clears a Question's Group/Subgroup assignment, moving it to depth 0 (see Metagroups). Logged as `M`.
- `next`: find and display the next `[ ]` Question in priority order (see Prioritization), including its History. Unlike taskctl's `next` (design-taskctl.md, "Sequential Processing"), it is never blocked by an earlier `[B]`/`[R]`/`[C]` Question — those are simply skipped, since (see Status above) they don't block other Questions' progress.
- `next-all`: lists **every** `[ ]` Question across the whole store, grouped by metagroup path (Group, then Subgroup, ungrouped Questions listed first) for readability — the same sort order used everywhere else (see Prioritization). Aborts with an error, listing nothing, if **any** Question anywhere in the store currently has status `[~]` — `next-all` is meant to kick off a fresh batch of parallel work from a clean slate, not to be mixed with work already underway.

## Prioritization

Questions are ordered by sorted Group, then sorted Subgroup (ungrouped Questions sort before any Group, as the "empty" depth-0 path), then Question number within that subpath — this order drives `next`, `next-all`'s grouping, and default listings.

## User Content

- `Description` — holds the question text itself (what is being asked).

Each block may contain Markdown and is stored with a `> ` prefix per line.

## CLI Contract additions

Beyond the shared `--<metagroup-type>` / `group-<metagroup-type>` / `add-<metagroup-type>` machinery (design.md, CLI Contract), questctl adds:

- `list [--group <path>] [--subgroup <path>] [--ungrouped] ...`: `--ungrouped` is new — a boolean filter for depth-0 Questions, needed because `--group`/`--subgroup` can only ever express "at or below a given path," never "at no path." At most one of `--group` / `--subgroup` / `--ungrouped` may be given per call (an object has exactly one placement).
- `--message "..."` on `answer`: same meaning and shape as on `annotate`/`set-status` — the History log text for the new `A` entry.
- `ungroup <id>`: object selector only, no positional value — mirrors `delete <id>`'s shape (design.md, CLI Contract), not `group-<metagroup-type> <id> <path>`'s, since there is no target path to give.
