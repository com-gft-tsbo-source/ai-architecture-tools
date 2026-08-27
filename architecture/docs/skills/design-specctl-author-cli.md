# specctl-author-cli

Skill that wraps the `specctl` CLI for the `specctl-author` Subagent
(`architecture/docs/subagents/design-specctl-author.md`). Purely an
instructional reference — a `SKILL.md`, no executable wrapper code. The
invoking agent calls the `specctl` binary itself via Bash; this Skill only
teaches it how to do that correctly for the draft-authoring workflow: full
CRUD over a document's still-`draft` content. Companion to
`specctl-editor-cli` (`architecture/docs/skills/design-specctl-editor-cli.md`),
which covers the narrower, ADR-gated subset of `specctl` that
`specctl-adr-author` uses for `stable` content instead — the two Skills'
command surfaces overlap only where the underlying CLI genuinely has no
narrower equivalent (`show`/`list`), and neither Skill's future Subagent
calls the other's exclusive commands.

## Scope

Covers the full `specctl` object-management surface, since the authoring
workflow may need to build, restructure, or tear down draft content in any
combination:

- `init` (with `--preamble`), `set-title`, `set-preamble` — document-level
  setup, including the mandatory one-time initialization
  (`design-specctl.md`, "Store").
- `add-part`, `add-chapter`, `add-section`, `add-subsection`, `add-point`
  (with inline `--description`, `--open-questions`, `--set-status`,
  `--abbrev`, `--id`) — create a Section at any of the 5 heading depths.
- `set-description`, `set-open-questions` — change a Section's content.
  Always called here with **no** `--adr` — every Section this Skill touches
  is still `draft` by construction (`specctl-adr-author` owns everything
  from `stable` onward), so the ADR-gating flag is never needed.
- `rename`, `reorder` — restructure a Section without moving it across
  parents.
- `move-to-part`, `move-to-chapter`, `move-to-section`, `move-to-subsection`,
  `move-to-point` — reassign a Section (and its whole subtree) to a
  different parent.
- `delete` (with `--force-delete` for a subtree) — remove a Section outright.
- `show`, `show-metagroups`, `list` (`--status`/`--under`) — inspect
  existing content before adding to or restructuring it, and re-read a
  just-created/-deleted Section to confirm the write actually took effect.

Not in scope (belongs to a different workflow, so not documented here):
`set-status`, `set-adr` — any Status change or ADR linkage is
`specctl-editor-cli`'s job entirely; this Skill's Subagent never calls
either. Also not in scope: `render`, `history` — read-only
convenience/reporting views neither authoring nor editing content.

## Detecting initialization

There is no dedicated "is this store initialized?" query command. Use one
of:

- `specctl --root <root> --json show-metagroups` (or any other read
  command) and check whether it fails with the "not initialized" error —
  cheap, but conflates "not initialized" with any other read failure unless
  the error text is inspected.
- Simpler and preferred: attempt the first real operation the prompt
  actually needs (e.g. `add-part <path>`); if it fails with the
  not-initialized error, run `init` and retry the same operation once.

Either way, `init` itself is idempotent-**rejecting**: calling it on an
already-initialized store fails rather than silently discarding the
existing Title/Preamble (`design-specctl.md`, "Amendments... specctl `init`
lifecycle"). Never call `init` speculatively without first confirming the
store isn't already initialized — a failed speculative `init` is expected
and fine to treat as "already initialized, proceed," but calling it
*after* a successful one in the same run would be a bug, not a recoverable
error.

## Invocation conventions

- **`--root <path>`**: always supplied by the caller (the `specctl-author`
  Subagent receives it from whoever invoked it — user or orchestrating
  Skill). Never hardcode or guess a root.
- **`--json`**: always pass this flag when the output needs to be parsed
  programmatically (`show`, `show-metagroups`, `list`) — do not scrape the
  human-readable format.
- **Exit codes**: `0` = ok, `1` = error. Error text goes to stderr.
- Every operation is a single, independent `specctl` invocation — there is
  no batch/transaction mode. A multi-step change (e.g. "create a Chapter,
  then add three Sections under it") is several sequential CLI calls; if one
  fails partway, whatever was already created before the failure remains.

## Operation recipes

**Initializing a brand-new document**:

```
specctl --root <root> init "<Title>" [--preamble "<preamble text>"]
```

**Creating a metagroup path and its Section content in one step** — the
path is the full `/`-separated sequence of heading texts, ancestors then
the new leaf; every ancestor segment must already exist:

```
specctl --root <root> add-part "<Part name>" \
  [--description "<text>"] [--open-questions "<text>"] [--id <value>] [--abbrev <code>]
specctl --root <root> add-chapter "<Part name>/<Chapter name>" [--description "<text>"] ...
specctl --root <root> add-section "<Part>/<Chapter>/<Section name>" ...
specctl --root <root> add-subsection "<...>/<Subsection name>" ...
specctl --root <root> add-point "<.../Point name>" ...
```

A Section may skip intermediate levels where the document's own structure
calls for it (e.g. a Chapter holding Points directly) — just target the
depth that actually matches what's being added; there is no requirement to
populate every level. Every newly created Section starts at `draft`
(`specctl`'s default initial Status) unless `--set-status` is given — this
Skill never passes `--set-status` (see `design-specctl-author.md`,
"Status").

**Editing a Section's content**:

```
specctl --root <root> set-description <id> "<new description>"
specctl --root <root> set-open-questions <id> "<new open questions text>"
```

**Restructuring**:

```
specctl --root <root> rename <id> "<new heading text>"
specctl --root <root> reorder <id> --after <sibling-number>
specctl --root <root> move-to-chapter <id> "<Part name>/<new Chapter name>"
```

`move-to-part` omits the path argument entirely (a Part has no parent).
`reorder --after 0` inserts before all siblings. A moved Section carries its
whole subtree with it and always lands as the new parent's last child —
follow with `reorder` for a specific position.

**Deleting**:

```
specctl --root <root> delete <id> [--force-delete]
```

Rejected without `--force-delete` if the Section still has descendant
Sections — pass it to remove the whole subtree in one step.

**Browsing before adding/restructuring**, to see what already exists:

```
specctl --root <root> --json list [--status draft] [--under "<path>"]
specctl --root <root> --json show-metagroups
```

**Inspecting one Section, or confirming a write actually persisted**:

```
specctl --root <root> --json show <id> [--history]
```

`show <id>` right after `add-<level>`/`delete` is how you confirm the write
actually took effect — a run's own belief about what it did is not itself
evidence.

## Error handling

- **Unknown metagroup path** (an ancestor segment named in `add-<level>`'s
  path, or in a `move-to-<level>`'s target parent, doesn't exist yet):
  create the missing ancestor segment(s) first (the same `add-<level>`
  recipe, one level shallower), then retry the original operation. Never
  treat this as a fatal error for the overall run.
- **Not-yet-initialized store**: `init` first (see "Detecting
  initialization"), then retry.
- **Object ID collision** on `add-<level>`: astronomically unlikely with
  generated IDs; if it happens anyway, retry once — `specctl` regenerates
  the ID from content on each attempt.
- **Delete rejected (descendants exist)**: retry with `--force-delete` only
  if the invocation prompt actually asked for the whole subtree to go;
  otherwise surface this as a failed item rather than guessing the user
  meant the larger deletion.
- Any other non-zero exit: surface the stderr text as-is in the Subagent's
  final report for that one operation; do not retry blindly, and do not let
  one failed item abort the whole run — continue with the rest of the
  prompt's requested operations.

## Out of scope

This Skill does not cover Status changes or ADR linkage (`set-status`,
`set-adr`, or `set-description`/`set-open-questions` with `--adr`) — that is
`specctl-editor-cli`'s job entirely, used by the separate `specctl-adr-author`
Subagent once a Section leaves `draft`.
