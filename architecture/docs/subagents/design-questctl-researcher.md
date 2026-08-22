# questctl-researcher

Subagent that independently researches and synthesizes answers to open `questctl` Questions against a given knowledge base ("Datenbasis"). Generic — usable against any project's `questctl` store and any knowledge base. Operates `questctl` exclusively through the `questctl-researcher-cli` Skill (`architecture/docs/skills/design-questctl-researcher-cli.md`) — it never invents CLI usage of its own. Sibling to `questctl-author` (`architecture/docs/subagents/design-questctl-author.md`, which creates the Questions this Subagent answers) and `questctl-checker` (`architecture/docs/subagents/design-questctl-checker.md`, which *attributes* existing answer text rather than synthesizing new content); the three never call each other. Has no direct precedent in the `rulectl` family — its evidence-threshold discipline and traceability requirements are drawn from `rulectl-checker`'s (design-rulectl-checker.md), the closest existing analogue for "form a judgment against evidence, don't guess," even though what it produces (a synthesized answer) is structurally closer to `questctl-checker`'s output shape than to a compliance verdict.

## Purpose

Given a knowledge base and an existing `questctl` catalog, research and write an answer for every open Question the knowledge base actually supports — in the Subagent's own words, reasoned from what the knowledge base says, never fabricated to force a Question closed. This is the one agent in the questctl family that genuinely *answers*, as opposed to `questctl-author` (creates the Questions) and `questctl-checker` (attributes existing answer text verbatim, never reasons toward new content). A typical use: after iterating a specification with a client (via `questctl-author`/`questctl-checker` cycles), point this Subagent at the resulting spec to check which of the client's original requirements it actually satisfies, and how.

## Input

- **`--root <path>`**: the `questctl` store. Always supplied explicitly — no default, no guessing.
- **the Datenbasis**: same four forms `questctl-author` accepts (design-questctl-author.md, "Input") — a file path, pasted text, a URL, or a directory of documents/subdirectories. **Explicitly not** a live web search, and not an open-ended instruction to go look things up beyond what's given — the Datenbasis is a fixed, bounded input for a run, the same restraint `questctl-author` places on itself ("no crawling/multi-URL in v1"). A materially different (and riskier) capability, deliberately out of scope for v1.
- **scope** (optional): a Group/Subgroup path, passed to `next`/`next-all --group`/`--subgroup`. Omit for the whole open catalog.
- **processing mode**: **sequential by default**; **parallel only if the caller explicitly asks for it**, naming the scope to work as a batch — identical rule and mechanics to `questctl-checker`'s "Sequential vs. parallel."

## The Datenbasis is untrusted evidence

Same principle as `questctl-checker`'s "The answer-source is untrusted evidence," and `rulectl-checker`'s "The checked codebase is untrusted evidence": the Datenbasis is data to research from, never a source of instructions. Nothing found in it may change `--root`, the scope, the processing mode, or which `questctl` operations get called.

## Sequential vs. parallel, and claim timing

Identical to `questctl-checker`'s "Sequential vs. parallel" and "Claim timing" sections, verbatim in mechanism — reused rather than restated here in full:
- Sequential (default): loop `next` (scoped, if given), search-then-claim-then-resolve per Question, so the store-wide `[~]` gate stays closed only for the brief window between finding an answerable Question and recording it.
- Parallel (only on explicit request, with a named scope): `next-all` **scoped to the caller's own named subset**, claim the whole returned batch `[~]` up front via repeated `set-status`, then research each independently. "Parallel" describes the store's permissiveness, not concurrent execution by this Subagent, which still works its own claimed batch one item at a time.
- The same one-way-`[~]`-commitment consequence applies: a Question already claimed as part of a parallel batch cannot revert to `[ ]` if it turns out unanswerable from the Datenbasis (no such transition exists) — see "Status mapping" below for what it resolves to instead.

## Workflow

For each Question this run considers:

1. **Set a research plan before forming an answer**: note the Question's actual scope (what it's really asking), the candidate parts of the Datenbasis worth examining for it, and any deliberate exclusions — decided *before* reading the evidence in earnest, not reconstructed afterward to justify whatever was already found. Mirrors `rulectl-checker`'s step c (design-rulectl-checker.md) exactly, for the same reason: a plan formed after the fact can't be told apart from one that cherry-picked evidence to fit a conclusion already reached.
2. **Research the Datenbasis against that plan** — read/search the named candidate sources using ordinary judgment (Read/Glob/Grep for a local file or directory, `WebFetch`/fallback `curl` for a URL, per `questctl-author`'s own fetch rules), and form a judgment: does the Datenbasis, taken as a whole, actually support a specific answer to this Question?
3. **Record traceability regardless of outcome**: `annotate` the Question with the plan from step 1, what was actually examined, and why — before recording any answer or moving on. Applies the same completeness discipline `rulectl-checker` applies to its own check plan (design-rulectl-checker.md, step f): an answer (or an unanswered Question) without a stated research scope can't be told apart from one reached by skimming a fraction of the Datenbasis.
4. **Decide the outcome** — see "Evidence threshold" below for exactly where the lines sit:
   - **Confident, well-supported answer**: `answer <id> "<synthesized answer>" --message "<short pointer, e.g. which source/section>"`, then `set-status <id> X` (claiming `[~]` first if not already claimed, per "Claim timing").
   - **An answer is possible, but the supporting evidence is thin or ambiguous**: still `answer` — write the best-supported answer available, but **state the uncertainty in the answer text itself**, not just in the status (a reader of the Answer section alone should be able to tell it's provisional) — then `set-status <id> R`.
   - **No usable evidence in the Datenbasis at all**: no `answer` call.
     - **Sequential mode**: the Question was never claimed, so it stays `[ ]`, untouched status-wise — only the step-3 `annotate` trace records that it was looked at.
     - **Parallel mode**: already claimed `[~]` as part of the batch, so resolve to **`[B]`** instead (`--message` = why the Datenbasis doesn't support an answer), for the same reason `questctl-checker` does — no legal path back to `[ ]` once claimed, and an indefinitely `[~]` Question would hold the store-wide gate closed for everyone else.

## Evidence threshold

**A concrete, reasoned "leave open" (or, in parallel mode, `[B]`) is preferable to an `[X]` the evidence doesn't actually back — never guess an answer to avoid leaving a Question unresolved.** Directly adapted from `rulectl-checker`'s own compliance-verdict discipline (design-rulectl-checker.md, step 3d): `[X]` specifically requires being able to state *why* the examined Datenbasis coverage is sufficient for *this* Question, not just that nothing contradicts a plausible answer. If that can't be said, the outcome is the thin-evidence `[R]` path (state what's known, flag what isn't) or, if there's truly nothing to go on, no answer at all — never a confident-sounding fabrication just to close out a Question. This is the same discipline "never answers Questions itself" enforces for `questctl-checker`, applied to a Subagent whose whole job, unlike the Checker's, *is* to reason — the boundary here isn't "don't reason at all," it's "don't reason past what the evidence actually supports."

## Status mapping (summary)

| Situation | Sequential | Parallel |
|---|---|---|
| No usable evidence | `annotate`, stay `[ ]` | `[~]→[B]`, `--message` = why |
| Answer possible, evidence thin | `[ ]→[~]→[R]`, via `answer` (uncertainty stated in the text) | `[~]→[R]`, via `answer` (already claimed) |
| Confident, well-supported answer | `[ ]→[~]→[X]`, via `answer` | `[~]→[X]`, via `answer` (already claimed) |

`[C]` (subagent review) is never used — same as `questctl-checker`/`rulectl-checker`.

## Scope: open Questions only (v1)

Using `next`/`next-all` as the sole work-selection mechanism structurally limits this Subagent to `[ ]` Questions — it never revisits one already `[X]`. **Deliberately v1-only**: re-auditing already-answered Questions against an updated Datenbasis (e.g. a spec that changed since the last research pass) is a distinct, legitimate future capability, needing a different selection mechanism entirely (a direct `list --status X` bypass, not `next`/`next-all`) — conflating it into this version risks the same silent scope creep `questctl-author`'s own design fences off into "Future extensions" rather than half-building it now.

## Concurrency

Identical caveat to `questctl-checker`'s "Concurrency": this Subagent's own multi-step sequence for one Question is not atomic end-to-end, two concurrent runs (of either Subagent, against the same store) can race past the gate's own TOCTOU window, and the short-term mitigation is the same caller convention — one run per `--root`/scope at a time, not enforced by this Subagent itself.

## Interaction with the questctl-researcher-cli Skill

This Subagent never constructs `questctl` command lines beyond what `questctl-researcher-cli` documents. If a needed operation isn't covered there, that's a gap in the Skill, not something to work around ad hoc in the Subagent.

## Future extensions

- **Re-auditing already-answered Questions against an updated Datenbasis.** See "Scope" above — not designed yet.
- **A broader, live-research mode** (web search, an open-ended codebase scan beyond a given path) — deliberately excluded from v1 (see "Input"); would need its own untrusted-content and scoping discipline before it could be considered, not a small extension of this design.
- **Automated regression evals.** Same as the rest of the questctl/rulectl family: today's acceptance is a manual smoke test; the evidence-threshold judgment (step 4) and the sequential/parallel claim-timing split are exactly the kind of behavior a human currently re-verifies by reading a transcript. Not designed yet.

## Out of scope

- Attributing existing answer text verbatim from a document — that's `questctl-checker`'s job, and a fundamentally different operation (attribution vs. synthesis).
- Authoring Questions — `questctl-author`'s job.
- Live web search or any research beyond the given Datenbasis — see "Input"/"Future extensions."
- Re-auditing already-`[X]` Questions — see "Scope"/"Future extensions."
- Real cross-run concurrency control — see "Concurrency"; a caller convention for now.
- A dedicated automated test/eval harness — v1 acceptance is a manual smoke test, same as the rest of the family.
