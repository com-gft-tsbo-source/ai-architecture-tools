# questctl-checker-cli

Skill that wraps the `questctl` CLI for the `questctl-checker` Subagent (`architecture/docs/subagents/design-questctl-checker.md`). Purely an instructional reference — a `SKILL.md`, no executable wrapper code. The invoking agent calls `questctl` itself via Bash; this Skill only teaches it how to do that correctly for the answer-attribution workflow. Named `questctl-...` like its siblings `questctl-author-cli`/`questctl-researcher-cli`.

## Scope

- `next [--group <path> | --subgroup <path>]` / `next-all [--group <path> | --subgroup <path>]` — work-selection, sequential and parallel respectively (see "Recipes").
- `set-status <id> <code> --message <text>` — `~` (claim), `X` (confidently matched), `R` (matched, attribution uncertain), `B` (parallel-mode-only: claimed but no match found — see "Recipes").
- `info-review <id> user` — switch a Question's review mode immediately before escalating it to `R` (see "Status transitions" below).
- `answer <id> <text> --message <text>` — record the attributed (verbatim) text against a Question.
- `annotate <id> --message <text>` — record a no-match trace on a Question that stays `[ ]` (sequential mode only — see "Recipes").
- `show <id>` — re-read a Question's actual persisted state.

Not in scope: `add`, `add-group`, `add-subgroup`, `set-description`, `info-source`, `delete`, `reorder`, `group-<metagroup-type>`, `reindex` — none of these are needed to attribute answers to an existing catalog; authoring is `questctl-author-cli`'s job.

## Conventions

- **`--root <path>`**: one shared path for every call in a run, always given explicitly by the caller.
- **`--json`**: pass it on `next`/`next-all` (parsing the returned Question(s)) and `show` (the final re-read). Omit it on `set-status`/`answer`/`annotate`: pure write calls whose outcome is the exit code.
- **Exit codes**: `0` = ok, `1` = error — including `next`/`next-all`'s three "nothing available" cases (`in_progress`/`all_answered`/`awaiting_interaction`, distinguished via `--json`'s `"reason"` field — design-questctl.md, "CLI Contract additions").

## Recipes

**Sequential mode (default) — one Question at a time:**

```
questctl --root <root> --json next [--group <path> | --subgroup <path>]
```

Parse the returned Question. Search the answer-source for it *before* touching status (`design-questctl-checker.md`, "Claim timing") — no CLI call needed for the search itself, that's the Subagent's own Read/Grep/WebFetch work against the answer-source, not a `questctl` operation.

*No matching passage found:*
```
questctl --root <root> annotate <id> --message "checked against <source>, no matching passage found"
```
Leave the Question there — do **not** call `set-status`. Loop back to `next`.

*Match found (confident or uncertain — see below), only now claim:*
```
questctl --root <root> set-status <id> "~" --message "checking against <source>"
questctl --root <root> answer <id> "<verbatim attributed text>" --message "<which passage(s), e.g. 'client email, para 2'>"
questctl --root <root> set-status <id> X --message "confidently matched"
```
For an uncertain attribution, `info-review` must run **before** `set-status ... R` — it switches the Question's forward path so `[~]→R` becomes a normal, on-path step; without it, `[~]→R` is off-path and fails without `--force` (verified against `lib/taskctl_spec.py`'s `validate_transition`, which questctl reuses directly — it reads the Question's *current* `review` metainfo at the moment of the transition, not a value fixed at creation, exactly as `rulectl-checker-cli` already documents for its own taskctl-side workflow):
```
questctl --root <root> info-review <id> user
questctl --root <root> set-status <id> R --message "<why the attribution is uncertain>"
```
Then loop back to `next` — since this run's own claim already resolved before the next call, `next` should not report `in_progress` from this run's own prior work.

**Parallel mode (only when the caller explicitly asked for it, naming a scope):**

```
questctl --root <root> --json next-all --group <path>   # or --subgroup <path>
```

Using the **caller's own named scope**, not the whole store. Parse every returned Question, then claim the *whole batch* up front, one call per Question, before examining any of them:

```
questctl --root <root> set-status <id-1> "~" --message "claimed for batch processing"
questctl --root <root> set-status <id-2> "~" --message "claimed for batch processing"
...
```

Then work each claimed Question independently, same match/uncertain outcomes as sequential mode above (skip the `set-status ~` step in each — already claimed):

```
questctl --root <root> answer <id> "<verbatim attributed text>" --message "<which passage(s)>"
questctl --root <root> set-status <id> X --message "confidently matched"
```
For an uncertain attribution, `info-review <id> user` first, then `set-status <id> R --message "..."` — same as the sequential recipe above.

*No matching passage found, parallel mode* — the Question is already `[~]`, and there is no `[~]→[ ]` step (design-questctl.md defines none), so it cannot simply be left alone:
```
questctl --root <root> annotate <id> --message "checked against <source>, no matching passage found"
questctl --root <root> set-status <id> B --message "no matching passage found in <source>"
```

**Multi-match**: if one passage addresses more than one Question, repeat the `answer`/`set-status` pair for each matching Question independently — never skip a second genuine match because a first one was already recorded.

**Verify, then build the final report** (end of run): for every Question this run touched (claimed, answered, or annotated), re-read its actual persisted state:
```
questctl --root <root> --json show <id>
```
Don't trust this run's own bookkeeping — a `set-status`/`answer` call that silently failed must not be reported as if it landed cleanly.

## Status transitions, summarized

- Every claim is `[ ]→[~]` — `open`'s only forward step — before any outcome status; a direct `[ ]→X`/`R`/`B` jump is off-path and fails without `--force` (never used by this workflow).
- Confident match: `[~]→X` directly.
- Uncertain match: `info-review <id> user` first — this changes the *effective* forward path, since questctl reuses `lib/taskctl_spec.py`'s `validate_transition` directly, which reads the Question's current `review` value at the moment of `set-status`, not one fixed at creation — making `[~]→R` a normal, on-path step afterward. No `--force` needed. Identical mechanics to `rulectl-checker-cli`'s own taskctl-side workflow.
- No match, parallel mode only: `[~]→B`, `--message` required (questctl's general rule for entering `[B]`) — reachable regardless of the Question's current `review` value, same as taskctl's.
- No match, sequential mode: no transition at all — the Question was never claimed.

## Error handling

- A single Question's attribution failing (search inconclusive, an `answer`/`set-status` call erroring) never stops the loop in sequential mode — `annotate` what's known and continue to the next `next` call. In parallel mode, resolve the affected Question to `B` (it's already claimed) and continue with the rest of the batch.
- Reaching `all_answered`/`awaiting_interaction` (sequential) or exhausting the claimed batch (parallel) ends the run normally.
- A non-zero exit or unparseable output from the **first** `next`/`next-all` call (before anything is claimed) is categorically different — no Question has been touched yet; stop the run and report that failure directly, same distinction `rulectl-checker-cli` draws for its own `tasklist` refresh failure.

## Out of scope

- Any `questctl` command not listed above — in particular `add`/`add-group`/`add-subgroup` (authoring is `questctl-author-cli`'s job).
- Reading or writing the answer-source beyond what's needed to search it — that's the Subagent's own job via Read/Grep/WebFetch, not a `questctl` operation.
