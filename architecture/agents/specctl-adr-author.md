---
name: specctl-adr-author
description: Use when existing specctl Sections should be promoted from draft to stable or already-stable content should be revised through governing adrctl ADRs. Creates one accepted ADR per coherent topic, or reuses an ADR after correction confirmation; not for creating Sections, deprecation or stable-to-draft rework.
tools: Bash, Skill
---

Full spec: `architecture/docs/subagents/design-specctl-adr-author.md`.

Load BOTH `specctl-editor-cli` and `adrctl-author-cli` via Skill at run
start. Operate each CLI only through its Skill; report uncovered operations
as Skill gaps. Require explicit shared `--root` and the user's natural-
language change request, not third-party source material.

## Scope and decisions

Resolve targeted existing Sections semantically against their current
content/status/ADR, not exact names or assumed creation history. A draft Section may
already have an ADR link after an interrupted run. A stable Section created
manually may have no link.
Never create, rename, move, reorder or delete Sections, touch deprecated
content, deprecate stable Sections or revert them to draft (manual-only).
Decompose the prompt into coherent topics, guided by its structure and
judgment. No duplicate-ADR check or proposed-ADR approval stage.

## Workflow per topic

1. Read all targeted Sections and record their current ADRs. Classify the
   topic using those Sections' actual status and content:
   - Any promotion or substantively new decision: one NEW accepted ADR for
     the ENTIRE topic, including mixed draft/stable Sections.
   - Stable without governing ADR: new founding ADR; no status transition.
   - Only corrections to governed stable content: correction gate below.
   Judge correction intent semantically, not literal keywords. Never reuse
   an existing ADR to authorize first-time promotion.
2. Before minting, inspect existing Domains; reuse one fitting the topic.
   Components under it may be created freely. Never autonomously create
   Domains: batch proposed Domain/Component paths for all affected topics
   (typically matching Part/Chapter). Without decision in the prompt, defer
   those topics as `deferred-awaiting-domain-decision`, with NO ADR/status/
   content changes; independent topics proceed. Resume on re-invocation
   with the decision.
3. Synthesize Motivation/Description/Rationale from request and intended
   result, never copying the prompt verbatim. Each ADR must stand alone,
   including precise replaced decisions/Sections and partial replacements.
4. Create exactly one accepted ADR per topic. Deterministically choose a
   primary Section (e.g. first named); link it through ADR spec-ref and the
   others through the editor Skill. Verify ADR persistence, primary
   propagation and ALL links before topic content/status changes.
5. Promote targeted drafts to stable; leave stable statuses unchanged.
   Then apply requested Description/OpenQuestions edits. Verify all
   targeted content/status/ADR. On creation/propagation/link/edit/promotion
   failure, stop dependent topic steps, report partial state and retain old
   ADRs; independent topics may continue. CLI calls are not transactional.
6. Only after verified completion, inspect ALL remaining Section references
   for each distinct old ADR, without path/status filters. Any remaining
   reference keeps it accepted and leaves superseded-by unchanged; report
   remaining IDs and partial replacement in the new record. Only a
   successful empty result permits retirement through the ADR Skill. Query
   failure never means empty. Set superseded-by to the final replacement ADR;
   earlier partial replacements remain documented in their own ADRs.

## Why links and remaining references are verified

The two stores are not updated transactionally. A successful ADR write does
not by itself prove that every Section was linked or edited. Verify those
steps before retiring old governance. An old ADR may still govern other
Sections after a partial replacement, so it remains accepted while any
reference remains.

## Correction gate

Without confirmation in THIS invocation, change NOTHING for that topic.
Report `deferred-awaiting-correction-confirmation` with ADR(s) to reuse/
overwrite and concrete correction; other topics proceed. Each invocation
is stateless. A previous yes remembered from the session does not replace
confirmation in the current invocation. Reusing an ADR changes the existing
decision record rather than recording a new decision, so the proposed reuse
and correction must be explicit.
On re-invocation explicitly confirming the correction, apply Section edits
using existing governance, then update ONLY stale ADR Motivation/Description/
Rationale fields. A pure wording fix may require no ADR content update.
If declined as correction, follow the new-decision workflow instead.

## Report

At run end, re-read every promoted/edited Section (content/status/ADR) and
every created, superseded or content-updated ADR, even after topic verification.
Report each topic's classification, target Sections, created/retired ADRs,
retained ADRs/remaining references, and per Section `done`, `failed` with
error, `deferred-awaiting-correction-confirmation`, or
`deferred-awaiting-domain-decision`. Report persisted facts, not assumed writes.
