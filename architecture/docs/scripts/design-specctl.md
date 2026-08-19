# specctl

Objects are **Sections** of a specification/design document — a Markdown heading at any depth, together with the content directly under it, before its next sibling or child heading.

## Deviation from the general model

In the other three tools, a metagroup path is pure classification — it has no content of its own, only objects nested under its leaf. `specctl` cannot work that way: a document like `design.md` carries prose under *every* heading level, not just at the deepest one (e.g. "## Metagroups" itself has text, and so does "### Object ID" beneath it). So for `specctl`, **every metagroup-path node is itself an object** — it has its own ID, Status, Content and History, in addition to being the parent path for whatever nests beneath it. `add-<metagroup-type>` therefore both establishes the path *and* creates that level's object in one step (see Operations).

This also resolves what would otherwise be "arbitrary heading depth": since a metagroup path node is always an object with a bounded set of ancestor levels, the same 3-level cap from `design.md` needed a tool-specific extension (see Metagroups below) rather than being unlimited.

## Metagroups

5 levels — extends the general 3-level cap in `design.md` for this tool only. Each level maps to one Markdown heading depth:

| Level | Metagroup Type | Heading |
|---|---|---|
| 1 | Part | `##` |
| 2 | Chapter | `###` |
| 3 | Section | `####` |
| 4 | Subsection | `#####` |
| 5 | Point | `######` |

The document's own `# <title>` is not a `specctl` object. This is also why 5 is the natural cap, not an arbitrary choice: Markdown offers heading depths `#` through `######`; reserving `#` for the document title leaves exactly 5 usable depths.

Not every branch needs all 5 levels — a Chapter may hold Points directly, skipping Section/Subsection, exactly as a shallower branch is allowed under the general metagroup model. As with the other tools, a path segment must be created before anything is added under it: adding a `#####` heading requires its enclosing `####`/`###`/`##` objects to already exist (this falls out naturally from Markdown nesting, not from an extra check).

## Object Type

Replaces the general derivation table for this tool (a second named exception alongside `taskctl`'s, see `design.md`). Width grows with depth instead of staying fixed at 6 characters, since a 5-level path could not stay legible otherwise:

| Level | Letters taken at this level | Cumulative width |
|---|---|---|
| 1 (Part) | 2 | 2 |
| 2 (Chapter) | 2 | 4 |
| 3 (Section) | 2 | 6 |
| 4 (Subsection) | 2 | 8 |
| 5 (Point) | 2 | 10 |

Letters are taken from the metagroup Name after stripping its `<nr>-` prefix, same as the general rule. The same collision-resolution ladder from `design.md` (anchor on common prefix → extend up to 3 extra characters → numeric suffix → abort, require `--abbrev`) applies unchanged, generalized to the object's actual depth.

## Object Format (lightweight — replaces the general format entirely)

`design.md`'s generic Object Format (`# <signature>` heading, `## Meta` bullet list, `> `-quoted content, `## History` section) is deliberately **not** used here — it would work against `specctl`'s own stated goal (see `VISION.md`) of keeping the document human-readable while still being agent-usable. Instead:

- The heading itself (`##` … `######`) is plain, human-authored text — the object's Name, verbatim. No ID, Signature, or type is encoded into it.
- Immediately below the heading, exactly one HTML comment holds all bookkeeping (`id`, `type`, `nr`, `status`, `adr`, `history`, and optionally `open-questions`, see User Content) — invisible in a normal Markdown render or diff-preview, but trivial to parse. `type` is stored explicitly rather than re-derived on every read, for the same reason the general Object Format stores it in `## Meta`: collision resolution depends on creation order (design.md, "Object Type").
- Content follows as plain Markdown — no `> ` quoting.

There is no `## Meta` list (a node's ancestors are already visible from its heading nesting), no re-stated `## <name>` heading, no separate `## History` section, and no `## Metagroups` bookkeeping block (the headings themselves are the metagroup declarations — nothing needs registering ahead of time).

Example:

    ### Locking

    <!-- specctl id=a3f9c2 type=PaCh__ nr=003 status=stable adr=b1c2d3
    open-questions:
    > Re-check the timeout after a steal, or leave it as-is?
    history:
    - 2026-08-17T15:45:48: M | Add
    - 2026-08-18T09:10:00: M [draft] -> [stable] | adr=b1c2d3
    -->

    A lock is held for the duration of a single invocation only — never
    persisted between invocations. ...

    #### Timeout Behaviour

    <!-- specctl id=f00d21 type=PaChTi nr=001 status=draft -->

    Waiting instances time out after 3 minutes; on timeout they steal the
    lock...

**Single-file mode:** the whole document is one file; sections appear in document order, which *is* their sort order (metagroup path, then number) — no separate reordering of "objects vs. document" to keep in sync.

**Directory mode:** since every node (not just leaves) is an object here, directory mode cannot use the general model's split of "directory = pure classification, file = object" — a node that has children would need to be a directory *and* a file at once. Resolved uniformly: **every Section is a directory**, `<nr>-<type>-<id>-<slug>/`, regardless of whether it currently has children — `<nr>`/`<type>`/`<id>` guarantee uniqueness the same way the general model's object file names do (design.md, "Index Files"); `<slug>` (lowercase, filesystem-safe) only needs to stay readable. Inside it:

- `_content.md` — that Section's own heading + metadata comment + `Description`, in the exact same format as one block of the single-file mode (see Object Format above) — a directory-mode `_content.md` and a single-file-mode heading block are byte-for-byte interchangeable modulo surrounding context.
- one further such directory per child Section, recursively.

There is no `.index.md`/`.index.json`: those general-model files cache an Object Type *shared* by every object filed under one metagroup leaf, but a specctl Section already carries its own Object Type directly in `_content.md` (see Object Format) — a parallel index would only duplicate it, not serve a distinct purpose. The document's preamble (its own `# <title>` and any intro text, kept verbatim in single-file mode) has no single file to live in in directory mode either; it is instead an optional `_preamble.md` at the root directory itself.

Like single-file mode's whole-file rewrite, a directory-mode write clears and rebuilds the whole tree from the in-memory Section list on every change — there is no incremental file-level diffing. This is simpler and, since the whole `--root` directory is understood to be exclusively managed by `specctl` (design.md, "File and Directory Parameters"), safe; it is not atomic across the multiple directories/files touched by one write, the same limitation the general model's directory mode already has for an interrupted reorder cascade (design.md, "Concurrency / Locking").

## Status

- `draft` (initial) — free editing; no ADR required; content changes are not logged (see History).
- `stable` — reached only by explicit transition; from here, any content change requires a valid `adr` reference already set (see Metainfo) — the tool aborts the change otherwise, unless `--adr <id>` is supplied inline with the same command to satisfy it.
- `deprecated` — reachable from `stable`; same ADR requirement (the ADR documents the deprecation decision itself).

No automatic transitions, per the `design.md` default. `stable` → `draft` (rework) requires `--force`, as does any other non-listed transition.

## Metainfo

- `adr`: ID of the single, currently-governing ADR (an `adrctl` object ID) for this Section. Optional in `draft`; required from `stable` onward. Set either manually (`specctl set-adr <id>`) or automatically by `adrctl` via the shared linkage mechanism below — whichever last touched it wins, both are logged identically.

## History

Deviates from the general model: only `M` entries for **Add**, **Rename**, **Move** (metagroup/path change), and **Status change** (including the `adr` value that made a `stable`/`deprecated` transition valid) are logged. Content changes to `Description`/`OpenQuestions` are **not** logged here. This is intentional, not an omission: during `draft`, changes are meant to stay untracked (no overhead while a section is still being drafted, per `VISION.md`); from `stable` onward, content changes only happen alongside an `adr` update anyway, so the authoritative trail for *why* the content changed lives in that ADR's own History, not duplicated here.

## User Content

- `Description` — the Section's main, visible prose. Mandatory, always available (same fixed name as the general model's `--description`). Stored as plain Markdown directly under the object's metadata comment — no `> ` prefix (see Object Format).
- `OpenQuestions` — optional free text; unresolved questions or todos for this Section, pending a future ADR. Unlike `Description`, this is stored **inside** the hidden metadata comment (`open-questions:` block, `> `-encoded), not as visible Markdown: a second visible convention would need its own in-band delimiter (e.g. a sub-heading) that could collide with a real nested Section/Subsection/Point heading one level down. Since open questions are working notes rather than primary reading content, hiding them alongside `history:` fits the same "keep the rendered document readable" goal instead of working against it.

## ADR Linkage

`specctl` and `adrctl` objects reference each other, kept in sync by a shared module `lib/spec_link.py`, used by both `adrctl.py` and `specctl.py`. Neither CLI script imports the other directly, per the existing convention in `architecture/scripts/CLAUDE.md` ("a CLI script never imports another CLI script as a whole").

- **specctl → adrctl**: the `adr` Metainfo field (above) names the one currently-governing ADR for a Section.
- **adrctl → specctl**: a new `adrctl` Metainfo field, `spec-ref=<file>#<id>` — repeatable, since one ADR may govern several Sections across one or more spec documents. See the corresponding addition to `design-adrctl.md`.
- **Propagation is automatic**, not a manual sync step: whenever an ADR carrying one or more `spec-ref` values is created, or has its status changed via `adrctl set-status`, `lib/spec_link.py` updates the `adr` field — and appends the matching `M` History entry — on every referenced `specctl` object, within the same invocation. A `spec-ref` pointing at a file or object ID that doesn't exist aborts the `adrctl` operation with an error rather than being silently skipped.
- Superseding an ADR (`adrctl`'s existing `superseded-by` metainfo) updates a Section's `adr` value the same way, once the superseding ADR itself declares the matching `spec-ref` and is accepted — older ADRs remain fully queryable in `adrctl`'s own History, even though a Section's `adr` field only ever shows the single current one.

**Implementation status:** the automatic propagation (`spec-ref`, `lib/spec_link.py`, the `adrctl`-side write-back) is specified above but **deferred** to a follow-up change. The first implementation of `specctl` ships the `adr` Metainfo field and `set-adr` as a manual command only — `adrctl` is not yet touched. This lets `specctl` land and be exercised standalone before the cross-tool wiring is built on top of it.

## Operations

In addition to the general operations from `design.md`, adapted per the deviations above:

- `add-<metagroup-type> <name>` creates the path segment **and** its object in one step (see "Deviation from the general model") — there is no separate content-less path-declaration step to run first. `<name>` is the full `/`-separated path of heading texts, ancestors then the new leaf (the general model's own shape for `add-<type> <name>`, e.g. `add-component frontend/mocking`) — there is no separate `--name` flag, since the path's leaf segment *is* the Section's heading text.
- `set-description <id> <value>`: change a Section's `Description` content — the general model's "Change content" operation, made explicit here (unlike the other three tools, which don't yet expose it over the CLI) because the ADR-gating rule under Status needs a command to attach to. Accepts `--adr <id>` inline for the case described under Status.
- `set-adr <id> <value>`: manually set or correct the `adr` Metainfo field. Normally driven automatically by `adrctl` (see ADR Linkage), but available directly for manual correction or for documents not yet backed by an ADR store. Not logged in History (see History above).
- `rename <id> <name>`: change a Section's heading text without moving it. Cascades: every descendant's stored ancestor path embeds this Section's own `<nr>-<name>` segment (see Object Format) and is rewritten accordingly.
- `reorder <id> --after <nr>`: move a Section to a new position among its siblings (same parent), per the general model's Numbering/Reorder rules. A Section's own subtree moves with it; renumbering a sibling cascades into its descendants' ancestor paths the same way `rename` does.
- `move-to-<metagroup-type> <id> [<parent-path>]`: the general model's "Change metagroup" operation (design.md: `set-<metagroup-type>`), renamed here to avoid colliding with `set-adr`/`set-description`'s `set-*` shape and to read naturally alongside `add-<metagroup-type>`. Reassigns the Section's parent — one subcommand per target level (`move-to-part`/`-chapter`/`-section`/`-subsection`/`-point`), `<parent-path>` is the `/`-separated path of *existing* ancestor Sections at that level (omitted entirely for `move-to-part`, which has no parent to name) — the Section's own Name and Description are untouched, only its position. It always lands as the last child of the new parent (`add`'s own placement rule, see "Deviation from the general model"); combine with `reorder` afterwards for a specific position.

  Re-derives everything downstream, same rationale as the general model's `set-<metagroup-type>` (design-decisions.md, "Numbering": "changing an object's metagroup re-derives everything downstream") — but here that means the **entire moved subtree**, not just the Section itself: every descendant's Object Type is derived from its own full ancestor-name path (see Object Type above), which changed for all of them, not only for the moved root. The Section's own Number is reassigned (`max+1` among the new siblings, the same rule `add` uses); descendants keep their own Numbers, only the ancestor prefix embedded in their stored path is rewritten (the same cascade `rename`/`reorder` already perform, generalized from a single-position substitution to a whole-prefix replacement, since both the ancestor values *and* their count can change).

  Rejected: moving a Section into its own subtree (a cycle), moving it to its current parent (no-op — use `reorder` for repositioning among unchanged siblings instead), and any move whose resulting depth — for the Section itself or any descendant — would exceed the 5-level cap (design-specctl.md, "Metagroups").
- `render`: emit the document as plain, comment-stripped Markdown (headings and content only) — a read-only convenience view, does not alter the source.

## Scope

Generic tool, like `taskctl`/`rulectl`/`adrctl` — usable for any project's specification documents. This repository's own `architecture/docs/scripts/*.md` documents are a first application, not the only one; `specctl` should be able to manage them without knowing anything specific about this repository.
