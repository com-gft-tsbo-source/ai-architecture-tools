"""taskctl's ToolSpec, extracted from taskctl.py into a shared lib module so
lib/tasklist.py (rulectl -> taskctl export) can construct a lib/store.py
Store against the taskctl store without taskctl.py itself needing to be
imported (architecture/scripts/CLAUDE.md: "a CLI script never imports
another CLI script as a whole"). taskctl.py imports build_spec()/DONE from
here instead of defining them locally -- single source of truth, no risk of
the two drifting apart.

Carries more than just build_spec(): taskctl's ToolSpec references
validate_transition and object_type_from_phase directly, so those (and the
status-code constants they use) had to move here too -- leaving them in
taskctl.py would make this module import taskctl.py back, circularly.

lib/questctl_spec.py also imports the status constants and
validate_transition from here directly (design-questctl.md, "Status":
"unchanged from taskctl") rather than duplicating them -- the two tools are
the only ones sharing this exact review-gated state machine, so there was
no need for a third, more general module just to hold it.
"""

from __future__ import annotations

from typing import Optional

from lib import abbrev
from lib.guards import APPROVAL_HINT, APPROVAL_REQUIRED, SEQUENCE_BLOCKED, GuardViolation
from lib.model import ObjectRecord
from lib.toolspec import MetagroupLevelSpec, MetainfoSpec, StatusSpec, ToolSpec

OPEN, IN_PROGRESS, REVIEW_USER, REVIEW_SUBAGENT, BLOCKED, DONE = " ", "~", "R", "C", "B", "X"

_REVIEW_STEP = {"none": None, "user": REVIEW_USER, "subagent": REVIEW_SUBAGENT}

GATE_SEQUENTIAL, GATE_NONE = "sequential", "none"

_STATUS_LABEL = {
    OPEN: "open", IN_PROGRESS: "in progress", REVIEW_USER: "review by user",
    REVIEW_SUBAGENT: "review by subagent", BLOCKED: "blocked", DONE: "done",
}


def _forward_path(review: str) -> list[str]:
    step = _REVIEW_STEP.get(review)
    if step is None:
        return [OPEN, IN_PROGRESS, DONE]
    return [OPEN, IN_PROGRESS, step, DONE]


def validate_transition(
    record: ObjectRecord, target: str, *, message: str, force: bool, approval: Optional[str] = None
) -> None:
    current = record.status
    if current == target:
        return

    if current == REVIEW_USER and target == DONE and not (approval or force):
        # design-taskctl.md, "Guards": [R] -> [X] *is* the user's review
        # verdict -- on-path, but never the agent's own call.
        raise GuardViolation(
            APPROVAL_REQUIRED,
            f"{record.object_id}: [R] -> [X] completes a user review -- {APPROVAL_HINT}",
        )

    if target == BLOCKED:
        if current == DONE:
            raise ValueError("cannot block a task that is already done")
        if not message:
            raise ValueError("blocking a task ([B]) requires --message with a reason")
        return

    review = record.metainfo_value("review") or "none"
    path = _forward_path(review)
    non_terminal = path[:-1]

    if current == BLOCKED:
        if target in non_terminal or force:
            return
        raise ValueError(f"cannot unblock into {target!r} without --force")

    if current in (REVIEW_USER, REVIEW_SUBAGENT) and target == IN_PROGRESS:
        return  # rework

    if current in path and target in path and path.index(target) == path.index(current) + 1:
        return  # normal forward step

    if force:
        return
    raise ValueError(f"invalid status transition {current!r} -> {target!r} for review={review!r} (use --force)")


def priority_key(record: ObjectRecord) -> tuple:
    """design-taskctl.md, "Prioritization": sorted Phase, then number."""
    return (record.metagroup_levels, record.number)


def is_gating(record: ObjectRecord) -> bool:
    """design-taskctl.md, "Metainfo": a Task with gate=none (e.g. a
    `rulectl tasklist` compliance check) neither blocks later Tasks nor is
    held back by earlier ones."""
    return (record.metainfo_value("gate") or GATE_SEQUENTIAL) != GATE_NONE


def first_blocker(records: list[ObjectRecord], record: ObjectRecord) -> Optional[ObjectRecord]:
    """The earliest gating, not-[X] Task ahead of `record` in priority order."""
    key = priority_key(record)
    ahead = [
        r for r in records
        if r.object_id != record.object_id and r.status != DONE and is_gating(r)
        and priority_key(r) < key
    ]
    return min(ahead, key=priority_key, default=None)


def sequence_guard(records: list[ObjectRecord], record: ObjectRecord, target: str) -> None:
    """design-taskctl.md, "Sequential Processing"/"Guards": a Task may not
    move into [~]/[R]/[C]/[X] while an earlier gating Task is unresolved --
    blocking ([B]) or reopening ([ ]) it stays free."""
    if target in (OPEN, BLOCKED) or not is_gating(record):
        return
    blocker = first_blocker(records, record)
    if blocker is None:
        return
    raise GuardViolation(
        SEQUENCE_BLOCKED,
        f"{record.object_id}: earlier task {blocker.object_id} ({blocker.signature}) is "
        f"[{blocker.status}] ({_STATUS_LABEL[blocker.status]}) -- resolve it first, or {APPROVAL_HINT}",
        blocking_task=blocker.object_id,
    )


def review_metainfo_guard(record: ObjectRecord, metainfo_type: str, value: str) -> None:
    """design-taskctl.md/design-questctl.md, "Guards": `review` may not
    change while the object sits in review, nor be lowered from `user` --
    either would let an agent route around a user review."""
    if metainfo_type != "review":
        return
    old = record.metainfo_value("review") or "none"
    if old == value:
        return
    if record.status in (REVIEW_USER, REVIEW_SUBAGENT):
        raise GuardViolation(
            APPROVAL_REQUIRED,
            f"{record.object_id}: review cannot change while in [{record.status}] -- {APPROVAL_HINT}",
        )
    if old == "user":
        raise GuardViolation(
            APPROVAL_REQUIRED,
            f"{record.object_id}: lowering review from 'user' to {value!r} removes a user review -- "
            f"{APPROVAL_HINT}",
        )


def taskctl_metainfo_guard(record: ObjectRecord, metainfo_type: str, value: str) -> None:
    review_metainfo_guard(record, metainfo_type, value)
    if metainfo_type == "gate" and (record.metainfo_value("gate") or GATE_SEQUENTIAL) != value:
        # Fixed at creation (rulectl tasklist sets gate=none): flipping it
        # afterwards would switch the sequence guard off for that Task.
        raise GuardViolation(
            APPROVAL_REQUIRED,
            f"{record.object_id}: gate is fixed at creation -- {APPROVAL_HINT}",
        )


def object_type_from_phase(level_names: list[str]) -> str:
    """taskctl's exception to the generic Object Type scheme (design-taskctl.md,
    "Object Type"): the unpadded Phase number, not a letter abbreviation.
    A phase-less (depth-0) store has no Phase number to derive from, so it
    falls back to the general 0-level derivation instead (design.md,
    "Object Type"): every Task there derives to "______"."""
    if not level_names:
        return abbrev.derive_object_type([], {})
    phase_name = level_names[-1]
    prefix = phase_name.split("-", 1)[0]
    return str(int(prefix))


def build_spec() -> ToolSpec:
    return ToolSpec(
        name="taskctl",
        metagroup_levels=(MetagroupLevelSpec(type="Phase"),),
        metainfo=(
            MetainfoSpec(type="review", choices=("none", "user", "subagent")),
            MetainfoSpec(type="assignee-type"),
            MetainfoSpec(type="assignee-name"),
            # design-taskctl.md, "Metainfo": traceability back to the
            # document a Task was derived from -- design-decisions.md,
            # "Amendments (2026-08-25, taskctl-author/taskctl-worker Subagent
            # design)": the same gap questctl's own `source` field (below,
            # via lib/questctl_spec.py) was added to close, now that
            # taskctl-author routinely bulk-authors Tasks from a set of
            # source documents rather than Tasks always being hand-created.
            MetainfoSpec(type="source"),
            MetainfoSpec(type="origin"),
            MetainfoSpec(type="gate", choices=(GATE_SEQUENTIAL, GATE_NONE)),
        ),
        status=StatusSpec(
            codes=(OPEN, IN_PROGRESS, REVIEW_USER, REVIEW_SUBAGENT, BLOCKED, DONE),
            initial=OPEN,
            transition_validator=validate_transition,
        ),
        user_content_blocks=("Description",),
        root_name="tasks",
        default_mode="directory",
        object_type_fn=object_type_from_phase,
        variable_depth=True,
        sequence_guard=sequence_guard,
        metainfo_guard=taskctl_metainfo_guard,
    )
