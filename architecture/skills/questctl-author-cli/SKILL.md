---
name: questctl-author-cli
description: Use when questctl-author needs to detect store depth, create a confirmed taxonomy, add Questions or inspect duplicates. Not for recording answers, selecting Questions for processing or changing their execution status.
---

Full spec: `architecture/docs/skills/design-questctl-author-cli.md`.

Use `questctl` from PATH via Bash. Allowed operations are listed below;
the calling Agent decides extraction, taxonomy confirmation and duplicates.

## Conventions and depth detection

Use exactly the supplied `--root`; an absent store initializes on first use.
Put `--json` before read commands whose output you parse, and do not scrape
human-readable output. Exit code 0 means success; exit code 1 means an
error reported on stderr. Judge success by exit code, not stderr presence.
Calls are independent; earlier writes survive a later failure.

Before taxonomy proposal, combine these reads:

```
questctl --root <root> --json list
questctl --root <root> --json show-metagroups
```

If any Question exists, its `metagroup` array length is established depth
0/1/2 for the whole store. Otherwise a two-segment metagroup path establishes
2 even without Questions. Otherwise depth is not established. The Agent
chooses/reconciles the complete taxonomy; at depth 0 create no metagroups.

## Commands

Create only confirmed taxonomy nodes, parents first. Segments may be bare
auto-numbered names or explicit `<nr>-<name>`.

```
questctl --root <root> add-group <group>
questctl --root <root> add-subgroup <group>/<subgroup>
questctl --root <root> add --group <group> --name "<name>" \
  --description "<question>" --source "<origin>"
```

At depth 2 replace `--group` with `--subgroup <group>/<subgroup>`; at depth 0
omit both. Keep initial open status and review/assignee fields unset;
this workflow never overrides them. No Answer/Procedure is authored here.

Before each creation, read duplicates at its exact target depth:

```
questctl --root <root> --json list --group <group>
questctl --root <root> --json list --subgroup <group>/<subgroup>
questctl --root <root> --json show <id>
```

At depth 0 use unfiltered list. Group filters include Subgroup descendants;
use Subgroup for a depth-2 candidate. Compare Names/Descriptions.
Use show for immediate representative verification AND separate final audit.
Correct only newly created Questions within the same run:

```
questctl --root <root> info-source <id> "<origin>"
questctl --root <root> set-description <id> "<question>"
```

## Errors and limits

If a path is unknown, create the permitted missing ancestors and retry.
If a depth rejection says `this store is fixed at metagroup depth ...`,
read the current depth again and reconcile the taxonomy before retrying;
there is no force override. Retry an ID collision on add once. Report
other item failures with stderr and continue remaining items.
Do not answer, annotate, select work with next/next-all, change status,
review or assignees, or call delete, reorder, regroup, reindex or history.
