#!/usr/bin/env python3
"""adrctl -- CLI for the adrctl object type (design-adrctl.md).

Objects are ADRs whose implementation in a codebase is to be verified,
classified by a 2-level Domain/Component metagroup. No transition
validator: every manual status change is accepted, same rationale as
rulectl.

`spec-ref` (design-adrctl.md, "Metainfo") links an ADR to the specctl
Section it governs: after a successful `add`, `set-status`, or
`set-spec-ref` that leaves `spec-ref` set, lib/spec_link.py propagates the
ADR's ID into that Section's `adr` field (design-specctl.md, "ADR
Linkage"). This runs via cliapp.main()'s `after_dispatch` hook rather than
adrctl importing specctl.py directly (architecture/scripts/CLAUDE.md: "a
CLI script never imports another CLI script as a whole") -- both tools
instead import the shared lib/spec_link.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib import cliapp, spec_link
from lib.model import ObjectRecord
from lib.store import Store
from lib.toolspec import MetagroupLevelSpec, MetainfoSpec, StatusSpec, ToolSpec

_SPEC_LINK_TRIGGERS = ("add", "set-status", "set-spec-ref")


def build_spec() -> ToolSpec:
    return ToolSpec(
        name="adrctl",
        metagroup_levels=(
            MetagroupLevelSpec(type="Domain"),
            MetagroupLevelSpec(type="Component"),
        ),
        metainfo=(
            MetainfoSpec(type="superseded-by"),
            MetainfoSpec(type="spec-ref"),
        ),
        status=StatusSpec(
            codes=("proposed", "accepted", "deprecated", "superseded", "rejected"),
            initial="proposed",
        ),
        user_content_blocks=("Motivation", "Description", "Rationale"),
        root_name="adrs",
        default_mode="directory",
        deferred_operations=("tasklist",),
    )


def _handle_spec_link(
    _spec: ToolSpec, _store: Store, args: argparse.Namespace, result: object
) -> None:
    if args.command not in _SPEC_LINK_TRIGGERS or not isinstance(result, ObjectRecord):
        return
    spec_ref = result.metainfo_value("spec-ref")
    if not spec_ref:
        return
    try:
        spec_link.propagate(Path(args.root), spec_ref, result.object_id, message=f"adr={result.object_id}")
    except spec_link.SpecLinkError as exc:
        raise cliapp.CliError(str(exc)) from exc


def main(argv: list[str]) -> int:
    spec = build_spec()
    extra_handlers: dict = {}

    def configure_parser(_parser, subparsers) -> None:
        for name in spec.deferred_operations:
            cliapp.register_deferred(subparsers, name, extra_handlers)

    return cliapp.main(
        spec, argv,
        extra_handlers=extra_handlers, configure_parser=configure_parser,
        after_dispatch=_handle_spec_link,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
