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

Accepts the source document as exactly one of:
- a **file path** (the Subagent reads it itself),
- **text pasted directly** into the invocation prompt, or
- a **URL** (the Subagent fetches it itself).

All three forms are supported without the caller needing to pick one in
advance. Fetching multiple URLs/documents in one run is out of scope for
v1 (see "Out of scope").

**Fetching a URL**: try `WebFetch` first. Fall back to `Bash` (`curl`) when
`WebFetch` fails (network/access error) or when it would not yield the
guideline text faithfully — e.g. a raw `.md`/`.txt` file where `WebFetch`'s
rendering could summarize or reformat content the extraction step (step 2)
needs verbatim. If both fail, or the fetched content is empty, **abort the
run immediately** with a clear error and create no Rule at all — unlike a
single failed `add` (step 5), a failed fetch means there is no document to
process, not one bad item among many.

## `--root`

Always supplied explicitly by the caller (user or orchestrating Skill/agent)
— there is no default or auto-discovered path. The Subagent is stateless
with respect to *which* project's rule store it targets; `rulectl` itself
auto-creates the store on first use if `--root` points at a location that
doesn't exist yet, so a fresh project is not a precondition.

## Workflow

1. **Obtain the document** (read the file path, use the pasted text
   directly, or fetch the URL — see "Input" above for the fetch/fallback/
   abort rules).
2. **Build a structural worklist from the document's own outline.** Walk the
   document's headings, sub-headings, and numbered/bulleted items —
   whatever structure it actually has — top to bottom, and produce one
   worklist entry per structural unit. This is a structured walk of the
   outline, not a free-form pass over the flowing text: a unit must never be
   able to disappear before it is ever considered. If the document has no
   discernible structure (plain prose, no headings), treat the whole
   document as a single unit.

   Every worklist entry gets one of three explicit dispositions:
   - **own Rule**: this unit becomes one candidate Rule (needs at minimum a
     short Name and a Description — judgment still governs exactly how a
     unit's content is worded as a Rule, just not *whether* the unit is
     considered at all).
   - **merged into `<sibling unit>`**: this unit's content is folded into a
     named sibling/neighboring unit's candidate Rule instead of becoming its
     own (e.g. a short sub-section that only elaborates on its parent).
   - **no-rule-needed (`<reason>`)**: this unit produces no Rule at all —
     state why (e.g. purely introductory text, a table of contents, out of
     scope for quality guidelines).

   The worklist itself — every structural unit with its disposition — is
   the artifact steps 3-6 work from and step 6 reconciles against; it is not
   discarded once the "own Rule" entries have been extracted into
   candidates.
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
6. **Report — reconciled against the step 2 worklist, not just a log of
   executed `add` calls.** Every worklist entry from step 2 must appear in
   the report in exactly one of four categories, with no exceptions:
   - **created**: Signature/ID and metagroup path.
   - **skipped-likely-duplicate**: the existing Rule it matched.
   - **failed**: the error from the failed `add`/corrective call.
   - **no-rule-needed**: the reason — either the disposition already given
     in step 2 (a stated reason, or "merged into `<sibling unit>`") for a
     unit that was never a candidate, or, for a unit that *was* a candidate,
     any reason it ends up here instead of "created" other than being a
     duplicate or a failure.

   A worklist entry with no corresponding report entry is a defect in this
   step, not an acceptable omission — reconciling against the full worklist
   (rather than just listing what was actually created) is what makes a
   silently dropped structural unit impossible. Also report newly created
   metagroup paths. The whole report remains retrospective — it documents
   what was done, not a plan awaiting approval.

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
  For a URL source, this is the full URL, plus an anchor/heading when one is
  identifiable in the fetched content. Cheap to produce, and the only field
  that gives later readers traceability back to the source document.
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
- Processing more than one document/URL per run — a single invocation takes
  exactly one source (file path, pasted text, or URL); crawling a site or
  batching several URLs is a possible later extension, not v1.
