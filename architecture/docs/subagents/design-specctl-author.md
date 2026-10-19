# specctl-author

Subagent that cooperatively builds and restructures a `specctl` document's
content while it is still in `draft` — adding, editing, moving, and deleting
Sections per the user's own turn-by-turn instructions. Generic — usable in
any project that has (or is willing to start) a `specctl` document; not
specific to `ai-architecture-tools`. Operates `specctl` exclusively through
the `specctl-author-cli` Skill
(`architecture/docs/skills/design-specctl-author-cli.md`) — it never invents
CLI usage of its own. Companion to `specctl-adr-author`
(`architecture/docs/subagents/design-specctl-adr-author.md`), which promotes
the Sections this Subagent drafts to `stable` and, from then on, revises them
under ADR governance — the two never call each other, and this Subagent never
touches `adrctl` or a Section's Status.

## Purpose

Given an invocation prompt describing what to add, change, restructure, or
remove in a `specctl` document, carry that instruction out directly against
the store — this run's own synthesis of what the prompt asks for, not an
atomization of some other, external document (see "Input" below). This is
the free-editing half of the `specctl` lifecycle described in `VISION.md`
("in Interaktion mit dem User die vorhandenen Tools nutzen, um dessen
Spezifikation kooperativ zu erstellen"): every Section this Subagent creates
starts at `draft`, and stays freely editable — including deletable — for as
long as it remains there. Once a Section is accepted and promoted to
`stable`, it passes out of this Subagent's reach entirely (see "Out of
scope").

## Input

- **`--root <path>`**: the shared tool directory (`design.md`, "File and
  Directory Parameters"). Always supplied explicitly by the caller — no
  default, no guessing.
- **the invocation prompt**: the sole driver of what happens this run.
  There is no separate document/file/URL input mode, unlike
  `rulectl-author`/`questctl-author`: a cooperative, incremental drafting
  workflow has no single external document to atomize by its very nature — if
  the user has a rough outline to start from, it is pasted into the prompt as
  instruction text ("lege diese Abschnitte an: ..."), read like any other
  part of the prompt, not as a separate structured input this Subagent walks
  section-by-section. Keeping exactly one input shape avoids reintroducing
  `rulectl-author`'s worklist/atomization machinery for a case this
  workflow's own nature doesn't need.
- The prompt is always the user's own words, directed at this Subagent — not
  third-party content being processed. Unlike every sibling Subagent that
  atomizes a document, there is no untrusted-source boundary to state here:
  nothing this Subagent reads is external material it must treat with
  suspicion.

## Store initialization

`specctl`, unlike `taskctl`/`rulectl`/`adrctl`, does not auto-vivify an empty
store — `init <title> [--preamble <value>]` must run once, explicitly,
before any other operation (`design-specctl.md`, "Store"). This Subagent
handles that itself rather than requiring a separate manual step:

1. On every invocation, check whether the store at `--root` is already
   initialized (`specctl-author-cli`, "Detecting initialization").
2. If not: derive a Title from the prompt if one is obviously stated or
   implied; otherwise **stop and report `deferred-awaiting-title`** for the
   whole run rather than inventing one (Title is mandatory, user-authored
   content) — this Subagent never blocks mid-run to ask; it reports what it
   needs and lets whoever invoked it re-run with a Title included in the
   next prompt, the same deferred-and-resume shape `rulectl-author` uses for
   an undecided Language (`design-rulectl-author.md`, step 3) and
   `taskctl-author` uses for an unconfirmed deletion
   (`design-taskctl-author.md`, step 7) — neither of which blocks either.
   Once a Title is available (obvious from the prompt, or supplied on a
   later invocation): call `init`, with `--preamble` only if
   the prompt supplies preamble text.
3. Proceed with the rest of the prompt's instruction against the
   now-initialized store in the same run — `init` is not a separate
   invocation the user has to trigger on its own.

This is a mechanical accommodation for `specctl`'s own lifecycle
requirement, not a new workflow concept: every other tool in this family
auto-vivifies on first `add`, and this Subagent's self-`init` step exists
only to give `specctl` the same "just works on a brand-new project" property
the others already have for free.

## Workflow

1. **Ensure the store is initialized** (see above).
2. **Read the prompt as one or more concrete operations** against the
   document: create a Section (at a given path, possibly a new one), edit a
   Section's `Description`/`OpenQuestions`, rename it, reorder it among
   siblings, move it to a different parent, or delete it (with its subtree,
   if the prompt says so). A single invocation commonly asks for several of
   these at once (e.g. "leg Kapitel X mit drei Abschnitten an und
   formuliere den ersten aus") — this Subagent fulfills the whole prompt in
   one run, the same way `rulectl-author`/`taskctl-author` process a whole
   document/request in one run, not one operation per invocation.
3. **Resolve or create metagroup paths (Part…Point) as needed**, freely —
   `add-<metagroup-type>` for any ancestor segment that doesn't exist yet,
   the same "create what's missing, prefer what already fits" judgment
   `rulectl-author`'s Context/Category handling uses. **No batched
   confirmation gate before creating a new top-level Part**, unlike
   `rulectl-author`'s Language gate or `adrctl-author`'s Domain gate: those
   gates exist because their Subagents make an autonomous judgment call
   about an *external* document with no user present to correct it
   mid-decision. Here, the user is issuing this exact instruction this exact
   turn — there is no autonomous-judgment risk a gate would protect against,
   only the normal, already-cheap `rename`/`move-to-<type>` undo path if a
   placement turns out wrong.
4. **Execute each operation directly**, continuing past any single failed
   item — no confirmation step precedes creation, edit, move, or reorder
   (there is nothing to confirm beyond what the user's own prompt already
   specified). **Deletion is also ungated** here, unlike
   `taskctl-author`'s shrink gate: draft content is explicitly, by
   definition, pre-acceptance and low-stakes, and the user is driving this
   exact turn directly rather than a batch of inferred deletions the
   Subagent itself decided on. A gate would work against the "kooperativ"
   nature of this workflow without preventing any real unattended-deletion
   risk.
5. **Verify, then report.** Re-read the store once more before compiling the
   report — for every Section this run believes it created, `show <id>` to
   reconfirm it persisted; for every Section this run deleted, confirm it's
   actually gone. The report lists, per requested operation: **done**
   (Signature/ID and, for a create, its metagroup path), or **failed** (the
   error). Retrospective, like every sibling Subagent's report — a record of
   what was done, not a plan awaiting approval.

## Status

Every Section this Subagent creates is left at `specctl`'s default initial
Status, `draft` — this Subagent never calls `set-status` at all. (Promoting
a Section to `stable` requires a valid ADR reference already set,
`design-specctl.md`'s "Status" — a mechanical gate this Subagent has no way
to satisfy on its own, since it never touches `adrctl`. Promotion is
`specctl-adr-author`'s job entirely — see "Out of scope".)

## Interaction with the specctl-author-cli Skill

This Subagent never constructs `specctl` command lines itself beyond what
`specctl-author-cli` documents — `init`, metagroup creation, Section
creation/editing/renaming/reordering/moving/deletion, and the verification
`show` calls all go through the recipes in that Skill. If a needed operation
isn't covered there, that is a gap in the Skill, not something to work
around ad hoc in the Subagent.

## Out of scope

- **Any Status change** (`draft`→`stable`, `stable`→`deprecated`,
  `stable`→`draft` rework) — entirely `specctl-adr-author`'s job for the
  first, and manual/human-only CLI calls for the other two (neither
  Subagent performs them; see `design-specctl-adr-author.md`, "Out of
  scope").
- Editing, revising, or in any way touching an already-`stable` Section —
  once a Section leaves `draft`, it is out of this Subagent's reach; a
  request to change one is `specctl-adr-author`'s job.
- Any `adrctl` operation — this Subagent has no `adrctl-author-cli` Skill
  and never needs one.
- A document/file/URL input mode — see "Input"; deliberately not built.
- A pre-write confirmation gate for creation, editing, or deletion — see
  step 4's reasoning.
- A dedicated automated test/eval harness — v1 acceptance is a manual smoke
  test against a scratch `specctl` store, same as every sibling Subagent.

## Future extensions

- **Automated regression evals.** Today's acceptance is a manual smoke
  test; the self-`init` path, the multi-operation-per-prompt fulfillment,
  and the ungated-delete behavior in particular deserve reproducible
  scenarios once a harness exists. Not designed yet.
