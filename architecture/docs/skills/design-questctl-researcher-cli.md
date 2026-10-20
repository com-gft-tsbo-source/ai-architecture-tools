# questctl-researcher-cli

CLI contract for `questctl-researcher`, implemented by its paired `SKILL.md`.

You operate `questctl` via Bash, using only the operations below.
The calling Agent decides research scope and evidence sufficiency.

## Scope and conventions

- Allowed: `next-all`, `show`, `annotate`, `set-status`, `answer`, `info-review`.
- Use the explicitly supplied `--root` for every call. Use `--json` before
  `next-all` and `show`; parse JSON rather than human-readable output.
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

Claims and snapshot selection are not atomic. The caller must serialize
runs per whole `--root`, even for disjoint scopes.

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

For thin or ambiguous evidence, set review before transitioning:

```
questctl --root <root> info-review <id> user
questctl --root <root> set-status <id> R --message "<reason for uncertainty>"
```

Never fabricate an answer to close a Question. Evidence sufficiency and uncertainty are judgments governed by the Agent.

## Errors and verification

Stop on an initial snapshot error or malformed output before writing.
A failed claim permits no answer or further mutation of that Question.
For a per-Question failure before claiming, report it and advance once.
After a successful claim, try to resolve a write failure to `[B]` with its
reason. If that fails too, stop processing further IDs and report the
unfinished claims and unvisited IDs; never label a failed write successful.

Snapshot exhaustion ends the run normally, even with Questions still open.
Re-read every touched ID with `show` and report actual status, answer,
errors, skipped conflicts, and the stop reason. Never infer `all_answered`
from snapshot exhaustion. Other than reading/searching the supplied
bounded Datenbasis (no live web search), source handling belongs to the Agent.
