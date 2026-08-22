# questctl-researcher-cli

Skill that wraps the `questctl` CLI for the `questctl-researcher` Subagent (`architecture/docs/subagents/design-questctl-researcher.md`). Purely an instructional reference — a `SKILL.md`, no executable wrapper code. The invoking agent calls `questctl` itself via Bash; this Skill only teaches it how to do that correctly for the answer-research workflow. Nearly identical in shape to `questctl-checker-cli` (design-questctl-checker-cli.md) — both agents claim, resolve, and verify Questions the same way; only *what* justifies each outcome differs (attribution vs. synthesized research), which is the Subagent's own judgment, not a CLI concern.

## Scope

- `next [--group <path> | --subgroup <path>]` / `next-all [--group <path> | --subgroup <path>]` — work-selection, sequential and parallel respectively (see "Recipes").
- `set-status <id> <code> --message <text>` — `~` (claim), `X` (confident, well-supported answer), `R` (answer possible, evidence thin), `B` (parallel-mode-only: claimed but no usable evidence).
- `info-review <id> user` — switch a Question's review mode immediately before escalating it to `R` (see "Status transitions").
- `answer <id> <text> --message <text>` — record the synthesized answer.
- `annotate <id> --message <text>` — record the research plan/scope/sources examined, for **every** Question this run touches, regardless of outcome (design-questctl-researcher.md, "Workflow", step 3) — unlike `questctl-checker-cli`, where `annotate` is only used for the no-match case.
- `show <id>` — re-read a Question's actual persisted state.

Not in scope: `add`, `add-group`, `add-subgroup`, `set-description`, `info-source`, `delete`, `reorder`, `group-<metagroup-type>`, `reindex` — authoring is `questctl-author-cli`'s job.

## Conventions

Identical to `questctl-checker-cli`: `--root <path>` shared across a run; `--json` on `next`/`next-all`/`show` only; exit codes `0`/`1`, including `next`/`next-all`'s three `reason`-bearing "nothing available" cases.

## Recipes

**Sequential mode (default) — one Question at a time:**

```
questctl --root <root> --json next [--group <path> | --subgroup <path>]
```

Parse the returned Question. Set a research plan and examine the Datenbasis (Read/Glob/Grep for a local file/directory, `WebFetch`/fallback `curl` for a URL — the Subagent's own work, not a `questctl` operation) *before* claiming — same "search first, claim only once there's something to record" rationale as `questctl-checker-cli`'s "Claim timing".

**Always record the research trace first, whatever the outcome:**
```
questctl --root <root> annotate <id> --message "<plan, sources examined, why>"
```

*No usable evidence found:* stop here — do **not** call `set-status`. Loop back to `next`.

*Confident, well-supported answer:*
```
questctl --root <root> set-status <id> "~" --message "researching"
questctl --root <root> answer <id> "<synthesized answer>" --message "<short pointer, e.g. source/section>"
questctl --root <root> set-status <id> X --message "well-supported by <source>"
```

*Answer possible, evidence thin* — write the answer with its own uncertainty stated in the text (not just the status), then:
```
questctl --root <root> set-status <id> "~" --message "researching"
questctl --root <root> answer <id> "<answer, uncertainty stated in the text>" --message "<what's missing/ambiguous>"
questctl --root <root> info-review <id> user
questctl --root <root> set-status <id> R --message "<why the evidence is thin>"
```
`info-review` must run **before** `set-status ... R` — it switches the Question's forward path so `[~]→R` becomes a normal, on-path step (verified against `lib/taskctl_spec.py`'s `validate_transition`, reused directly by questctl: it reads the Question's *current* `review` metainfo at the moment of the transition, not one fixed at creation). Without it, `[~]→R` is off-path and fails without `--force`.

**Parallel mode (only when the caller explicitly asked for it, naming a scope):**

```
questctl --root <root> --json next-all --group <path>   # or --subgroup <path>
```

Using the caller's own named scope. Claim the whole returned batch up front:
```
questctl --root <root> set-status <id-1> "~" --message "claimed for batch research"
questctl --root <root> set-status <id-2> "~" --message "claimed for batch research"
...
```
Then research each independently — same `annotate`-always, then `answer`+`set-status` (skipping the already-done claim step) as sequential mode above.

*No usable evidence, parallel mode* — already `[~]`, no `[~]→[ ]` step exists, so it cannot simply stay untouched:
```
questctl --root <root> annotate <id> --message "<plan, sources examined, why nothing supports an answer>"
questctl --root <root> set-status <id> B --message "no usable evidence in <Datenbasis>"
```

**Verify, then build the final report** (end of run): for every Question this run touched, re-read its actual persisted state:
```
questctl --root <root> --json show <id>
```

## Status transitions, summarized

- Every claim is `[ ]→[~]` — `open`'s only forward step — before any outcome status.
- Confident answer: `[~]→X` directly.
- Thin-evidence answer: `info-review <id> user` first, then `[~]→R` — same mechanics as `questctl-checker-cli`'s own "Status transitions".
- No usable evidence, parallel mode only: `[~]→B`, `--message` required.
- No usable evidence, sequential mode: no transition at all — the Question was never claimed.

## Error handling

- A single Question's research failing (Datenbasis inconclusive, an `answer`/`set-status` call erroring) never stops the loop in sequential mode — the `annotate` trace already recorded what was attempted; continue to the next `next` call. In parallel mode, resolve the affected Question to `B` (already claimed) and continue with the rest of the batch.
- Reaching `all_answered`/`awaiting_interaction` (sequential) or exhausting the claimed batch (parallel) ends the run normally.
- A non-zero exit or unparseable output from the **first** `next`/`next-all` call (before anything is claimed) is categorically different — stop the run and report that failure directly.

## Out of scope

- Any `questctl` command not listed above — in particular `add`/`add-group`/`add-subgroup` (authoring is `questctl-author-cli`'s job).
- Reading or writing the Datenbasis beyond what's needed to research it — the Subagent's own job via Read/Grep/WebFetch, not a `questctl` operation.
- Any source of evidence beyond the given Datenbasis (live web search, an unscoped codebase walk) — see `design-questctl-researcher.md`, "Input"/"Future extensions".
