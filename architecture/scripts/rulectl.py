#!/usr/bin/env python3
"""rulectl -- CLI for the rulectl object type (design-rulectl.md).

Objects are checks applicable to a code or data base, classified by a
3-level Language/Context/Category metagroup. No transition validator: every
manual status change is accepted (design.md/design-decisions.md, "no
automatic transitions" -- rulectl deliberately does not restrict which
manual transitions are allowed, unlike taskctl).
"""

from __future__ import annotations

import sys

from lib import cliapp
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
        deferred_operations=("tasklist",),
    )


def main(argv: list[str]) -> int:
    spec = build_spec()
    extra_handlers: dict = {}

    def configure_parser(_parser, subparsers) -> None:
        for name in spec.deferred_operations:
            cliapp.register_deferred(subparsers, name, extra_handlers)

    return cliapp.main(spec, argv, extra_handlers=extra_handlers, configure_parser=configure_parser)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
