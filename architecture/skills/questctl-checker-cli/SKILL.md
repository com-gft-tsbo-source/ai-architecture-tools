---
name: questctl-checker-cli
description: Use when questctl-checker needs to select open Questions, claim them and record verbatim answer attributions with review or error outcomes. Not for authoring Questions, synthesizing answers or searching the answer-source itself.
---

Full spec: `architecture/docs/skills/design-questctl-checker-cli.md`.

You operate `questctl` via Bash, using only the operations below.
The calling Agent decides passage attribution and confidence.

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
questctl --root <root> set-status <id> "~" --message "checking against <source>"
```

The caller must serialize runs per root, even across disjoint scopes.
Selection and claims are separate CLI calls, so the snapshot is not a lock.
In sequential mode, claim only after finding an answer: an in-progress
Question closes the store-wide selection gate. Delaying the claim keeps
that window short. A Question without an answer stays open, so calling
`next` again would return it repeatedly; advance through the snapshot instead.

## Record the outcome

For a no-match outcome, annotate what source was searched.

```
questctl --root <root> annotate <id> --message "<source searched, no matching passage found>"
```

**No matching passage:** in sequential mode, leave status `[ ]` and advance to
the next snapshot ID. In parallel mode the Question is already claimed:

```
questctl --root <root> set-status <id> B --message "<why no answer is supported>"
```

**Answer supported:** after a successful claim (skip claiming if already
claimed in parallel mode), record the answer:

```
questctl --root <root> answer <id> "<verbatim source passage(s), unchanged>" --message "<source/section>"
```

For a confident answer:

```
questctl --root <root> set-status <id> X --message "<evidence for confidence>"
```

For uncertain attribution, set review before transitioning. The status
validator uses the current review value to determine the permitted path:

```
questctl --root <root> info-review <id> user
questctl --root <root> set-status <id> R --message "<reason for uncertainty>"
```

A passage may answer several Questions in the snapshot. Record each genuine attribution independently, preserving the source wording.

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
answer-source.
