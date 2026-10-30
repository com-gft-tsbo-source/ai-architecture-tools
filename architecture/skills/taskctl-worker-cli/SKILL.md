---
name: taskctl-worker-cli
description: Use when taskctl-worker needs to select, claim or resume existing Tasks and record progress, review, completion or blocking. Not for creating, restructuring, deleting or reassigning Tasks, or for deciding how to perform their work.
---

Full spec: `architecture/docs/skills/design-taskctl-worker-cli.md`.

Invoke taskctl from PATH through Bash. You may use next, set-status,
annotate, show, and info-review immediately before an authorized outcome
transition. Do not author, restructure, delete or reassign Tasks, set origin,
browse with list/show-metagroups, or call reindex/history. Mutate only the ID
most recently returned by next, and never use --force. Use exactly the
supplied --root. Put --json before next/show and omit it on writes.
Exit code 0 means success; exit code 1 means an error.

taskctl guards reject skipping past unresolved earlier Tasks and deciding a
user review yourself (`[R]`→X, review changes while in R/C, lowering review
from user). With --json their output is `{"reason": "sequence_blocked" |
"approval_required", ...}`. Do not work around a rejection: stop and report
it to the user. Add `--user-approved "<the user's instruction>"` to a write
only when the user explicitly instructed that exact operation for THIS Task;
it is recorded in History. Never supply it on your own judgment.

## Select, claim, resume and stop

```
taskctl --root <root> --json next
```

By default, work one Task to its resting point and stop. Repeat next after
a Task only if the prompt explicitly requests a loop; stop at all_done or
a Task in B, R or C. Selection follows the global queue, so a Phase or
assignee request cannot bypass earlier unresolved work.

- Open (`" "`): claim before working. If claim fails, do not annotate,
  set outcome or advance to another Task; report the error.
- In progress (`"~"`): resume, do not reclaim; read History.
- If the status is B, R or C, the Task is an unresolved blocker. Do no work
  and stop.
- If next exits with code 1 and JSON reason `all_done` (NoWorkAvailable),
  the queue is drained. Other failures are genuine errors.

```
taskctl --root <root> set-status <id> "~" --message "starting"
taskctl --root <root> --json show <id> --history
```

Before claim, the Agent checks origin: open/in-progress rulectl exports
may be blocked directly with the routing reason, without claim/annotation.
Assignee does not establish provenance; legacy marker repair is outside
this Skill. Ordinary Task work happens outside taskctl.

## Record an outcome

After work, ALWAYS annotate actual work/evidence (except the export-routing
exception), then any authorized review change, then outcome:

```
taskctl --root <root> annotate <id> --message "<actual work/evidence>"
taskctl --root <root> set-status <id> X --message "<completion evidence>"
```

For review, check current review via show; info-review is needed only if
it does not already cover the target. It must precede the transition:

```
taskctl --root <root> info-review <id> user
taskctl --root <root> set-status <id> R --message "<reason>"
```

For subagent review, use `subagent` with info-review and `C` with
set-status instead of `user` and `R`. Existing reviews
remain required. Only an explicit user instruction for THIS Task permits
removing a review; annotate that instruction/reason before. Lowering a
`user` review requires the instruction as approval:

```
taskctl --root <root> info-review <id> none --user-approved "<user's instruction>"
taskctl --root <root> set-status <id> X --message "<user-authorized removal; completion evidence>"
```

If the user explicitly accepts a Task waiting in R, record their verdict:

```
taskctl --root <root> set-status <id> X --user-approved "<user's instruction>" --message "<verdict>"
```

Never remove review for remote-action Tasks. To block, no review change needed:

```
taskctl --root <root> set-status <id> B --message "<reason>"
```

The Agent decides remote-action approval from History; pending/prepared
and executed remote actions both return R, never X. Resume does not itself
prove approval. Review→in-progress is user rework/approval, not a worker-
initiated bypass; read History as required above.

## Verification and errors

At the end of the run, re-read every touched ID with --json show and report
the actual state and any mismatch with the intended writes. After a successful claim, report any nonzero write's
stderr for that Task without corrupting finalized Tasks. Evidence sufficiency,
remote-action approval judgment and final report content belong to Agent.
