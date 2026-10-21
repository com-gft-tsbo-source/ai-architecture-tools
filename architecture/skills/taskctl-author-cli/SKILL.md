---
name: taskctl-author-cli
description: Use when taskctl-author needs to create or extend Phases and Tasks, correct new Task fields, or restructure and delete confirmed targets. Not for selecting execution work, annotating progress or setting outcomes; those belong to taskctl-worker-cli.
---

Full spec: `architecture/docs/skills/design-taskctl-author-cli.md`.

Use `taskctl` from PATH via Bash. Use only operations below; the calling
Agent controls planning, deletion confirmation and ordering judgments.

## Conventions

Use exactly the supplied `--root`; absent stores initialize on first use.
Put `--json` before read commands whose output you parse, rather than scraping
human-readable output. Exit code 0 means success; exit code 1 reports an error
on stderr; exit code 2 means malformed CLI usage. Calls are independent; earlier writes are not rolled back.
A store uses Phases or stays flat, never both. Segments may be bare
(auto-numbered) or explicit `<nr>-<name>`.

## Commands

```
taskctl --root <root> add-phase <name>
taskctl --root <root> add --name "<name>" --description "<work>" \
  [--phase <path>] [--review none|user|subagent] \
  [--assignee-type <value>] [--assignee-name <value>] [--source "<origin>"] \
  [--set-status <code>]
taskctl --root <root> --json list [--phase <path>] [--status <value>]
taskctl --root <root> --json show <id> [--history]
taskctl --root <root> --json show-metagroups
```

Phase is required in Phase stores and omitted in flat stores. Inspect
Tasks/Phases before extension and show every believed creation at run end.
`--set-status` is an initial-value override for imports, not an execution
transition; taskctl-author never uses it for newly planned work.

Correct newly created Task fields within the run:

```
taskctl --root <root> set-description <id> "<work>"
taskctl --root <root> info-review <id> none|user|subagent
taskctl --root <root> info-assignee-type <id> <value>
taskctl --root <root> info-assignee-name <id> <value>
taskctl --root <root> info-source <id> "<origin>"
```

Restructure/delete existing Tasks only as the Agent directs:

```
taskctl --root <root> group-phase <id> <phase-path>
taskctl --root <root> reorder <id> --after <sibling-number>
taskctl --root <root> delete <id>
```

Leave `origin` unset, including for agent/tool assignments. Never fabricate
reserved `origin=rulectl:<rule-id>` export provenance.

## Errors and limits

If a Phase is unknown, create it and retry. Retry an ID collision on add
once. For other failures, report the item's stderr and continue remaining
Tasks and Phases. Do not call annotate, next, standalone set-status,
reindex or history.
