"""rulectl -> taskctl: exports rulectl's active Rules into taskctl as Tasks
(design-rulectl.md, "Operations": tasklist). rulectl.py calls `run()` from
its own `tasklist` extra_handler; it never imports taskctl.py as a whole
(architecture/scripts/CLAUDE.md) -- it builds a taskctl-shaped Store via
lib/taskctl_spec.py instead, the same pattern lib/adr_lookup.py and
lib/spec_link.py already use for their own cross-store directions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from lib import abbrev
from lib.model import ObjectRecord
from lib.store import Store, StoreError
from lib.taskctl_spec import OPEN, build_spec as build_taskctl_spec

PHASE_SEPARATOR = "::"
ASSIGNEE_TYPE_AGENT = "agent"
ASSIGNEE_TYPE_TOOL = "tool"

_ACTIVE_STATUS = "active"


class TasklistError(Exception):
    pass


def run(
    shared_root: Path, rulectl_store: Store, *, under: Optional[list[str]] = None
) -> list[ObjectRecord]:
    """Export every active Rule in `rulectl_store` into the taskctl store
    resolved within `shared_root` -- the *unresolved* --root the triggering
    rulectl invocation received (args.root), not rulectl_store.root, so
    taskctl's Store independently resolves its own target, the same
    requirement lib/spec_link.py's `propagate()` documents for the
    adrctl -> specctl direction. `under`, if given, is a metagroup path
    already resolved against `rulectl_store` (design.md: '--<metagroup-type>
    <value>' semantics), restricting export to that subtree."""
    taskctl_store = Store(spec=build_taskctl_spec(), root=shared_root)

    active_rules = [r for r in rulectl_store.list_all() if r.status == _ACTIVE_STATUS]
    if under is not None:
        active_rules = [
            r for r in active_rules
            if list(r.metagroup_levels[: len(under)]) == under
        ]

    phase_cache: dict[tuple[str, ...], list[str]] = {}
    results: list[ObjectRecord] = []
    for rule in active_rules:
        phase_path = phase_cache.get(rule.metagroup_levels)
        if phase_path is None:
            phase_path = _resolve_or_create_phase(taskctl_store, rule.metagroup_levels)
            phase_cache[rule.metagroup_levels] = phase_path
        results.append(_export_rule(taskctl_store, rule, phase_path))

    results.sort(key=lambda r: (r.metagroup_levels, r.number))
    return results


def _flatten_phase_name(metagroup_levels: tuple[str, ...]) -> str:
    """Rulectl's 3-level Language/Context/Category path, flattened into the
    single Phase Name taskctl's one-level Metagroup uses. '/' is
    deliberately not used as the join character -- it is reserved elsewhere
    as the CLI's metagroup path-segment separator (lib/cliapp.py's
    `_metagroup_path_for_add`, `group-<type>`, `list`'s metagroup filter all
    split a metagroup value on '/'); a '/'-containing Phase Name would break
    any later `taskctl ... --phase "<name>"` resolution against taskctl's
    single-level hierarchy."""
    return PHASE_SEPARATOR.join(abbrev.strip_sort_prefix(segment) for segment in metagroup_levels)


def _find_phase(taskctl_store: Store, flattened_name: str) -> Optional[list[str]]:
    for path in taskctl_store.metagroup_paths():
        if abbrev.strip_sort_prefix(path[0]) == flattened_name:
            return [path[0]]
    return None


def _resolve_or_create_phase(taskctl_store: Store, rule_path: tuple[str, ...]) -> list[str]:
    flattened_name = _flatten_phase_name(rule_path)
    found = _find_phase(taskctl_store, flattened_name)
    if found is not None:
        return found
    taskctl_store.add_metagroup_path([flattened_name])
    found = _find_phase(taskctl_store, flattened_name)
    if found is None:
        raise TasklistError(f"internal error: Phase {flattened_name!r} missing right after creation")
    return found


def _map_fields(rule: ObjectRecord) -> tuple[str, str, str]:
    """Field mapping for a Rule's `checkable` metainfo (design-rulectl.md,
    "Operations"): `llm` -> the agent works the Task directly, using the
    Rule's own text; anything else -> an external tool checks it, and the
    Task just points the agent at running that tool."""
    checkable = rule.metainfo_value("checkable") or ""
    if checkable == "llm":
        return ASSIGNEE_TYPE_AGENT, "", _agent_description(rule)
    tool = rule.metainfo_value("tool") or checkable
    tool_rule = rule.metainfo_value("tool-rule") or ""
    return ASSIGNEE_TYPE_TOOL, tool, _tool_description(rule, tool, tool_rule)


def _agent_description(rule: ObjectRecord) -> str:
    parts = [rule.content.get("Description", "").strip()]
    procedure = rule.content.get("Procedure", "").strip()
    if procedure:
        parts.append(f"### Procedure\n\n{procedure}")
    parts.append(f"_(source: rulectl rule {rule.signature})_")
    return "\n\n".join(part for part in parts if part)


def _tool_description(rule: ObjectRecord, tool: str, tool_rule: str) -> str:
    return f"Run `{tool}` to verify rule `{tool_rule}` (source: rulectl rule {rule.signature})."


def _export_rule(taskctl_store: Store, rule: ObjectRecord, phase_path: list[str]) -> ObjectRecord:
    assignee_type, assignee_name, description = _map_fields(rule)
    metainfo = {"assignee-type": assignee_type, "assignee-name": assignee_name}

    try:
        existing = taskctl_store.get(rule.object_id)
    except StoreError:
        existing = None

    if existing is None:
        return taskctl_store.add(
            metagroup_path=phase_path, name=rule.name, description=description,
            metainfo=metainfo, object_id=rule.object_id,
        )

    # Idempotent re-export: only touch fields that actually changed, so a
    # rerun against an unchanged Rule doesn't add redundant `M` History
    # noise -- the `T` annotate entry below is always added regardless, so
    # a re-export is never silently invisible even when nothing else moved.
    if list(existing.metagroup_levels) != phase_path:
        taskctl_store.set_metagroup(rule.object_id, phase_path)
    if existing.content.get("Description", "") != description:
        taskctl_store.set_content(rule.object_id, "Description", description)
    for metainfo_type, value in metainfo.items():
        if existing.metainfo_value(metainfo_type) != value:
            taskctl_store.set_metainfo(rule.object_id, metainfo_type, value)
    if existing.status != OPEN:
        taskctl_store.set_status(
            rule.object_id, OPEN, force=True,
            message=f"reset to open by rulectl tasklist re-export ({rule.object_id})",
        )
    return taskctl_store.annotate(
        rule.object_id, f"re-exported from rulectl rule {rule.signature}",
    )
