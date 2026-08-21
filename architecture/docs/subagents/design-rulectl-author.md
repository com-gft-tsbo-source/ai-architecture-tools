# rulectl-author

Subagent that turns a document into `rulectl` Rules. Generic — usable in any
project that has (or is willing to start) a `rulectl` store; not specific to
`ai-architecture-tools`. Operates `rulectl` exclusively through the
`rulectl-author-cli` Skill (`architecture/docs/skills/design-rulectl-author-cli.md`)
— it never invents CLI usage of its own.

## Purpose

Given a document that expresses quality guidelines (a style guide, a review
checklist, informal notes, ...), break it into individual, `rulectl`-sized
Rules, place each under a fitting Language/Context/Category path, and persist
them. This is the authoring half of the rulectl workflow; a separate, future
Subagent (and its own wrapping Skill) covers checking a codebase against
already-authored Rules — out of scope here.

## Input

Accepts the source document either as:
- a **file path** (the Subagent reads it itself), or
- **text pasted directly** into the invocation prompt.

Both forms are supported without the caller needing to pick one in advance.

## `--root`

Always supplied explicitly by the caller (user or orchestrating Skill/agent)
— there is no default or auto-discovered path. The Subagent is stateless
with respect to *which* project's rule store it targets; `rulectl` itself
auto-creates the store on first use if `--root` points at a location that
doesn't exist yet, so a fresh project is not a precondition.

## Workflow

1. **Read the document** (from the file path, or use the pasted text
   directly).
2. **Segment it into candidate Rules.** Judgment call, not a fixed
   heuristic — group related sentences into one Rule where they express a
   single guideline, split apart where a paragraph bundles unrelated
   concerns. Each candidate Rule needs at minimum a short Name and a
   Description.
3. **Determine each Rule's metagroup path** (Language/Context/Category):
   - Prefer an existing path (`show-metagroups`, or `list`) that already
     fits.
   - **Context and Category**: create new ones freely (`add-context`,
     `add-category`) when nothing existing fits — this is the expected,
     natural granularity when carving up a new document.
   - **Language**: never create a new one autonomously. If no existing
     Language fits, stop and ask the user before proceeding with any Rule
     that would need it — introducing a new Language is a structural
     decision, not a per-document one.
4. **Duplicate check.** Before creating each Rule, `list` the existing Rules
   under its target Category path and compare Name/Description for likely
   overlap. A likely duplicate is **skipped** — it is not created — and
   recorded (with a reference to the existing Rule it matches) for the final
   report. This is judgment, not exact-string matching; when in doubt
   whether two Rules really say the same thing, prefer creating the new one
   over silently dropping a genuinely distinct guideline.
5. **Create each remaining candidate Rule** via the `rulectl-author-cli`
   Skill, populating fields as described under "Metainfo" below. No
   confirmation step with the user precedes this — the Subagent writes
   directly, sequentially, continuing past any single failed item (see
   `design-rulectl-author-cli.md`, "Error handling").
6. **Report.** After processing every candidate Rule, produce a summary:
   created Rules (Signature/ID, metagroup path), newly created metagroup
   paths, skipped likely-duplicates (with the existing Rule each one
   matched), and any items that failed to create (with the error). This
   report is retrospective — it documents what was done, not a plan awaiting
   approval.

## Status

Every created Rule is left at `rulectl`'s default initial status, `active`
— never `draft`. There is no post-creation review gate; a Rule is live
(and will be picked up by a future `rulectl tasklist` export) as soon as
this Subagent creates it. This is a deliberate choice: correctness rests on
the duplicate check (step 4) and the retrospective report (step 6), not on a
pre-activation buffer.

## Metainfo population

Per created Rule:

- **`source`**: always set, pointing back to the originating document and,
  where identifiable, the specific section/passage the Rule was drawn from.
  Cheap to produce, and the only field that gives later readers
  traceability back to the source document.
- **`checkable`**: `llm` unless the document itself explicitly names a
  checking tool for that guideline (e.g. "enforced by eslint's
  `no-unused-vars`") — only then is it set to that tool's name, with `tool`
  and `tool-rule` populated from the same explicit mention. Never inferred
  or guessed from the guideline's general subject matter.
- **`weight`**: left unset unless the document explicitly states a priority
  or severity for that guideline. Not inferred from tone or position in the
  document.

## Interaction with the rulectl-author-cli Skill

This Subagent never constructs `rulectl` command lines itself beyond what
`rulectl-author-cli` documents — metagroup creation, Rule creation, the
duplicate-check `list` call, and any corrective `info-*`/`set-*` call all go
through the recipes in that Skill. If a needed operation isn't covered
there, that is a gap in the Skill, not something to work around ad hoc in
the Subagent.

## Out of scope

- Checking existing code/documents against already-authored Rules
  (`tasklist` and everything downstream) — a separate, future Subagent.
- A pre-write approval step — deliberately not part of this workflow (see
  "Status" above).
- A dedicated automated test/eval harness — v1 acceptance is a manual smoke
  test against a scratch `rulectl` store.
