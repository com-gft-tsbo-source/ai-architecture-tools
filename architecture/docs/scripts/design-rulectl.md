# rulectl

Objects are checks that can be applied to a code or data base.

## Store

Store name `rules` (design.md, "File and Directory Parameters"): resolves to `<shared-dir>/rules.md` or `<shared-dir>/rules`. Default mode when neither exists yet: **directory** — the 3-level Language/Context/Category hierarchy reads more naturally as nested directories than as one growing file.

## Metagroups

- `Language=Go|Python|C|Java|...`
- `Context=<Language>/<name>`
- `Category=<Language>/<Context>/<name>`

## Metainfo

- `source`: free text
- `weight`: free text
- `tool`: tool name
- `tool-rule`: rule identifier within that tool
- `checkable`: `llm` | `<tool-name>`

## Status

- `draft`: still being drafted, but already applied regularly
- `active`: in use
- `obsolete`: no longer in use

There is no `--draft` flag at creation; the initial status is always `active`. `draft`/`obsolete` are reached only via an explicit `set-status` afterwards. No automatic transitions — all status changes are manual, made by a user or an agent acting on instruction.

## Operations

In addition to the general operations from design.md, rulectl supports:

- `tasklist [--language <path>|--context <path>|--category <path>]`: exports every **active** Rule (`draft`/`obsolete` Rules are skipped) into taskctl as Tasks (design-decisions.md, "Amendments (2026-08-21, rulectl `tasklist`)" has the full rationale). With no filter flag, the whole store is processed; at most one of `--language`/`--context`/`--category` may be given to restrict export to that metagroup subtree (same semantics as `list`'s filters — inclusive of descendants).

  **Phase mapping**: every unique (Language, Context, Category) path among the processed Rules becomes exactly one taskctl Phase — never one Phase per Rule, never one Phase per Language. The Phase's Name is the three segments' own (sort-prefix-stripped) names joined with `::` (not `/`, which is reserved by the CLI as the metagroup path separator). Multiple Rules sharing a path land as separate Tasks inside that one Phase. A Phase is reused if an equivalent one (same flattened name) already exists in the taskctl store; otherwise it is created with an auto-assigned Phase number, same as any other `add-phase`.

  **Task identity and idempotency**: a Task's Object ID is the *same* ID as its source Rule (safe — Object IDs are only unique within their own store). Re-running `tasklist`:
  - creates a new Task (initial status open) for a Rule with no existing Task of that ID yet;
  - **updates** an existing Task in place otherwise: its Phase (if the Rule's path changed), Description, `assignee-type`/`assignee-name` are refreshed to the Rule's current values (each field is only actually rewritten if it changed, to avoid needless History noise); its Status is force-reset to open (even from `done`/blocked/in review) if it wasn't already open; its `review` metainfo is force-reset to `none` if it had drifted away from that (see "Review reset" below); and a `T` History entry is appended via the same `annotate` mechanism `taskctl annotate` uses, referencing the source Rule's Signature, so a re-export is always visible in the Task's History even when nothing else about it changed.

  **Review reset**: a Task previously escalated to `R` carries `review=user` (taskctl's `info-review`), which changes its valid forward path (design-taskctl.md; `lib/taskctl_spec.py`'s `validate_transition` reads `review` at the moment of each transition). Resetting only the Status to `open` without also resetting `review` back to `none` would leave that changed path in place, so a fresh `[~]→[X]` verdict on re-check would still be routed through `[R]` (or rejected outright without `--force`) even though the Task is, from `tasklist`'s point of view, freshly re-exported. `tasklist` therefore resets `review` to `none` in the same pass whenever it isn't already `none`, so every re-exported Task's forward path starts clean, matching a first-time export.

  **Field mapping**, keyed off the Rule's `checkable` metainfo:
  - `checkable == "llm"`: `assignee-type = "agent"`, `assignee-name = ""`. The Task's Description is the Rule's own `Description` (and, if non-empty, its `Procedure` as a `### Procedure` subsection) embedded directly — the agent working the Task reads the rule text itself, not a pointer back to rulectl.
  - `checkable != "llm"` (a tool name): `assignee-type = "tool"`, `assignee-name = <the Rule's tool metainfo value>` (not `checkable` itself — `tool`/`tool-rule` are the fields documented as tool name/rule identifier; `checkable` is only the branch switch). The Task's Description is no longer just a bare tool instruction: it leads with `` Run `<tool>` to verify rule `<tool-rule>`. ``, then embeds the Rule's own `Description` (as a `### Rule` subsection), its `Procedure` if non-empty (`### Procedure`), and its `source` metainfo if set (`### Source`) — the same Rule content an `llm`-branch Task gets, so a Task worked by a checking Subagent can judge a tool's result against the actual guideline, not just a tool/rule-id pair.

  Both branches end their Description with, or otherwise reference, the source Rule's Signature for traceability. No back-reference is written onto the Rule itself — the shared Object ID between Rule and Task is already sufficient to cross-reference (`taskctl show <id>` / `rulectl show <id>`), so no bidirectional linkage machinery like `lib/spec_link.py`'s (adrctl<->specctl) was built for this one-directional batch export.

  `tasklist` writes into the taskctl store sharing this invocation's `--root` (design.md, "File and Directory Parameters"), the same way adrctl's `spec-ref` reaches specctl's store — not transactionally with rulectl's own store: `tasklist` never modifies any Rule.

## User Content

- `Description`
- `Procedure`

Each block may contain Markdown and is stored with a `> ` prefix per line.
