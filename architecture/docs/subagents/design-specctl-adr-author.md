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

## Invariant: every `stable` Section reachable here already has a governing ADR

Because this Subagent is the only path by which a Section ever leaves
`draft` (see "Companion to `specctl-author`" above — `specctl-author` never
calls `set-status`, and this Subagent never creates new Sections), and
because this Subagent's own promotion step (below) always establishes a
governing `adr` before the transition completes, every `stable` Section
this workflow ever encounters already has a non-empty `adr` field. This
matters concretely: it means the "first-time promotion vs. revision" branch
below can be decided purely from whether the target Section's `adr` field
is set, with no edge case where a `stable` Section might have none. (A
Section promoted to `stable` by some other means entirely — e.g. a human
running raw `specctl`/`adrctl` commands outside this workflow, or the
`add --set-status stable` initial-creation exception `design-specctl.md`
allows — could in principle violate this invariant; if `specctl-editor-cli`'s
initial `show <id>` ever finds a `stable` Section with no `adr` set, treat
it as an unpromoted Section for this run's purposes and follow the
promotion path, minting a founding ADR for it now.)

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
3. **For each topic, classify it against every Section it targets**:
   - **First-time promotion**: the Section is `draft` (no `adr` yet) — see
     step 4.
   - **Revision — new decision**: the Section is `stable`, already governed
     by an ADR, and this topic reads as a substantively new decision, not a
     correction to the existing one — see step 5.
   - **Revision — correction**: the Section is `stable`, already governed,
     and the prompt's own wording for this topic reads as a correction —
     "revise," "redo," "correct," "fix," or equivalent phrasing judged
     semantically (not literal keyword matching: "korrigiere die Formatierung
     in Abschnitt X" and "das war falsch formuliert, bitte anders" both
     read as corrections without using any of the four example words) —
     applied to a specific part of already-governed content. See step 6.

     A topic targeting several Sections may mix these — one Section being
     promoted for the first time while another, already-stable Section in
     the same request is being revised — each Section's own classification
     is independent even within one topic.

4. **First-time promotion**, per targeted Section:
   1. `adrctl add --spec-ref <section-id> --set-status accepted ...` — mints
      the founding ADR (`adrctl-author-cli`, "Creating an ADR"), which
      auto-propagates its ID into the Section's `adr` field. This is
      inherently a single-topic ADR — "this content is now accepted as-is"
      needs no further decomposition, even if the Section being promoted
      itself covers several ideas.
   2. `specctl set-status <section-id> stable` (no `--adr` needed — already
      set by propagation).
   3. If the same prompt also asks for a content change alongside
      promotion (e.g. "finalize Section X, fixing the typo while you're at
      it"), apply it via `specctl set-description`/`set-open-questions`
      after the promotion (also no `--adr` needed) — the founding ADR
      already covers this Section's content as a whole.
5. **Revision — new decision**, per topic (possibly spanning several
   Sections — see "Multi-Section topics" below for the mechanics when it
   does):
   1. Read each targeted Section's *current* `adr` value first — this is
      the old, about-to-be-superseded ADR (guaranteed present, per the
      Invariant above).
   2. `adrctl add --spec-ref <primary-section-id> --set-status accepted ...`
      — mints the new ADR.
   3. For every additional Section this topic touches beyond the primary
      one: `specctl set-adr <id> <new-adr-id>` (see "Multi-Section topics").
   4. For every distinct old ADR replaced by this new one (there may be
      more than one if the topic merges concerns that previously had
      separate governing ADRs): `adrctl info-superseded-by <old-id>
      <new-id>` then `adrctl set-status <old-id> superseded` — never leave
      a no-longer-governing ADR sitting at `accepted` (`adrctl-author-cli`,
      "Superseding an ADR").
   5. Apply the actual content change: `specctl set-description`/
      `set-open-questions` per targeted Section (no `--adr` needed — set by
      the propagation/linking above).
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
        decision" instead and step 5 handles it — the classification was
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
     superseded (if any), and the outcome per Section — **done**,
     **failed** (the error), or **deferred-awaiting-correction-confirmation**
     (step 6.2 — no ADR/content change was made for this topic this run).
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
- **Re-litigating a superseded ADR's own Section governance.** Superseding
  an ADR (step 5.4) never re-examines whether the *old* ADR governed other
  Sections too (via a prior multi-Section topic of its own) — only the
  Section(s) this run's new ADR now covers are re-linked. A stale
  cross-reference on an old, multi-Section ADR's other Sections is not
  auto-detected or fixed by this Subagent. Not designed yet.
