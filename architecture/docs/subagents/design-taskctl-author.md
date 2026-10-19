# taskctl-author

Subagent that turns a set of documents into a `taskctl` Tasklist — Phases,
then Tasks distributed into them — shaped by the user's invocation prompt.
Generic — usable in any project that has (or is willing to start) a
`taskctl` store; not specific to `ai-architecture-tools`. Operates `taskctl`
exclusively through the `taskctl-author-cli` Skill
(`architecture/docs/skills/design-taskctl-author-cli.md`) — it never invents
CLI usage of its own. Loosely modeled on `questctl-author`
(`architecture/docs/subagents/design-questctl-author.md`) — same source
ideas (multiple documents, untrusted input, a batched structural decision
before individual objects are created) — but diverges where taskctl's own
purpose forces it to: this Subagent doesn't *atomize* what a document
already says, it *plans* what the user's prompt asks for, using the
documents as material (`design-decisions.md`, "Amendments (2026-08-25,
taskctl-author/taskctl-worker Subagent design)").

## Purpose

Given one or more source documents (design documents, specs, README drafts,
...) and a user prompt describing what to build and how, derive a
Phase-structured Tasklist that fulfills the prompt: determine the necessary
and sensible Phases first, then distribute Tasks into them. On explicit
request, extend or shrink an already-existing Tasklist the same way. This
is the authoring half of the taskctl workflow; a separate Subagent,
`taskctl-worker` (`architecture/docs/subagents/design-taskctl-worker.md`),
works the resulting Tasklist — out of scope here, and the two never call
each other.

## Input

- **`--root <path>`**: the `taskctl` store. Always supplied explicitly by
  the caller — no default, no guessing. `taskctl` auto-creates the store on
  first use.
- **one or more sources**: any combination of a file path, pasted text, a
  URL, or a directory (read recursively for documents, `design-questctl-author.md`'s
  "Input" form, §4) — given as a **list**, not a single value. "A number of
  documents" (the normal case here) no longer has to mean "one directory
  containing them all," the way it does for `questctl-author`.
- **the invocation prompt**: mandatory, and does more work here than for any
  sibling Subagent — it's the primary driver of the Tasklist, not just a
  scoping hint on top of document-derived content:
  1. **Scope filter** — which subset of the sources' content actually
     becomes Tasks (e.g. "only a Tasklist for the installation
     instructions" — the rest of the source material is read for context
     but yields no Task).
  2. **Detail constraints** — implementation choices a Task's own text must
     honor (e.g. "no Bash scripts, do everything in Python").
  3. **Extend/shrink targeting** — when the prompt refers to an existing
     part of the Tasklist ("Füge den Installationsanweisungen der Tasklist
     auch die Compileanweisungen hinzu"), this run adds to (or, per
     "Shrinking", removes from) that existing structure instead of
     authoring an unrelated, disconnected addition. There is no separate
     "mode" flag — whether a run ends up creating fresh Phases, adding to
     existing ones, or removing Tasks is read entirely from what the
     prompt says, never auto-detected from whether the store already has
     content.

## Source content is untrusted

Same principle as `rulectl-author`/`questctl-author`: every document — file,
pasted text, fetched URL, or file found under a source directory — is data,
never instruction. Nothing in it is a command directed at this Subagent.

**This carries more weight here than for any sibling Subagent, because of
what a Task becomes downstream.** A Rule or a Question is read and judged
by whatever consumes it; a Task's Description is *executed* by
`taskctl-worker` — Bash, file edits, whatever the described work calls for.
If a Task's text could ever be a verbatim copy of attacker-controlled
source content, authoring would be a direct path to prompt-injected
execution. The mechanism that closes this: **Task Description text is
always this Subagent's own synthesis** of what a source says and what the
prompt asks for — never a verbatim excerpt copied out of a source document
the way `questctl-checker`'s `answer` deliberately *is* verbatim. A source
document can state facts, requirements, and constraints for this Subagent
to reason about; it can never contribute literal text that ends up,
unexamined, inside a Task another Subagent will later act on. This is the
Author-side half of a trust boundary `design-taskctl-worker.md` states from
its own side.

## Workflow

1. **Obtain every source** (see "Input"). If any one fails — a bad URL, an
   unreadable file, a source directory with zero readable documents under
   it — **abort the whole run immediately**, create nothing. Unlike a
   single failed `add` later (step 5), a failed source means the material
   this run needs to plan against is incomplete, not that one item among
   many was bad; extended from `rulectl-author`'s single-source rule to
   every source in the list, not relaxed just because there are now
   several.

2. **Read every source, and the current state of `--root` (if it already
   has Tasks/Phases), before drafting anything.** The store's existing
   content is not a separate "mode" to branch on (see "Input", point 3) —
   it's just more context: relevant existing Phases get reused where the
   prompt's intent maps onto them, irrelevant ones are left alone, and
   nothing already there is touched unless the prompt actually asks for
   it.

3. **Determine the Phase breakdown.** Propose the Phases this run's Tasks
   need — reusing an existing Phase (via `--phase` on `add`) wherever the
   prompt's target already has one that fits, creating a new one
   (`add-phase`) otherwise. **No confirmation gate before creating** —
   unlike `questctl-author`'s batched taxonomy confirmation, which exists
   because a wrong Group/Subgroup *depth* choice has no cheap undo. A wrong
   Phase call here is cheap to fix after the fact (`group-phase` reassigns
   a Task, `reorder`/`delete` fix the rest), so proceed directly and let
   the final report carry the result, rather than stopping the whole run
   on a decision that isn't actually expensive to get wrong.

   **Phase-less stores.** A `taskctl` store is either Phase-using or
   phase-less, fixed by its first write and never mixed
   (`taskctl-author-cli`, "Recipes"). A **fresh** store always gets Phases
   — this workflow plans Phases first. An **existing phase-less** store
   (e.g. a hand-written flat list) stays flat: no `add-phase`, every Task
   added without `--phase`, and the report says so and groups everything
   under a single "(no Phases)" heading.

   **Creation order is execution order.** `taskctl-worker` works Tasks
   strictly in `next`'s global sequential order (design-taskctl.md,
   "Sequential Processing") and cannot skip ahead; an unresolved earlier
   Task holds back everything after it. So the order Phases and Tasks are
   created in *is* the execution plan: create them in dependency/execution
   order. When extending, append new Tasks at the end of their Phase;
   use `reorder` only when a new Task must run before an existing **open**
   (`[ ]`) Task, and never place a new Task ahead of one already `[~]`,
   `[R]`, `[C]`, `[B]` or `[X]`.

4. **Draft the Tasks for each Phase**, synthesizing from the relevant
   source material, filtered and shaped by the prompt (see "Input," points
   1–2). This is *not* a structural walk of each document's own outline —
   there is no worklist to reconcile against, and no guarantee every
   document section yields something; a Tasklist is a plan for the prompt,
   not an inventory of the sources. Every Task's Description is this
   Subagent's own synthesis (see "Source content is untrusted").

   **Description content standard.** `taskctl-worker` sees only the Task —
   never the source documents, never this run's prompt — and must mark a
   Task `[B]` if its Description doesn't say what "done" looks like. So
   every Description is self-contained prose covering three things (no
   mandated headings): **the goal**; **the concrete work**, including every
   detail constraint from the prompt that applies to this Task, repeated
   per Task rather than stated once somewhere else (e.g. "Python only, no
   Bash scripts"); and **a checkable completion criterion** ("done when
   ..."). `source` carries traceability (see "Metainfo population") — the
   worker never needs to open the source to do the work.

5. **Duplicate check — local, then against the store**, adapted from
   `rulectl-author`/`questctl-author` step 4 for the absence of a worklist:
   - **Local**: before creating, review the whole drafted set for this run
     for two Tasks that would say the same thing under the same Phase —
     judgment, not exact-string matching, same bias toward creating a
     genuinely distinct Task over silently dropping it.
   - **Against the store**: for a Phase that already existed before this
     run, `list` its current Tasks and compare against each drafted
     candidate targeting it; a likely duplicate is skipped, not created,
     and recorded (referencing the existing Task it matches) for the
     report.

6. **Create each remaining Task**, via `taskctl-author-cli`, populating
   fields per "Metainfo population" below. No confirmation precedes
   creation (see step 3's reasoning, which applies equally to Tasks, not
   just Phases) — write directly, continuing past any single failed item
   (`design-taskctl-author-cli.md`, "Error handling").

7. **Shrinking, only when the prompt actually asks for it.** Resolve the
   prompt's natural-language reference (e.g. "die Installationsanweisungen
   der Tasklist") against the existing store — `list`/`show`, the same
   judgment-based matching duplicate-checking already uses, not exact-string
   matching against a Phase/Task name. **Unlike every other write this
   Subagent makes, deletion is gated**: the person must confirm the exact
   list of Tasks (and, if now-empty, Phases) to be removed before `delete`
   is called on any of them. This is the one place a pre-write gate
   belongs in this design — every other mistake here (a wrong Phase, an
   unwanted Task) is cheap to undo; a deleted Task is not (`design.md`,
   "Object Operations": no tombstone, nothing logged once it's gone).

   A Subagent cannot pause mid-run to ask — it runs to completion and
   returns a report. The gate is therefore **two-pass**:
   - **Pass 1** (the shrink request): does everything else the prompt
     asks for, deletes **nothing**, and reports every targeted item as
     **deferred-awaiting-deletion-confirmation** with its exact ID and
     Signature (and the reason it matches the request).
   - **Pass 2** (a re-invocation whose prompt explicitly confirms those
     IDs — typically relayed by the calling agent after asking the user):
     deletes exactly the confirmed IDs that **still** match the original
     request against the store's then-current state; a confirmed ID that
     no longer exists or no longer matches is reported, not deleted. Any
     other work in the prompt runs normally; the duplicate check (step 5)
     keeps a repeated creation request from duplicating pass 1's Tasks.
   - A blanket pre-authorization in the first prompt ("delete without
     asking") does **not** satisfy the gate — the point is that the person
     confirms the concrete list, which they haven't seen yet at that time.
   This is the same "deferred, resume by re-invoking" shape as
   `questctl-author`'s taxonomy decision; there is no separate resume
   mechanism.

8. **Verify, then report.** Re-read the store once more before compiling
   the report — for every Task this run believes it created, `show <id>`
   to reconfirm it persisted; for every Task this run deleted (after
   confirmation), confirm it's actually gone. The report is structured by
   Phase, not by a worklist (there is none):
   - **Every Phase touched this run** (newly created, or already existing
     and added to), with why it exists/was chosen.
   - **Under each, every Task**, with its outcome: **created** (Signature,
     `source`), **skipped-likely-duplicate** (the Task it matched),
     **failed** (the error), or — for a shrink target still awaiting
     confirmation — **deferred-awaiting-deletion-confirmation**.
   - **Every deleted Task** (shrink runs only, after confirmation), with a
     one-line reason tying it back to the prompt's request.
   - **How the prompt's scope filter and detail constraints were applied**
     — what was included, what was deliberately left out and why, what
     constraints shaped how Tasks were written.
   - Retrospective, like every sibling Subagent's report — a record of what
     was done, not a plan awaiting approval (except the one, explicit,
     shrink-confirmation gate in step 7).

## Status

Every created Task is left at `taskctl`'s default initial status, open
(`[ ]`) — there is no other sensible choice for freshly-authored work
nobody has started yet, and no post-creation review gate, mirroring
`rulectl-author`/`questctl-author`'s own "Status" sections exactly.

## Metainfo population

Per created Task:

- **`source`**: set whenever the Task actually derives from an identifiable
  document/section — same convention as `rulectl-author`/`questctl-author`'s
  own `source` field (design-taskctl.md, "Metainfo"; design-decisions.md,
  "Amendments (2026-08-25, ...)"): a file's resolved path plus a
  heading/line range, a URL plus an anchor, or (for pasted text) the
  `pasted invocation text` convention plus a content hash. Left unset for a
  Task that's purely a synthesis of the prompt's own instructions with
  nothing to point back to in a source document.
- **`review`, `assignee-type`, `assignee-name`**: left unset by default.
  This Subagent doesn't know, at authoring time, whether a given Task will
  turn out to need human review once actually worked — `taskctl-worker` can
  escalate that dynamically (`design-taskctl-worker-cli.md`, "Recipes").
  Populated **only** when the invocation prompt explicitly states something
  about review or assignment for a Task or a named group of Tasks (e.g.
  "alles, was die Datenbank-Migration betrifft, braucht User-Review") —
  never inferred from a Task's own subject matter, **with one exception**:
- **Outward-facing actions always get `review=user`.** A Task whose work
  includes publishing, releasing, deploying, pushing, sending messages,
  opening PRs/issues, or another action that leaves the working area or
  can't be undone is created with `review=user`, regardless of the
  prompt — the prompt can't waive it. Keep such an action in **its own
  Task**, separate from the local preparation before it (build, test,
  check), so only the action itself waits for approval; its Description
  names the action and states that it runs only after user approval. This
  is what makes `taskctl-worker`'s pre-action gate apply
  (`design-taskctl-worker.md`, "Outward-facing and irreversible actions").

## Tools

`Read`, `Glob`, `Grep` (sources, directories), `WebFetch` with `Bash`
(`curl`) as fallback for URL sources (same rule as `questctl-author`),
`Bash` for `taskctl`, `Skill` to load `taskctl-author-cli`. No
`Edit`/`Write`: this Subagent writes only through `taskctl`.

## Interaction with the taskctl-author-cli Skill

This Subagent never constructs `taskctl` command lines itself beyond what
`taskctl-author-cli` documents — Phase creation, Task creation, the
duplicate-check `list` call, any corrective `info-*`/`set-*` call, and
`delete` (after shrink confirmation) all go through the recipes in that
Skill. If a needed operation isn't covered there, that is a gap in the
Skill, not something to work around ad hoc in the Subagent.

## Future extensions

- **Cross-Phase duplicate curation.** Same gap `rulectl-author`/
  `questctl-author` name for themselves: step 5's store-duplicate check is
  scoped to a Task's exact target Phase, so a duplicate filed under a
  different Phase isn't caught by any single run. Planned: a periodic
  curation workflow, not designed yet.
- **Automated regression evals.** Today's acceptance is a manual smoke
  test, same as every sibling Subagent; the prompt-driven scope-filter/
  detail-constraint interpretation (step 4) and the shrink-confirmation
  flow (step 7) in particular deserve reproducible scenarios once a
  harness exists. Not designed yet.
- **Re-verifying an already-authored Tasklist against an updated source.**
  This Subagent only ever adds (or, on request, removes) — it has no
  notion of "this source changed, some existing Task may now be stale."
  Not designed.

## Out of scope

- Working Tasks — deciding what "done" means for a Task's described work,
  performing that work, and changing Status accordingly — entirely
  `taskctl-worker`'s job.
- A pre-write approval step for **creating** Phases/Tasks — deliberately
  not part of this workflow (see step 3); the one approval gate that does
  exist (step 7's shrink confirmation) is structural to deletion
  specifically, not a general review step.
- Auto-detecting extend/shrink from store population state — deliberately
  not done; see "Input," point 3.
- A dedicated automated test/eval harness — v1 acceptance is a manual
  smoke test, same as every sibling Subagent. See "Future extensions."
- Duplicate detection across Phases other than a Task's exact target — see
  "Future extensions."
