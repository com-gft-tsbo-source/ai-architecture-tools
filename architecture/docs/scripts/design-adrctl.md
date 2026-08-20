# adrctl

Objects are ADRs (Architecture Decision Records) whose implementation in a codebase is to be verified.

## Store

Store name `adrs` (design.md, "File and Directory Parameters"): resolves to `<shared-dir>/adrs.md` or `<shared-dir>/adrs`. Default mode when neither exists yet: **directory** — the 2-level Domain/Component hierarchy reads more naturally as nested directories than as one growing file.

## Metagroups

- `Domain=<name>`
- `Component=<Domain>/<name>`

An ADR affecting more than one component gets its own, dedicated metagroup path that the user creates manually to represent that combination (see design.md, "exactly one metagroup"). There is no tool support for multi-component assignment; referencing a path that doesn't exist aborts with an error.

## Metainfo

- `superseded-by=<id of the ADR>` — only set when status is `superseded`.
- `spec-ref=<id>` — names the specctl Section this ADR governs. Single-valued, like every other Metainfo field (design-decisions.md, "Amendments": kept single-valued rather than generalizing the shared Metainfo mechanism for this one field's repeatable use case) — one ADR names at most one governed Section; setting it again replaces the previous value. No file component: `spec-ref` resolves within the same shared `--root` directory the triggering `adrctl` invocation itself received (design.md, "File and Directory Parameters"), so the target specctl store is found the same way `adrctl`'s own store is. After a successful `add`, `set-status`, or `info-spec-ref` that leaves `spec-ref` set, the shared `lib/spec_link.py` module (used by both `adrctl.py` and `specctl.py`) updates the `adr` Metainfo field on the referenced specctl Section and logs an `M` History entry there (`lib/spec_store.py`'s `receive_adr_link` — see design-specctl.md, "ADR Linkage", for the full mechanism and its distinction from the manual `set-adr`). A `spec-ref` naming a Section that doesn't exist aborts the `adrctl` operation (exit code 1) — the ADR itself remains persisted regardless, since the two stores are not updated transactionally (design-decisions.md, "Amendments").

## Status

- `proposed` (initial status)
- `accepted`
- `deprecated`
- `superseded`
- `rejected`

No automatic transitions — all status changes are manual, made by a user or an agent acting on instruction.

Note: unlike rulectl, adrctl has no `tool`/`tool-rule`/`checkable` metainfo — ADRs are verified exclusively by an LLM/agent, never by an external tool.

## Operations

In addition to the general operations from design.md, adrctl supports:

- `tasklist`: convert existing objects into a task list suitable for taskctl. **Deferred — not yet specified**; will be designed separately.

## User Content

- `Motivation`
- `Description`
- `Rationale`

Each block may contain Markdown and is stored with a `> ` prefix per line.
