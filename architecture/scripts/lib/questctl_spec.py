"""questctl's ToolSpec (design-questctl.md), extracted into a shared lib
module the same way lib/taskctl_spec.py/lib/adrctl_spec.py already are, so
questctl.py stays a thin CLI wrapper.

Reuses taskctl's status machine verbatim (design-questctl.md, "Status":
"unchanged from taskctl") via a direct import from lib/taskctl_spec.py,
rather than duplicating it -- see that module's docstring for why that's a
plain import and not a third, more general module.
"""

from __future__ import annotations

from lib.taskctl_spec import (
    BLOCKED, DONE, IN_PROGRESS, OPEN, REVIEW_SUBAGENT, REVIEW_USER, review_metainfo_guard,
    validate_transition,
)
from lib.toolspec import MetagroupLevelSpec, MetainfoSpec, StatusSpec, ToolSpec


def build_spec() -> ToolSpec:
    return ToolSpec(
        name="questctl",
        metagroup_levels=(
            MetagroupLevelSpec(type="Group"),
            MetagroupLevelSpec(type="Subgroup"),
        ),
        metainfo=(
            MetainfoSpec(type="review", choices=("none", "user", "subagent")),
            MetainfoSpec(type="assignee-type"),
            MetainfoSpec(type="assignee-name"),
            # design-questctl.md, "Metainfo": traceability back to the
            # document/passage a Question was drawn from -- same convention
            # as rulectl's own `source` field, and (design-decisions.md,
            # "Amendments (2026-08-25, taskctl-author/taskctl-worker
            # Subagent design)") taskctl's own `source` field, added later
            # for the identical reason once taskctl-author started
            # bulk-authoring Tasks from source documents too.
            MetainfoSpec(type="source"),
        ),
        status=StatusSpec(
            codes=(OPEN, IN_PROGRESS, REVIEW_USER, REVIEW_SUBAGENT, BLOCKED, DONE),
            initial=OPEN,
            transition_validator=validate_transition,
        ),
        # Answer is bespoke (design-questctl.md, "Operations"): it still
        # renders/parses as a normal `### Answer` section (hence its
        # presence here), but no_generic_setter (below) suppresses the
        # generic `set-answer` command and the `--answer` inline `add` flag
        # that would otherwise be auto-generated for it -- questctl.py's own
        # `answer` command is the only write path.
        user_content_blocks=("Description", "Answer"),
        root_name="questions",
        default_mode="directory",
        variable_depth=True,
        no_generic_setter=("Answer",),
        # design-questctl.md, "Guards": taskctl's review protection applies
        # verbatim; its sequence guard does not -- Questions are worked in
        # parallel by design.
        metainfo_guard=review_metainfo_guard,
    )
