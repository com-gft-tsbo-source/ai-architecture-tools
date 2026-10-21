# Design Decisions — taskctl / questctl / rulectl / adrctl / specctl

Status: **Finalized**, 2026-08-17; amended since — see the Amendment index below. This is the rationale trail behind `design.md`, `design-taskctl.md`, `design-rulectl.md`, `design-adrctl.md` and `design-specctl.md` — those documents are the authoritative spec; this log records *what* was decided and *why*, for anyone reviewing or later revisiting a choice. Superseded intermediate proposals and resolved open questions from earlier drafts are omitted; only what actually landed is listed.

## Amendment index

Amendments are appended in date order; earlier text is never rewritten, only
marked inline as *(Superseded …)*. The second column lists only later changes an amendment itself names; when an amendment is superseded in part, the superseded passage is also marked inline. The current rules are always those in `design.md` and the tool-specific design documents.

| Amendment | Later changed by |
|---|---|
| 2026-08-17, during implementation | `--root` repeatable → revisited by 2026-08-19, shared-root resolution (multi-root merge dropped) |
| 2026-08-19, shared-root resolution |  |
| 2026-08-19, spec-ref single-valued |  |
| 2026-08-19, closing spec/implementation gaps |  |
| 2026-08-19, three-verb command namespace + Change metagroup |  |
| 2026-08-20, correctness review: ID uniqueness, atomic writes, ADR validation |  |
| 2026-08-20, adr_lookup follow-up fixes |  |
| 2026-08-20, specctl `init` lifecycle |  |
| 2026-08-21, rulectl `tasklist` | refined by 2026-08-21, rulectl `tasklist` review-reset + tool-task context |
| 2026-08-21, rulectl `tasklist` review-reset + tool-task context |  |
| 2026-08-22, questctl introduction + taskctl sequential-blocking clarification | `ungroup`, `list --ungrouped`, `answer`-as-annotate → superseded by 2026-08-22, grilling |
| 2026-08-22, grilling: uniform per-store depth, bespoke Answer section, `[~]` gating | "taskctl needs no three-way split" → reversed by 2026-08-25, taskctl `NoWorkAvailable` |
| 2026-08-22, questctl-author/-checker/-researcher design |  |
| 2026-08-22, questctl/taskctl implementation |  |
| 2026-08-25, taskctl `NoWorkAvailable` + taskctl-author-cli/taskctl-worker-cli design |  |
| 2026-08-25, taskctl-author/taskctl-worker Subagent design |  |
| 2026-08-27, specctl-author/specctl-adr-author design | files created by 2026-08-27, specctl-author/specctl-adr-author implementation |
| 2026-08-27, specctl-author/specctl-adr-author implementation |  |
| 2026-10-19, plugin distribution |  |
| 2026-10-19, taskctl-author/taskctl-worker implementation |  |
| 2026-10-19, local-first: one gated path for remote actions |  |
| 2026-10-19, specctl/adrctl fixes from integrating the specctl Subagents |  |
| 2026-10-20, agent workflow consistency |  |
| 2026-10-20, compact runtime instructions |  |
| 2026-10-20, readability review of compact instructions | "eval plan not executed" → E1, E3–E6 executed, see `../evals/results-2026-10-20.md` |
| 2026-10-21, CI and plugin versioning |  |
| 2026-10-21, cross-tool CLI contract tests |  |

## Scope
`tasklist` (the rulectl/adrctl → taskctl export operation) is intentionally **out of scope** for this design pass. Both tool docs list it as an operation but mark its behavior as deferred. It will be designed once the core object model has stabilized in an implementation.

*(Superseded — see "Amendments (2026-08-21, rulectl `tasklist`)" below: `tasklist` is now implemented, for rulectl only; adrctl's `tasklist` was dropped entirely rather than implemented.)*

## Object ID
6-character hex code hashed from initial content, or a free-form string supplied at creation. Free-form IDs may not contain `/`, because `/` is the discriminator the `--id` selector uses to recognize a metagroup-path reference (see CLI Contract). Frozen at creation, like everything else that must survive renames.

## Metagroups
- **Exactly one metagroup per object**, not "one or more" as originally drafted. A single object can only meaningfully sit at one point in a tree-shaped, path-based hierarchy; allowing multiple independent memberships would have required either an arbitrary tie-break for numbering/type-derivation (which subpath "owns" the object?) or a much more complex model. Cross-cutting cases (e.g. an ADR touching two components) are handled by the user manually creating a new metagroup that represents the combination — a naming convention, not a feature, so the tool stays simple.
- **Max. 3 levels**, matching the deepest hierarchy already in use (rulectl: Language/Context/Category).
- **Sort number embedded in the name** (`<nr>-<name>`, 3-digit zero-padded) rather than tracked separately, for every tool uniformly — this was originally a taskctl-only convention (`Phase=<nr>-<name>`) and was generalized once rulectl/adrctl also needed a defined listing order. Embedding it in the name avoids a second storage location and reuses the same numbering mechanism as objects.
- **Directory mode mirrors the hierarchy 1:1 as subdirectories** — the natural way to give each path a stable, independently lockable, independently listable location, and the basis for per-directory index files.
- **Single-file mode needs a `## Metagroups` bookkeeping block** because there's no directory to stand in for "this path exists." Two rejected alternatives and why: putting it in YAML frontmatter was rejected because we'd already eliminated frontmatter everywhere specifically to avoid a leading `---` being misread as frontmatter by generic tooling — reintroducing it for bookkeeping alone would undo that and add a second parser (YAML) alongside the Markdown-bullet convention used everywhere else. Treating the *first* H1 heading as a special bookkeeping block was rejected because it breaks the otherwise exceptionless "every H1 is an object" rule and doesn't scale to a file needing several declared metagroups. A level-2 `## Metagroups` section at the top of the file — same bullet-list style as `## Meta` — solves both: no new syntax, no exception to the H1 rule, holds arbitrarily many (including empty) declarations.
- A referenced-but-missing metagroup path **always aborts with an error**, in both modes — no auto-vivification. Chosen for predictability: a script/agent that always calls `add-<type>` first shouldn't have to remember a mode-dependent exception.

## Object Type
- **Derived from the metagroup name's initial letters**: 6 letters for 1 level, 3+3 for 2 levels, 2+2+2 for 3 levels (always after stripping the `<nr>-` sort prefix — otherwise digits would dominate the abbreviation and collide constantly). Short, mnemonic, and directly tied to the classification it represents rather than an opaque counter.
- **Manual override** via `--abbrev` at `add-<metagroup-type>` time, stored in `.index.md` (directory mode) or the `## Metagroups` section (single-file mode) — write-once, never silently changed later.
- **Collision resolution**: keep the non-colliding levels' letters fixed, and for the colliding level advance position-by-position through the source name to the first character that differs from the already-assigned name at that position (e.g. `login`/`logik` differ only at position 5, so `logik` resolves to `lok` instead of `log`). This keeps existing, already-referenced abbreviations completely stable — only the newly-added, colliding one adapts — which matters because the abbreviation is embedded in every existing object's file name.
- **Escalation if that's not enough**: extend up to 3 characters past the target width, then a numeric suffix, then abort and require `--abbrev`. Chosen as a graceful degradation ladder rather than either silently producing non-unique types or immediately forcing manual intervention on every collision.
- **taskctl exception**: its Object Type is the (unpadded) Phase number, not a letter code — because Phase is a single, purely sequential axis, not a classification; a letter abbreviation would add no information there.

## Numbering
- **`max + 1`, not smallest-free-gap**, on creation. Reusing a freed number risks referencing ambiguity against History entries and old Signatures that already used it; monotonic growth avoids that entirely.
- **Gaps are permanent** on delete.
- **Reorder reuses an existing gap when the target position allows it**, falling back to a shifting cascade (renaming subsequent files) only when no gap is available. This was tightened from an initial "always cascade" rule specifically to reduce how many files/locks a routine reorder touches.
- **Changing an object's metagroup re-derives everything downstream** in one atomic step: new number (`max+1` in the new subpath, old number becomes a gap), new type, new signature, new file name/location, updated `## Meta`. Logged as a single `M` history entry rather than as several separate ones, since it is conceptually one operation.

## Signature & Escaping
`<type>-<nr>-<id>-<name>[-<class>]`, with every non-`[A-Za-z0-9]` character in free-text components mapped to `_`. Explicitly **one-way** — no reverse-parsing of a Signature back into the original name is supported or needed, since objects are always resolved via ID, not by parsing their Signature. This was the simplification that let us drop an earlier, more complex reversible-escaping scheme.

## Status
- taskctl keeps its explicit state machine (`[ ]→[~]→[R]/[C]→[X]`, `[B]` from anywhere, rework path from `[R]`/`[C]`, `--force` for everything else) — it was already well-specified and is left as the model rulectl/adrctl deliberately do *not* need.
- rulectl/adrctl: **no automatic transitions**, status changes only on explicit user/agent instruction. rulectl has no `--draft` flag (initial status is always `active`); adrctl's initial status is `proposed`.
- **`--set-status` at `add` time may set any initial status**, even one a normal transition couldn't reach (e.g. a taskctl task created directly in `[~]`) — because choosing an initial value isn't a transition (there's no prior state to violate), so it never needs `--force`.

## History Format
`M` (management operation) / `T` (taskctl `annotate` progress log) prefixed, timestamped lines; `T` always shows `[<old>] -> [<new>]`, `M` only when the status actually changed. Continuation lines are indented `  > `. Deliberately **not** a formal grammar with a real parser — a line starting with `- ` in column 0 is always a new entry, a line starting with exactly `  > ` is always a continuation; that's sufficient and keeps every tool's implementation trivial.

## Object / File Format
- **Frontmatter dropped entirely**, in both modes — the original design used YAML frontmatter plus a redundant `## Meta` body section for the same data; removing frontmatter eliminated the duplication in one direction rather than the other; it also avoids the frontmatter-vs-horizontal-rule ambiguity for `---` in single-file mode.
- **Exactly one H1 per object**, with `## Meta` / `## <name>` / `### <optional>` / `## History` as level-2/3 children. An earlier draft used two H1 sections per object (a "technical" and a "readable" section); that was revised once the rule "every H1 marks a new object" was introduced, since two H1s per object would make that rule ambiguous.
- **Single-file mode separates objects with `---`**, used strictly *between* objects, never leading or trailing — specifically to avoid the file's first line being misread as a YAML frontmatter delimiter by generic Markdown tooling.
- **Directory mode uses the object template unchanged** — no heading shift, no inserted metagroup-path heading — because the directory location already conveys the metagroup unambiguously; the shift/insert rule in an earlier draft was redundant once that was recognized.

## Index Files
- **`.index.md` and `.index.json` are separate files**, not merged, because they serve different lifecycles: `.index.md` is a small, human-editable, write-once source of truth (the Object Type abbreviation); `.index.json` is a disposable, tool-maintained performance cache (object metadata by ID, direct children only) that a `reindex` command can always regenerate from the object files without touching `.index.md`. Merging them would risk a routine reindex clobbering a manually-chosen abbreviation.
- `.index.json` includes a `meta` block (Metainfo key/values) so metainfo-based listing is index-accelerated too, not just status/type/name.
- Both are **directory-mode only** — in single-file mode there's only one file to scan, so a separate cache buys nothing; the `## Metagroups` section (see above) covers the one thing that still needed persisting (declared-but-empty metagroups and their abbreviations).

## Concurrency / Locking
- **Lock scope is exactly the invocation's target** — the single file, or the directory root — never something broader. This was tightened after an earlier draft's "lock the root directory" wording risked reading as a shared lock across unrelated targets, which would have made two invocations on two unrelated files block each other for no reason.
- **3-minute timeout, then the lock is stolen** by the waiting instance (with a logged warning naming the previous holder's PID/timestamp). This accepts a small risk — a merely slow (not crashed) holder could in principle still be writing — in exchange for not requiring manual intervention on every stale lock; it's a deliberate simplicity-over-safety call.
- **Writes go through `<...>.tmp` + rename-on-success** to protect individual files from partial writes; multi-file cascades (reorder, metagroup change) can still leave a partial cascade behind on a crash, which `reindex` is expected to help detect and clean up rather than the locking model preventing outright.

## CLI Contract
- **Subcommand style**, not `--flag`-only: `add`, `add-<type> <name>`, `set-status`, `set-<type> <name>`, `annotate`, `next`, `show`, `show-metagroups`, `reindex`. `set-*` operations are additionally available as inline flags on `add`, so creating an object and populating its fields (including its metagroup) doesn't require a second invocation.
- **`add-<type> <name>` / `set-<type> <name>` share one uniform shape** across metagroups and metainfo — a deliberate simplification over the earlier, inconsistent `--add-<path>=<value>` sketch.
- **`--id` selector** resolves, in order: Signature pattern → contains `/` (metagroup-path + number) → raw ID. This ordering (and the "no `/` in free-form IDs" rule above) is what keeps the three forms unambiguous without a separate disambiguating flag.
- **`--message`** carries the History log text for `set-status`/`annotate`/other logged operations — previously missing from the contract entirely.

## Language & Naming
All field, parameter and status names are English in the final docs. Typos from the German drafts were corrected in the process: *Katergorie* → `Category`, *weigth* → `weight`, *assigne-type/-name* → `assignee-type`/`assignee-name`, *Sprache* → `Language`, *Komponente* → `Component`.

## Amendments (2026-08-17, during implementation)

Three refinements surfaced while implementing against this "finalized" design (`architecture/docs/scripts/corrections.md`), decided the same day and folded into `design.md` directly rather than kept as a separate errata list:

- **`add-<metagroup-type>` auto-numbers by default.** The original text already specified `max + 1` numbering "at creation" for metagroups, same as objects, but the CLI Contract's own examples (`add-domain backend`) left it ambiguous whether a `<nr>-` prefix was still mandatory input. Clarified: the prefix is optional on `add-<metagroup-type>` — omitted, it's auto-assigned; supplied, it's used verbatim. Applies uniformly to **all three tools**, not just taskctl's Phase, per the general "keep CLI structure uniform" rule in `architecture/scripts/CLAUDE.md` — a tool-specific carve-out here would have been a needless asymmetry.
- **Flexible `--<metagroup-type>` reference.** Referencing an *existing* metagroup path (on `add`, or wherever else a path is given) now resolves each `/`-separated segment against its siblings as either the exact `<nr>-<name>` form, a bare number, or a bare name — instead of requiring the exact stored string. Chosen to apply **per segment**, uniformly across single- and multi-level tools, rather than special-casing taskctl's one-level Phase; an agent or user citing "Setup" or "1" is far more natural than requiring the exact zero-padded form it doesn't necessarily know ahead of time. Ambiguous matches (e.g. two siblings sharing a stripped name) abort with an error — silently picking one would make the resolution unpredictable and hide a naming collision the user should probably fix.
- **`--root` is repeatable**, directly implementing the read-only multi-root merge already described under "File and Directory Parameters" (which specified the *behavior* but not the CLI mechanism to trigger it). Chosen over positional trailing path arguments — despite the CLI Contract's separate "positional parameters: only file or directory names, always last" line inviting that reading — because a repeated flag keeps every root uniformly explicit and avoids ambiguity between "the primary root" and "additional merge roots" that two different syntaxes (`--root` plus bare positionals) would have introduced. **Superseded 2026-08-19, see "Amendments (2026-08-19, shared-root resolution)" below.** *(Superseded — see "Amendments (2026-08-19, shared-root resolution)": `--root` is a single shared path, multi-root merge was dropped.)*

## Amendments (2026-08-19, shared-root resolution)

Revisits the "`--root` is repeatable" decision above, once implementing the `adrctl` ↔ `specctl` ADR linkage (design-specctl.md, "ADR Linkage") exposed a gap the original design never closed: an ADR's `spec-ref` needed to name *some* path to the governed spec document, and nothing tied that path to anything else — a plain string, freely divergent from wherever the user actually happened to invoke `specctl` with. Multi-root merge, in hindsight, was solving a different (and, per `architecture/scripts/CLAUDE.md`'s "not yet used for our own work" status, still hypothetical) problem and never needed for anything actually built.

- **Multi-root, read-only merge removed entirely.** `--root` now takes exactly one path; passing several was the only reason `Store`/`SpecStore` carried a `"merged"` mode with its own read-only guard sprinkled through every mutating method. No tool has shipped a use case for it. Removing it is a straightforward simplification of `lib/store.py`/`lib/spec_store.py`, not a loss of anything exercised.
- **`--root <path>` now names a directory *shared by all four tools*, not a single tool's own file/directory.** Each tool has a fixed store name (`tasks`/`rules`/`adrs`/`spec`) and resolves its actual target within that shared directory as `<name>.md` (single-file mode) or `<name>` (directory mode) — see design.md, "File and Directory Parameters", for the exact algorithm. This is what makes cross-tool referencing (the motivating case: `adrctl`'s `spec-ref`) resolvable without a separately-configured path: given the *same* `--root` a user already passes to `adrctl`, `lib/spec_link.py` can find `specctl`'s data deterministically.
- **Resolution accepts either a shared directory or any single tool's own path**, deriving the shared directory from the latter (its parent, once the `.md`/no-`.md` ambiguity for a not-yet-existing path is resolved by suffix). Chosen over requiring the shared directory explicitly, so a user (or agent) who only knows one tool's conventional path can still invoke any other tool correctly without first working out the shared directory by hand. **Only reliable for a `.md` file today** (design.md, "File and Directory Parameters", "Open gap") — an *existing* bare directory belonging to a different tool is currently just treated as the shared directory itself (predating this amendment, and correct on its own terms), so pointing tool B at tool A's already-created directory nests B's data inside it rather than finding the real shared directory. Left open rather than guessed at during this pass; revisit if it turns out to matter in practice (e.g. once the `adrctl` spec-ref linkage is built and exercised).
- **Both candidates (`<name>.md` and `<name>` present at once) is a hard error**, not a silently-broken tie. This mirrors the general "referencing an undeclared metagroup path aborts" philosophy (predictability over guessing) applied to the store-resolution layer instead of the object layer.
- **An explicitly-named, not-yet-existing path overrides the tool's own default mode.** E.g. `adrctl --root ./project/adrs.md` on a brand-new project creates `adrs.md` as a file even though `adrctl`'s own default (nothing exists yet, no explicit signal) is directory mode — the literal name the user typed is a stronger signal than the tool's generic default. Symmetric for an explicitly-named bare directory candidate against a file-defaulting tool (e.g. `specctl --root ./project/spec`).
- **A bare path whose own name matches the tool's store name also names the target directly** (shared-directory step, not the override step above) — caught during implementation: without this, `adrctl --root ./project/adrs` on a brand-new project (nothing exists yet) would treat `./project/adrs` itself as the *shared* directory (since it doesn't look like a file) and then look for `adrs.md`/`adrs` *inside* it, double-nesting to `./project/adrs/adrs`. The fix applies the same "this path names my own target, use its parent as the shared directory" logic the `.md` case already gets, keyed on the bare name matching instead of the suffix.
- **Per-tool default mode when neither candidate exists and the given path names neither directly**: `spec` defaults to single-file (a spec document's primary use case, per `VISION.md`, is one flowing document); `tasks`/`rules`/`adrs` default to directory (their metagroup hierarchies — Phase; Language/Context/Category; Domain/Component — read more naturally as nested directories than as one growing file). A tool-specific choice, not a uniform one, since the two shapes genuinely fit different tools' typical content differently — recorded per tool in each tool's own design document rather than centrally in design.md.
- **Store name `spec` stays singular** where the other three (`tasks`/`rules`/`adrs`) are plural: one spec document per project, with potentially many ADRs governing parts of it — the asymmetry reflects a real difference in what's being named (a singular document vs. a collection of many small objects), not an inconsistency to fix.

## Amendments (2026-08-19, spec-ref single-valued)

Implements the `adrctl` ↔ `specctl` ADR linkage (design-specctl.md, "ADR Linkage") deferred by the original design, once the shared-root convention above made an ADR's spec target resolvable without a separately-configured path.

- **`spec-ref` stays single-valued**, dropping the original design's "repeatable, since one ADR may govern several Sections" shape. The general Metainfo mechanism (`ToolSpec.metainfo`, `lib/store.py`/`lib/toolspec.py`) has no concept of a repeated value anywhere — every field is one string, set or replaced wholesale by `set-<type>`. Making `spec-ref` the sole exception would mean either a special case bolted onto the shared engine for one field on one tool, or generalizing the engine's value model for a need no other Metainfo field (on any of the four tools) has ever shown. Chosen instead: `spec-ref` is one string, exactly like `superseded-by` or any other Metainfo value. An ADR governing several Sections is still expressible — one ADR per Section, or a Section's own `adr` field pointing back at a single governing ADR that itself documents the broader decision in its `Rationale` — just not as one `spec-ref` fan-out. Revisit only if a real multi-Section case actually surfaces; not designed for speculatively.
- **No `<file>` component in `spec-ref`.** The original sketch (`spec-ref=<file>#<id>`) predated the shared-root convention; now that every tool resolves its store from the same `--root` a caller already supplies, `lib/spec_link.py`'s `propagate()` takes that same raw `--root` value from the triggering `adrctl` invocation (`args.root`, not `adrctl`'s own already-resolved `store.root`) and re-resolves `specctl`'s store independently — exactly like `adrctl` resolved its own. Passing `adrctl`'s resolved directory instead would risk hitting the accepted "pointed at another tool's own directory" gap (see the shared-root amendment above); passing the original unresolved value sidesteps it the same way the top-level CLI invocation itself does.
- **Propagation runs via a new `after_dispatch` hook on `lib/cliapp.py`'s `main()`**, not inline in `dispatch()`. `dispatch()` returns a tool-agnostic `ObjectRecord`/list/report; only `adrctl.py` itself knows to look for a `spec-ref` value and call `lib/spec_link.py`. Adding the hook as an optional callback keeps `taskctl.py`/`rulectl.py` (which pass none) completely unaffected, and keeps `lib/spec_link.py`'s existence a fact known only to `adrctl.py` and `specctl.py` — `lib/cliapp.py` itself never imports it.
- **Trigger commands are `add`, `set-status`, and `set-spec-ref`** — the three points where an ADR's `spec-ref` value can newly take effect: `add` (set at creation), `set-status` (a status change may be the ADR becoming `accepted`, the point that actually makes it authoritative), and `set-spec-ref` (retroactively attaching or changing the link on an existing ADR). Other mutating commands (`set-description`, `reorder`, `set-superseded-by`) don't change what a Section should show, so they don't re-trigger propagation.
- **`receive_adr_link` (automatic) is a separate `SpecStore` method from `set_adr` (manual)**, differing only in one thing: `receive_adr_link` always appends an `M` History entry, `set_adr` never does. This mirrors the already-documented History rule (design-specctl.md, "History"): a real ADR decision is worth a logged entry, a manual correction to already-ADR-backed metadata is not. Keeping them as two methods rather than one with a `log: bool` flag makes each call site self-documenting about which case it is, without a caller having to know the rule to pass the right flag.
- **No rollback/transactionality across the two stores.** If `lib/spec_link.py`'s `propagate()` fails (most commonly: `spec-ref` names a Section that doesn't exist), the triggering `adrctl` operation still exits 1 with the error on stderr — but the ADR itself, already written by `store.add`/`store.set_status` before `after_dispatch` runs, stays persisted. This is the same non-atomicity already accepted for directory-mode's own multi-file cascades (see "Concurrency / Locking" above: "a partial cascade behind on a crash, which `reindex` is expected to help detect and clean up") — extended here across two independent stores rather than within one. A user or agent correcting a bad `spec-ref` simply re-runs `set-spec-ref` with the right value; no cleanup of the ADR itself is needed since it was written correctly, only the cross-reference failed.

## Amendments (2026-08-19, closing spec/implementation gaps)

A spec-vs-implementation audit found several operations `design.md` already documented (in some cases since the original pass) but that had never actually been wired up, plus a validation rule (`MetainfoSpec.choices`) that existed in the data model but was never enforced. This amendment covers the ones that were then implemented; two more (metagroup Rename, and `set-<metagroup-type>`/"Change metagroup" for taskctl/rulectl/adrctl) were identified in the same audit but intentionally left for a later pass — `design.md`'s "Metagroup Operations"/"Object Operations" now say so explicitly, rather than silently continuing to imply they exist. **"Change metagroup" was implemented in the next pass, as `group-<metagroup-type>` — see "Amendments (2026-08-19, three-verb command namespace + Change metagroup)" below. Metagroup Rename remains open.**

- **`MetainfoSpec.choices` is now enforced**, in `lib/store.py`'s `set_metainfo` and inline on `add`, via a small `_validate_metainfo_choice` helper. Previously the field was declared (e.g. taskctl's `review: none | user | subagent`) but nothing read it — an invalid value was silently accepted, and in taskctl's case silently fell back to the 3-step forward path (`_REVIEW_STEP.get(review)` returning `None`) instead of erroring. Kept as a single shared helper, called from both write paths, rather than duplicating the check — the two call sites (`add`'s inline metainfo dict, `set_metainfo`'s single value) were the only places a Metainfo value is ever newly written.
- **`set-<user-content-block>` for taskctl/rulectl/adrctl** (`design.md`, "Object Operations": "Change content"), one subcommand per declared block (e.g. `set-description`, rulectl's `set-procedure`, adrctl's `set-motivation`/`set-rationale`) generated the same way `set-<metainfo-type>` already is — a loop over the tool's own declared list, not a hardcoded set of names. Chosen over a single generic `set-content <id> <block> <value>` command specifically to keep the "add-<type>/set-<type>" uniform shape (`design.md`, CLI Contract) extending cleanly to a third axis (content blocks) alongside metagroups and metainfo, rather than introducing a differently-shaped command for just this one case. Logged as a plain `M` History entry (`"<block> changed"`), same as any other content/metainfo/metagroup change (`design.md`, "Object History").
- **`list` filters by metagroup and metainfo** (`design.md`, "Operations Across All Objects") reuse the exact flag names `add` already uses for the same concepts (`--<metagroup-type>`, `--<metainfo-type>`) rather than inventing separate filter-specific flag names — a user who already knows `add --domain Backend` needs no new vocabulary for `list --domain Backend`. The metagroup filter is **inclusive of descendants** (a path plus everything below it), not an exact-match-only filter: since objects only ever sit at the deepest (leaf) level of their metagroup, an exact-match filter on a non-leaf level (e.g. `rulectl list --language Python` without `--context`/`--category`) would otherwise always return nothing, which is never what "list objects in this metagroup" means in practice. At most one metagroup flag may be given per `list` call (an object has exactly one metagroup path, so combining two would be over-specified); multiple metainfo flags combine with AND.
- **Delete** (`design.md`, "Object Operations") for taskctl/rulectl/adrctl is a plain removal — the file (directory mode) or record (single-file mode) is gone, the Number becomes a permanent gap (`design.md`, "Numbering", unchanged), nothing is logged anywhere afterward (there is no tombstone; the object no longer exists to hold a History). This is straightforward for these three tools because an object there is always a metagroup *leaf* — it can never have descendants of its own, only the metagroup path above it can, and `design.md` never asked for metagroup-path deletion, only object deletion.
- **Delete for specctl needed an extra rule** the other three tools don't, because a specctl Section is simultaneously a metagroup-path node and an object (`design-specctl.md`, "Deviation from the general model") — it can have real descendant Sections. Deciding what `delete` should do when the target still has children was an open design question, resolved as: **reject by default, `--force-delete` to cascade** — deleting a Section with descendants fails with an error unless `--force-delete` is given, in which case the whole subtree (the Section plus every descendant) is removed in one step. Chosen over always-cascading (too easy to lose a large, unintended amount of content with one command) and over always-rejecting-outright (too inflexible — deliberately restructuring away a whole subtree is a legitimate operation, it just shouldn't be the *default* outcome of a plain `delete <id>`). The flag is named `--force-delete`, deliberately distinct from the existing `--force` (used for `set-status`'s already-established meaning, "accept normally-disallowed status transition") — the two flags guard unrelated kinds of surprise and conflating their names would blur that.

## Amendments (2026-08-19, three-verb command namespace + Change metagroup)

Implements the other item deferred by the previous amendment (`group-<metagroup-type>`, the general model's "Change metagroup"), once a namespace question about it was raised: with `set-<user-content-block>` now shipped alongside the existing `set-<metainfo-type>`, adding a third axis (`set-<metagroup-type>`, as originally sketched in `design.md`) under the same bare `set-` prefix would let two axes collide if a tool's own metagroup-, metainfo-, and content-block type names ever overlapped — nothing in `ToolSpec` enforced them being disjoint across axes, only within one.

- **Each of the three per-object update axes gets its own fixed verb prefix**: `group-<metagroup-type>` (Change metagroup), `info-<metainfo-type>` (Metainfo, renamed from the original `set-<metainfo-type>`), `set-<user-content-block>` (Change content, unchanged). This makes the three axes' command namespaces disjoint by construction — a metagroup type and a metainfo type can now share a bare name with no collision, since `group-x` and `info-x` are different subcommands.
- **The verb-per-axis mapping is a fixed convention in the generic engine** (`lib/cliapp.py`'s `build_parser`/`dispatch`), not a `ToolSpec` field a tool could override. Considered and rejected: a declarative `ToolSpec.axis_verbs` (or per-`MetagroupLevelSpec`/`MetainfoSpec` `verb` field) letting a tool choose its own prefixes. Rejected because `architecture/scripts/CLAUDE.md` already requires uniform CLI structure across all four tools "auch wenn ein Tool das jeweilige Feature (noch) nicht braucht" — no tool has ever needed, or plausibly would need, a different verb for the same axis, so a configurable field would be exactly the kind of premature abstraction the project's own conventions warn against (three fixed strings beat a knob nobody turns).
- **`info-<metainfo-type>` renames the already-shipped `set-<metainfo-type>`** (including `adrctl`'s `spec-ref`/`superseded-by`, both landed in the previous two amendments) — a breaking rename, accepted because there is no external consumer yet (this repository is still the tool's only user). `lib/spec_link.py`'s trigger list (design-specctl.md, "ADR Linkage") is updated accordingly: `add`, `set-status`, `info-spec-ref` (was `set-spec-ref`).
- **`group-<metagroup-type> <id> <path>`** (`lib/store.py`'s new `set_metagroup`) reassigns an object to a different, already-existing metagroup path — resolved the same way `--<metagroup-type>` is elsewhere (`resolve_metagroup_path`, unchanged) — and re-derives Number/Object Type/file location exactly the way `add` derives them for a new object, reusing the same `metagroup.dir_object_type_for`/`sf_object_type_for`/`level_directory` helpers rather than duplicating that logic. Rejects reassigning an object to its own current path (would otherwise double-count the object among its own "new" siblings when computing the next Number, and is a no-op anyway) with an error pointing at `reorder` instead — the same guard shape specctl's own `move` already uses for the analogous case.
- **No Object Type re-derivation cascade is needed here**, unlike specctl's `move`: a generic-model object is always a metagroup *leaf*, never a metagroup-path node with descendants of its own, so `group-<metagroup-type>` only ever touches the one object being moved.
- **Fixed while touching the same code path**: `_dir_resolve_path`/`_sf_resolve_path` (shared by `add`, `group-<metagroup-type>`, and `resolve_metagroup_path`) now catch `lib/metagroup.py`'s `MetagroupError` and re-raise as `StoreError`. Previously an unresolvable metagroup path (e.g. `add --component Nonexistent/thing`) crashed with an unhandled traceback instead of the clean, `StoreError`-driven exit-code-1 message every other error path already produces — an existing bug, not one introduced by this change, surfaced by writing `group-<metagroup-type>`'s own "unknown path" test.

## Amendments (2026-08-20, correctness review: ID uniqueness, atomic writes, ADR validation)

A focused correctness review (not a spec-vs-implementation gap audit like the earlier passes — these are all places the implementation didn't do what the *implementation itself*, or the already-written spec text, already implied) found five issues, resolved as follows.

- **Object ID uniqueness is now enforced on `add`**, in both `lib/store.py` (taskctl/rulectl/adrctl) and `lib/spec_store.py` (specctl). Previously `validate_free_form_id` checked only syntax (no `/`, non-empty) — an explicit `--id` colliding with an existing object's ID was silently accepted, creating a second object no `--id`/`resolve_id`/`_find` lookup could ever reach again (they return the *first* match), and silently breaking anything that resolves an object by ID, including the adrctl `spec-ref` → specctl `adr` linkage. `design.md`, "Object ID", now states uniqueness explicitly. The check scans the whole store (`list_all()`/the already-loaded `sections`/`sf_records` list, not just the target metagroup path's siblings), since IDs are global to a store, not per-metagroup.
- **`lib/store.py`'s directory-mode object writes are now atomic**, via `atomicio.atomic_write_text` (`.tmp` + `os.replace`) at all five call sites that previously wrote directly with `path.write_text(...)`: `add`, `set_metagroup`, `_dir_reorder` (twice), `_persist` (the shared path for `set_status`/`info-<type>`/`set-<block>`/`annotate`). `lib/spec_store.py` was already fully atomic; only the three-generic-tool engine had the gap. This directly implements what `design.md`, "Concurrency / Locking", already specified ("Writes go through a `<...>.tmp` file, renamed into place only on success") — a correctness bug against the existing spec text, not a new decision.
- **`set_metagroup`'s write order was inverted relative to `_dir_reorder`'s own established pattern**, and relative to what atomicity requires: it deleted the old file *before* writing the new one, so a failure between those two steps left the object existing at neither location. Now: write the new file (atomically) first, then delete the old one — the same order `_dir_reorder` already used for its own file moves, generalized rather than reinvented.
- **`OpenQuestions` (design-specctl.md, "User Content") is now settable via the CLI** — `add-<metagroup-type> ... --open-questions <value>` and `set-open-questions <id> <value>` (`SpecStore.set_open_questions`, gated by the same ADR-validity rule as `set_description`, since it's Section content, not bookkeeping). The field existed in `SpecSection` since the original implementation but was never exposed — a plain oversight, not a deferred decision, so no design-doc text needed correcting beyond documenting the new commands.
- **specctl's ADR-existence check is now real**, not a non-empty-string check. `SpecStore._require_valid_adr` (used by `set_status`, `set_description`, `set_open_questions`) validates the referenced ADR actually exists in the `adrctl` store sharing this specctl store's root, via a new `lib/adr_lookup.py`. Chosen over the alternative (weakening `design-specctl.md`'s "valid adr reference" wording to mean only "non-empty") because the stronger guarantee is cheap to provide now that the shared-root convention makes the adrctl store deterministically findable — the same reasoning that already justified `lib/spec_link.py` for the reverse direction.
  - **`adrctl.py`'s `ToolSpec` construction moved to a new `lib/adrctl_spec.py`** (`build_spec()`), which `adrctl.py` now imports instead of defining locally. This is what makes the existence check possible without `lib/spec_store.py` importing `adrctl.py` as a whole (forbidden, `architecture/scripts/CLAUDE.md`) or duplicating adrctl's `ToolSpec` by hand (drift risk) — a small, purely mechanical extraction, adrctl's own behavior is unchanged.
  - **`lib/adr_lookup.py` is a separate module from `lib/spec_link.py`**, not a new function added to it, specifically to avoid a circular import: `lib/spec_link.py` already imports `lib/spec_store.py` (for the adrctl → specctl propagation direction), and `lib/spec_store.py` now needs this existence check (the specctl → adrctl direction) — putting both directions' logic in one module would make the two lib modules import each other.
  - **Only existence is checked, not the ADR's Status, and not that its `spec-ref` points back at this Section.** A stricter check (e.g. requiring `accepted`, or requiring the back-reference to match) was considered and deliberately left out: `design-specctl.md` never specified which ADR statuses may govern a Section (an ADR could legitimately still be `proposed` when first referenced), and a back-reference/self-consistency check would duplicate work the automatic propagation (`lib/spec_link.py`) already keeps in sync in the common case, for a scenario (a Section's `adr` and the ADR's `spec-ref` disagreeing) that existence-checking alone doesn't claim to solve. Revisit only if a concrete need for either surfaces.
  - **No new side effect beyond what `lib/store.py`'s `Store.__post_init__` already does everywhere else**: constructing a `Store` for a project with no adrctl data yet eagerly creates an empty `<shared>/adrs/` directory (directory-mode default), even though the very next line's lookup will then fail with "not found". This is existing, uniform `Store` behavior (every `Store(...)` construction does this), not something specific to this check, so it wasn't specially guarded against. **Reconsidered the same day — see "Amendments (2026-08-20, adr_lookup follow-up fixes)" below**: this framing undersold the problem, since here the side effect fires from a *validating* call nested inside a different tool's write path, and persists even when that call ultimately fails.

## Amendments (2026-08-20, adr_lookup follow-up fixes)

A second review of the same day's ADR-existence validation (above) found two implementation bugs and two documentation defects it introduced or left standing. All four fixed.

- **`check_adr_exists` no longer creates `<shared>/adrs/` on a failed check.** It now calls `lib/store.py`'s `resolve_root` first — pure path logic, no filesystem writes — and raises `AdrLookupError` immediately if the resolved target doesn't exist yet, before ever constructing a `Store`. Only when the adrctl store already exists does it build one (at which point `Store.__post_init__`'s `mkdir(..., exist_ok=True)` is a harmless no-op on an already-existing directory). This directly reverses the "no new side effect" framing in the previous amendment, which was too permissive for this specific case: a `specctl` operation that ultimately fails (bad `--adr`) must not leave new files behind.
- **`check_adr_exists` now holds the adrctl store's own lock for the duration of the lookup** (`with store.lock(): store.get(adr_id)`), closing the "no lock at all" gap — previously `Store.get` (used nowhere else under a lock either, e.g. `show`/`list`) ran fully unlocked. This does **not** make the check and the specctl write that follows it one atomic cross-store transaction — a concurrent adrctl mutation between the check returning and the specctl write completing is still possible in principle. Deliberately not pursued further: true cross-store atomicity would need a distributed-transaction mechanism the project has already declined to build for the adrctl ↔ specctl link in general (see "No rollback/transactionality across the two stores" in the `spec-ref` propagation amendment above) — extending that same acceptance to this direction is consistent, not a new gap.
- **`add --set-status stable`/`deprecated` intentionally does not require or validate `--adr`.** Raised as an open question (does the newly-real existence check mean this path should now also require one?); resolved as **no** — the ADR requirement, like the general model's `--force` requirement, is a *transition* rule (`design.md`, "Object Status": choosing an initial status at `add` time is "an initial-value choice, not a transition"). `design-specctl.md`, "Status", now states this exception explicitly, so a future reader doesn't have to reconstruct the reasoning from a test comment (`tests/lib/test_spec_store.py`'s `test_stable_without_adr_content_change_rejected`, which already exercised the resulting behavior — a `stable` Section created this way still needs `--adr` the first time its content changes, same as any other `stable` Section with no `adr` set).
- **Fixed the standing self-contradiction in `design-specctl.md`, "Metainfo"'s `adr` bullet**: it claimed manual (`set-adr`) and automatic (`receive_adr_link`) updates are "logged identically", directly contradicting both the "Operations" section's own `set-adr` entry ("Not logged in History") and the "History" section itself two paragraphs below. Correctness bug in the prose only, not a code change — a pre-existing defect, not introduced by the amendment above, but touched by it and left standing at the time.

## Amendments (2026-08-20, specctl `init` lifecycle)

Previously, a specctl document's own `# <title>` and any Preamble were opaque, unmanaged text (design-specctl.md, "Metagroups": "preserved verbatim, never touched") — no operation could set either, and every mutating operation (`add`, `set-status`, ...) silently auto-vivified an empty document on first write, the same way the other three tools auto-vivify an empty store. Requested: an explicit `init` operation that creates the document and sets Title/Preamble, with every other mutating operation now required to check the document was actually initialized first, rather than silently creating one.

- **Title is promoted to a first-class, mandatory field, split out of the previously-opaque preamble blob** (`lib/spec_document.py`'s `parse_document`/`render_document`, now `(title, preamble, sections)` instead of `(preamble, sections)`) — symmetric with how every Section has a mandatory `Name` and optional `Description`. Single-file mode's first line must now be `# <title>`; a document lacking one (including an empty/non-existent file) is treated as uninitialized, not as a parse error, except for a genuinely malformed non-empty file (see below).
- **The "is this store initialized?" check cannot be directory-existence in directory mode**, for the same reason `lib/adr_lookup.py`'s `check_adr_exists` fix (the immediately preceding amendment, same day) had to stop using it: `SpecStore.__post_init__` already unconditionally `mkdir`s the directory-mode target, so an empty, never-initialized directory is indistinguishable from an initialized one by existence alone. Resolved with an explicit, mandatory marker file, `_title.md` — always written on every directory-mode write (unlike the pre-existing, optional `_preamble.md`, only written when non-empty) — so `title == ""` after a read is now the single, mode-independent "not yet initialized" signal `SpecStore._require_initialized` checks, used by every mutating method.
- **`init` is idempotent-rejecting, not idempotent-overwriting**: calling it on an already-initialized store raises, mirroring `add`'s existing "fail on ID collision, don't silently overwrite" behavior, rather than quietly discarding an existing Title/Preamble. `set-title`/`set-preamble` are the intended way to change them afterward, and themselves require the store to already be initialized (same guard as every other mutating operation).
- **Scope is specctl-only, not generalized to `taskctl`/`rulectl`/`adrctl`.** Those three tools have no Title/Preamble concept — a store there is genuinely content-free until the first object exists, so "first `add` auto-vivifies an empty store" loses nothing an explicit `init` would add. specctl differs because Title/Preamble are real, user-supplied content that needs a place to be set, not bookkeeping that can be inferred.
- **New validation, beyond what was explicitly asked for: a Preamble may not itself contain a line matching a Section-heading pattern** (`##` through `######`, `lib/spec_document.py`'s `validate_preamble`, called from `SpecStore.init`/`set_preamble`). Without it, `set-preamble` would be a way to silently corrupt the document: such a line would be misread as the start of a Section on the very next read (`parse_document`'s heading scan runs across the whole pre-Section blob, independent of the title/preamble split within it), producing a bogus, metadata-comment-less "Section" that fails to parse. Symmetric, lower-stakes case for Title was not worth a matching check: `render_document` always emits it as `# {title}`, and since `_TITLE_RE` requires the run of `#` characters at the very start of the line, no single-line Title text can itself start a line matching `_HEADING_RE` (which requires 2-6 `#` at the very start) once rendered behind the mandatory leading `# `.

## Amendments (2026-08-21, rulectl `tasklist`)

`tasklist` (design.md's original placeholder, deferred in the "Scope" section above) is now implemented — for **rulectl only**. adrctl's `tasklist` stub is removed outright, not implemented: ADRs are verified exclusively by an LLM/agent (design-adrctl.md, "Metainfo"), so there is no tool-checked/agent-checked distinction for `tasklist`'s field mapping to key off, and no concrete need for exporting ADRs into taskctl surfaced. `lib/adrctl_spec.py`'s `deferred_operations` no longer lists it; `design-adrctl.md`'s "Operations" section says so explicitly.

- **Phase mapping**: every unique (Language, Context, Category) path among the exported Rules becomes exactly one taskctl Phase, not one per Rule or per Language — multiple Rules under the same path become multiple Tasks inside that one Phase. The Phase Name is the three segments' sort-prefix-stripped own names joined by `::`. `/` was rejected as the separator despite being the "natural" path-join character: it is reserved by `lib/cliapp.py` as the metagroup path-segment splitter (`_metagroup_path_for_add`, `group-<type>`), and taskctl has only one metagroup level — a `/`-containing Phase Name would make any later `taskctl ... --phase "<name>"` CLI invocation mis-split it and fail to resolve. Phase reuse-or-create is memoized once per distinct source path across a single `tasklist` invocation (not once per Rule), via an in-memory cache in `lib/tasklist.py`'s `run()` — this prevents duplicate Phases for multiple Rules sharing a path *within one run*, but does not defend against two concurrent `tasklist` invocations racing to create the same Phase; that residual gap is accepted at the same rigor the adrctl↔specctl link already accepts (see "Amendments (2026-08-20, adr_lookup follow-up fixes)": true cross-invocation atomicity was explicitly declined there too).
- **Task identity**: a Task's Object ID is the *same* ID as its source Rule. Safe because Object ID uniqueness (design-decisions.md, "Object ID"; enforced by `lib/store.py`'s `add`) is scoped to a single store, not globally — confirmed by reading `Store.add`'s collision check, which only scans the store being written to.
- **Idempotent re-export**: re-running `tasklist` updates an existing Task in place — Phase/Description/`assignee-type`/`assignee-name` refreshed (only the fields that actually changed, to avoid needless History noise on unchanged reruns), Status force-reset to `open` if it had drifted away from it (`Store.set_status(..., force=True)` — confirmed required, since taskctl's `validate_transition` has no defined backward path from any non-open status directly to open), and a `T` History entry appended via `Store.annotate` (the exact function backing `taskctl annotate`, reused rather than reimplemented) referencing the source Rule's Signature. The Status-reset's own `M` History entry (from `set_status`) and the `T` entry from `annotate` are both expected, not suppressed — same "don't try to collapse multiple logged operations into one" stance already taken elsewhere (e.g. `group-<metagroup-type>` logging one `M` entry per `set_metagroup` call).
- **Field mapping** keys off the Rule's `checkable` metainfo: `checkable == "llm"` → `assignee-type=agent`, Description embeds the Rule's own `Description`/`Procedure` verbatim (the agent working the Task reads the rule text directly, not a pointer back to rulectl); otherwise → `assignee-type=tool`, `assignee-name` sourced from the Rule's `tool` metainfo (not `checkable` itself, since `tool`/`tool-rule` are the fields documented as the actual tool name/rule-identifier), Description a short "run `<tool>` to verify rule `<tool-rule>`" instruction. Both include the source Rule's Signature for human/agent traceability.
- **No back-reference field added to the Rule side.** Considered and rejected, unlike adrctl's `spec-ref`↔specctl `adr` bidirectional linkage (`lib/spec_link.py`): here the shared Object ID between Rule and Task is already a sufficient, always-in-sync cross-reference (`taskctl show <id>` / `rulectl show <id>`), and `tasklist` is a one-directional batch export, not a live, per-write-propagated relationship like `spec-ref` — building `spec_link.py`-style machinery for it would be unused complexity.
- **`lib/taskctl_spec.py`** is a new module, extracted from `taskctl.py` the same way `lib/adrctl_spec.py` was extracted from `adrctl.py` (Amendments, 2026-08-20) — except it must also carry `validate_transition`/`object_type_from_phase`/the status-code constants, not just the `ToolSpec` construction, since taskctl's `ToolSpec` references those functions and leaving them in `taskctl.py` would make the extraction circularly import `taskctl.py` back. `taskctl.py` now imports `build_spec`/`DONE` from `lib.taskctl_spec` instead of defining them locally; pure refactor, no behavior change.
- **Locking**: no new locking primitive. `lib/tasklist.py` calls the taskctl `Store`'s already-locking public methods (`add`, `add_metagroup_path`, `set_metagroup`, `set_content`, `set_metainfo`, `set_status`, `annotate`) one at a time in sequence — `FileLock` (`lib/locking.py`) is not reentrant, so holding one lock across a whole multi-field Task update was rejected as it would require bypassing the `Store`'s public API. This makes a single Task's multi-field update non-atomic (a concurrent `taskctl` write could interleave between, e.g., the Description update and the Status reset) — accepted at the same rigor already established for `check_adr_exists`'s check-then-write gap and the adrctl↔specctl link generally.
- **`tasklist [--language|--context|--category <path>]`**: scoping flags reuse rulectl's own existing `list`-filter vocabulary (same flag names `list` already auto-generates per metagroup level) rather than introducing a differently-named `--under` flag borrowed from specctl's unrelated, hand-rolled CLI.
- **The `deferred_operations`/`register_deferred`/`DeferredOperationError` mechanism is removed entirely** (`lib/cliapp.py`, `lib/toolspec.py`), rather than left in place unused: after this change, no tool has any deferred operation left (rulectl's `tasklist` is real, adrctl's is gone), so keeping the generic stub machinery around would be exactly the kind of unused-for-now abstraction `architecture/scripts/CLAUDE.md`'s "drei ähnliche Zeilen sind besser als eine verfrühte Abstraktion" already argues against.

## Amendments (2026-08-21, rulectl `tasklist` review-reset + tool-task context)

Found while reviewing the `rulectl-checker` Subagent design against `tasklist`'s actual behavior — two gaps, both in `lib/tasklist.py`, both closed:

- **`tasklist` now also resets a re-exported Task's `review` metainfo to `none`**, not just its Status. Previously only `Status` was force-reset to `open` on re-export; a Task previously escalated to `R` (via `taskctl info-review <id> user`) keeps `review=user` regardless of Status, and `lib/taskctl_spec.py`'s `validate_transition` reads `review` at the moment of each transition to pick the Task's valid forward path. Left unfixed, a Task re-checked after a prior escalation would still have its `[~]→[X]` compliant verdict routed through `[R]` (or rejected without `--force`), even though `tasklist` had just force-reset its Status to `open` — the "clean re-export" `tasklist` already promised for Status didn't actually extend to the field that governs the forward path. Fixed in the same re-export pass, alongside the Status reset (`lib/tasklist.py`'s `_export_rule`, using `Store.set_metainfo` — already used there for `assignee-type`/`assignee-name`, so no new Store capability was needed). Covered by `test_tasklist_rerun_after_escalation_resets_review_too` (`tests/test_rulectl.py`), which reproduces exactly this escalate-then-recheck sequence and asserts the follow-up `[~]→[X]` succeeds without `--force`.
- **Tool-branch Task Descriptions now embed the Rule's own `Description`/`Procedure`/`source`**, not just a bare `` Run `<tool>` to verify rule `<tool-rule>`. `` instruction. The `llm` branch already embedded the full Rule text (design-rulectl.md, "Operations"); the tool branch didn't, leaving a Subagent working a tool-checked Task with only a tool name and rule id — no guideline text to judge the tool's result against, and no way to state *why* the Rule applies without going back to `rulectl show <id>` itself (a lookup this one-directional batch export was specifically designed to avoid, per the existing "no back-reference field" amendment above). Fixed in `lib/tasklist.py`'s `_tool_description`, formatted the same way the `llm` branch already structures its subsections (`### Rule`, `### Procedure`), plus a new `### Source` subsection since the tool branch had no prior use for that metainfo. Covered by `test_tasklist_tool_task_description_includes_rule_context`.

Neither change touches Task identity, Phase mapping, or the idempotent-update field-diffing already in place — both are strictly additive to what gets written into the Description/`review` fields during re-export. The two new tests bring the suite from 452 to 454 total (`python -m unittest discover -s architecture/scripts/tests -t architecture/scripts`).

## Amendments (2026-08-22, questctl introduction + taskctl sequential-blocking clarification)

Introduces a fifth tool, `questctl` (design-questctl.md), for managing Questions that need answering — deliberately modeled as "taskctl, but for questions" rather than a fresh design, since the two share almost the entire object model. Writing questctl's doc surfaced an ambiguity already latent in taskctl's own doc, closed in the same pass.

- **questctl's Group/Subgroup replace taskctl's single-level Phase**, structured as a regular ≤2-level tree — identical in *shape* to adrctl's Domain/Component (design-adrctl.md, "Metagroups"), not a new hierarchy pattern. What's actually new is **optional depth of attachment**. *(Superseded the same day — see "Amendments (2026-08-22, grilling: uniform per-store depth, bespoke Answer section, `[~]` gating)" below: depth turned out to be a whole-store property, not per-object, and `ungroup` was dropped.)*
- **Object Type for an ungrouped Question needed no new mechanism.** design.md's derivation table already right-pads a short abbreviation with `_` to reach 6 characters; extending the table with a 0-level row (0 letters taken) naturally falls out to `______` via that same existing rule, and — since a real Group/Subgroup Name can never be empty — that code can never collide with a derived one, so no collision-resolution special case was needed either. Chosen over inventing a dedicated sentinel constant specifically because it requires no new concept, only a table row. (This reasoning survives the same-day correction below unchanged — only *where* the 0-row applies changed, from "this one ungrouped object" to "every object in this depth-0 store.")
- **`ungroup <id>` is a new operation** ... *(Superseded — see the same amendment below: dropped entirely once depth became a whole-store property with nothing for a per-object operation to act on.)*
- **`list --ungrouped`** ... *(Superseded alongside `ungroup` — see below.)*
- **`answer` is `annotate` with a different History prefix**, not a new field. ... *(Superseded — see below: the answer text moved out of History into its own section entirely.)*
- **questctl's `[B]`/`[R]`/`[C]` do not block work on other Questions; several Questions may be `[~]` at once.** This is the deliberate point of contrast against taskctl, and writing it down precisely required first pinning down what taskctl's own "sequential" processing actually means for `next` — previously implied but never stated as a rule. **Closed for taskctl in the same pass** (design-taskctl.md, new "Sequential Processing" section): `next` returns the *earliest Task, in priority order, that is not `[X]`* — not simply "the next `[ ]` Task" — so a Task sitting in `[B]`/`[R]`/`[C]` is reported back as the blocker rather than silently skipped in favor of a later open Task. This was always the intent (taskctl's whole point is a single-threaded, resumable work queue with user/subagent handoff points, design.md's Vision) but the doc previously only specified the per-object state machine, not what "blocks the sequential processing" means for `next` across objects — a gap that would otherwise have left taskctl's and questctl's `next` looking identical on paper despite being opposite in behavior. **This part stands unchanged** — only questctl's own side of the contrast (below) was refined further.
- **Store name `questions` (plural)**, following `tasks`/`rules`/`adrs`, not `spec`'s singular exception (design-decisions.md, "Amendments (2026-08-19, shared-root resolution)": the singular/plural split reflects one-document vs. many-small-objects, and questctl is squarely the latter). Stands unchanged.

## Amendments (2026-08-22, grilling: uniform per-store depth, bespoke Answer section, `[~]` gating)

A `/grill-me` pass on the questctl introduction above, the same day, surfaced that "a Question may attach at any depth" had been read too literally as *per-object*. The user's actual intent: depth is chosen once per store, uniformly — "wenn eine Datei eine Frage mit 2 Metagruppen hat, dann sind alle Fragen unter (potentiell anderen) L2-Metagruppen." Three changes resulted, plus one applied symmetrically to taskctl.

- **Metagroup depth is a whole-store property, not a per-object one**, for both questctl (0/1/2) and taskctl (0/1) — generalized into design.md itself (a "Metagroups" bullet), since it's now genuinely shared machinery between two tools, not a questctl-only quirk. A tool may declare an **allowed range** of level-counts instead of one fixed number; the depth actually used is uniform across every object in a given store. This directly obsoletes `ungroup` and `list --ungrouped` (design-questctl.md's first draft, both dropped): there is no per-object depth to change or filter on anymore, only a whole-store one fixed at creation.
- **Lock-in mechanism, modeled on `resolve_root`'s own precedent** (design.md, "File and Directory Parameters": infer the mode from what's on disk, don't persist a separate marker): the depth is inferred, not stored — fixed by the first successful object `add` (whichever depth it does or doesn't use), or by an earlier `add-subgroup` call, which unambiguously implies depth 2 before any object need exist. A bare `add-group` call decides nothing by itself, since it's valid scaffolding for either a depth-1 or depth-2 store — only `add-subgroup` (unambiguous) or an actual object `add` (which reveals its own real depth) can lock things in. Chosen over an explicit `init`-style operation (specctl's approach, design-decisions.md "specctl `init` lifecycle") for the same reason specctl's own amendment gives for *not* generalizing `init` to the other three tools: taskctl/questctl have no Title/Preamble-shaped content needing an up-front setup step, so introducing `init` here would reintroduce exactly the asymmetry that amendment argued against.
- **Once locked, `add-group`/`add-subgroup` stay available only where they could still matter**: both in a depth-2 store, only `add-group` in a depth-1 store, neither in a depth-0 store. This is a direct consequence of "uniform depth," not a separately-invented rule — an `add-subgroup` in a depth-1-locked store, or any `add-group`/`add-subgroup` in a depth-0-locked store, could never have an object attach to what it creates.
- **A depth-0 store's objects sit directly in the store root** (directory mode), which becomes the sole metagroup-path directory that ever exists for that store, complete with its own `.index.md`/`.index.json` pair — unchanged from the first draft's reasoning, just now applying to the *whole store* rather than to a subset of objects coexisting alongside grouped ones. Same fallback for taskctl's phase-less mode, symmetrically.
- **The Answer became a dedicated, bespoke content field** (`### Answer`, design.md Object Format's tool-specific-section slot), not a repurposed History entry type. Root cause: design.md's generic `set-<user-content-block>` always logs a fixed `M` entry (design-decisions.md, "Amendments (2026-08-19, closing spec/implementation gaps)"), so a plain User Content block named "Answer" would need either a second write path (`set-answer`, logging `M`) alongside `answer` (logging something else), or `set-answer` suppressed entirely — the ambiguity the user's redesign request resolves by moving the content itself out of History altogether. Decided: `Answer` is written *only* by `answer <id> <text> --message "..."` — no generated `set-answer` — logging a single `T` entry per change (mandatory `--message`, mirroring `annotate`'s existing `required=True`, since the previous answer text is now genuinely gone once overwritten and the message is the only trace of why). Content is Markdown, `> `-quoted, handled exactly like `Description` (per the user's explicit clarification) — only the write path and logging differ. The prior design's `A`-prefixed History entries and "last `A` wins" rule are dropped entirely; confirmed via `lib/store.py`'s `annotate()` that neither it nor (by the same shape) `answer` can change status, so "mark several `[~]` before answering" (below) is necessarily a separate `set-status` step, not something `answer` itself does.
- **questctl's `[~]` now gates *starting* new work, store-wide, across both `next` and `next-all`** — not just `next-all`'s already-established precondition. While any Question anywhere is `[~]`, neither command hands out a `[ ]` Question; `[R]`/`[C]`/`[B]` do not hold this gate closed (moving out of `[~]` into any of them releases it, same as reaching `[X]` would), which is what still lets questctl's earlier `[B]`/`[R]`/`[C]`-doesn't-block-others property do real work: a batch can free the gate for the next batch while individual items in it remain unresolved. No new batch-start command was added for "mark several `[~]` before answering" — repeated `set-status <id> ~` calls suffice, and the acting agent already knows its own batch, so the shared gate only needs to stop *other* callers, not coordinate the batch's own members.
- **`next`/`next-all` distinguish three "nothing available" outcomes** — `in_progress` (gate closed by a `[~]`), `all_answered` (nothing but `[X]`, including the degenerate empty-store case), `awaiting_interaction` (nothing but `[X]`/`[R]`/`[C]`/`[B]`, with at least one of the latter three) — communicated via stderr message text and a `--json` `"reason"` field. All three exit 1, not just the first: chosen over a distinct exit 0 for `all_answered` specifically because a caller looping on `next` wants one uniform "stop asking" signal, and this matches both `next-all`'s prior-round design and taskctl's *already-implemented* `next` (`taskctl.py`'s `_handle_next`, confirmed via its `StoreError("no open tasks")` on the equivalent case), which already treats "nothing to hand out" as an error condition, not an empty success. taskctl itself needed no equivalent three-way split: its `next` always returns the blocking item itself (per the unchanged "Sequential Processing" amendment above) rather than ever reporting "nothing available" except in the one all-`[X]`-or-empty case it already handles today.

## Amendments (2026-08-22, questctl-author/-checker/-researcher design)

A `/grill-me` pass covering the three planned Subagent+Skill pairs around `questctl` (`architecture/docs/subagents/design-questctl-author.md`, `design-questctl-checker.md`, `design-questctl-researcher.md`, and their `-cli` Skill docs), modeled on `rulectl-author`/`rulectl-checker` where the shape carries over, diverging where questctl's own model forces it to. Two changes land in `design-questctl.md` itself, not just the Subagent docs — the rest is purely additive (new documents), touching no existing tool contract.

- **`questctl` gains a `source` Metainfo type** (design-questctl.md, "Metainfo"), populated the same way `rulectl`'s own `source` field already is. Surfaced by cross-referencing `rulectl-author`'s traceability convention against questctl's actual Metainfo set (`review`/`assignee-type`/`assignee-name`, inherited verbatim from taskctl) and finding no home for it there at all — a requirements-traceability tool authoring Questions in bulk, with no field pointing back to which requirement a Question came from, is a real defect the architect role exists to catch before it's built, not a style preference. **Implemented the same day** — `lib/questctl_spec.py`'s `MetainfoSpec` tuple gained the new entry; no other code changes were needed (the generic `info-<type>`/`--<type>` machinery picks up any declared Metainfo type automatically).
- **`next`/`next-all` gain an optional `--group`/`--subgroup` scope filter** (design-questctl.md, "Operations"/"CLI Contract additions"), mirroring `list`'s existing flag shape. Needed because `questctl-checker`/`questctl-researcher` (design-questctl-checker.md/design-questctl-researcher.md) must be pointable at one Group/Subgroup subtree of a store that accumulates several unrelated "Fragekomplexe" over time — without it, a Checker run matching last month's client answers could start attributing them into a currently-open, unrelated complex it was never asked to touch. The `[~]`-in-progress gate itself stays **unscoped** even when a filter is given — a Question `[~]` outside the filtered subtree still blocks new work, since the gate's whole point ("an agent is already working somewhere in this store") doesn't depend on where; scoping the gate too would reintroduce exactly the per-branch complexity the original design (`design-decisions.md`, "Amendments (2026-08-22, grilling: uniform per-store depth, bespoke Answer section, `[~]` gating)") deliberately rejected in favor of one global rule. **Implemented the same day** — `questctl.py`'s `_configure_parser` gained `--group`/`--subgroup` on both subcommands, and `_handle_next`/`_handle_next_all` now split the record set into an unscoped list (for the gate check) and a scoped one (for what's actually returned), reusing the same `resolve_metagroup_path`-based matching `list` already does in `lib/cliapp.py`'s `dispatch()`. Covered by 9 new tests (`TestSourceMetainfo`, `TestNextScopeFilter`, `tests/test_questctl.py`) — full suite now 523.
- **Grouping in `questctl-author` is semantic, not structural** — the single biggest departure from the original design sketch (which proposed mapping a source directory's own folder nesting onto Group/Subgroup) and from `rulectl-author`'s own per-candidate, on-the-fly metagroup resolution. A source directory's folder names carry no weight; the taxonomy is derived purely from the atomized candidates' own content (plus the invocation prompt's own grouping hints), proposed as a **complete** Group/Subgroup structure and confirmed with the user **once, up front, before any candidate is atomized against it** — a deliberate strengthening of `rulectl-author`'s narrower "just new Language names" batching, justified by the fact that a wrong taxonomy here permanently locks the store's whole-store-uniform depth (design-questctl.md, "Metagroups"), unlike a wrong `rulectl` metagroup path, which `group-<metagroup-type>` fixes cheaply after the fact.
- **Depth choice for a fresh store**: depth 2 only if *every* proposed Group has genuine sub-structure; otherwise flatten the whole taxonomy to depth 1. Chosen over "depth 2 whenever *most* Groups subdivide, with a synthetic filler Subgroup for the rest" specifically to avoid *ever* inventing a synthetic Subgroup when a fresh store still has the freedom not to need one — that escape hatch doesn't exist for a store *already* established at depth 2 by an earlier run, where a synthetic Subgroup (design-questctl-author.md, step 3c) is the only option left once the depth itself can no longer be renegotiated.
- **Checker/Researcher's claim-timing deliberately inverts `rulectl-checker`'s own pattern**: `rulectl-checker` claims a Task `[~]` *before* examining it; both new Subagents search *first* and claim only once there's something to record. Root cause: questctl's `[~]` gate is global and store-wide (nothing analogous exists in taskctl), so claiming early would hold every other agent's `next`/`next-all` shut for the entire duration of examining each Question in sequential mode — a cost `rulectl-checker`'s per-Task, non-global gate never had to pay. Parallel mode is the deliberate exception (claim the whole named-scope batch up front, by design) precisely because reserving the batch *is* the point there.
- **A batch-claimed Question with no match/evidence resolves to `[B]`, not "stays `[ ]`."** Surfaced by reconciling two separately-confirmed answers that turned out to be in tension: sequential mode's "no match → leave `[ ]` untouched" (confirmed for the general case) assumes the Question was never claimed — true in sequential mode (claim comes after the search), but false in parallel mode (the whole batch is claimed *before* any searching, that being the entire mechanism parallel mode relies on). Since `design-questctl.md`'s Status model defines no `[~]→[ ]` step, "stays `[ ]`" is not actually reachable for an already-claimed Question — `[B]` (with a message explaining why) is the only coherent resolution, and also the one that lets the store-wide gate clear once every batch member reaches *some* terminal-ish status, rather than one stuck `[~]` blocking the whole store indefinitely.
- **`questctl-checker`'s attribution is strictly verbatim** (typos included), confirmed explicitly by the user over this document's own first-draft proposal of allowing "light rewording." Assembly of several verbatim excerpts into one Answer is still allowed — that's judgment about *which* excerpts belong together, never judgment about *what the answer says*.
- **`[~]→[R]` needs `info-review <id> user` first, for both new Subagents** — caught and fixed while drafting `design-questctl-checker-cli.md`'s first pass, which incorrectly claimed this step was unnecessary. Verified directly against `lib/taskctl_spec.py`'s `validate_transition` (reused verbatim by questctl, confirmed by running it against a `review`-unset record and observing the rejection): it reads a Question's *current* `review` metainfo at the moment of `set-status`, exactly as `rulectl-checker-cli` already documents for its own taskctl-side workflow — this was never actually a difference between the two tools, only a drafting error in a first pass over this document.
- **`questctl-researcher` has no direct `rulectl` precedent** — its evidence-threshold discipline ("never guess an answer to avoid leaving a Question open," an `[X]` requires being able to state *why* the coverage is sufficient) is adapted from `rulectl-checker`'s compliance-verdict judgment (design-rulectl-checker.md, step 3d), the closest existing analogue for "form a judgment against evidence, don't guess" even though what it produces is structurally closer to `questctl-checker`'s own output shape (an `answer` call) than to a bare verdict. v1 is deliberately restricted to open (`[ ]`) Questions only, via `next`/`next-all` — re-auditing already-`[X]` Questions against a changed Datenbasis needs a different selection mechanism (`list --status X`, bypassing the `next`/`next-all` gate entirely) and is left as a named future extension rather than half-built now, the same restraint `rulectl-author` applies to its own out-of-scope items.

## Amendments (2026-08-22, questctl/taskctl implementation)

Implements the design above against `lib/`, `taskctl.py`, and a new `questctl.py`. One design correction surfaced; everything else translated directly.

- **`add-phase` locks taskctl's depth to 1 immediately**, on the first Phase created — even before any Task exists — contrary to the previous amendment's text ("add-phase is rejected once a store is locked at depth 0... fixed by the first successful `add`"), which implied only an object `add` could ever lock taskctl's depth. Caught while implementing `Store._established_depth()`'s general rule (design.md, "Metagroups": "a metagroup path already created at the tool's own maximum declared depth" locks immediately) against taskctl specifically: Phase is taskctl's *only* declared level, so it is simultaneously its shallowest and its deepest — exactly the unambiguous case questctl's `add-subgroup` already gets, not the ambiguous-either-way case questctl's `add-group` gets. Fixed in both the implementation (one general rule, `Store._check_metagroup_creation_depth`, applies uniformly to both tools — no special-casing needed) and design-taskctl.md's "Metagroups" text, which previously implied the opposite for taskctl specifically.
- **One general mechanism serves both tools**: `ToolSpec.variable_depth: bool` (default `False`, unchanged for rulectl/adrctl/specctl) and `Store._established_depth()`/`_check_metagroup_creation_depth()`/`_check_object_depth()` (the latter two implementing, respectively, the "≤ established" rule for `add-<type>` and the "== established" rule for `add`, design-decisions.md above). `_established_depth()` reads whatever already exists — an object's own depth first, then a metagroup path at the tool's max depth, then (directory mode only) the store root's own `.index.md` — never a separate persisted marker, mirroring `resolve_root`'s own inference-over-marker precedent exactly.
- **Depth-0's Object Type needed no new sentinel mechanism, confirmed working as designed**: `lib/abbrev.py` gained a `0: ()` row in `_WIDTHS_BY_LEVEL_COUNT` and a `widths_target_length(0) == 6` special case (0 levels has nothing to sum, but still pads to the standard width); `derive_object_type([], {})` and `natural_object_type([])` both now route through it and return `"______"`, exactly as design-questctl.md/design-taskctl.md ("Object Type") already specified. A depth-0 store's root directory registers itself the same way any other metagroup directory does (`lib/metagroup.py`'s new `dir_ensure_root_registered`, idempotent, reusing `index.write_abbrev`/`index.read_abbrev` unchanged) — the existing `_all_metagroup_directories()` walk already includes any directory with a recorded abbrev, so no changes were needed there at all.
- **`answer` needed one new generic `Store` primitive, `annotate_content(object_id, block, value, message)`** — content write + `T` log in one step, factored out because `set_content` (the generic path) is hardwired to log `M`, and `annotate` (the generic `T`-logger) doesn't touch content at all; questctl's `answer` command is a two-line wrapper over it. Suppressing the generic `set-answer`/`--answer` used a new `ToolSpec.no_generic_setter: tuple[str, ...]` field, checked at exactly the three places `lib/cliapp.py` would otherwise generate that surface (the `add`-inline-flag loop, the `set-<block>` subcommand loop, and the `add` dispatch's content-dict comprehension) — `Answer` still appears in `user_content_blocks` so `objectfile.py`/`render.py` render/parse/display it exactly like any other block, only its *write* path is restricted.
- **`next`/`next-all`'s three-way "nothing available" signal is `lib/store.py`'s new `NoWorkAvailable(StoreError)`**, carrying a `.reason` string, caught specifically in `lib/cliapp.py`'s `main()` (before the generic `StoreError` catch) to emit `{"reason": ..., "message": ...}` on `--json` instead of the plain stderr line every other error gets — the only place the CLI engine now branches on an exception *type* beyond `StoreError`/`CliError`/`ValueError`, kept intentionally narrow (one `except` clause, no broader "structured error" mechanism) since no other tool has a comparable need yet.
- **Fixed in the same pass, a genuine pre-existing gap, not something the redesign introduced**: `lib/cliapp.py`'s `_print_result` only ever rendered a `next` result with `render.short_line` (no History), even though design-taskctl.md already promised "including its History" before this session's changes began. Now keyed on `args.command == "next"` generically (alongside the existing `show --history` case) — a one-line fix that benefits both taskctl's and questctl's `next` uniformly, since neither tool's own code decides this, the shared engine does.
- **taskctl.py itself needed no code changes at all** — every behavioral change routes through `lib/taskctl_spec.py` (`variable_depth=True`, `object_type_from_phase`'s depth-0 fallback) and the shared `lib/` engine; the CLI script's own `_handle_next`/`_handle_annotate`/`_configure_parser` were already generic enough (e.g. `metagroup_levels` sorts fine on an all-empty-tuple store) to need nothing further.
- **questctl's status machine is a direct import from `lib/taskctl_spec.py`** (`OPEN`/`IN_PROGRESS`/`REVIEW_USER`/`REVIEW_SUBAGENT`/`BLOCKED`/`DONE`, `validate_transition`), not a third shared module — the two tools are the only ones using this exact state machine, so extracting a new module for it would be premature; `lib/taskctl_spec.py`'s docstring now says so explicitly.

## Amendments (2026-08-25, taskctl `NoWorkAvailable` + taskctl-author-cli/taskctl-worker-cli design)

A `/grill-me` pass on the two planned Skills around `taskctl` itself (`architecture/docs/skills/design-taskctl-author-cli.md`, `design-taskctl-worker-cli.md`, and their `SKILL.md`s) — unlike `rulectl`/`questctl`'s Author/Checker(/Researcher) pairs, `taskctl` has no upstream tool exporting a bounded tasklist into it (design-taskctl.md, "Operations": Tasks may originate from `rulectl tasklist`, but `taskctl` itself doesn't care), so the pair here is Author (creates/extends Tasks directly) and **Worker** (works them, changing Status per the work done) rather than Author/Checker. Deliberately scoped to just the two Skills, not their future Subagents (`taskctl-author`/`taskctl-worker` — no `design-taskctl-author.md`/`design-taskctl-worker.md` yet, unlike `rulectl-author`/`rulectl-checker` which already had both layers before their Skills were written): the Skills stand as pure CLI-contract references, workflow-agnostic, the same way `rulectl-author-cli`/`rulectl-checker-cli` do.

- **One small `taskctl.py` code change, found while scoping `taskctl-worker-cli`'s recipes**: `_handle_next` now raises `lib/store.py`'s existing `NoWorkAvailable("all_done", "no open tasks")` instead of a bare `StoreError`. This **reverses** the explicit call made in "Amendments (2026-08-22, grilling: uniform per-store depth, bespoke Answer section, `[~]` gating)" ("taskctl itself needed no equivalent three-way split... already treats 'nothing to hand out' as an error condition") and in "Amendments (2026-08-22, questctl/taskctl implementation)" ("taskctl.py itself needed no code changes at all") — both correct at the time (no consumer needed structured JSON on that path), but `taskctl-worker`'s loop mode (see below) now does: it must tell "drained, stop cleanly" apart from a genuine failure (a corrupt store, a lock timeout) when scripting against `--json next`, exactly the problem `NoWorkAvailable` already solves for questctl. taskctl needs only the one `all_done` reason — it has no `in_progress`/`awaiting_interaction`-shaped cases, since `next` already always hands back the blocking Task itself rather than reporting "unavailable" around it (design-taskctl.md, "Sequential Processing", unchanged). One line in `_handle_next`, no other code touched; `design-taskctl.md`'s "Operations" section now documents the `reason`/`--json` shape explicitly, mirroring design-questctl.md's own "CLI Contract additions" wording. Covered by a new `test_next_no_work_available_is_json_structured` (`tests/test_taskctl.py`); full suite now 524.
- **Command partition mirrors "creating/extending" vs. "working"**, not "authoring" vs. "checking compliance" (there is no compliance verdict here, just arbitrary described work): `taskctl-author-cli` covers `add-phase`/`add`/`list`/`show`/`show-metagroups`/`set-description`/`group-phase`/`reorder`/`delete`/`info-review`/`info-assignee-type`/`info-assignee-name`; `taskctl-worker-cli` covers `next`/`set-status`/`annotate`/`show`, plus `info-review` for exactly one purpose (below). Both exclude `reindex`/`history` (maintenance/reporting, neither authoring nor working) and, per the same "pure CLI-contract reference" stance `rulectl-checker-cli` already takes, neither Skill prescribes *how* to judge a duplicate/overlapping Task or *how* to actually perform a Task's described work — that's the future Subagents' job.
- **`taskctl-worker` may call `info-review` too, not just `taskctl-author`** — the one metainfo-axis operation shared across the split. A Task's `review` value is normally fixed at creation (`add --review ...`), but real work surfaces review needs an author can't always foresee; the Worker may escalate (`none`→`user`/`subagent`, mirroring `rulectl-checker`'s own `info-review <id> user`-before-`R` pattern, design-rulectl-checker.md) or de-escalate (`user`/`subagent`→`none`, symmetric case, e.g. a pre-flagged Task turns out not to need review after all) immediately before the corresponding `set-status` call. The Worker never touches `info-assignee-type`/`info-assignee-name` — reassignment is an authoring action.
- **`taskctl-worker`'s iteration model defaults to one Task per invocation** (worked to its next resting point — `[X]`, or an escalation `[R]`/`[C]`/`[B]`), **looping only when the invoking user explicitly asks for it** (repeated `next` calls until `NoWorkAvailable`/`all_done`, or until `next` returns a Task already sitting in `[B]`/`[R]`/`[C]` — nothing further to do this run, since `next` would just keep re-returning it). This is an invocation-time instruction to the Subagent, not a `taskctl` CLI flag — no scope-filter equivalent to questctl's `next --group`/`--subgroup` was added, since `assignee-type`/`assignee-name` stay purely informational for `taskctl-worker` (see below), leaving nothing for a filter to scope by.
- **The Worker never targets a Task ID other than the one `next` just returned.** Since `next` always returns the earliest not-done Task in priority order (design-taskctl.md, "Sequential Processing", unchanged), a later Task can only legitimately be `[~]` if a *prior*, in-order Worker invocation put it there — so this invariant is self-enforcing given `next`'s existing selection rule, not a new mechanism. A Task `next` returns already `[~]` is a **resume** (read its History via `show --history` for context; no redundant `[~]`-transition), never grounds to start a different Task instead.
- **`assignee-type`/`assignee-name` stay purely informational for `taskctl-worker`** — considered and rejected: filtering `next` to only Tasks matching the Worker's own assignee (would have needed a new `next --assignee-type`/`--assignee-name` CLI filter, allowed in principle but not built). Rejected as a bigger model change than this pass's two-Skill scope warrants — `taskctl`'s "Sequential Processing" is one global queue, not per-assignee lanes — and revisit only if task hand-off routing is actually needed later, not speculatively.

## Amendments (2026-08-25, taskctl-author/taskctl-worker Subagent design)

A `/grill-me` pass writing the two Subagent design documents the previous
amendment deliberately deferred (`architecture/docs/subagents/design-taskctl-author.md`,
`design-taskctl-worker.md`) — the CLI-contract Skills already existed;
this pass designs the workflows that actually use them. `taskctl-author`
was explicitly modeled on `questctl-author`, diverging where taskctl's own
purpose forces a real difference; `taskctl-worker` has no direct precedent
(no sibling Subagent *executes* what it reads, the rest only ever judge
or attribute).

- **`taskctl` gains a `source` Metainfo type**, mirroring the identical gap
  closed for `questctl` in "Amendments (2026-08-22, questctl-author/-checker/
  -researcher design)" above, for the same reason: `taskctl-author` bulk-authors
  Tasks from source documents, and a traceability field pointing a Task back
  to what informed it was missing. **Implemented the same day** —
  `lib/taskctl_spec.py`'s `MetainfoSpec` tuple gained the entry (no other
  code changes needed, the generic `info-<type>`/`--<type>` machinery picks
  it up automatically); `lib/questctl_spec.py`'s own `source` field comment,
  which had claimed this was "not part of taskctl's own Metainfo set,"
  updated to stop contradicting itself. `design-taskctl.md`'s "Metainfo"
  section, `design-taskctl-author-cli.md`, and `taskctl-author-cli/SKILL.md`
  updated to expose `--source`/`info-source` in the authoring workflow.
  Covered by `test_source_metainfo_settable_inline_and_via_info`
  (`tests/test_taskctl.py`); full suite now 525.
- **`taskctl-author`'s generation model is prompt-driven synthesis, not
  worklist atomization** — the single biggest departure from
  `rulectl-author`/`questctl-author`, and from the original request's own
  first framing ("arbeitet ähnlich wie questctl-author"). Those two
  Subagents walk a document's own structure and reconcile every unit
  against a report, guaranteeing nothing is silently dropped. A Tasklist is
  a *plan* the user's prompt asks for, not an inventory of its sources — the
  prompt does double duty as a **scope filter** (which subset of the
  sources' content becomes Tasks at all) and a **detail constraint** on how
  Tasks are written (e.g. "no Bash scripts, only Python"). This has a real
  consequence for the trust story: since there's no worklist forcing
  verbatim unit-by-unit extraction, **every Task Description is this
  Subagent's own synthesis, never a copied excerpt** — which is what then
  lets `taskctl-worker` treat a Task's Description as a trustworthy
  instruction to execute (see below), a guarantee `questctl-checker`'s
  deliberately-verbatim `answer` could never offer if it executed anything.
- **No Phase-taxonomy confirmation gate**, unlike `questctl-author`'s
  batched Group/Subgroup confirmation. That gate exists specifically
  because a wrong *depth* choice has no cheap undo; taskctl's Phase model
  is single-level and `taskctl-author-cli` already has cheap undo
  (`group-phase`/`reorder`/`delete`), so the risk the gate exists to
  prevent doesn't transfer. Phases are proposed and created directly,
  reported afterward like everything else.
- **Extend/shrink is prompt-triggered only, never auto-detected from store
  state** — whether a run creates fresh Phases, adds to existing ones, or
  removes Tasks is read entirely from what the invocation prompt says (a
  reference to "die Installationsanweisungen der Tasklist" resolved via
  `list`/`show`, the same judgment-based matching duplicate-checking
  already uses), not branched on whether `--root` already has content.
  This fell out directly from treating the existing store as "just more
  context" (per the prompt-driven-synthesis point above) rather than as a
  fresh-vs-extend mode switch requiring its own detection logic.
- **Shrink is the one gated write in the whole design** — deletion has no
  undo (`design.md`, "Object Operations": no tombstone), unlike every other
  mistake this Subagent can make, so it's the one place a pre-write
  confirmation belongs even though Q3's "no gate" reasoning otherwise holds
  for everything else. Present exactly what would be deleted, wait for
  explicit confirmation, delete only after. A run ending before that
  confirmation arrives deletes nothing and reports
  **deferred-awaiting-deletion-confirmation** for the targeted items —
  reusing `questctl-author`'s own deferred-decision shape (no separate
  resume mechanism; invoking again re-evaluates against the store's
  then-current state).
- **`taskctl-worker` states an explicit untrusted-content boundary**,
  something no other Subagent needed to add this late because none of them
  *execute* what they read — `rulectl-checker` only judges a codebase,
  `questctl-checker` only attributes verbatim text into an `Answer` field.
  `taskctl-worker` runs Bash/Edit/whatever a Task's Description calls for,
  which is a materially larger blast radius if that content were ever
  attacker-influenced. The boundary that makes it safe is stated from both
  sides: `taskctl-author` never copies untrusted source text into a Task
  verbatim (see above), and `taskctl-worker` trusts a Task's Description
  specifically *because* of that — not as a blanket, unexamined trust in
  anything labeled "Task."
- **No `next` scope filter, no tool allow-list, no separate codebase-path
  input for `taskctl-worker`** — three deliberate non-additions, all
  following the same shape: `rulectl-checker` needed each of these (a
  Rule-scope filter, a vetted-tool allow-list for `checkable=<tool>`
  Tasks, an explicit codebase path independent of `--root`) because it is
  *always* checking code against Rules from a possibly-different
  repository. `taskctl-worker`'s Tasks are arbitrary by design — not
  always code, not always in one repository — so none of those three
  fixed-shape inputs generalizes; where scoping is needed at all, it's
  expressed in the invocation prompt itself, in whatever terms fit that
  run, not as a structured parameter.
- **Iteration mode is prompt-controlled, confirmed unchanged from the
  previous session's design**: one Task per invocation by default,
  looping only when the prompt explicitly asks for it. This request's own
  phrasing ("Wenn nicht im Prompt explizit anders spezifiziert, wird immer
  nur die nächste Task bearbeitet") independently reconfirmed
  `design-taskctl-worker-cli.md`'s existing "Iteration model" section
  rather than changing it.
- **`taskctl-worker`'s outcome judgment is adapted from `rulectl-checker`'s
  compliance-verdict discipline and `questctl-researcher`'s evidence
  threshold**, not invented fresh: `[X]` requires being able to state *why*
  the work is actually complete and correct, not just that nothing
  obviously failed; a concrete, reasoned `[R]`/`[C]`/`[B]` is preferable to
  a guessed `[X]` the evidence doesn't back. Carried over as precedent
  rather than re-litigated, since the same judgment-integrity concern
  applies here as to every other Subagent that forms a verdict.

## Amendments (2026-08-27, specctl-author/specctl-adr-author design)

A `/grill-me` pass designing the first Subagent+Skill pairs around `specctl`
and `adrctl` together (`architecture/docs/subagents/design-specctl-author.md`,
`design-specctl-adr-author.md`, and three Skill docs:
`design-specctl-author-cli.md`, `design-specctl-editor-cli.md`,
`design-adrctl-author-cli.md`) — neither tool had one before, and
`VISION.md` didn't mention either. Design docs only, same as the
`taskctl-author`/`taskctl-worker` pass: the actual `SKILL.md`/Subagent files
don't exist yet.

- **Split by lifecycle phase, not by tool**: `specctl-author` (draft-phase,
  full CRUD, `specctl`-only) creates and freely restructures content while
  it's still `draft`; `specctl-adr-author` (stable-phase) promotes a Section
  to `stable` and, from then on, revises it — always under `adrctl`
  governance. The two never call each other, and `specctl-adr-author` never
  creates a new Section.
- **First Subagent in this project family whose workflow spans two tools'
  CLIs through two separate Skills** (`specctl-editor-cli` +
  `adrctl-author-cli`), a deliberate exception to the otherwise-uniform
  one-Subagent-one-Skill pattern (`VISION.md`: "jeweils als Paar"). Chosen
  over splitting stable-phase work across two further Subagents (one per
  tool, sequenced by a third orchestrator) because a stable-phase change is
  a single atomic unit — the `specctl` edit and the `adrctl` decision that
  authorizes it — and splitting that coupling across an invocation boundary
  would only reintroduce the ordering problem it exists to solve (see
  below). `specctl-editor-cli` is a second, narrower-scoped Skill over the
  same `specctl` CLI that `specctl-author-cli` already covers in full —
  mirrors the existing `rulectl-author-cli`/`rulectl-checker-cli` split over
  one CLI for two different Subagents.
- **Mechanically discovered ordering constraint, corrected mid-pass**: an
  early recommendation had `specctl-author` perform the `draft`→`stable`
  promotion itself, on the (unverified) assumption that only *subsequent*
  content edits to an already-`stable` Section need a governing ADR.
  Grepping `lib/spec_store.py`'s actual `set_status` showed the ADR
  requirement (`_ADR_REQUIRING_STATUSES`) applies to the **transition
  itself**, not just to edits made afterward — so promotion mechanically
  requires an ADR to already exist at the moment of transition, exactly
  like a content edit does, with no exception for a first-time `draft`→
  `stable` move (unlike `add --set-status stable` on a *brand-new* Section,
  which *is* exempt — an initial-value choice, not a transition,
  `design-specctl.md`, "Status"). Promotion therefore moved entirely to
  `specctl-adr-author`, which mints a single founding ADR (topic: "this
  content is now accepted") and only then calls `set-status stable` — a
  case study in why this project's process greps the implementation before
  finalizing a recommendation that depends on undocumented mechanical
  behavior, not just before shipping code.
- **ADR-before-edit resolution, generally**: since `specctl` requires a
  valid `adr` reference *already set* (inline `--adr`, or already
  propagated) at the moment of a `stable` Section's status transition or
  content edit, the literal call order for any stable-phase change is
  always "mint/identify the ADR, then the `specctl` write" — even though
  the Grundidee's own wording ("Änderungen an der Spec werden zuerst mit
  `specctl` integriert. Danach werden... ADR(s)... erzeugt") reads the
  opposite way. Resolved by reading that sentence as describing which
  artifact is *authoritative* (the ADR is what makes the change legitimate),
  not the literal CLI invocation sequence: `adrctl add --spec-ref
  <section-id> --set-status accepted` first (auto-propagates the ADR's ID
  into the Section's `adr` field, `design-specctl.md`, "ADR Linkage"), then
  the `specctl` write, which now succeeds without even needing an inline
  `--adr`.
- **ADRs from this workflow are always created directly `accepted`**
  (`add --set-status accepted`), never left at `adrctl`'s own default
  initial Status `proposed` — the user's own change request already
  constitutes the decision being documented; a separate `proposed` stage
  would only add a redundant manual step with no real review happening in
  between that it would meaningfully gate.
- **One ADR per coherent topic, topics judgment-atomized from the change
  request** — the same "atomic candidates" reasoning `rulectl-author`
  applies to a document (`design-rulectl-author.md`, step 2), applied here
  to a natural-language change request instead of a source document. No
  duplicate-check step, unlike `rulectl-author`/`questctl-author`/
  `taskctl-author`'s own candidate-deduplication passes: a topic here comes
  directly from an explicit, already-decided request, not from atomizing
  ambiguous external material, so there is no ambiguous candidate pool to
  de-duplicate against.
- **Multi-Section topics, given `spec-ref`'s single-valued constraint**
  (already established, "Amendments (2026-08-19, spec-ref single-valued)"
  above): the new ADR's `--spec-ref` names one "primary" Section (chosen
  deterministically, e.g. first named in the prompt — carries no meaning
  beyond being the one `spec-ref` points at); every additional Section the
  same topic touches is linked afterward via `specctl set-adr <id>
  <adr-id>` — the existing, documented-but-until-now-unused-for-this-purpose
  manual correction command (`design-specctl.md`, "Operations": "a
  correction tool, not validated"), reused here for a legitimate multi-link
  case rather than inventing a new mechanism. The caller discipline this
  requires (only ever pass an ADR ID this same run just created or
  confirmed exists, since `set-adr` performs no validation of its own) is
  stated explicitly in `design-specctl-editor-cli.md` and
  `design-adrctl-author-cli.md`.
- **Revising an already-governed Section explicitly supersedes the old
  ADR** (`adrctl info-superseded-by` + `set-status superseded`) rather than
  letting the Section's `adr` field get silently overwritten by
  auto-propagation, leaving the old ADR sitting at `accepted` forever even
  though it's no longer the governing decision — `adrctl` already has
  `superseded-by` (`design-adrctl.md`, "Metainfo") precisely for this case;
  not using it here would ignore a mechanism built for exactly this
  situation, for no reason beyond it not being autopropagated by default.
- **Intent classification — correction vs. new decision — is
  prompt-driven, not tool-driven, decided by the requester over this
  document's own first-draft framing** (which had proposed "every revision
  to already-governed content gets its own new, superseding ADR,"
  full stop). A user offering several quick revisions to the same
  just-drafted wording ("das war falsch formuliert, mach nochmal") should
  not accumulate one superseding ADR per iteration — that would flood the
  ADR history with noise documenting wording churn, not decisions. Resolved:
  when the prompt's own phrasing for a topic reads as a correction
  ("revise"/"redo"/"correct"/"fix," or equivalent — judged semantically,
  never by literal keyword match) to a Section that already has a governing
  ADR, no new ADR is created; the existing one is reused **and its own
  content updated** (only the fields that actually go stale) to stay
  accurate, rather than just silently reusing its ID for gating purposes
  alone. **Gated by an explicit user confirmation before every such
  reuse/overwrite, with no memory-based shortcut across repeated
  corrections in the same session** — each invocation is stateless per the
  existing "no separate resume mechanism" precedent
  (`design-rulectl-author.md`/`design-taskctl-author.md`), so nothing short
  of asking every time could tell "the user already agreed to this kind of
  thing" from "this correction is different." A declined confirmation falls
  back to the normal new-ADR-plus-supersede path for that topic — the
  classification is only ever a shortcut the user can override, never a
  hard branch foreclosing the other path. A topic with **no** prior
  governing ADR (a first-time promotion) is never eligible for this
  classification at all — there is nothing yet to reuse.
- **`specctl-author` self-`init`s a brand-new store** rather than requiring
  a separate manual setup step, asking the user for a Title only when the
  prompt's own wording doesn't already make one obvious — `specctl`'s own
  `init` requirement (`design-specctl.md`, "Store";
  "Amendments (2026-08-20, specctl `init` lifecycle)" above) is a mechanical
  wrinkle every other tool's auto-vivification doesn't have; routing around
  it inside the Subagent keeps "just works on a brand-new project"
  uniform across the whole family rather than pushing an asymmetric manual
  pre-step onto the user for this one tool.
- **No batched creation gate for `specctl-author`'s Part-level metagroup**,
  unlike `rulectl-author`'s Language gate or the new `adrctl-author-cli`'s
  Domain gate (below): those gates exist to protect against an *autonomous*
  judgment call over external material with no user present to correct it
  mid-decision. `specctl-author` fulfills exactly what the user's own prompt
  asks for, this exact turn — there is no autonomous-judgment risk left for
  a gate to guard against, only the already-cheap `rename`/`move-to-<type>`
  undo path if a placement turns out wrong.
- **`adrctl-author-cli` gains a Domain-level creation gate**, mirroring
  `rulectl-author-cli`'s Language gate exactly (`design-rulectl-author.md`,
  step 3): `adrctl`'s Domain is the coarsest, only-2-level axis, and a
  spurious top-level Domain is the expensive mistake to make casually, the
  same reasoning that justified the Language gate originally. Component
  (the leaf) is created freely, same as Context/Category.
- **`specctl-author`'s deletions stay ungated**, deliberately diverging
  from `taskctl-author`'s shrink-confirmation gate: draft content is
  explicitly, by definition, pre-acceptance and low-stakes, and — unlike
  `taskctl-author`'s autonomously-inferred shrink targets — the user is
  driving this exact turn directly. A gate here would work against the
  "kooperativ" nature `VISION.md` describes for this workflow without
  preventing any real unattended-deletion risk.
- **`stable`→`deprecated` and `stable`→`draft` rework are both explicitly
  out of scope for v1**, manual/human-only CLI calls neither Subagent ever
  issues — `deprecated` per the original request's own "ausschließlich durch
  den User," and rework (newly surfaced during this pass, `design-specctl.md`
  allows it under `--force`) because reverting already-accepted content to
  unstructured free editing is a significant, easy-to-regret decision no
  routine prompt should be able to trigger.

## Amendments (2026-08-27, specctl-author/specctl-adr-author implementation)

A `/grill-me` pass writing the actual `SKILL.md`/Subagent files the previous
pass's design docs described:
`architecture/subagents/specctl-author.md`, `specctl-adr-author.md`,
`architecture/skills/specctl-author-cli/SKILL.md`,
`specctl-editor-cli/SKILL.md`, `adrctl-author-cli/SKILL.md`. Per the
requester's own choice among three offered verification levels, every
recipe across the three Skills was run against the real CLI in a scratch
store before being condensed into the final files — not just transcribed
from the design docs unverified. Two real mistakes surfaced this way, both
corrected in the design docs themselves (not just the new implementation
files, since a Skill's whole point is to be a CLI-contract reference a
Subagent trusts without re-deriving it) plus one clarification neither
needed code changes, only wording:

- **`move-to-<level>`'s path argument is the parent path, one level
  shallower than the target — not `<parent>/<own-new-name>`.** The original
  `specctl-author-cli` recipe (`move-to-chapter <id>
  "<Part name>/<new Chapter name>"`) was wrong on inspection: `move-to-chapter`
  actually failed with "expects a 1-segment parent path (got 2: ...)" against
  the real CLI. Worse, a second run confirmed `move-to-<level>` doesn't just
  reparent — it **changes the Section's own depth to match the command**,
  even converting an existing `Section`-depth object into a `Chapter` (its
  Object Type re-derived accordingly) when given `move-to-chapter`. This was
  always the documented behavior in `design-specctl.md`'s own "Operations"
  section (`move-to-<metagroup-type>`, "one subcommand per target level") —
  not a newly discovered tool behavior, just a mistake in how this pass's
  own first-draft Skill recipe read that existing text. Fixed in
  `design-specctl-author-cli.md` and the new `specctl-author-cli/SKILL.md`
  alike.
- **`specctl` has no `show-metagroups` command at all.** Both new specctl-
  facing Skill design docs (`design-specctl-author-cli.md`,
  `design-specctl-editor-cli.md`) and the `specctl-adr-author` subagent doc
  referenced it by analogy with the other three tools' shared generic
  engine — but `specctl.py` is its own hand-rolled CLI
  (`architecture/scripts/CLAUDE.md`: "nutzt bewusst nicht `lib/cliapp.py`"),
  confirmed directly against `build_parser()`'s subcommand list, which has
  no such entry (and a live `specctl --root ... show-metagroups` call fails
  with "invalid choice"). There's nothing for it to enumerate anyway — a
  Section already carries its own position/type directly, unlike the other
  tools' separate metagroup-path registry. Every reference now points at
  `list --under <path>` instead. This also surfaced a second, related gap
  while fixing the "Detecting initialization" recipe that had leaned on
  `show-metagroups`' non-existent error: `list`/`render`/`history` are
  explicitly **exempt** from `specctl`'s own initialization check
  (`design-specctl.md`, "Operations") and return empty output on an
  uninitialized store rather than erroring — verified directly (`list`
  returns `[]`, exit `0`; `render` returns empty text, exit `0`) — so no
  read command can ever detect "not initialized" at all. Only a **mutating**
  call's specific error text (`this specctl document has not been
  initialized yet -- run 'init <title>' first`, exit `1`) is a reliable
  signal; the design doc's own "simpler and preferred" fallback option
  already described exactly this, so the fix was deleting the broken first
  option, not inventing a new one.
- **The correction-confirmation gate (and `specctl-author`'s missing-Title
  case) are deferred, non-blocking reports, not literal in-run questions**
  — clarified in both subagent design docs and the new files, matching
  every existing gate in this project rather than reading as an interactive
  back-and-forth. Confirmed by checking precedent directly: no existing
  Subagent's `tools:` frontmatter lists anything `AskUserQuestion`-shaped,
  and `rulectl-author`'s Language gate, `questctl-author`'s taxonomy
  confirmation, and `taskctl-author`'s shrink-deletion confirmation all
  explicitly describe "no separate resume mechanism... invoking again
  re-evaluates" rather than a blocking wait. `specctl-adr-author`'s
  correction gate now reports `deferred-awaiting-correction-confirmation`
  for that one topic and continues with every other topic in the same run
  (mirroring `rulectl-author`'s "only the affected candidates wait");
  `specctl-author`'s missing-Title case reports `deferred-awaiting-title`
  for the whole run the same way.
- **Neither new Subagent needs `Read`/`Glob`/`WebFetch`** — both take
  prompt-only input (no document/URL mode), so their `tools:` frontmatter
  is just `Bash, Skill`.
- **Verification scope, as chosen by the requester**: every CLI recipe
  actually run against a scratch store (catching the two mistakes above);
  not extended to a full hand-simulated Subagent walkthrough, and not
  extended to literally invoking the new Subagents via the Agent tool —
  confirmed infeasible in this session regardless of choice, since
  `architecture/subagents/*.md` isn't wired into this session's own Agent
  tool at all (no existing project Subagent appears in its available agent
  types either — these files are deliverables for whatever project deploys
  these scripts, same as every existing one). The existing 525-test Python
  suite was re-run as a sanity check (unchanged — no `.py` files were
  touched) rather than skipped, per this project's own "Tester" role.

## Amendments (2026-10-19, plugin distribution)

The tools, Skills and Subagents are distributed as one Claude Code plugin,
without changing the development layout of the repository.

- **The repo is its own plugin marketplace.** `.claude-plugin/marketplace.json`
  at the repo root lists a single plugin, `architecture-tools`, with
  `"source": "./architecture"`; `architecture/.claude-plugin/plugin.json` is
  that plugin's manifest. Users install with
  `/plugin marketplace add <git-url-or-path>` and
  `/plugin install architecture-tools@ai-architecture-tools`. Rejected:
  a separate distribution repo or a build step copying files into a
  `dist/` tree — both add a second source of truth for no gain, since the
  existing directories already match the plugin component formats.
- **`architecture/` is the plugin root**, so `scripts/` (and, harmlessly,
  `docs/`) ship together with the Skills and Subagents that call them.
  `plugin.json` points at the existing directories via custom paths:
  `"skills": "./skills/"` (adds to the default scan). **`architecture/subagents/`
  was renamed to `architecture/agents/`**, the plugin format's default
  directory: a custom `agents` key accepts only an explicit list of `.md`
  files (no directory), which would have meant a hand-maintained list per
  new Subagent. With the default directory, `plugin.json` sets no `agents`
  key at all (`tests/test_plugin.py` enforces that — the key would
  *replace* the default scan). Subagent names come from frontmatter and are
  unaffected. The design documents stay in `architecture/docs/subagents/`:
  "Subagent" remains the concept name; only the shipped directory follows
  the plugin convention.
- **CLIs reach `PATH` through `architecture/bin/`**: one POSIX `sh` wrapper per
  `scripts/<tool>.py` (`exec python3 .../scripts/<tool>.py "$@"`, resolving
  its own location via `readlink -f`). Claude Code puts an enabled plugin's
  `bin/` on the Bash tool's `PATH`, so the Skills' CLI contract is just the
  bare command name. The former fallback in every `SKILL.md`
  (`python3 <repo>/architecture/scripts/<tool>.py`) was removed — it
  pointed into a repository checkout a plugin user doesn't have. Outside
  Claude Code, a user can put `architecture/bin` on their own `PATH`.
  Stdlib-only Python (`architecture/scripts/CLAUDE.md`, "Tech-Stack") is what
  makes this zero-install beyond `python3`. Known limitation: claude.ai/Cowork
  do not install plugins with a top-level `bin/` — Claude Code only.
- **Skills are referenced by bare name.** Installed, they are namespaced
  (`architecture-tools:rulectl-author-cli`), but the Skill tool resolves the
  bare name too (verified with Claude Code 2.1.303), so Subagents keep
  naming their Skill without the plugin prefix and stay independent of the
  plugin name.
- **The plugin is disabled inside this repository** via
  `.claude/settings.json` (`enabledPlugins`), enforcing the root `CLAUDE.md`
  rule that the tools must not be used for work on this repo even when a
  developer has installed the plugin at user scope. Development testing
  loads the working tree explicitly: `claude --plugin-dir ./architecture`.
- **"Full spec: `architecture/docs/...`" lines in Skills/Subagents stay** —
  they are developer pointers into this repository, not runtime
  instructions; in an installed plugin they resolve relative to the plugin
  copy only by accident and are not relied upon.
- **No pip/`pyproject.toml` packaging for now.** It would require renaming
  the generic top-level package `lib` (it would collide in site-packages);
  deferred until there is a concrete need to use the CLIs outside Claude
  Code beyond putting `bin/` on `PATH`.
- **Releasing**: bump `version` in `plugin.json` (semver, checked by
  `tests/test_plugin.py`); `claude plugin validate .` must pass;
  optionally tag with `claude plugin tag`.

## Amendments (2026-10-19, taskctl-author/taskctl-worker implementation)

A `/grilling` pass turning `design-taskctl-author.md`/`design-taskctl-worker.md`
into the actual Subagent files (`architecture/agents/taskctl-{author,worker}.md`)
surfaced gaps the design left open; all now resolved in the design documents
themselves:

- **Shrink confirmation is two-pass.** The design said "wait for one
  explicit confirmation", which a Subagent can't do — it runs to completion
  and returns a report. Pass 1 deletes nothing and reports exact IDs as
  deferred-awaiting-deletion-confirmation; a re-invocation confirming those
  IDs deletes only those that still match. A blanket pre-authorization in
  the first prompt ("delete without asking") explicitly does **not**
  count — the person must confirm the concrete list they haven't seen yet.
  Rejected: accepting pre-authorization (skips exactly what the gate is
  for, on the one write with no undo).
- **Phase-less stores**: a fresh store always gets Phases; an existing
  phase-less store stays flat (never mixed, `taskctl`'s depth rule).
- **Creation order is execution order** — made explicit for the author,
  since the worker follows `next`'s global sequence and can't skip ahead.
  `reorder` only to place a new Task before an existing *open* one.
- **Description content standard**: goal, concrete work with every
  applicable prompt constraint repeated per Task, and a checkable "done
  when" criterion — the worker sees only the Task.
- **Worker tools**: a fixed list without `Agent` and MCP tools; a Task
  needing either is a `[B]`. Rejected: inheriting every tool.
- **Worker outward-facing actions** (push, publish, deploy, send,
  destructive operations outside the working area) only when the Task or
  prompt explicitly asks; otherwise `[R]` with the pending action as reason.
  Local commits likewise only on request.
- **`rulectl tasklist` exports are not worked by `taskctl-worker`** — this
  closes a gap in the worker's trust argument: the export copies Rule text
  verbatim (`lib/tasklist.py`), so the "Description is the author's own
  synthesis" guarantee doesn't hold, and those Tasks are compliance checks
  for `rulectl-checker` anyway. Recognized heuristically by
  `assignee-type` `agent`/`tool`; set `[B]` without claiming.
  `VISION.md` no longer lists `rulectl tasklist` as a worker input.
- **Worker report** specified (it wasn't): per Task status before → after,
  what was done, evidence for the outcome, any `info-review` change; then
  stop reason and end-of-run verification.

Acceptance: manual smoke tests in a scratch store via
`claude -p --plugin-dir ./architecture --agent architecture-tools:<agent>` —
author create / extend + shrink pass 1 (blanket pre-authorization correctly
refused) / pass 2 (confirmed ID deleted); worker single Task, resume of a
`[~]` Task, loop to `all_done`, a `review=user` Task ending `[R]` (and
blocking the next run), and a rulectl-style Task set `[B]` unworked. All
passed.

- **Outward-facing Tasks get `review=user`, and it gates the action, not
  just the result** (follow-up to the smoke test, where the author created
  a "publish to PyPI" Task unflagged and the worker's explicit-request rule
  would have let it publish). The author always sets `review=user` on a
  Task whose work includes an outward/irreversible action, in its own Task
  separate from local preparation — an explicit exception to "review is
  never inferred from subject matter", which the prompt can't waive. On
  such a Task the worker stops at `[R]` "pending: needs user approval"
  *before* the action and performs it only after a `[R]`→`[~]` History
  entry approving it, then sets `[R]` again for the final check. No new
  `taskctl` status or command: rework (`[R]`→`[~]`) already exists.
  Rejected: plain `review=user` without the gate — the review would only
  come after the irreversible action. The invocation prompt can't stand in
  for the History approval (it may come from a calling agent).

## Amendments (2026-10-19, local-first: one gated path for remote actions)

Follow-up to the outward-facing gate above, which still enumerated actions
(publish, push, deploy, ...) and let an explicit request in the Task text
or invocation prompt suffice outside `review=user` Tasks. Triggering a
GitHub pipeline or changing a JIRA item fell through that list. Since
`taskctl` is mainly used to guide an AI through progressive **local**
changes and remote changes are the absolute exception:

- **"Local" is defined positively; everything else is remote** — judged by
  effect, not tool: local file edits, local git (commit on request),
  local builds/tests/scripts, dependencies into the working area are
  free; read-only remote access (GET, `git fetch`, `WebFetch`) is free;
  anything changing state outside the working area and local repository
  (and irreversible local operations on things the Task didn't create)
  is remote. When in doubt, remote. Rejected: extending the enumeration —
  it always misses one.
- **One single path for a remote action**: a `review=user` Task, local
  part done, `[R]` "pending: needs user approval", user's approving
  `[R]`→`[~]` History entry, action, `[R]` again. The worker raises
  `review` to `user` itself on any Task lacking it (hand-written, or
  `none`/`subagent`). The Task text or invocation prompt no longer
  suffice on their own — that path is removed.
- **The author plans remote-action Tasks only when the prompt explicitly
  asks for that action**; a source mentioning it is not enough. Otherwise
  the plan ends at the local result and the report says what was left
  out.
- **Honest about strength**: the classification and the History check are
  model judgment, not a mechanism. The hard guarantee belongs to the
  environment — operating guidance (design-taskctl-worker.md, "Operating
  guidance"; README) is to run unattended loops in Claude Code's sandbox
  with outbound writes restricted and without remote credentials. A
  per-Subagent command blocklist (tool config or hook) is noted as a
  possible later backstop, not built: unverified whether Claude Code
  supports it per Subagent, a plugin-wide hook would affect the user's
  normal sessions, and a pattern list never catches everything.

## Amendments (2026-10-19, specctl/adrctl fixes from integrating the specctl Subagents)

Merging `main` (plugin layout) into the specctl-author/specctl-adr-author
branch and re-running both its recipe verification and new end-to-end
smoke tests of the two Subagents surfaced three pre-existing defects —
none caused by the merge (no `.py` file changed in it) — plus several
documentation gaps:

- **adrctl re-pointed a Section at a superseded ADR (bug, fixed).**
  `set-status` is a `spec-ref` propagation trigger, so the documented
  supersede flow's last step (`set-status <old> superseded`) wrote the
  *old* ADR's ID back into the Section — silently, contradicting
  design-specctl.md ("superseding updates a Section's `adr`" to the
  superseding ADR). Fix: no propagation while the ADR sits in a
  no-longer-governing status (`superseded`/`deprecated`/`rejected`).
  Rejected: propagating only on entering `accepted` — that would also stop
  `add`/`info-spec-ref` of a `proposed` ADR from linking, which the
  existing spec and tests rely on. Regression test:
  `test_superseding_keeps_section_on_new_adr` (`tests/test_adrctl.py`).
- **specctl rejected level skipping the spec allows (code brought to
  spec).** design-specctl.md, "Metagroups", allowed "a Chapter may hold
  Points directly", but `level` was derived from the path length. `level`
  is now stored on `SpecSection`; a Section only has to be deeper than its
  parent. The spec's own next sentence ("adding a `#####` heading requires
  its enclosing `####`/`###`/`##` objects to already exist") contradicted
  that literally and is now worded as "named ancestors must exist".
  Two points the spec left open, decided here: **only a Part sits at the
  root** (every branch hangs off a `##`; a root-level `###` has no anchor
  for its Object Type and reads as a malformed document), and **skipped
  levels contribute `__` to the Object Type**, keeping it level-aligned
  (width still encodes the level; unskipped documents keep their exact
  types). A moved subtree keeps its internal level gaps (uniform shift).
  A second recipe re-check then found the one layout Markdown can't
  express: a deeper child *after* a shallower sibling under the same
  parent (a Point after a Section under one Chapter) — single-file mode
  silently re-parented it on the next read. Decided: **sibling levels
  never increase in document order**, enforced by `add`, `move-to-<level>`
  and `reorder` on the in-memory result before writing (both modes, so the
  model stays mode-independent). Rejected: auto-placing the Section before
  its shallower siblings — keeps more layouts reachable, but breaks
  "always lands as the last child" and needs renumbering; not worth it for
  an edge case.
- **`--json show-metagroups` printed Python tuples (bug, fixed)** in the
  shared `lib/cliapp.py` — affecting taskctl/questctl/rulectl/adrctl,
  whose author Skills all say to parse it as JSON. Now a JSON array of
  paths (`[["001-Spec"], ["001-Spec", "001-Core"]]`, the same shape as
  specctl's `path`); the plain output prints one `/`-joined path per line.
- **Documentation**: specctl takes only the 6-character `id`, not the
  Signature (both specctl Skills now say so — the smoke test's first move
  attempt failed on exactly this); `info-spec-ref` leaves the previously
  referenced Section's `adr` unchanged (adrctl-author-cli); two error
  texts and `adr` null-vs-absent wording (specctl-editor-cli);
  `design-specctl-author-cli.md` no longer lists the nonexistent specctl
  `show-metagroups`; `specctl-adr-author` now documents the Domain gate it
  inherits from `adrctl-author-cli` and its
  **deferred-awaiting-domain-decision** outcome (the smoke test hit that
  gate; the agent improvised a sensible report, but neither its design doc
  nor its agent file named it).
- **Skill wording from the re-check**: mutating specctl commands accept
  only the 6-character `id` (`show` also takes the Signature); usage errors
  exit `2` (argparse), not only `0`/`1`; a nonexistent `--adr` fails with
  "adr '<id>': no object with ID", and `--adr` on a draft Section is
  ignored.
- **Clarified, not a defect**: `specctl set-description` writes no History
  entry — by design (design-specctl.md, "History": content changes are not
  logged; from `stable` on the trail lives in the ADR).

## Amendments (2026-10-20, agent workflow consistency)

Question processors select one read-only `next-all` snapshot in both modes.
Sequential processing claims only answerable Questions individually; no-match
Questions stay open without preventing progress to later snapshot IDs.
Batch claiming remains explicit and scoped. Runs must be serialized per root.

Task Metainfo gains optional `origin`, distinct from source documents and
assignment. Rule exports stamp/refresh `rulectl:<rule-id>`; assignment alone
cannot distinguish an exported compliance check from ordinary agent work.
Legacy exports need re-export before worker use. Review requirements are
preserved unless the user explicitly instructs otherwise; remote-action gates
remain mandatory.

ADR creation is per coherent topic for both promotion and revision. New
records document partial replacements; an old ADR remains accepted until no
Section references it. Verify the topic before retiring old ADRs; a failed
reference query never counts as an empty one. The single-valued
`superseded-by` points at the final replacement; earlier partial replacements
remain recorded in their respective ADRs. These are agent-level lifecycle
rules; general manual CLI status operations remain available.

## Amendments (2026-10-20, compact runtime instructions)

Agent/Skill runtime definitions are editorially compacted with no intended
behavior change. Each role remains independently usable through its own
named Skill(s); Author and Worker are normally separate invocations and
never need each other's instructions. No common runtime reference or new
loading mechanism is introduced. The two-Skill specctl-adr-author remains
the existing explicit exception to one-Skill pairing.

Agents own inputs/trust, semantic workflow, decisions, approval boundaries
and report requirements. Skills own the full allowed CLI surface, command
recipes, technical transitions, errors and persisted-state verification.
Critical boundaries can be repeated at both levels where needed for clarity.
Descriptions route to roles; rationale, implementation history, examples and
future work remain in design documents. Existing Full-spec pointers remain
developer references, not runtime dependencies.

The rule comparison in `architecture/docs/optimizing-rule-comparison.md`
records retained invariants and their new locations against commit e476614.
Validation uses static comparison plus the existing CLI/plugin tests; it
cannot establish unchanged model behavior. Actual Agent evals, shared
runtime-reference architecture and potential rule changes are explicitly
tracked in `architecture/docs/backlog-optimizing.md`, outside this editorial pass.

## Amendments (2026-10-20, readability review of compact instructions)

The compact definitions are revised for clarity rather than further shortening.
Descriptions explicitly state use cases and neighboring role exclusions.
Decision-relevant reasons remain in the runtime text, particularly for claim
timing, provenance, approval, separate verification and partial ADR replacement.
These are explanations of the existing contracts, not new exceptions.

The repeated Runtime allocation notes are removed from the role designs.
Their common ownership and validation policy is maintained once in
[agent-skill-guidelines.md](../agent-skill-guidelines.md). Agent workflow details
remain in their designs and the workflow-consistency amendment above, rather
than the additional implementation section in VISION.md. scripts/CLAUDE.md
keeps only the origin implementation note from that added section.

The backlog now lives at `architecture/docs/backlog-optimizing.md`.
[The comparative eval plan](../evals/agent-instruction-comparison.md) defines
routing, skill-loading, unanswered-Question, review/provenance and ADR scenarios.
It has not been executed; CLI tests and static review do not establish unchanged
model behavior. *(Since executed for E1 and E3–E6 without observed regression —
see [the results](../evals/results-2026-10-20.md); the failure scenarios remain open in
`architecture/docs/backlog-optimizing.md`, B4.)* Further substantial compaction waits for those comparisons.

## Amendments (2026-10-21, CI and plugin versioning)

GitHub Actions runs both test suites on every push and pull request
(`.github/workflows/tests.yml`), on GitHub-hosted `ubuntu-latest` runners only
(free for this public repository, no self-hosted runner). The matrix covers
Python 3.10 — the guaranteed minimum of every target environment, so the
3.10-only-stdlib constraint is now checked rather than assumed — and 3.13, the
development version. The CLI wrappers in `architecture/bin/` deliberately do
not check the interpreter version at runtime: an older Python is out of scope
and failing there is accepted.

The plugin version had stayed at `0.1.0` since distribution began despite
substantial Agent and Skill changes; it is now `0.2.0`. To keep the existing
"bump `version` before a release" rule from being forgotten again, the
`plugin-version` job fails a pull request that changes `architecture/agents`,
`architecture/skills` or `architecture/bin` without changing `version`.
Changes under `scripts/` alone are not covered, as they are frequently
internal refactorings without user-visible effect.

## Amendments (2026-10-21, cross-tool CLI contract tests)

specctl's own CLI sits beside `lib/cliapp.py` by design, so the shared CLI
contract was only kept consistent by hand. `scripts/tests/test_cli_contract.py`
now checks it once for all five tools: `--help` exits `0` and names `--root`
and `--json`; a missing `--root` or an unknown subcommand is an argparse usage
error (exit `2`, already accepted in "Amendments (2026-10-19, specctl/adrctl
fixes ...)"); a runtime error exits `1` with the message on stderr and nothing
on stdout, with or without `--json`; `--json` output is valid JSON, human
output is not; all tools share one `--root` without seeing each other's
objects. Merging specctl into the generic engine remains rejected — the tests
replace the manual consistency rule, not the separate implementation.

`scripts/CLAUDE.md` now describes only the current implementation state,
conventions and open points; the change history it had accumulated lives
here. It no longer records test counts, which went stale with every change.
