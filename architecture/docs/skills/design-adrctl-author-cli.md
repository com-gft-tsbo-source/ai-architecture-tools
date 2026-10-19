# adrctl-author-cli

Skill that wraps the `adrctl` CLI for the `specctl-adr-author` Subagent
(`architecture/docs/subagents/design-specctl-adr-author.md`). Purely an
instructional reference — a `SKILL.md`, no executable wrapper code. The
invoking agent calls the `adrctl` binary itself via Bash; this Skill only
teaches it how to do that correctly for creating and superseding ADRs that
document `specctl` changes. Modeled closely on `rulectl-author-cli`
(`architecture/docs/skills/design-rulectl-author-cli.md`) — same shape, one
tool, one authoring workflow — adapted for `adrctl`'s own metagroup/content
vocabulary and for the `spec-ref` linkage `adrctl` shares with `specctl`.
Always used alongside `specctl-editor-cli`
(`architecture/docs/skills/design-specctl-editor-cli.md`) in the same run —
see `design-specctl-adr-author.md` for how the two interleave.

## Scope

Covers only the `adrctl` operations the stable-phase workflow needs —
creating ADRs and, when a topic is genuinely superseded, retiring the old
one:

- `add-domain`, `add-component` — create metagroup paths.
- `add` (with inline `--component` for the target path, `--motivation`/
  `--description`/`--rationale`, `--spec-ref`, `--set-status accepted`) —
  create an ADR, always directly at `accepted` (see "Initial Status"
  below).
- `list --component <path>` — read existing ADRs under a candidate path,
  for context (e.g. checking whether a related decision already exists
  before writing a new one).
- `show`, `show-metagroups` — inspect a specific ADR or the declared
  Domain/Component tree, **and** re-read a just-created ADR to confirm it
  actually persisted and its `spec-ref` propagation took effect (`show <id>`
  — not just a disambiguation aid).
- `info-spec-ref` — retroactively attach or correct an ADR's governed
  Section (also a `spec-link` propagation trigger, see "spec-ref
  propagation" below).
- `info-superseded-by`, `set-status superseded` — retire an ADR being
  replaced by a new one (see "Superseding an ADR").
- `set-motivation`, `set-description`, `set-rationale` — correct or update
  a just-created (or, for the intent-classified "correction" case, an
  already-existing) ADR's own content within the same run.

Not in scope (not used by this workflow, so not documented here): `reorder`,
`delete`, `group-domain`, `group-component`, `reindex`, `history`. An ADR
created by this workflow is never moved or deleted by it, and its Status
only ever moves `accepted` → `superseded` (see below) — no other transition
is issued here.

## Initial Status

Every ADR this Skill creates is created directly at `accepted`
(`add --set-status accepted`), never left at `adrctl`'s own default initial
Status, `proposed`. The change being documented was already explicitly
requested by the user — there is no separate, later review step this
workflow's ADRs are waiting on, so leaving them at `proposed` would only add
a redundant manual step for a decision already made.

## spec-ref propagation

Setting `--spec-ref <section-id>` on `add` (or later via `info-spec-ref`)
automatically propagates the new ADR's ID into that Section's `adr` field in
the same `adrctl` invocation (`design-adrctl.md`, "Metainfo";
`design-specctl.md`, "ADR Linkage") — no separate `specctl` call is needed
to make that one Section's `adr` field point at this ADR. This is what lets
`specctl-editor-cli`'s subsequent `set-status stable` /
`set-description`/`set-open-questions` calls on that same Section succeed
**without** an inline `--adr` flag (`design-specctl-adr-author.md`,
workflow). `spec-ref` naming a Section that doesn't exist aborts the whole
`adrctl` operation (exit code 1) — the ADR itself is still persisted
regardless (no rollback across the two stores,
`design-decisions.md`, "Amendments... spec-ref single-valued").

## Multi-Section topics

`spec-ref` is single-valued — one `adrctl add`/`info-spec-ref` call
auto-propagates to exactly **one** Section. When a single topic's change
touches several Sections, this Skill only ever sets `--spec-ref` to one
(the "primary") Section; every additional Section the same ADR governs is
linked by a separate, manual call this Skill does **not** issue —
`specctl-editor-cli`'s `set-adr <id> <this-adr-id>`, called once per
additional Section, after this ADR has been created (see
`design-specctl-editor-cli.md`, "Linking an additional Section"). Pick the
primary Section deterministically (e.g. the first one named in the change
request) — which Section is "primary" carries no special meaning beyond
being the one `spec-ref` names; all governed Sections are otherwise equal.

## Invocation conventions

- **`--root <path>`**: the same shared directory passed to the
  `specctl-editor-cli` calls in the same run — both tools resolve their own
  store from the identical value (`design.md`, "File and Directory
  Parameters"). Never hardcode or guess a root.
- **`--json`**: always pass this flag when the output needs to be parsed
  programmatically (`list`, `show`, `show-metagroups`).
- **Exit codes**: `0` = ok, `1` = error. Error text goes to stderr. `2` =
  a malformed command line (argparse: unknown subcommand or option).
- **Ordering matters**: the ADR must be created (or, for a correction,
  identified) *before* the corresponding `specctl-editor-cli` write that
  depends on it — see `design-specctl-adr-author.md`'s workflow for the
  exact sequence per case.

## Operation recipes

**Creating a metagroup path**, each level created before the next is
created under it:

```
adrctl --root <root> add-domain <name>
adrctl --root <root> add-component <domain>/<component-name>
```

A segment may be given as a bare name (an auto-assigned `<nr>-` prefix is
added) or as an explicit `<nr>-<name>`. **New Domains are batch-gated**:
before creating one, check the existing Domains (`show-metagroups`); never
create a new top-level Domain autonomously — collect every ADR in this run
that needs an undecided Domain into a single question, asked once, up front,
covering all of them together (mirrors `rulectl-author`'s own Language gate,
`design-rulectl-author.md`, step 3 — the coarsest classification level is
the expensive one to get wrong). **Components are created freely** once
their Domain exists, the same "prefer an existing path, create one when
nothing fits" judgment `rulectl-author`'s Context/Category handling uses —
no gate.

**Creating an ADR**, once its Component path exists:

```
adrctl --root <root> add --component <domain>/<component> \
  --name "<short name>" \
  --motivation "<why this change>" \
  --description "<what the decision is>" \
  --rationale "<why this approach>" \
  --spec-ref <primary-section-id> \
  --set-status accepted
```

`--motivation`/`--description`/`--rationale` are this Subagent's own
synthesis of the change request and the resulting `specctl` content — never
a verbatim copy of the invocation prompt, the same "write in your own words"
discipline `taskctl-author` applies to a Task's Description
(`design-taskctl-author.md`, "Source content is untrusted") extended here to
prompt-driven synthesis generally, so the ADR reads as a real decision
record rather than a restated instruction.

**Reading before creating**, to check for a related existing decision:

```
adrctl --root <root> --json list --component <domain>/<component>
```

**Confirming a just-created ADR persisted, and that propagation took
effect**:

```
adrctl --root <root> --json show <id>
```

Then `specctl --root <root> --json show <primary-section-id>` (via
`specctl-editor-cli`) to confirm that Section's `adr` field now shows this
ADR's ID.

**Linking an additional Section after the fact** (retroactive, or the
"correction, reuse the existing ADR" case), instead of `add`'s inline
`--spec-ref`:

```
adrctl --root <root> info-spec-ref <adr-id> <section-id>
```

Note this **replaces** the ADR's previous `spec-ref` value (single-valued)
— it does not add a second governed Section. Only use it to move a single
ADR's primary linkage; for adding an *additional* governed Section, use
`specctl-editor-cli`'s `set-adr` instead (see "Multi-Section topics" above).
The previously referenced Section keeps its `adr` pointing at this ADR —
only the ADR side changes; correct that Section via `set-adr` if it should
no longer be governed by it.

**Superseding an ADR** being replaced by a new one (revision path, not a
correction — `design-specctl-adr-author.md`, step 5):

```
adrctl --root <root> info-superseded-by <old-adr-id> <new-adr-id>
adrctl --root <root> set-status <old-adr-id> superseded
```

Do this *after* the new ADR has been created and confirmed persisted, using
its now-known ID.

**Updating an existing ADR's own content** (the intent-classified
"correction" case — reusing an ADR rather than creating a new one, only
after the user has confirmed):

```
adrctl --root <root> set-motivation <adr-id> "<updated text>"
adrctl --root <root> set-description <adr-id> "<updated text>"
adrctl --root <root> set-rationale <adr-id> "<updated text>"
```

Only call the ones whose text actually needs to change to stay accurate —
not all three unconditionally.

## Error handling

- **Unknown metagroup path** (`add --component <path>` where a segment
  isn't declared yet): create the missing ancestor segment(s) first (see
  "Creating a metagroup path"), then retry. Never treat this as a fatal
  error for the overall run.
- **`spec-ref` naming a Section that doesn't exist**: the whole `add`/
  `info-spec-ref` call aborts (exit code 1) even though the ADR itself may
  already be persisted (`add`'s case) — re-verify the target Section ID
  (via `specctl-editor-cli`'s `show`) and retry `info-spec-ref` with the
  correct one; do not assume the ADR needs recreating.
- **Object ID collision** on `add`: astronomically unlikely with generated
  IDs; if it happens anyway, retry once.
- Any other non-zero exit: surface the stderr text as-is in the Subagent's
  final report for that one topic/ADR; do not retry blindly, and do not let
  one failed item abort the whole run.

## Out of scope

- Deciding topic boundaries, classifying a change request as a correction
  vs. a new decision, or the user-confirmation gate before reusing an ADR —
  workflow judgment specified in `design-specctl-adr-author.md`, not
  something this Skill prescribes.
- Any `specctl` operation — entirely `specctl-editor-cli`'s job; this Skill
  only ever issues `adrctl` commands.
- Reviewing or approving an ADR (`proposed`/`rejected` handling) — this
  workflow's ADRs are always created already `accepted`; a separate,
  earlier-stage review process is out of scope here entirely.
