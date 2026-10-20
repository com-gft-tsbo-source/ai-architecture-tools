# specctl-adr-author

Subagent that promotes `specctl` Sections to `stable` and, from then on,
revises them — always under `adrctl` governance. Generic — usable in any
project that has (or is willing to start) `specctl`/`adrctl` stores sharing
one `--root`; not specific to `ai-architecture-tools`. Operates `specctl`
exclusively through the `specctl-editor-cli` Skill
(`architecture/docs/skills/design-specctl-editor-cli.md`) and `adrctl`
exclusively through the `adrctl-author-cli` Skill
(`architecture/docs/skills/design-adrctl-author-cli.md`) — it never invents
CLI usage of its own for either tool. The first Subagent in this project
family whose workflow spans two tools' CLIs through two separate Skills,
rather than one tool through one — a deliberate exception (see
`design-decisions.md`, "Amendments... specctl-author/specctl-adr-author
design") to the otherwise-uniform one-Subagent-one-Skill pattern, because
every stable-phase change is a single, atomic unit of work coupling a
`specctl` edit to the `adrctl` decision that authorizes it; splitting that
coupling across an invocation boundary would only reintroduce the ordering
problem it exists to solve (see "Workflow" below).

Companion to `specctl-author`
(`architecture/docs/subagents/design-specctl-author.md`), which creates
every Section this Subagent later promotes — the two never call each other.
This Subagent **never creates a new Section**: it only ever promotes a
`draft` Section that already exists, or revises one that's already
`stable`.

## Purpose

Given an invocation prompt describing a change to make to the specification
— "accept Section X as final," "change what Section Y says about Z," "fix
the wording I just wrote in Section W" — apply that change through the
mechanism `specctl`'s own `stable` Status requires: a governing `adrctl`
Architecture Decision Record, created (or, for a genuine correction, reused)
as part of the same run, one ADR per coherent topic the change addresses.
This is the ADR-governed half of the `specctl` lifecycle described in
`VISION.md`'s Grundidee: once a Section is accepted, "werden alle
Änderungen mit Hilfe von ADRs des `adrctl`-Tools erzeugt."

## Input

- **`--root <path>`**: the shared tool directory, passed identically to
  both the `specctl-editor-cli` and `adrctl-author-cli` calls this Subagent
  makes — both tools resolve their own store from the same value
  (`design.md`, "File and Directory Parameters"). Always supplied explicitly
  by the caller.
- **the invocation prompt**: a natural-language change request, always the
  user's own words directed at this Subagent (not third-party content —
  there is no untrusted-source boundary to state here, the same reasoning
  `specctl-author` gives for its own prompt-only input). Drives three
  independent things:
  1. **Which Section(s) are targeted** — resolved via `list`/`show`
     against the current document, matching the prompt's natural-language
     reference the same judgment-based way `taskctl-author`'s shrink-target
     resolution works (`design-taskctl-author.md`, step 7), not
     exact-string matching.
  2. **How many topics the change addresses, and which Section(s) each
     touches** — see "Topic decomposition" below.
  3. **Whether each touched Section's part of the change reads as a
     correction to something already governed, or a new decision** — see
     "Intent classification" below.

## Read actual lifecycle state

Use each Section's Status and current ADR link, not an assumed history of
how it was created. Draft Sections can already carry a link after an
interrupted run; stable Sections created manually can lack one. Read and
verify both stores before choosing dependent operations. CLI calls are not
transactional across stores.

## Workflow

1. **Resolve the invocation prompt's target Section(s)**
   (`specctl-editor-cli`'s `list`/`show` — `specctl` has no
   `show-metagroups`, unlike `adrctl`).
2. **Decompose the change into topics.** A single invocation commonly
   addresses more than one coherent topic (e.g. "passe Abschnitt A an X an
   und ergänze Abschnitt B um Y") — read the prompt's own structure as the
   primary signal for where one topic ends and another begins, refined by
   judgment where the prompt's phrasing doesn't cleanly separate them, the
   same "atomic candidates" reasoning `rulectl-author` applies to a
   document (`design-rulectl-author.md`, step 2), applied here to a change
   request instead. Every topic ends up targeting one or more Sections (see
   "Multi-Section topics" below for more than one).

   **No duplicate-check step here**, unlike `rulectl-author`/
   `questctl-author`/`taskctl-author`'s own duplicate-detection passes:
   those exist because those Subagents extract *candidates* from ambiguous
   source material with real risk of restating the same guideline/question/
   task twice. A topic here comes directly from an explicit, already-decided
   user change request — there is no ambiguous candidate pool to
   de-duplicate against, and inventing one would only add a check against a
   risk this workflow's own shape doesn't have.
3. **Classify each topic and its targeted Sections.** Read current Status,
   `adr`, and content. Reject deprecated Sections; never infer promotion
   solely from the presence or absence of an ADR. A draft Section may
   already have a link from an interrupted earlier run.
   - A topic containing a first-time promotion or a substantively new
     decision follows steps 4-5: exactly one new ADR for the whole topic,
     including any draft and stable Sections it jointly affects.
   - A topic consisting only of corrections to governed stable content
     follows step 6's confirmation/reuse path. Judge correction intent
     semantically from the user's request, not by literal keyword matching.
     Do not reuse an old ADR to authorize a first-time promotion.
   - A stable Section without a governing ADR needs a founding ADR through
     steps 4-5, without a status transition.
4. **Create and link one ADR per topic**, including first-time promotion:
   1. Before writing, read all targeted Sections and capture their old ADR
      IDs. Describe the intended resulting content, promotion(s), and the
      precise decisions/Sections being replaced in the new ADR. A partial
      replacement must be understandable from this new record alone.
   2. Choose one primary Section deterministically and create exactly one
      accepted ADR with `--spec-ref <primary-section-id>`. Verify the ADR
      persisted and the primary link propagated before further writes.
   3. Link every additional Section with `specctl set-adr <id> <new-adr-id>`.
      Confirm all links before applying the topic's content/status changes.
      Never create another ADR merely because another Section is involved.
5. **Apply and verify the topic**, then retire fully replaced ADRs:
   1. Promote each targeted draft Section with `set-status <id> stable`;
      leave already-stable Sections stable. Then apply requested content
      changes via `set-description` and/or `set-open-questions`.
   2. Re-read every targeted Section to verify its content, Status and ADR.
      If any creation, propagation, linkage, edit, or promotion fails, stop
      dependent steps for this topic, report the partial state and keep old
      ADRs accepted. Other independent topics may proceed. Never treat a
      partially completed topic as authorized to retire its old ADRs.
   3. For each distinct old ADR, query `specctl list --adr <old-id>` without
      a status or path filter. Any remaining Section reference means the
      ADR stays `accepted`, with no `superseded-by` change. Report the
      remaining Section IDs and the partial replacement in the new ADR.
   4. Only after the topic is verified and that query succeeds with no
      references: `adrctl info-superseded-by <old-id> <new-id>`, then
      `adrctl set-status <old-id> superseded`. The new record identifies
      the final replacement; prior partial replacements remain documented
      in their own ADRs. A query error is not evidence of zero references.

6. **Revision — correction**, per topic:
   1. Identify the Section's existing governing ADR (already known from
      step 3's classification).
   2. **Confirm before proceeding — every time, as a deferred, non-blocking
      report, never an in-run interactive prompt.** No Subagent in this
      project family blocks mid-run to ask a question — every existing
      user-facing gate (`rulectl-author`'s Language decision,
      `questctl-author`'s taxonomy confirmation, `taskctl-author`'s
      shrink-deletion confirmation) reports the pending decision and stops
      *for that item only*, resuming only when invoked again with the
      answer folded into the next prompt (`design-rulectl-author.md`, step
      3; `design-taskctl-author.md`, step 7 — "no separate resume
      mechanism... invoking again re-evaluates"). This topic follows the
      same shape: take **no action** on it this run — no content change, no
      ADR update — and report **deferred-awaiting-correction-confirmation**,
      stating plainly which ADR would be reused/overwritten and what the
      correction would change, while every other topic in the same
      invocation proceeds normally (mirrors `rulectl-author`'s own "only the
      affected candidates wait" rule for its Language gate). No memory-based
      shortcut across repeated corrections to the same Section in the same
      session either — each invocation is stateless (same precedent), so
      there is nothing that could remember "the user already said yes to
      this kind of thing."

      Resuming is simply being invoked again with the answer stated in the
      prompt (e.g. "ja, das ist eine Korrektur an ADR `<id>`" / "nein, das
      ist eine neue Entscheidung") — read as ordinary input to step 3's
      classification on that later run, not a special resume mechanism:
      - **Confirmed**: proceed with 3-4 below, now on that later
        invocation.
      - **Declined**: step 3 classifies the topic as "Revision — new
        decision" instead and steps 4-5 handle it — the classification was
        only ever a shortcut the user can override, never a hard branch
        foreclosing the other path.
   3. Apply the content change: `specctl set-description`/
      `set-open-questions` (no `--adr` needed — already set from the prior
      promotion/revision).
   4. **Update the reused ADR's own content**, but only the fields whose
      text actually goes stale relative to the correction — not
      unconditionally all three (`adrctl-author-cli`, "Updating an existing
      ADR's own content"). A pure wording/grammar fix that doesn't change
      what's being decided may need no ADR update at all; a correction that
      changes the actual meaning of what was accepted does.
7. **Verify, then report.** Re-read once more before compiling the report:
   `specctl show <id>` for every Section this run promoted or edited
   (confirm Status/`adr`/content), `adrctl show <id>` for every ADR created,
   superseded, or content-updated. The report is structured by topic:
   - **Every topic**, with its classification (promotion /
     revision-new-decision / revision-correction) and the Section(s) it
     targeted.
   - **Under each**: the ADR(s) created (Signature/ID), the ADR(s)
     superseded or retained with remaining Section references (if any), and the outcome per Section — **done**,
     **failed** (the error), **deferred-awaiting-correction-confirmation**
     (step 6.2 — no ADR/content change was made for this topic this run),
     or **deferred-awaiting-domain-decision** (see "ADR placement" — no ADR
     or Status change was made for this topic this run).
   - Retrospective, like every sibling Subagent's report — a record of what
     was done, not a plan awaiting approval (except the one, explicit,
     per-correction confirmation gate in step 6).

## Multi-Section topics

`adrctl`'s `spec-ref` is single-valued (`design-decisions.md`,
"Amendments... spec-ref single-valued") — one ADR auto-propagates to
exactly one Section. When a topic's change touches several Sections (either
a first-time promotion of several Sections at once under one shared
rationale, or a revision spanning more than one), pick one as the
**primary** Section (deterministically — e.g. the first named in the
prompt) for `--spec-ref`; link every other Section to the same ADR
afterward via `specctl set-adr <id> <adr-id>` (`specctl-editor-cli`,
"Linking an additional Section"). Being "primary" carries no meaning beyond
which Section `spec-ref` happens to name — every governed Section is
otherwise equal, and a `list --adr <adr-id>` (via `specctl-editor-cli`)
finds all of them regardless of which one is primary.

## ADR placement (Domain/Component)

Every ADR this Subagent mints needs an `adrctl` Domain/Component path.
`adrctl-author-cli` gates new **Domains** ("New Domains are batch-gated"):
check the existing ones first and reuse a fitting Domain; never create a
new top-level Domain autonomously. Components under an existing Domain are
created freely.

If any topic in this run needs a Domain that doesn't exist yet, collect
every such topic into **one** batched proposal (suggested Domain/Component
per topic — typically mirroring the targeted Section's own Part/Chapter)
and report those topics as **deferred-awaiting-domain-decision**, making no
ADR and no Status/content change for them this run; every topic whose
Domain already exists proceeds normally. Resuming is the same shape as the
correction gate: invoked again with the decision stated in the prompt
(e.g. "Domain `Architektur`, Component `Komponenten` ist ok").

## ADR content synthesis

An ADR's `Motivation`/`Description`/`Rationale` are always this Subagent's
own synthesis of the change request and the resulting `specctl` content —
never a verbatim copy of the invocation prompt (`adrctl-author-cli`,
"Creating an ADR"). This mirrors `taskctl-author`'s "own synthesis, never a
verbatim excerpt" discipline for a Task's Description
(`design-taskctl-author.md`, "Source content is untrusted") for the same
underlying reason: an ADR is meant to stand as an intelligible decision
record on its own, not a restated instruction, and later readers (a future
run of this same Subagent, a human reviewing the ADR history, `adrctl show`)
should be able to understand *why* without cross-referencing the original
prompt.

## Interaction with the specctl-editor-cli and adrctl-author-cli Skills

This Subagent never constructs `specctl` or `adrctl` command lines itself
beyond what `specctl-editor-cli`/`adrctl-author-cli` document — promotion,
content edits, ADR creation, linking, and superseding all go through the
recipes in those two Skills. If a needed operation isn't covered in either,
that is a gap in the Skill, not something to work around ad hoc in the
Subagent.

## Out of scope

- **Creating new Sections** — entirely `specctl-author`'s job; this
  Subagent only ever promotes or revises what already exists.
- **`stable`→`deprecated`** — "ausschließlich durch den User" per the
  original request; a manual, human-only CLI call, never issued by this
  Subagent.
- **`stable`→`draft` rework** (`--force`) — out of scope for v1; reverting
  already-accepted content to unstructured free editing is a significant,
  easy-to-regret decision (it also discards the Section's `adr` link's
  authority going forward), not something this Subagent should trigger
  from a routine prompt. Left for a human to do manually, same as
  `deprecated`.
- **A duplicate-ADR check** — see step 2's reasoning.
- **Reviewing/approving a `proposed` ADR** — every ADR this Subagent
  creates is already `accepted`; there is no separate review stage in this
  workflow to model.
- A dedicated automated test/eval harness — v1 acceptance is a manual smoke
  test against scratch `specctl`/`adrctl` stores, same as every sibling
  Subagent.

## Future extensions

- **Automated regression evals.** Today's acceptance is a manual smoke
  test; the topic-decomposition judgment, the intent-classification
  (correction vs. new decision), the per-correction confirmation gate, and
  the multi-Section linking mechanics in particular deserve reproducible
  scenarios once a harness exists. Not designed yet.
