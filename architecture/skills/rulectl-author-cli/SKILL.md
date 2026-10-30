---
name: rulectl-author-cli
description: Use when rulectl-author needs the CLI syntax for creating metagroups and Rules, checking exact-target duplicates or correcting newly created Rules. Not for code compliance checks, Tasklist exports or changing Rule status.
---

Full spec: `architecture/docs/skills/design-rulectl-author-cli.md`.

Use `rulectl` from PATH via Bash. Only the operations below are allowed;
content, grouping and duplicate judgments belong to the calling Agent.

## Conventions

Use exactly the supplied `--root`; a missing store is created on first use.
Put `--json` BEFORE read commands whose output you parse; never scrape
human output. Exit code 0 means success; exit code 1 means an error reported
on stderr; exit code 2 means malformed CLI usage. Judge success by the exit code rather than stderr presence.
Each call is independent; earlier writes are not rolled back if a later call fails.

## Commands

Create ancestors before descendants/Rules. A path segment may be a bare
auto-numbered name or explicit `<nr>-<name>`; paths are not auto-created.

```
rulectl --root <root> add-language <name>
rulectl --root <root> add-context <language>/<context>
rulectl --root <root> add-category <language>/<context>/<category>
rulectl --root <root> add --category <language>/<context>/<category> \
  --name "<short name>" --description "<requirement>" \
  [--procedure "<verification steps>"] [--source "<origin>"] \
  [--checkable llm|<tool-name>] [--tool <tool-name> --tool-rule <rule-id>] \
  [--weight "<explicit severity>"]
rulectl --root <root> --json list --category <language>/<context>/<category>
rulectl --root <root> --json show <id>
rulectl --root <root> --json show-metagroups
```

List before each candidate creation to compare existing Names/Descriptions.
Category filters include descendants: use the exact most-specific target,
not a broader Language/Context. `show` supports both the immediate duplicate-
representative verification and the separate final audit, as directed by Agent.
New Rules are always active. No creation-as-draft flag exists, and this
workflow does not permit later status changes.

Same-run corrections to newly created Rules only:

```
rulectl --root <root> set-description <id> "<text>"
rulectl --root <root> set-procedure <id> "<text>"
rulectl --root <root> info-source <id> "<origin>"
rulectl --root <root> info-weight <id> "<severity>"
rulectl --root <root> info-checkable <id> llm|<tool-name>
rulectl --root <root> info-tool <id> <tool-name>
rulectl --root <root> info-tool-rule <id> <rule-id>
```

## Errors and limits

If a path is missing, create the permitted ancestors and retry, respecting
the Agent's Language gate. Retry an ID collision on add once. For any other
failure, report that item's stderr unchanged and continue remaining items.
Do not call tasklist, history, reorder, delete, regroup, reindex or set-status.
