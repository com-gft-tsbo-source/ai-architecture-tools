---
name: specctl-author-cli
description: Wraps the specctl CLI for the draft-authoring workflow — full CRUD over a document's still-draft content, including self-initializing the store. Use whenever specctl draft content is being created, edited, restructured, or deleted (init, add-<level>, set-description/set-open-questions, rename, reorder, move-to-<level>, delete, list, show). Not for any Status change or ADR linkage (set-status, set-adr) — that's specctl-editor-cli's job for stable-phase work.
---

Full spec: `architecture/docs/skills/design-specctl-author-cli.md`.

You operate the `specctl` CLI (on `PATH`, provided by the
`architecture-tools` plugin's `bin/`) via Bash for the
draft-authoring workflow. This is a reference, not a wrapper script — call
`specctl` yourself, following the recipes below.

## Scope

- `init` (with `--preamble`), `set-title`, `set-preamble` — document-level
  setup, including the mandatory one-time initialization.
- `add-part`, `add-chapter`, `add-section`, `add-subsection`, `add-point`
  (with inline `--description`, `--open-questions`, `--set-status`,
  `--abbrev`, `--id`) — create a Section at any of the 5 heading depths.
- `set-description`, `set-open-questions` — change a Section's content.
  Always with **no** `--adr` — every Section you touch here is still
  `draft` by construction.
- `rename`, `reorder` — restructure without moving across parents.
- `move-to-part`, `move-to-chapter`, `move-to-section`, `move-to-subsection`,
  `move-to-point` — reassign a Section (and its whole subtree) to a
  different parent — see "move-to-\<level\>'s real semantics" below, it's
  not just "reparent."
- `delete` (with `--force-delete` for a subtree).
- `show`, `list` (`--status`/`--under`) — inspect existing content, and
  re-read a just-created/-deleted Section to confirm the write took effect.

Never call `set-status` or `set-adr` from this Skill — any Status change or
ADR linkage is `specctl-editor-cli`'s job for stable-phase work. Also never
call `render`/`history` — read-only convenience views this workflow doesn't
need. **`specctl` has no `show-metagroups`** — unlike `taskctl`/`rulectl`/
`adrctl`'s shared generic engine, `specctl.py` is its own hand-rolled CLI
and a Section already carries its own position/type directly; use `list`
instead when you need to see the declared structure.

## Detecting initialization

There's no dedicated query command, and reading doesn't help either —
`list`/`render`/`history` are explicitly exempt from the initialization
check and just return empty output on an uninitialized store, indistinguishable
from "initialized, zero Sections yet." The only reliable signal is a
**mutating** call's error text: attempt the first real operation the prompt
needs (e.g. `add-part`); if it fails with

```
this specctl document has not been initialized yet -- run 'init <title>' first
```

(exit 1), run `init` and retry. Any other error means something else is
wrong — don't call `init` reflexively on every failure. `init` itself is
idempotent-**rejecting** (fails on an already-initialized store rather than
overwriting it) — never call it speculatively without confirming via the
error above first.

## Conventions

- **`--root <path>`**: use exactly what you were given. Never hardcode or
  guess it.
- **`--json`**: pass it whenever you're going to parse the output (`show`,
  `list`).
- **`<id>`** is the 6-character `id` field from `--json list`/`show` (e.g.
  `e306b7`). Every command that changes a Section accepts only that
  `id`, not the Signature the human-readable output prints (`show`
  also takes the Signature).
- **Exit codes**: `0` = ok, `1` = error, error text on stderr; `2` = a
  malformed command line (unknown subcommand or option).
- Each call is independent — no transaction. A multi-step change is
  several sequential calls; if one fails partway, whatever was already
  created stays created.

## Recipes

**Initialize**:

```
specctl --root <root> init "<Title>" [--preamble "<preamble text>"]
```

**Create a metagroup path and Section content in one step** — the path is
the full `/`-separated sequence of heading texts, ancestors then the new
leaf; every ancestor segment must already exist:

```
specctl --root <root> add-part "<Part name>" [--description "<text>"] [--open-questions "<text>"]
specctl --root <root> add-chapter "<Part name>/<Chapter name>" [--description "<text>"] ...
specctl --root <root> add-section "<Part>/<Chapter>/<Section name>" ...
specctl --root <root> add-subsection "<...>/<Subsection name>" ...
specctl --root <root> add-point "<.../Point name>" ...
```

A Section may skip intermediate levels (e.g. a Chapter holding Points
directly) — target the depth that actually matches; the path then names
only the ancestors that exist (`add-point "<Part>/<Chapter>/<Point name>"`).
Only a Part can sit at the root.
Under one parent, a deeper (level-skipping) Section must come *before*
shallower siblings — `add`/`move-to-<level>` append as last child, so they
reject a Point after an existing Section under the same Chapter (in
Markdown it would nest under that Section), and `reorder` rejects an order
that breaks this. Every new Section
starts `draft` unless `--set-status` is given — you never pass it.

**Edit content**:

```
specctl --root <root> set-description <id> "<new description>"
specctl --root <root> set-open-questions <id> "<new open questions text>"
```

**Restructure**:

```
specctl --root <root> rename <id> "<new heading text>"
specctl --root <root> reorder <id> --after <sibling-number>
specctl --root <root> move-to-chapter <id> "<Part name>"
```

**`move-to-<level>`'s real semantics** (verified against the actual CLI, not
just the argparse help text): its path argument is the **parent** path
only — one segment shallower than the target level (`move-to-chapter` takes
just the Part name, not `<Part>/<Chapter>`; `move-to-section` takes
`<Part>/<Chapter>`) — never the Section's own name (that's `rename`'s job).
`move-to-part` omits the path entirely. It also **changes the Section's own
depth to match the command**, not just its parent — `move-to-chapter` turns
whatever you give it into a Chapter, even if it was a Section or Subsection
before, re-deriving its Object Type accordingly. Pick the command for the
depth the Section should actually end up at. `reorder --after 0` inserts
before all siblings. A moved Section carries its whole subtree with it and
always lands as the new parent's last child — follow with `reorder` for a
specific position.

**Delete**:

```
specctl --root <root> delete <id> [--force-delete]
```

Rejected without `--force-delete` if descendant Sections still exist.

**Browse before adding/restructuring**:

```
specctl --root <root> --json list [--status draft] [--under "<path>"]
```

**Inspect one Section, or confirm a write persisted**:

```
specctl --root <root> --json show <id> [--history]
```

## Error handling

- **Unknown metagroup path** (an ancestor segment doesn't exist yet): create
  the missing ancestor(s) first, then retry.
- **Not-yet-initialized store**: `init` first (see above), then retry.
- **Object ID collision** on `add-<level>`: retry once — `specctl`
  regenerates the ID from content each time.
- **Delete rejected (descendants exist)**: retry with `--force-delete` only
  if the prompt actually asked for the whole subtree to go; otherwise
  report a failed item rather than guessing.
- Any other non-zero exit: report the stderr text as-is for that one
  operation; don't retry blindly, and don't let one failed item stop the
  rest of the run.

## Out of scope

Status changes and ADR linkage (`set-status`, `set-adr`, or
`set-description`/`set-open-questions` with `--adr`) — entirely
`specctl-editor-cli`'s job.
