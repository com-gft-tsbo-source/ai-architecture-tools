# adrctl

Objects are ADRs (Architecture Decision Records) whose implementation in a codebase is to be verified.

## Metagroups

- `Domain=<name>`
- `Component=<Domain>/<name>`

An ADR affecting more than one component gets its own, dedicated metagroup path that the user creates manually to represent that combination (see design.md, "exactly one metagroup"). There is no tool support for multi-component assignment; referencing a path that doesn't exist aborts with an error.

## Metainfo

- `superseded-by=<id of the ADR>` — only set when status is `superseded`.
- `spec-ref=<file>#<id>` — repeatable; names the specctl Section(s) this ADR governs. Whenever this ADR is created or has its status changed, the shared `lib/spec_link.py` module (used by both `adrctl.py` and `specctl.py`) automatically updates the `adr` Metainfo field on every referenced specctl object, logging the change there too. See design-specctl.md, "ADR Linkage", for the full mechanism. A `spec-ref` pointing at a file or object ID that doesn't exist aborts the operation. **Deferred — not yet implemented** (see design-specctl.md, "ADR Linkage", Implementation status): `specctl` ships first, standalone; this field and its propagation follow in a later change.

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
