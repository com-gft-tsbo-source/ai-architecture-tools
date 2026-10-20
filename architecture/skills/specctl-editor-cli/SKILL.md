---
name: specctl-editor-cli
description: Use with adrctl-author-cli when specctl-adr-author promotes existing Sections to stable or revises ADR-governed content. Covers Section reads, links and content/status writes; not for Section creation, restructuring, deletion or manual-only lifecycle changes.
---

Full spec: `architecture/docs/skills/design-specctl-editor-cli.md`.

Use `specctl` from PATH via Bash, alongside `adrctl-author-cli`.
The permitted operations are set-status stable, set-description,
set-open-questions, set-adr, list and show. Do not initialize documents,
change their title or preamble, add, rename, reorder, move or delete Sections,
call render/history, deprecate Sections or use --force for rework.
Inspect structure with list --under; show-metagroups does not exist.

## Conventions and reads

Use exactly the explicit shared `--root` for specctl and adrctl. Use --json
before parsed reads. Writes use the six-character JSON id, not Signature;
show accepts both. Exit code 0 means success, 1 means an error on stderr,
and 2 means malformed CLI usage.

```
specctl --root <root> --json list [--status stable] [--under "<path>"]
specctl --root <root> --json show <id>
```

Match prompt targets by meaning and read both their actual status and ADR.
A draft needs promotion even if an earlier interrupted run linked it. A stable
Section with an ADR needs revision; one without an ADR needs founding
governance without a status change. Deprecated Sections are outside scope.
The Agent groups topics and decides correction intent and approval gates.

## Linked writes

Create or identify the governing ADR through its Skill before dependent
writes. Verify its existence and propagated link, then promote the targeted
drafts before editing their content:

```
specctl --root <root> set-status <id> stable [--adr <adr-id>]
specctl --root <root> set-description <id> "<text>" [--adr <adr-id>]
specctl --root <root> set-open-questions <id> "<text>" [--adr <adr-id>]
specctl --root <root> set-adr <id> <adr-id>
```

Normally omit --adr because ADR spec-ref already propagated the primary
link. Additional Sections in the same topic use set-adr. It is NOT
validated and NOT logged in Section History: pass only an ADR ID just
created or verified via adrctl show. ADR History supplies decision context.
One topic's ADR can link several draft/stable Sections before promotion/edits.

## Verification, retirement and errors

Use show to verify Section content/status/ADR after writes and again in
the Agent's final audit. After verified topic completion, inspect ALL
remaining references before old-ADR retirement:

```
specctl --root <root> --json list --adr <old-adr-id>
```

Do not add a status or path filter: any remaining Section reference keeps
the ADR accepted. Only a successful query with no references permits
superseding through adrctl-author-cli.
- `requires a valid 'adr' reference`: mint/link the governing ADR first,
  then retry; never invent one.
- Nonexistent inline ADR: `... adr '<id>': no object with ID '<id>'`.
  On draft content --adr is ignored and not stored: establish the link
  through adrctl or set-adr, never --adr on a draft.
- Bad set-adr silently corrupts linkage; never treat lack of validation
  errors as proof of existence.
- Other nonzero exits: report Section/topic stderr unchanged, no blind
  retries. Stop dependent topic steps on failure; independent topics proceed.
