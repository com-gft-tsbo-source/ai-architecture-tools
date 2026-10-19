---
name: rulectl-author-cli
description: Wraps the rulectl CLI for the authoring workflow — creating Language/Context/Category metagroups and Rules, and checking a target Category for likely duplicates before adding a new Rule. Use whenever a document is being turned into rulectl Rules (add-language/add-context/add-category, add, list, show, show-metagroups, info-*/set-* corrections). Not for reviewing code against existing Rules (tasklist) — that is a separate, later workflow.
---

Full spec: `architecture/docs/skills/design-rulectl-author-cli.md`.

You operate the `rulectl` CLI (on `PATH`, provided by the
`architecture-tools` plugin's `bin/`) via Bash for the
rule-authoring workflow. This is a reference, not a wrapper script — call
`rulectl` yourself, following the recipes below.

## Scope

Only these operations, because only these are needed to author Rules:

- `add-language`, `add-context`, `add-category` — create metagroup paths.
- `add` — create a Rule.
- `list --category <path>` — read existing Rules under a path, for duplicate
  checking.
- `show`, `show-metagroups` — inspect one Rule, or the declared metagroup
  tree, when the breakdown needs disambiguating, **and** re-read a
  just-created Rule to confirm it actually persisted — the
  local-duplicate representative/fallback loop and the final worklist
  audit both depend on `show <id>` for this, not just disambiguation.
- `info-source`, `info-weight`, `info-tool`, `info-tool-rule`,
  `info-checkable`, `set-description`, `set-procedure` — correct a
  just-created Rule's fields within the same run.

Never call `tasklist`, `history`, `reorder`, `delete`,
`group-<metagroup-type>`, `reindex`, or `set-status` from this Skill — they
belong to workflows this Skill doesn't cover. A Rule you create is left at
its default initial status (`active`); do not touch its status afterward.

## Conventions

- **`--root <path>`**: use exactly the path you were given by whoever
  invoked you. Never hardcode or guess one. A not-yet-existing path is fine
  — `rulectl` creates the store on first use.
- **`--json`**: always pass it when you're going to parse the output
  (`list`, `show`, `show-metagroups`). Parse the JSON; never scrape the
  human-readable format.
- **Exit codes**: `0` = ok, `1` = error, error text on stderr. Check the
  exit code to decide success — don't infer it from stderr being non-empty
  (there is none on success) or empty.
- Each `rulectl` call is independent — there's no transaction. If a
  multi-step change fails partway, whatever was created before the failure
  stays created.

## Recipes

**Create a metagroup path** — every level must exist before the next is
created under it or referenced by a Rule:

```
rulectl --root <root> add-language <name>
rulectl --root <root> add-context <language>/<context-name>
rulectl --root <root> add-category <language>/<context-name>/<category-name>
```

A segment may be a bare name (auto-numbered) or an explicit `<nr>-<name>`.
Referencing a path before it exists aborts with an error — nothing is
auto-created as a side effect.

**Create a Rule**, once its Category exists:

```
rulectl --root <root> add --category <language>/<context>/<category> \
  --name "<short name>" --description "<description text>" \
  [--procedure "<procedure text>"] \
  [--source "<traceability note>"] \
  [--checkable llm|<tool-name>] \
  [--tool <tool-name> --tool-rule <rule-id>] \
  [--weight <free text>]
```

No flag exists to create it as `draft` — it is always `active` on creation
by design; don't try to work around that.

**Check for duplicates before creating a Rule**, against its target
Category:

```
rulectl --root <root> --json list --category <language>/<context>/<category>
```

Compare the returned Rules' Names/Descriptions against the candidate. A
Category filter includes descendants too, so scope it to the most specific
level you have — a Language- or Context-level filter over-matches.

## Error handling

- **Unknown metagroup path**: create the missing ancestor segment(s) first
  (see "Create a metagroup path"), then retry. This is a missed
  prerequisite, not a reason to abort the whole run.
- **Object ID collision** on `add`: retry once — `rulectl` regenerates the
  ID from content each time; a repeat collision is not expected.
- **Any other failure**: report the stderr text as-is for that one item, and
  move on to the next Rule/metagroup rather than stopping the run.
