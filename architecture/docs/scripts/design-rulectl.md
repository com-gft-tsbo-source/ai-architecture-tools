# rulectl

Objects are checks that can be applied to a code or data base.

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

- `tasklist`: convert existing objects into a task list suitable for taskctl. **Deferred — not yet specified**; will be designed separately.

## User Content

- `Description`
- `Procedure`

Each block may contain Markdown and is stored with a `> ` prefix per line.
