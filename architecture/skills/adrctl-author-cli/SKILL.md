---
name: adrctl-author-cli
description: Use with specctl-editor-cli when specctl-adr-author needs to create accepted ADRs, repair their Section links, apply confirmed corrections or retire fully replaced decisions. Not for approving proposed ADRs, deleting ADRs or restructuring their placement.
---

Full spec: `architecture/docs/skills/design-adrctl-author-cli.md`.

Use `adrctl` from PATH via Bash, alongside `specctl-editor-cli`.
You may use add-domain/component, add, list, show, show-metagroups,
info-spec-ref, info-superseded-by, set-status superseded, set-motivation,
set-description and set-rationale. Do not call reorder, delete, regroup,
reindex or history. All created ADRs are
accepted; topic decisions, correction confirmation and Domain gates belong
to the Agent. Use no other operations.

## Conventions and placement

Use exactly the explicit shared root for both tools. Put --json BEFORE
parsed list/show/show-metagroups. Exit code 0 means success, 1 means an
error on stderr, and 2 means malformed CLI usage.
Inspect existing Domains; new ones require ONE batched upfront decision,
never autonomous creation. Components under an existing Domain are free.
Create parents before children:

```
adrctl --root <root> --json show-metagroups
adrctl --root <root> add-domain <name>
adrctl --root <root> add-component <domain>/<component>
adrctl --root <root> --json list --component <domain>/<component>
```

show-metagroups returns a JSON array of paths. List existing ADRs for context.

## Creation and linkage

```
adrctl --root <root> add --component <domain>/<component> --name "<name>" \
  --motivation "<why change>" --description "<decision>" \
  --rationale "<why this approach>" --spec-ref <primary-section-id> \
  --set-status accepted
adrctl --root <root> --json show <adr-id>
adrctl --root <root> info-spec-ref <adr-id> <section-id>
```

ADR text is synthesized from request/result, never copied verbatim.
Spec-ref has one value. Setting it through add or info-spec-ref propagates
the ADR ID to that Section's adr field. Verify both the persisted ADR and
the primary Section through the editor Skill before dependent writes.
Link additional Sections through specctl set-adr, without creating a second
ADR for each Section. Replacing spec-ref leaves the
previous Section's adr unchanged; correct it via editor Skill if needed.
A nonexistent spec-ref fails exit 1 AFTER the ADR may be persisted:
no cross-store rollback. Verify IDs and repair via info-spec-ref;
never recreate an already-persisted ADR just to repair propagation.

## Retirement and correction

Retire only after the Agent verifies the replacement topic AND the editor
Skill's unfiltered list --adr <old-id> succeeds with no remaining references.
Otherwise keep old ADR accepted and superseded-by unchanged; new ADR text
records precise partial replacements. A query error is not an empty result.

```
adrctl --root <root> info-superseded-by <old-id> <new-id>
adrctl --root <root> set-status <old-id> superseded
```

For confirmed corrections (or corrections to a just-created ADR), change
ONLY fields actually stale; a pure wording fix may need no ADR update:

```
adrctl --root <root> set-motivation <id> "<text>"
adrctl --root <root> set-description <id> "<text>"
adrctl --root <root> set-rationale <id> "<text>"
```

## Errors

If a path is unknown, create the permitted ancestors after the Domain
decision and retry. If a spec-ref Section is missing, verify its ID and the
persisted ADR, then repair the link rather than creating a duplicate ADR.
Retry an ID collision on add once. For other errors, report the topic's or
ADR's stderr unchanged and avoid blind retries. Stop dependent steps for
that topic, but continue independent topics. Use the editor Skill for
specctl calls.
