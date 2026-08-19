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
- Immediately below the heading, exactly one HTML comment holds all bookkeeping (`id`, `nr`, `status`, `adr`, `history`) — invisible in a normal Markdown render or diff-preview, but trivial to parse.
- Content follows as plain Markdown — no `> ` quoting.

There is no `## Meta` list (a node's ancestors are already visible from its heading nesting), no re-stated `## <name>` heading, no separate `## History` section, and no `## Metagroups` bookkeeping block (the headings themselves are the metagroup declarations — nothing needs registering ahead of time).

Example:

    ### Locking

    <!-- specctl id=a3f9c2 nr=003 status=stable adr=b1c2d3
    history:
    - 2026-08-17T15:45:48: M | Add
    - 2026-08-18T09:10:00: M [draft] -> [stable] | adr=b1c2d3
    -->

    A lock is held for the duration of a single invocation only — never
    persisted between invocations. ...

    #### Timeout Behaviour

    <!-- specctl id=f00d21 nr=001 status=draft -->

    Waiting instances time out after 3 minutes; on timeout they steal the
    lock...

**Single-file mode:** the whole document is one file; sections appear in document order, which *is* their sort order (metagroup path, then number) — no separate reordering of "objects vs. document" to keep in sync.

**Directory mode:** one file per leaf, subdirectories mirroring the heading hierarchy, as in the general model. Since every node (not just leaves) is an object, each directory additionally holds a `_content.md` file carrying that node's own heading/comment/content — distinct from the tool-bookkeeping `.index.md`/`.index.json` files, which continue to serve their general-model role unchanged. *(This mapping is a proposal — directory mode is secondary for a tool whose primary use case is a single flowing document; revisit once a real multi-file spec surfaces.)*

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

- `Description` — the Section's main prose. Mandatory, always available (same fixed name as the general model's `--description`).
- `OpenQuestions` — optional free Markdown; unresolved questions or todos for this Section, pending a future ADR.

Both stored as plain Markdown directly under the object's metadata comment — no `> ` prefix (see Object Format).

## ADR Linkage

`specctl` and `adrctl` objects reference each other, kept in sync by a shared module `lib/spec_link.py`, used by both `adrctl.py` and `specctl.py`. Neither CLI script imports the other directly, per the existing convention in `architecture/scripts/CLAUDE.md` ("a CLI script never imports another CLI script as a whole").

- **specctl → adrctl**: the `adr` Metainfo field (above) names the one currently-governing ADR for a Section.
- **adrctl → specctl**: a new `adrctl` Metainfo field, `spec-ref=<file>#<id>` — repeatable, since one ADR may govern several Sections across one or more spec documents. See the corresponding addition to `design-adrctl.md`.
- **Propagation is automatic**, not a manual sync step: whenever an ADR carrying one or more `spec-ref` values is created, or has its status changed via `adrctl set-status`, `lib/spec_link.py` updates the `adr` field — and appends the matching `M` History entry — on every referenced `specctl` object, within the same invocation. A `spec-ref` pointing at a file or object ID that doesn't exist aborts the `adrctl` operation with an error rather than being silently skipped.
- Superseding an ADR (`adrctl`'s existing `superseded-by` metainfo) updates a Section's `adr` value the same way, once the superseding ADR itself declares the matching `spec-ref` and is accepted — older ADRs remain fully queryable in `adrctl`'s own History, even though a Section's `adr` field only ever shows the single current one.

## Operations

In addition to the general operations from `design.md`, adapted per the deviations above:

- `add-<metagroup-type> <name>` creates the path segment **and** its object in one step (see "Deviation from the general model") — there is no separate content-less path-declaration step to run first.
- `set-adr <id>`: manually set or correct the `adr` Metainfo field. Normally driven automatically by `adrctl` (see ADR Linkage), but available directly for manual correction or for documents not yet backed by an ADR store.
- `render`: emit the document as plain, comment-stripped Markdown (headings and content only) — a read-only convenience view, does not alter the source.

## Scope

Generic tool, like `taskctl`/`rulectl`/`adrctl` — usable for any project's specification documents. This repository's own `architecture/docs/scripts/*.md` documents are a first application, not the only one; `specctl` should be able to manage them without knowing anything specific about this repository.
