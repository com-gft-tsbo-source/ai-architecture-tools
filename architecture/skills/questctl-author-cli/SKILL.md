---
name: questctl-author-cli
description: Wraps the questctl CLI for the authoring workflow — detecting a store's established metagroup depth, creating Group/Subgroup metagroups, creating Questions, and checking a target Group/Subgroup for likely duplicates before adding a new Question. Use whenever a document (or a directory of documents) is being turned into questctl Questions (add-group/add-subgroup, add, list, show, show-metagroups, info-source/set-description corrections). Not for matching answers to existing Questions (answer/annotate) or researching answers (next/next-all) — those are separate, later workflows.
---

Full spec: `architecture/docs/skills/design-questctl-author-cli.md`.

You operate the `questctl` CLI (on `PATH`, provided by the
`architecture-tools` plugin's `bin/`) via Bash for the
question-authoring workflow. This is a reference, not a wrapper script —
call `questctl` yourself, following the recipes below.

## Scope

Only these operations, because only these are needed to author Questions:

- `list`, `show-metagroups` — **detect the store's established metagroup
  depth** before proposing a taxonomy (see "Detecting the established
  depth"). No `rulectl` equivalent — `rulectl`'s depth is fixed per tool,
  never a whole-store property to detect.
- `add-group`, `add-subgroup` — create the confirmed taxonomy's metagroup
  paths.
- `add` — create a Question.
- `list --group <path>` / `list --subgroup <path>` — read existing
  Questions under a candidate node, for duplicate checking.
- `show`, `show-metagroups` — inspect one Question or the declared
  taxonomy when disambiguating, **and** re-read a just-created Question to
  confirm it actually persisted — the local-duplicate representative/
  fallback loop and the final worklist audit both depend on `show <id>`
  for this, not just disambiguation.
- `info-source`, `set-description` — correct a just-created Question's
  fields within the same run.

Never call `answer`, `annotate`, `next`, `next-all`, `set-status`,
`info-review`, `info-assignee-type`, `info-assignee-name`, `history`,
`reorder`, `delete`, `group-<metagroup-type>`, or `reindex` from this
Skill — they belong to workflows this Skill doesn't cover (matching or
researching answers). A Question you create is left at its default
initial status (`[ ]`), with `review`/`assignee-type`/`assignee-name`
unset; do not touch those — the Author doesn't know yet whether a Question
will end up matched or researched, so setting them now is guessing at a
fact only that later step actually knows.

## Conventions

- **`--root <path>`**: use exactly the path you were given by whoever
  invoked you. Never hardcode or guess one. A not-yet-existing path is
  fine — `questctl` creates the store on first use.
- **`--json`**: always pass it when you're going to parse the output
  (`list`, `show`, `show-metagroups`). Parse the JSON; never scrape the
  human-readable format.
- **Exit codes**: `0` = ok, `1` = error, error text on stderr. Check the
  exit code, not stderr's presence.
- Each `questctl` call is independent — there's no transaction. If a
  multi-step change fails partway, whatever was created before the failure
  stays created.

## Detecting the established depth

Before proposing a taxonomy, determine whether the target store already
has a fixed metagroup depth — no single command reports this directly,
combine two read-only calls:

```
questctl --root <root> --json list
questctl --root <root> --json show-metagroups
```

- `list` returns any Question → its `"metagroup"` array's length **is**
  the established depth (`0`, `1`, or `2`) — every Question in a store
  shares the same depth, so the first one found is representative.
- Otherwise, `show-metagroups` returns a path with **two** segments →
  depth `2` is established even with no Question there yet (only reachable
  via a prior `add-subgroup`, which is unambiguous).
- Otherwise → depth is **not yet established**; this run is free to
  choose (propose depth 2 only if every Group in your taxonomy has genuine
  sub-structure, else flatten the whole thing to depth 1 — never a mix).

## Recipes

**Create the confirmed taxonomy**, once the batched taxonomy confirmation
has an answer — each Group before any Subgroup under it:

```
questctl --root <root> add-group <name>
questctl --root <root> add-subgroup <group-name>/<subgroup-name>
```

A segment may be a bare name (auto-numbered) or an explicit `<nr>-<name>`.
If the store is already established at depth 0, **skip this recipe
entirely** — no Group/Subgroup is ever created there.

**Create a Question**, once its target node exists (or, at depth 0, with
no node at all):

```
questctl --root <root> add --group <group-name> \
  --name "<short name>" --description "<question text>" \
  --source "<traceability note>"
```

Use `--subgroup <group-name>/<subgroup-name>` instead of `--group` for a
depth-2 target. For a depth-0 store, omit both — `add` with neither flag
is exactly how a depth-0 Question is created, not an error. Created at
status `[ ]` by default; no flag exists to create it any other way, and
this workflow never overrides it.

**Check for duplicates before creating a Question**, against its target
node:

```
questctl --root <root> --json list --group <group-name>
questctl --root <root> --json list --subgroup <group-name>/<subgroup-name>
```

Use whichever matches the candidate's actual target depth. Compare the
returned Questions' Names/Descriptions against the candidate. Like
`rulectl`'s `list --category`, a `--group` filter over-matches everything
underneath (every Subgroup too) — scope to `--subgroup` whenever the
candidate's real target is a Subgroup.

## Error handling

- **Unknown metagroup path**: create the missing segment(s) first (see
  "Recipes"), then retry. A missed prerequisite, not a reason to abort the
  run.
- **Depth rejection** (`add`/`add-group`/`add-subgroup` failing with "this
  store is fixed at metagroup depth ..."): your depth-detection was run
  against stale information, or the taxonomy wasn't reconciled against the
  established depth before creating — re-derive the depth (see "Detecting
  the established depth") and reconcile before retrying. Never `--force`
  this — there is no `--force` for a metagroup depth violation.
- **Object ID collision** on `add`: retry once — `questctl` regenerates
  the ID from content each time; a repeat collision is not expected.
- **Any other failure**: report the stderr text as-is for that one
  Question/metagroup node, and move on to the next rather than stopping
  the run.
