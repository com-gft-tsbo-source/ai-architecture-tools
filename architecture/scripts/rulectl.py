#!/usr/bin/env python3
"""rulectl -- CLI for the rulectl object type (design-rulectl.md).

Objects are checks applicable to a code or data base, classified by a
3-level Language/Context/Category metagroup. No transition validator: every
manual status change is accepted (design.md/design-decisions.md, "no
automatic transitions" -- rulectl deliberately does not restrict which
manual transitions are allowed, unlike taskctl).

`tasklist` exports every active Rule into taskctl as a Task, grouped into
one Phase per unique (Language, Context, Category) path (design-rulectl.md,
"Operations"; lib/tasklist.py does the actual cross-store work, following
the same pattern lib/adr_lookup.py/lib/spec_link.py use elsewhere -- rulectl.py
never imports taskctl.py as a whole, architecture/scripts/CLAUDE.md).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib import cliapp, tasklist
from lib.model import ObjectRecord
from lib.store import Store
from lib.toolspec import MetagroupLevelSpec, MetainfoSpec, StatusSpec, ToolSpec


def build_spec() -> ToolSpec:
    return ToolSpec(
        name="rulectl",
        metagroup_levels=(
            MetagroupLevelSpec(type="Language"),
            MetagroupLevelSpec(type="Context"),
            MetagroupLevelSpec(type="Category"),
        ),
        metainfo=(
            MetainfoSpec(type="source"),
            MetainfoSpec(type="weight"),
            MetainfoSpec(type="tool"),
            MetainfoSpec(type="tool-rule"),
            MetainfoSpec(type="checkable"),
        ),
        status=StatusSpec(codes=("draft", "active", "obsolete"), initial="active"),
        user_content_blocks=("Description", "Procedure"),
        root_name="rules",
        default_mode="directory",
    )


def _tasklist_dest(level_type: str) -> str:
    return f"tasklist__{level_type}"


def _handle_tasklist(spec: ToolSpec, store: Store, args: argparse.Namespace) -> list[ObjectRecord]:
    supplied = [
        (level.type, getattr(args, _tasklist_dest(level.type)))
        for level in spec.metagroup_levels
        if getattr(args, _tasklist_dest(level.type)) is not None
    ]
    if len(supplied) > 1:
        flags = ", ".join(f"--{level.type.lower()}" for level in spec.metagroup_levels)
        raise cliapp.CliError(f"tasklist accepts at most one of [{flags}] as a metagroup filter")
    under = store.resolve_metagroup_path(supplied[0][1].split("/")) if supplied else None
    return tasklist.run(Path(args.root), store, under=under)


def main(argv: list[str]) -> int:
    spec = build_spec()

    def configure_parser(_parser, subparsers) -> None:
        tasklist_parser = subparsers.add_parser(
            "tasklist",
            help="Export active Rules into taskctl as Tasks, grouped by metagroup path",
        )
        for level in spec.metagroup_levels:
            tasklist_parser.add_argument(
                f"--{level.type.lower()}", dest=_tasklist_dest(level.type), default=None,
                help=f"Restrict export to this {level.type} metagroup path, including descendants",
            )

    extra_handlers = {"tasklist": lambda store, args: _handle_tasklist(spec, store, args)}
    return cliapp.main(spec, argv, extra_handlers=extra_handlers, configure_parser=configure_parser)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
