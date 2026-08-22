# Agent Tool Design Criteria

This document describes the general design principles for CLI tools that support agentic AI workflows. Each tool manages "objects" that share the same semantic meaning within that tool.

Tools:

- taskctl — see design-taskctl.md
- questctl — see design-questctl.md
- rulectl — see design-rulectl.md
- adrctl — see design-adrctl.md
- specctl — see design-specctl.md

## File and Directory Parameters

Tools store their data in files or directories, resolved from a single `--root <path>` (see CLI Contract). Each tool has a fixed **store name** (`tasks` for taskctl, `questions` for questctl, `rules` for rulectl, `adrs` for adrctl, `spec` for specctl — see each tool's design document) that names its data within a directory shared by all five tools — this is what lets tools reference each other's objects (e.g. adrctl ↔ specctl, design-specctl.md "ADR Linkage") without an ambiguous, separately-configured path.

`--root <path>` is resolved to the tool's actual file-or-directory target in two steps:

**1. Determine the shared directory** — the directory that holds (or will hold) every tool's data for this project. `path` is treated as naming *this tool's own target directly* — and its parent used as the shared directory — whenever it looks like a file (exists as one, or doesn't exist yet but ends in `.md`) **or** its own name already matches this tool's store name `<name>` (e.g. `path` is exactly `.../adrs` for `adrctl`); otherwise `path` itself is the shared directory:
- `path` exists and is a file → its parent directory.
- `path` does not exist, ends in `.md` → its parent directory (created if necessary).
- `path`'s own name equals `<name>` (this tool's store name) → its parent directory (created if necessary) — without this, a first invocation naming the target directory directly (e.g. `adrctl --root ./project/adrs`, not yet existing) would otherwise double-nest to `./project/adrs/adrs`.
- Anything else (including an existing directory) → `path` itself.

This means `--root` may point at *any* tool's own **file** — e.g. running `specctl --root ./project/adrs.md` resolves the shared directory to `./project`, exactly as `--root ./project` would. **Open gap:** the equivalent for an existing bare *directory* belonging to a different tool (e.g. `specctl --root ./project/adrs`, an existing directory) is not yet resolved the same way — its name doesn't match specctl's own store name, so rule 4 below applies and `./project/adrs` is (incorrectly, from a cross-tool-pointing perspective) treated as the shared directory itself. Only pointing at the shared directory directly, or at a tool's own `<name>.md` file, is currently reliable.

**2. Resolve this tool's target within the shared directory**, given its store name `<name>`:
- Two candidates: `<name>.md` (file, *single-file mode*, see "Object Format" below) and `<name>` (directory, *directory mode* — one object per file).
- Both candidates exist → abort with an error (ambiguous; requires manual cleanup).
- Exactly one candidate exists → use it, in the corresponding mode.
- Neither exists (first invocation for this tool):
  - `path` (from step 1, before resolving to the shared directory) is itself exactly the file candidate → create and use it as a file.
  - `path` is itself exactly the directory candidate → create and use it as a directory.
  - Otherwise → the tool's own default mode (see its design document), creating `<name>.md` or `<name>`.

There is no multi-root, read-only merge mode — `--root` takes exactly one path, and every invocation resolves to exactly one file-or-directory target (design-decisions.md, "Amendments": this replaced the original repeatable-`--root` merge design once cross-tool referencing needed an unambiguous, shared location instead).

## Managed Objects

### Object ID

- Every object has an ID, **unique within its store** — `add` rejects an explicit `--id` (or, astronomically unlikely, a derived one) that already exists there.
- Generated once, on creation, as a 6-character hexadecimal code derived from the object's initial content. It never changes afterwards, even if the content changes later.
- May instead be supplied explicitly as a parameter at creation time; in that case it may be any free-form string.
- Free-form IDs **must not contain `/`** (reserved for the `--id` path-selector syntax, see CLI Contract).

### Metagroups

- Metagroups classify objects along a tool-specific, hierarchical axis (e.g. Category for rulectl, Component for adrctl, Phase for taskctl).
- A metagroup is a Type/Name tuple. The set of metagroup Types and their order is fixed per tool, with a maximum of **3 levels** (exception: specctl, up to **5** levels — see design-specctl.md).
- A tool's metagroup **hierarchy** is fixed (as above), but whether a given object must sit at that hierarchy's deepest level is not always so: questctl (design-questctl.md) is the one exception, where an object may attach at any level of its (≤2-level) hierarchy, including none at all.
- Each metagroup Name is itself a (partial) path reflecting its position in the hierarchy, e.g.:

      Type: Category
      Name (level 1, Language):  Python
      Name (level 2, Context):   Python/backend
      Name (level 3, Category):  Python/backend/validation

- **Every object belongs to exactly one metagroup** (one leaf-level path) — there is no multi-membership (exception: questctl, where that one path may also be empty — see design-questctl.md, "Metagroups"). If an object would logically belong to more than one path (e.g. an ADR affecting two components), the user manually creates a new metagroup that semantically represents the combination. This is a manual convention, not a tool feature.
- The object's `Meta` section (see Object Format) lists the resolved value for every ancestor level of that one path, for easy filtering/display — this is a derived display of the single assignment, not independent membership.
- A metagroup path that is referenced (e.g. via `add`/`group-<metagroup-type>`) but does not exist aborts the operation with an error, in both modes. Metagroup paths must be created explicitly first via `add-<metagroup-type> <name>` — tools never auto-create them.
  - In **directory mode**, this mirrors the metagroup hierarchy 1:1 as nested subdirectories; `add-<metagroup-type> <name>` creates that directory.
  - In **single-file mode**, there is no filesystem directory to create; `add-<metagroup-type> <name>` instead writes an entry to the file's `## Metagroups` bookkeeping section (see Object Format). This keeps the "must exist first" rule identical across both modes.
- Every metagroup Name carries a 3-digit, zero-padded sort number as prefix: `<nr>-<name>` (e.g. `002-Implementation`). This number determines display/listing order and is stripped before deriving the Object Type (see below). By default it is assigned the same way as object numbers (see Numbering) — `max + 1` among sibling metagroups at creation — but `add-<metagroup-type>` also accepts the prefix supplied explicitly (`add-<metagroup-type> <nr>-<name>`), which is then used verbatim instead of being auto-assigned. There is no dedicated "reorder metagroup" operation; changing the order of an already-created metagroup is done via Rename (assigning a different `<nr>-<name>`).
- **Changing an object's metagroup** (`group-<metagroup-type>`) re-derives everything that depends on it: a new Number (via `max + 1` in the new subpath — the old subpath's number becomes a gap), a new Object Type, a new Signature and file name, the file's physical location (directory mode) or its position within the file (single-file mode), and the `## Meta` section content. This is logged as a normal `M` history entry.

### Metainfo

- Every object may carry Metainfo: Type/Name tuples that provide context for the object's content (e.g. `weight`, `tool`, `assignee-type`). Available types are tool-specific.
- A Metainfo type may declare a fixed, closed set of valid values (e.g. taskctl's `review`: `none`/`user`/`subagent`) instead of free text. Setting a value outside that set — via `info-<metainfo-type>` or inline on `add` — is rejected with an error; a type without a declared value set accepts any text.

### Numbering

- Every object has a running number, counted from 1 within its metagroup path (subpath), displayed 3-digit zero-padded.
- Assigned automatically on creation as `max + 1` of the numbers currently used in that subpath — **not** the smallest free/gap number.
- Deleting an object leaves a gap — numbers are never compacted.
- Reordering an object moves it to a new position among its siblings. If an existing gap between the target neighbors can accommodate the new position, it is reused and no other object is touched. Otherwise, the numbers of the objects between the old and new position are shifted by one, renaming their files and updating their content accordingly.

### Object Type

The Object Type is a short, stable code derived from the object's metagroup, unique per distinct metagroup path combination, and forms part of the Signature and the file name.

**Derivation** (unless an explicit abbreviation was supplied, see below):

| Metagroup levels | Letters taken per level |
|---|---|
| 1 | 6 |
| 2 | 3 + 3 |
| 3 | 2 + 2 + 2 |

- Letters are taken from the metagroup Name **after** stripping its `<nr>-` sort prefix.
- If the result is shorter than 6 characters, it is right-padded with `_` to reach 6.
- A tool may define an entirely different derivation (see design-taskctl.md and design-specctl.md for exceptions), or extend this table to a 0-level row (see design-questctl.md, "Object Type").

**Explicit override:** an abbreviation may be supplied explicitly when creating a metagroup path (`add-<metagroup-type> <name> --abbrev <code>`). In directory mode it is stored in `.index.md`; in single-file mode it is stored alongside the path in the `## Metagroups` section. Either way it is then stable / write-once — later collisions elsewhere never change an abbreviation once assigned.

**Collision resolution:** when the derived abbreviation for a *new* metagroup path collides with an existing one, resolve per colliding level: keep the letters of non-colliding levels unchanged; for the colliding level, keep the common prefix as an anchor and advance position by position through the source name until the first character is found that differs from the corresponding position in the already-assigned colliding name; use that character in place of the naturally-derived one.

Example: `backend/login` → `baclog`. Adding `backend/logik` also naturally derives to `baclog` (collision). `login` and `logik` are identical through position 4 and first differ at position 5 (`n` vs. `k`), so the resolved abbreviation becomes `baclok` (`bac` unchanged + `lok`, keeping the 3-character width for that level).

**If that is not sufficient** (e.g. two source names are identical, or the divergent character lies beyond the target width):
1. Keep advancing beyond the normal target width, up to 3 extra characters (e.g. up to 9 total characters for a 6-character target, unpadded).
2. If still colliding, append a numeric suffix: `baclok-2`, `baclok-3`, …
3. If that still doesn't resolve it, abort with an error and require an explicit `--abbrev` override.

**On the command line**, trailing `_` padding may be omitted when typing an Object Type — the tool re-pads before matching.

**Stability:** the Object Type is always derived from the object's current metagroup assignment and is part of its file name. Once recorded (in `.index.md` or in a file's `## Metagroups` section), an abbreviation is never silently changed by a later, unrelated addition elsewhere.

### Object Name

Every object has a Name: single-line free text.

### Object Signature

Every object has a Signature: `<type>-<nr>-<id>-<name>[-<class>]`

- `<type>` = the (padded) Object Type
- `<nr>` = 3-digit, zero-padded running number
- `<id>` = the object's ID
- `<name>` = the object's Name
- `<class>` = optional, tool-defined

**Escaping:** every character in `<name>` (and any other free-text component) outside `[A-Za-z0-9]` is replaced with `_`. This mapping is one-way — reconstructing the original text from a Signature is neither possible nor required; Signatures are for display only, objects are resolved via ID (see `--id` in CLI Contract).

### Object Status

Every object has a Status. Valid values and any transition rules are tool-specific (see each tool's document). Unless a tool defines otherwise, status changes are manual — triggered by a user or an agent acting on instruction — there is no automatic transition logic.

`--set-status` may be supplied together with `add` to choose any status as the object's **initial** value, even one that would be unreachable as a *transition* under the tool's normal rules (e.g. creating a taskctl task directly in `[~]`). This counts as an initial-value choice, not a transition, and therefore never requires `--force`.

### Object History

Every object has a History: a chronological, timestamped log of every management operation and, where applicable, every explicitly annotated progress log.

**Format:**

    - 2026-08-17T15:45:48: M [draft] -> [active] | Status set to active
    - 2026-08-17T15:46:02: T [~] -> [~] |
      > Research on signature escaping complete,
      > proposal is in review.
    - 2026-08-17T16:01:10: M | Description refined

**Grammar (line-based; no parser required):**
- A line starting with `- ` in column 0 begins a new entry.
- A line starting with exactly `  > ` continues the previous entry's message.
- Prefix `M` marks a management operation on the object (add, rename, content/metainfo/metagroup change, status change). The transition segment `[<old>] -> [<new>]` is shown only when the status actually changed.
- A tool may define additional prefixes for its own operations (see design-taskctl.md for `T`).
- Message text follows either inline after `" | "` on the header line, or as one or more `  > `-prefixed continuation lines — never both in the same entry. Message text must not itself contain a line starting with `  > ` or with `- ` in column 0.
- A tool may restrict which operations are logged here (see design-specctl.md for an exception that omits content-change entries).

### User Content

Objects are filled with user content, typically Markdown containing instructions or guidance for an agent or user. Tools request specific named blocks (e.g. `Description`); each tool defines which blocks it supports. Every block may contain Markdown and is stored with a `> ` prefix per line.

## Object Format

A tool may replace this format entirely with its own (see design-specctl.md, whose human-readability requirement is incompatible with the `> `-quoted, signature-headed format below).

An object consists of exactly **one** level-1 heading and its nested sections:

    # <signature>

    ## Meta

    - <metagroup-type>: <metagroup-name>
    - <metainfo-type>: <metainfo-name>
    ...

    ## <object name>

    > <description>

    ### <optional section, tool-specific>

    > <section content>

    ## History

    - 2026-08-17T15:45:48: M | ...

- No YAML frontmatter is used, in either mode.
- The `## Meta` section is a Markdown bullet list (`- Type: Name`), listing every ancestor level of the object's single metagroup path.
- **Every level-1 heading marks a new object.** No exceptions — bookkeeping content (see below) always stays at level 2 or deeper so this rule never needs a special case.

**Single-file mode:** multiple objects appear one after another in the same file, sorted by metagroup then number. Objects are separated by a horizontal rule (`---`) — only *between* objects, never before the first or after the last (a leading `---` would otherwise risk being misread as YAML frontmatter by generic Markdown tooling).

If the file uses metagroups that need to be created ahead of any object (mirroring `add-<metagroup-type>` in directory mode), it starts with a `## Metagroups` section, before the first object's `# <signature>` heading:

    ## Metagroups

    - Phase: 001-Setup (abbrev: 001)
    - Phase: 002-Implementation (abbrev: 002)

    # <signature of first object>
    ...

This is plain Markdown (same bullet-list style as `## Meta`), holds one line per declared metagroup path with its Object Type abbreviation, and is the single-file-mode equivalent of `.index.md` (see Index Files) — a metagroup referenced by `group-<metagroup-type>` but missing from this section aborts with an error, exactly as an undeclared directory would in directory mode.

**Directory mode:** exactly one object per file. Since the metagroup is already conveyed by the file's location in the directory tree, no additional metagroup-path heading is inserted and headings are not shifted — the template above is used unchanged.

## Operations

### Metagroup Operations
- Create (`add-<metagroup-type> <name>`) — creates the metagroup's directory (directory mode) or its `## Metagroups` entry (single-file mode).
- Rename — **not yet implemented** for taskctl/rulectl/adrctl (no store method or CLI command); specctl covers this implicitly, since every metagroup node is itself an object there and its own `rename` operation applies (design-specctl.md, Operations).
- Show (`show-metagroups`)

### Object Operations
- Add
- Reorder
- Delete (`delete <id>`) — removes the object outright; leaves its Number as a permanent gap, same as any other deletion (see Numbering above). Not logged anywhere once gone — there is no tombstone.
- Change status
- Change content (`set-<user-content-block> <id> <value>`, e.g. `set-description`) — one subcommand per declared user-content block.
- Change metagroup (`group-<metagroup-type> <id> <path>`, see "Changing an object's metagroup" above) — reassigns the object to a different, already-existing metagroup path, resolved the same way `--<metagroup-type>` is elsewhere; rejects a no-op (the object's current path) with an error pointing at `reorder` instead. specctl has its own, differently-named equivalent (`move-to-<metagroup-type>`, design-specctl.md, Operations), since `set-*`/`group-*` there would collide with its own command shapes.
- Display: short (single line)
- Display: full description
- Display: short + history

### Operations Across All Objects
- List all objects (short display)
- List objects in specific metagroups (`list --<metagroup-type> <path>`) — includes every object at or below that path, not only an exact match.
- List objects with specific metainfo (`list --<metainfo-type> <value>`) — exact match.
- List objects with a specific status (`list --status <value>`)
- Historical overview: the combined history of all objects, newest first

## Index Files

Two files per metagroup-path directory (**directory mode only**), kept strictly separate. (The single-file-mode equivalent is the in-file `## Metagroups` section described under Object Format — there is only one file to scan, so a separate cache file is unnecessary there.)

### `.index.md`
Human-maintainable; holds the Object Type abbreviation for that path segment (see Object Type). Write-once / stable — never overwritten automatically once set, except by an explicit user edit or an explicit `--abbrev` override at creation time.

### `.index.json`
A pure performance cache, indexed by Object ID, listing only the **direct children** of that directory (no transitive aggregation across sub-levels). Written synchronously on every change that affects it.

    {
      "updated": "2026-08-17T16:20:00",
      "objects": {
        "a3f9c2": {
          "nr": 5,
          "type": "baclok",
          "name": "Configure database connection",
          "status": "active",
          "file": "005-baclok-a3f9c2-configure-database-connection.md",
          "meta": { "weight": "high", "tool": "eslint" }
        }
      }
    }

`meta` carries the object's Metainfo key/value pairs, so metainfo-based listing is also index-accelerated. `.index.json` can be rebuilt at any time from the object files via the explicit `reindex` command, which never modifies `.index.md`.

## Concurrency / Locking

- A lock is held for the duration of a single invocation only — never persisted between invocations. Its scope is exactly the target the tool was invoked on: the **single file** in single-file mode, or the **root directory** in directory mode. Two invocations operating on different files or different directory roots must never block each other.
- Waiting instances time out after **3 minutes**; on timeout they steal the lock. A warning should be logged, recording the previous holder's PID/timestamp, since a slow (rather than crashed) holder could still be writing.
- Writes go through a `<...>.tmp` file, renamed into place only on success, to protect against partial writes.
- `reindex` should detect and help clean up residual inconsistencies (numbering gaps/duplicates, orphaned `.tmp` files) that a stolen lock or interrupted multi-file operation (e.g. an aborted reorder cascade) may leave behind.

## CLI Contract

- `--root <path>`: resolved to this tool's file-or-directory target as described under "File and Directory Parameters" above. Required, single value — not repeatable.
- Subcommand style: `add`, `add-<metagroup-type> <name>`, `set-status`, `group-<metagroup-type>`, `info-<metainfo-type>`, `set-<user-content-block>`, `delete`, `annotate`, `next`, `show`, `show-metagroups`, `reindex`, `list`, …
- **Three separate verb-prefix families, one per axis a `<type> <value>`-shaped update can target** — `group-<metagroup-type>` (Change metagroup), `info-<metainfo-type>` (Metainfo), `set-<user-content-block>` (Change content) — each a fixed part of the generic engine (`lib/cliapp.py`), not a per-tool choice, so the same three prefixes apply uniformly across taskctl/rulectl/adrctl. Splitting the update verb by axis, rather than a single shared `set-<type>` for all three, is what keeps the command namespace collision-free: since each tool independently declares its own metagroup-, metainfo-, and content-block type names, nothing stops two axes from picking the same bare name (design-decisions.md, "Amendments"). `add-<type> <name>` and `group-<type> <id> <value>` / `info-<type> <id> <value>` / `set-<type> <id> <value>` all share one uniform *shape* — a subcommand followed by positional value(s) — even though the verb differs per axis, e.g. `add-domain backend`, `group-domain backend`, `info-superseded-by <id> abc123`, `set-description <id> "..."` (nested metagroup types take a path-like name spanning their own ancestors).
- `group-<metagroup-type> <id> <value>`: reassigns an object to a different, already-existing metagroup path — resolved the same way `--<metagroup-type>` is (see below). Rejects reassigning to the object's current path (no-op — use `reorder` for repositioning among unchanged siblings instead).
- Inline on `add`, the same three axes are populated via bare `--<type>` flags (`--<metagroup-type>`, `--<metainfo-type>`, `--<user-content-block>`) — no verb prefix there, since `add` itself is the single command they're all inline to.
- `add-<metagroup-type> <name> [--abbrev <code>]`: creates a metagroup path (and, optionally, its Object Type abbreviation) — as a directory in directory mode, or as a `## Metagroups` entry in single-file mode. Only the path's last segment is newly created; every ancestor segment must already exist and is resolved the same way as `--<metagroup-type>` below. If the last segment lacks a `<nr>-` sort prefix, one is auto-assigned (`max + 1` among its siblings, see Metagroups above); an explicitly supplied prefix is used verbatim.
- `--<metagroup-type> <value>` — whether inline on `add`, on `group-<metagroup-type>`, or anywhere else a metagroup path is referenced (not created) — resolves an *existing* path one `/`-separated segment at a time against that segment's siblings. Each segment may be given as the exact `<nr>-<name>` form, a bare number (`2`), or a bare name (`Implementation`). A segment matching more than one sibling (e.g. two same-named siblings with different numbers) aborts with an error rather than guessing.
- `delete <id>`: removes the object outright (see "Object Operations" above).
- `list [--status <value>] [--<metagroup-type> <path>] [--<metainfo-type> <value>]`: lists objects, optionally filtered. At most one `--<metagroup-type>` flag may be given (an object has exactly one metagroup path); it is resolved the same way as `--<metagroup-type>` above and matches that path plus everything below it. Every `--<metainfo-type>` flag given must match that Metainfo's value exactly; multiple such flags combine (AND).
- `--name "..."`: the object's Name.
- `--description "..."`: the object's Description (always available under this fixed name).
- `--<user-section> "..."`: content for any other tool-defined user-content block.
- `--message "..."`: the History log text for `set-status`, `annotate`, or any other logged operation.
- `--id <value>`: object selector, resolved in order: (1) matches the Signature pattern, (2) contains `/` → interpreted as `<metagroup-path>/<nr>`, (3) otherwise treated as a raw ID. (This is why free-form IDs must not contain `/`.) Note: this full resolver only backs `show`'s `--id`-flavored positional `id`; other commands' `id` positional (`set-status`, `group-<metagroup-type>`, `info-<metainfo-type>`, `set-<user-content-block>`, `delete`, `reorder`, …) match a raw Object ID only, not a Signature or path selector.
- Positional parameters carry the subcommand's own values (an object's `--id` selector, a Name/path, a Status, a metainfo/content/metagroup value, …) — never a file or directory path; every filesystem location is resolved exclusively through `--root` (see "File and Directory Parameters"). Where a subcommand takes more than one positional parameter, the object selector (if any) always comes first.
