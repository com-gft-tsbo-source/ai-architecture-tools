#!/usr/bin/env python3
"""questctl -- CLI for the questctl object type (design-questctl.md).

Objects are Questions, grouped by an optional, uniform-per-store Group/
Subgroup metagroup (design.md, "Metagroups": variable_depth). Status codes
and their transition machine are shared verbatim with taskctl
(lib/taskctl_spec.py); what's questctl-specific here is `answer` (a
bespoke, T-logged content field -- design-questctl.md, "Operations") and
`next`/`next-all`'s parallel-processing gate (design-questctl.md,
"Parallel Processing").
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from lib import cliapp
from lib.model import ObjectRecord
from lib.questctl_spec import DONE, IN_PROGRESS, OPEN, build_spec
from lib.store import NoWorkAvailable, Store


def _handle_annotate(store: Store, args: argparse.Namespace) -> ObjectRecord:
    return store.annotate(args.id, args.message)


def _handle_answer(store: Store, args: argparse.Namespace) -> ObjectRecord:
    return store.annotate_content(args.id, "Answer", args.text, args.message)


def _no_work_reason(records: list[ObjectRecord]) -> Optional[tuple[str, str]]:
    """design-questctl.md, "Parallel Processing": while any Question is
    `[~]`, nothing new is handed out (in_progress) -- checked before
    anything else, so it also gates a store that additionally still has
    `[ ]` Questions sitting around. Failing that: every Question `[X]`
    (also true, vacuously, of an empty store) is all_answered; anything
    else left over (no `[~]`, no `[ ]`, but not all `[X]`) must be a mix
    including `[R]`/`[C]`/`[B]` -- awaiting_interaction. None means there
    *is* open work: at least one `[ ]` Question, with no `[~]` blocking it."""
    if any(r.status == IN_PROGRESS for r in records):
        return ("in_progress", "a Question is already in progress -- no new work will be started")
    if any(r.status == OPEN for r in records):
        return None
    if all(r.status == DONE for r in records):
        return ("all_answered", "every Question is answered -- nothing left to do")
    return (
        "awaiting_interaction",
        "remaining Questions need review or are blocked -- nothing available to start right now",
    )


def _open_sorted(records: list[ObjectRecord]) -> list[ObjectRecord]:
    open_records = [r for r in records if r.status == OPEN]
    open_records.sort(key=lambda r: (r.metagroup_levels, r.number))
    return open_records


def _handle_next(store: Store, _args: argparse.Namespace) -> ObjectRecord:
    records = store.list_all()
    reason = _no_work_reason(records)
    if reason is not None:
        raise NoWorkAvailable(*reason)
    return _open_sorted(records)[0]


def _handle_next_all(store: Store, _args: argparse.Namespace) -> list[ObjectRecord]:
    records = store.list_all()
    reason = _no_work_reason(records)
    if reason is not None:
        raise NoWorkAvailable(*reason)
    return _open_sorted(records)


def _configure_parser(parser: argparse.ArgumentParser, subparsers) -> None:
    annotate_parser = subparsers.add_parser("annotate", help="Log progress notes on a Question")
    annotate_parser.add_argument("id")
    annotate_parser.add_argument("--message", required=True)

    answer_parser = subparsers.add_parser(
        "answer", help="Record or revise the Answer to a Question (replaces the Answer section)"
    )
    answer_parser.add_argument("id")
    answer_parser.add_argument("text", help="Markdown answer text, replacing the Answer section")
    answer_parser.add_argument(
        "--message", required=True,
        help="Short log note for the T History entry -- the only remaining trace of why the "
             "answer changed, since the previous text is gone once overwritten",
    )

    subparsers.add_parser(
        "next", help="Show the next open Question (or report why none is available)"
    )
    subparsers.add_parser(
        "next-all", help="List every open Question, grouped by metagroup path (or report why none is available)"
    )


def main(argv: list[str]) -> int:
    spec = build_spec()
    extra_handlers = {
        "annotate": _handle_annotate,
        "answer": _handle_answer,
        "next": _handle_next,
        "next-all": _handle_next_all,
    }
    return cliapp.main(spec, argv, extra_handlers=extra_handlers, configure_parser=_configure_parser)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
