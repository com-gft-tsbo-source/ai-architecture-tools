# questctl

Objects are Questions to be answered — open items requiring investigation, decision, or clarification, typically tracked during requirements or architecture work. questctl is almost identical to taskctl (design-taskctl.md); this document states only where it differs, and otherwise defers to design.md/design-taskctl.md.

## Store

Store name `questions` (design.md, "File and Directory Parameters"): resolves to `<shared-dir>/questions.md` or `<shared-dir>/questions`. Default mode when neither exists yet: **directory** — same reasoning as taskctl (design-taskctl.md, "Store"): the hierarchical structure reads more naturally as nested directories, and directory mode gives each Group/Subgroup its own independently lockable, independently listable location.

## Metagroups

- `Group=<nr>-<name>` (level 1)
- `Subgroup=<Group>/<nr>-<name>` (level 2, requires an existing Group)

As a *tree shape*, this is identical to adrctl's Domain/Component (design-adrctl.md, "Metagroups"): a regular, ≤2-level hierarchy. What's different is that questctl declares an **allowed depth range, 0–2**, rather than one fixed number — and, per design.md ("Metagroups"), the depth actually used is chosen once, **for the whole store**, not per object: every Question in a given store sits at the same depth — none at all (0, "ungrouped"), a Group only (1), or a Group/Subgroup (2). A store with any Question under a Subgroup has *every* Question under some (potentially different) Subgroup; there is no mixing of depths within one store, and consequently no per-object "move to a different depth" operation (`ungroup` or similar) — depth is a whole-store property, not a per-object one, so there is nothing for an object-level operation to act on.

- The depth is not persisted as an explicit marker; it is inferred from whatever already exists, the same way `resolve_root` already infers directory-vs-single-file mode from what's on disk (design.md, "File and Directory Parameters"). It is fixed by the first event that reveals it: the first successful `add` (whichever of `--group`/`--subgroup` it did or didn't use), or a preceding `add-subgroup` call, which unambiguously implies depth 2 before any Question need exist. A bare `add-group` call decides nothing by itself — it's valid scaffolding for either a depth-1 or a depth-2 store.
- Once the depth is established, every subsequent `add` must use exactly that depth. `add-group`/`add-subgroup` remain available only where they could still matter: both stay available in a depth-2 store (more Groups need Subgroups before anything can attach); only `add-group` stays available in a depth-1 store (`add-subgroup` is rejected — nothing could ever attach at depth 2 anymore); neither is available in a depth-0 store (there is no grouping axis to build at all). A call that would violate the established depth is rejected with an error.
- **Directory mode:** a depth-1 or depth-2 store mirrors Group/Subgroup as nested subdirectories exactly like adrctl. A depth-0 store has no subdirectories at all — every Question file sits directly in the store root, which is then the *only* metagroup-path directory that ever exists, with its own single `.index.md`/`.index.json` pair (see design.md, "Index Files").
- **Single-file mode:** a depth-0 store's `## Metagroups` bookkeeping section is simply absent/empty, and no object ever carries a metagroup-type entry in its `## Meta` section.

## Object Type

The general derivation table (design.md, "Object Type") is extended with a 0-level row:

| Metagroup levels | Letters taken per level |
|---|---|
| 0 | (none) |
| 1 | 6 |
| 2 | 3 + 3 |

Since depth is fixed per store (see Metagroups), a depth-0 store has every Question derive to the same code, `______` — 0 letters taken, then right-padded to 6 by the existing rule; not a per-object special case, just the table's 0-row applied uniformly because that is the only depth this store ever uses. It can never collide with anything, since a depth-0 store has no Group/Subgroup names to collide with in the first place.

## Metainfo

Same as taskctl (design-taskctl.md, "Metainfo") plus one addition: `review` (`none` | `user` | `subagent`), `assignee-type`, `assignee-name`, and:

- `source`: free text, pointing back to the document/passage a Question was drawn from — same convention as `rulectl`'s `source` Metainfo (design-rulectl.md, "Metainfo"): a file's resolved path plus a heading/line range, a URL plus an anchor, or (for pasted text) the `pasted invocation text` convention plus a content hash. Not part of taskctl's own Metainfo set — taskctl's Tasks are usually authored directly by whoever is using them, so there is nothing upstream to trace back to; questctl's Questions, by contrast, are routinely authored in bulk from a source document by `questctl-author` (`design-questctl-author.md`), where losing that trace would leave a Question with no way back to the requirement it came from. Left unset for a Question created any other way (e.g. a user typing `add` by hand).

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

**Deviation from taskctl:** `[B]`, `[R]`, and `[C]` on one Question never block *other* Questions from being *finished*. This is not the same thing as when *new* work may start — see Parallel Processing, below, for that.

## Parallel Processing

questctl is not sequential the way taskctl is (design-taskctl.md, "Sequential Processing") — several Questions may be worked at once, spanning a Subgroup, a whole Group, or any combination. But "several at once" is a deliberate act, not something `next`/`next-all` build up incrementally on their own:

- **While any Question anywhere in the store is `[~]`, neither `next` nor `next-all` will hand out a new `[ ]` Question.** The gate is global — it does not matter which Group/Subgroup the in-progress Question belongs to. This is what makes "several in parallel" a real, bounded batch rather than an ever-growing one: once *anything* is in flight, no one (agent or user) is offered more until that batch clears.
- To start several Questions together, an agent marks each of them `[~]` itself — repeated `set-status <id> ~` calls, no separate batch-start operation — *before* beginning to answer any of them. The first such call closes the gate for everyone else's `next`/`next-all` from that point on; the agent already knows which Questions it committed to and proceeds independently of the gate for its own batch.
- Once the gate is closed by one Question, it stays closed until **no** Question is `[~]` anywhere — not until the whole original batch reaches `[X]`. `[R]`/`[C]`/`[B]` don't hold the gate closed (per Status, above): moving a Question out of `[~]` into `[R]`/`[C]`/`[B]` releases the gate exactly as reaching `[X]` would, even while that Question itself sits unresolved.

When `next`/`next-all` cannot hand out anything, they report *why*, distinguishing three cases (see CLI Contract additions for their exact signal):

1. **`in_progress`** — the gate above is closed: at least one Question is `[~]`. Meaning: work is already underway, don't start more.
2. **`all_answered`** — no Question is `[~]`, and every Question is `[X]` (an empty store, with no Questions at all, is reported the same way — vacuously nothing left). Meaning: nothing left to do.
3. **`awaiting_interaction`** — no Question is `[~]`, not every Question is `[X]`, but none is `[ ]` either (the remainder is `[X]`/`[R]`/`[C]`/`[B]`, with at least one `[R]`/`[C]`/`[B]`). Meaning: nothing an agent can pick up on its own right now — a review or a blocker needs to be resolved by a user or another agent first, after which `next`/`next-all` may have something again.

Only when none of the three applies does `next` return a Question (the earliest `[ ]`, per Prioritization) or `next-all` return a list (every `[ ]`, grouped).

## History

In addition to `M`, questctl uses `T` for two purposes (taskctl has only one, plain progress notes):
- Written by `annotate`: a free-form progress-log entry, exactly as taskctl's `T`.
- Written by `answer`: records that the Answer section changed. The entry carries only a short log message (see CLI Contract additions) — the answer text itself lives solely in the Answer section (see User Content), never duplicated into History. Each `answer` call **replaces** the Answer section outright; the `T` entry is the only remaining trace that a change happened, and why.

`T` entries always show the `[<old>] -> [<new>]` transition, even when unchanged (e.g. `[~] -> [~]`) — same as taskctl. Neither `annotate` nor `answer` can themselves change status (`Store.annotate`'s implementation always sets `new_status = old_status`) — moving a Question to `[~]`/`[X]`/etc. is always a separate `set-status` call.

## Operations

In addition to the general operations from design.md, questctl supports:

- `annotate`: append a `T` History entry documenting progress. Does not touch the Answer section.
- `answer`: replace the Answer section's content and append a `T` History entry recording that it changed (see User Content, History). This is the *only* way to write the Answer section — there is deliberately no generic `set-answer`, so there is exactly one write path with exactly one logging behavior. (design.md's generic `set-<user-content-block>` always logs a fixed `M` entry — "`<block> changed`" — which would give the same field two different, inconsistent logging behaviors if both `answer` and `set-answer` existed side by side.)
- `next [--group <path> | --subgroup <path>]`: find and display the next `[ ]` Question in priority order (see Prioritization and Parallel Processing above), including its History — or report one of the three "nothing available" reasons. The optional scope filter (mirroring `list`'s existing shape, design.md CLI Contract) restricts consideration to that metagroup path and its descendants; the `[~]`-in-progress gate (see Parallel Processing) is checked **unscoped, store-wide** either way — a `[~]` Question outside the given scope still blocks, since it is still true that "an agent is already working" regardless of where.
- `next-all [--group <path> | --subgroup <path>]`: list every `[ ]` Question at or below the given metagroup path (the whole store if omitted), grouped by metagroup path (Group, then Subgroup) for readability — mirroring the sort order used everywhere else (Prioritization) — or report one of the three "nothing available" reasons, under the same unscoped `[~]`-gate rule as `next` above.

## Prioritization

Questions are ordered by sorted Group, then sorted Subgroup, then Question number within that subpath — this order drives `next`, `next-all`'s grouping, and default listings. (In a depth-0 store there is only the one, empty subpath.)

## User Content

- `Description` — the question text itself (what is being asked).
- `Answer` — the current answer, written only via `answer` (see Operations); there is no `set-answer`. Handled exactly like `Description`: full Markdown, stored with a `> ` prefix per line, rendered as a `### Answer` tool-specific section (design.md, "Object Format"). Starts absent and is created by the first `answer` call.

## CLI Contract additions

Beyond the shared `--<metagroup-type>` / `group-<metagroup-type>` / `add-<metagroup-type>` machinery (design.md, CLI Contract):

- `answer <id> <text> --message "..."`: `<text>` (Markdown, like `--description`) replaces the Answer section; `--message` is **required** (mirrors `annotate`'s existing `--message`, `required=True`) and becomes the `T` entry's log text — the only remaining trace of *why* the answer changed, since the previous text is gone once overwritten.
- `next [--group <path> | --subgroup <path>]` / `next-all [--group <path> | --subgroup <path>]`: the optional scope filter restricts which `[ ]` Questions are considered, same flag shape and at-most-one-of rule as `list`'s own metagroup filter — added specifically so `questctl-checker`/`questctl-researcher` (design-questctl-checker.md/design-questctl-researcher.md) can be pointed at one Group/Subgroup subtree of an accumulating store without touching unrelated, currently-open work elsewhere. Both commands' `[~]`-in-progress gate (Parallel Processing) stays unscoped regardless — a Question `[~]` outside the given filter still blocks, since the gate's whole point ("an agent is already working somewhere") doesn't depend on where.
- `next`/`next-all` failure reporting: exit 1 in all three "nothing available" cases (see Parallel Processing), distinguished by the stderr message text and, with `--json`, a machine-readable `"reason"` field (`in_progress` | `all_answered` | `awaiting_interaction`) — consistent with `next-all`'s and taskctl's existing `next`'s precedent of treating "nothing to hand out" as an error condition (exit 1), not an empty success.
- `list [--group <path>] [--subgroup <path>] ...`: since depth is a whole-store property (see Metagroups), there is no per-object "ungrouped" state to filter for within a mixed store — a `list --ungrouped` filter is meaningless once depth can no longer vary within one store, so none is offered.
