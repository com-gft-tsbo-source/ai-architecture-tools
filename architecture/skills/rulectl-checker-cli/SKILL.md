---
name: rulectl-checker-cli
description: Use when rulectl-checker needs to refresh its exported compliance Tasklist and record taskctl check outcomes. Covers snapshot selection, claims, annotations, reviews and verification; not for authoring Rules, executing ordinary Tasks or searching the codebase itself.
---

Full spec: `architecture/docs/skills/design-rulectl-checker-cli.md`.

Invoke rulectl and taskctl from PATH through Bash. The permitted operations
are rulectl tasklist and taskctl annotate, info-review user, set-status
with ~, X, R or B, and show. Do not use other CLI operations, including
taskctl list/next, authoring or maintenance commands.
Use the same explicit `--root` for both tools. Put `--json` before tasklist
and show when parsing their output; omit it on writes. Exit code 0 means
success and exit code 1 means an error.

## Refresh and claim

```
rulectl --root <root> --json tasklist [--language <path> | --context <path> | --category <path>]
```

At most one filter; absent means all Rules. Require success and a JSON
array of exported Tasks; its exact IDs are the fixed work set. Failure or
malformed output stops BEFORE Task writes. Never widen/rederive via list/next.
Export resets every in-scope active Rule Task to open and review=none,
including previous X/R/B checks; every run rechecks them.

For each snapshot ID:

```
taskctl --root <root> set-status <id> "~" --message "checking"
```

If the claim fails, do not examine, annotate or set an outcome for that
Task. Report the failure and continue with the next snapshot ID. A successful claim precedes all outcomes.
The Agent performs the check and chooses the verdict.

## Record and verify

Always annotate plan, actual evidence examined and applicability:

```
taskctl --root <root> annotate <id> --message "<plan, evidence, applicability>"
```

Then one outcome:

| Agent verdict | Command after annotation |
|---|---|
| Compliant | `taskctl --root <root> set-status <id> X --message "compliant"` |
| Violated | `taskctl --root <root> info-review <id> user`, THEN `taskctl --root <root> set-status <id> R --message "<actionable violation>"` |
| Can't check | `taskctl --root <root> set-status <id> B --message "<reason>"` |

Set review before transitioning to R because the validator uses its current
value to choose the permitted status path. Blocking requires a reason,
regardless of review. Never use --force. If a check or tool fails after
claiming, record it as uncheckable and continue with remaining IDs. Other write errors: report stderr per Task and continue,
without labeling failed writes successful or touching finalized Tasks.
At snapshot end re-read EVERY ID, including failed claims:

```
taskctl --root <root> --json show <id>
```

Classify the persisted status as compliant for X, user review for R and
blocked for B. Any other status or a failed show belongs in
`not successfully finalized`. Snapshot exhaustion is the
normal stop; source inspection and verdict evidence belong to the Agent.
