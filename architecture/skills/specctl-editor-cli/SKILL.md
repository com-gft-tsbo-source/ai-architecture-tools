---
name: specctl-editor-cli
description: Wraps the specctl CLI for the ADR-governed side of its lifecycle — promoting a Section to stable and revising one that already is (set-status stable, set-description/set-open-questions with --adr, set-adr, list, show). Always used alongside adrctl-author-cli in the same run. Use whenever a stable specctl Section is being promoted or revised. Not for creating, renaming, restructuring, or deleting Sections — that's specctl-author-cli's job, used only for draft content.
---

Full spec: `architecture/docs/skills/design-specctl-editor-cli.md`.

You operate the `specctl` CLI (already on `PATH`, or run as
`python3 <repo>/architecture/scripts/specctl.py`) via Bash for the
ADR-governed side of its lifecycle: promoting a Section to `stable`, and
revising one that already is. This is a reference, not a wrapper script —
call `specctl` yourself, following the recipes below. Always used alongside
`adrctl-author-cli` in the same run — see `design-specctl-adr-author.md` for
the exact interleaving.

## Scope

Deliberately narrow — everything here already implies a governing ADR
exists or is being created in the same run:

- `set-status <id> stable [--adr <id>]` — promote out of `draft`. **Never**
  pass `deprecated`, and never pass `--force` (a `stable`→`draft` rework) —
  both are manual, human-only, outside this workflow entirely.
- `set-description`, `set-open-questions` (each with optional `--adr <id>`)
  — change a `stable` Section's content once its governing ADR exists.
- `set-adr <id> <value>` — the manual linkage command, used for its
  documented purpose extended to one concrete case: attaching an
  already-minted ADR to an **additional** Section a topic touches, beyond
  the primary one `adrctl add --spec-ref` auto-propagated to (`spec-ref` is
  single-valued — see `adrctl-author-cli`, "Multi-Section topics"). **Not
  validated** — only ever pass an ADR ID you just created this run or
  confirmed via `adrctl show`, never a guessed one.
- `show`, `list` (`--status`/`--under`/`--adr`) — resolve which Section(s) a
  change request targets, read a Section's current `adr` before deciding
  promotion vs. revision, and re-read a just-changed Section to confirm the
  write persisted.

Not in scope (`specctl-author-cli`'s job instead — never call these):
`init`, `set-title`, `set-preamble`, `add-<level>`, `rename`, `reorder`,
`move-to-<level>`, `delete`. Also not in scope: `render`, `history`. **No
`show-metagroups`** — `specctl` doesn't have one (unlike `adrctl`); use
`list --under "<path>"` instead.

## Reading a Section's current ADR state

Before deciding promotion vs. revision:

```
specctl --root <root> --json show <id>
```

- `status: draft`, `adr` absent → first-time promotion.
- `status: stable`, `adr` present → revision (every `stable` Section this
  workflow reaches already has an `adr` set, since promotion through this
  same Skill is the only way one ever gets there).

## Conventions

- **`--root <path>`**: the same value passed to the `adrctl` calls in the
  same run — both tools resolve their own store from it.
- **`--json`**: pass it whenever parsing output (`show`, `list`).
- **Exit codes**: `0` = ok, `1` = error, error text on stderr.
- **Ordering matters.** These calls are almost always part of a fixed
  sequence with `adrctl` calls interleaved: mint the ADR first, *then* the
  `specctl` write that depends on it existing. Calling `set-status stable`
  or `set-description`/`set-open-questions` on an ungoverned Section without
  its ADR already in place is simply rejected.

## Recipes

**Promote**, once the founding ADR exists (auto-propagated, no `--adr`
needed):

```
specctl --root <root> set-status <id> stable
```

If propagation didn't set it (e.g. `--spec-ref` targeted a different
Section), pass it explicitly: `... set-status <id> stable --adr <adr-id>`.

**Edit `stable` content**, same two forms:

```
specctl --root <root> set-description <id> "<new description>"
specctl --root <root> set-open-questions <id> "<new open questions text>"
```

**Link an additional Section to an already-minted ADR** (multi-Section
topic, or a confirmed correction):

```
specctl --root <root> set-adr <id> <adr-id>
```

Not logged in the Section's own History — expected; the ADR's own History
(via `adrctl`) is the authoritative trail for *why*.

**Resolve a change request's target Section(s)**:

```
specctl --root <root> --json list [--status stable] [--under "<path>"]
specctl --root <root> --json show <id>
```

Matching a prompt's natural-language reference against `list`/`show` output
is judgment, not exact-string matching.

## Error handling

- **"requires a valid adr" rejection** on `set-status`/`set-description`/
  `set-open-questions`: the preceding `adrctl` step (mint or link) was
  skipped or hasn't propagated — go do that first, then retry. Never invent
  an `--adr` value.
- **`set-adr` has no "not found"** (it isn't validated) — but a bad ID
  silently corrupts the linkage with no error at all. Discipline is on you:
  only pass an ID you just created or confirmed exists.
- Any other non-zero exit: report the stderr text as-is for that one
  Section/topic; don't retry blindly, don't let one failure stop the rest
  of the run.

## Out of scope

Creating, renaming, restructuring, or deleting Sections; `deprecated` and
`stable`→`draft` rework; judging correction-vs-new-decision or topic
boundaries or the confirmation gate — all workflow judgment in
`design-specctl-adr-author.md`, not something this Skill prescribes.
