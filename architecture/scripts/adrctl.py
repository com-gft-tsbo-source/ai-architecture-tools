#!/usr/bin/env python3
"""adrctl -- CLI for the adrctl object type (design-adrctl.md).

Objects are ADRs whose implementation in a codebase is to be verified,
classified by a 2-level Domain/Component metagroup. No transition
validator: every manual status change is accepted, same rationale as
rulectl.
"""

from __future__ import annotations

import sys

from lib import cliapp
from lib.toolspec import MetagroupLevelSpec, MetainfoSpec, StatusSpec, ToolSpec


def build_spec() -> ToolSpec:
    return ToolSpec(
        name="adrctl",
        metagroup_levels=(
            MetagroupLevelSpec(type="Domain"),
            MetagroupLevelSpec(type="Component"),
        ),
        metainfo=(MetainfoSpec(type="superseded-by"),),
        status=StatusSpec(
            codes=("proposed", "accepted", "deprecated", "superseded", "rejected"),
            initial="proposed",
        ),
        user_content_blocks=("Motivation", "Description", "Rationale"),
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
