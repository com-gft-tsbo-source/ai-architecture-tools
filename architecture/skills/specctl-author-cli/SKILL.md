---
name: specctl-author-cli
description: Use when specctl-author needs CLI commands to initialize a document or create, edit, restructure and delete its draft content. Not for Section status changes or ADR linkage; those belong to specctl-editor-cli.
---

Full spec: `architecture/docs/skills/design-specctl-author-cli.md`.

Invoke specctl from PATH through Bash. You may use init, set-title,
set-preamble, add-part/chapter/section/subsection/point, set-description,
set-open-questions, rename, reorder, move-to-<level>, delete, list and show.
Operate only on draft content. Do not call set-status, set-adr, render or
history, and do not pass inline --adr. Inspect structure with list;
show-metagroups does not exist.

## Conventions and initialization

Use explicit `--root`, never guess. Put `--json` before parsed list/show.
Writes require the 6-character JSON `id`, not Signature; show accepts both.
Exit code 0 means success, 1 means an error on stderr, and 2 means malformed
CLI usage. Calls are independent; partial changes remain after later failure.
Try the first mutating operation that the prompt actually requires. Initialize
and retry only if it exits with code 1 and reports:
`this specctl document has not been initialized yet -- run 'init <title>' first`.
An empty list cannot distinguish an uninitialized store from an initialized
empty document. Do not call init speculatively, since it rejects an already
initialized store. The Agent supplies the Title or defers the whole run.

```
specctl --root <root> init "<Title>" [--preamble "<supplied text>"]
specctl --root <root> set-title "<Title>"
specctl --root <root> set-preamble "<text>"
```

## Create and edit

```
specctl --root <root> add-part "<Part>" [--description "<text>"] [--open-questions "<text>"]
specctl --root <root> add-chapter "<Part>/<Chapter>" [--description "<text>"] [--open-questions "<text>"]
specctl --root <root> add-section "<Part>/<Chapter>/<Section>" [--description "<text>"] [--open-questions "<text>"]
specctl --root <root> add-subsection "<ancestors>/<Subsection>" [--description "<text>"] [--open-questions "<text>"]
specctl --root <root> add-point "<ancestors>/<Point>" [--description "<text>"] [--open-questions "<text>"]
specctl --root <root> set-description <id> "<text>"
specctl --root <root> set-open-questions <id> "<text>"
```

Add --id <value> or --abbrev <code> only when the user specified that ID or
type abbreviation; otherwise specctl generates both. Every ancestor must
exist. Only Parts may sit at root. Intermediate levels may be skipped
(e.g. add-point Part/Chapter/Point), but deeper siblings must precede shallower ones under the same parent.
Add and move append as last child and reject invalid ordering; reorder
also enforces it. Every new Section stays draft.

## Structure, deletion and reads

```
specctl --root <root> rename <id> "<heading>"
specctl --root <root> reorder <id> --after <sibling-number>
specctl --root <root> move-to-chapter <id> "<parent Part>"
specctl --root <root> move-to-part <id>
specctl --root <root> delete <id> [--force-delete]
specctl --root <root> --json list [--status draft] [--under "<path>"]
specctl --root <root> --json show <id> [--history]
```

move-to-<level> takes the PARENT path, never the moving Section's own name;
move-to-part has no path. Pick part/chapter/section/subsection/point for the
resulting level: move changes the Section's depth/type as well as parent,
carries its subtree, and appends last; follow with reorder for placement.
`reorder --after 0` inserts first. Delete with descendants requires
--force-delete ONLY when the user requested the whole subtree.
Browse before additions/restructuring; show creations and confirm deletions
at final verification, as directed by Agent.

## Errors

If ancestors are missing, create the permitted ones and retry. Initialize
and retry only on the specific uninitialized-store error above. Retry an
ID collision on add once. If deletion is rejected because descendants exist
and the user did not request subtree deletion, report the failure rather
than forcing it. Report an unresolvable type-abbreviation collision so the
user can supply --abbrev; never invent one. For other errors, report item
stderr unchanged, avoid blind retries and continue remaining operations.
