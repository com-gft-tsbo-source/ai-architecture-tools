# specctl-editor-cli

Skill that wraps the `specctl` CLI for the `specctl-adr-author` Subagent
(`architecture/docs/subagents/design-specctl-adr-author.md`). Purely an
instructional reference — a `SKILL.md`, no executable wrapper code. The
invoking agent calls the `specctl` binary itself via Bash; this Skill only
teaches it how to do that correctly for the ADR-governed side of the
`specctl` lifecycle: promoting a Section to `stable` and revising one that
already is. Companion to `specctl-author-cli`
(`architecture/docs/skills/design-specctl-author-cli.md`), which covers the
full, ungated CRUD surface `specctl-author` uses for `draft` content — the
two Skills' command surfaces are disjoint except for the read-only
`show`/`list` commands both need, and neither Skill's Subagent calls the
other's exclusive commands. Always used alongside `adrctl-author-cli`
(`architecture/docs/skills/design-adrctl-author-cli.md`) in the same run —
see `design-specctl-adr-author.md` for how the two interleave.

## Scope

Deliberately the *narrow*, ADR-gated slice of `specctl` — everything this
Skill's Subagent is allowed to do already implies a governing ADR exists or
is being created in the same run:

- `set-status <id> stable [--adr <id>]` — promote a Section out of `draft`.
  This Skill **never** passes `deprecated`, and never calls `set-status`
  with `--force` (a `stable`→`draft` rework) — both are manual, human-only
  operations outside this workflow entirely (`design-specctl-adr-author.md`,
  "Out of scope").
- `set-description`, `set-open-questions` (each with optional `--adr <id>`)
  — change a `stable` Section's content once its governing ADR is
  established.
- `set-adr <id> <value>` — the manual linkage correction command
  (`design-specctl.md`, "Operations"), used here for its documented purpose
  extended to one more concrete case: attaching an already-minted ADR to an
  **additional** Section the same topic touches, beyond the one Section
  `adrctl add --spec-ref` auto-propagated to (`spec-ref` is single-valued —
  see `design-adrctl-author-cli.md`, "Multi-Section topics"). Because
  `set-adr` is **not validated** (`design-specctl.md`: "Set either manually
  ..., not validated — a correction tool"), only ever pass an ADR ID this
  same run just created or otherwise confirmed exists via `adrctl show` —
  never a guessed or unverified one.
- `show`, `list` (`--status`/`--under`/`--adr`) — resolve which Section(s)
  a change request targets, read a Section's current `adr` value before
  deciding whether this is a first-time promotion or a revision, and
  re-read a just-changed Section to confirm the write persisted.
- `show-metagroups` — disambiguate a Section reference against the
  document's actual structure when the invocation prompt's own wording is
  ambiguous.

Not in scope (belongs to `specctl-author-cli` instead, and this Skill's
Subagent never calls it): `init`, `set-title`, `set-preamble`,
`add-<level>`, `rename`, `reorder`, `move-to-<level>`, `delete` — creating,
renaming, restructuring, or removing Sections is entirely `specctl-author`'s
job; this Subagent only ever revises content that already exists. Also not
in scope: `render`, `history`.

## Reading a Section's current ADR state

Before deciding whether a change is a first-time promotion or a revision
(`design-specctl-adr-author.md`, step 2), read the target Section:

```
specctl --root <root> --json show <id>
```

- `status: draft`, `adr` absent → first-time promotion path.
- `status: stable`, `adr` present → revision path (every `stable` Section
  reachable by this workflow has an `adr` already set, since promotion
  through this same Skill is the only way a Section governed by this
  workflow ever reaches `stable` in the first place — see
  `design-specctl-adr-author.md`, "Invariant").

## Invocation conventions

- **`--root <path>`**: always supplied by the caller, shared with the
  `adrctl` calls made in the same run (both tools resolve their own store
  from the identical `--root` value — `design.md`, "File and Directory
  Parameters").
- **`--json`**: always pass this flag when the output needs to be parsed
  programmatically (`show`, `list`, `show-metagroups`).
- **Exit codes**: `0` = ok, `1` = error. Error text goes to stderr.
- **Ordering matters.** Unlike `specctl-author-cli`'s independent,
  order-insensitive operations, this Skill's calls are almost always part
  of a fixed sequence with `adrctl` calls interleaved — see
  `design-specctl-adr-author.md`'s workflow for the exact order (mint the
  ADR first, *then* the `specctl` write that depends on it existing).
  Never call `set-status stable` or `set-description`/`set-open-questions`
  on an unpromoted/ungoverned `stable`-bound Section without a governing
  `adr` already in place — the command will simply be rejected, but calling
  it out of order also means the preceding `adrctl` step was skipped.

## Operation recipes

**Promoting a Section to `stable`**, once its founding ADR has already been
created via `adrctl-author-cli` (which auto-propagates the ADR's ID into
this Section's `adr` field — no `--adr` flag needed here):

```
specctl --root <root> set-status <id> stable
```

If, for any reason, propagation didn't already set `adr` (e.g. the ADR's
`--spec-ref` targeted a different Section), pass it explicitly instead:

```
specctl --root <root> set-status <id> stable --adr <adr-id>
```

**Editing a `stable` Section's content**, once its governing ADR is set
(same two forms — omit `--adr` when propagation already set it, supply it
inline otherwise):

```
specctl --root <root> set-description <id> "<new description>"
specctl --root <root> set-open-questions <id> "<new open questions text>"
```

**Linking an additional Section to an already-minted ADR** (multi-Section
topic, or the intent-classified "correction, reuse the existing ADR" case —
`design-specctl-adr-author.md`, steps 4 and 5):

```
specctl --root <root> set-adr <id> <adr-id>
```

Not logged in the Section's own History (`design-specctl.md`, "History") —
this is expected; the ADR's own History (via `adrctl`) is the authoritative
trail for *why*.

**Resolving a change request's target Section(s)**, before acting:

```
specctl --root <root> --json list [--status stable] [--under "<path>"]
specctl --root <root> --json show <id>
specctl --root <root> --json show-metagroups
```

Matching a prompt's natural-language reference against `list`/`show`
output is judgment, the same way `taskctl-author`'s shrink-target
resolution is — not exact-string matching.

## Error handling

- **"requires a valid adr" rejection** on `set-status`/`set-description`/
  `set-open-questions`: means the preceding `adrctl` step (mint or link the
  ADR) was skipped or hasn't propagated yet — go back and do that first,
  then retry. Never work around this by inventing an `--adr` value.
- **`set-adr` "not found"-shaped failures don't exist** (the command isn't
  validated) — but passing a bad ID here silently corrupts the linkage
  with no error at all. The discipline is entirely on the caller: only ever
  pass an ID this run itself just created via `adrctl add` or confirmed via
  `adrctl show`.
- Any other non-zero exit: surface the stderr text as-is in the Subagent's
  final report for that one Section/topic; do not retry blindly, and do
  not let one failed item abort the whole run.

## Out of scope

- Creating, renaming, restructuring, or deleting Sections — entirely
  `specctl-author-cli`'s job.
- `deprecated` and `stable`→`draft` rework (`--force`) — manual, human-only
  CLI calls, never issued by this Skill's Subagent.
- Judging whether a change request reads as a correction or a new decision,
  deciding topic boundaries, or the user-confirmation gate before reusing
  an ADR — workflow judgment specified in `design-specctl-adr-author.md`,
  not something this Skill prescribes (mirrors `rulectl-author-cli`'s own
  "purely a CLI-contract reference" stance).
