# taskctl

Objects are tasks.

## Store

Store name `tasks` (design.md, "File and Directory Parameters"): resolves to `<shared-dir>/tasks.md` or `<shared-dir>/tasks`. Default mode when neither exists yet: **directory** — a task list's Phase-level structure reads more naturally as nested directories than as one growing file.

## Metagroups

`Phase=<nr>-<name>` (single level; the 3-digit, zero-padded `<nr>` prefix is the metagroup's sort key, as for all tools — see design.md). Example: `002-Implementation`.

Like questctl (design-questctl.md, "Metagroups"), taskctl declares an **allowed depth range** rather than one fixed number — here, 0 or 1: a store either uses Phases for every Task, or uses no Phases at all (a flat task list). The depth is a whole-store property, not a per-Task one: it is not persisted as an explicit marker but inferred from what already exists, exactly as design.md, "Metagroups", describes generally. Unlike questctl's `add-group` (which by itself decides nothing — Group is not questctl's deepest level, Subgroup is), **`add-phase` locks depth 1 immediately, the moment the first Phase is created**, even before any Task exists: Phase is taskctl's *only* declared level, so it is simultaneously its shallowest and its deepest — creating one is exactly as unambiguous a signal as questctl's `add-subgroup` is for *its* deepest level, not the ambiguous-either-way signal `add-group` is for questctl. Failing that (no Phase created yet either), depth is fixed by the first successful `add` (with or without `--phase`). `add-phase` is rejected once a store is locked at depth 0 (there is nothing for a Phase to attach to); every `add` after the first must match the established depth. A depth-0 store's Task files sit directly in the store root (directory mode), which is then the only metagroup-path directory that ever exists, with its own `.index.md`/`.index.json` pair.

## Metainfo

- `origin`: optional producer reference, separate from document `source` and assignment. `rulectl tasklist` sets `rulectl:<rule-id>`; ordinary authored Tasks leave it unset. Exposed through `add --origin`, `info-origin`, `list --origin`, and JSON output like other Metainfo fields. This is provenance, not authentication.

- `review`: `none` | `user` | `subagent`
- `assignee-type`: free text
- `assignee-name`: free text
- `source`: free text — traceability back to the document a Task was derived
  from, same convention as rulectl's own `source` field (design-decisions.md,
  "Amendments (2026-08-25, taskctl-author/taskctl-worker Subagent design)").
  Left unset for a Task with no such origin (e.g. a hand-created Task, or one
  authored directly through `taskctl-author-cli` without a source document).
- `gate`: `sequential` | `none` — whether the Task takes part in Sequential Processing (see there). Absent means `sequential`. `rulectl tasklist` creates its compliance checks with `gate=none`: they are independent of each other, and `rulectl-checker` records a violation as `[R]` and moves on to the next check. The value is fixed at creation — changing it later requires `--user-approved` (see Guards).

## Status

| Status | Meaning |
|---|---|
| `[ ]` | open |
| `[~]` | in progress |
| `[R]` | review by user |
| `[C]` | review by subagent |
| `[B]` | blocked |
| `[X]` | done |

Depending on the task's `review` value, the normal forward path is:
- `none`:     `[ ]` → `[~]` → `[X]`
- `user`:     `[ ]` → `[~]` → `[R]` → `[X]`
- `subagent`: `[ ]` → `[~]` → `[C]` → `[X]`

`[B]` is reachable from any non-terminal status, and from there back into any non-terminal status of the path (unblocking) — a reason **must** be supplied via `--message` when transitioning to `[B]`; it is recorded in the History. From `[R]` or `[C]`, a step back to `[~]` is allowed (rework). All other transitions require `--force`, which in turn requires `--user-approved` (see Guards). `[R]` → `[X]` is on-path but is the user's review verdict, so it also requires `--user-approved`; `[C]` → `[X]` does not.

As described in design.md, `--set-status` at `add` time may set any initial status, including one unreachable as a transition (e.g. creating a task directly in `[~]`) — no `--force` needed for that case, since it is not a transition. The sequence guard still applies to it (see Guards).

## Sequential Processing

Task processing is sequential: the tool assumes at most one Task is actively worked at a time, in priority order (see Prioritization). `[B]`, `[R]`, and `[C]` **block** this sequential progression — a Task in any of these statuses must be resolved (moved onward, or unblocked and then moved onward) before work proceeds to a later Task. This is enforced, not only reflected in `next`: see Guards.

Tasks with `gate=none` (see Metainfo) are outside this progression: they never block a later Task, and starting them is never held back by an earlier one.

This is what `next` (see Operations) actually returns: not "the next `[ ]` Task," but **the earliest Task, in priority order, that is not `[X]`** — whatever its status. A Task already `[~]` is reported as the one currently active; a Task in `[B]`/`[R]`/`[C]` is reported as the one currently blocking further progress; only when the earliest non-`[X]` Task is `[ ]` does `next` hand back a genuinely new Task to start. `next` therefore never skips past an unresolved Task to reach a later `[ ]` one, however far down the list that later Task is. The one exception is a `gate=none` Task sitting in `[B]`/`[R]`/`[C]`: it holds nothing up, so `next` passes over it (a `gate=none` Task in `[ ]`/`[~]` is still handed out like any other).

## Guards

An agent working a task list must not skip past unresolved work or decide a user review itself. taskctl therefore **rejects** the following operations (exit 1) unless they carry `--user-approved "<text>"`:

1. **Sequence:** moving a Task into `[~]`, `[R]`, `[C]` or `[X]` — by `set-status`, or by `add --set-status` — while an earlier Task (priority order, see Prioritization) is not `[X]`. Moving a later Task to `[B]` (with a reason) or `[ ]` stays free. Tasks with `gate=none` neither block nor are blocked.
2. **Self-approval:** `[R]` → `[X]`.
3. **Review change during review:** `info-review` on a Task in `[R]` or `[C]`.
4. **Review de-escalation:** lowering `review` from `user` to `none` or `subagent`, in any status. `none`/`subagent` → anything else and `subagent` → `none` stay free.
5. **Leaving the status path:** every `set-status --force`. `--force` without `--user-approved` is rejected outright.
6. **Gate change:** `info-gate` after creation.

All other operations — authoring, `set-description`, `reorder`, `delete`, `group-phase`, other `info-*`, `annotate`, rework `[R]`/`[C]` → `[~]` — are unaffected.

`--user-approved <text>` (on `add`, `set-status`, `info-<metainfo-type>`) states that **the user** asked for this operation; `<text>` is the user's instruction (quote or summary). It must not be empty. It lifts the guards for that one call and is recorded in the `M` History entry as the first message line, followed by `--message` if any:

    - 2026-10-30T10:00:00: M [R] -> [X] |
      > USER-APPROVED: User: "Task 3 is accepted"
      > review ok

`--user-approved` is accepted on an operation that needs no approval too; it is then recorded the same way. An agent must never supply it on its own.

**Error contract:** a rejection exits 1 with a plain stderr message naming the blocking Task (ID, Signature, status) or the missing approval. With `--json`, stdout carries `{"reason": "sequence_blocked" | "approval_required", "message": ..., "blocking_task": <id>}` (`blocking_task` for `sequence_blocked` only) — the same mechanism as `NoWorkAvailable`, so a looping agent stops and asks the user instead of parsing text.

**What this does and does not protect against:** taskctl cannot tell the user from an agent — an instruction the user gives in a chat (CLI or web interface) reaches taskctl only through the agent. The guards stop an agent from *accidentally* performing an illegal operation and make every authorized exception explicit and auditable; they do not stop an agent that deliberately lies via `--user-approved` or edits the store files directly. For a real human-in-the-loop check, a project may add a Claude Code permission rule so the harness asks the user before any approved call runs (`.claude/settings.json`):

    {
      "permissions": {
        "ask": ["Bash(taskctl * --user-approved *)", "Bash(questctl * --user-approved *)"]
      }
    }

Per the Claude Code permission docs (code.claude.com/docs/en/permissions, /permission-modes), explicit `ask` rules prompt in every permission mode, including auto and `bypassPermissions`. They match the command text, though (after splitting compound commands), so an agent can evade them by invoking the tool differently (e.g. `sh -c '...'`); this is a safeguard against mistakes, not a security boundary.

Internal callers bypass the guards through `lib/store.py`'s `force` parameter (`set_status`, `set_metainfo`) without a History marker — `rulectl tasklist` uses this for its re-export reset of status, `review` and `gate`. The CLI never passes `force` without `--user-approved`.

(Contrast questctl, design-questctl.md, "Status": there, `[B]`/`[R]`/`[C]` on one Question never blocks work on any other Question — several Questions may be worked in parallel — precisely because questctl's processing model is not sequential in this sense.)

## Object Type

Exception to the general rule in design.md: **when Phases are in use** (depth 1, see Metagroups), the Object Type equals the Phase number, **not** padded to 6 characters — this exists purely to make tasks more easily identifiable, not as a true classification. **In a phase-less (depth 0) store**, there is no Phase number to derive from, so the general 0-level derivation applies instead (design.md, "Object Type"; design-questctl.md, "Object Type", for the same fallback in questctl): every Task derives to `______`.

## History

In addition to the general `M` (management) entries from design.md, taskctl uses `T` to log execution progress via `annotate`. `T` entries **always** show the `[<old>] -> [<new>]` transition, even when unchanged (e.g. `[~] -> [~]`) — unlike `M`, which shows a transition only when the status actually changed.

## Operations

In addition to the general operations from design.md, taskctl supports:

- `annotate`: append a History entry (`T`) documenting task execution progress.
- `next`: find and display the earliest Task, in priority order, that is not `[X]` (see Sequential Processing) — including its History. This may be the next new `[ ]` Task, or an already-`[~]`/`[B]`/`[R]`/`[C]` Task blocking further progress. If no such Task exists (every Task is `[X]`, or the store is empty), `next` raises `NoWorkAvailable` with reason `all_done` — exit 1, plain stderr text, or with `--json` a machine-readable `{"reason": "all_done", "message": ...}` (design-decisions.md, "Amendments (2026-08-25, taskctl `NoWorkAvailable` + taskctl-author-cli/taskctl-worker-cli design)"; the same mechanism questctl's `next`/`next-all` already use, design-questctl.md, "CLI Contract additions" — taskctl only ever has this one "nothing to hand out" case, never questctl's other two).

Phases and Tasks may also originate from `rulectl tasklist` (design-rulectl.md, "Operations") rather than being created directly through taskctl's own `add-phase`/`add` — such a Task's Object ID is shared with its source Rule, and `annotate`-style `T` History entries record every re-export. No taskctl-side behavior differs for these Tasks; this is purely informational.

## Prioritization

Tasks are ordered by sorted Phase, then by task number within that Phase — this order drives `next` and default listings.

## User Content

- `Description`

Each block may contain Markdown and is stored with a `> ` prefix per line.
