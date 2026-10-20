---
name: adrctl-author-cli
description: Wraps the adrctl CLI for creating and superseding ADRs that document specctl changes — add-domain/add-component, add (always --set-status accepted, with --spec-ref), info-spec-ref, info-superseded-by/set-status superseded, set-motivation/set-description/set-rationale. Always used alongside specctl-editor-cli in the same run. Use whenever a specctl stable-phase change needs an authorizing ADR. Not for reviewing/approving proposed ADRs — every ADR this workflow creates is already accepted.
---

Full spec: `architecture/docs/skills/design-adrctl-author-cli.md`.

You operate the `adrctl` CLI (on `PATH`, provided by the
`architecture-tools` plugin's `bin/`) via Bash for creating and
superseding ADRs that document `specctl` changes. This is a reference, not
a wrapper script — call `adrctl` yourself, following the recipes below.
Always used alongside `specctl-editor-cli` in the same run — see
`design-specctl-adr-author.md` for the exact interleaving.

## Scope

- `add-domain`, `add-component` — create metagroup paths.
- `add` (inline `--component` for the target path, `--motivation`/
  `--description`/`--rationale`, `--spec-ref`, `--set-status accepted`) —
  create an ADR, always directly `accepted` (see below).
- `list --component <path>` — read existing ADRs under a path, for context.
- `show-metagroups` — inspect existing Domains/Components before placement.
- `show` — inspect a specific ADR, **and** re-read a just-created one to
  confirm it persisted and its `spec-ref` propagation took effect.
- `info-spec-ref` — retroactively attach/correct an ADR's governed Section
  (also a propagation trigger).
- `info-superseded-by`, `set-status superseded` — retire an ADR being
  replaced.
- `set-motivation`, `set-description`, `set-rationale` — update a just-
  created (or, for the correction case, an already-existing) ADR's own
  content.

Never call `reorder`, `delete`, `group-domain`, `group-component`,
`reindex`, or `history` from this Skill.

## Initial Status

Every ADR you create here goes directly to `accepted`
(`add --set-status accepted`), never left at `adrctl`'s default,
`proposed`. The user's own request already constitutes the decision — a
separate `proposed` stage would only be a redundant step with no real
review happening in between.

## spec-ref propagation

Setting `--spec-ref <section-id>` on `add` (or later via `info-spec-ref`)
automatically writes the new ADR's ID into that Section's `adr` field in
the same `adrctl` invocation — no separate `specctl` call needed for that
one Section. That's what lets `specctl-editor-cli`'s following
`set-status stable` / `set-description`/`set-open-questions` succeed
**without** an inline `--adr`. `spec-ref` naming a Section that doesn't
exist aborts the whole `adrctl` call (exit 1) — the ADR itself is still
persisted regardless (no rollback across the two stores).

## Multi-Section topics

`spec-ref` is single-valued — one call propagates to exactly **one**
Section. When a topic touches several, only ever set `--spec-ref` to one
(the "primary" — pick deterministically, e.g. first named in the change
request); every additional Section is linked by `specctl-editor-cli`'s
`set-adr <id> <this-adr-id>` instead, called once per additional Section,
after this ADR exists. "Primary" carries no meaning beyond being the one
`spec-ref` names.

## Conventions

- **`--root <path>`**: the same value passed to the `specctl-editor-cli`
  calls in the same run.
- **`--json`**: pass it whenever parsing output (`list`, `show`).
- **Exit codes**: `0` = ok, `1` = error, error text on stderr; `2` = a
  malformed command line (unknown subcommand or option).
- **Ordering matters**: mint/identify the ADR before the corresponding
  `specctl-editor-cli` write that depends on it.

## Recipes

**Create a metagroup path**, each level before the next is created under
it. **New Domains are batch-gated** — before creating one, check the
existing Domains (`adrctl --root <root> --json show-metagroups` — a JSON
array of paths, e.g. `[["001-Spec"], ["001-Spec", "001-Core"]]`); never
create a new top-level Domain autonomously — collect every ADR in this run
needing an undecided Domain into one question, asked once, up front.
**Components are created freely** once their Domain exists.

```
adrctl --root <root> add-domain <name>
adrctl --root <root> add-component <domain>/<component-name>
```

**Create an ADR**, once its Component exists:

```
adrctl --root <root> add --component <domain>/<component> \
  --name "<short name>" \
  --motivation "<why this change>" \
  --description "<what the decision is>" \
  --rationale "<why this approach>" \
  --spec-ref <primary-section-id> \
  --set-status accepted
```

`--motivation`/`--description`/`--rationale` are always your own synthesis
of the change request and the resulting `specctl` content — never a
verbatim copy of the invocation prompt.

**Read before creating**, for context:

```
adrctl --root <root> --json list --component <domain>/<component>
```

**Confirm a just-created ADR persisted and propagated**:

```
adrctl --root <root> --json show <id>
```

Then `specctl --root <root> --json show <primary-section-id>` (via
`specctl-editor-cli`) to confirm that Section's `adr` now shows this ADR's
ID.

**Link an additional Section after the fact** (retroactive, or the
correction case), instead of `add`'s inline `--spec-ref` — note this
**replaces** the ADR's previous `spec-ref`, it does not add a second one:

```
adrctl --root <root> info-spec-ref <adr-id> <section-id>
```

The previously referenced Section keeps its `adr` pointing at this ADR —
only the ADR side changes. If that Section should no longer be governed by
it, correct it with `specctl-editor-cli`'s `set-adr`.

For adding an *additional* governed Section, use `specctl-editor-cli`'s
`set-adr` instead (see "Multi-Section topics").

**Supersede only a fully replaced ADR**, after the new topic's Sections
have been linked, edited/promoted, and verified. First use
`specctl --root <root> --json list --adr <old-adr-id>` through
`specctl-editor-cli`, with no status/path filter. If any Section still
references the old ADR, keep it `accepted` and leave `superseded-by`
unchanged. The new ADR documents precisely which part it replaces.
A failed query never permits retirement.

Only when no Section references it:

```
adrctl --root <root> info-superseded-by <old-adr-id> <new-adr-id>
adrctl --root <root> set-status <old-adr-id> superseded
```

**Update an existing ADR's own content** (the confirmed-correction case) —
only the fields that actually need to change, not all three:

```
adrctl --root <root> set-motivation <adr-id> "<updated text>"
adrctl --root <root> set-description <adr-id> "<updated text>"
adrctl --root <root> set-rationale <adr-id> "<updated text>"
```

## Error handling

- **Unknown metagroup path**: create the missing ancestor(s) first, then
  retry.
- **`spec-ref` naming a Section that doesn't exist**: the whole `add`/
  `info-spec-ref` call aborts even though the ADR may already be persisted
  (`add`'s case) — re-verify the Section ID and retry `info-spec-ref`; the
  ADR doesn't need recreating.
- **Object ID collision** on `add`: retry once.
- Any other non-zero exit: report the stderr text as-is for that one
  topic/ADR; don't retry blindly, don't let one failure stop the rest of
  the run.

## Out of scope

Deciding topic boundaries, correction-vs-new-decision classification, or
the confirmation gate before reusing an ADR — all workflow judgment in
`design-specctl-adr-author.md`. Any `specctl` operation — entirely
`specctl-editor-cli`'s job.
