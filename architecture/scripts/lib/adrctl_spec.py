"""adrctl's ToolSpec, extracted from adrctl.py into a shared lib module so
lib/adr_lookup.py can construct a lib/store.py Store against the adrctl
store without adrctl.py itself needing to be imported (architecture/scripts/
CLAUDE.md: "a CLI script never imports another CLI script as a whole").
adrctl.py imports build_spec() from here instead of defining it locally --
single source of truth, no risk of the two drifting apart.
"""

from __future__ import annotations

from lib.toolspec import MetagroupLevelSpec, MetainfoSpec, StatusSpec, ToolSpec


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
    )
