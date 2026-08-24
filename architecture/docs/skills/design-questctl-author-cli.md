# questctl-author-cli

Skill that wraps the `questctl` CLI for the `questctl-author` Subagent (`architecture/docs/subagents/design-questctl-author.md`). Purely an instructional reference — a `SKILL.md`, no executable wrapper code. The invoking agent calls the `questctl` binary itself via Bash; this Skill only teaches it how to do that correctly for the authoring workflow. Modeled on `rulectl-author-cli` (`architecture/docs/skills/design-rulectl-author-cli.md`); read together with it for anything not restated here.

## Scope

Covers only the `questctl` operations the authoring workflow needs:

- `list`, `show-metagroups` — **detect the store's already-established metagroup depth** before proposing a taxonomy (see "Detecting the established depth" below) — this is the one recipe with no `rulectl-author-cli` analogue, since `rulectl`'s metagroup depth is fixed per tool, never a whole-store property to detect.
- `add-group`, `add-subgroup` — create the confirmed taxonomy's metagroup paths.
- `add` (with inline `--group`/`--subgroup`, `--source`, `--description`) — create a Question.
- `list --group <path>` / `list --subgroup <path>` — read existing Questions under a candidate node, for duplicate detection before `add`.
- `show`, `show-metagroups` — inspect a specific Question or the declared taxonomy when disambiguation is needed, **and** re-read a just-created Question to confirm it actually persisted (the local-duplicate representative/fallback loop and the final worklist audit both depend on this, `design-questctl-author.md`, steps 5–6).
- `info-source`, `set-description` — correct a just-created Question's fields within the same run.

Not in scope (not used by this workflow, so not documented here): `answer`, `annotate`, `next`, `next-all`, `set-status`, `info-review`/`info-assignee-type`/`info-assignee-name`, `history`, `reorder`, `delete`, `group-<metagroup-type>`, `reindex`. A Question created by this workflow is always left at its default initial status (`[ ]`) and with `review`/`assignee-type`/`assignee-name` unset (design-questctl-author.md, "Status"/"Metainfo population") — this Skill never calls `set-status`/`info-review`/`info-assignee-type`/`info-assignee-name`, and never touches `Answer` (`answer`/`annotate`) at all — that's exclusively `questctl-checker`/`questctl-researcher` territory.

## Invocation conventions

Same as `rulectl-author-cli`: `--root <path>` always supplied by the caller; `--json` on every call whose output is parsed programmatically (`list`, `show`, `show-metagroups`); exit codes `0`/`1`, check the code not stderr's presence; every operation is a single, independent `questctl` invocation, no batch/transaction mode.

## Detecting the established depth

Before proposing a taxonomy (`design-questctl-author.md`, step 3a), determine whether the target store already has a fixed metagroup depth — there is no single command that reports this directly, so combine two read-only calls:

```
questctl --root <root> --json list
questctl --root <root> --json show-metagroups
```

- If `list` returns any Question, its `"metagroup"` array's length **is** the established depth (`0`, `1`, or `2`) — every Question in a store shares the same depth (design-questctl.md, "Metagroups"), so the first one found is representative.
- Otherwise, if `show-metagroups` returns any path with **two** segments, depth `2` is established even though no Question exists there yet (only reachable via a prior `add-subgroup`, which is unambiguous — design-questctl.md, "Metagroups").
- Otherwise, the store's depth is **not yet established** — this run is free to choose (design-questctl-author.md, step 3c, "fresh store" case).

## Operation recipes

**Creating the confirmed taxonomy**, once step 3's batched confirmation has an answer — each Group before any Subgroup under it:

```
questctl --root <root> add-group <name>
questctl --root <root> add-subgroup <group-name>/<subgroup-name>
```

A segment may be given as a bare name (an auto-assigned `<nr>-` prefix is added) or as an explicit `<nr>-<name>`. If the store is already established at depth 0, **skip this recipe entirely** — no Group/Subgroup is ever created there (design-questctl-author.md, step 3a).

**Creating a Question**, once its target node (or, for a depth-0 store, with no node at all) exists:

```
questctl --root <root> add --group <group-name> \
  --name "<short name>" --description "<question text>" \
  --source "<traceability note>"
```

For a depth-2 target, use `--subgroup <group-name>/<subgroup-name>` instead of `--group`. For a depth-0 store, omit both flags entirely — `add` without either is exactly how a depth-0 Question is created (design.md, "Metagroups": variable_depth), not an error. The Question is created at status `[ ]` by default — no flag is needed or available to create it any other way, and this workflow never overrides it.

**Duplicate check before creating a Question**, against the candidate node:

```
questctl --root <root> --json list --group <group-name>
questctl --root <root> --json list --subgroup <group-name>/<subgroup-name>
```

Use whichever matches the candidate's target depth. Read the returned Questions' Names/Descriptions and judge similarity against the Question about to be created. Like `rulectl`'s `list --category`, this over-matches everything at or below the given path — for a `--group` filter on a depth-2 store this includes every Subgroup underneath, so scope to `--subgroup` whenever the candidate's actual target is a Subgroup.

## Error handling

- **Unknown metagroup path** (`add --group`/`--subgroup <path>` where the path isn't declared yet): create the missing segment(s) first (see "Operation recipes"), then retry. Never fatal for the overall run.
- **Depth rejection** (`add`/`add-group`/`add-subgroup` failing with "this store is fixed at metagroup depth ..."): this means step 3's depth-detection (see "Detecting the established depth") was run against stale information, or the reconciliation in `design-questctl-author.md` step 3c wasn't actually applied before creating — re-derive the established depth and reconcile the confirmed taxonomy against it before retrying; never just retry blindly, and never fall back to `--force` (there is no `--force` for a metagroup depth violation — design.md defines none).
- **Object ID collision** on `add`: astronomically unlikely with generated IDs; retry once — `questctl` regenerates the ID from content on each attempt.
- Any other non-zero exit: surface the stderr text as-is in the Subagent's final report for that one Question/metagroup node; do not retry blindly, and do not let one failed item abort the whole run — continue with the remaining extracted Questions.

## Out of scope

This Skill does not cover matching answers to Questions (`questctl-checker-cli`'s job) or independently researching answers (`questctl-researcher-cli`'s job) — both are separate Skills for separate Subagents.
