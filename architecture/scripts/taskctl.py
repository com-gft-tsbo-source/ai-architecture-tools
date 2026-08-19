#!/usr/bin/env python3
"""taskctl -- CLI for the taskctl object type (design-taskctl.md).

Objects are tasks, grouped by a single-level Phase metagroup. Status codes
are stored bracket-free (" ", "~", "R", "C", "B", "X") -- see
lib/toolspec.py's StatusSpec docstring for why -- but are always displayed
in the familiar "[ ]"-bracketed form.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib import cliapp
from lib.model import ObjectRecord
from lib.store import Store, StoreError
from lib.toolspec import MetagroupLevelSpec, MetainfoSpec, StatusSpec, ToolSpec

OPEN, IN_PROGRESS, REVIEW_USER, REVIEW_SUBAGENT, BLOCKED, DONE = " ", "~", "R", "C", "B", "X"

_REVIEW_STEP = {"none": None, "user": REVIEW_USER, "subagent": REVIEW_SUBAGENT}


def _forward_path(review: str) -> list[str]:
    step = _REVIEW_STEP.get(review)
    if step is None:
        return [OPEN, IN_PROGRESS, DONE]
    return [OPEN, IN_PROGRESS, step, DONE]


def validate_transition(record: ObjectRecord, target: str, *, message: str, force: bool) -> None:
    current = record.status
    if current == target:
        return

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


def object_type_from_phase(level_names: list[str]) -> str:
    """taskctl's exception to the generic Object Type scheme (design-taskctl.md,
    "Object Type"): the unpadded Phase number, not a letter abbreviation."""
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
        ),
        status=StatusSpec(
            codes=(OPEN, IN_PROGRESS, REVIEW_USER, REVIEW_SUBAGENT, BLOCKED, DONE),
            initial=OPEN,
            transition_validator=validate_transition,
        ),
        user_content_blocks=("Description",),
        object_type_fn=object_type_from_phase,
    )


def _handle_annotate(store: Store, args: argparse.Namespace) -> ObjectRecord:
    return store.annotate(args.id, args.message)


def _handle_next(store: Store, _args: argparse.Namespace) -> ObjectRecord:
    open_records = [r for r in store.list_all() if r.status != DONE]
    if not open_records:
        raise StoreError("no open tasks")
    open_records.sort(key=lambda r: (r.metagroup_levels, r.number))
    return open_records[0]


def _configure_parser(parser: argparse.ArgumentParser, subparsers) -> None:
    annotate_parser = subparsers.add_parser("annotate", help="Log execution progress on a task")
    annotate_parser.add_argument("id")
    annotate_parser.add_argument("--message", required=True)
    subparsers.add_parser("next", help="Show the next open task (by Phase, then task number)")


def main(argv: list[str]) -> int:
    spec = build_spec()
    extra_handlers = {"annotate": _handle_annotate, "next": _handle_next}
    return cliapp.main(spec, argv, extra_handlers=extra_handlers, configure_parser=_configure_parser)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
