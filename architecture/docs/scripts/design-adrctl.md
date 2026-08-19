# adrctl

Objects are ADRs (Architecture Decision Records) whose implementation in a codebase is to be verified.

## Metagroups

- `Domain=<name>`
- `Component=<Domain>/<name>`

An ADR affecting more than one component gets its own, dedicated metagroup path that the user creates manually to represent that combination (see design.md, "exactly one metagroup"). There is no tool support for multi-component assignment; referencing a path that doesn't exist aborts with an error.

## Metainfo

- `superseded-by=<id of the ADR>` — only set when status is `superseded`.

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
