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
from lib.store import NoWorkAvailable, Store
from lib.taskctl_spec import DONE, build_spec


def _handle_annotate(store: Store, args: argparse.Namespace) -> ObjectRecord:
    return store.annotate(args.id, args.message)


def _handle_next(store: Store, _args: argparse.Namespace) -> ObjectRecord:
    open_records = [r for r in store.list_all() if r.status != DONE]
    if not open_records:
        # design-decisions.md, "Amendments (2026-08-25, taskctl NoWorkAvailable
        # + taskctl-author-cli/taskctl-worker-cli design)": taskctl has exactly
        # one "nothing to hand out" case (everything is [X], or the store is
        # empty), unlike questctl's three -- but a looping taskctl-worker run
        # still needs to tell it apart from a genuine error under --json.
        raise NoWorkAvailable("all_done", "no open tasks")
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
