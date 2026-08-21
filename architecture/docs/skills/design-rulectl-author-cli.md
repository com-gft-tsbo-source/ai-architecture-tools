# rulectl-author-cli

Skill that wraps the `rulectl` CLI for the `rulectl-author` Subagent
(`architecture/docs/subagents/design-rulectl-author.md`). Purely an
instructional reference — a `SKILL.md`, no executable wrapper code. The
invoking agent calls the `rulectl` binary itself via Bash; this Skill only
teaches it how to do that correctly for the authoring workflow.

## Scope

Covers only the `rulectl` operations the authoring workflow needs:

- `add-language`, `add-context`, `add-category` — create metagroup paths.
- `add` (with inline `--language`/`--context`/`--category` and
  `--source`/`--weight`/`--tool`/`--tool-rule`/`--checkable`, `--description`,
  `--procedure`) — create a Rule.
- `list --category <path>` — read existing Rules under a candidate path, for
  duplicate detection before `add`.
- `show`, `show-metagroups` — inspect a specific Rule or the declared
  metagroup tree when the extracted breakdown needs disambiguating.
- `info-source`, `info-weight`, `info-tool`, `info-tool-rule`,
  `info-checkable`, `set-description`, `set-procedure` — correct a
  just-created Rule's fields within the same run (e.g. a duplicate check that
  only becomes possible after seeing the Description).

Not in scope (not used by this workflow, so not documented here):
`tasklist`, `history`, `reorder`, `delete`, `group-<metagroup-type>`,
`reindex`, and any `set-status` beyond the implicit default. A Rule created
by this workflow is always left at its default initial status (`active`) —
this Skill never calls `set-status`.

## Invocation conventions

- `--root <path>`: always supplied by the caller (the `rulectl-author`
  Subagent receives it from whoever invoked it — user or orchestrating
  Skill). Never hardcode or guess a root; `rulectl` auto-creates the store on
  first use if it doesn't exist yet, so a not-yet-existing path is not an
  error.
- `--json`: always pass this flag when the output needs to be parsed
  programmatically (`list`, `show`, `show-metagroups`) — do not scrape the
  human-readable format.
- Exit codes: `0` = ok, `1` = error. Error text goes to stderr. Check the
  exit code, not the presence of stderr output, to decide whether an
  operation succeeded.
- Every operation is a single, independent `rulectl` invocation — there is no
  batch/transaction mode. A multi-step change (e.g. "create a Category, then
  add three Rules under it") is several sequential CLI calls; if one fails
  partway, whatever was already created before the failure remains.

## Operation recipes

**Creating a metagroup path.** Each level must exist before the next is
created under it, and before any Rule references it:

```
rulectl --root <root> add-language <name>
rulectl --root <root> add-context <language>/<context-name>
rulectl --root <root> add-category <language>/<context-name>/<category-name>
```

A segment may be given as a bare name (an auto-assigned `<nr>-` prefix is
added) or as an explicit `<nr>-<name>`. Referencing a path that doesn't exist
yet (in `add`, or in any of the above) aborts with an error — metagroup paths
are never auto-created as a side effect.

**Creating a Rule**, once its Category path exists:

```
rulectl --root <root> add --category <language>/<context>/<category> \
  --name "<short name>" --description "<description text>" \
  [--procedure "<procedure text>"] \
  [--source "<traceability note>"] \
  [--checkable llm|<tool-name>] \
  [--tool <tool-name> --tool-rule <rule-id>] \
  [--weight <free text>]
```

The Rule is created at status `active` by default — no flag is needed or
available to create it as `draft` (`design-rulectl.md`, "Status"); this
workflow relies on that default and never overrides it.

**Duplicate check before creating a Rule**, against the candidate Category:

```
rulectl --root <root> --json list --category <language>/<context>/<category>
```

Read the returned Rules' Names/Descriptions and judge similarity against the
Rule about to be created. `list` with a Category filter includes everything
at or below that path, not just an exact match — this over-matches
(descendant Contexts too) whenever the target is actually a Language or
Context level, so scope the filter to the most specific level available.

## Error handling

- **Unknown metagroup path** (`add --category <path>` where `<path>` isn't
  declared yet, or the path's own parent segment doesn't exist): create the
  missing ancestor segments first (see "Creating a metagroup path"), then
  retry the original operation. Never treat this as a fatal error for the
  overall run — it means a prerequisite step was skipped, not that the
  operation itself is invalid.
- **Object ID collision** on `add`: astronomically unlikely with generated
  IDs (design.md, "Object ID"); if it happens anyway, retry once — `rulectl`
  regenerates the ID from content on each attempt.
- Any other non-zero exit: surface the stderr text as-is in the Subagent's
  final report for that one Rule/metagroup; do not retry blindly, and do not
  let one failed item abort the whole run — continue with the remaining
  extracted Rules.

## Out of scope

This Skill does not cover reviewing a codebase against Rules (`tasklist` and
everything downstream of it) — that belongs to the future rule-checking
Subagent and its own wrapping Skill.
