---
name: questctl-researcher-cli
description: Use when questctl-researcher needs to select open Questions, record research traces and synthesized answers, and set supported, uncertain or blocked outcomes. Not for authoring Questions, attributing passages verbatim or conducting the research itself.
---

Full spec: `architecture/docs/skills/design-questctl-researcher-cli.md`.

You operate `questctl` via Bash, using only the operations below.
The calling Agent decides research scope and evidence sufficiency.

## Scope and conventions

- Allowed: `next-all`, `show`, `annotate`, `set-status`, `answer`, `info-review`.
- Use exactly the supplied `--root`. Put `--json` before `next-all` and
  `show` when parsing their output. Invoke questctl from PATH through Bash;
  no operations beyond the allow-list are permitted.
- Exit `0` means success, `1` means error or no work. On initial
  `next-all`, `all_answered`/`awaiting_interaction` means no available work;
  `in_progress` means another run is active: defer without writes.
- Never use `--force`, `next`, authoring, deletion, or regrouping commands.

## Snapshot and claims

Read the ordered work set exactly once at run start:

```
questctl --root <root> --json next-all [--group <path> | --subgroup <path>]
```

**Sequential (default):** scope is optional. Keep the returned IDs and
process each at most once in order. `next-all` does not claim anything.
Before examining an ID, `show` it and require status `[ ]`; otherwise skip
and report the changed state. Search first; claim only if recording an answer.
An unanswered Question stays open and does not prevent visiting later IDs.
Never refresh the snapshot or loop through `next`.

**Parallel (explicit request, named scope required):** use exactly that
scope and claim the batch up front, one `set-status ~` per ID. Track only
successful claims; skip/report failed claims without answering or mutating
them further. Before examining a claimed ID, `show` and require `[~]`.
Then process the successfully claimed batch individually.

```
questctl --root <root> --json show <id>
questctl --root <root> set-status <id> "~" --message "researching"
```

The caller must serialize runs per root, even across disjoint scopes.
Selection and claims are separate CLI calls, so the snapshot is not a lock.
In sequential mode, claim only after finding an answer: an in-progress
Question closes the store-wide selection gate. Delaying the claim keeps
that window short. A Question without an answer stays open, so calling
`next` again would return it repeatedly; advance through the snapshot instead.

## Record the outcome

Always annotate the research plan and evidence examined before recording an answer or moving on.

```
questctl --root <root> annotate <id> --message "<research plan, sources examined, why>"
```

**No usable evidence:** in sequential mode, leave status `[ ]` and advance to
the next snapshot ID. In parallel mode the Question is already claimed:

```
questctl --root <root> set-status <id> B --message "<why no answer is supported>"
```

**Answer supported:** after a successful claim (skip claiming if already
claimed in parallel mode), record the answer:

```
questctl --root <root> answer <id> "<synthesized answer; state uncertainty if provisional>" --message "<source/section>"
```

For a confident answer:

```
questctl --root <root> set-status <id> X --message "<evidence for confidence>"
```

For thin or ambiguous evidence, set review before transitioning. The status
validator uses the current review value to determine the permitted path:

```
questctl --root <root> info-review <id> user
questctl --root <root> set-status <id> R --message "<reason for uncertainty>"
```

Never fabricate an answer to close a Question. Evidence sufficiency and uncertainty are judgments governed by the Agent.

## Errors and verification

If the initial snapshot command fails or returns malformed output, stop
before writing. If a claim fails, do not answer or further mutate that
Question. For other item failures before claiming, report the failure and
advance once to the next snapshot ID.
After a successful claim, try to resolve a write failure to `[B]` with its
reason. If that fails too, stop processing further IDs and report the
unfinished claims and unvisited IDs; never label a failed write successful.

When the snapshot is exhausted or the run stops with an error, use show
for every touched ID. Report actual status and Answer, errors, conflicts
and the stop reason. Exhausting the snapshot does not imply all_answered.
The Agent is responsible for reading and searching the supplied
bounded Datenbasis; this workflow does not permit live web research.
